import re

from asgiref.sync import async_to_sync
from django.test.client import Client

from captcha_demo.captcha import manager

_CAPTCHA_ID = re.compile(r'name="captcha_0" value="([0-9a-f]{32})"')


def captcha_id_from(html: str) -> str:
    match = _CAPTCHA_ID.search(html)
    assert match, "no captcha id in the page"
    return match.group(1)


def solution_for(challenge_id: str) -> str:
    challenge = async_to_sync(manager.storage.get)(challenge_id)
    assert challenge is not None
    return challenge.solution


def fresh_captcha(client: Client, url: str) -> tuple[str, str]:
    """GET a form page and return ``(challenge_id, solution)`` of its captcha."""
    challenge_id = captcha_id_from(client.get(url).content.decode())
    return challenge_id, solution_for(challenge_id)


class FrozenClock:
    def __init__(self, now: float) -> None:
        self.value = now

    def now(self) -> float:
        return self.value
