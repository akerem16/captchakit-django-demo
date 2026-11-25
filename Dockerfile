FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.9

WORKDIR /app

# Dependencies first, so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY . .
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi --workers 2 --bind 0.0.0.0:${PORT:-8000}"]
