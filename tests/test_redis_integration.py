"""Runs against a real Redis (CI service container): ``TEST_REDIS_URL=... pytest -m redis``."""

import os
import subprocess
import sys
import textwrap
import uuid

import pytest
from asgiref.sync import async_to_sync
from captchakit import CaptchaManager, ImageRenderer, RateLimited, TextChallengeFactory
from captchakit.storage.redis import RedisStorage

from captcha_demo.captcha import build_backends
from captcha_demo.loop_bridge import LoopBridgedRateLimiter, LoopBridgedStorage

REDIS_URL = os.environ.get("TEST_REDIS_URL", "")

pytestmark = [
    pytest.mark.redis,
    pytest.mark.skipif(not REDIS_URL, reason="TEST_REDIS_URL is not set"),
]


def test_plain_client_breaks_across_async_to_sync_calls() -> None:
    # Documents why LoopBridgedStorage exists: the pooled connection from the
    # first call belongs to an event loop that async_to_sync already closed.
    # Runs in a subprocess because that orphaned connection can never be closed.
    script = textwrap.dedent(
        """
        import sys
        from asgiref.sync import async_to_sync
        from captchakit.storage.redis import RedisStorage
        from redis.asyncio import Redis

        storage = RedisStorage(client=Redis.from_url(sys.argv[1]), prefix="test-plain")
        assert async_to_sync(storage.get)("missing") is None
        try:
            async_to_sync(storage.get)("missing")
        except RuntimeError as exc:
            print(exc)
        """
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-W", "ignore", "-c", script, REDIS_URL],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "Event loop is closed" in result.stdout


def test_bridged_rate_limiter_works_across_calls() -> None:
    storage, limiter = build_backends(REDIS_URL, capacity=2, refill_rate=0.001)
    assert isinstance(storage, LoopBridgedStorage)
    assert isinstance(storage.inner, RedisStorage)
    assert isinstance(limiter, LoopBridgedRateLimiter)
    key = f"test-{uuid.uuid4().hex}"
    try:
        async_to_sync(limiter.acquire)(key)
        async_to_sync(limiter.acquire)(key)
        with pytest.raises(RateLimited):
            async_to_sync(limiter.acquire)(key)
    finally:
        async_to_sync(storage.loop.run)(storage.inner.client.aclose())


def test_bridged_storage_works_across_calls() -> None:
    storage, _limiter = build_backends(REDIS_URL, capacity=5, refill_rate=1)
    assert isinstance(storage, LoopBridgedStorage)
    assert isinstance(storage.inner, RedisStorage)
    manager = CaptchaManager(
        factory=TextChallengeFactory(length=5),
        renderer=ImageRenderer(),
        storage=storage,
    )
    try:
        for _ in range(3):
            challenge_id, _png = async_to_sync(manager.issue)()
            challenge = async_to_sync(storage.get)(challenge_id)
            assert challenge is not None
            assert async_to_sync(manager.verify)(challenge_id, challenge.solution) is True
            assert async_to_sync(storage.get)(challenge_id) is None
    finally:
        async_to_sync(storage.loop.run)(storage.inner.client.aclose())
