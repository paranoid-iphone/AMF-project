FROM ghcr.io/astral-sh/uv:0.8.11 AS uv
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-groups --no-install-project

COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]