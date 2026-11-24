from asgiref.sync import async_to_sync
from django.test import Client

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
