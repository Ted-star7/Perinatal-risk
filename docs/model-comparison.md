# Classification comparison — 16 November 2026

These aggregate results reproduce the local frozen export reports. They are not new clinical validation. The comparison does not alter serving models or publish metrics.

The original notebook experiments and the antenatal releases have different feature sets and checklists. Keep the profile explicit when discussing a winning model. The original notebooks have some cleared outputs; this comparison reconstructs the exported recipes rather than claiming to recover every original notebook run.

A read-only check of the hosted database on 16 November 2026 confirms these highest **stored test PR-AUC** values:

| Hosted cohort | Highest stored test PR-AUC | Value |
|---|---|---:|
| LBW | Gradient boosting | 0.1590 |
| Perinatal | Random forest | 0.0731 |
| Perinatal ANC | Random forest | 0.0919 |

These match the team’s stated list. They describe the existing hosted notebook submissions, not the algorithms currently serving clinician predictions. The hosted values were not changed during this check. The local dashboard was populated with the newer antenatal evaluation metrics; that local publication did not update the hosted database.

The shared metrics table stores one row per cohort/algorithm, without experiment or decision-rule provenance. It does not persist TP/FP/TN/FN or the flag count. Do not reconstruct a confusion matrix from rounded hosted recall or assume a historic submission matches a newer refit. The latest notebook source intends equal-checklist flag capacity, but the hosted rows do not prove which revision or rule produced each submitted value.

The export-based comparisons below verify their own frozen reports and keep the historical and antenatal experiments separate. The historical export refits differ from some hosted submissions. Their matrices must not be presented as the confusion matrices of those hosted runs. The comparison does not modify the shared table or its schema.

Each approach flags exactly as many held-out records as its profile’s checklist. This is a batch ranking evaluation, with stable row order breaking ties; it is not a deployable probability cutoff. TP/FP/TN/FN require known outcomes. No individual pregnancy can be labelled a true positive before its outcome is observed.

In these frozen reports, the selected release was calibrated and the other candidates were not. Calibration status is explicit below. Training cross-validation selected the release; the highest observed test metric is descriptive and does not retroactively choose the deployment model.

## Historical experiment

| Cohort | Approach | Calibrated | Training CV AP | Test AP | Test ROC-AUC | TP | FP | TN | FN | Recall | Precision |
|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| perinatal | Logistic regression | No | 0.0793 | 0.0723 | 0.5989 | 129 | 2679 | 3290 | 91 | 58.6% | 4.6% |
| perinatal | Random forest | No | 0.0809 | 0.0731 | 0.5998 | 124 | 2684 | 3285 | 96 | 56.4% | 4.4% |
| perinatal | Gradient boosting | Yes | 0.0816 | 0.0742 | 0.6064 | 130 | 2678 | 3291 | 90 | 59.1% | 4.6% |
| perinatal_anc | Logistic regression | Yes | 0.0817 | 0.0849 | 0.6324 | 66 | 1391 | 1811 | 42 | 61.1% | 4.5% |
| perinatal_anc | Random forest | No | 0.0708 | 0.0919 | 0.6313 | 70 | 1387 | 1815 | 38 | 64.8% | 4.8% |
| perinatal_anc | Gradient boosting | No | 0.0794 | 0.0786 | 0.6218 | 63 | 1394 | 1808 | 45 | 58.3% | 4.3% |
| lbw | Logistic regression | No | 0.1933 | 0.1429 | 0.6127 | 76 | 694 | 1025 | 54 | 58.5% | 9.9% |
| lbw | Random forest | No | 0.1978 | 0.1370 | 0.6263 | 79 | 691 | 1028 | 51 | 60.8% | 10.3% |
| lbw | Gradient boosting | Yes | 0.1991 | 0.1590 | 0.6182 | 73 | 697 | 1022 | 57 | 56.2% | 9.5% |

- `perinatal`: 6,189 test records, 220 events; every approach flags 2,808. Checklist TP=115, FP=2693, TN=3276, FN=105. Frozen release: Gradient boosting; model SHA-256 `119b83856382bd52a54ef372978bd7a3a86a2a283cd86d7984c9d78196bcce3f`.
- `perinatal_anc`: 3,310 test records, 108 events; every approach flags 1,457. Checklist TP=49, FP=1408, TN=1794, FN=59. Frozen release: Logistic regression; model SHA-256 `2d9178e92396b99c3490bcb7bd950fded486e0ba9583ecea15b8b0137e020b3a`.
- `lbw`: 1,849 test records, 130 events; every approach flags 770. Checklist TP=69, FP=701, TN=1018, FN=61. Frozen release: Gradient boosting; model SHA-256 `fae687b490436cedab75be5b4cdee477f45f5cf9256fceb644b59ae1524f8e08`.

## Antenatal experiment

| Cohort | Approach | Calibrated | Training CV AP | Test AP | Test ROC-AUC | TP | FP | TN | FN | Recall | Precision |
|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| perinatal | Logistic regression | Yes | 0.0794 | 0.0721 | 0.5999 | 109 | 2062 | 3907 | 111 | 49.5% | 5.0% |
| perinatal | Random forest | No | 0.0763 | 0.0746 | 0.5913 | 104 | 2067 | 3902 | 116 | 47.3% | 4.8% |
| perinatal | Gradient boosting | No | 0.0778 | 0.0646 | 0.5814 | 99 | 2072 | 3897 | 121 | 45.0% | 4.6% |
| perinatal_anc | Logistic regression | Yes | 0.0753 | 0.0808 | 0.6212 | 52 | 1090 | 2112 | 56 | 48.1% | 4.6% |
| perinatal_anc | Random forest | No | 0.0558 | 0.0780 | 0.5925 | 50 | 1092 | 2110 | 58 | 46.3% | 4.4% |
| perinatal_anc | Gradient boosting | No | 0.0687 | 0.0650 | 0.5966 | 55 | 1087 | 2115 | 53 | 50.9% | 4.8% |
| lbw | Logistic regression | No | 0.1838 | 0.1692 | 0.6344 | 65 | 527 | 1192 | 65 | 50.0% | 11.0% |
| lbw | Random forest | Yes | 0.1914 | 0.1436 | 0.6525 | 64 | 528 | 1191 | 66 | 49.2% | 10.8% |
| lbw | Gradient boosting | No | 0.1852 | 0.1544 | 0.6542 | 68 | 524 | 1195 | 62 | 52.3% | 11.5% |

- `perinatal`: 6,189 test records, 220 events; every approach flags 2,171. Checklist TP=94, FP=2077, TN=3892, FN=126. Frozen release: Logistic regression; model SHA-256 `494b30029578e1045f15c33ecea27af58bc652c8d0a7de595b20867a8cdda1fe`.
- `perinatal_anc`: 3,310 test records, 108 events; every approach flags 1,142. Checklist TP=46, FP=1096, TN=2106, FN=62. Frozen release: Logistic regression; model SHA-256 `65f80541e82bf76389dd514b0b64c94f76ae97bcced987b623c971fd6b709960`.
- `lbw`: 1,849 test records, 130 events; every approach flags 592. Checklist TP=53, FP=539, TN=1180, FN=77. Frozen release: Random forest; model SHA-256 `ce73d39081d9191fd8e1420ce78e34f0e793760a36cd32f734396f61c1de2667`.

## Choosing the criterion

For screening at a fixed review workload, compare recall/TP and missed cases/FN at equal flag capacity, alongside precision and false positives. PR-AUC/AP summarizes ranking across precision-recall tradeoffs. ROC-AUC is supporting ranking evidence. Probability estimates also need calibration assessment. Choosing a metric depends on the intended decision and capacity, not just whether the label is LBW or perinatal death.

Agree the model-selection objective and action policy before looking at final test rankings. Fit/tune on training or validation folds, freeze the decision rule, and evaluate on untouched test records. Independent prospective clinical validation and clinical action thresholds remain pending.

Run `ml/notebooks/modeling/model_comparison.ipynb` to inspect the matrices and change experiment profiles. The shared implementation is `ml/src/compare_classification.py`. Aggregate JSON reports are under ignored `ml/models/comparisons/`; licensed data and row-level predictions are not included here.

Sources: [scikit-learn evaluation metrics](https://scikit-learn.org/stable/modules/model_evaluation.html), [decision-threshold guidance](https://scikit-learn.org/stable/modules/classification_threshold.html).
