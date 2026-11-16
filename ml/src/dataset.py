"""Shared dataset builder for the modeling stage.

Division of work:
  - load_cohort()  — concatenates the Kenya + Tanzania files for a cohort.
                     (written; don't change the concat logic)
  - clean_cohort() — checks the counts and cleans the concatenated data, plus the
                     train/test split, cv_folds() and check_interval_medians().
                     Jeff (done).
  - SELECTED       — the columns each cohort keeps.  TODO: team (from the EDA).

Everyone imports build_cohort() so all three models train on the same combined,
cleaned data. Run `python ml/src/dataset.py` to sanity-check the concatenation.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"

# The three cohorts. Each concatenates its ke_ + tz_ files.
COHORTS = ["perinatal", "perinatal_anc", "lbw"]


def load_cohort(name: str) -> pd.DataFrame:
    """Concatenate the Kenya and Tanzania files for one cohort (stack the rows).

    Both files must have the same columns; we add nothing and drop nothing here.
    """
    if name not in COHORTS:
        raise ValueError(f"unknown cohort {name!r}; expected one of {COHORTS}")

    ke = pd.read_csv(PROCESSED / f"ke_{name}.csv")
    tz = pd.read_csv(PROCESSED / f"tz_{name}.csv")

    if list(ke.columns) != list(tz.columns):
        raise ValueError(f"{name}: Kenya and Tanzania columns differ, cannot concatenate")

    combined = pd.concat([ke, tz], ignore_index=True)
    return combined


# -------------------------------------------------------------------------
# The final columns to keep for each cohort: the outcome and design columns
# (split, cluster_id, country, weight, interval_imputed), then the features.
# Lists and reasons: ml/notebooks/pooled/correlation_features.ipynb (section G).
# -------------------------------------------------------------------------
SELECTED: dict[str, list[str] | None] = {
    "perinatal": [
        "perinatal_death",
        "split",
        "cluster_id",
        "country",
        "weight",
        "interval_imputed",
        "maternal_age",
        "prior_live_births",
        "first_pregnancy",
        "prior_stillbirth",
        "prior_loss",
        "preceding_interval_m",
        "multiple",
    ],
    "perinatal_anc": [
        "perinatal_death",
        "split",
        "cluster_id",
        "country",
        "weight",
        "interval_imputed",
        "maternal_age",
        "prior_live_births",
        "first_pregnancy",
        "prior_stillbirth",
        "prior_loss",
        "preceding_interval_m",
        "multiple",
        "no_anc",
        "anc4plus",
        "urine_tested",
        "iron_tablets",
    ],
    "lbw": [
        "low_birth_weight",
        "split",
        "cluster_id",
        "country",
        "weight",
        "interval_imputed",
        "maternal_age",
        "prior_live_births",
        "first_pregnancy",
        "prior_stillbirth",
        "prior_loss",
        "preceding_interval_m",
        "multiple",
        "education",
        "no_anc",
        "anc4plus",
    ],
}


# =========================================================================
# Jeff: cleaning, train/test split and checks (everything from here down to
# build_cohort). Agreed rules: G13 Final Plan, section 1.
# =========================================================================
OUTCOMES = {
    "perinatal": "perinatal_death",
    "perinatal_anc": "perinatal_death",
    "lbw": "low_birth_weight",
}
# Median preceding interval (months) of later pregnancies with a known interval,
# from the training rows only; check_interval_medians() recomputes them.
INTERVAL_MEDIAN = {"perinatal": 35, "perinatal_anc": 36, "lbw": 39}
INTERVAL_ORDER = ["First pregnancy", "<24 months", "24-35 months", "36+ months"]
N_SPLITS = 5  # every fifth cluster is held out = 20% test
SEED = 42
CONFIG = Path(__file__).resolve().parents[2] / "contracts" / "cohort_config.yaml"


def check_counts(df: pd.DataFrame, name: str) -> None:
    """Stop if any country's rows or events differ from contracts/cohort_config.yaml."""
    spec = yaml.safe_load(CONFIG.read_text())["cohorts"][name]
    expected_countries = set(spec["n"])
    actual_countries = set(df["country"].str.lower().dropna())
    if actual_countries != expected_countries or df["country"].isna().any():
        raise ValueError(
            f"{name}: expected countries {sorted(expected_countries)}, "
            f"got {sorted(actual_countries)}"
        )
    for country, part in df.groupby("country"):
        key = country.lower()
        expected = (spec["n"][key], spec["expected_events"][key])
        found = (len(part), int(part[OUTCOMES[name]].sum()))
        if found != expected:
            raise ValueError(
                f"{name}, {country}: rows/events {found}, expected {expected}. "
                "Re-copy the CSV from G13_Team_Data.zip."
            )


def clean_cohort(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Clean the concatenated cohort (Kenya + Tanzania together, row by row).

    0. check_counts(): rows and events per country must match cohort_config.yaml,
       so everyone is working on identical data.
    1. cluster_id = country + "_" + v001 (cluster numbers restart in each survey).
    2. first_pregnancy = 1 when there is no previous pregnancy. These have no
       interval by design and are never given one.
    3. Later pregnancies with an unknown preceding_interval_m get the cohort's
       training median (INTERVAL_MEDIAN); interval_imputed = 1 marks them.
    4. interval_group, short_interval (<24 months), and for the ANC and LBW
       cohorts no_anc and anc4plus (blank when the number of visits is unknown).
    5. checklist_flag: any item of the current high-risk checklist.
    6. split: "train" or "test", the same 80/20 cluster split for every cohort.
    No rows are dropped. Categories are encoded later, inside each model's
    pipeline, and the few remaining blanks (ANC items) are imputed there too.
    If SELECTED lists columns, keep the outcome, split, cluster_id, country and
    weight in the list.
    """
    check_counts(df, name)
    df = df.copy()
    df["cluster_id"] = df["country"] + "_" + df["v001"].astype(str)

    first = df["prior_pregnancies"].eq(0)
    unknown = ~first & df["preceding_interval_m"].isna()
    df["first_pregnancy"] = first.astype(int)
    df["interval_imputed"] = unknown.astype(int)
    df.loc[unknown, "preceding_interval_m"] = INTERVAL_MEDIAN[name]

    interval = df["preceding_interval_m"]
    groups = np.select(
        [first, interval < 24, interval < 36],
        INTERVAL_ORDER[:3],
        default=INTERVAL_ORDER[3],
    )
    df["interval_group"] = pd.Categorical(groups, INTERVAL_ORDER)
    df["short_interval"] = interval.lt(24).astype(int)

    if "anc_visits" in df:
        visits = df["anc_visits"]
        df["no_anc"] = visits.eq(0).astype(float).where(visits.notna())
        df["anc4plus"] = visits.ge(4).astype(float).where(visits.notna())

    df["checklist_flag"] = (
        (df["maternal_age"] < 18)
        | (df["maternal_age"] >= 35)
        | (df["prior_live_births"] >= 5)
        | (interval < 24)
        | (df["multiple"] == 1)
        | (df["prior_stillbirth"] == 1)
    ).astype(int)

    df["split"] = np.where(df["cluster_id"].isin(test_clusters()), "test", "train")

    cols = SELECTED.get(name)
    if cols is not None:
        df = df[cols]
    return df


def _cluster_positions(df: pd.DataFrame, outcome: str) -> pd.Series:
    """Each cluster's position within its country: ordered by events, then a fixed hash."""
    per = df.groupby(["country", "cluster_id"])[outcome].sum().rename("events").reset_index()
    per["tiebreak"] = [hashlib.md5(f"{SEED}-{c}".encode()).hexdigest() for c in per["cluster_id"]]
    per = per.sort_values(["country", "events", "tiebreak"]).reset_index(drop=True)
    per["position"] = per.groupby("country").cumcount()
    return per.set_index("cluster_id")["position"]


@lru_cache(maxsize=1)
def test_clusters() -> frozenset:
    """The test clusters: every fifth cluster per country, ordered by perinatal deaths.

    Chosen once on the perinatal cohort and used for all three cohorts. No random
    numbers, so the split is identical on every computer and package version.
    """
    df = load_cohort("perinatal")
    df["cluster_id"] = df["country"] + "_" + df["v001"].astype(str)
    position = _cluster_positions(df, "perinatal_death")
    return frozenset(position[position % N_SPLITS == 0].index)


def cv_folds(train: pd.DataFrame, name: str, n_splits: int = N_SPLITS) -> list:
    """Cluster-grouped cross-validation folds on the training rows (pass as cv=folds).

    `train` must have a fresh index, e.g. df[df["split"] == "train"].reset_index(drop=True).
    """
    position = _cluster_positions(train, OUTCOMES[name])
    fold = train["cluster_id"].map(position % n_splits).to_numpy()
    return [(np.where(fold != k)[0], np.where(fold == k)[0]) for k in range(n_splits)]


def check_interval_medians() -> dict:
    """Recompute each cohort's median interval from training rows; must match INTERVAL_MEDIAN."""
    found = {}
    for c in COHORTS:
        raw = load_cohort(c)
        raw["cluster_id"] = raw["country"] + "_" + raw["v001"].astype(str)
        train = raw[~raw["cluster_id"].isin(test_clusters())]
        known = train[train["prior_pregnancies"].gt(0) & train["preceding_interval_m"].notna()]
        found[c] = int(known["preceding_interval_m"].median())
    if found != INTERVAL_MEDIAN:
        raise ValueError(f"training medians {found} differ from INTERVAL_MEDIAN {INTERVAL_MEDIAN}")
    return found


# ======================= end of Jeff's section ===========================


def build_cohort(name: str) -> pd.DataFrame:
    """Concatenate then clean — the function the modeling notebooks import."""
    return clean_cohort(load_cohort(name), name)


if __name__ == "__main__":
    for c in COHORTS:
        df = load_cohort(c)
        print(
            f"{c:16s} -> {df.shape[0]:,} rows, {df.shape[1]} cols "
            f"(countries: {sorted(df['country'].unique())})"
        )
