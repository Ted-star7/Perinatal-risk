"""Seed the combined cohort tables into the app database on startup.

Runs ml.src.dataset.build_cohort() for each cohort and writes it as a
`combined_<cohort>` table — so the research data lives in the same database as
the clinics/doctors/predictions. Runs once (skips if already seeded), and skips
gracefully if the data CSVs aren't available (e.g. a teammate without the data).
"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def seed_cohorts(engine: Engine) -> None:
    try:
        if inspect(engine).has_table("combined_perinatal"):
            print("[seed] cohort tables already present — skipping")
            return

        from ml.src.dataset import COHORTS, build_cohort

        for name in COHORTS:
            df = build_cohort(name)
            df.to_sql(f"combined_{name}", engine, if_exists="replace", index=False)
            print(f"[seed] combined_{name}: {len(df):,} rows")
    except Exception as exc:  # data or deps missing — app still runs
        print(f"[seed] skipped cohort seeding ({type(exc).__name__}: {exc})")
