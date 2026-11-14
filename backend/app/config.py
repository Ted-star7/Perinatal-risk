
"""Backend settings, read from the environment (see .env.example)."""

from __future__ import annotations

import os


def _normalize_db_url(url: str) -> str:
    """Make a Postgres URL use the psycopg driver.

    Render's managed Postgres hands out URLs like ``postgres://`` or
    ``postgresql://``; SQLAlchemy needs the explicit ``postgresql+psycopg://``
    driver. Local SQLite / already-qualified URLs are left untouched.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings:
    app_db_url: str = _normalize_db_url(
        os.getenv(
            "APP_DB_URL",
            "postgresql+psycopg://app:app@localhost:5432/perinatal_app",
        )
    )

    # Signing secret for auth tokens. Override in production.
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    token_ttl_hours: int = 12

    # Where the Angular dev server runs (for CORS).
    frontend_origin: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:4200",
    )

    # Optional shared key for POST /metrics.
    metrics_key: str = os.getenv("METRICS_KEY", "")

    # Optional remote source for shared metrics in local development.
    # If unset, the API reads metrics from its own database.
    metrics_source_url: str = os.getenv("METRICS_SOURCE_URL", "")


settings = Settings()
