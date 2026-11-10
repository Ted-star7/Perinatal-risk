"""Database models: clinics, doctors, and the predictions they record."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="clinic")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    clinic: Mapped[Clinic] = relationship(back_populates="doctors")


class Prediction(Base):
    """One assessment, tagged with the clinic and doctor who made it."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    patient_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    risk: Mapped[float] = mapped_column(Float)
    risk_band: Mapped[str] = mapped_column(String(16))
    top_drivers: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(Text)
