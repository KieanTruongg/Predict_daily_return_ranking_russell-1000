# -*- coding: utf-8 -*-
"""
tests/test_nan_classifier.py
============================
Unit and integration tests for feature NaN breakdown classification contracts.
Verifies exact decomposition using the shared production classifier (src.features.nan_classifier):
- Missing middle bar -> nan_due_to_window_defect_or_halt
- Missing endpoint at T -> nan_due_to_quality_at_t
- Missing endpoint at T-W -> nan_due_to_window_defect_or_halt
- Zero volume -> nan_due_to_zero_denom_or_invalid
- Bollinger sigma = 0 -> nan_due_to_zero_denom_or_invalid
- RSI reseed after invalid bar -> nan_due_to_rsi_state_reset
- Error in skipped momentum month [T-20, T] -> does NOT invalidate mom_12m_skip_1m
- GMT field-quarantine: Open/Low quarantined, Close valid -> ret_1d finite, ret_intraday NaN (quality_at_t)
- HOMS pre-IPO quarantine: clean count < 232 in [T-252, T-21] -> window_defect_or_halt
- Parkinson volatility: defect in middle of 20-day window -> window_defect_or_halt
"""

import numpy as np
import pandas as pd
import pytest

from src.features.base import (
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    BollingerPctBFeature,
    RSIFeature,
    AmihudIlliquidityFeature,
    IntradayReturnFeature,
    ParkinsonVolatilityFeature,
)
from src.features.nan_classifier import (
    classify_cell_nan,
    classify_feature_nans,
)


def test_classifier_missing_middle_bar():
    """Verify missing middle bar in ret_20d evaluates to nan_due_to_window_defect_or_halt."""
    n = 30
    prices = np.full(n, 100.0)
    bar_q = np.ones(n, dtype=bool)
    bar_q[15] = False  # defect at T-10 for T=25
    prices[15] = np.nan

    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    feat = PriceRatioMomentumFeature(window=20)
    res = feat.compute({"adj_close": df_p}, bar_quality_mask=df_q)

    # At T=25, window is [5, 25], bar 15 is False -> NaN
    assert np.isnan(res.iloc[25, 0])
    raw_inputs = {"adj_close": prices[:, None]}
    bar_q_2d = bar_q[:, None]
    reason = classify_cell_nan("ret_20d", 25, 0, raw_inputs, bar_q_2d, first_valid_idx=0)
    assert reason == "nan_due_to_window_defect_or_halt"


def test_classifier_missing_endpoints():
    """Verify missing endpoints: T -> nan_due_to_quality_at_t; T-W -> nan_due_to_window_defect_or_halt."""
    n = 30
    prices = np.full(n, 100.0)
    raw_inputs = {"adj_close": prices[:, None]}

    # Case A: defect at date T (index 25)
    bar_q_t = np.ones(n, dtype=bool)
    bar_q_t[25] = False
    reason_t = classify_cell_nan("ret_20d", 25, 0, raw_inputs, bar_q_t[:, None], first_valid_idx=0)
    assert reason_t == "nan_due_to_quality_at_t"

    # Case B: defect at date T-20 (index 5)
    bar_q_w = np.ones(n, dtype=bool)
    bar_q_w[5] = False
    reason_w = classify_cell_nan("ret_20d", 25, 0, raw_inputs, bar_q_w[:, None], first_valid_idx=0)
    assert reason_w == "nan_due_to_window_defect_or_halt"

    # Case C: lack of history (first valid trade was at index 10)
    reason_hist = classify_cell_nan("ret_20d", 25, 0, raw_inputs, np.ones((n, 1), dtype=bool), first_valid_idx=10)
    assert reason_hist == "nan_due_to_lack_of_history"


def test_classifier_zero_volume_amihud():
    """Verify zero volume in Amihud window evaluates to nan_due_to_zero_denom_or_invalid."""
    n = 30
    prices = np.full(n, 100.0)
    returns = np.full(n, 0.01)
    volumes = np.full(n, 1000.0)
    bar_q = np.ones(n, dtype=bool)
    volumes[20] = 0.0  # Zero volume at session 20

    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_r = pd.DataFrame({"A": returns}, index=dates)
    df_v = pd.DataFrame({"A": volumes}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    feat = AmihudIlliquidityFeature(window=20)
    res = feat.compute({"close": df_p, "volume": df_v, "daily_return": df_r}, bar_quality_mask=df_q)

    # At T=25, window includes session 20 where volume=0 -> NaN
    assert np.isnan(res.iloc[25, 0])
    raw_inputs = {"adj_close": prices[:, None], "adj_volume": volumes[:, None], "daily_return": returns[:, None]}
    reason = classify_cell_nan("amihud_illiq_20d", 25, 0, raw_inputs, bar_q[:, None], first_valid_idx=0)
    assert reason == "nan_due_to_zero_denom_or_invalid"


def test_classifier_bollinger_zero_sigma():
    """Verify constant prices (sigma=0) evaluate to nan_due_to_zero_denom_or_invalid."""
    n = 30
    prices = np.full(n, 100.0)  # Constant price -> sigma = 0
    bar_q = np.ones(n, dtype=bool)

    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    feat = BollingerPctBFeature(window=20)
    res = feat.compute({"adj_close": df_p}, bar_quality_mask=df_q)

    assert np.isnan(res.iloc[25, 0])
    raw_inputs = {"adj_close": prices[:, None]}
    reason = classify_cell_nan("bollinger_pct_b_20d", 25, 0, raw_inputs, bar_q[:, None], first_valid_idx=0)
    assert reason == "nan_due_to_zero_denom_or_invalid"


def test_classifier_rsi_reseed():
    """Verify RSI state reset requires full 14 clean consecutive deltas."""
    n = 40
    prices = np.linspace(100.0, 140.0, n)
    bar_q = np.ones(n, dtype=bool)
    bar_q[20] = False  # Invalid bar at index 20
    prices[20] = np.nan

    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    feat = RSIFeature(window=14)
    res = feat.compute({"adj_close": df_p}, bar_quality_mask=df_q)

    # At index 34: bars 21..34 (14 prices, 13 deltas) are clean, but bar 20 was dirty
    # 13 deltas is not enough to seed 14d RSI -> NaN due to rsi_state_reset
    assert np.isnan(res.iloc[34, 0])
    raw_inputs = {"adj_close": prices[:, None]}
    reason_34 = classify_cell_nan("rsi_14d", 34, 0, raw_inputs, bar_q[:, None], first_valid_idx=0)
    assert reason_34 == "nan_due_to_rsi_state_reset"

    # At index 35: 15 clean prices (14 deltas) since bar 20 -> successfully reseeded!
    assert np.isfinite(res.iloc[35, 0])


def test_mom12m_skip1m_ignores_skipped_month():
    """
    CRITICAL CONTRACT:
    mom_12m_skip_1m strictly inspects [T-252, T-21].
    Any error or quality flag in the skipped month [T-20, T] must NOT invalidate the feature at T!
    """
    n = 300
    prices = np.linspace(50.0, 150.0, n)
    bar_q = np.ones(n, dtype=bool)

    # Inject dirty bar at index 270 (which is T-5 for T=275)
    t_eval = 275
    bar_q[270] = False
    prices[270] = np.nan
    bar_q[t_eval] = False  # Even dirty bar at date T!
    prices[t_eval] = np.nan

    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    feat = Mom12mSkip1mFeature(lookback=252, skip=21)
    res = feat.compute({"adj_close": df_p}, bar_quality_mask=df_q)

    # Feature at T=275 only reads [275-252, 275-21] = [23, 254], where all bars are clean!
    val = res.iloc[t_eval, 0]
    assert np.isfinite(val), f"Expected finite mom_12m_skip_1m at T={t_eval} despite errors in skipped month, got {val}"

    # Now inject dirty bar INSIDE [T-252, T-21], e.g. at index 100
    bar_q[100] = False
    prices[100] = np.nan
    df_p = pd.DataFrame({"A": prices}, index=dates)
    df_q = pd.DataFrame({"A": bar_q}, index=dates)

    res_dirty = feat.compute({"adj_close": df_p}, bar_quality_mask=df_q)
    assert np.isnan(res_dirty.iloc[t_eval, 0]), "Expected NaN when bar inside [T-252, T-21] is dirty"

    raw_inputs = {"adj_close": prices[:, None]}
    reason = classify_cell_nan("mom_12m_skip_1m", t_eval, 0, raw_inputs, bar_q[:, None], first_valid_idx=0)
    assert reason == "nan_due_to_window_defect_or_halt"


def test_classifier_field_quarantine_gmt():
    """
    CRITICAL INTEGRATION TEST:
    GMT has Open/Low quarantined (set to NaN), but Close is valid!
    1. ret_1d (Close-based) MUST be finite and valid.
    2. ret_intraday (Open/Close) MUST be NaN and classified as nan_due_to_quality_at_t.
    """
    n = 20
    dates = pd.date_range("2007-01-10", periods=n, freq="B")
    
    # Simulate GMT: close is valid ~44.0, open is 0.01 at T=10, quarantined to NaN
    close = np.full(n, 44.25)
    close[9] = 46.32  # Prev close
    open_prices = np.full(n, 44.50)
    
    # Field quarantine on open at T=10
    t_eval = 10
    open_prices[t_eval] = np.nan
    
    bar_q = np.ones((n, 1), dtype=bool)
    field_q = {"adj_open": np.ones((n, 1), dtype=bool)}
    field_q["adj_open"][t_eval, 0] = False  # Field-level quarantine
    
    df_c = pd.DataFrame({"GMT": close}, index=dates)
    df_o = pd.DataFrame({"GMT": open_prices}, index=dates)
    df_bar_q = pd.DataFrame({"GMT": bar_q[:, 0]}, index=dates)
    df_field_o_q = pd.DataFrame({"GMT": field_q["adj_open"][:, 0]}, index=dates)
    
    # 1. ret_1d check
    feat_ret1 = PriceRatioMomentumFeature(window=1)
    res_ret1 = feat_ret1.compute({"adj_close": df_c}, bar_quality_mask=df_bar_q)
    val_ret1 = res_ret1.iloc[t_eval, 0]
    assert np.isfinite(val_ret1), "ret_1d must remain finite when only Open/Low are quarantined"
    expected_ret1 = (44.25 - 46.32) / 46.32
    assert abs(val_ret1 - expected_ret1) < 1e-6
    
    # 2. ret_intraday check
    feat_intra = IntradayReturnFeature()
    res_intra = feat_intra.compute(
        {"adj_open": df_o, "adj_close": df_c},
        bar_quality_mask=df_bar_q,
        field_quality_masks={"adj_open": df_field_o_q},
    )
    assert np.isnan(res_intra.iloc[t_eval, 0]), "ret_intraday must be NaN when Open is quarantined"
    
    # 3. Classifier check
    raw_inputs = {"adj_open": open_prices[:, None], "adj_close": close[:, None]}
    reason = classify_cell_nan(
        "ret_intraday",
        t_eval,
        0,
        raw_inputs=raw_inputs,
        bar_quality_mask=bar_q,
        first_valid_idx=0,
        field_quality_masks=field_q,
    )
    assert reason == "nan_due_to_quality_at_t"


def test_classifier_homs_pre_ipo_in_lookback():
    """
    CRITICAL INTEGRATION TEST:
    HOMS has a quarantined pre-IPO bar at 1999-08-04 (T-252 for T=2000-08-02).
    Clean bar count in [T-252, T-21] drops to 231 (< 232) -> mom_12m_skip_1m must evaluate
    to NaN and be classified as nan_due_to_window_defect_or_halt!
    """
    n = 260
    prices = np.full(n, 100.0)
    bar_q = np.ones(n, dtype=bool)
    
    # Quarantined pre-IPO bar at T-252 for T=255
    t_eval = 255
    idx_pre_ipo = t_eval - 252  # index 3
    bar_q[idx_pre_ipo] = False
    prices[idx_pre_ipo] = np.nan
    
    # Also simulate 20 non-trading/holiday sessions in 231-session window
    # so that clean count is exactly 231 (< 232 threshold)
    for i in range(10, 30):
        bar_q[i] = False
        prices[i] = np.nan
        
    dates = pd.date_range("1999-08-01", periods=n, freq="B")
    df_p = pd.DataFrame({"HOMS": prices}, index=dates)
    df_q = pd.DataFrame({"HOMS": bar_q}, index=dates)
    
    feat_mom = Mom12mSkip1mFeature(lookback=252, skip=21)
    res_mom = feat_mom.compute({"adj_close": df_p}, bar_quality_mask=df_q)
    
    assert np.isnan(res_mom.iloc[t_eval, 0]), "mom_12m_skip_1m must be NaN when clean count < 232"
    
    raw_inputs = {"adj_close": prices[:, None]}
    reason = classify_cell_nan(
        "mom_12m_skip_1m",
        t_eval,
        0,
        raw_inputs=raw_inputs,
        bar_quality_mask=bar_q[:, None],
        first_valid_idx=0,
    )
    assert reason == "nan_due_to_window_defect_or_halt"


def test_classifier_parkinson_window_defect():
    """
    CRITICAL INTEGRATION TEST:
    Parkinson Volatility requires 20 clean bars of High and Low in [T-19, T].
    If a defect/quarantine occurs at T-10, Parkinson volatility at T must evaluate to NaN
    and be classified as nan_due_to_window_defect_or_halt!
    """
    n = 30
    high = np.full(n, 82.0)
    low = np.full(n, 78.0)
    bar_q = np.ones(n, dtype=bool)
    
    # Quarantine high/low at T-10 (index 15 for T=25)
    t_eval = 25
    defect_idx = 15
    high[defect_idx] = np.nan
    low[defect_idx] = np.nan
    
    field_q = {
        "adj_high": np.ones((n, 1), dtype=bool),
        "adj_low": np.ones((n, 1), dtype=bool),
    }
    field_q["adj_high"][defect_idx, 0] = False
    field_q["adj_low"][defect_idx, 0] = False
    
    dates = pd.date_range("2008-06-01", periods=n, freq="B")
    df_h = pd.DataFrame({"A": high}, index=dates)
    df_l = pd.DataFrame({"A": low}, index=dates)
    df_bar_q = pd.DataFrame({"A": bar_q}, index=dates)
    df_qh = pd.DataFrame({"A": field_q["adj_high"][:, 0]}, index=dates)
    df_ql = pd.DataFrame({"A": field_q["adj_low"][:, 0]}, index=dates)
    
    feat_park = ParkinsonVolatilityFeature(window=20)
    res_park = feat_park.compute(
        {"adj_high": df_h, "adj_low": df_l},
        bar_quality_mask=df_bar_q,
        field_quality_masks={"adj_high": df_qh, "adj_low": df_ql},
    )
    
    assert np.isnan(res_park.iloc[t_eval, 0]), "vol_parkinson_20d must be NaN when High/Low is quarantined in window"
    
    raw_inputs = {"adj_high": high[:, None], "adj_low": low[:, None]}
    reason = classify_cell_nan(
        "vol_parkinson_20d",
        t_eval,
        0,
        raw_inputs=raw_inputs,
        bar_quality_mask=bar_q[:, None],
        first_valid_idx=0,
        field_quality_masks=field_q,
    )
    assert reason == "nan_due_to_window_defect_or_halt"
