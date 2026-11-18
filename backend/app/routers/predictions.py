"""Assess, pin the reviewed result, and retrieve clinic-scoped patient records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from jwt import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_doctor
from app.config import settings
from app.database import get_db
from app.models import BirthOutcome, Prediction
from app.schemas import (
    AssessmentResult,
    BirthOutcomeIn,
    BirthOutcomeResponse,
    Driver,
    PredictRequest,
    PredictResponse,
)
from app.scoring import AssessmentInputError, ModelUnavailable, score

router = APIRouter(tags=["predictions"])


def _inputs(body: PredictRequest) -> dict:
    values = body.model_dump(mode="json", exclude={"assessment_token"})
    if values["age_at_start"] is None:
        values.pop("age_at_start")
    return values


def _input_hash(body: PredictRequest) -> str:
    return hashlib.sha256(json.dumps(_inputs(body), sort_keys=True).encode()).hexdigest()


def _existing(db: Session, clinic_id: int, request_id: str | None):
    if not request_id:
        return None
    return db.scalar(
        select(Prediction).where(
            Prediction.clinic_id == clinic_id, Prediction.request_id == request_id
        )
    )


def _to_response(prediction: Prediction, outcomes=None) -> PredictResponse:
    created = prediction.created_at.replace(tzinfo=timezone.utc)
    return PredictResponse(
        id=prediction.id,
        risk=prediction.risk,
        risk_band=prediction.risk_band,
        top_drivers=[Driver(**driver) for driver in prediction.top_drivers],
        recommendation=prediction.recommendation,
        created_at=created,
        patient_ref=prediction.patient_ref,
        assessment=prediction.assessment,
        outcomes=outcomes or [],
        multiple=bool(prediction.inputs.get("multiple")),
    )


def _retry_response(prediction: Prediction, body: PredictRequest) -> PredictResponse:
    if prediction.inputs != _inputs(body):
        raise HTTPException(
            409, "This save request was already used for different patient details."
        )
    return _to_response(prediction)


@router.post("/assess", response_model=AssessmentResult)
def assess(body: PredictRequest, who: dict = Depends(current_doctor)) -> AssessmentResult:
    try:
        result = score(body)
    except AssessmentInputError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    snapshot = result.model_dump(mode="json", exclude={"assessment_token"})
    token = jwt.encode(
        {
            "purpose": "assessment",
            "sub": str(who["doctor_id"]),
            "clinic": who["clinic_id"],
            "inputs": _input_hash(body),
            "result": snapshot,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return result.model_copy(update={"assessment_token": token})


@router.post("/predict", response_model=PredictResponse)
def predict(
    body: PredictRequest, db: Session = Depends(get_db), who: dict = Depends(current_doctor)
) -> PredictResponse:
    request_id = str(body.request_id) if body.request_id else None
    existing = _existing(db, who["clinic_id"], request_id)
    if existing:
        return _retry_response(existing, body)
    if body.assessment_token:
        try:
            payload = jwt.decode(
                body.assessment_token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"require": ["exp"]},
            )
            if (
                payload.get("purpose") != "assessment"
                or payload["sub"] != str(who["doctor_id"])
                or payload["clinic"] != who["clinic_id"]
                or payload["inputs"] != _input_hash(body)
            ):
                raise ValueError("Assessment details changed")
            result = AssessmentResult.model_validate(payload["result"])
        except (JWTError, ValueError, KeyError) as exc:
            raise HTTPException(409, "Assess these details again before saving.") from exc
    else:
        # Legacy API clients can still calculate and save in one request.
        try:
            result = score(body)
        except AssessmentInputError as exc:
            raise HTTPException(422, str(exc)) from exc
        except ModelUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
    prediction = Prediction(
        clinic_id=who["clinic_id"],
        doctor_id=who["doctor_id"],
        patient_ref=body.patient_ref,
        inputs=_inputs(body),
        risk=result.perinatal.score,
        risk_band="unclassified",
        top_drivers=[],
        recommendation=result.recommendation,
        assessment=result.model_dump(mode="json", exclude={"assessment_token"}),
        request_id=request_id,
    )
    db.add(prediction)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _existing(db, who["clinic_id"], request_id)
        if existing is None:
            raise
        return _retry_response(existing, body)
    return _to_response(prediction)


@router.get("/history", response_model=list[PredictResponse])
def history(
    db: Session = Depends(get_db),
    who: dict = Depends(current_doctor),
    search: str = Query(default="", max_length=60),
    limit: int = Query(default=25, ge=1, le=100),
    before: int | None = Query(default=None, ge=1),
) -> list[PredictResponse]:
    query = select(Prediction).where(Prediction.clinic_id == who["clinic_id"])
    if search.strip():
        query = query.where(Prediction.patient_ref.ilike(f"%{search.strip()}%"))
    if before:
        query = query.where(Prediction.id < before)
    rows = db.scalars(query.order_by(Prediction.id.desc()).limit(limit)).all()
    ids = [row.id for row in rows]
    outcomes = (
        db.scalars(
            select(BirthOutcome)
            .where(BirthOutcome.prediction_id.in_(ids))
            .order_by(BirthOutcome.version.desc())
        ).all()
        if ids
        else []
    )
    latest = {}
    for outcome in outcomes:
        latest.setdefault((outcome.prediction_id, outcome.baby_number), _outcome_response(outcome))
    return [
        _to_response(row, [value for (pid, _), value in latest.items() if pid == row.id])
        for row in rows
    ]


def _outcome_response(row: BirthOutcome) -> BirthOutcomeResponse:
    return BirthOutcomeResponse(
        **row.details,
        expected_version=row.version,
        version=row.version,
        doctor_id=row.doctor_id,
        recorded_at=row.recorded_at.replace(tzinfo=timezone.utc),
    )


def _clinic_prediction(db, who, prediction_id):
    row = db.scalar(
        select(Prediction).where(
            Prediction.id == prediction_id, Prediction.clinic_id == who["clinic_id"]
        )
    )
    if row is None:
        raise HTTPException(404, "Assessment not found.")
    return row


@router.get("/predictions/{prediction_id}/outcomes", response_model=list[BirthOutcomeResponse])
def outcome_history(
    prediction_id: int, db: Session = Depends(get_db), who: dict = Depends(current_doctor)
):
    _clinic_prediction(db, who, prediction_id)
    rows = db.scalars(
        select(BirthOutcome)
        .where(BirthOutcome.prediction_id == prediction_id)
        .order_by(BirthOutcome.recorded_at.desc(), BirthOutcome.id.desc())
    ).all()
    return [_outcome_response(row) for row in rows]


@router.post("/predictions/{prediction_id}/outcomes", response_model=BirthOutcomeResponse)
def record_outcome(
    prediction_id: int,
    body: BirthOutcomeIn,
    db: Session = Depends(get_db),
    who: dict = Depends(current_doctor),
):
    prediction = _clinic_prediction(db, who, prediction_id)
    if body.baby_number > 1 and not prediction.inputs.get("multiple"):
        raise HTTPException(422, "This assessment records a single baby.")
    latest = db.scalar(
        select(BirthOutcome)
        .where(
            BirthOutcome.prediction_id == prediction_id,
            BirthOutcome.baby_number == body.baby_number,
        )
        .order_by(BirthOutcome.version.desc())
        .limit(1)
    )
    version = latest.version if latest else 0
    if body.expected_version != version:
        raise HTTPException(409, "This follow-up changed. Reload the record before editing.")
    row = BirthOutcome(
        prediction_id=prediction_id,
        baby_number=body.baby_number,
        version=version + 1,
        doctor_id=who["doctor_id"],
        details=body.model_dump(mode="json", exclude={"expected_version"}),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This follow-up changed. Reload the record before editing."
        ) from exc
    return _outcome_response(row)
