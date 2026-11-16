"""Clinic registration, membership invitations and revocable sign-in sessions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_token, current_doctor, hash_password, verify_password
from app.database import get_db
from app.models import Clinic, ClinicInvitation, Doctor, RevokedToken
from app.schemas import AcceptInvitation, ClinicRegister, InviteRequest, Login, PasswordChange
from app.schemas import Session as SessionOut

router = APIRouter(tags=["accounts"])


def _session(doctor: Doctor, clinic: Clinic) -> SessionOut:
    return SessionOut(
        token=create_token(doctor.id, clinic.id, doctor.token_version),
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        clinic_id=clinic.id,
        clinic_name=clinic.name,
        is_owner=doctor.is_owner,
    )


def _commit_registration(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This email is already registered. Sign in instead.") from exc


@router.post("/clinics/register", response_model=SessionOut)
def register(body: ClinicRegister, db: Session = Depends(get_db)) -> SessionOut:
    email = str(body.email).casefold()
    if db.scalar(select(Doctor).where(func.lower(Doctor.email) == email)):
        raise HTTPException(409, "This email is already registered. Sign in instead.")
    clinic = Clinic(
        name=body.clinic_name,
        type=body.type,
        county=body.county,
        phone=body.phone,
        country=body.country,
    )
    db.add(clinic)
    db.flush()
    doctor = Doctor(
        clinic_id=clinic.id,
        name=body.doctor_name,
        email=email,
        password_hash=hash_password(body.password),
        is_owner=True,
    )
    db.add(doctor)
    _commit_registration(db)
    return _session(doctor, clinic)


@router.post("/login", response_model=SessionOut)
def login(body: Login, db: Session = Depends(get_db)) -> SessionOut:
    doctor = db.scalar(select(Doctor).where(Doctor.email == str(body.email)))
    if doctor is None:
        matches = db.scalars(
            select(Doctor).where(func.lower(Doctor.email) == str(body.email).casefold())
        ).all()
        doctor = matches[0] if len(matches) == 1 else None
    if (
        not doctor
        or not doctor.is_active
        or not verify_password(body.password, doctor.password_hash)
    ):
        raise HTTPException(401, "The email or password is incorrect.")
    clinic = db.get(Clinic, doctor.clinic_id)
    if clinic is None:
        raise HTTPException(401, "This clinic account is unavailable.")
    return _session(doctor, clinic)


@router.get("/session")
def session(who: dict = Depends(current_doctor)) -> dict:
    return {
        "doctor_id": who["doctor_id"],
        "clinic_id": who["clinic_id"],
        "is_owner": who["is_owner"],
    }


@router.post("/logout")
def logout(who: dict = Depends(current_doctor), db: Session = Depends(get_db)) -> dict:
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))
    db.merge(RevokedToken(token_id=who["token_id"], expires_at=who["expires_at"]))
    db.commit()
    return {"signed_out": True}


@router.post("/clinics/invitations")
def invite(
    body: InviteRequest, who: dict = Depends(current_doctor), db: Session = Depends(get_db)
) -> dict:
    if not who["is_owner"]:
        raise HTTPException(403, "The clinic owner can invite colleagues.")
    email = str(body.email).casefold()
    if db.scalar(select(Doctor).where(func.lower(Doctor.email) == email)):
        raise HTTPException(409, "This email already has an account.")
    token = secrets.token_urlsafe(32)
    db.add(
        ClinicInvitation(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            clinic_id=who["clinic_id"],
            email=email,
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
    )
    db.commit()
    return {"token": token, "email": email, "expires_in_hours": 48}


@router.post("/clinics/join", response_model=SessionOut)
def join(body: AcceptInvitation, db: Session = Depends(get_db)) -> SessionOut:
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    invitation = db.scalar(
        select(ClinicInvitation).where(ClinicInvitation.token_hash == digest).with_for_update()
    )
    if (
        not invitation
        or invitation.used
        or invitation.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    ):
        raise HTTPException(400, "This invitation has expired or has already been used.")
    doctor = Doctor(
        clinic_id=invitation.clinic_id,
        name=body.doctor_name,
        email=invitation.email,
        password_hash=hash_password(body.password),
        is_owner=False,
    )
    invitation.used = True
    db.add(doctor)
    _commit_registration(db)
    return _session(doctor, db.get(Clinic, doctor.clinic_id))


@router.get("/clinics/team")
def team(who: dict = Depends(current_doctor), db: Session = Depends(get_db)) -> list[dict]:
    if not who["is_owner"]:
        raise HTTPException(403, "Only the clinic owner can manage the team.")
    doctors = db.scalars(
        select(Doctor).where(Doctor.clinic_id == who["clinic_id"]).order_by(Doctor.name)
    ).all()
    return [
        {
            "id": doctor.id,
            "name": doctor.name,
            "email": doctor.email,
            "is_active": doctor.is_active,
            "is_owner": doctor.is_owner,
        }
        for doctor in doctors
    ]


@router.post("/clinics/team/{doctor_id}/deactivate")
def deactivate(
    doctor_id: int, who: dict = Depends(current_doctor), db: Session = Depends(get_db)
) -> dict:
    if not who["is_owner"]:
        raise HTTPException(403, "Only the clinic owner can manage the team.")
    doctor = db.get(Doctor, doctor_id)
    if not doctor or doctor.clinic_id != who["clinic_id"]:
        raise HTTPException(404, "This clinician is not in your clinic.")
    if doctor.id == who["doctor_id"]:
        raise HTTPException(400, "You cannot deactivate your own owner account.")
    doctor.is_active = False
    db.commit()
    return {"deactivated": True}


@router.post("/password", response_model=SessionOut)
def password(
    body: PasswordChange, who: dict = Depends(current_doctor), db: Session = Depends(get_db)
) -> SessionOut:
    doctor = db.scalar(select(Doctor).where(Doctor.id == who["doctor_id"]).with_for_update())
    if not verify_password(body.current_password, doctor.password_hash):
        raise HTTPException(400, "The current password is incorrect.")
    doctor.password_hash = hash_password(body.new_password)
    doctor.token_version += 1
    db.commit()
    return _session(doctor, db.get(Clinic, doctor.clinic_id))
