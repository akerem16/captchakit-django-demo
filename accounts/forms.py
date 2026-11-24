from typing import TYPE_CHECKING, Any

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from captcha_demo.forms import DemoCaptchaField

if TYPE_CHECKING:
    _UserCreationForm = UserCreationForm[User]
else:
    _UserCreationForm = UserCreationForm


class RegisterForm(_UserCreationForm):
    """Username + password (twice) + captcha."""

    captcha = DemoCaptchaField()


class LoginForm(AuthenticationForm):
    """Django's login form + captcha."""

    captcha = DemoCaptchaField()

    def clean(self) -> dict[str, Any]:
        # AuthenticationForm.clean() checks the password. Skip it when the captcha
        # failed, otherwise "wrong password" vs. "wrong captcha" would let a bot
        # test passwords without ever solving a captcha.
        if self.has_error("captcha"):
            return self.cleaned_data
        return super().clean()
