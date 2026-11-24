import asyncio
import os

import pytest
from asgiref.sync import async_to_sync
from captchakit import Challenge, MemoryStorage

from captcha_demo.loop_bridge import BackgroundLoop, LoopBridgedStorage


def make_challenge(challenge_id: str = "abc") -> Challenge:
    return Challenge(
        id=challenge_id,
        prompt="ABCDE",
        solution="ABCDE",
        case_sensitive=False,
        created_at=0.0,
        expires_at=1e12,
    )


def test_calls_from_different_loops_run_on_one_loop() -> None:
    bridge = BackgroundLoop()

    async def current_loop() -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    # Each async_to_sync call runs in a fresh, short-lived event loop ...
    first = async_to_sync(bridge.run)(current_loop())
    second = async_to_sync(bridge.run)(current_loop())
    # ... but the wrapped coroutine always runs on the bridge's loop.
    assert first is second is bridge.get_loop()


def test_new_loop_after_fork(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = BackgroundLoop()
    parent_loop = bridge.get_loop()
    monkeypatch.setattr(os, "getpid", lambda: -1)
    assert bridge.get_loop() is not parent_loop


def test_bridged_storage_round_trip() -> None:
    storage = LoopBridgedStorage(MemoryStorage())
    challenge = make_challenge()

    async_to_sync(storage.put)(challenge)
    assert async_to_sync(storage.get)("abc") == challenge
    assert async_to_sync(storage.incr_attempts)("abc") == 1
    async_to_sync(storage.delete)("abc")
    assert async_to_sync(storage.get)("abc") is None
