"""Shared dataset builder for the modeling stage.

Division of work:
  - load_cohort()  — concatenates the Kenya + Tanzania files for a cohort.
                     (written; don't change the concat logic)
  - clean_cohort() — cleans the concatenated data.  TODO: Jeff.
  - SELECTED       — the columns each cohort keeps.  TODO: team (from the EDA).

Everyone imports build_cohort() so all three models train on the same combined,
cleaned data. Run `python ml/src/dataset.py` to sanity-check the concatenation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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
        raise ValueError(
            f"{name}: Kenya and Tanzania columns differ, cannot concatenate"
        )

    combined = pd.concat([ke, tz], ignore_index=True)
    return combined


# -------------------------------------------------------------------------
# TODO (team): the final columns to keep for each cohort, from the EDA.
# Leave as None to keep all columns for now.
# -------------------------------------------------------------------------
SELECTED: dict[str, list[str] | None] = {
    "perinatal": None,
    "perinatal_anc": None,
    "lbw": None,
}


def clean_cohort(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Clean the concatenated cohort.  TODO: Jeff.

    This runs AFTER concatenation, so cleaning is done once on the combined
    Kenya+Tanzania data (consistent for both countries). Put the agreed steps
    here, e.g.:
      - first_pregnancy flag + median-fill preceding_interval_m
      - drop unused raw columns
      - encode categories
    For now it returns the data unchanged.
    """
    # TODO: implement the cleaning here.
    cols = SELECTED.get(name)
    if cols is not None:
        df = df[cols]
    return df


def build_cohort(name: str) -> pd.DataFrame:
    """Concatenate then clean — the function the modeling notebooks import."""
    return clean_cohort(load_cohort(name), name)


if __name__ == "__main__":
    for c in COHORTS:
        df = load_cohort(c)
        print(f"{c:16s} -> {df.shape[0]:,} rows, {df.shape[1]} cols "
              f"(countries: {sorted(df['country'].unique())})")
