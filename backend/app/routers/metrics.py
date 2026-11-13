"""Shared model-metrics endpoint.

Every modeling notebook posts its result here (via db.metrics.save_metrics), so
all nine models' numbers collect in the one hosted database and the team can
compare them in one place — GET /metrics, or the eval dashboard.

One row per (cohort, algorithm); re-posting replaces it (upsert).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import MetricsIn

router = APIRouter(tags=["metrics"])

_UPSERT = text(
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


@router.post("/metrics")
def save_metric(
    body: MetricsIn,
    x_metrics_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    # Optional shared key: if METRICS_KEY is set on the server, callers must match
    # it. Left unset (default) the endpoint is open — fine for the capstone demo.
    if settings.metrics_key and x_metrics_key != settings.metrics_key:
        raise HTTPException(status_code=401, detail="bad or missing X-Metrics-Key")
    db.execute(_UPSERT, body.model_dump())
    db.commit()
    return {"saved": f"{body.cohort}/{body.algorithm}"}


@router.get("/metrics")
def list_metrics(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        text(
            "SELECT cohort, algorithm, pr_auc, roc_auc, recall_at_flag, "
            "beats_checklist, is_best, test_events, updated_at "
            "FROM model_metrics ORDER BY cohort, algorithm"
        )
    ).mappings().all()
    return [dict(r) for r in rows]
