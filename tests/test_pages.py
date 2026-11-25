from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client, RequestFactory
from django.views.defaults import server_error

from captcha_demo.captcha import manager


def test_home_page(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "captchakit" in response.content.decode()


def test_captcha_image_is_png(client: Client) -> None:
    challenge_id, _ = async_to_sync(manager.issue)()
    response = client.get(f"/captcha/{challenge_id}.png")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_unknown_captcha_image_is_404(client: Client) -> None:
    response = client.get("/captcha/does-not-exist.png")
    assert response.status_code == 404


def test_home_page_links_favicon(client: Client) -> None:
    html = client.get("/").content.decode()
    assert 'rel="icon"' in html
    assert finders.find("favicon.svg") is not None


def test_unknown_page_uses_site_404(client: Client) -> None:
    response = client.get("/no-such-page/")
    html = response.content.decode()
    assert response.status_code == 404
    assert "Page not found" in html
    assert 'href="/"' in html


def test_unknown_page_404_in_turkish(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "tr"
    response = client.get("/no-such-page/")
    assert "Sayfa bulunamadı" in response.content.decode()


def test_server_error_page() -> None:
    response = server_error(RequestFactory().get("/"))
    html = response.content.decode()
    assert response.status_code == 500
    assert "Something went wrong" in html
    assert 'href="/"' in html
