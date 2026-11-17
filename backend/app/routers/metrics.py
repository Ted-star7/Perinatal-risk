"""Shared model-metrics endpoint.

Modeling notebooks submit their results through db.metrics.save_metrics.
The results are stored centrally so the team can compare model performance
through GET /metrics and the evaluation dashboard.

One row per (cohort, algorithm). Re-submitting a result updates that row.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import _bearer, current_doctor, require_metrics_access
from app.config import settings
from app.database import get_db
from app.schemas import MetricsIn

router = APIRouter(tags=["metrics"])


@router.get("/evaluation-metrics")
def evaluation_metrics(
    who: dict = Depends(current_doctor), db: Session = Depends(get_db)
) -> list[dict]:
    """Read the approved research comparison persisted in this database."""
    from app.evaluation import approved_evaluation

    return approved_evaluation(db)


def read_metrics_access(
    x_metrics_key: str | None = Header(default=None),
    creds=Depends(_bearer),
    db: Session = Depends(get_db),
) -> None:
    if x_metrics_key:
        require_metrics_access(x_metrics_key)
    else:
        current_doctor(creds, db)


_UPSERT = text(
    """
    INSERT INTO model_metrics
        (cohort, algorithm, pr_auc, roc_auc, recall_at_flag,
         beats_checklist, is_best, test_events, updated_at)
    VALUES
        (:cohort, :algorithm, :pr_auc, :roc_auc, :recall_at_flag,
         :beats_checklist, :is_best, :test_events, CURRENT_TIMESTAMP)
    ON CONFLICT (cohort, algorithm) DO UPDATE SET
        pr_auc          = EXCLUDED.pr_auc,
        roc_auc         = EXCLUDED.roc_auc,
        recall_at_flag  = EXCLUDED.recall_at_flag,
        beats_checklist = EXCLUDED.beats_checklist,
        is_best         = EXCLUDED.is_best,
        test_events     = EXCLUDED.test_events,
        updated_at      = CURRENT_TIMESTAMP
    """
)


@router.post("/metrics")
def save_metric(
    body: MetricsIn,
    x_metrics_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """Save or update a model's evaluation results."""

    require_metrics_access(x_metrics_key)
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:cohort))"), {"cohort": body.cohort})
    if body.is_best:
        db.execute(
            text("UPDATE model_metrics SET is_best = FALSE WHERE cohort = :cohort"),
            {"cohort": body.cohort},
        )
    try:
        db.execute(_UPSERT, body.model_dump())
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "Another model update is in progress. Retry the publication."
        ) from exc

    return {"saved": f"{body.cohort}/{body.algorithm}"}


@router.get("/metrics")
def list_metrics(
    db: Session = Depends(get_db), access: None = Depends(read_metrics_access)
) -> list[dict]:
    """Retrieve shared model metrics or read from the local database."""

    # In local development, retrieve the shared metrics from the hosted API.
    if settings.metrics_source_url:
        try:
            with urlopen(
                Request(
                    settings.metrics_source_url, headers={"X-Metrics-Key": settings.metrics_key}
                ),
                timeout=20,
            ) as response:
                return json.loads(response.read().decode("utf-8"))

        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not retrieve shared model metrics: {exc}",
            ) from exc

    # Otherwise, retrieve metrics from this API's own database.
    rows = (
        db.execute(
            text(
                "SELECT cohort, algorithm, pr_auc, roc_auc, recall_at_flag, "
                "beats_checklist, is_best, test_events, updated_at "
                "FROM model_metrics ORDER BY cohort, algorithm"
            )
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in rows]


@router.get("/model-releases")
def model_releases(who: dict = Depends(current_doctor)) -> list[dict]:
    from app.scoring import MODEL_PATHS, get_model

    releases = []
    for cohort in MODEL_PATHS:
        try:
            model, _, identifier = get_model(cohort)
            releases.append(
                dict(
                    model.release_metadata_,
                    model_id=identifier,
                    available=True,
                    serving=cohort in ["perinatal", "lbw"],
                )
            )
        except Exception:
            releases.append({"cohort": cohort, "available": False})
    return releases
