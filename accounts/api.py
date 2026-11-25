from typing import Any

from asgiref.sync import async_to_sync
from captchakit import RateLimited
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from captcha_demo.captcha import issue_limiter, manager
from captcha_demo.drf import (
    CaptchaChallengeSerializer,
    CaptchaError,
    CaptchaErrorSerializer,
    CaptchaSerializerMixin,
)
from captcha_demo.errors import failure_for

CAPTCHA_ERRORS = {
    400: OpenApiResponse(CaptchaErrorSerializer, "Captcha missing or wrong, or invalid fields."),
    404: OpenApiResponse(CaptchaErrorSerializer, "Unknown or already used captcha."),
    410: OpenApiResponse(CaptchaErrorSerializer, "Captcha expired."),
    429: OpenApiResponse(CaptchaErrorSerializer, "Too many wrong answers for this captcha."),
}


class RegisterSerializer(CaptchaSerializerMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    captcha_manager = manager
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "username", "password", "captcha_id", "captcha_answer")
        read_only_fields = ("id",)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_("This username is already taken."))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        try:
            password_validation.validate_password(
                attrs["password"], User(username=attrs["username"])
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        return User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )


class TokenRequestSerializer(CaptchaSerializerMixin, serializers.Serializer):  # type: ignore[type-arg]
    captcha_manager = manager
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = authenticate(
            self.context.get("request"), username=attrs["username"], password=attrs["password"]
        )
        if user is None:
            raise serializers.ValidationError(
                _("Wrong username or password."), code="authorization"
            )
        attrs["user"] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):  # type: ignore[type-arg]
    token = serializers.CharField(help_text="Send as `Authorization: Token <token>`.")


class UserSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = User
        fields = ("id", "username", "date_joined")


class CaptchaCreateView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Issue a captcha",
        request=None,
        responses={
            201: CaptchaChallengeSerializer,
            429: OpenApiResponse(CaptchaErrorSerializer, "Rate limited (see Retry-After)."),
        },
    )
    def post(self, request: Request) -> Response:
        client_ip = BaseThrottle().get_ident(request)
        try:
            async_to_sync(issue_limiter.acquire)(client_ip)
        except RateLimited as exc:
            raise CaptchaError(failure_for(exc), retry_after=exc.retry_after) from exc
        challenge_id, _image = async_to_sync(manager.issue)()
        image_url = request.build_absolute_uri(reverse("captcha-image", args=[challenge_id]))
        body = {"id": challenge_id, "image_url": image_url, "expires_in": int(manager.ttl)}
        return Response(CaptchaChallengeSerializer(body).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Register a user",
    responses={201: RegisterSerializer, **CAPTCHA_ERRORS},
)
class RegisterView(generics.CreateAPIView):  # type: ignore[type-arg]
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class TokenView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Log in and get a token",
        request=TokenRequestSerializer,
        responses={200: TokenResponseSerializer, **CAPTCHA_ERRORS},
    )
    def post(self, request: Request) -> Response:
        serializer = TokenRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        token, _created = Token.objects.get_or_create(user=serializer.validated_data["user"])
        return Response({"token": token.key})


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="The current user", responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)
