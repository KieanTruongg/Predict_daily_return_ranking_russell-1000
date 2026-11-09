# -*- coding: utf-8 -*-
"""
tests/test_causal_integrity.py
==============================
Pytest integration test for Point-In-Time (PIT) causality on candidate features.
Verifies that neither future perturbation nor future truncation alters historical feature values.
Asserts that evaluated coordinates are finite (preventing trivial NaN pass).
"""

import numpy as np
import pandas as pd
import pytest

from src.features.base import (
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    RealizedVolatilityFeature,
    ParkinsonVolatilityFeature,
    BollingerPctBFeature,
    RSIFeature,
)


def test_causal_integrity_synthetic_all_archetypes():
    """
    Verify causality on synthetic data across multiple feature archetypes:
    - Ratio momentum (PriceRatioMomentumFeature)
    - Shifted momentum (Mom12mSkip1mFeature)
    - Rolling volatility (RealizedVolatilityFeature)
    - High-low extreme volatility (ParkinsonVolatilityFeature)
    - Band normalized (BollingerPctBFeature)
    - Recursive state indicator (RSIFeature)
    """
    n = 300
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    
    # Synthetic random walk prices
    returns = rng.normal(0.0005, 0.015, size=(n, 2))
    prices = 100.0 * np.exp(np.cumsum(returns, axis=0))
    highs = prices * (1.0 + np.abs(rng.normal(0.005, 0.003, size=(n, 2))))
    lows = prices * (1.0 - np.abs(rng.normal(0.005, 0.003, size=(n, 2))))
    opens = (highs + lows) / 2.0
    
    df_p = pd.DataFrame(prices, index=dates, columns=["A", "B"])
    df_h = pd.DataFrame(highs, index=dates, columns=["A", "B"])
    df_l = pd.DataFrame(lows, index=dates, columns=["A", "B"])
    df_o = pd.DataFrame(opens, index=dates, columns=["A", "B"])
    df_r = pd.DataFrame(returns, index=dates, columns=["A", "B"])
    df_q = pd.DataFrame(True, index=dates, columns=["A", "B"])

    t_eval = dates[260]

    test_features = [
        ("ret_20d", PriceRatioMomentumFeature(window=20), {"adj_close": df_p}),
        ("mom_12m_skip_1m", Mom12mSkip1mFeature(lookback=252, skip=21), {"adj_close": df_p}),
        ("vol_realized_20d", RealizedVolatilityFeature(window=20), {"daily_return": df_r}),
        ("vol_parkinson_20d", ParkinsonVolatilityFeature(window=20), {"adj_high": df_h, "adj_low": df_l}),
        ("bollinger_pct_b_20d", BollingerPctBFeature(window=20), {"adj_close": df_p}),
        ("rsi_14d", RSIFeature(window=14), {"adj_close": df_p}),
    ]

    for name, feat, data in test_features:
        # 1. Baseline
        df_base = feat.compute(data=data, bar_quality_mask=df_q)
        val_base = float(df_base.loc[t_eval, "A"])
        assert np.isfinite(val_base), f"Baseline value for {name} must be finite!"

        # 2. Perturbation: corrupt all rows t > t_eval
        data_pert = {}
        for k, v in data.items():
            v_c = v.copy()
            v_c.loc[dates > t_eval] = v_c.loc[dates > t_eval] * 10.0
            data_pert[k] = v_c

        df_pert = feat.compute(data=data_pert, bar_quality_mask=df_q)
        val_pert = float(df_pert.loc[t_eval, "A"])
        assert np.isfinite(val_pert), f"Perturbed value for {name} must be finite!"
        assert abs(val_pert - val_base) <= 1e-11, f"Future perturbation leaked into {name}!"

        # 3. Truncation: drop all rows t > t_eval
        data_trunc = {k: v.loc[dates <= t_eval].copy() for k, v in data.items()}
        df_q_trunc = df_q.loc[dates <= t_eval]

        df_trunc = feat.compute(data=data_trunc, bar_quality_mask=df_q_trunc)
        val_trunc = float(df_trunc.loc[t_eval, "A"])
        assert np.isfinite(val_trunc), f"Truncated value for {name} must be finite!"
        assert abs(val_trunc - val_base) <= 1e-11, f"Future truncation altered {name}!"
