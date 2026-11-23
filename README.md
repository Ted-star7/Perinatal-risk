# Afya Nova

**Predicting perinatal death and low birth weight in Kenya and Tanzania from the 2022 DHS surveys.**
Moringa School, DSF-PT15 — Group 13.

We pool the Kenya and Tanzania survey data, train models to rank which pregnancies
are high-risk, and serve the result through a clinician-facing web app backed by a
shared database.

- **Primary outcome** — perinatal death (stillbirth, or death in the first 7 days).
- **Secondary outcome** — low birth weight (under 2,500 g).
- **ANC cohort** — the perinatal cohort with antenatal-care predictors added, used
  as a research comparison.

## Live demo

| | URL |
|---|---|
| Clinician app | https://perinatal-ui.onrender.com |
| API (docs at `/docs`) | https://perinatal-api.onrender.com |

The app has two views: a **Triage** view (enter pregnancy details → a research risk
estimate, the high-risk checklist, and suggested follow-up) and a **Model performance**
view (how each model scores, for the team and the presentation). Registrations and saved
assessments are multi-tenant — each clinic sees only its own records.

## Where the project landed

It grew in two stages:

1. **Research** — nine modeling notebooks (3 cohorts × logistic regression / random
   forest / gradient boosting), all pooling Kenya + Tanzania on one cluster-based
   80/20 split. A formal audit on 17 Nov 2026 re-ran every notebook on a pinned
   scikit-learn stack with fresh kernels; the scores, confusion counts and the
   sklearn-version comparison are in
   [docs/notebook-results-2026-11-17.md](docs/notebook-results-2026-11-17.md).
2. **Product** — the research recipes were turned into calibrated, packaged serving
   models (`ml/src/train_antenatal_models.py` → `package_release.py`) that the API
   loads to score real assessments, plus the clinician + evaluation dashboards.

Headline finding: the signal in DHS pregnancy-time fields is genuinely weak for
perinatal death (ROC-AUC ~0.60), stronger for low birth weight (~2× the random
baseline). By mean cross-validated PR-AUC the best model is **gradient boosting**
for perinatal and LBW, and **logistic regression** for ANC — but every model still
catches more true cases than the checklist at the same alert budget.

## Layout

```
ml/
├── notebooks/
│   ├── kenya/ · tanzania/     EDA, one notebook per cohort per country
│   └── modeling/              9 research notebooks (3 cohorts × 3 algorithms)
└── src/
    ├── dataset.py             concatenate KE+TZ, clean, 80/20 split  (build_cohort)
    ├── antenatal.py           antenatal predictor definitions
    ├── train_antenatal_models.py  select, calibrate and evaluate the serving models
    ├── package_release.py     verify and package the fitted releases
    └── export_combined.py     write the 3 combined cohorts to CSV

backend/                       FastAPI — auth, assessments, shared /metrics
frontend/                      Angular — Triage + Model-performance dashboards
contracts/                     shared definitions: cohort_config, feature_spec
db/                            Postgres schema, seed, and the metrics helper
docs/                          KE vs TZ comparison + the 17-Nov notebook audit
data/                          CSVs, git-ignored (licensed — never committed)
```

## The pipeline

```
KE + TZ cohorts ─► build_cohort() ─► combined + cleaned + 80/20 split
                                           │
                     train 3 algorithms ───┤──► best model per cohort
                                           │
                     metrics ──────────────┴──► model_metrics ─► eval dashboard
```

- `build_cohort("perinatal")` returns the combined, cleaned data with a `split`
  column. Each modeling notebook reads from this (or from the DB — both shown).
- `db.metrics.save_metrics()` publishes a model's results to the shared `/metrics`
  endpoint, so every teammate's numbers collect in one hosted database and the
  eval dashboard ranks them per cohort.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r ml/requirements.txt
# data: drop the shared CSVs into data/processed/   (see data/README.md)

# database + assessment API (packaged models ship in the repo):
docker compose up -d --build

# frontend:
cd frontend && npm ci && npm start      # http://localhost:4200
```

Windows (Docker + WSL) walkthrough: [RUNNING.md](RUNNING.md).

## Contributors

Group 13 — six of us, every stage a genuine team effort. We split into Kenya and
Tanzania squads for the data work, then regrouped around the build. **Jeff Waweru
led the team overall**, steering the project across EDA, modeling and delivery and
keeping all three cohorts moving in step.

| Person | GitHub | Role & contributions |
|--------|--------|----------------------|
| **Jeff Waweru** | [`Kirukuu`](https://github.com/Kirukuu) | **Overall Team Lead** — guided the whole team through EDA, modeling and delivery. Tanzania ANC EDA; ANC & LBW gradient boosting; tuned the logistic-regression models on the shared cluster-grouped CV folds. |
| **Teddy Kibuthu** | [`Ted-star7`](https://github.com/Ted-star7) | Scrum master & integrator (reviews and merges into `main`). Tanzania & Kenya perinatal EDA; perinatal gradient boosting; FastAPI backend, database, Render hosting, shared metrics endpoint, and the Triage UI. |
| **Dennis Mwikya** | [`des-data`](https://github.com/des-data) | Kenya ANC EDA; ANC random forest; designed and built the evaluation dashboard; the shared-metrics proxy and notebook save-cell wiring. |
| **Jeremy Mwangi** | [`mwangi54`](https://github.com/mwangi54) | Kenya LBW EDA; perinatal & LBW random forest, with bootstrap confidence intervals and calibration — the most statistically careful of the notebooks. |
| **Eglen Nyangasi** | [`eglen-nyangasi`](https://github.com/eglen-nyangasi) | Helped set up the database (Docker Postgres + connecting the team); perinatal & ANC logistic regression; Kenya EDA support. |
| **Caroline Rotich** | [`carolnerotich`](https://github.com/carolnerotich) | Tanzania LBW EDA; LBW logistic regression, with clear plain-language write-ups of the results. |

Everyone contributed across EDA, modeling and the shared `contracts/` definitions.
`main` stays clean: each person branches, opens a pull request, and Teddy merges.
See [GETTING_STARTED.md](GETTING_STARTED.md) to set up, [CONTRIBUTING.md](CONTRIBUTING.md)
for the rules, and [TEAM.md](TEAM.md) for who owns which folder.

## What this is

A coursework and research project, not a clinical device. The model ranks risk
across a population so care can be targeted; it does not diagnose anyone, and the
follow-up text stays within standard, non-diagnostic advice. The DHS microdata is
licensed and is never committed to this repository.
