"""Write the combined, cleaned cohorts to CSV files.

Runs build_cohort() for each cohort and saves the result to data/combined/.
These files are git-ignored (licensed data), so they stay on your machine.

    python ml/src/export_combined.py
"""

from __future__ import annotations

from pathlib import Path

from ml.src.dataset import COHORTS, build_cohort

OUT = Path(__file__).resolve().parents[2] / "data" / "combined"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in COHORTS:
        df = build_cohort(name)
        path = OUT / f"combined_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  wrote {path}  ({len(df):,} rows, {df.shape[1]} cols)")


if __name__ == "__main__":
    main()
