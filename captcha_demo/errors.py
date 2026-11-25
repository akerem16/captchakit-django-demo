"""One place that maps captcha outcomes to a code, a translated message and an HTTP status.

Both the HTML form field and the DRF serializer use it, so a wrong, unknown, expired or
exhausted captcha reads the same everywhere. Messages are lazy: they are translated into
the language of the request when they are rendered.
"""

from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync
from captchakit import (
    CaptchaKitError,
    CaptchaManager,
    ChallengeError,
    ChallengeExpired,
    RateLimited,
    TooManyAttempts,
)
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise


@dataclass(frozen=True, slots=True)
class CaptchaFailure:
    code: str
    message: "StrOrPromise"
    status: HTTPStatus


REQUIRED = CaptchaFailure(
    "captcha_required", _("Please type the characters from the image."), HTTPStatus.BAD_REQUEST
)
WRONG = CaptchaFailure("captcha_invalid", _("The captcha answer is wrong."), HTTPStatus.BAD_REQUEST)
NOT_FOUND = CaptchaFailure(
    "captcha_not_found",
    _("This captcha does not exist or was already used. Please try a new one."),
    HTTPStatus.NOT_FOUND,
)
EXPIRED = CaptchaFailure(
    "captcha_expired", _("This captcha has expired. Please try a new one."), HTTPStatus.GONE
)
TOO_MANY_ATTEMPTS = CaptchaFailure(
    "captcha_too_many_attempts",
    _("Too many wrong answers. Please try a new captcha."),
    HTTPStatus.TOO_MANY_REQUESTS,
)
RATE_LIMITED = CaptchaFailure(
    "rate_limited",
    _("Too many requests. Please try again in a moment."),
    HTTPStatus.TOO_MANY_REQUESTS,
)


def failure_for(exc: CaptchaKitError) -> CaptchaFailure:
    if isinstance(exc, ChallengeExpired):
        return EXPIRED
    if isinstance(exc, TooManyAttempts):
        return TOO_MANY_ATTEMPTS
    if isinstance(exc, RateLimited):
        return RATE_LIMITED
    return NOT_FOUND


def check_answer(manager: CaptchaManager, challenge_id: str, answer: str) -> CaptchaFailure | None:
    """Verify an answer from sync code. ``None`` means the captcha was solved."""
    challenge_id, answer = challenge_id.strip(), answer.strip()
    if not challenge_id or not answer:
        return REQUIRED
    try:
        solved = async_to_sync(manager.verify)(challenge_id, answer)
    except ChallengeError as exc:
        return failure_for(exc)
    return None if solved else WRONG
