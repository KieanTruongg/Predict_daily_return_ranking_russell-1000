# -*- coding: utf-8 -*-
"""
tests/test_pilot_features.py
============================
Automated regression tests for Pilot Features v1 (16 features):
Batch 1:
- ret_20d (PriceRatioMomentumFeature)
- vol_realized_20d (RealizedVolatilityFeature, daily unit)
- amihud_illiq_20d (AmihudIlliquidityFeature)
- rsi_14d (RSIFeature with Wilder smoothing & state reset)
- bollinger_pct_b_20d (BollingerPctBFeature, ddof=0)

Batch 2:
- Momentum: ret_1d, ret_5d, ret_60d, mom_12m_skip_1m
- Volatility: vol_realized_60d, vol_parkinson_20d, downside_deviation_20d
- Volume & Intraday: volume_ratio_5_20, log_dollar_volume_20d, ret_intraday, ret_overnight

All disk-dependent tests on real market matrices are tagged with @pytest.mark.integration.
"""

import unittest
import numpy as np
import pandas as pd
import pytest

from src.features.base import (
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    RealizedVolatilityFeature,
    ParkinsonVolatilityFeature,
    DownsideDeviationFeature,
    AmihudIlliquidityFeature,
    VolumeRatioFeature,
    LogDollarVolumeFeature,
    IntradayReturnFeature,
    OvernightReturnFeature,
    RSIFeature,
    BollingerPctBFeature,
)
from src.features.transforms import cross_sectional_rank
from src.data.matrix_loader import (
    load_matrix,
    load_bar_quality_mask,
    load_layer1_mask,
)


class TestPilotFeatures(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2000-01-01", periods=300, freq="B")

    # =========================================================================
    # BATCH 1 PORTABLE SYNTHETIC TESTS (01 - 08)
    # =========================================================================

    def test_01_ret_20d_geometric_and_flat(self):
        """Verify ret_20d exact formula on geometric and flat price series."""
        p_geom = pd.DataFrame({"A": [100.0 * (1.01 ** i) for i in range(25)]}, index=self.dates[:25])
        feat = PriceRatioMomentumFeature(window=20)
        res = feat.compute({"adj_close": p_geom})
        exp = (1.01 ** 20) - 1.0
        self.assertAlmostEqual(res.iloc[20]["A"], exp, places=7)

        # Flat series -> 0.0
        p_flat = pd.DataFrame({"A": [100.0] * 25}, index=self.dates[:25])
        res_flat = feat.compute({"adj_close": p_flat})
        self.assertAlmostEqual(res_flat.iloc[20]["A"], 0.0, places=7)

    def test_02_ret_20d_dirty_bar_nan_and_recovery(self):
        """Verify ret_20d evaluates to NaN when dirty bar is in window, recovers after."""
        p = pd.DataFrame({"A": [100.0 + i for i in range(40)]}, index=self.dates[:40])
        q_mask = pd.DataFrame({"A": [True] * 40}, index=self.dates[:40])
        q_mask.iloc[10, 0] = False  # Bar 10 is dirty

        feat = PriceRatioMomentumFeature(window=20)
        res = feat.compute({"adj_close": p}, bar_quality_mask=q_mask)
        # At index 20, lookback is [0..20], contains bar 10 -> NaN
        self.assertTrue(np.isnan(res.iloc[20]["A"]))
        # At index 30, lookback is [10..30], contains bar 10 -> NaN
        self.assertTrue(np.isnan(res.iloc[30]["A"]))
        # At index 31, lookback is [11..31], bar 10 has exited -> valid
        exp_31 = (100.0 + 31) / (100.0 + 11) - 1.0
        self.assertAlmostEqual(res.iloc[31]["A"], exp_31, places=7)

    def test_03_vol_realized_20d_daily_unit_and_zero(self):
        """Verify vol_realized_20d uses daily unit (ddof=1) without annualization."""
        rets = [0.01 if i % 2 == 0 else -0.01 for i in range(25)]
        df_ret = pd.DataFrame({"A": rets}, index=self.dates[:25])
        feat = RealizedVolatilityFeature(window=20, return_type="daily_return", annualize=False)
        res = feat.compute({"daily_return": df_ret})
        exp = np.sqrt(20.0 * (0.01 ** 2) / 19.0)
        self.assertAlmostEqual(res.iloc[19]["A"], exp, places=7)

        # Zero return series -> 0.0
        df_zero = pd.DataFrame({"A": [0.0] * 25}, index=self.dates[:25])
        res_zero = feat.compute({"daily_return": df_zero})
        self.assertAlmostEqual(res_zero.iloc[19]["A"], 0.0, places=7)

    def test_04_amihud_illiq_20d_formula_and_zero_volume(self):
        """Verify amihud_illiq_20d formula and NaN on zero volume."""
        df_ret = pd.DataFrame({"A": [0.01] * 25}, index=self.dates[:25])
        df_p = pd.DataFrame({"A": [100.0] * 25}, index=self.dates[:25])
        df_v = pd.DataFrame({"A": [10000.0] * 25}, index=self.dates[:25])
        feat = AmihudIlliquidityFeature(window=20)
        res = feat.compute({"daily_return": df_ret, "close": df_p, "volume": df_v})
        self.assertAlmostEqual(res.iloc[19]["A"], 0.01, places=7)

        # Zero volume on 1 day -> NaN
        df_v_zero = df_v.copy()
        df_v_zero.iloc[10, 0] = 0.0
        res_zero = feat.compute({"daily_return": df_ret, "close": df_p, "volume": df_v_zero})
        self.assertTrue(np.isnan(res_zero.iloc[19]["A"]))

    def test_05_rsi_14d_wilder_smoothing_and_reset(self):
        """Verify rsi_14d Wilder smoothing, flat convention, and state reset."""
        p_inc = pd.DataFrame({"A": [100.0 + i for i in range(40)]}, index=self.dates[:40])
        feat = RSIFeature(window=14)
        res_inc = feat.compute({"adj_close": p_inc})
        self.assertAlmostEqual(res_inc.iloc[14]["A"], 100.0, places=6)

        # Flat series -> 50.0
        p_flat = pd.DataFrame({"A": [100.0] * 25}, index=self.dates[:25])
        res_flat = feat.compute({"adj_close": p_flat})
        self.assertAlmostEqual(res_flat.iloc[14]["A"], 50.0, places=6)

        # Dirty bar reset
        q_mask = pd.DataFrame({"A": [True] * 40}, index=self.dates[:40])
        q_mask.iloc[10, 0] = False
        res_dirty = feat.compute({"adj_close": p_inc}, bar_quality_mask=q_mask)
        # Bar 10 dirty -> gap -> seeds anew after 14 clean deltas (idx 11..25 = 14 deltas -> idx 25 valid)
        self.assertTrue(np.isnan(res_dirty.iloc[15]["A"]))
        self.assertAlmostEqual(res_dirty.iloc[25]["A"], 100.0, places=6)

    def test_06_bollinger_pct_b_20d_formula_and_zero_sigma(self):
        """Verify bollinger_pct_b_20d ddof=0, formula, and NaN when sigma=0."""
        prices = [95.0] * 10 + [105.0] * 9 + [115.0]
        df_p = pd.DataFrame({"A": prices}, index=self.dates[:20])
        feat = BollingerPctBFeature(window=20)
        res = feat.compute({"adj_close": df_p})

        m = float(np.mean(prices))
        s = float(np.std(prices, ddof=0))
        self.assertAlmostEqual(s, 5.89491306, places=6)
        exp = (115.0 - (m - 2.0 * s)) / (4.0 * s)
        self.assertAlmostEqual(res.iloc[19]["A"], exp, places=7)

        # Zero sigma on flat series -> NaN
        df_flat = pd.DataFrame({"A": [100.0] * 20}, index=self.dates[:20])
        res_flat = feat.compute({"adj_close": df_flat})
        self.assertTrue(np.isnan(res_flat.iloc[19]["A"]))

    def test_07_ret_momentum_rejects_inf_and_negative_prices(self):
        """Verify PriceRatioMomentumFeature rejects Inf and non-positive prices."""
        p_inf = pd.DataFrame({"A": [100.0, np.inf, 110.0]}, index=self.dates[:3])
        feat_2d = PriceRatioMomentumFeature(window=2)
        res_inf = feat_2d.compute({"adj_close": p_inf})
        self.assertTrue(np.isnan(res_inf.iloc[2]["A"]), "Window with Inf price must evaluate to NaN")

        p_neg = pd.DataFrame({"A": [-100.0, 105.0, 110.0]}, index=self.dates[:3])
        res_neg = feat_2d.compute({"adj_close": p_neg})
        self.assertTrue(np.isnan(res_neg.iloc[2]["A"]), "Window with negative price must evaluate to NaN")

    def test_08_amihud_rejects_negative_price_and_volume(self):
        """Verify AmihudIlliquidityFeature rejects negative price and volume even if product is positive."""
        df_ret = pd.DataFrame({"A": [0.01] * 3}, index=self.dates[:3])
        df_p = pd.DataFrame({"A": [-10.0, 10.0, 10.0]}, index=self.dates[:3])
        df_v = pd.DataFrame({"A": [-100.0, 1000.0, 1000.0]}, index=self.dates[:3])
        feat_2d = AmihudIlliquidityFeature(window=2)
        res = feat_2d.compute({"daily_return": df_ret, "close": df_p, "volume": df_v})
        self.assertTrue(np.isnan(res.iloc[1]["A"]))
        self.assertFalse(np.isnan(res.iloc[2]["A"]))

    # =========================================================================
    # BATCH 1 INTEGRATION TESTS (09a, 09b, 10, 10b, 11, 19) - REAL MARKET DATA
    # =========================================================================

    @pytest.mark.integration
    def test_09a_aapl_split_internal_pipeline_consistency(self):
        """
        Verify AAPL 2:1 split on 2000-06-21 daily_return internal pipeline consistency:
        Expected = (P_raw[T] * (s_T / s_{T-1}) / P_raw[T-1]) - 1.0.
        Parity must hold within machine epsilon (< 1e-12).
        """
        p_raw = load_matrix("close", dev_only=True, include_warmup=True)
        split_mat = load_matrix("cumulative_split_factor", dev_only=True, include_warmup=True)
        ret_matrix = load_matrix("daily_return", dev_only=True, include_warmup=True)
        sid_aapl = "AAPL R735QTJ8XC9X"

        p_prev_raw = p_raw.loc["2000-06-20", sid_aapl]  # 101.0
        p_curr_raw = p_raw.loc["2000-06-21", sid_aapl]  # 55.56
        s_prev = split_mat.loc["2000-06-20", sid_aapl]  # 0.00892857
        s_curr = split_mat.loc["2000-06-21", sid_aapl]  # 0.0178571

        # Source factor parity formula
        source_factor_ratio = s_curr / s_prev
        expected_ret_source = (p_curr_raw * source_factor_ratio / p_prev_raw) - 1.0
        actual_ret = ret_matrix.loc["2000-06-21", sid_aapl]

        diff_source = abs(actual_ret - expected_ret_source)
        self.assertLess(diff_source, 1e-12, f"Matrix daily_return deviates from internal factor formula: {diff_source}")

    @pytest.mark.integration
    def test_09b_aapl_split_theoretical_ideal_comparison(self):
        """
        Compare AAPL 2:1 split on 2000-06-21 against the theoretical ideal integer ratio (2.0).
        Observation:
        The internal factor ratio is 0.0178571 / 0.00892857 = 1.9999955199992832.
        Compared to the ideal integer 2.0, this yields a minor discrepancy of 2.46e-6,
        strictly within tolerance 1e-5. We document this observed difference objectively
        without asserting an unverified vendor rounding mechanism.
        """
        p_raw = load_matrix("close", dev_only=True, include_warmup=True)
        ret_matrix = load_matrix("daily_return", dev_only=True, include_warmup=True)
        sid_aapl = "AAPL R735QTJ8XC9X"

        p_prev_raw = p_raw.loc["2000-06-20", sid_aapl]  # 101.0
        p_curr_raw = p_raw.loc["2000-06-21", sid_aapl]  # 55.56
        ideal_factor = 2.0

        expected_ret_ideal = (p_curr_raw * ideal_factor / p_prev_raw) - 1.0  # 0.1001980198
        actual_ret = ret_matrix.loc["2000-06-21", sid_aapl]                 # 0.1001955554

        diff_ideal = abs(actual_ret - expected_ret_ideal)
        self.assertAlmostEqual(actual_ret, expected_ret_ideal, delta=1e-5)
        self.assertLess(diff_ideal, 3e-6, f"Deviation from ideal 2:1 factor was {diff_ideal:.2e}")

    @pytest.mark.integration
    def test_10_bf_warmup_exact_nan_sessions(self):
        """Verify BF has exactly 2 NaN sessions at index entry (2000-07-03, 2000-07-05) and valid on 07-06."""
        adj = load_matrix("adj_close", dev_only=True, include_warmup=True)
        q_mask = load_bar_quality_mask(dev_only=True, include_warmup=True)
        mem_mask = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
        sid_bf = "BF RVCJ9QZYSJMT"

        feat = PriceRatioMomentumFeature(window=20)
        res = feat.compute({"adj_close": adj[[sid_bf]]}, bar_quality_mask=q_mask[[sid_bf]], membership_mask=mem_mask[[sid_bf]])

        # 2000-07-03: trading session 1 -> NaN
        self.assertTrue(np.isnan(res.loc["2000-07-03", sid_bf]))
        # 2000-07-05: trading session 2 -> NaN
        self.assertTrue(np.isnan(res.loc["2000-07-05", sid_bf]))
        # 2000-07-06: trading session 3 -> valid!
        self.assertFalse(np.isnan(res.loc["2000-07-06", sid_bf]))
        self.assertAlmostEqual(res.loc["2000-07-06", sid_bf], -0.075330, places=5)

    @pytest.mark.integration
    def test_10b_agilent_matrix_history_and_mom12m(self):
        """
        Directly verify Agilent bar counts from matrices:
        - 126 clean bars strictly before Russell 1000 entry (up to 2000-06-30).
        - 127 bars up to entry date 2000-07-03.
        - 252 bars up to 2000-12-29 (< 253 required for 12-month momentum).
        - 253rd bar on 2001-01-02 -> mom_12m_skip_1m recovers to valid value.
        """
        adj = load_matrix("adj_close", dev_only=True, include_warmup=True)
        q_mask = load_bar_quality_mask(dev_only=True, include_warmup=True)
        mem_mask = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
        sid_a = "A RPTMYV3VC57P"

        p_a = adj[sid_a].dropna()
        q_a = q_mask[sid_a]

        # Count directly from matrix
        clean_pre_entry = p_a.loc[:"2000-06-30"][q_a.loc[:"2000-06-30"]]
        self.assertEqual(len(clean_pre_entry), 126)

        clean_all = p_a[q_a.loc[p_a.index]]
        self.assertEqual(len(clean_all.loc[:"2000-12-29"]), 252)
        self.assertEqual(clean_all.index[252].strftime("%Y-%m-%d"), "2001-01-02")

        # Compute mom_12m_skip_1m
        f_mom = Mom12mSkip1mFeature(lookback=252, skip=21)
        res_mom = f_mom.compute({"adj_close": adj[[sid_a]]}, bar_quality_mask=q_mask[[sid_a]], membership_mask=mem_mask[[sid_a]])

        # NaN at entry date 2000-07-03
        self.assertTrue(np.isnan(res_mom.loc["2000-07-03", sid_a]))
        # Valid at 2001-01-02
        self.assertFalse(np.isnan(res_mom.loc["2001-01-02", sid_a]))
        self.assertAlmostEqual(res_mom.loc["2001-01-02", sid_a], -0.274655, places=5)
        q_mask = load_bar_quality_mask(dev_only=True, include_warmup=True)
        mem_mask = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
        sid_bf = "BF RVCJ9QZYSJMT"

        feat = PriceRatioMomentumFeature(window=20)
        res = feat.compute({"adj_close": adj[[sid_bf]]}, bar_quality_mask=q_mask[[sid_bf]], membership_mask=mem_mask[[sid_bf]])

        # 2000-07-03: trading session 1 -> NaN
        self.assertTrue(np.isnan(res.loc["2000-07-03", sid_bf]))
        # 2000-07-05: trading session 2 -> NaN
        self.assertTrue(np.isnan(res.loc["2000-07-05", sid_bf]))
        # 2000-07-06: trading session 3 -> valid!
        self.assertFalse(np.isnan(res.loc["2000-07-06", sid_bf]))
        self.assertAlmostEqual(res.loc["2000-07-06", sid_bf], -0.075330, places=5)

    @pytest.mark.integration
    def test_11_ksu_spinoff_exact_21_nan_sessions(self):
        """Verify KSU spinoff on 2000-07-13 causes exactly 21 consecutive trading days of NaN."""
        adj = load_matrix("adj_close", dev_only=True, include_warmup=True)
        q_mask = load_bar_quality_mask(dev_only=True, include_warmup=True)
        mem_mask = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
        sid_ksu = "KSU R735QTJ8XC9X"

        feat = PriceRatioMomentumFeature(window=20)
        res = feat.compute({"adj_close": adj[[sid_ksu]]}, bar_quality_mask=q_mask[[sid_ksu]], membership_mask=mem_mask[[sid_ksu]])

        # 2000-07-13 to 2000-08-10 is exactly 21 trading sessions
        nan_window = res.loc["2000-07-13":"2000-08-10", sid_ksu]
        self.assertEqual(len(nan_window), 21)
        self.assertTrue(nan_window.isna().all(), "All 21 trading sessions in spinoff lookback must be NaN")

        # 2000-08-11 is first valid session
        val_0811 = res.loc["2000-08-11", sid_ksu]
        self.assertFalse(np.isnan(val_0811))
        self.assertAlmostEqual(val_0811, -0.036337, places=5)

    # =========================================================================
    # BATCH 2 PORTABLE SYNTHETIC TESTS (12 - 18)
    # =========================================================================

    def test_12_ret_1d_5d_60d_synthetic(self):
        """Verify ret_1d, ret_5d, ret_60d formulas on geometric price series."""
        p_geom = pd.DataFrame({"A": [100.0 * (1.01 ** i) for i in range(70)]}, index=self.dates[:70])

        # ret_1d: W=1 -> requires 2 prices
        f_1d = PriceRatioMomentumFeature(window=1)
        res_1d = f_1d.compute({"adj_close": p_geom})
        self.assertAlmostEqual(res_1d.iloc[1]["A"], 0.01, places=7)

        # ret_5d: W=5 -> requires 6 prices
        f_5d = PriceRatioMomentumFeature(window=5)
        res_5d = f_5d.compute({"adj_close": p_geom})
        exp_5d = (1.01 ** 5) - 1.0
        self.assertAlmostEqual(res_5d.iloc[5]["A"], exp_5d, places=7)

        # ret_60d: W=60 -> requires 61 prices
        f_60d = PriceRatioMomentumFeature(window=60)
        res_60d = f_60d.compute({"adj_close": p_geom})
        exp_60d = (1.01 ** 60) - 1.0
        self.assertAlmostEqual(res_60d.iloc[60]["A"], exp_60d, places=7)

    def test_13_mom_12m_skip_1m_formula_and_skip(self):
        """Verify mom_12m_skip_1m formula P[T-21]/P[T-252]-1 and insensitivity to prices after T-21."""
        # 280 dates: P_t = 100.0 + t
        n = 280
        p_series = [100.0 + i for i in range(n)]
        df_p = pd.DataFrame({"A": p_series}, index=self.dates[:n])
        feat = Mom12mSkip1mFeature(lookback=252, skip=21)
        res = feat.compute({"adj_close": df_p})

        # At index 260: P[260-21] = P[239], P[260-252] = P[8]
        exp_260 = (100.0 + 239) / (100.0 + 8) - 1.0
        self.assertAlmostEqual(res.iloc[260]["A"], exp_260, places=7)

        # Changing price at T=260 should NOT alter mom_12m_skip_1m[T]
        df_p_mod = df_p.copy()
        df_p_mod.iloc[260, 0] = 9999.0
        res_mod = feat.compute({"adj_close": df_p_mod})
        self.assertAlmostEqual(res_mod.iloc[260]["A"], exp_260, places=7)

        # Dirty bar in measured range [T-252 .. T-21] causes NaN
        q_mask = pd.DataFrame({"A": [True] * n}, index=self.dates[:n])
        q_mask.iloc[100, 0] = False  # idx 100 is between 8 and 239
        res_dirty = feat.compute({"adj_close": df_p}, bar_quality_mask=q_mask)
        self.assertTrue(np.isnan(res_dirty.iloc[260]["A"]))

        # Dirty bar in skipped range (e.g. idx 250) does NOT invalidate mom_12m_skip_1m
        q_mask_skip = pd.DataFrame({"A": [True] * n}, index=self.dates[:n])
        q_mask_skip.iloc[250, 0] = False  # in skipped range [240..260]
        res_skip_dirty = feat.compute({"adj_close": df_p}, bar_quality_mask=q_mask_skip)
        self.assertAlmostEqual(res_skip_dirty.iloc[260]["A"], exp_260, places=7)

    def test_14_vol_parkinson_20d_formula(self):
        """Verify Parkinson volatility formula, flat bar zero contribution, and invalid bar NaN."""
        # 25 dates: H = 102.0, L = 100.0 (H/L = 1.02)
        h = [102.0] * 25
        l = [100.0] * 25
        df_h = pd.DataFrame({"A": h}, index=self.dates[:25])
        df_l = pd.DataFrame({"A": l}, index=self.dates[:25])
        feat = ParkinsonVolatilityFeature(window=20)
        res = feat.compute({"adj_high": df_h, "adj_low": df_l})

        term = (np.log(1.02) ** 2) / (4.0 * np.log(2.0))
        exp = np.sqrt(term)
        self.assertAlmostEqual(res.iloc[19]["A"], exp, places=7)

        # Flat bars H=L=100 -> term=0.0 -> vol=0.0
        df_l_flat = df_h.copy()
        res_flat = feat.compute({"adj_high": df_h, "adj_low": df_l_flat})
        self.assertAlmostEqual(res_flat.iloc[19]["A"], 0.0, places=7)

        # Invalid bar H < L -> NaN
        df_h_bad = df_h.copy()
        df_h_bad.iloc[10, 0] = 90.0  # H < L
        res_bad = feat.compute({"adj_high": df_h_bad, "adj_low": df_l})
        self.assertTrue(np.isnan(res_bad.iloc[19]["A"]))

    def test_15_downside_deviation_20d_formula(self):
        """Verify downside deviation formula, non-negative return zero contribution, and full denominator W."""
        # 25 returns: 10 returns of -0.02 and 10 returns of +0.02
        rets = [-0.02 if i % 2 == 0 else 0.02 for i in range(25)]
        df_ret = pd.DataFrame({"A": rets}, index=self.dates[:25])
        feat = DownsideDeviationFeature(window=20)
        res = feat.compute({"daily_return": df_ret})

        # 10 negative returns of -0.02 -> sum of squared negative returns = 10 * (-0.02)^2 = 0.004
        # Denominator is 20 (full window) -> 0.004 / 20 = 0.0002 -> sqrt(0.0002) = 0.0141421356
        exp = np.sqrt(10.0 * (0.02 ** 2) / 20.0)
        self.assertAlmostEqual(res.iloc[19]["A"], exp, places=7)

        # All positive returns -> 0.0
        df_pos = pd.DataFrame({"A": [0.02] * 25}, index=self.dates[:25])
        res_pos = feat.compute({"daily_return": df_pos})
        self.assertAlmostEqual(res_pos.iloc[19]["A"], 0.0, places=7)

    def test_16_volume_ratio_5_20_formula(self):
        """Verify volume_ratio_5_20 formula mean_5/mean_20 on split-adjusted volume."""
        # 25 volumes: first 15 = 10,000, next 5 = 20,000
        vols = [10000.0] * 15 + [20000.0] * 5 + [10000.0] * 5
        df_v = pd.DataFrame({"A": vols}, index=self.dates[:25])
        feat = VolumeRatioFeature(fast_window=5, slow_window=20)
        res = feat.compute({"adj_volume": df_v})

        # At idx 19 (window 0..19): 15 bars of 10k, 5 bars of 20k
        # mean_5 = 20k
        # mean_20 = (15*10k + 5*20k)/20 = 250k/20 = 12.5k
        # ratio = 20k / 12.5k = 1.6
        self.assertAlmostEqual(res.iloc[19]["A"], 1.60, places=7)

        # Zero volume inside window causes NaN
        df_v_zero = df_v.copy()
        df_v_zero.iloc[10, 0] = 0.0
        res_zero = feat.compute({"adj_volume": df_v_zero})
        self.assertTrue(np.isnan(res_zero.iloc[19]["A"]))

    def test_17_log_dollar_volume_20d_formula(self):
        """Verify log_dollar_volume_20d formula log1p(mean_20(p_raw * v_raw))."""
        df_p = pd.DataFrame({"A": [100.0] * 25}, index=self.dates[:25])
        df_v = pd.DataFrame({"A": [10000.0] * 25}, index=self.dates[:25])
        feat = LogDollarVolumeFeature(window=20)
        res = feat.compute({"close": df_p, "volume": df_v})

        # mean_20(DV) = 1,000,000 USD -> log1p(1,000,000)
        exp = np.log1p(1000000.0)
        self.assertAlmostEqual(res.iloc[19]["A"], exp, places=7)

    def test_18_ret_intraday_and_overnight_identity(self):
        """Verify ret_intraday, ret_overnight, and identity (1+r_1d) == (1+r_overnight)*(1+r_intraday)."""
        # Day 0: C=100.0, O=99.0
        # Day 1: C=105.0, O=102.0
        dates_2 = self.dates[:2]
        df_c = pd.DataFrame({"A": [100.0, 105.0]}, index=dates_2)
        df_o = pd.DataFrame({"A": [99.0, 102.0]}, index=dates_2)

        f_intra = IntradayReturnFeature()
        f_over = OvernightReturnFeature()
        f_1d = PriceRatioMomentumFeature(window=1)

        res_intra = f_intra.compute({"adj_close": df_c, "adj_open": df_o})
        res_over = f_over.compute({"adj_close": df_c, "adj_open": df_o})
        res_1d = f_1d.compute({"adj_close": df_c})

        # Day 1 intraday: 105 / 102 - 1
        exp_intra = (105.0 / 102.0) - 1.0
        self.assertAlmostEqual(res_intra.iloc[1]["A"], exp_intra, places=7)

        # Day 1 overnight: 102 / 100 - 1 = 0.02
        exp_over = (102.0 / 100.0) - 1.0
        self.assertAlmostEqual(res_over.iloc[1]["A"], exp_over, places=7)

        # Identity: (1 + 0.02) * (105 / 102) - 1 = 105 / 100 - 1 = 0.05
        decomp = (1.0 + res_over.iloc[1]["A"]) * (1.0 + res_intra.iloc[1]["A"]) - 1.0
        self.assertAlmostEqual(decomp, res_1d.iloc[1]["A"], places=7)

    @pytest.mark.integration
    def test_19_msft_parkinson_vol_exact_numerical_parity(self):
        """
        Verify Parkinson volatility on real market data (MSFT 2000-07-05)
        against an independent direct numpy calculation across the exact 20-bar High/Low window.
        Enforces strict numerical parity within tolerance 1e-7.
        """
        adj_high = load_matrix("adj_high", dev_only=True, include_warmup=True)
        adj_low = load_matrix("adj_low", dev_only=True, include_warmup=True)
        bar_q = load_bar_quality_mask(dev_only=True, include_warmup=True)
        sid_msft = "MSFT R735QTJ8XC9X"
        d_check = "2000-07-05"

        # Independent calculation from 20 bars of High and Low
        h_20 = adj_high.loc[:d_check, sid_msft].iloc[-20:].values
        l_20 = adj_low.loc[:d_check, sid_msft].iloc[-20:].values
        exp_park = float(np.sqrt(np.mean((np.log(h_20 / l_20) ** 2) / (4.0 * np.log(2.0)))))

        f_park = ParkinsonVolatilityFeature(window=20)
        res_park = f_park.compute({"adj_high": adj_high[[sid_msft]], "adj_low": adj_low[[sid_msft]]},
                                  bar_quality_mask=bar_q[[sid_msft]])
        act_park = float(res_park.loc[d_check, sid_msft])

        diff = abs(act_park - exp_park)
        self.assertLess(diff, 1e-7, f"Parkinson volatility deviated from independent numpy formula by {diff}")
        self.assertAlmostEqual(act_park, exp_park, places=7)


if __name__ == "__main__":
    unittest.main()
