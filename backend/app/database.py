"""Database sessions and idempotent, serialized application migrations."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

connect_args = {"check_same_thread": False} if settings.app_db_url.startswith("sqlite") else {}
engine = create_engine(settings.app_db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

METRICS_DDL = """
CREATE TABLE IF NOT EXISTS model_metrics (
 cohort VARCHAR(32), algorithm VARCHAR(32), pr_auc DOUBLE PRECISION,
 roc_auc DOUBLE PRECISION, recall_at_flag DOUBLE PRECISION, beats_checklist BOOLEAN,
 is_best BOOLEAN DEFAULT FALSE, test_events INTEGER,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (cohort, algorithm)
);
CREATE TABLE IF NOT EXISTS feature_importance (
 cohort VARCHAR(32), feature VARCHAR(64), importance DOUBLE PRECISION,
 PRIMARY KEY (cohort, feature)
);
"""


def init_db() -> None:
    with engine.begin() as con:
        if engine.dialect.name == "postgresql":
            con.execute(text("SELECT pg_advisory_xact_lock(78263410)"))
        Base.metadata.create_all(con)
        con.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        if not con.scalar(text("SELECT version FROM schema_migrations WHERE version = 3")):
            changes = {
                "predictions": {"assessment": "JSON", "request_id": "VARCHAR(36)"},
                "clinics": {"country": "VARCHAR(32) NOT NULL DEFAULT 'Kenya'"},
                "doctors": {
                    "token_version": "INTEGER NOT NULL DEFAULT 0",
                    "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
                    "is_owner": "BOOLEAN NOT NULL DEFAULT TRUE",
                },
            }
            for table, columns in changes.items():
                existing = {column["name"] for column in inspect(con).get_columns(table)}
                for name, definition in columns.items():
                    if name not in existing:
                        con.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
            con.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_prediction_request "
                    "ON predictions (clinic_id, request_id)"
                )
            )
            con.execute(text("INSERT INTO schema_migrations(version) VALUES (3)"))
        if not con.scalar(text("SELECT version FROM schema_migrations WHERE version = 4")):
            if engine.dialect.name == "postgresql":
                con.execute(text("ALTER TABLE clinics ALTER COLUMN country TYPE VARCHAR(80)"))
            con.execute(text("INSERT INTO schema_migrations(version) VALUES (4)"))
        for statement in filter(str.strip, METRICS_DDL.split(";")):
            con.execute(text(statement))
        # Historical duplicate flags are resolved deterministically before the unique index.
        con.execute(
            text("""UPDATE model_metrics SET is_best = FALSE WHERE is_best = TRUE AND EXISTS (
            SELECT 1 FROM model_metrics other WHERE other.cohort = model_metrics.cohort
            AND other.is_best = TRUE AND (other.updated_at > model_metrics.updated_at OR
            (other.updated_at = model_metrics.updated_at
             AND other.algorithm > model_metrics.algorithm)))""")
        )
        con.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_best_model_per_cohort "
                "ON model_metrics(cohort) WHERE is_best = TRUE"
            )
        )

        from app.evaluation import install_approved_evaluation

        install_approved_evaluation(con)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
