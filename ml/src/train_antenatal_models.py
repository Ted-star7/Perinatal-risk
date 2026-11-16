"""Select and calibrate antenatal models using information available during pregnancy."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.model_selection import GridSearchCV

from ml.src import antenatal
from ml.src.artifacts import FORMAT_VERSION, contract_hash, validate_bundle
from ml.src.calibrate_models import evaluate
from ml.src.dataset import COHORTS, OUTCOMES, cv_folds
from ml.src.select_models import candidates, publish_local


def train(cohort: str) -> dict:
    data = antenatal.dataset(cohort)
    train = data[data.split.eq("train")].reset_index(drop=True)
    test = data[data.split.eq("test")].reset_index(drop=True)
    columns = antenatal.features(cohort)
    target = OUTCOMES[cohort]
    folds = cv_folds(train, cohort)
    fitted, searches = {}, []
    for algorithm, pipeline, grid in candidates(cohort, columns):
        if algorithm == "gradient_boosting":
            pipeline.set_params(model__class_weight="balanced")
        print(cohort, algorithm, "antenatal grouped model selection", flush=True)
        search = GridSearchCV(
            pipeline, grid, cv=folds, scoring="average_precision", n_jobs=2, error_score="raise"
        )
        search.fit(train[columns], train[target])
        fitted[algorithm] = search.best_estimator_
        searches.append(
            {
                "algorithm": algorithm,
                "cv_pr_auc": float(search.best_score_),
                "parameters": search.best_params_,
            }
        )
        print(searches[-1], flush=True)
    winner = max(searches, key=lambda row: row["cv_pr_auc"])
    base = fitted[winner["algorithm"]]
    calibrated = CalibratedClassifierCV(
        estimator=clone(base), cv=folds, method="sigmoid", ensemble=False, n_jobs=2
    )
    calibrated.fit(train[columns], train[target])
    truth = test[target]
    probability = calibrated.predict_proba(test[columns])[:, list(calibrated.classes_).index(1)]
    flags = antenatal.checklist_flags(test)
    events = truth.to_numpy() == 1
    evaluation = []
    for algorithm, model in fitted.items():
        scores = (
            probability
            if algorithm == winner["algorithm"]
            else model.predict_proba(test[columns])[:, 1]
        )
        flagged = np.zeros(len(test), dtype=bool)
        flagged[np.argsort(-scores, kind="stable")[: int(flags.sum())]] = True
        metrics = evaluate(truth, scores)
        caught = int((flagged & events).sum())
        evaluation.append(
            {
                "cohort": cohort,
                "algorithm": algorithm,
                "pr_auc": metrics["pr_auc"],
                "roc_auc": metrics["roc_auc"],
                "recall_at_flag": caught / int(events.sum()),
                "beats_checklist": caught > int((flags & events).sum()),
                "test_events": int(events.sum()),
                "is_best": algorithm == winner["algorithm"],
            }
        )
    observed, predicted = calibration_curve(truth, probability, n_bins=10, strategy="quantile")
    country_metrics = {}
    for country, rows in test.groupby("country"):
        indexes = rows.index.to_numpy()
        country_metrics[country] = {
            "unweighted": evaluate(truth.iloc[indexes], probability[indexes]),
            "survey_weighted": evaluate(truth.iloc[indexes], probability[indexes], rows.weight),
        }
    report = {
        "cohort": cohort,
        "algorithm": winner["algorithm"],
        "prediction_context": antenatal.CONTEXT,
        "input_definitions": antenatal.contract(cohort),
        "features": columns,
        "sklearn_version": sklearn.__version__,
        "selection": (
            "Highest five-fold grouped training CV average precision across three algorithms."
        ),
        "candidates": searches,
        "evaluation_metrics": evaluation,
        "test": evaluate(truth, probability),
        "country_metrics": country_metrics,
        "calibrated": True,
        "calibration": {
            "method": "sigmoid_grouped_oof",
            "observed": observed.tolist(),
            "predicted": predicted.tolist(),
        },
        "risk_cutoffs": None,
        "clinical_validation": "Independent prospective clinical validation pending",
        "checklist_definition": (
            "Antenatal history checklist using age at pregnancy start, parity, "
            "multiple pregnancy and prior stillbirth."
        ),
    }
    bundle = {
        "format_version": FORMAT_VERSION,
        "cohort": cohort,
        "target": target,
        "prediction_context": antenatal.CONTEXT,
        "features": columns,
        "contract_hash": contract_hash(cohort, antenatal.CONTEXT),
        "calibration": "sigmoid_grouped_oof",
        "model": calibrated,
        "base_model": clone(base),
        "algorithm": winner["algorithm"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": report,
    }
    validate_bundle(bundle, cohort)
    destination = antenatal.OUT / cohort
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        staged = Path(temporary) / "selected.joblib"
        joblib.dump(bundle, staged)
        report = dict(
            report,
            sha256=hashlib.sha256(staged.read_bytes()).hexdigest(),
            contract_hash=bundle["contract_hash"],
        )
        staged_report = Path(temporary) / "selected.json"
        staged_report.write_text(json.dumps(report, indent=2) + "\n")
        staged.replace(destination / "selected.joblib")
        staged_report.replace(destination / "selected.json")
    print("Completed antenatal release", cohort, winner["algorithm"], report["test"], flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publish-local",
        action="store_true",
        help="Publish the completed antenatal evaluation reports to the local API.",
    )
    args = parser.parse_args()
    if args.publish_local:
        publish_local(antenatal.OUT)
    else:
        for cohort in COHORTS:
            train(cohort)
