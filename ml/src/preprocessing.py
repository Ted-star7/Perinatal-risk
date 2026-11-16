"""Fold-fitted pregnancy-interval handling shared by calibration and validation."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class BirthIntervalImputer(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = len(X.columns)
        known = X["first_pregnancy"].eq(0) & X["preceding_interval_m"].notna()
        if "interval_imputed" in X:
            known &= X["interval_imputed"].eq(0)
        self.median_ = float(X.loc[known, "preceding_interval_m"].median())
        if not np.isfinite(self.median_):
            raise ValueError("The training fold has no known birth intervals.")
        return self

    def transform(self, X):
        result = X.copy()
        first = result["first_pregnancy"].eq(1)
        unknown = result["preceding_interval_m"].isna()
        if "interval_imputed" in result:
            unknown |= result["interval_imputed"].eq(1)
        result.loc[unknown & ~first, "preceding_interval_m"] = self.median_
        result.loc[first, "preceding_interval_m"] = np.nan
        return result

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_
