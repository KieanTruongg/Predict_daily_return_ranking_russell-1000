"""Base class for Machine Learning Alpha Models (Phase 3)."""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


class BaseMLAlphaModel(ABC):
    """
    Abstract interface for ML/DL Alpha models.
    Produces stock ranking scores or predicted forward returns.
    """
    def __init__(self, name: str):
        self.name = name
        self.is_fitted = False
        self.feature_cols: List[str] = []

    @abstractmethod
    def fit(self, train_df: pd.DataFrame, feature_cols: List[str], target_col: str = "target_return_rank"):
        """Fits model on training panel DataFrame."""
        pass

    @abstractmethod
    def predict(self, test_df: pd.DataFrame) -> pd.Series:
        """Outputs raw prediction score for each (Date, Ticker) row."""
        pass

    def predict_cross_sectional_rank(self, test_df: pd.DataFrame) -> pd.Series:
        """
        Generates cross-sectional percentile rank [0, 1] per Date.
        """
        preds = self.predict(test_df)
        df_temp = test_df[["Date", "Ticker"]].copy()
        df_temp["score"] = preds
        ranks = df_temp.groupby("Date")["score"].rank(pct=True)
        return ranks
