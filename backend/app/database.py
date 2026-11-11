"""SQLAlchemy engine, session, and table creation."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

connect_args = (
    {"check_same_thread": False} if settings.app_db_url.startswith("sqlite") else {}
)
engine = create_engine(settings.app_db_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

# Tables the modeling side writes and the eval dashboard reads. In local Docker
# these come from db/app/001_schema.sql; in production (Render managed Postgres,
# no init-sql hook) the backend creates them here. All IF NOT EXISTS, so safe.
_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS model_metrics (
    cohort          VARCHAR(32),
    algorithm       VARCHAR(32),
    pr_auc          DOUBLE PRECISION,
    roc_auc         DOUBLE PRECISION,
    recall_at_flag  DOUBLE PRECISION,
    beats_checklist BOOLEAN,
    is_best         BOOLEAN DEFAULT FALSE,
    test_events     INTEGER,
    updated_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (cohort, algorithm)
);
CREATE TABLE IF NOT EXISTS feature_importance (
    cohort          VARCHAR(32),
    feature         VARCHAR(64),
    importance      DOUBLE PRECISION,
    PRIMARY KEY (cohort, feature)
);
"""


def init_db() -> None:
    Base.metadata.create_all(engine)  # clinics, doctors, predictions (ORM)
    if not settings.app_db_url.startswith("sqlite"):
        with engine.begin() as con:
            for stmt in filter(str.strip, _METRICS_DDL.split(";")):
                con.execute(text(stmt))


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
