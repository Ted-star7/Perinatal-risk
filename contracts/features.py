"""The single feature function shared by training and serving.

Both ml/train.py and the backend import build_features() so a clinician's
web-form input is encoded exactly the way the training data was. If a
predictor's coding changes, it changes HERE once — never in two places.

Column names follow the processed cohorts (see contracts/feature_spec.yaml):
maternal_age, prior_pregnancies, prior_live_births, prior_stillbirth,
prior_loss, preceding_interval_m, multiple, education, wealth_quintile,
residence, region, told_high_bp (+ anc_visits, first_anc_month, bp_measured,
urine_tested, blood_tested, iron_tablets in the *_anc cohorts).

TODO (integrator + DS together, this is the shared truth):
  - RawInput dataclass matching the predictor columns above
  - build_features(raw) -> dict[str, float]   (encode categories, handle blanks)
  - checklist_flag(raw) -> bool               (the high-risk baseline to beat)
  - FEATURE_ORDER                             (stable column order for the model)
"""
