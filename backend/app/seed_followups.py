"""Explicit, idempotent synthetic follow-up examples for a development clinic."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import BirthOutcome, Doctor, Prediction
from app.schemas import BirthOutcomeIn


def seed_followups(doctor_id: int) -> int:
    if settings.app_env != "development":
        raise ValueError("Synthetic follow-ups can only be seeded in development.")
    init_db()
    count = 0
    with SessionLocal() as db:
        doctor = db.get(Doctor, doctor_id)
        if doctor is None or not doctor.is_active:
            raise ValueError("Choose an active clinician in your development database.")
        today = datetime.now(timezone.utc).date()
        for index, (status, weight, days) in enumerate(
            [("alive", 2800, None), ("alive", 2200, None), ("died", 1900, 2)], 1
        ):
            request_id = str(uuid5(NAMESPACE_URL, f"afyanova:demo-followup:{doctor.id}:{index}"))
            if db.scalar(
                select(Prediction.id).where(
                    Prediction.clinic_id == doctor.clinic_id, Prediction.request_id == request_id
                )
            ):
                continue
            prediction = Prediction(
                clinic_id=doctor.clinic_id,
                doctor_id=doctor.id,
                patient_ref=f"DEMO-FOLLOWUP-{index}",
                request_id=request_id,
                inputs={"synthetic": True, "multiple": False, "baby_count": 1},
                baby_count=1,
                risk=0,
                risk_band="unclassified",
                top_drivers=[],
                assessment=None,
                recommendation="Synthetic example for testing follow-up only; no model was run.",
            )
            db.add(prediction)
            db.flush()
            prediction.pregnancy_id = prediction.id
            details = BirthOutcomeIn(
                baby_number=1,
                expected_version=0,
                birth_date=today - timedelta(days=10),
                observed_on=today,
                status=status,
                death_age_days=days,
                birth_weight_grams=weight,
                source="Synthetic demonstration data",
                notes="Invented test record. Exclude from clinical evaluation and model training.",
            )
            db.add(
                BirthOutcome(
                    prediction_id=prediction.id,
                    baby_number=1,
                    version=1,
                    doctor_id=doctor.id,
                    details=details.model_dump(mode="json", exclude={"expected_version"}),
                )
            )
            count += 1
        db.commit()
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor-id", type=int, required=True)
    parser.add_argument(
        "--demo",
        action="store_true",
        required=True,
        help="Confirm these are synthetic examples in a development database.",
    )
    args = parser.parse_args()
    print(f"Created {seed_followups(args.doctor_id)} synthetic follow-up records.")
