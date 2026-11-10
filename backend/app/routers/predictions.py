"""Make an assessment (saved against the signed-in doctor's clinic) and list a
clinic's history."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_doctor
from app.database import get_db
from app.models import Prediction
from app.schemas import Driver, PredictRequest, PredictResponse
from app.scoring import score

router = APIRouter(tags=["predictions"])


def _to_response(p: Prediction) -> PredictResponse:
    return PredictResponse(
        id=p.id,
        risk=p.risk,
        risk_band=p.risk_band,
        top_drivers=[Driver(**d) for d in p.top_drivers],
        recommendation=p.recommendation,
        created_at=p.created_at,
        patient_ref=p.patient_ref,
    )


@router.post("/predict", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    db: Session = Depends(get_db),
    who: dict = Depends(current_doctor),
) -> PredictResponse:
    risk, band, drivers, recommendation = score(body)
    pred = Prediction(
        clinic_id=who["clinic_id"],
        doctor_id=who["doctor_id"],
        patient_ref=body.patient_ref,
        inputs=body.model_dump(),
        risk=risk,
        risk_band=band,
        top_drivers=drivers,
        recommendation=recommendation,
    )
    db.add(pred)
    db.commit()
    return _to_response(pred)


@router.get("/history", response_model=list[PredictResponse])
def history(
    db: Session = Depends(get_db), who: dict = Depends(current_doctor)
) -> list[PredictResponse]:
    """Every assessment made at the signed-in doctor's clinic, newest first."""
    rows = db.scalars(
        select(Prediction)
        .where(Prediction.clinic_id == who["clinic_id"])
        .order_by(Prediction.created_at.desc())
    ).all()
    return [_to_response(p) for p in rows]
