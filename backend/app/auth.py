"""Password hashing, authenticated clinic membership and team-only authorization."""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Clinic, Doctor, RevokedToken

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def create_token(doctor_id: int, clinic_id: int, token_version: int = 0) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.token_ttl_hours)
    return jwt.encode(
        {
            "sub": str(doctor_id),
            "clinic": clinic_id,
            "exp": expires,
            "jti": str(uuid4()),
            "purpose": "session",
            "version": token_version,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def current_doctor(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> dict:
    try:
        if creds is None:
            raise ValueError("Missing session")
        payload = jwt.decode(
            creds.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp"]},
        )
        doctor = db.get(Doctor, int(payload["sub"]))
        if (
            payload.get("purpose") != "session"
            or not payload.get("jti")
            or not doctor
            or not doctor.is_active
            or payload.get("version", 0) != doctor.token_version
            or doctor.clinic_id != int(payload["clinic"])
            or not db.get(Clinic, doctor.clinic_id)
            or db.get(RevokedToken, payload["jti"])
        ):
            raise ValueError("Session no longer valid")
        return {
            "doctor_id": doctor.id,
            "clinic_id": doctor.clinic_id,
            "is_owner": doctor.is_owner,
            "token_id": payload["jti"],
            "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc),
        }
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            401, "Please sign in again.", headers={"WWW-Authenticate": "Bearer"}
        ) from exc


def require_metrics_access(x_metrics_key: str | None = Header(default=None)) -> None:
    if not (
        settings.metrics_key
        and x_metrics_key
        and hmac.compare_digest(settings.metrics_key, x_metrics_key)
    ):
        raise HTTPException(401, "A valid model publishing key is required.")
