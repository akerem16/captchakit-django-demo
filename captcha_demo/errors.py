"""One place that maps captcha outcomes to a code, a Turkish message and an HTTP status.

Both the HTML form field and the DRF serializer use it, so a wrong, unknown, expired or
exhausted captcha reads the same everywhere.
"""

from dataclasses import dataclass
from http import HTTPStatus

from asgiref.sync import async_to_sync
from captchakit import (
    CaptchaKitError,
    CaptchaManager,
    ChallengeError,
    ChallengeExpired,
    RateLimited,
    TooManyAttempts,
)


@dataclass(frozen=True, slots=True)
class CaptchaFailure:
    code: str
    message: str
    status: HTTPStatus


REQUIRED = CaptchaFailure(
    "captcha_required", "Lütfen görseldeki karakterleri yazın.", HTTPStatus.BAD_REQUEST
)
WRONG = CaptchaFailure("captcha_invalid", "Captcha cevabı yanlış.", HTTPStatus.BAD_REQUEST)
NOT_FOUND = CaptchaFailure(
    "captcha_not_found",
    "Captcha bulunamadı ya da zaten kullanıldı. Lütfen yenisini deneyin.",
    HTTPStatus.NOT_FOUND,
)
EXPIRED = CaptchaFailure(
    "captcha_expired", "Captcha'nın süresi doldu. Lütfen yenisini deneyin.", HTTPStatus.GONE
)
TOO_MANY_ATTEMPTS = CaptchaFailure(
    "captcha_too_many_attempts",
    "Çok fazla yanlış deneme. Lütfen yeni bir captcha deneyin.",
    HTTPStatus.TOO_MANY_REQUESTS,
)
RATE_LIMITED = CaptchaFailure(
    "rate_limited",
    "Çok fazla istek. Lütfen biraz sonra tekrar deneyin.",
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
