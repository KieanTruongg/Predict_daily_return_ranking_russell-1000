"""Model and Data Drift Monitoring (Phase 8).
Tracks distribution shifts in input features and degradation in strategy Rank IC/Sharpe.
"""
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np


class DriftDetector:
    """
    Lightweight monitor for Data Drift (feature distribution shifts)
    and Model Performance Drift (Rank IC degradation).
    """
    def __init__(self, p_value_threshold: float = 0.05, ic_warning_threshold: float = 0.01):
        self.p_value_threshold = p_value_threshold
        self.ic_warning_threshold = ic_warning_threshold

    def check_feature_drift(
        self,
        reference_features: pd.DataFrame,
        current_features: pd.DataFrame,
        feature_cols: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Runs Kolmogorov-Smirnov (KS) test or summary comparison on feature distributions.
        """
        drift_report = {}
        for col in feature_cols:
            if col in reference_features.columns and col in current_features.columns:
                ref = reference_features[col].dropna()
                cur = current_features[col].dropna()

                ref_mean, cur_mean = ref.mean(), cur.mean()
                ref_std, cur_std = ref.std(), cur.std()

                # Normalized mean difference
                mean_shift = abs(cur_mean - ref_mean) / (ref_std + 1e-6)

                drift_report[col] = {
                    "ref_mean": float(ref_mean),
                    "cur_mean": float(cur_mean),
                    "mean_shift_zscore": float(mean_shift),
                    "is_drifted": bool(mean_shift > 2.0)  # > 2 standard deviations shift
                }
        return drift_report

    def check_performance_degradation(self, rolling_ic_series: pd.Series) -> Dict[str, Any]:
        """
        Detects if trailing 30-day Rank IC drops below threshold.
        """
        recent_ic = rolling_ic_series.iloc[-30:].mean() if len(rolling_ic_series) >= 30 else rolling_ic_series.mean()
        needs_retrain = bool(recent_ic < self.ic_warning_threshold)

        return {
            "recent_30d_mean_ic": float(recent_ic),
            "threshold": self.ic_warning_threshold,
            "trigger_retrain": needs_retrain
        }
