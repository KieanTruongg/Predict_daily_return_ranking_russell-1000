"""XGBoost Alpha Model for Cross-Sectional Ranking Prediction."""
import pandas as pd
import numpy as np
from typing import List, Optional
from src.models.base_model import BaseMLAlphaModel


class XGBoostAlphaModel(BaseMLAlphaModel):
    """
    Alpha Model using XGBoost Gradient Boosted Trees.
    Hyperparameters: max_depth, learning_rate, n_estimators, subsample, colsample_bytree.
    """
    def __init__(
        self,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        n_estimators: int = 100,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42
    ):
        super().__init__(name="Alpha_ML_XGBoost")
        self.params = {
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "n_estimators": n_estimators,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": -1
        }
        self.model = None

    def fit(self, train_df: pd.DataFrame, feature_cols: List[str], target_col: str = "target_return_rank"):
        self.feature_cols = feature_cols
        X = train_df[feature_cols].fillna(0.0)
        y = train_df[target_col].fillna(0.5)

        try:
            import xgboost as xgb
            self.model = xgb.XGBRegressor(**self.params)
            self.model.fit(X, y)
        except ImportError:
            try:
                from sklearn.linear_model import Ridge
                self.model = Ridge(alpha=1.0)
                self.model.fit(X, y)
            except ImportError:
                print("[Info] Neither xgboost nor scikit-learn installed. Using NumPy OLS/Ridge fallback.")
                # w = (X^T X + alpha I)^-1 X^T y
                X_mat = np.hstack([np.ones((len(X), 1)), X.values])
                alpha_reg = 1.0 * np.eye(X_mat.shape[1])
                alpha_reg[0, 0] = 0.0  # don't penalize bias
                weights = np.linalg.solve(X_mat.T @ X_mat + alpha_reg, X_mat.T @ y.values)
                class _NumpyLinearModel:
                    def __init__(self, w):
                        self.w = w
                    def predict(self, x):
                        x_mat = np.hstack([np.ones((len(x), 1)), x.values])
                        return x_mat @ self.w
                self.model = _NumpyLinearModel(weights)

        self.is_fitted = True
        return self

    def predict(self, test_df: pd.DataFrame) -> pd.Series:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted yet.")

        X = test_df[self.feature_cols].fillna(0.0)
        preds = self.model.predict(X)
        return pd.Series(preds, index=test_df.index)
