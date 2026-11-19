"""Database sessions and idempotent, serialized application migrations."""

from __future__ import annotations

import json
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
        if not con.scalar(text("SELECT version FROM schema_migrations WHERE version = 5")):
            # Base.metadata.create_all creates the additive, append-only birth_outcomes table.
            con.execute(text("INSERT INTO schema_migrations(version) VALUES (5)"))
        if not con.scalar(text("SELECT version FROM schema_migrations WHERE version = 6")):
            existing = {column["name"] for column in inspect(con).get_columns("predictions")}
            for name in ("baby_count", "pregnancy_id"):
                if name not in existing:
                    con.execute(text(f"ALTER TABLE predictions ADD COLUMN {name} INTEGER"))
            con.execute(text("UPDATE predictions SET pregnancy_id = id WHERE pregnancy_id IS NULL"))
            if "inputs" in existing:
                for row in con.execute(text("SELECT id, inputs FROM predictions")):
                    inputs = row.inputs
                    if isinstance(inputs, str):
                        inputs = json.loads(inputs)
                    inputs = inputs or {}
                    count = inputs.get("baby_count")
                    if count is None and not inputs.get("multiple"):
                        count = 1
                    if isinstance(count, int) and 1 <= count <= 10:
                        con.execute(
                            text("UPDATE predictions SET baby_count = :count WHERE id = :id"),
                            {"count": count, "id": row.id},
                        )
            con.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_predictions_pregnancy_id "
                    "ON predictions(pregnancy_id)"
                )
            )
            if "patient_ref" in existing:
                con.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_predictions_patient_reference "
                        "ON predictions(clinic_id, lower(trim(patient_ref)))"
                    )
                )
            con.execute(text("INSERT INTO schema_migrations(version) VALUES (6)"))
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
