"""Pydantic request/response models — the API contract."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


# ---- registration / auth ----
class ClinicRegister(BaseModel):
    clinic_name: str
    type: str | None = None
    county: str | None = None
    phone: str | None = None
    doctor_name: str
    email: EmailStr
    password: str


class Login(BaseModel):
    email: EmailStr
    password: str


class Session(BaseModel):
    token: str
    doctor_id: int
    doctor_name: str
    clinic_id: int
    clinic_name: str


# ---- predictions ----
class PredictRequest(BaseModel):
    patient_ref: str | None = None
    age: int
    parity: int
    interval_months: int | None = None
    previous_stillbirth: bool = False
    previous_loss: bool = False
    multiple: bool = False
    told_high_bp: bool = False
    anc_visits: int = 0


class Driver(BaseModel):
    label: str
    weight: float


class PredictResponse(BaseModel):
    id: int
    risk: float
    risk_band: str
    top_drivers: list[Driver]
    recommendation: str
    created_at: datetime
    patient_ref: str | None = None


# ---- model metrics (one row per cohort + algorithm; modeling notebooks post here) ----
class MetricsIn(BaseModel):
    cohort: str
    algorithm: str
    pr_auc: float
    roc_auc: float
    recall_at_flag: float
    beats_checklist: bool
    test_events: int
    is_best: bool = False
