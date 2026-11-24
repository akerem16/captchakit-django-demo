from captchakit.adapters.django import captcha_image_view
from django.urls import path

from captcha_demo.captcha import manager
from captcha_demo.views import home

urlpatterns = [
    path("", home, name="home"),
    path("captcha/<str:challenge_id>.png", captcha_image_view(manager), name="captcha-image"),
]
