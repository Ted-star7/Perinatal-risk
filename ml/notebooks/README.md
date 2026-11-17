# Notebooks

Split by country so two people never edit the same file. Each EDA notebook is
owned by one person. Keep outputs cleared before committing (they bloat diffs
and can leak data).

## Execution environments

Use Python 3.12 and the pinned current notebook environment:

```bash
python3.12 -m venv .venv-notebooks
.venv-notebooks/bin/pip install -r ml/requirements-notebooks.txt
.venv-notebooks/bin/python -m ipykernel install --user --name perinatal-notebooks --display-name "Perinatal notebooks (sklearn 1.9.1)"
```

Select that kernel for all 19 notebooks. The numerical stack matches the
antenatal training and serving environment. The perinatal GB grid search now
explicitly balances fitting while keeping validation AP and ROC-AUC unweighted,
consistent with the other eight algorithms. This prevents automatic weight
forwarding from changing the meaning of its CV scores in newer sklearn versions.

For an older-result reproduction only, create a separate `.venv-research` and
install `ml/requirements-research-legacy.txt` (scikit-learn 1.5.2). That environment
supports the six country EDA notebooks, pooled analysis, checklist baseline and
nine original algorithm notebooks. Do not use it to load the API's 1.9.1 joblib
files in `model_comparison` or `validation_shap`.

Do not mix results between versions. With identical source, data and split,
ANC Random Forest produced test AP 0.088694 under 1.5.2 and 0.091858 under 1.9.1.
Other forest results and selected configurations change too. The audit report
records both versions, with the current stack as the main comparison.

Record library versions, source commit, data hashes and decision rule with any
new publication. Run each notebook from its own directory in a fresh kernel,
with all `SAVE_TO_DB` / `SAVE_METRICS` flags off during review. Executed copies
belong under ignored `ml/notebook-runs/`; they can contain licensed survey rows
and must not be committed or shared publicly.

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
