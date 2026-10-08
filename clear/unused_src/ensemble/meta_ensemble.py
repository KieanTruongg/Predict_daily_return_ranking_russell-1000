"""ML Meta-Alpha Ensemble (Phase 4).
Combines XGBoost, LambdaMART, and LSTM predictions into a unified Meta-Alpha.
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class MLAlphaEnsemble:
    """
    Aggregates predictions from multiple ML/DL models (XGBoost, LambdaMART, LSTM).
    Supports:
    - Equal Weight
    - Inverse Volatility
    - Stacking (Ridge Meta-Model)
    """
    def __init__(self, method: str = "equal_weight"):
        self.method = method
        self.meta_model = None

    def combine_predictions(
        self,
        pred_dict: Dict[str, pd.Series],
        test_df: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Takes prediction Series from each model and outputs a combined cross-sectional rank table.
        """
        combined = pd.DataFrame(index=test_df.index)
        combined["Date"] = test_df["Date"]
        combined["Ticker"] = test_df["Ticker"]

        model_names = list(pred_dict.keys())

        if self.method == "equal_weight":
            w = 1.0 / len(model_names)
            combined["meta_score"] = 0.0
            for name in model_names:
                # Rank predictions cross-sectionally per model first
                temp = pd.DataFrame({"Date": test_df["Date"], "score": pred_dict[name]})
                ranked_score = temp.groupby("Date")["score"].rank(pct=True)
                combined["meta_score"] += ranked_score * w

        elif self.method == "custom" and weights is not None:
            combined["meta_score"] = 0.0
            for name, w in weights.items():
                temp = pd.DataFrame({"Date": test_df["Date"], "score": pred_dict[name]})
                ranked_score = temp.groupby("Date")["score"].rank(pct=True)
                combined["meta_score"] += ranked_score * w

        # Final cross-sectional Meta Rank [0, 1]
        combined["meta_rank"] = combined.groupby("Date")["meta_score"].rank(pct=True)
        return combined
