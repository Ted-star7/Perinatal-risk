"""Load the cleaned cohort CSVs into the clean Postgres database.

Run after `docker compose up -d app_db clean_db` and after the six CSVs are in
data/processed/. Creates one table per cohort (replacing it if it already
exists), so you can re-run this safely.

    python db/seed.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Connect to the clean DB. Default matches docker-compose (host port 5433).
CLEAN_DB_URL = os.getenv(
    "CLEAN_DB_URL",
    "postgresql+psycopg://readonly:readonly@localhost:5433/perinatal_clean",
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

COHORTS = [
    "ke_perinatal", "ke_perinatal_anc", "ke_lbw",
    "tz_perinatal", "tz_perinatal_anc", "tz_lbw",
]


def main() -> None:
    engine = create_engine(CLEAN_DB_URL)
    for name in COHORTS:
        csv = PROCESSED / f"{name}.csv"
        if not csv.exists():
            print(f"  SKIP {name}: {csv} not found")
            continue
        df = pd.read_csv(csv)
        df.to_sql(name, engine, if_exists="replace", index=False)
        print(f"  loaded {name}: {len(df):,} rows, {df.shape[1]} cols")

    with engine.connect() as con:
        tables = con.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            )
        ).fetchall()
    print("\ntables in clean DB:", [t[0] for t in tables])


if __name__ == "__main__":
    main()
