"""The single CaptchaManager shared by forms, views and the API, plus the API rate limiter."""

from captchakit import (
    CaptchaManager,
    ImageRenderer,
    MemoryStorage,
    RateLimiter,
    Storage,
    TextChallengeFactory,
    TokenBucketRateLimiter,
)
from django.conf import settings

from captcha_demo.loop_bridge import BackgroundLoop, LoopBridgedRateLimiter, LoopBridgedStorage


def build_backends(
    redis_url: str, *, capacity: float, refill_rate: float
) -> tuple[Storage, RateLimiter]:
    """Redis-backed storage and limiter when ``redis_url`` is set (shared by all workers),
    otherwise in-process memory (fine for one process: local runs and tests)."""
    if not redis_url:
        return MemoryStorage(), TokenBucketRateLimiter(capacity=capacity, refill_rate=refill_rate)

    from captchakit.ratelimit_redis import RedisTokenBucket  # noqa: PLC0415
    from captchakit.storage.redis import RedisStorage  # noqa: PLC0415
    from redis.asyncio import Redis  # noqa: PLC0415

    # Short timeouts so /healthz fails fast; health_check_interval re-checks idle
    # connections that the server may have closed.
    client = Redis.from_url(
        redis_url, socket_connect_timeout=2, socket_timeout=2, health_check_interval=30
    )
    loop = BackgroundLoop()
    storage = LoopBridgedStorage(RedisStorage(client=client, prefix="captchakit"), loop)
    limiter = LoopBridgedRateLimiter(
        RedisTokenBucket(
            client=client, capacity=capacity, refill_rate=refill_rate, prefix="captchakit:rl"
        ),
        loop,
    )
    return storage, limiter


storage, issue_limiter = build_backends(
    settings.REDIS_URL,
    capacity=settings.CAPTCHA_RATE_CAPACITY,
    refill_rate=settings.CAPTCHA_RATE_REFILL,
)

# No rate_limiter on the manager: CaptchaField issues with key="global", so every page
# view would share one bucket. The API applies `issue_limiter` per client IP instead.
manager = CaptchaManager(
    factory=TextChallengeFactory(length=5),
    renderer=ImageRenderer(),
    storage=storage,
    ttl=settings.CAPTCHA_TTL,
    max_attempts=settings.CAPTCHA_MAX_ATTEMPTS,
)
