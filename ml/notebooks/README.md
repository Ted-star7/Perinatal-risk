# Notebooks

Split by country so two people never edit the same file. Each EDA notebook is
owned by one person. Keep outputs cleared before committing (they bloat diffs
and can leak data).

## EDA — one notebook per person

```
kenya/      (Kenya EDA squad — Jeremy, Dennis, Eglen)
  eda_perinatal.ipynb        headline cohort
  eda_perinatal_anc.ipynb    + ANC predictors
  eda_lbw.ipynb              low birth weight (weighed births)

tanzania/   (Tanzania squad — Caroline, Jeff, Tedd)
  eda_perinatal.ipynb
  eda_perinatal_anc.ipynb
  eda_lbw.ipynb
```

Pick one cohort in your squad and work only in that file. Each notebook loads
its own dataset from `data/processed/` and has a short overview of what to
explore — you write and run your own code.

## Modeling — later, shared

```
modeling/
  checklist_baseline.ipynb   the baseline every model must beat
  models.ipynb               logreg / random forest / gradient boosting, grouped CV
  validation_shap.ipynb      Kenya -> Tanzania, SHAP, calibration
```

These come after EDA and are done by whoever leads modelling, on the headline
cohort. Column names and cohort definitions are in `contracts/`.
