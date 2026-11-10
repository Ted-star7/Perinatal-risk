"""Password hashing and JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# pbkdf2_sha256 is pure-Python — no native build needed.
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_bearer = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def create_token(doctor_id: int, clinic_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.token_ttl_hours)
    payload = {"sub": str(doctor_id), "clinic": clinic_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_doctor(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Decode the bearer token into {doctor_id, clinic_id}."""
    try:
        payload = jwt.decode(
            creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return {"doctor_id": int(payload["sub"]), "clinic_id": int(payload["clinic"])}
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        )
