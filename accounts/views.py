from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, RegisterForm


@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:me")
    form = RegisterForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, _("Your account is ready. Welcome!"))
        return redirect("accounts:me")
    return render(request, "accounts/register.html", {"form": form})


class CaptchaLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


@login_required
def me(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/me.html")
