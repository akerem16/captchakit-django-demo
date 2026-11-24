"""``/healthz`` for Render's health check: is the database reachable, and Redis if configured?

Implemented as the first middleware so it answers before ``ALLOWED_HOSTS`` validation and
the HTTPS redirect: a health checker may call the instance over plain HTTP with an internal
host name.
"""

from collections.abc import Callable

from asgiref.sync import async_to_sync
from captchakit.storage.redis import RedisStorage
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse

from captcha_demo.captcha import storage
from captcha_demo.loop_bridge import LoopBridgedStorage

HEALTH_PATH = "/healthz"


def check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # any failure means "unhealthy"
        return "error"
    return "ok"


def check_redis() -> str:
    if not (isinstance(storage, LoopBridgedStorage) and isinstance(storage.inner, RedisStorage)):
        return "not configured"
    client = storage.inner.client

    async def ping() -> None:
        await client.ping()

    try:
        async_to_sync(storage.loop.run)(ping())
    except Exception:  # any failure means "unhealthy"
        return "error"
    return "ok"


def health_response() -> JsonResponse:
    checks = {"database": check_database(), "redis": check_redis()}
    healthy = "error" not in checks.values()
    return JsonResponse(
        {"status": "ok" if healthy else "error", "checks": checks},
        status=200 if healthy else 503,
    )


class HealthCheckMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == HEALTH_PATH:
            return health_response()
        return self.get_response(request)
