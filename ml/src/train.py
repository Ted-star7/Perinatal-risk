"""Train from the clean DB and save ONE versioned artifact to ml/models/.

TODO (DS): grouped CV on v001, class_weight balanced, compare logreg / random
forest / gradient boosting on PR-AUC, fit a SHAP explainer, dump
{'model','version','explainer'} as model.joblib.
"""
