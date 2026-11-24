# ADR-001: Store captchas in Redis

- **Status:** accepted
- **Date:** 2026-11-25

## Context

A captcha is issued by one HTTP request and verified by a later one. In between, the server
has to remember the challenge: its solution, expiry time and number of attempts.

In production the app runs under gunicorn with **2 worker processes**. Render does not
guarantee which worker gets the next request. The free web service also restarts often,
since it sleeps after 15 minutes without traffic.

The API rate limit (`POST /api/captcha/`, per client IP) has the same problem: a counter
kept in one worker cannot see the requests the other worker handled.

## Options

| Option | Shared between workers | Expiry | Cost on Render free tier | Notes |
|---|---|---|---|---|
| `MemoryStorage` (per process) | no | manual cleanup | none | A captcha issued by worker A is "not found" in worker B. |
| Database table (SQLite/Postgres) | yes (Postgres) | needs a cleanup job | free Postgres expires after 30 days; SQLite is per-disk and reset on deploy | Writes on every page view; captchakit has `PostgresStorage`. |
| **Redis (Render Key Value)** | **yes** | **native key TTL** | **free plan** (25 MB, in-memory) | captchakit has `RedisStorage` and `RedisTokenBucket`. |

## Decision

Use Redis through captchakit's `RedisStorage` and `RedisTokenBucket` when `REDIS_URL` is
set, and `MemoryStorage` / `TokenBucketRateLimiter` otherwise (local runs, tests).

- Every worker sees the same challenges and the same rate-limit buckets.
- Redis deletes expired challenges by itself (`SET ... EX`), so no cleanup job is needed.
- The rate limiter runs as a Lua script inside Redis, so it is atomic across workers.
- The free Key Value plan loses its data on restart. That is acceptable here: a captcha
  lives for 3 minutes, and a lost one only means the user gets a new image.

## Consequences

- **Event loops:** captchakit's Redis client is asyncio-based, while Django under WSGI is
  sync. Every `async_to_sync` call runs in a new, short-lived event loop, and a
  `redis.asyncio` connection cannot be reused from another loop (`RuntimeError: Event loop
  is closed` on the second call, reproduced in CI). `captcha_demo/loop_bridge.py` runs all
  Redis calls on one long-lived background loop per worker.
- **Health check:** `/healthz` pings Redis, so Render restarts the service if Redis is
  unreachable.
- **No internet exposure:** the instance has an empty `ipAllowList`, so only services in the
  same Render region can connect.
- **Single point of failure:** if Redis is down, captchas cannot be issued or verified.
  For a demo that is acceptable; a production setup would use a paid, persistent instance.
