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

tanzania/   (Tanzania squad — Caroline, Jeff, Teddy)
  eda_perinatal.ipynb
  eda_perinatal_anc.ipynb
  eda_lbw.ipynb
```

Pick one cohort in your squad and work only in that file. Each notebook loads
its own dataset from `data/processed/` and has a short overview of what to
explore.

## Modeling

```
modeling/
  checklist_baseline.ipynb   the baseline every model must beat
  perinatal_*.ipynb         3 approaches for the general perinatal cohort
  anc_*.ipynb               3 approaches for the ANC research cohort
  lbw_*.ipynb               3 approaches for the LBW cohort
  validation_shap.ipynb      current antenatal calibration, country validation and permutation importance
```

These come after EDA and are done by whoever leads modelling, on the headline
cohort. Column names and cohort definitions are in `contracts/`.

The nine algorithm notebooks document the historical research recipes. Current
antenatal releases are built with `python -m ml.src.train_antenatal_models`.
Their features are defined in `ml/src/antenatal.py` and include age when pregnancy
began, previous live births, first pregnancy, previous stillbirth, previous loss
and multiple pregnancy. LBW adds education. The clinician form is checked against
the features in the exported artifacts. Run `python -m ml.src.validate_country`
to produce the country-transfer reports used by the validation notebook.
