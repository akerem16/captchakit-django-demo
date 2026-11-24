"""Test settings: no Redis, no static file serving, fast password hashing."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "tests-only-not-a-secret")

from config.settings import *  # noqa: F403
from config.settings import MIDDLEWARE, STORAGES

REDIS_URL = ""
# WhiteNoise scans STATIC_ROOT at startup, which only exists after collectstatic.
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith("whitenoise.")]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
