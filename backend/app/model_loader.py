"""Loads the trained artifact from ml/models/<MODEL_VERSION>/ and scores one
pregnancy. Imports the shared feature function from contracts/features.py so
serving and training encode inputs identically.

TODO (backend owner): load the joblib bundle, expose predict(raw) -> (risk,
band, drivers, version). Provide a 'stub' version for early frontend work.
"""
