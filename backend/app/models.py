"""Database models: clinics, doctors, and the predictions they record."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    county: Mapped[str | None] = mapped_column(String(60), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    country: Mapped[str] = mapped_column(String(80), default="Kenya")

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="clinic")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    token_version: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=True)

    clinic: Mapped[Clinic] = relationship(back_populates="doctors")


class Prediction(Base):
    """One assessment, tagged with the clinic and doctor who made it."""

    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("clinic_id", "request_id", name="uq_prediction_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    patient_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    risk: Mapped[float] = mapped_column(Float)
    risk_band: Mapped[str] = mapped_column(String(16))
    top_drivers: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(Text)
    assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    token_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClinicInvitation(Base):
    __tablename__ = "clinic_invitations"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"))
    email: Mapped[str] = mapped_column(String(160))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class BirthOutcome(Base):
    """Append-only follow-up revisions; one baby can have several observations."""

    __tablename__ = "birth_outcomes"
    __table_args__ = (
        UniqueConstraint("prediction_id", "baby_number", "version", name="uq_outcome_version"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    baby_number: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    details: Mapped[dict] = mapped_column(JSON)
