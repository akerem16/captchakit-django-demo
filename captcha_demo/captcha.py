"""The single CaptchaManager shared by forms, views and the API."""

from captchakit import (
    CaptchaManager,
    ImageRenderer,
    MemoryStorage,
    Storage,
    TextChallengeFactory,
)
from django.conf import settings

from captcha_demo.loop_bridge import LoopBridgedStorage


def build_storage(redis_url: str) -> Storage:
    """Redis when ``redis_url`` is set (shared by all workers), else in-process memory."""
    if not redis_url:
        return MemoryStorage()

    from captchakit.storage.redis import RedisStorage  # noqa: PLC0415
    from redis.asyncio import Redis  # noqa: PLC0415

    client = Redis.from_url(redis_url)
    return LoopBridgedStorage(RedisStorage(client=client, prefix="captchakit"))


def build_manager() -> CaptchaManager:
    return CaptchaManager(
        factory=TextChallengeFactory(length=5),
        renderer=ImageRenderer(),
        storage=build_storage(settings.REDIS_URL),
        ttl=settings.CAPTCHA_TTL,
        max_attempts=settings.CAPTCHA_MAX_ATTEMPTS,
    )


manager = build_manager()
