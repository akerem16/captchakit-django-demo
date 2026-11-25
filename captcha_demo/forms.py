from typing import Any

from captchakit import CaptchaManager
from captchakit.adapters.django import CaptchaField, CaptchaWidget
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from captcha_demo.captcha import manager as default_manager
from captcha_demo.errors import check_answer


class DemoCaptchaWidget(CaptchaWidget):
    """Points the field's ``<label>`` at the answer input.

    Django's ``MultiWidget.id_for_label()`` returns ``""``, which renders ``<label for="">``
    and leaves the answer box without an accessible name.
    """

    def id_for_label(self, id_: str) -> str:
        return f"{id_}_1" if id_ else ""


class DemoCaptchaField(CaptchaField):
    """captchakit's ``CaptchaField`` with translated messages and stable error codes."""

    def __init__(self, manager: CaptchaManager = default_manager, **kwargs: Any) -> None:
        kwargs.setdefault("label", _("Verification"))
        kwargs.setdefault("help_text", _("Type the characters in the image (not case-sensitive)."))
        super().__init__(manager=manager, **kwargs)
        self.manager = manager
        # CaptchaField builds its own CaptchaWidget, so swap in ours and repeat what
        # Field.__init__ does to a widget.
        widget = DemoCaptchaWidget(image_url_pattern=self.widget.image_url_pattern)
        widget.is_required = self.required
        # CaptchaField declares ``widget = CaptchaWidget`` (the class), so mypy types the
        # attribute as a class; at runtime Field stores an instance here.
        self.widget = widget  # type: ignore[assignment]
        answer_input = widget.widgets[1]
        answer_input.attrs.update(
            {"autocomplete": "off", "autocapitalize": "characters", "spellcheck": "false"}
        )

    def clean(self, value: Any) -> tuple[str, str]:
        challenge_id, answer = self.compress(value) if isinstance(value, list) else ("", "")
        failure = check_answer(self.manager, challenge_id, answer)
        if failure is not None:
            raise ValidationError(failure.message, code=failure.code)
        return (challenge_id, answer)
