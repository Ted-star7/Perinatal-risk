"""Reproduce classification counts without changing releases or publishing metrics.

Historical and antenatal experiments have different predictors and checklists.
The comparison keeps them separate and uses each experiment's existing held-out
split and recorded training-CV hyperparameters. Only a release winner has been
calibrated in the existing reports; other candidates retain their recorded recipe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

import joblib
import numpy as np

from ml.src import antenatal
from ml.src.artifacts import validate_bundle
from ml.src.calibrate_models import evaluate
from ml.src.dataset import COHORTS, OUTCOMES, build_cohort
from ml.src.select_models import OUT, candidates, feature_names


def classification_counts(truth, predicted) -> dict:
    """Count actual outcomes against binary flags; undefined rates remain null."""
    actual, flags = np.asarray(truth), np.asarray(predicted)
    if actual.ndim != 1 or flags.shape != actual.shape or not len(actual):
        raise ValueError("Expected nonempty, equally sized one-dimensional arrays.")
    if not np.isin(actual, [0, 1]).all() or not np.isin(flags, [0, 1]).all():
        raise ValueError("Outcomes and flags must contain only binary 0/1 values.")
    actual, flags = actual.astype(bool), flags.astype(bool)
    tp, fp = int((actual & flags).sum()), int((~actual & flags).sum())
    tn, fn = int((~actual & ~flags).sum()), int((actual & ~flags).sum())

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "flagged": tp + fp,
        "recall": ratio(tp, tp + fn),
        "precision": ratio(tp, tp + fp),
        "specificity": ratio(tn, tn + fp),
        "negative_predictive_value": ratio(tn, tn + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def flag_top_k(probability, count: int) -> np.ndarray:
    """Research batch ranking: stable row order breaks ties at the capacity limit."""
    scores = np.asarray(probability, dtype=float)
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError("Scores must be a finite one-dimensional array.")
    if ((scores < 0) | (scores > 1)).any():
        raise ValueError("Scores must lie between zero and one.")
    if isinstance(count, bool) or not isinstance(count, (int, np.integer)):
        raise ValueError("Flag count must be an integer.")
    if not 0 <= count <= len(scores):
        raise ValueError("Flag count must lie between zero and the number of records.")
    flags = np.zeros(len(scores), dtype=bool)
    flags[np.argsort(-scores, kind="stable")[:count]] = True
    return flags


def compare(profile: str = "antenatal") -> dict:
    """Evaluate frozen release recipes; never choose a winner from test results."""
    if profile not in ["historical", "antenatal"]:
        raise ValueError("Choose historical or antenatal.")
    root = antenatal.OUT if profile == "antenatal" else OUT
    result = {
        "profile": profile,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision_rule": "Flag the same number of held-out records as this profile's checklist.",
        "policy": "Research batch top-k; stable row order breaks score ties. No clinical cutoff.",
        "selection": "Existing training-CV settings are reused; test rows do not select models.",
        "calibration_note": (
            "Reproduces recorded exports: release winners are calibrated; "
            "other candidates are not. "
            "Calibration status is included for every row."
        ),
        "cohorts": [],
    }
    for cohort in COHORTS:
        path = root / cohort / "selected.joblib"
        report = json.loads(path.with_suffix(".json").read_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != report["sha256"]:
            raise ValueError(f"{cohort}: model hash does not match its evaluation report.")
        selected, _ = validate_bundle(joblib.load(path), cohort)
        data = antenatal.dataset(cohort) if profile == "antenatal" else build_cohort(cohort)
        train = data[data.split.eq("train")].reset_index(drop=True)
        test = data[data.split.eq("test")].reset_index(drop=True)
        if set(train.cluster_id) & set(test.cluster_id):
            raise ValueError("Training and held-out survey clusters overlap.")
        truth = test[OUTCOMES[cohort]]
        if profile == "antenatal":
            checklist = antenatal.checklist_flags(test)
        else:
            checklist = (
                test.maternal_age.lt(18)
                | test.maternal_age.ge(35)
                | test.prior_live_births.ge(5)
                | test.preceding_interval_m.lt(24)
                | test.multiple.eq(1)
                | test.prior_stillbirth.eq(1)
            ).to_numpy()
        count = int(checklist.sum())
        group = {
            "cohort": cohort,
            "target": OUTCOMES[cohort],
            "model_sha256": digest,
            "release_algorithm": report["algorithm"],
            "source_report_sha256": hashlib.sha256(
                path.with_suffix(".json").read_bytes()
            ).hexdigest(),
            "rows": len(test),
            "events": int(truth.sum()),
            "checklist": classification_counts(truth, checklist),
            "models": [],
        }
        published = {row["algorithm"]: row for row in report["evaluation_metrics"]}
        for setting in report["candidates"]:
            algorithm = setting["algorithm"]
            is_release = algorithm == report["algorithm"]
            if is_release:
                model = selected
                columns = list(model.feature_names_in_)
            else:
                columns = (
                    antenatal.features(cohort)
                    if profile == "antenatal"
                    else feature_names(cohort, algorithm)
                )
                _, model, _ = next(
                    row for row in candidates(cohort, columns) if row[0] == algorithm
                )
                if profile == "antenatal" and algorithm == "gradient_boosting":
                    model.set_params(model__class_weight="balanced")
                model.set_params(**setting["parameters"])
                model.fit(train[columns], train[OUTCOMES[cohort]])
            scores = model.predict_proba(test[columns])[:, list(model.classes_).index(1)]
            metrics = evaluate(truth, scores)
            counts = classification_counts(truth, flag_top_k(scores, count))
            reference = published[algorithm]
            for key, value in {
                "pr_auc": metrics["pr_auc"],
                "roc_auc": metrics["roc_auc"],
                "recall_at_flag": counts["recall"],
            }.items():
                if not np.isclose(value, reference[key], rtol=1e-8, atol=1e-10):
                    raise ValueError(
                        f"{profile}/{cohort}/{algorithm}: {key} differs from its report."
                    )
            group["models"].append(
                {
                    "algorithm": algorithm,
                    "features": columns,
                    "training_cv_average_precision": setting["cv_pr_auc"],
                    "is_release_algorithm": is_release,
                    "calibrated": is_release and report.get("calibrated", False),
                    **metrics,
                    **counts,
                }
            )
            print(profile, cohort, algorithm, counts, flush=True)
        result["cohorts"].append(group)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["historical", "antenatal"], default="antenatal")
    args = parser.parse_args()
    comparison = compare(args.profile)
    destination = OUT / "comparisons" / f"{args.profile}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(comparison, indent=2) + "\n")
    print("Wrote", destination)
