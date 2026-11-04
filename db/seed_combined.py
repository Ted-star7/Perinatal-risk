"""Load the combined, cleaned cohorts into the clean DB.

Runs ml/src/dataset.build_cohort() for each cohort (concatenate KE+TZ, clean,
split) and writes the result as a `combined_<cohort>` table. This is the
modeling-ready data — what the backoffice / eval portal reads.

    python db/seed_combined.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.src.dataset import COHORTS, build_cohort  # noqa: E402

CLEAN_DB_URL = os.getenv(
    "CLEAN_DB_URL",
    "postgresql+psycopg://readonly:readonly@localhost:5433/perinatal_clean",
)


def main() -> None:
    engine = create_engine(CLEAN_DB_URL)
    for name in COHORTS:
        df = build_cohort(name)
        table = f"combined_{name}"
        df.to_sql(table, engine, if_exists="replace", index=False)
        n_test = int((df["split"] == "test").sum()) if "split" in df else 0
        print(f"  loaded {table}: {len(df):,} rows, {df.shape[1]} cols "
              f"({n_test:,} in test split)")

    with engine.connect() as con:
        tables = con.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name LIKE 'combined_%' "
                "ORDER BY table_name"
            )
        ).fetchall()
    print("\ncombined tables in clean DB:", [t[0] for t in tables])


if __name__ == "__main__":
    main()
