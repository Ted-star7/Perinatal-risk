"""Export the winning algorithms recorded in the shared metrics store.

Run from the repository root with python -m ml.src.select_models.
Recipes follow modeling notebooks. Reports and fitted pipelines stay in ml/models.
No metrics are posted to the hosted API by this command.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

from ml.src.dataset import COHORTS, OUTCOMES, SELECTED, build_cohort, cv_folds

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ml" / "models"
EDUCATION = ["No education", "Primary", "Secondary", "Higher"]


def candidates(cohort: str, features: list[str]):
    numeric = [
        c
        for c in features
        if c
        in ["maternal_age", "maternal_age_at_start", "prior_live_births", "preceding_interval_m"]
    ]
    binary = [
        c
        for c in [
            "first_pregnancy",
            "prior_stillbirth",
            "prior_loss",
            "multiple",
            "interval_imputed",
            "no_anc",
            "anc4plus",
            "urine_tested",
            "iron_tablets",
        ]
        if c in features
    ]
    if cohort == "lbw":
        numeric = [c for c in features if c != "education"]
        binary = []
    transformers = [
        (
            "num",
            Pipeline([("fill", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
            numeric,
        ),
        ("binary", SimpleImputer(strategy="most_frequent"), binary),
    ]
    if "education" in features:
        transformers.append(
            (
                "education",
                Pipeline(
                    [
                        ("fill", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                ["education"],
            )
        )
    logistic = Pipeline(
        [
            ("prep", ColumnTransformer(transformers)),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]
    )
    yield "logistic_regression", logistic, {"model__C": [0.001, 0.01, 0.1, 1, 10]}

    interval_transformers = []
    if "preceding_interval_m" in features:
        interval_transformers.append(
            (
                "interval",
                SimpleImputer(strategy="constant", fill_value=-1),
                ["preceding_interval_m"],
            )
        )
    forest_transformers = interval_transformers + [
        ("rest", "passthrough", [c for c in features if c != "preceding_interval_m"]),
    ]
    if cohort == "lbw":
        anc = [c for c in ["no_anc", "anc4plus"] if c in features]
        forest_transformers = [
            ("education", OrdinalEncoder(categories=[EDUCATION]), ["education"]),
        ] + interval_transformers
        if anc:
            forest_transformers.append(("anc", SimpleImputer(strategy="median"), anc))
        forest_transformers.append(
            (
                "rest",
                "passthrough",
                [c for c in features if c not in ["education", "preceding_interval_m"] + anc],
            )
        )
    forest = Pipeline(
        [
            ("prep", ColumnTransformer(forest_transformers)),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=300, class_weight="balanced", random_state=42, n_jobs=1
                ),
            ),
        ]
    )
    forest_grid = {
        "model__min_samples_leaf": [10, 30, 80] if cohort == "lbw" else [20, 50, 150],
        "model__max_depth": [5, 8, None],
        "model__max_features": ["sqrt", 0.5],
    }
    if cohort == "perinatal_anc":
        # The ANC notebook uses four named configurations and omits interval_imputed.
        forest.set_params(
            prep=ColumnTransformer(
                [
                    ("numeric", SimpleImputer(strategy="median"), numeric),
                    ("binary", SimpleImputer(strategy="most_frequent"), binary),
                ]
            )
        )
        forest_grid = [
            {
                "model__n_estimators": [trees],
                "model__max_depth": [depth],
                "model__min_samples_leaf": [leaf],
            }
            for trees, depth, leaf in [(400, None, 1), (400, 8, 10), (400, 12, 20), (600, 10, 10)]
        ]
    yield (
        "random_forest",
        forest,
        forest_grid,
    )

    boosting_steps = []
    if "education" in features:
        boosting_steps.append(
            (
                "prep",
                ColumnTransformer(
                    [
                        ("education", OrdinalEncoder(categories=[EDUCATION]), ["education"]),
                    ],
                    remainder="passthrough",
                ),
            )
        )
    boosting_steps.append(
        (
            "model",
            HistGradientBoostingClassifier(
                class_weight="balanced",
                early_stopping=False,
                random_state=42,
            ),
        )
    )
    grid = {
        "model__learning_rate": [0.02, 0.05],
        "model__max_iter": [50, 100],
        "model__max_leaf_nodes": [4, 7],
        "model__min_samples_leaf": [20, 80, 150],
        "model__l2_regularization": [1.0, 5.0],
    }
    if cohort == "perinatal":
        boosting_steps[-1][1].set_params(class_weight=None)
    yield "gradient_boosting", Pipeline(boosting_steps), grid


def published_winner(rows: list[dict], cohort: str) -> dict:
    candidates = [
        row
        for row in rows
        if row["cohort"] == cohort
        and row["algorithm"] in ["logistic_regression", "random_forest", "gradient_boosting"]
    ]
    if len({row["algorithm"] for row in candidates}) != 3:
        raise ValueError(f"{cohort}: expected published results for all three algorithms.")
    marked = [row for row in candidates if row.get("is_best")]
    if len(marked) > 1:
        raise ValueError(f"{cohort}: multiple models are marked as best.")
    if marked:
        return marked[0]
    return max(candidates, key=lambda row: row["pr_auc"])


def feature_names(cohort: str, algorithm: str) -> list[str]:
    """Use the predictor order declared in each merged modeling notebook."""
    prefix = "anc" if cohort == "perinatal_anc" else cohort
    suffix = "logreg" if algorithm == "logistic_regression" else algorithm
    path = ROOT / "ml" / "notebooks" / "modeling" / f"{prefix}_{suffix}.ipynb"
    notebook = json.loads(path.read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        for statement in ast.parse("".join(cell["source"])).body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PREDICTORS"
                for target in statement.targets
            ):
                return ast.literal_eval(statement.value)
    if cohort == "perinatal_anc" and algorithm == "random_forest":
        return [
            "maternal_age",
            "prior_live_births",
            "preceding_interval_m",
            "first_pregnancy",
            "prior_stillbirth",
            "prior_loss",
            "multiple",
            "no_anc",
            "anc4plus",
            "urine_tested",
            "iron_tablets",
        ]
    return [
        c
        for c in SELECTED[cohort]
        if c not in [OUTCOMES[cohort], "split", "cluster_id", "country", "weight"]
    ]


def select(cohort: str, published: list[dict], jobs: int = 2, refresh: bool = False) -> dict:
    chosen = None if refresh else published_winner(published, cohort)
    data = build_cohort(cohort)
    train = data[data["split"] == "train"].reset_index(drop=True)
    test = data[data["split"] == "test"].reset_index(drop=True)
    if set(train.cluster_id) & set(test.cluster_id):
        raise ValueError("Training and test clusters overlap.")
    results, fitted = [], {}
    for algorithm in ["logistic_regression", "random_forest", "gradient_boosting"]:
        if not refresh and algorithm != chosen["algorithm"]:
            continue
        features = feature_names(cohort, algorithm)
        _, pipeline, grid = next(
            recipe for recipe in candidates(cohort, features) if recipe[0] == algorithm
        )
        X, y = train[features], train[OUTCOMES[cohort]]
        print(f"{cohort} / {algorithm}: grouped CV", flush=True)
        search = GridSearchCV(
            pipeline,
            grid,
            cv=cv_folds(train, cohort),
            scoring="average_precision",
            refit=True,
            n_jobs=jobs,
            error_score="raise",
        )
        fit_params = {}
        if cohort == "perinatal" and algorithm == "gradient_boosting":
            fit_params["model__sample_weight"] = compute_sample_weight("balanced", y)
        search.fit(X, y, **fit_params)
        results.append(
            {
                "algorithm": algorithm,
                "cv_pr_auc": float(search.best_score_),
                "parameters": search.best_params_,
            }
        )
        fitted[algorithm] = search.best_estimator_
        print(results[-1], flush=True)
    # The algorithm is selected from published metrics. CV selects its configuration.
    winner = max(results, key=lambda row: row["cv_pr_auc"]) if refresh else results[0]
    features = list(fitted[winner["algorithm"]].feature_names_in_)
    evaluation = []
    truth = test[OUTCOMES[cohort]]
    checklist = (
        (test.maternal_age < 18)
        | (test.maternal_age >= 35)
        | (test.prior_live_births >= 5)
        | (test.preceding_interval_m < 24)
        | (test.multiple == 1)
        | (test.prior_stillbirth == 1)
    ).to_numpy()
    events = truth.to_numpy() == 1
    for algorithm, fitted_model in fitted.items():
        predicted = fitted_model.predict_proba(test[fitted_model.feature_names_in_])[:, 1]
        flagged = np.zeros(len(test), dtype=bool)
        flagged[np.argsort(-predicted, kind="stable")[: int(checklist.sum())]] = True
        caught = int((flagged & events).sum())
        evaluation.append(
            {
                "cohort": cohort,
                "algorithm": algorithm,
                "pr_auc": float(average_precision_score(truth, predicted)),
                "roc_auc": float(roc_auc_score(truth, predicted)),
                "recall_at_flag": caught / int(events.sum()),
                "beats_checklist": caught > int((checklist & events).sum()),
                "test_events": int(events.sum()),
                "is_best": algorithm == winner["algorithm"],
            }
        )
    model = fitted[winner["algorithm"]]
    scores = model.predict_proba(test[features])[:, list(model.classes_).index(1)]
    truth = test[OUTCOMES[cohort]]
    path = OUT / cohort / "selected.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as staging:
        staged_model = Path(staging) / path.name
        joblib.dump(model, staged_model)
        staged_model.replace(path)
    report = {
        "cohort": cohort,
        "algorithm": winner["algorithm"],
        "selection": (
            "Highest five-fold grouped training CV PR-AUC across all three algorithms."
            if refresh
            else "Published is_best flag, otherwise highest published PR-AUC. "
            "Configuration tuned with five grouped training folds."
        ),
        "evaluation_metrics": evaluation,
        "published_metrics": chosen,
        "published_candidates": [row for row in published if row["cohort"] == cohort],
        "candidates": results,
        "features": features,
        "sklearn_version": sklearn.__version__,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "calibrated": False,
        "risk_cutoffs": None,
        "test": {
            "rows": len(test),
            "events": int(truth.sum()),
            "pr_auc": float(average_precision_score(truth, scores)),
            "roc_auc": float(roc_auc_score(truth, scores)),
            "brier_score": float(brier_score_loss(truth, scores)),
            "event_rate": float(truth.mean()),
            "mean_score": float(np.mean(scores)),
        },
    }
    path.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{cohort}: exported {winner['algorithm']}", flush=True)
    return report


def publish_local(model_root: Path = OUT) -> None:
    """Publish exported evaluation rows to the local review API."""
    for cohort in COHORTS:
        report = json.loads((model_root / cohort / "selected.json").read_text())
        for row in report["evaluation_metrics"]:
            request = urllib.request.Request(
                "http://localhost:8000/metrics",
                data=json.dumps(row).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-Metrics-Key": os.getenv("METRICS_KEY", ""),
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                json.load(response)
            print(f"Published locally: {cohort} / {row['algorithm']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reevaluate all nine current notebook recipes and select by training CV.",
    )
    parser.add_argument(
        "--publish-local",
        action="store_true",
        help="Publish exported evaluation metrics to http://localhost:8000.",
    )
    args = parser.parse_args()
    if args.refresh or not args.publish_local:
        published = []
        if not args.refresh:
            source = os.getenv("METRICS_API_URL", "https://perinatal-api.onrender.com")
            request = urllib.request.Request(
                f"{source.rstrip('/')}/metrics",
                headers={"X-Metrics-Key": os.getenv("METRICS_KEY", "")},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                published = json.load(response)
        for cohort in COHORTS:
            select(
                cohort,
                published,
                jobs=int(os.getenv("MODEL_SELECTION_JOBS", "2")),
                refresh=args.refresh,
            )
    if args.publish_local:
        publish_local()
