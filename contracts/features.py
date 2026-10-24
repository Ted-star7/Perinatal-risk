"""The single feature function shared by training and serving.

Both ml/train.py and the backend import build_features() so a clinician's
web-form input is encoded exactly the way the training data was. If a
predictor's coding changes, it changes HERE once — never in two places.

TODO (integrator + DS together, this is the shared truth):
  - RawInput dataclass matching contracts/feature_spec.yaml
  - build_features(raw) -> dict[str, float]
  - checklist_flag(raw) -> bool   (the high-risk baseline to beat)
  - FEATURE_ORDER   (stable column order for the model)
"""
