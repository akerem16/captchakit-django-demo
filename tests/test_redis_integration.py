"""Runs against a real Redis (CI service container): ``TEST_REDIS_URL=... pytest -m redis``."""

import os

import pytest
from asgiref.sync import async_to_sync
from captchakit import CaptchaManager, ImageRenderer, TextChallengeFactory
from captchakit.storage.redis import RedisStorage
from redis.asyncio import Redis

from captcha_demo.captcha import build_storage

REDIS_URL = os.environ.get("TEST_REDIS_URL", "")

pytestmark = [
    pytest.mark.redis,
    pytest.mark.skipif(not REDIS_URL, reason="TEST_REDIS_URL is not set"),
]


def test_plain_client_breaks_across_async_to_sync_calls() -> None:
    # Documents why LoopBridgedStorage exists: the pooled connection from the
    # first call belongs to an event loop that async_to_sync already closed.
    storage = RedisStorage(client=Redis.from_url(REDIS_URL), prefix="test-plain")
    assert async_to_sync(storage.get)("missing") is None
    with pytest.raises(RuntimeError, match="Event loop is closed"):
        async_to_sync(storage.get)("missing")


def test_bridged_storage_works_across_calls() -> None:
    manager = CaptchaManager(
        factory=TextChallengeFactory(length=5),
        renderer=ImageRenderer(),
        storage=build_storage(REDIS_URL),
    )
    for _ in range(3):
        challenge_id, _png = async_to_sync(manager.issue)()
        challenge = async_to_sync(manager.storage.get)(challenge_id)
        assert challenge is not None
        assert async_to_sync(manager.verify)(challenge_id, challenge.solution) is True
        assert async_to_sync(manager.storage.get)(challenge_id) is None
