from captchakit.adapters.django import captcha_image_view
from django.urls import include, path

from captcha_demo.captcha import manager
from captcha_demo.views import home

urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("captcha/<str:challenge_id>.png", captcha_image_view(manager), name="captcha-image"),
]
