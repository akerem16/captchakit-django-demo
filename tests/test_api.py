from typing import Any

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from captcha_demo.captcha import manager
from tests.helpers import FrozenClock, solution_for

pytestmark = pytest.mark.django_db

PASSWORD = "Gizli-Parola-2026"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def new_captcha(api: APIClient) -> tuple[str, str]:
    response = api.post("/api/captcha/")
    assert response.status_code == 201
    challenge_id: str = response.json()["id"]
    return challenge_id, solution_for(challenge_id)


def register(api: APIClient, **overrides: Any) -> Any:
    challenge_id, solution = new_captcha(api)
    body = {
        "username": "ayse",
        "password": PASSWORD,
        "captcha_id": challenge_id,
        "captcha_answer": solution,
        **overrides,
    }
    return api.post("/api/register/", body, format="json")


# --- POST /api/captcha/ -----------------------------------------------------


def test_issue_captcha(api: APIClient) -> None:
    response = api.post("/api/captcha/")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "image_url", "expires_in"}
    assert body["image_url"] == f"http://testserver/captcha/{body['id']}.png"
    assert body["expires_in"] == 180

    image = api.get(f"/captcha/{body['id']}.png")
    assert image.status_code == 200
    assert image["Content-Type"] == "image/png"


def test_issue_captcha_is_rate_limited_per_ip(api: APIClient) -> None:
    for _ in range(5):
        assert api.post("/api/captcha/").status_code == 201
    response = api.post("/api/captcha/")
    assert response.status_code == 429
    assert response.json() == {
        "detail": "Çok fazla istek. Lütfen biraz sonra tekrar deneyin.",
        "code": "rate_limited",
    }
    assert response["Retry-After"] == "1"

    other_ip = api.post("/api/captcha/", REMOTE_ADDR="10.0.0.2")
    assert other_ip.status_code == 201


def test_rate_limit_key_behind_cloudflare_and_render(api: APIClient, settings: Any) -> None:
    # The header chain measured on Render: "<client>, <Cloudflare edge>, <Render proxy>".
    # The proxies change per request; the client (3rd from the right) does not.
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 3}
    chains = [
        "78.188.230.26, 172.70.247.236, 10.24.75.94",
        "78.188.230.26, 104.23.180.220, 10.31.172.142",
        "1.2.3.4, 78.188.230.26, 104.23.180.221, 10.31.172.143",  # client spoofs a prefix
    ]
    for i in range(5):
        response = api.post("/api/captcha/", HTTP_X_FORWARDED_FOR=chains[i % 2])
        assert response.status_code == 201
    assert api.post("/api/captcha/", HTTP_X_FORWARDED_FOR=chains[2]).status_code == 429
    other_client = "203.0.113.7, 172.70.247.236, 10.24.75.94"
    assert api.post("/api/captcha/", HTTP_X_FORWARDED_FOR=other_client).status_code == 201


def test_captcha_endpoint_is_post_only(api: APIClient) -> None:
    assert api.get("/api/captcha/").status_code == 405


# --- POST /api/register/ ----------------------------------------------------


def test_register_201(api: APIClient) -> None:
    response = register(api)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ayse"
    assert set(body) == {"id", "username"}
    assert User.objects.get(username="ayse").check_password(PASSWORD)


def test_register_wrong_captcha_400(api: APIClient) -> None:
    response = register(api, captcha_answer="yanlis")
    assert response.status_code == 400
    assert response.json()["code"] == "captcha_invalid"
    assert not User.objects.exists()


def test_register_missing_captcha_400(api: APIClient) -> None:
    response = api.post("/api/register/", {"username": "ayse", "password": PASSWORD}, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "captcha_required"


def test_register_unknown_captcha_404(api: APIClient) -> None:
    response = register(api, captcha_id="0" * 32)
    assert response.status_code == 404
    assert response.json()["code"] == "captcha_not_found"


def test_register_expired_captcha_410(api: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    challenge_id, solution = new_captcha(api)
    monkeypatch.setattr(manager, "clock", FrozenClock(manager.clock.now() + manager.ttl + 1))
    response = api.post(
        "/api/register/",
        {
            "username": "ayse",
            "password": PASSWORD,
            "captcha_id": challenge_id,
            "captcha_answer": solution,
        },
        format="json",
    )
    assert response.status_code == 410
    assert response.json()["code"] == "captcha_expired"


def test_register_too_many_attempts_429(api: APIClient) -> None:
    challenge_id, _ = new_captcha(api)
    body = {
        "username": "ayse",
        "password": PASSWORD,
        "captcha_id": challenge_id,
        "captcha_answer": "yanlis",
    }
    statuses = [api.post("/api/register/", body, format="json").status_code for _ in range(4)]
    # Two wrong answers are retryable, the third exhausts the captcha, then it is gone.
    assert statuses == [400, 400, 429, 404]


def test_captcha_cannot_be_reused(api: APIClient) -> None:
    challenge_id, solution = new_captcha(api)
    body = {"password": PASSWORD, "captcha_id": challenge_id, "captcha_answer": solution}
    first = api.post("/api/register/", {**body, "username": "ayse"}, format="json")
    second = api.post("/api/register/", {**body, "username": "mehmet"}, format="json")
    assert first.status_code == 201
    assert second.status_code == 404


def test_captcha_is_checked_before_other_fields(api: APIClient) -> None:
    # A taken username must not be revealed to a request without a solved captcha.
    User.objects.create_user("ayse", password=PASSWORD)
    response = register(api, captcha_answer="yanlis")
    assert response.status_code == 400
    assert response.json()["code"] == "captcha_invalid"


def test_register_taken_username_400(api: APIClient) -> None:
    User.objects.create_user("Ayse", password=PASSWORD)
    response = register(api)
    assert response.status_code == 400
    assert response.json() == {"username": ["Bu kullanıcı adı zaten alınmış."]}


def test_register_weak_password_400(api: APIClient) -> None:
    response = register(api, password="123")
    assert response.status_code == 400
    assert "password" in response.json()


def test_register_rejects_non_object_body(api: APIClient) -> None:
    response = api.post("/api/register/", ["not", "an", "object"], format="json")
    assert response.status_code == 400


# --- POST /api/token/ and GET /api/me/ --------------------------------------


@pytest.fixture
def user() -> User:
    return User.objects.create_user("ayse", password=PASSWORD)


def token_request(api: APIClient, password: str = PASSWORD, answer: str | None = None) -> Any:
    challenge_id, solution = new_captcha(api)
    body = {
        "username": "ayse",
        "password": password,
        "captcha_id": challenge_id,
        "captcha_answer": solution if answer is None else answer,
    }
    return api.post("/api/token/", body, format="json")


def test_token_and_me(api: APIClient, user: User) -> None:
    response = token_request(api)
    assert response.status_code == 200
    token = response.json()["token"]
    assert Token.objects.get(user=user).key == token

    api.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    me = api.get("/api/me/")
    assert me.status_code == 200
    assert me.json()["username"] == "ayse"


def test_token_wrong_password_400(api: APIClient, user: User) -> None:
    response = token_request(api, password="hatali")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Kullanıcı adı veya şifre hatalı."]}


def test_token_wrong_captcha_400(api: APIClient, user: User) -> None:
    response = token_request(api, answer="yanlis")
    assert response.status_code == 400
    assert response.json()["code"] == "captcha_invalid"


def test_me_requires_token(api: APIClient) -> None:
    assert api.get("/api/me/").status_code == 401


# --- OpenAPI ----------------------------------------------------------------


def test_schema_and_docs(api: APIClient) -> None:
    schema = api.get("/api/schema/")
    assert schema.status_code == 200
    assert b"/api/register/" in schema.content

    docs = api.get("/api/docs/")
    assert docs.status_code == 200
    html = docs.content.decode()
    assert "swagger-ui" in html
    assert "cdn.jsdelivr.net" not in html
