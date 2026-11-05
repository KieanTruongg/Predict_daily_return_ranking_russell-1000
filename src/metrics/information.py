"""Information Coefficient (IC) and Rank IC metrics."""
from typing import Dict
import pandas as pd
import numpy as np


def compute_daily_ic_series(
    signals_or_weights: pd.DataFrame,
    forward_returns: pd.DataFrame,
    method: str = "spearman"
) -> pd.Series:
    """
    Computes cross-sectional Information Coefficient (IC) for each trading day.
    - 'spearman': Rank IC (correlation of ranks) - Primary metric for ranking models
    - 'pearson': Linear IC
    """
    common_dates = signals_or_weights.index.intersection(forward_returns.index)
    ic_dict = {}

    for date in common_dates:
        s_row = signals_or_weights.loc[date]
        r_row = forward_returns.loc[date]

        # Valid non-nan pairs
        mask = (~s_row.isna()) & (~r_row.isna())
        if mask.sum() < 5:  # Need minimum cross-section size
            continue

        s_valid = s_row[mask]
        r_valid = r_row[mask]

        try:
            if method == "spearman":
                corr = s_valid.rank().corr(r_valid.rank())
            else:
                corr = s_valid.corr(r_valid)

            if not pd.isna(corr):
                ic_dict[date] = float(corr)
        except Exception:
            pass

    return pd.Series(ic_dict)


def calculate_ic_summary(ic_series: pd.Series) -> Dict[str, float]:
    """
    Summarizes daily IC distribution:
    - Mean IC: average predictive strength (> 0.03 is considered good in equity quant research)
    - IC Std: stability of predictive strength
    - ICIR (Information Ratio): Mean IC / Std IC (> 0.5 is solid, > 1.0 is exceptional)
    - Positive IC Ratio: percentage of days with positive IC
    """
    clean_ic = ic_series.dropna()
    if len(clean_ic) < 2:
        return {"mean_ic": 0.0, "ic_std": 0.0, "icir": 0.0, "positive_ic_ratio": 0.0}

    mean_ic = float(clean_ic.mean())
    std_ic = float(clean_ic.std())
    icir = float(mean_ic / std_ic) if std_ic > 1e-8 else 0.0
    pos_ratio = float((clean_ic > 0).mean())

    return {
        "mean_ic": mean_ic,
        "ic_std": std_ic,
        "icir": icir,
        "positive_ic_ratio": pos_ratio,
        "days_evaluated": len(clean_ic)
    }
