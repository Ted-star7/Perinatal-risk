# Perinatal risk

Predicting perinatal death and low birth weight in Kenya and Tanzania from the
2022 DHS surveys. Moringa DSF-PT15, Group 13.

We pool the Kenya and Tanzania data, train models to rank which pregnancies are
high-risk, and serve the result in two dashboards: a **clinician** view (enter
pregnancy details → risk score, drivers, follow-up) and an **eval** view (model
accuracy for the team and the presentation).

## Layout

```
ml/
├── notebooks/
│   ├── kenya/ · tanzania/     EDA, one notebook per cohort per country
│   └── modeling/              9 model notebooks (3 cohorts x 3 algorithms)
└── src/
    ├── dataset.py             concatenate KE+TZ, clean, 80/20 split  (build_cohort)
    └── export_combined.py     write the 3 combined cohorts to CSV

contracts/                     shared definitions: cohort_config, feature_spec
db/                            Docker Postgres + seed + metrics helper + schemas
frontend/                      Angular app — clinician + eval dashboards
docs/                          KE vs TZ comparison
data/                          CSVs, git-ignored (licensed — never committed)
```

## The pipeline

```
KE + TZ cohorts ─► build_cohort() ─► combined + cleaned + 80/20 split
                                           │
                     train 3 algorithms ───┤──► best model per cohort
                                           │
                     metrics ──────────────┴──► model_metrics table ─► eval dashboard
```

- `build_cohort("perinatal")` returns the combined, cleaned data with a `split`
  column (`train`/`test`). Modeling reads from this (or from the DB — both shown
  in each notebook).
- Each of the 9 modeling notebooks trains one algorithm and saves its metrics
  with `db.metrics.save_metrics()`.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r ml/requirements.txt
# data: drop the shared CSVs into data/processed/   (see data/README.md)

# optional database (only for the dashboards):
docker compose up -d app_db clean_db
.venv/bin/pip install -r db/requirements.txt
python db/seed_combined.py        # loads the 3 combined cohorts

# frontend:
cd frontend && npm install && npm start      # http://localhost:4200
```

## Working together

`main` stays clean. You branch, open a pull request, and Teddy merges. See
[GETTING_STARTED.md](GETTING_STARTED.md) to set up, [CONTRIBUTING.md](CONTRIBUTING.md)
for the rules, and [TEAM.md](TEAM.md) for who owns what.

## What this is

A coursework and research project, not a clinical device. The model ranks risk
across a population so care can be targeted; it does not diagnose anyone, and the
follow-up text stays within standard non-diagnostic advice.
