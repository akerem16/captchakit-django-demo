from captchakit import MemoryStorage
from captchakit.storage.redis import RedisStorage
from django.conf import settings

from captcha_demo.captcha import build_storage, manager
from captcha_demo.loop_bridge import LoopBridgedStorage


def test_memory_storage_without_redis_url() -> None:
    assert isinstance(build_storage(""), MemoryStorage)


def test_bridged_redis_storage_with_redis_url() -> None:
    # Building the client does not connect, so no Redis server is needed here.
    storage = build_storage("redis://localhost:6379/0")
    assert isinstance(storage, LoopBridgedStorage)
    assert isinstance(storage.inner, RedisStorage)


def test_manager_uses_settings() -> None:
    assert isinstance(manager.storage, MemoryStorage)
    assert manager.ttl == settings.CAPTCHA_TTL == 180
    assert manager.max_attempts == settings.CAPTCHA_MAX_ATTEMPTS == 3
