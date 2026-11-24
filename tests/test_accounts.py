import pytest
from django.contrib.auth.models import User
from django.test import Client

from captcha_demo.captcha import manager
from tests.helpers import FrozenClock, captcha_id_from, fresh_captcha, solution_for

pytestmark = pytest.mark.django_db

REGISTER_URL = "/accounts/register/"
LOGIN_URL = "/accounts/login/"
ME_URL = "/accounts/me/"
PASSWORD = "Gizli-Parola-2026"


def register_data(challenge_id: str, answer: str, username: str = "ayse") -> dict[str, str]:
    return {
        "username": username,
        "password1": PASSWORD,
        "password2": PASSWORD,
        "captcha_0": challenge_id,
        "captcha_1": answer,
    }


def login_data(challenge_id: str, answer: str, password: str = PASSWORD) -> dict[str, str]:
    return {
        "username": "ayse",
        "password": password,
        "captcha_0": challenge_id,
        "captcha_1": answer,
    }


@pytest.fixture
def user() -> User:
    return User.objects.create_user("ayse", password=PASSWORD)


# --- register ---------------------------------------------------------------


def test_register_page_shows_captcha(client: Client) -> None:
    response = client.get(REGISTER_URL)
    html = response.content.decode()
    challenge_id = captcha_id_from(html)
    assert f'src="/captcha/{challenge_id}.png"' in html


def test_register_with_correct_captcha_logs_in(client: Client) -> None:
    challenge_id, solution = fresh_captcha(client, REGISTER_URL)
    response = client.post(REGISTER_URL, register_data(challenge_id, solution))
    assert response.status_code == 302
    assert response["Location"] == ME_URL
    assert User.objects.filter(username="ayse").exists()
    assert "Merhaba, ayse" in client.get(ME_URL).content.decode()


def test_register_answer_is_case_insensitive(client: Client) -> None:
    challenge_id, solution = fresh_captcha(client, REGISTER_URL)
    response = client.post(REGISTER_URL, register_data(challenge_id, f" {solution.lower()} "))
    assert response.status_code == 302


def test_register_with_wrong_captcha(client: Client) -> None:
    challenge_id, _ = fresh_captcha(client, REGISTER_URL)
    response = client.post(REGISTER_URL, register_data(challenge_id, "yanlis"))
    assert response.status_code == 200
    assert "Captcha cevabı yanlış." in response.content.decode()
    assert not User.objects.exists()


def test_register_with_empty_captcha(client: Client) -> None:
    challenge_id, _ = fresh_captcha(client, REGISTER_URL)
    response = client.post(REGISTER_URL, register_data(challenge_id, ""))
    assert "Lütfen görseldeki karakterleri yazın." in response.content.decode()
    assert not User.objects.exists()


def test_register_with_unknown_captcha(client: Client) -> None:
    response = client.post(REGISTER_URL, register_data("0" * 32, "ABCDE"))
    assert "Captcha bulunamadı" in response.content.decode()


def test_register_with_expired_captcha(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    challenge_id, solution = fresh_captcha(client, REGISTER_URL)
    monkeypatch.setattr(manager, "clock", FrozenClock(manager.clock.now() + manager.ttl + 1))
    response = client.post(REGISTER_URL, register_data(challenge_id, solution))
    assert "süresi doldu" in response.content.decode()
    assert not User.objects.exists()


def test_rerendered_form_shows_a_new_captcha(client: Client, user: User) -> None:
    # Correct captcha, taken username: the captcha is consumed, so the page must
    # show a new one instead of echoing the old id.
    challenge_id, solution = fresh_captcha(client, REGISTER_URL)
    response = client.post(REGISTER_URL, register_data(challenge_id, solution))
    html = response.content.decode()
    assert response.status_code == 200
    new_id = captcha_id_from(html)
    assert new_id != challenge_id
    assert solution_for(new_id)


def test_two_form_instances_have_distinct_captchas(client: Client) -> None:
    first_id, first_solution = fresh_captcha(client, REGISTER_URL)
    second_id, second_solution = fresh_captcha(Client(), REGISTER_URL)
    assert first_id != second_id

    assert client.post(REGISTER_URL, register_data(first_id, first_solution)).status_code == 302
    other = Client()
    response = other.post(REGISTER_URL, register_data(second_id, second_solution, "mehmet"))
    assert response.status_code == 302
    assert User.objects.count() == 2


def test_captcha_cannot_be_reused(client: Client) -> None:
    challenge_id, solution = fresh_captcha(client, REGISTER_URL)
    assert client.post(REGISTER_URL, register_data(challenge_id, solution)).status_code == 302
    response = Client().post(REGISTER_URL, register_data(challenge_id, solution, "mehmet"))
    assert "Captcha bulunamadı" in response.content.decode()
    assert User.objects.count() == 1


def test_too_many_wrong_answers(client: Client) -> None:
    challenge_id, _ = fresh_captcha(client, REGISTER_URL)
    for _ in range(manager.max_attempts - 1):
        client.post(REGISTER_URL, register_data(challenge_id, "yanlis"))
    response = client.post(REGISTER_URL, register_data(challenge_id, "yanlis"))
    assert "Çok fazla yanlış deneme" in response.content.decode()


def test_logged_in_user_is_redirected_from_register(client: Client, user: User) -> None:
    client.force_login(user)
    assert client.get(REGISTER_URL)["Location"] == ME_URL


# --- login / logout / me ----------------------------------------------------


def test_login_with_correct_captcha(client: Client, user: User) -> None:
    challenge_id, solution = fresh_captcha(client, LOGIN_URL)
    response = client.post(LOGIN_URL, login_data(challenge_id, solution))
    assert response.status_code == 302
    assert response["Location"] == ME_URL


def test_login_with_wrong_captcha(client: Client, user: User) -> None:
    challenge_id, _ = fresh_captcha(client, LOGIN_URL)
    response = client.post(LOGIN_URL, login_data(challenge_id, "yanlis"))
    assert response.status_code == 200
    assert "Captcha cevabı yanlış." in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_login_with_empty_captcha(client: Client, user: User) -> None:
    challenge_id, _ = fresh_captcha(client, LOGIN_URL)
    response = client.post(LOGIN_URL, login_data(challenge_id, ""))
    assert "Lütfen görseldeki karakterleri yazın." in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_wrong_captcha_does_not_reveal_password_check(client: Client, user: User) -> None:
    # Same response for a right and a wrong password while the captcha is wrong.
    challenge_id, _ = fresh_captcha(client, LOGIN_URL)
    response = client.post(LOGIN_URL, login_data(challenge_id, "yanlis", password="hatali"))
    form = response.context["form"]
    assert list(form.errors) == ["captcha"]


def test_login_with_wrong_password(client: Client, user: User) -> None:
    challenge_id, solution = fresh_captcha(client, LOGIN_URL)
    response = client.post(LOGIN_URL, login_data(challenge_id, solution, password="hatali"))
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()


def test_me_requires_login(client: Client) -> None:
    response = client.get(ME_URL)
    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN_URL)


def test_logout_requires_post(client: Client, user: User) -> None:
    client.force_login(user)
    assert client.get("/accounts/logout/").status_code == 405
    response = client.post("/accounts/logout/")
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session
