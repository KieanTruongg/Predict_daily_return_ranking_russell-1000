"""LambdaMART Learning-to-Rank Alpha Model using LightGBM."""
import pandas as pd
import numpy as np
from typing import List, Optional
from src.models.base_model import BaseMLAlphaModel


class LambdaMARTAlphaModel(BaseMLAlphaModel):
    """
    Alpha Model using LambdaMART (LightGBM Ranker with objective='lambdarank').
    Groups stocks by Date query groups to optimize pairwise ranking (NDCG/Rank loss).
    """
    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        random_state: int = 42
    ):
        super().__init__(name="Alpha_ML_LambdaMART")
        self.params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "random_state": random_state,
            "objective": "lambdarank",
            "n_jobs": -1
        }
        self.model = None

    def fit(self, train_df: pd.DataFrame, feature_cols: List[str], target_col: str = "target_return_rank"):
        self.feature_cols = feature_cols

        # LambdaMART requires data sorted by query group (Date)
        sorted_train = train_df.sort_values("Date").reset_index(drop=True)
        X = sorted_train[feature_cols].fillna(0.0)
        # Convert percentile rank to discrete relevance integer labels (e.g., 0 to 4 quintiles)
        y_int = (sorted_train[target_col].fillna(0.5) * 4).round().astype(int)
        query_groups = sorted_train.groupby("Date", sort=False).size().values

        try:
            import lightgbm as lgb
            self.model = lgb.LGBMRanker(**self.params)
            self.model.fit(X, y_int, group=query_groups)
        except ImportError:
            try:
                from sklearn.linear_model import Ridge
                self.model = Ridge(alpha=10.0)
                self.model.fit(X, sorted_train[target_col].fillna(0.5))
            except ImportError:
                print("[Info] Neither lightgbm nor scikit-learn installed. Using NumPy ranking linear fallback.")
                y_target = sorted_train[target_col].fillna(0.5).values
                X_mat = np.hstack([np.ones((len(X), 1)), X.values])
                alpha_reg = 10.0 * np.eye(X_mat.shape[1])
                alpha_reg[0, 0] = 0.0
                weights = np.linalg.solve(X_mat.T @ X_mat + alpha_reg, X_mat.T @ y_target)
                class _NumpyRankModel:
                    def __init__(self, w):
                        self.w = w
                    def predict(self, x):
                        x_mat = np.hstack([np.ones((len(x), 1)), x.values])
                        return x_mat @ self.w
                self.model = _NumpyRankModel(weights)

        self.is_fitted = True
        return self

    def predict(self, test_df: pd.DataFrame) -> pd.Series:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted yet.")

        X = test_df[self.feature_cols].fillna(0.0)
        preds = self.model.predict(X)
        return pd.Series(preds, index=test_df.index)
