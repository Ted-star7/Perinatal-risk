# Perinatal risk

Predicting perinatal death and low birth weight in Kenya and Tanzania from the
2022 DHS surveys. Moringa DSF-PT15, Group 13.

We train on the Kenya DHS and validate, unchanged, on Tanzania. The trained
model is served behind a web app where a clinician enters what's known during
pregnancy and gets back a risk score, the factors driving it, and a short
guideline-safe follow-up note. Every use is recorded so we can judge the tool
in practice.

This repo is the scaffold: the folders, the agreed definitions, and a
placeholder file in each spot saying what goes there and who owns it. We fill
it in stage by stage (see the build order below).

## Layout

- `ml/` — the data science work: notebooks for EDA and cleaning, plus the
  training and evaluation code. Runs offline. Its output is one versioned
  model file in `ml/models/`.
- `backend/` — the FastAPI service. Loads the trained model and answers
  requests (`/predict`, `/recommend`, `/eval`). It never trains.
- `frontend/` — the Angular app. Two parts: the clinical page (enter details →
  risk → recommendation → feedback) and the eval page (accuracy, calibration
  and SHAP charts for the presentation).
- `contracts/` — the definitions everyone shares, so no two of us drift apart:
  the feature list, the cohort rules, the one feature function, and the API
  schema. Changes here are reviewed before anything else.
- `db/` — Postgres: `clean/` holds the cleaned cohorts (read-only), `app/`
  holds predictions, recommendations and clinician feedback.
- `data/` — where the DHS files sit locally. They are licensed and **never**
  committed; the team shares them separately.

## How the model reaches the app

`ml/` produces `ml/models/vX.Y.Z/model.joblib`. The backend loads that file —
that's the whole handoff. The only code both sides share is
`contracts/features.py`, so the form inputs are encoded exactly the way the
training data was, and the score a clinician sees matches what we trained.

## Build order

Each step has to pass before the next builds on it.

1. Scaffold — repo clones, layout agreed. 
2. EDA and cleaning, per squad → cleaned cohorts land in the clean DB.
   Check: the weighted Kenya stillbirth rate comes out at 15.1 per 1,000,
   matching the published KDHS figure.
3. Checklist baseline + models (logistic regression, random forest, gradient
   boosting, grouped CV on the survey cluster) → one model file. Check: it
   beats the checklist on PR-AUC and still holds on Tanzania.
4. Backend wired up → serves the model, logs every call, adds the grounded
   recommendation and the feedback table.
5. Eval page → accuracy, calibration and SHAP charts.
6. Clinical page → the input form, the result, and recording each use.

## Working together

`main` stays clean and demo-able. No one pushes to it directly — you branch,
open a pull request, and Tedd merges. The rules are in
[CONTRIBUTING.md](CONTRIBUTING.md); who owns what is in [TEAM.md](TEAM.md).

## A note on what this is

This is a research and coursework project, not a clinical device. The model
ranks risk across a population so care can be targeted; it does not diagnose
anyone. The recommendations stay inside standard, non-diagnostic advice
(keep attending ANC, get BP and urine checked, take iron, seek referral if
flagged) — nothing that reads as a diagnosis or prescription.
