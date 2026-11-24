import pytest
from captchakit import TokenBucketRateLimiter

from accounts import api
from tests.helpers import FrozenClock


@pytest.fixture(autouse=True)
def fresh_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> TokenBucketRateLimiter:
    """A new, time-frozen API rate limiter per test (5 requests, no refill)."""
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1, clock=FrozenClock(0.0))
    monkeypatch.setattr(api, "issue_limiter", limiter)
    return limiter
