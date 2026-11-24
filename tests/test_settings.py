import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import settings as config_settings


@pytest.fixture
def reload_settings(monkeypatch: pytest.MonkeyPatch):
    yield monkeypatch
    monkeypatch.undo()
    importlib.reload(config_settings)


def test_secret_key_required_in_production(reload_settings: pytest.MonkeyPatch) -> None:
    reload_settings.delenv("DJANGO_SECRET_KEY", raising=False)
    reload_settings.setenv("DJANGO_DEBUG", "false")
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(config_settings)


def test_debug_falls_back_to_dev_secret_key(reload_settings: pytest.MonkeyPatch) -> None:
    reload_settings.delenv("DJANGO_SECRET_KEY", raising=False)
    reload_settings.setenv("DJANGO_DEBUG", "true")
    importlib.reload(config_settings)
    assert config_settings.SECRET_KEY.startswith("django-insecure-")


def test_render_hostname_is_trusted(reload_settings: pytest.MonkeyPatch) -> None:
    reload_settings.setenv("RENDER_EXTERNAL_HOSTNAME", "demo.onrender.com")
    importlib.reload(config_settings)
    assert "demo.onrender.com" in config_settings.ALLOWED_HOSTS
    assert "https://demo.onrender.com" in config_settings.CSRF_TRUSTED_ORIGINS


def test_env_list_and_bool(reload_settings: pytest.MonkeyPatch) -> None:
    reload_settings.setenv("DJANGO_ALLOWED_HOSTS", " a.example.com , b.example.com,")
    reload_settings.setenv("DJANGO_DEBUG", "YES")
    importlib.reload(config_settings)
    assert config_settings.ALLOWED_HOSTS == ["a.example.com", "b.example.com"]
    assert config_settings.DEBUG is True
