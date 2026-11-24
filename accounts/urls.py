from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.CaptchaLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", views.me, name="me"),
]
