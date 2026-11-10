"""Clinic registration and doctor sign-in."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_token, hash_password, verify_password
from app.database import get_db
from app.models import Clinic, Doctor
from app.schemas import ClinicRegister, Login
from app.schemas import Session as SessionOut

router = APIRouter(tags=["accounts"])


def _session(doctor: Doctor, clinic: Clinic) -> SessionOut:
    return SessionOut(
        token=create_token(doctor.id, clinic.id),
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        clinic_id=clinic.id,
        clinic_name=clinic.name,
    )


@router.post("/clinics/register", response_model=SessionOut)
def register(body: ClinicRegister, db: Session = Depends(get_db)) -> SessionOut:
    exists = db.scalar(select(Doctor).where(Doctor.email == body.email))
    if exists:
        raise HTTPException(409, "That email is already registered. Sign in instead.")

    clinic = Clinic(
        name=body.clinic_name, type=body.type, county=body.county, phone=body.phone
    )
    db.add(clinic)
    db.flush()  # assigns clinic.id

    doctor = Doctor(
        clinic_id=clinic.id,
        name=body.doctor_name,
        email=str(body.email),
        password_hash=hash_password(body.password),
    )
    db.add(doctor)
    db.commit()
    return _session(doctor, clinic)


@router.post("/login", response_model=SessionOut)
def login(body: Login, db: Session = Depends(get_db)) -> SessionOut:
    doctor = db.scalar(select(Doctor).where(Doctor.email == body.email))
    if not doctor or not verify_password(body.password, doctor.password_hash):
        raise HTTPException(401, "Wrong email or password.")
    clinic = db.get(Clinic, doctor.clinic_id)
    return _session(doctor, clinic)
