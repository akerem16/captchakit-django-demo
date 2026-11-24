# CLAUDE.md — captchakit-django-demo

Context for AI coding sessions. Read this first; update **Status** at the end of every session.

## Goal

A small Django + Django REST Framework demo that uses
[captchakit](https://github.com/akerem16/captchakit) (PyPI: `captchakit`), deployed on the
Render free tier. The owner, Ahmet Kerem Begiç (GitHub: `akerem16`), will present it in
internship interviews (Baykar web development, Python/Django + REST), so every step must be
explainable. Deadline: **2026-12-06**.

### Definition of done

- Live on Render: register, login and API flows work with a captcha.
- GitHub Actions green: `ruff check`, `ruff format --check`, `mypy`, `pytest`; coverage ≥ 85%.
- captchakit bug fixed upstream with a test and released as 1.0.2; the demo depends on `>=1.0.2`.
- README (English): live link, screenshot, architecture diagram (mermaid), local setup with
  Docker Compose, Render notes.

## Working rules

- Talk to the owner in **Turkish**, briefly (they read on a phone). UI text is Turkish; code,
  commits, README and this file are English.
- Ask only when a decision is genuinely the owner's.
- Start each session with a 3–5 bullet plan. End each session with a short Turkish
  "what we did and why" summary that explains the Django/DRF concepts used at interview level,
  plus one small change the owner can make by hand (a test, an error message).
- Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`), small commits.
  One branch + PR per session.
- No guessing: check an API in the installed package source or its docs before using it.
- No secrets in the repo. Settings come from environment variables.
- Plain CSS, no external CDN.
- When working on captchakit itself, follow its `AGENTS.md` / `CONTRIBUTING.md`
  (`mypy --strict`, ruff, coverage ≥ 90%).

## Scope

| Route | What |
|---|---|
| `/` | Home: what the demo is, captchakit link, form and API examples |
| `/accounts/register/` | username + password + `CaptchaField`; on success log in, redirect to `/accounts/me/` |
| `/accounts/login/` | `AuthenticationForm` + `CaptchaField` |
| `/accounts/logout/` | POST only |
| `/accounts/me/` | Profile |
| `/captcha/<id>.png` | `captcha_image_view` |
| `POST /api/captcha/` | `{"id", "image_url", "expires_in"}`; per-IP rate limit |
| `POST /api/register/` | `{"username", "password", "captcha_id", "captcha_answer"}` → 201; captcha errors: 400 wrong, 404 unknown, 410 expired, 429 attempts exhausted / rate limited |
| `POST /api/token/` | Login with captcha, returns a DRF token |
| `GET /api/me/` | Current user via token |
| `/api/schema/`, `/api/docs/` | drf-spectacular |
| `/healthz` | Database and Redis reachable (Render health check) |

The DRF layer lives in `captcha_demo/drf.py` as a reusable serializer mixin/field that maps
captchakit errors to DRF errors and status codes. Keep it clean enough to move into captchakit
later as `adapters/drf`, but do not add it to captchakit now.

Out of scope: email verification, password reset, social login, React/Next.js, i18n.

## Stack

Python 3.12, uv (`pyproject.toml` + `uv.lock`), Django 5.2 LTS, DRF, drf-spectacular,
`captchakit[django,redis]`, redis, gunicorn (2 workers), whitenoise, dj-database-url
(default SQLite; Render free Postgres expires after 30 days, so it is not used), ruff, mypy +
django-stubs + djangorestframework-stubs, pytest, pytest-django, pytest-cov.
Local: Docker Compose with `web` + `redis`.

Layout: `config/` (settings, urls, wsgi, asgi), `captcha_demo/` (`captcha.py`: the single
manager — `RedisStorage` when `REDIS_URL` is set, else `MemoryStorage`; `drf.py`; `views.py`),
`accounts/` (forms, views, api, urls, templates), `templates/base.html`, `tests/`,
`docs/` (ADR-001: why Redis), `Dockerfile`, `docker-compose.yml`, `render.yaml`,
`.env.example`, `README.md`.

Environment: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `REDIS_URL`, `CAPTCHA_TTL=180`, `CAPTCHA_MAX_ATTEMPTS=3`;
`TextChallengeFactory(length=5)`.

## Tests

Tests run without Redis (MemoryStorage); the Redis integration test is marked `redis` and
runs in CI against a Redis service container. Required scenarios: register and login with
correct / wrong / empty captcha; two form instances show different ids and both work after
one succeeds; API 201/400/404/410/429 (fake clock for expiry); a challenge cannot be reused;
rate limit 429; image 200 `image/png` and unknown id 404; `/healthz` 200.
`python manage.py check --deploy` must be warning-free with production settings.

## Render

`render.yaml` Blueprint (verify field names against render.com/docs/blueprint-spec).
Web service: `runtime: python`, `plan: free`, build installs with uv + `collectstatic`, start
runs `migrate` + `gunicorn config.wsgi --workers 2`, `healthCheckPath: /healthz`.
Key Value: `plan: free`, empty `ipAllowList` (no external access). `REDIS_URL` via
`fromService` → the Key Value internal `connectionString`; `DJANGO_SECRET_KEY` via
`generateValue`. README must note: free web service sleeps after 15 min (≈1 min wake-up),
Key Value is in-memory only (wiped on restart), disk is ephemeral (SQLite may reset).
The owner connects the Render account; give them click-by-click steps.

## Sessions

1. captchakit bug (test + fix + 1.0.2 prep) and demo skeleton (uv, Django, settings,
   Docker Compose, CI)
2. HTML register / login / logout / profile pages and form tests
3. DRF endpoints, serializer layer, rate limit, OpenAPI and API tests
4. Redis storage, `/healthz`, security settings, `render.yaml`, deploy instructions
5. README, screenshot, mermaid architecture diagram, ADR-001, demo link in captchakit docs

## Status

- **Session 1 — in progress.**
  - captchakit: `CaptchaField` shared one challenge across all instances of a form class.
    Fixed in akerem16/captchakit#1 (merged, `40ca284`): challenge issued in `__deepcopy__`,
    lazily in `get_bound_field` for runtime fields, `bound_data` returns the fresh challenge.
    Also allowed Pillow 13 and refreshed vulnerable locked deps (pip-audit). Version 1.0.2
    prepared; **owner tags `v1.0.2` to publish to PyPI**. Until then the demo pins captchakit
    to the git commit via `[tool.uv.sources]`.
  - Demo skeleton: see the session 1 PR.
- Open question: does `redis.asyncio.Redis` break under `async_to_sync` across event loops?
  Checked by the `redis`-marked test in CI (no Redis on the dev machine).
