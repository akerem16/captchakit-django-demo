import pytest
from captchakit import MemoryStorage
from captchakit.storage.redis import RedisStorage
from django.db import connection
from django.test import Client

from captcha_demo import health
from captcha_demo.loop_bridge import LoopBridgedStorage

pytestmark = pytest.mark.django_db


class FakeRedis:
    def __init__(self, *, up: bool) -> None:
        self.up = up

    async def ping(self) -> bool:
        if not self.up:
            raise ConnectionError("redis is down")
        return True


def use_redis(monkeypatch: pytest.MonkeyPatch, *, up: bool) -> None:
    storage = LoopBridgedStorage(RedisStorage(client=FakeRedis(up=up)))  # type: ignore[arg-type]
    monkeypatch.setattr(health, "storage", storage)


def test_healthy_without_redis(client: Client) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "not configured"},
    }


def test_healthy_with_redis(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    use_redis(monkeypatch, up=True)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["checks"]["redis"] == "ok"


def test_redis_down_is_503(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    use_redis(monkeypatch, up=False)
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "checks": {"database": "ok", "redis": "error"}}


def test_database_down_is_503(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_cursor() -> None:
        raise RuntimeError("database is down")

    monkeypatch.setattr(connection, "cursor", broken_cursor)
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"


def test_health_ignores_unknown_host(client: Client) -> None:
    # Answered before ALLOWED_HOSTS validation: a checker may use any Host header.
    assert client.get("/healthz", HTTP_HOST="10.0.0.7:10000").status_code == 200
    assert client.get("/", HTTP_HOST="10.0.0.7:10000").status_code == 400


def test_memory_storage_reports_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "storage", MemoryStorage())
    assert health.check_redis() == "not configured"
