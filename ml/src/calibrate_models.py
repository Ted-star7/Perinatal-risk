"""Calibrate selected models on grouped training folds and export verified bundles.

The existing held-out rows are used for evaluation only. These are research
estimates. Clinical validation requires an independently collected cohort.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from ml.src.artifacts import FORMAT_VERSION, contract_hash, validate_bundle
from ml.src.dataset import COHORTS, OUTCOMES, build_cohort, cv_folds
from ml.src.preprocessing import BirthIntervalImputer
from ml.src.select_models import OUT


def evaluate(y, probability, weights=None) -> dict:
    return {
        "rows": len(y),
        "events": int(y.sum()),
        "pr_auc": float(average_precision_score(y, probability, sample_weight=weights)),
        "roc_auc": float(roc_auc_score(y, probability, sample_weight=weights)),
        "brier_score": float(brier_score_loss(y, probability, sample_weight=weights)),
        "event_rate": float(np.average(y, weights=weights)),
        "mean_score": float(np.average(probability, weights=weights)),
    }


def export(cohort: str) -> dict:
    path = OUT / cohort / "selected.joblib"
    previous = joblib.load(path)
    base = previous["base_model"] if isinstance(previous, dict) else previous
    base = clone(base)
    # Balance only the risk estimator. Calibration itself uses actual outcome frequencies.
    if cohort == "perinatal" and "model__class_weight" in base.get_params():
        base.set_params(model__class_weight="balanced")
    report = json.loads(path.with_suffix(".json").read_text())
    data = build_cohort(cohort)
    train = data[data.split.eq("train")].reset_index(drop=True)
    test = data[data.split.eq("test")].reset_index(drop=True)
    features = report["features"]
    model = CalibratedClassifierCV(
        estimator=Pipeline([("history", BirthIntervalImputer()), ("risk", base)]),
        method="sigmoid",
        cv=cv_folds(train, cohort),
        ensemble=False,
        n_jobs=2,
    )
    print(f"{cohort}: fitting grouped out-of-fold calibration", flush=True)
    model.fit(train[features], train[OUTCOMES[cohort]])
    probability = model.predict_proba(test[features])[:, list(model.classes_).index(1)]
    truth = test[OUTCOMES[cohort]]
    observed, predicted = calibration_curve(truth, probability, n_bins=10, strategy="quantile")
    report["uncalibrated_test"] = report.get("uncalibrated_test", report["test"])
    report["test"] = evaluate(truth, probability)
    report["calibrated"] = True
    report["clinical_validation"] = "Independent prospective validation pending"
    report["calibration"] = {
        "method": "sigmoid_grouped_oof",
        "observed": observed.tolist(),
        "predicted": predicted.tolist(),
    }
    report["country_metrics"] = {}
    for country, rows in test.groupby("country"):
        indexes = rows.index.to_numpy()
        report["country_metrics"][country] = {
            "unweighted": evaluate(truth.iloc[indexes], probability[indexes]),
            "survey_weighted": evaluate(truth.iloc[indexes], probability[indexes], rows.weight),
        }
    checklist = (
        (test.maternal_age < 18)
        | (test.maternal_age >= 35)
        | (test.prior_live_births >= 5)
        | (test.preceding_interval_m < 24)
        | test.multiple.eq(1)
        | test.prior_stillbirth.eq(1)
    ).to_numpy()
    flagged = np.zeros(len(test), dtype=bool)
    flagged[np.argsort(-probability, kind="stable")[: int(checklist.sum())]] = True
    events = truth.to_numpy() == 1
    for row in report["evaluation_metrics"]:
        if row["is_best"]:
            row.update(
                pr_auc=report["test"]["pr_auc"],
                roc_auc=report["test"]["roc_auc"],
                recall_at_flag=float((flagged & events).sum() / events.sum()),
                beats_checklist=bool((flagged & events).sum() > (checklist & events).sum()),
            )
    bundle = {
        "format_version": FORMAT_VERSION,
        "cohort": cohort,
        "target": OUTCOMES[cohort],
        "features": features,
        "contract_hash": contract_hash(cohort),
        "calibration": "sigmoid_grouped_oof",
        "model": model,
        "base_model": base,
        "algorithm": report["algorithm"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    validate_bundle(bundle, cohort)
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        staged = type(path)(temporary) / path.name
        joblib.dump(bundle, staged)
        report["sha256"] = hashlib.sha256(staged.read_bytes()).hexdigest()
        report["contract_hash"] = contract_hash(cohort)
        bundle["evaluation"] = {key: value for key, value in report.items() if key != "sha256"}
        joblib.dump(bundle, staged)
        report["sha256"] = hashlib.sha256(staged.read_bytes()).hexdigest()
        staged.replace(path)
        staged_report = type(path)(temporary) / "selected.json"
        staged_report.write_text(json.dumps(report, indent=2) + "\n")
        staged_report.replace(path.with_suffix(".json"))
    print(cohort, report["test"], flush=True)
    return report


if __name__ == "__main__":
    for cohort in COHORTS:
        export(cohort)
