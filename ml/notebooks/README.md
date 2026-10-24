# Notebooks

One notebook per stage. Keep outputs cleared before committing (they bloat
diffs and can leak data). Notebooks explore and explain; the reusable code
lives in `ml/src/`.

- `01_eda.ipynb` — shape, missingness, distributions, outcome rates
- `02_cleaning.ipynb` — recode missing (98, 99), derive variables
- `03_cohort_build.ipynb` — build the three cohorts; **gate**: KE weighted
  stillbirth rate = 15.1/1000
- `04_baseline_checklist.ipynb` — score the high-risk checklist
- `05_models.ipynb` — logreg / random forest / gradient boosting, grouped CV
- `06_validation_shap.ipynb` — Kenya metrics, transport to Tanzania, SHAP,
  calibration

Create them as you reach each stage. Add this to `.gitignore` locally if you
prefer to keep heavy notebooks out until they're clean:
`git add --renormalize` and clear outputs first.
