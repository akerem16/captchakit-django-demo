"""Reusable Django REST Framework pieces for captchakit.

Written so it could later move into captchakit as ``adapters/drf``:

* :class:`CaptchaSerializerMixin` adds ``captcha_id`` + ``captcha_answer`` to any serializer
  and checks them *before* the other fields, so a request without a solved captcha learns
  nothing (not even "this username is taken").
* :class:`CaptchaError` turns a captcha failure into the right HTTP status:
  400 wrong/missing, 404 unknown or used, 410 expired, 429 attempts exhausted/rate limited.
"""

import math
from collections.abc import Mapping
from typing import Any, ClassVar

from captchakit import CaptchaManager
from rest_framework import serializers
from rest_framework.exceptions import APIException

from captcha_demo.errors import CaptchaFailure, check_answer


class CaptchaError(APIException):
    """Response body: ``{"detail": "<message>", "code": "<code>"}``."""

    def __init__(self, failure: CaptchaFailure, *, retry_after: float | None = None) -> None:
        self.status_code = failure.status
        # DRF's exception handler turns `wait` into a Retry-After header.
        self.wait = math.ceil(retry_after) if retry_after else None
        super().__init__(detail={"detail": failure.message, "code": failure.code})


class CaptchaSerializerMixin(serializers.Serializer):  # type: ignore[type-arg]
    """Put first in the bases: ``class S(CaptchaSerializerMixin, serializers.ModelSerializer)``.

    Subclasses set ``captcha_manager``. A ``ModelSerializer`` must list ``captcha_id`` and
    ``captcha_answer`` in ``Meta.fields``.
    """

    captcha_id = serializers.CharField(
        write_only=True, max_length=64, help_text="`id` from `POST /api/captcha/`."
    )
    captcha_answer = serializers.CharField(
        write_only=True, max_length=32, help_text="The characters shown in the image."
    )

    captcha_manager: ClassVar[CaptchaManager]

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, Mapping):
            failure = check_answer(
                self.captcha_manager,
                str(data.get("captcha_id") or ""),
                str(data.get("captcha_answer") or ""),
            )
            if failure is not None:
                raise CaptchaError(failure)
        values = super().to_internal_value(data)
        values.pop("captcha_id", None)
        values.pop("captcha_answer", None)
        return values


class CaptchaChallengeSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Response of the endpoint that issues a captcha."""

    id = serializers.CharField(help_text="Send back as `captcha_id`.")
    image_url = serializers.URLField(help_text="PNG image to show to the user.")
    expires_in = serializers.IntegerField(help_text="Seconds until the captcha expires.")


class CaptchaErrorSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Body of a captcha error response (for the OpenAPI schema)."""

    detail = serializers.CharField()
    code = serializers.CharField()
