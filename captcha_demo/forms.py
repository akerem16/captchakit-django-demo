from typing import Any

from captchakit import CaptchaManager
from captchakit.adapters.django import CaptchaField
from django.core.exceptions import ValidationError

from captcha_demo.captcha import manager as default_manager
from captcha_demo.errors import check_answer


class DemoCaptchaField(CaptchaField):
    """captchakit's ``CaptchaField`` with Turkish messages and stable error codes."""

    def __init__(self, manager: CaptchaManager = default_manager, **kwargs: Any) -> None:
        kwargs.setdefault("label", "Doğrulama")
        kwargs.setdefault(
            "help_text", "Görseldeki karakterleri yazın (büyük/küçük harf fark etmez)."
        )
        super().__init__(manager=manager, **kwargs)
        self.manager = manager
        answer_input = self.widget.widgets[1]
        answer_input.attrs.update(
            {"autocomplete": "off", "autocapitalize": "characters", "spellcheck": "false"}
        )

    def clean(self, value: Any) -> tuple[str, str]:
        challenge_id, answer = self.compress(value) if isinstance(value, list) else ("", "")
        failure = check_answer(self.manager, challenge_id, answer)
        if failure is not None:
            raise ValidationError(failure.message, code=failure.code)
        return (challenge_id, answer)
