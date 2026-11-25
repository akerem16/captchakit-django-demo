import pytest
from django.conf import settings
from django.test import Client
from rest_framework.test import APIClient

from tests.helpers import fresh_captcha

pytestmark = pytest.mark.django_db

REGISTER_URL = "/accounts/register/"


def wrong_captcha_register(client: Client) -> str:
    challenge_id, _ = fresh_captcha(client, REGISTER_URL)
    response = client.post(
        REGISTER_URL,
        {
            "username": "ayse",
            "password1": "Gizli-Parola-2026",
            "password2": "Gizli-Parola-2026",
            "captcha_0": challenge_id,
            "captcha_1": "yanlis",
        },
    )
    return response.content.decode()


def test_english_by_default(client: Client) -> None:
    response = client.get("/")
    assert response["Content-Language"] == "en"
    assert '<html lang="en">' in response.content.decode()
    assert "Create an account" in response.content.decode()


def test_browser_language_does_not_switch_html_pages(client: Client) -> None:
    # The demo looks the same to every first-time visitor.
    response = client.get("/", HTTP_ACCEPT_LANGUAGE="tr-TR,tr;q=0.9")
    assert response["Content-Language"] == "en"


def test_language_switch_sets_cookie_and_redirects(client: Client) -> None:
    response = client.post("/i18n/setlang/", {"language": "tr", "next": REGISTER_URL})
    assert response.status_code == 302
    assert response["Location"] == REGISTER_URL
    assert client.cookies[settings.LANGUAGE_COOKIE_NAME].value == "tr"

    page = client.get(REGISTER_URL).content.decode()
    assert '<html lang="tr">' in page
    assert "Hesap oluştur" in page
    assert "Doğrulama" in page


def test_turkish_form_errors(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "tr"
    assert "Captcha cevabı yanlış." in wrong_captcha_register(client)


def test_english_form_errors(client: Client) -> None:
    assert "The captcha answer is wrong." in wrong_captcha_register(client)


def test_unknown_language_cookie_falls_back_to_english(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "xx"
    assert client.get("/")["Content-Language"] == "en"


@pytest.mark.parametrize(
    ("accept_language", "detail"),
    [
        ("", "This captcha does not exist or was already used. Please try a new one."),
        ("tr", "Bu captcha bulunamadı ya da zaten kullanıldı. Lütfen yenisini deneyin."),
    ],
)
def test_api_follows_accept_language(accept_language: str, detail: str) -> None:
    api = APIClient()
    body = {
        "username": "ayse",
        "password": "Gizli-Parola-2026",
        "captcha_id": "0" * 32,
        "captcha_answer": "ABCDE",
    }
    response = api.post("/api/register/", body, format="json", HTTP_ACCEPT_LANGUAGE=accept_language)
    assert response.status_code == 404
    assert response.json() == {"detail": detail, "code": "captcha_not_found"}


def test_every_page_renders_in_both_languages(client: Client) -> None:
    for language in ("en", "tr"):
        client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
        for url in ("/", REGISTER_URL, "/accounts/login/"):
            response = client.get(url)
            assert response.status_code == 200
            assert response["Content-Language"] == language
