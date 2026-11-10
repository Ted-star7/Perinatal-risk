"""Backend settings, read from the environment (see .env.example)."""

from __future__ import annotations

import os


class Settings:
    app_db_url: str = os.getenv(
        "APP_DB_URL", "postgresql+psycopg://app:app@localhost:5432/perinatal_app"
    )
    # Signing secret for auth tokens. Override in production.
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    token_ttl_hours: int = 12
    # Where the Angular dev server runs (for CORS).
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:4200")


settings = Settings()
