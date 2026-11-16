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
  model_comparison.ipynb     TP/FP/TN/FN, recall, precision and separate experiment profiles
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

`model_comparison.ipynb` separates the historical export experiment from the
antenatal release experiment. It reconstructs every candidate using the recorded
training-CV settings, verifies its results against the frozen export report, and
shows confusion matrices against the checklist at equal flag capacity. Selected
release models are calibrated; the other recorded candidates are not. Each row
states this calibration status. No new clinical threshold or serving winner is
chosen. The notebook keeps team nominations separate from observed test rankings.

To generate the aggregate reports from the repository root:

```bash
python -m ml.src.compare_classification --profile antenatal
python -m ml.src.compare_classification --profile historical
```

The reports are written to ignored `ml/models/comparisons/`. Historical comparison
requires the original local exports. Both profiles require the licensed processed
CSVs. These commands do not publish metrics or change any fitted release.
