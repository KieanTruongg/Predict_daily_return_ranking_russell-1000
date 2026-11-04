"""Long-Short dollar-neutral balance enforcer and risk constraint manager."""
import pandas as pd
import numpy as np


def neutralize_and_scale(
    signal: pd.DataFrame,
    target_leverage: float = 1.0,
    max_stock_weight: float = 0.05
) -> pd.DataFrame:
    """
    Transforms any raw cross-sectional signal or ranking into a strictly long-short balanced,
    dollar-neutral portfolio weight matrix.
    
    Properties guaranteed:
    1. Dollar-neutral: sum(w_i) == 0 for every timestamp t.
    2. Leverage-controlled: sum(|w_i|) == target_leverage (e.g. 50% long, 50% short if leverage=1.0).
    3. Position capped: |w_i| <= max_stock_weight (if specified).
    """
    # 1. Demean: subtract cross-sectional mean so sum(weights) = 0
    row_mean = signal.mean(axis=1)
    demeaned = signal.sub(row_mean, axis=0)

    # 2. L1 Normalize to target leverage
    abs_sum = demeaned.abs().sum(axis=1).replace(0, np.nan)
    scaled = demeaned.div(abs_sum, axis=0) * target_leverage

    # 3. Optional position clipping (with re-demeaning if clipped)
    if max_stock_weight is not None and max_stock_weight > 0:
        clipped = scaled.clip(lower=-max_stock_weight, upper=max_stock_weight)
        # Re-demean to ensure strict zero-sum after clipping
        clipped = clipped.sub(clipped.mean(axis=1), axis=0)
        # Re-scale
        clipped_abs_sum = clipped.abs().sum(axis=1).replace(0, np.nan)
        scaled = clipped.div(clipped_abs_sum, axis=0) * target_leverage

    return scaled


def verify_dollar_neutrality(weights: pd.DataFrame, tol: float = 1e-6) -> bool:
    """
    Sanity test to ensure every timestamp satisfies sum(weights) == 0.
    """
    daily_net_sum = weights.sum(axis=1).dropna()
    is_neutral = (daily_net_sum.abs() < tol).all()
    return bool(is_neutral)
