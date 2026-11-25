from captchakit.adapters.django import captcha_image_view
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts import api
from captcha_demo.captcha import manager
from captcha_demo.views import home

urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("captcha/<str:challenge_id>.png", captcha_image_view(manager), name="captcha-image"),
    path("api/captcha/", api.CaptchaCreateView.as_view(), name="api-captcha"),
    path("api/register/", api.RegisterView.as_view(), name="api-register"),
    path("api/token/", api.TokenView.as_view(), name="api-token"),
    path("api/me/", api.MeView.as_view(), name="api-me"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]
