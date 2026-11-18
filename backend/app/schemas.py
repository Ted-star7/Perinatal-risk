"""Pydantic request/response models — the API contract."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator

# ---- registration / auth ----
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=6, max_length=128)]


class ClinicRegister(BaseModel):
    clinic_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)
    ]
    type: str | None = Field(default=None, max_length=40)
    county: str | None = Field(default=None, max_length=60)
    phone: str | None = Field(default=None, max_length=40)
    doctor_name: Name
    email: EmailStr = Field(max_length=160)
    password: Password
    country: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = "Kenya"


class Login(BaseModel):
    email: EmailStr = Field(max_length=160)
    password: str


class Session(BaseModel):
    token: str
    doctor_id: int
    doctor_name: str
    clinic_id: int
    clinic_name: str
    is_owner: bool = False


class InviteRequest(BaseModel):
    email: EmailStr = Field(max_length=160)


class AcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    doctor_name: Name
    password: Password


# ---- predictions ----
class PredictRequest(BaseModel):
    request_id: UUID | None = None
    assessment_token: str | None = None
    patient_ref: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ]
    age: int | None = Field(default=None, ge=11, le=55)
    age_at_start: int | None = Field(default=None, ge=11, le=55)
    parity: int = Field(ge=0, le=16)
    first_pregnancy: bool | None = None
    interval_months: int | None = Field(default=None, ge=1, le=240)
    previous_stillbirth: bool = False
    previous_loss: bool = False
    multiple: bool = False
    told_high_bp: bool = False
    anc_visits: int | None = Field(default=None, ge=0, le=20)
    education: Literal["No education", "Primary", "Secondary", "Higher"] | None = None
    urine_tested: bool | None = None
    iron_tablets: bool | None = None

    @model_validator(mode="after")
    def check_history(self):
        if self.first_pregnancy and (
            self.parity > 0 or self.previous_loss or self.previous_stillbirth
        ):
            raise ValueError("First pregnancy conflicts with the previous pregnancy history.")
        if self.first_pregnancy and self.interval_months is not None:
            raise ValueError("A first pregnancy has no preceding birth interval.")
        return self


class OutcomeResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: Literal["available", "unavailable"]
    label: str
    description: str
    score: float | None = None
    model_id: str | None = None
    message: str
    prediction_context: str | None = None
    calibrated: bool = False
    used_inputs: list[str] = []


class ChecklistResult(BaseModel):
    flagged: bool
    factors: list[str]
    unknown_factors: list[str]
    summary: str


class AssessmentResult(BaseModel):
    assessment_token: str | None = None
    perinatal: OutcomeResult
    lbw: OutcomeResult
    baseline: ChecklistResult
    recommendation: str
    notes: list[str]


class Driver(BaseModel):
    label: str
    weight: float


class BirthOutcomeIn(BaseModel):
    baby_number: int = Field(ge=1, le=10)
    expected_version: int = Field(ge=0)
    birth_date: date | None = None
    observed_on: date
    status: Literal["unknown", "alive", "stillbirth", "died"]
    death_age_days: int | None = Field(default=None, ge=0, le=3650)
    birth_weight_grams: int | None = Field(default=None, ge=100, le=10000)
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] = ""

    @model_validator(mode="after")
    def check_dates(self):
        today = datetime.now(timezone.utc).date()
        if self.observed_on > today or (self.birth_date and self.birth_date > self.observed_on):
            raise ValueError("Check the birth and follow-up dates; future dates are not allowed.")
        if self.status != "unknown" and self.birth_date is None:
            raise ValueError("Enter the birth date for a known birth outcome.")
        if self.birth_weight_grams is not None and self.birth_date is None:
            raise ValueError("Enter the birth date with a measured birth weight.")
        if self.status == "died":
            if self.death_age_days is None:
                raise ValueError("Enter the baby's age in completed days at death.")
            if self.death_age_days > (self.observed_on - self.birth_date).days:
                raise ValueError("Age at death cannot be after the follow-up date.")
        elif self.death_age_days is not None:
            raise ValueError("Age at death applies only to a baby who died after live birth.")
        return self


class BirthOutcomeResponse(BirthOutcomeIn):
    version: int
    doctor_id: int
    recorded_at: datetime


class PredictResponse(BaseModel):
    id: int
    risk: float
    risk_band: str
    top_drivers: list[Driver]
    recommendation: str
    created_at: datetime
    patient_ref: str | None = None
    assessment: AssessmentResult | None = None
    outcomes: list[BirthOutcomeResponse] = []
    multiple: bool = False


# ---- model metrics (one row per cohort + algorithm; modeling notebooks post here) ----
class MetricsIn(BaseModel):
    cohort: Literal["perinatal", "perinatal_anc", "lbw"]
    algorithm: Literal["logistic_regression", "random_forest", "gradient_boosting", "checklist"]
    pr_auc: float = Field(ge=0, le=1, allow_inf_nan=False)
    roc_auc: float = Field(ge=0, le=1, allow_inf_nan=False)
    recall_at_flag: float = Field(ge=0, le=1, allow_inf_nan=False)
    beats_checklist: bool
    test_events: int = Field(ge=0)
    is_best: bool = False


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password
