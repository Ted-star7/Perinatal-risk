"""Save a model's results into the app DB.

Call this at the end of a modeling notebook so the eval dashboard can read the
result. One row per (cohort, algorithm) — re-running replaces it (upsert), so
the table always holds the current numbers.

    from db.metrics import save_metrics
    save_metrics("perinatal", "gradient_boosting",
                 pr_auc=0.41, roc_auc=0.78, recall_at_flag=0.33,
                 beats_checklist=True, test_events=6189)
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text

APP_DB_URL = os.getenv(
    "APP_DB_URL",
    "postgresql+psycopg://app:app@localhost:5432/perinatal_app",
)


def save_metrics(
    cohort: str,
    algorithm: str,
    *,
    pr_auc: float,
    roc_auc: float,
    recall_at_flag: float,
    beats_checklist: bool,
    test_events: int,
    is_best: bool = False,
) -> None:
    """Upsert one model's metrics into model_metrics."""
    engine = create_engine(APP_DB_URL)
    stmt = text(
        """
        INSERT INTO model_metrics
            (cohort, algorithm, pr_auc, roc_auc, recall_at_flag,
             beats_checklist, is_best, test_events, updated_at)
        VALUES
            (:cohort, :algorithm, :pr_auc, :roc_auc, :recall_at_flag,
             :beats_checklist, :is_best, :test_events, now())
        ON CONFLICT (cohort, algorithm) DO UPDATE SET
            pr_auc          = EXCLUDED.pr_auc,
            roc_auc         = EXCLUDED.roc_auc,
            recall_at_flag  = EXCLUDED.recall_at_flag,
            beats_checklist = EXCLUDED.beats_checklist,
            is_best         = EXCLUDED.is_best,
            test_events     = EXCLUDED.test_events,
            updated_at      = now()
        """
    )
    with engine.begin() as con:
        con.execute(
            stmt,
            {
                "cohort": cohort,
                "algorithm": algorithm,
                "pr_auc": pr_auc,
                "roc_auc": roc_auc,
                "recall_at_flag": recall_at_flag,
                "beats_checklist": beats_checklist,
                "is_best": is_best,
                "test_events": test_events,
            },
        )
    print(f"saved metrics for {cohort} / {algorithm}")
