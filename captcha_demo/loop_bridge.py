"""Run async storage calls on one long-lived event loop.

captchakit's Django adapter calls the async manager through ``asgiref.async_to_sync``.
Under WSGI (gunicorn sync workers) every such call creates a new event loop and closes
it afterwards. A ``redis.asyncio`` connection belongs to the loop it was opened on, so
reusing the same client on the next call fails with ``RuntimeError: Event loop is closed``.

:class:`LoopBridgedStorage` and :class:`LoopBridgedRateLimiter` forward every call to a
single background loop, so the Redis client and its connection pool always live on the
same loop.
"""

import asyncio
import os
import threading
from collections.abc import Coroutine
from typing import Any

from captchakit import Challenge, RateLimiter, Storage


class BackgroundLoop:
    """An event loop running forever in a daemon thread, started on first use."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pid: int | None = None

    def get_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            # Threads do not survive fork(): start a new loop in a forked worker.
            if self._loop is None or self._pid != os.getpid():
                loop = asyncio.new_event_loop()
                thread = threading.Thread(target=loop.run_forever, name="captcha-loop", daemon=True)
                thread.start()
                self._loop, self._pid = loop, os.getpid()
            return self._loop

    async def run[T](self, coro: Coroutine[Any, Any, T]) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self.get_loop())
        return await asyncio.wrap_future(future)


class LoopBridgedStorage:
    """A captchakit ``Storage`` that runs the wrapped storage on a background loop."""

    def __init__(self, inner: Storage, loop: BackgroundLoop | None = None) -> None:
        self.inner = inner
        self.loop = loop or BackgroundLoop()

    async def put(self, challenge: Challenge) -> None:
        await self.loop.run(self.inner.put(challenge))

    async def get(self, challenge_id: str) -> Challenge | None:
        return await self.loop.run(self.inner.get(challenge_id))

    async def delete(self, challenge_id: str) -> None:
        await self.loop.run(self.inner.delete(challenge_id))

    async def incr_attempts(self, challenge_id: str) -> int:
        return await self.loop.run(self.inner.incr_attempts(challenge_id))


class LoopBridgedRateLimiter:
    """A captchakit ``RateLimiter`` that runs the wrapped limiter on a background loop."""

    def __init__(self, inner: RateLimiter, loop: BackgroundLoop | None = None) -> None:
        self.inner = inner
        self.loop = loop or BackgroundLoop()

    async def acquire(self, key: str) -> None:
        await self.loop.run(self.inner.acquire(key))
