"""Assess, pin the reviewed result, and retrieve clinic-scoped patient records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from jwt import PyJWTError as JWTError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_doctor
from app.config import settings
from app.database import get_db
from app.models import BirthOutcome, Prediction
from app.schemas import (
    AssessmentResult,
    BabyCountUpdate,
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
        multiple=(
            prediction.baby_count > 1
            if prediction.baby_count
            else bool(prediction.inputs.get("multiple"))
        ),
        baby_count=prediction.baby_count,
        pregnancy_id=prediction.pregnancy_id or prediction.id,
        birth_spacing_months=prediction.inputs.get("birth_spacing_months"),
    )


def _retry_response(prediction: Prediction, body: PredictRequest) -> PredictResponse:
    if prediction.inputs != _inputs(body):
        raise HTTPException(
            409, "This save request was already used for different patient details."
        )
    return _to_response(prediction)


@router.post("/assess", response_model=AssessmentResult)
def assess(
    body: PredictRequest, db: Session = Depends(get_db), who: dict = Depends(current_doctor)
) -> AssessmentResult:
    if body.pregnancy_id:
        _continuing_pregnancy(db, who, body)
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
    parent = _continuing_pregnancy(db, who, body) if body.pregnancy_id else None
    if parent:
        _validate_count(db, parent, body.baby_count)
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
        patient_ref=parent.patient_ref if parent else body.patient_ref,
        baby_count=body.baby_count,
        pregnancy_id=parent.id if parent else None,
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
        db.flush()
        prediction.pregnancy_id = parent.id if parent else prediction.id
        if parent:
            db.execute(
                update(Prediction)
                .where(
                    Prediction.clinic_id == who["clinic_id"], Prediction.pregnancy_id == parent.id
                )
                .values(baby_count=body.baby_count)
            )
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
    return _responses(db, rows)


def _responses(db, rows):
    ids = {row.pregnancy_id or row.id for row in rows}
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
        _to_response(
            row,
            [value for (pid, _), value in latest.items() if pid == (row.pregnancy_id or row.id)],
        )
        for row in rows
    ]


def _continuing_pregnancy(db, who, body):
    parent = _clinic_prediction(db, who, body.pregnancy_id)
    parent = _clinic_prediction(db, who, parent.pregnancy_id or parent.id, lock=True)
    if (parent.patient_ref or "").strip().casefold() != body.patient_ref.strip().casefold():
        raise HTTPException(422, "This pregnancy belongs to a different patient reference.")
    return parent


@router.get("/patients/lookup")
def patient_lookup(
    reference: str = Query(min_length=1, max_length=60),
    db: Session = Depends(get_db),
    who: dict = Depends(current_doctor),
):
    condition = (
        Prediction.clinic_id == who["clinic_id"],
        func.lower(func.trim(Prediction.patient_ref)) == reference.strip().lower(),
    )
    latest = db.scalar(select(Prediction).where(*condition).order_by(Prediction.id.desc()).limit(1))
    if latest is None:
        return {"found": False, "assessment_count": 0, "latest": None, "inputs": None}
    count = db.scalar(select(func.count()).select_from(Prediction).where(*condition))
    return {
        "found": True,
        "assessment_count": count,
        "latest": _responses(db, [latest])[0],
        "inputs": latest.inputs,
    }


@router.get("/outcome-summary")
def outcome_summary(db: Session = Depends(get_db), who: dict = Depends(current_doctor)):
    rows = db.scalars(
        select(Prediction).where(Prediction.clinic_id == who["clinic_id"]).order_by(Prediction.id)
    ).all()
    pregnancies = {}
    synthetic = {row.pregnancy_id or row.id for row in rows if row.inputs.get("synthetic")}
    for row in rows:
        if (row.pregnancy_id or row.id) not in synthetic:
            pregnancies[row.pregnancy_id or row.id] = row
    ids = list(pregnancies)
    latest = {}
    if ids:
        for outcome in db.scalars(
            select(BirthOutcome)
            .where(BirthOutcome.prediction_id.in_(ids))
            .order_by(BirthOutcome.version.desc())
        ):
            latest.setdefault((outcome.prediction_id, outcome.baby_number), outcome.details)
    counts = {"pending": 0, "alive": 0, "stillbirth": 0, "died": 0}
    weights = {"below_2500": 0, "at_least_2500": 0, "unknown": 0}
    unknown_counts = 0
    for pregnancy_id, row in pregnancies.items():
        if row.baby_count is None:
            unknown_counts += 1
            continue
        for number in range(1, row.baby_count + 1):
            details = latest.get((pregnancy_id, number), {})
            status = details.get("status", "unknown")
            counts["pending" if status == "unknown" else status] += 1
            weight = details.get("birth_weight_grams")
            weights[
                "unknown" if weight is None else "below_2500" if weight < 2500 else "at_least_2500"
            ] += 1
    return {
        "pregnancies": len(pregnancies),
        "babies": sum(counts.values()),
        "pregnancies_without_baby_count": unknown_counts,
        "survival": counts,
        "birth_weight": weights,
        "synthetic_excluded": True,
    }


def _validate_count(db, prediction, count):
    highest = (
        db.scalar(
            select(func.max(BirthOutcome.baby_number)).where(
                BirthOutcome.prediction_id == prediction.id
            )
        )
        or 0
    )
    if count < highest:
        raise HTTPException(422, "Baby count cannot hide an existing baby's follow-up.")


@router.patch("/predictions/{prediction_id}/baby-count", response_model=PredictResponse)
def confirm_baby_count(
    prediction_id: int,
    body: BabyCountUpdate,
    db: Session = Depends(get_db),
    who: dict = Depends(current_doctor),
):
    prediction = _clinic_prediction(db, who, prediction_id)
    root = _clinic_prediction(db, who, prediction.pregnancy_id or prediction.id, lock=True)
    if root.baby_count != body.expected_count:
        raise HTTPException(409, "Baby count changed. Reload the record before editing.")
    _validate_count(db, root, body.baby_count)
    db.execute(
        update(Prediction)
        .where(Prediction.clinic_id == who["clinic_id"], Prediction.pregnancy_id == root.id)
        .values(baby_count=body.baby_count)
    )
    root.baby_count = body.baby_count
    db.commit()
    return _responses(db, [prediction])[0]


def _outcome_response(row: BirthOutcome) -> BirthOutcomeResponse:
    return BirthOutcomeResponse(
        **row.details,
        expected_version=row.version,
        version=row.version,
        doctor_id=row.doctor_id,
        recorded_at=row.recorded_at.replace(tzinfo=timezone.utc),
    )


def _clinic_prediction(db, who, prediction_id, lock=False):
    query = select(Prediction).where(
        Prediction.id == prediction_id, Prediction.clinic_id == who["clinic_id"]
    )
    row = db.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )
    if row is None:
        raise HTTPException(404, "Assessment not found.")
    return row


@router.get("/predictions/{prediction_id}/outcomes", response_model=list[BirthOutcomeResponse])
def outcome_history(
    prediction_id: int, db: Session = Depends(get_db), who: dict = Depends(current_doctor)
):
    prediction = _clinic_prediction(db, who, prediction_id)
    prediction_id = prediction.pregnancy_id or prediction.id
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
    prediction = _clinic_prediction(db, who, prediction.pregnancy_id or prediction.id, lock=True)
    prediction_id = prediction.id
    if prediction.baby_count is None:
        raise HTTPException(422, "Confirm the saved number of babies before adding follow-up.")
    if body.baby_number > prediction.baby_count:
        raise HTTPException(422, "Baby number exceeds the saved number of babies.")
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
