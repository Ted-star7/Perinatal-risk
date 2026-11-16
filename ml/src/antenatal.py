"""Predictors whose definitions are available before the current pregnancy ends."""

from pathlib import Path

import numpy as np

from ml.src.dataset import OUTCOMES, build_cohort, load_cohort

CONTEXT = "antenatal_history_v1"
OUT = Path(__file__).resolve().parents[1] / "models" / "antenatal"
COMMON_FEATURES = [
    "maternal_age_at_start",
    "prior_live_births",
    "first_pregnancy",
    "prior_stillbirth",
    "prior_loss",
    "multiple",
]


def features(cohort: str) -> list[str]:
    return COMMON_FEATURES + (["education"] if cohort == "lbw" else [])


def contract(cohort: str) -> dict:
    return {
        "prediction_context": CONTEXT,
        "target": OUTCOMES[cohort],
        "features": features(cohort),
        "age_definition": "Completed years at estimated pregnancy start: floor((p3-p20-v011)/12)",
    }


def dataset(cohort: str):
    data = build_cohort(cohort)
    source = load_cohort(cohort)
    # p3 is the pregnancy-end month, p20 its duration, v011 the mother's birth month.
    # Subtracting duration gives an estimated start date that can be known antenatally.
    age = np.floor((source.p3 - source.p20 - source.v011) / 12)
    if age.isna().any() or not age.between(11, 55).all():
        raise ValueError("A valid age at pregnancy start is required for every training record.")
    data["maternal_age_at_start"] = age.astype(int)
    return data


def checklist_flags(data):
    # This antenatal checklist uses the same information available to the new models.
    return (
        data.maternal_age_at_start.lt(18)
        | data.maternal_age_at_start.ge(35)
        | data.prior_live_births.ge(5)
        | data.multiple.eq(1)
        | data.prior_stillbirth.eq(1)
    ).to_numpy()
