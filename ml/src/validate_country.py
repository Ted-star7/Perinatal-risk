"""Select and calibrate on Kenya only, then evaluate Tanzania as a country holdout.

This is retrospective survey validation. Prospective clinical validation requires
independent patient data. No held-out Tanzania rows participate in model selection.
"""

from __future__ import annotations

import json

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GridSearchCV

from ml.src import antenatal
from ml.src.calibrate_models import evaluate
from ml.src.dataset import COHORTS, OUTCOMES, cv_folds
from ml.src.select_models import candidates

OUT = antenatal.OUT


def validate(cohort: str) -> dict:
    data = antenatal.dataset(cohort)
    train = data[data.country.eq("Kenya")].reset_index(drop=True)
    test = data[data.country.eq("Tanzania")].reset_index(drop=True)
    models, results = {}, []
    for algorithm in ["logistic_regression", "random_forest", "gradient_boosting"]:
        features = antenatal.features(cohort)
        _, estimator, grid = next(
            row for row in candidates(cohort, features) if row[0] == algorithm
        )
        if algorithm == "gradient_boosting":
            estimator.set_params(model__class_weight="balanced")
        print(cohort, algorithm, "Kenya-only grouped selection", flush=True)
        search = GridSearchCV(
            estimator,
            grid,
            scoring="average_precision",
            cv=cv_folds(train, cohort),
            n_jobs=2,
            error_score="raise",
        )
        search.fit(train[features], train[OUTCOMES[cohort]])
        results.append(
            {
                "algorithm": algorithm,
                "cv_pr_auc": float(search.best_score_),
                "parameters": search.best_params_,
            }
        )
        models[algorithm] = search.best_estimator_
    winner = max(results, key=lambda row: row["cv_pr_auc"])
    features = list(models[winner["algorithm"]].feature_names_in_)
    calibrated = CalibratedClassifierCV(
        estimator=clone(models[winner["algorithm"]]),
        cv=cv_folds(train, cohort),
        method="sigmoid",
        ensemble=False,
        n_jobs=2,
    )
    calibrated.fit(train[features], train[OUTCOMES[cohort]])
    probability = calibrated.predict_proba(test[features])[:, 1]
    report = {
        "cohort": cohort,
        "prediction_context": antenatal.CONTEXT,
        "features": features,
        "training_country": "Kenya",
        "held_out_country": "Tanzania",
        "algorithm": winner["algorithm"],
        "candidates": results,
        "calibration": "Kenya-only grouped out-of-fold sigmoid",
        "test": evaluate(test[OUTCOMES[cohort]], probability),
        "survey_weighted_test": evaluate(test[OUTCOMES[cohort]], probability, test.weight),
        "clinical_validation": "Independent prospective validation pending",
    }
    path = OUT / cohort / "country_validation.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("Completed country validation", cohort, report["test"], flush=True)
    return report


if __name__ == "__main__":
    for cohort in COHORTS:
        validate(cohort)
