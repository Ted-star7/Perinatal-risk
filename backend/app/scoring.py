"""Serve trusted fitted pipelines using the same feature definitions as training."""

from __future__ import annotations

import hashlib
import io
import logging
import os
import tempfile
import urllib.request
import warnings
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

from app.schemas import (
    AssessmentResult,
    ChecklistResult,
    OutcomeResult,
    PredictRequest,
)
from ml.src import antenatal
from ml.src.artifacts import validate_bundle

logger = logging.getLogger(__name__)
INPUT_LABELS = {
    "maternal_age_at_start": "Mother’s age when this pregnancy began",
    "prior_live_births": "Previous live births",
    "first_pregnancy": "First pregnancy",
    "prior_stillbirth": "Previous stillbirth",
    "prior_loss": "Previous pregnancy loss",
    "multiple": "Twins or more babies",
    "education": "Highest education level",
}
MODEL_ROOT = antenatal.OUT
MODEL_PATHS = {
    "perinatal": ("PERINATAL_MODEL_PATH", MODEL_ROOT / "perinatal" / "selected.joblib"),
    "perinatal_anc": ("ANC_MODEL_PATH", MODEL_ROOT / "perinatal_anc" / "selected.joblib"),
    "lbw": ("LBW_MODEL_PATH", MODEL_ROOT / "lbw" / "selected.joblib"),
}
LABELS = {
    "perinatal": (
        "Risk of death around birth",
        "Stillbirth or death in the first 7 days after birth.",
    ),
    "perinatal_anc": (
        "Risk of death around birth",
        "Stillbirth or death in the first 7 days after birth.",
    ),
    "lbw": ("Low birth weight", "A baby weighing less than 2.5 kg at birth."),
}


class AssessmentInputError(ValueError):
    """The new antenatal predictor definitions need an explicit input."""


class ModelUnavailable(Exception):
    """A fitted model cannot produce a supported prediction."""


@lru_cache(maxsize=3)
def download_model(url: str, digest: str) -> str:
    """Fetch an operator-configured release artifact and verify it before loading."""
    if not url.startswith("https://") or len(digest) != 64:
        raise ValueError("Model downloads need HTTPS and an expected SHA-256 digest.")
    int(digest, 16)
    destination = Path(tempfile.gettempdir()) / f"perinatal-model-{digest}.joblib"
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            checksum = hashlib.sha256()
            total = 0
            with urllib.request.urlopen(url, timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise ValueError("Model download redirected away from HTTPS.")
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 256 * 1024 * 1024:
                        raise ValueError("Model artifact exceeds 256 MB.")
                    checksum.update(chunk)
                    output.write(chunk)
            if checksum.hexdigest() != digest.lower():
                raise ValueError("Model artifact checksum does not match the release.")
            output.flush()
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return str(destination)


@lru_cache(maxsize=3)
def load_model(path: str, cohort: str):
    # Only operator-supplied artifacts are loaded. Joblib files execute Python.
    artifact = Path(path).read_bytes()
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        bundle = joblib.load(io.BytesIO(artifact))
        model, manifest = validate_bundle(bundle, cohort)
    if not hasattr(model, "predict_proba") or not hasattr(model, "feature_names_in_"):
        raise ValueError("Export a fitted pipeline with named input columns and predict_proba.")
    model.release_metadata_ = {
        key: bundle[key]
        for key in [
            "cohort",
            "target",
            "algorithm",
            "created_at",
            "features",
            "calibration",
            "evaluation",
        ]
    }
    model.release_metadata_["prediction_context"] = bundle.get("prediction_context")
    classes = list(model.classes_)
    if len(classes) != 2 or 1 not in classes:
        raise ValueError("Expected a binary outcome with positive class 1.")
    digest = hashlib.sha256(artifact).hexdigest()
    return model, classes.index(1), f"{Path(path).stem}:{digest}"


def first_pregnancy(req: PredictRequest) -> bool:
    if req.first_pregnancy is not None:
        return req.first_pregnancy
    # Compatibility for callers created before the explicit pregnancy question.
    return req.parity == 0 and not req.previous_loss and not req.previous_stillbirth


def feature_row(req: PredictRequest, cohort: str) -> dict:
    return {
        "maternal_age_at_start": req.age_at_start,
        "prior_live_births": req.parity,
        "first_pregnancy": int(first_pregnancy(req)),
        "prior_stillbirth": int(req.previous_stillbirth),
        "prior_loss": int(req.previous_loss),
        "multiple": int(req.multiple),
        "education": req.education,
    }


def predict_outcome(req: PredictRequest, cohort: str) -> OutcomeResult:
    label, description = LABELS[cohort]
    result = OutcomeResult(
        status="unavailable",
        label=label,
        description=description,
        message="This model is unavailable. Ask the project team to check the model setup.",
    )
    try:
        model, positive_index, model_id = get_model(cohort)
        columns = list(model.feature_names_in_)
        row = feature_row(req, cohort)
        if set(columns) - row.keys():
            raise ValueError("The model requires inputs that this assessment does not collect.")
        if "education" in columns and req.education is None:
            result.message = "Enter the mother’s education level to calculate low birth weight."
            return result
        frame = pd.DataFrame([row], columns=columns)
        probabilities = np.asarray(model.predict_proba(frame))
        if probabilities.shape != (1, 2) or not np.isfinite(probabilities).all():
            raise ValueError("The model returned invalid probabilities.")
        if (probabilities < 0).any() or (probabilities > 1).any():
            raise ValueError("The model returned a probability outside 0–1.")
        if not np.isclose(probabilities.sum(), 1):
            raise ValueError("The model probabilities do not sum to one.")
        return result.model_copy(
            update={
                "status": "available",
                "score": float(probabilities[0, positive_index]),
                "model_id": model_id,
                "calibrated": True,
                "prediction_context": antenatal.CONTEXT,
                "used_inputs": [INPUT_LABELS[name] for name in columns],
                "message": "Calibrated using the research training data. "
                "Review this estimate alongside the mother’s current condition and the checklist.",
            }
        )
    except Exception:
        logger.exception("Could not score %s", cohort)
        return result


def checklist(req: PredictRequest) -> ChecklistResult:
    age = req.age_at_start if req.age_at_start is not None else req.age
    if age is None:
        raise AssessmentInputError("Enter the mother’s age when this pregnancy began.")
    checks = [
        (age < 18, "Mother was younger than 18 when this pregnancy began"),
        (age >= 35, "Mother was 35 years or older when this pregnancy began"),
        (req.parity >= 5, "Five or more previous live births"),
        (req.multiple, "Twins or more babies"),
        (req.previous_stillbirth, "Previous stillbirth"),
    ]
    factors = [label for matched, label in checks if matched]
    return ChecklistResult(
        flagged=bool(factors),
        factors=factors,
        unknown_factors=[],
        summary=(
            "Pregnancy-history checklist flags this pregnancy for review."
            if factors
            else "No pregnancy-history checklist factors found in the information entered."
        ),
    )


def score(req: PredictRequest) -> AssessmentResult:
    if req.age_at_start is None:
        raise AssessmentInputError("Enter the mother’s age when this pregnancy began.")
    perinatal = predict_outcome(req, "perinatal")
    if perinatal.status != "available":
        raise ModelUnavailable(perinatal.message)
    baseline = checklist(req)
    return AssessmentResult(
        perinatal=perinatal,
        lbw=predict_outcome(req, "lbw"),
        baseline=baseline,
        recommendation=(
            "Review the checklist factors with the mother and agree on a follow-up and birth plan "
            "using local care guidelines."
            if baseline.flagged
            else "Review the mother’s current condition and agree on the next antenatal visit "
            "using local care guidelines."
        ),
        notes=[
            "These models were retrained using age at pregnancy start, pregnancy history, "
            "multiple pregnancy and education where applicable.",
            "The checklist reviews age at pregnancy start, previous live births, previous "
            "stillbirth and multiple pregnancy.",
            "Clinical validation and action thresholds are pending. Review these research "
            "estimates alongside the mother’s current condition and local care guidelines.",
        ],
    )


def get_model(cohort: str):
    environment, default = MODEL_PATHS[cohort]
    prefix = "ANC" if cohort == "perinatal_anc" else cohort.upper()
    path = os.getenv(environment, str(default))
    if os.getenv(f"{prefix}_MODEL_URL"):
        path = download_model(
            os.environ[f"{prefix}_MODEL_URL"], os.getenv(f"{prefix}_MODEL_SHA256", "")
        )
    model, index, identifier = load_model(path, cohort)
    if model.release_metadata_.get("prediction_context") != antenatal.CONTEXT:
        raise ValueError("This service requires an antenatal-history model release.")
    return model, index, identifier


def model_readiness() -> dict:
    readiness = {}
    for cohort in ["perinatal", "lbw"]:
        try:
            get_model(cohort)
            readiness[cohort] = True
        except Exception:
            logger.exception("Model readiness failed for %s", cohort)
            readiness[cohort] = False
    return readiness
