"""Versioned serving bundles shared by training, deployment and the API."""

from __future__ import annotations

import hashlib
import json

from ml.src import antenatal
from ml.src.dataset import INTERVAL_MEDIAN, OUTCOMES, SELECTED

FORMAT_VERSION = 1


def contract(cohort: str, prediction_context: str | None = None) -> dict:
    if prediction_context == antenatal.CONTEXT:
        return antenatal.contract(cohort)
    return {
        "target": OUTCOMES[cohort],
        "features": [
            name
            for name in SELECTED[cohort]
            if name not in [OUTCOMES[cohort], "split", "cluster_id", "country", "weight"]
        ],
        "interval_median": INTERVAL_MEDIAN[cohort],
    }


def contract_hash(cohort: str, prediction_context: str | None = None) -> str:
    return hashlib.sha256(
        json.dumps(contract(cohort, prediction_context), sort_keys=True).encode()
    ).hexdigest()


def validate_bundle(bundle: object, cohort: str) -> tuple:
    if not isinstance(bundle, dict) or bundle.get("format_version") != FORMAT_VERSION:
        raise ValueError("A versioned model bundle is required. Run the calibration exporter.")
    if bundle.get("cohort") != cohort or bundle.get("target") != OUTCOMES[cohort]:
        raise ValueError("The model outcome does not match its configured endpoint.")
    context = bundle.get("prediction_context")
    if context not in [None, antenatal.CONTEXT]:
        raise ValueError("Unsupported model prediction context.")
    if bundle.get("contract_hash") != contract_hash(cohort, context):
        raise ValueError("The model input contract does not match this application version.")
    if bundle.get("calibration") != "sigmoid_grouped_oof":
        raise ValueError("The release must contain a grouped out-of-fold calibrated model.")
    model = bundle["model"]
    features = list(model.feature_names_in_)
    if features != bundle.get("features") or set(features) - set(
        contract(cohort, context)["features"]
    ):
        raise ValueError("The model feature list differs from its release manifest.")
    return model, bundle
