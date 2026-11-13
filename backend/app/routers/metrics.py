
"""Shared model-metrics endpoint.

Modeling notebooks submit their results through db.metrics.save_metrics.
The results are stored centrally so the team can compare model performance
through GET /metrics and the evaluation dashboard.

One row per (cohort, algorithm). Re-submitting a result updates that row.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

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
    """Save or update a model's evaluation results."""

    if settings.metrics_key and x_metrics_key != settings.metrics_key:
        raise HTTPException(
            status_code=401,
            detail="Bad or missing X-Metrics-Key",
        )

    db.execute(_UPSERT, body.model_dump())
    db.commit()

    return {"saved": f"{body.cohort}/{body.algorithm}"}


@router.get("/metrics")
def list_metrics(db: Session = Depends(get_db)) -> list[dict]:
    """Retrieve shared model metrics or read from the local database."""

    # In local development, retrieve the shared metrics from the hosted API.
    if settings.metrics_source_url:
        try:
            with urlopen(settings.metrics_source_url, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not retrieve shared model metrics: {exc}",
            ) from exc

    # Otherwise, retrieve metrics from this API's own database.
    rows = db.execute(
        text(
            "SELECT cohort, algorithm, pr_auc, roc_auc, recall_at_flag, "
            "beats_checklist, is_best, test_events, updated_at "
            "FROM model_metrics ORDER BY cohort, algorithm"
        )
    ).mappings().all()

    return [dict(row) for row in rows]
