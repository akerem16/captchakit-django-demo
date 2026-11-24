from captchakit import MemoryStorage, TokenBucketRateLimiter
from captchakit.ratelimit_redis import RedisTokenBucket
from captchakit.storage.redis import RedisStorage
from django.conf import settings

from captcha_demo.captcha import build_backends, manager
from captcha_demo.loop_bridge import LoopBridgedRateLimiter, LoopBridgedStorage


def test_memory_backends_without_redis_url() -> None:
    storage, limiter = build_backends("", capacity=5, refill_rate=1)
    assert isinstance(storage, MemoryStorage)
    assert isinstance(limiter, TokenBucketRateLimiter)


def test_bridged_redis_backends_with_redis_url() -> None:
    # Building the client does not connect, so no Redis server is needed here.
    storage, limiter = build_backends("redis://localhost:6379/0", capacity=5, refill_rate=1)
    assert isinstance(storage, LoopBridgedStorage)
    assert isinstance(storage.inner, RedisStorage)
    assert isinstance(limiter, LoopBridgedRateLimiter)
    assert isinstance(limiter.inner, RedisTokenBucket)
    # One client and one background loop for both.
    assert limiter.loop is storage.loop
    assert limiter.inner.client is storage.inner.client


def test_manager_uses_settings() -> None:
    assert isinstance(manager.storage, MemoryStorage)
    assert manager.ttl == settings.CAPTCHA_TTL == 180
    assert manager.max_attempts == settings.CAPTCHA_MAX_ATTEMPTS == 3
