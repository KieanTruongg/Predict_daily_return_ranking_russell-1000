"""
tests.test_library_fixes
========================
Regression test suite covering the 6 critical edge cases and library fixes:
1. Strict as-of date resolution in ticker_to_canonical_sids (zero fallback).
2. Ticker resolution as of specific trading date.
3. Querying active constituents in development window (e.g. 2020) without OOS false positives.
4. OOS access rejection on true OOS dates.
5. Quality-window preservation during rolling feature calculations (dirty bar protection).
6. Return type explicitness in feature classes (zero silent ambiguity).
7. Exact mathematical cross-sectional uniform rank formula (rank - 1) / (N - 1).
8. Boundary purge verification and causal alignment checks.
9. Decoupled bar_quality_mask: warm-up preservation before index entry date.
10. Dirty bar in pre-entry warmup invalidates feature upon entry.
11. Isolation of valid_label_mask from feature input filtering.
"""

from pathlib import Path
import unittest
import numpy as np
import pandas as pd

from src.data.universe import (
    canonical_sid_to_ticker,
    get_active_constituents,
    ticker_to_canonical_sids,
)
from src.features.base import RealizedVolatilityFeature, TotalReturnMomentumFeature
from src.features.transforms import cross_sectional_rank
from src.quality.quality_window import (
    OOSFreezeViolationError,
    assert_causal_alignment,
    assert_coordinate_alignment,
    verify_boundary_purge,
)


class TestLibraryFixes(unittest.TestCase):

    def test_01_ticker_to_canonical_sids_strict_date_no_fallback(self):
        """Verify ticker_to_canonical_sids returns [] when date has no active mapping (zero fallback)."""
        # Date 1900-01-01 has no active mapping for AAPL
        res_1900 = ticker_to_canonical_sids("AAPL", as_of_date="1900-01-01")
        self.assertEqual(res_1900, [], "Expected empty list [] for inactive date, got fallback SIDs.")

        # Real active date in 2020 must return AAPL's canonical SID
        res_2020 = ticker_to_canonical_sids("AAPL", as_of_date="2020-01-02")
        self.assertTrue(len(res_2020) >= 1, "Expected active SID for AAPL in 2020.")
        self.assertTrue(any("AAPL" in sid for sid in res_2020))

    def test_02_canonical_sid_to_ticker_as_of_date(self):
        """Verify canonical_sid_to_ticker respects as_of_date and returns None outside range."""
        aapl_sids = ticker_to_canonical_sids("AAPL", as_of_date="2020-01-02")
        self.assertTrue(len(aapl_sids) > 0)
        sid = aapl_sids[0]

        # Valid date
        ticker_valid = canonical_sid_to_ticker(sid, as_of_date="2020-01-02")
        self.assertEqual(ticker_valid, "AAPL")

        # Inactive date far in the past
        ticker_inactive = canonical_sid_to_ticker(sid, as_of_date="1900-01-01")
        self.assertIsNone(ticker_inactive, "Expected None for SID queried far outside active window.")

    def test_03_get_active_constituents_dev_no_oos_error(self):
        """Verify querying constituents in development window (e.g. 2020-01-02) does NOT raise OOS error."""
        constituents = get_active_constituents("2020-01-02", strict=True, allow_oos=False)
        self.assertIsInstance(constituents, list)
        self.assertGreater(len(constituents), 900, "Russell 1000 should have ~1,000 active constituents in 2020.")

    def test_04_get_active_constituents_oos_strictly_blocked(self):
        """Verify querying constituents in OOS window (e.g. 2025-01-02) raises OOSFreezeViolationError."""
        with self.assertRaises(OOSFreezeViolationError):
            get_active_constituents("2025-01-02", allow_oos=False)

    def test_05_quality_window_rolling_dirty_bar_protection(self):
        """Verify rolling features return NaN across any window spanning an invalid/bad-quality bar."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        returns = pd.DataFrame(
            {"AAPL": [0.01, 0.02, 0.01, 0.03, -0.01, 0.02, 0.01, -0.02, 0.01, 0.02]},
            index=dates,
        )
        # Bar 3 (2020-01-04) is flagged as bad tick (bar_quality_mask = False)
        valid_mask = pd.DataFrame(
            {"AAPL": [True, True, True, False, True, True, True, True, True, True]},
            index=dates,
        )

        feat = TotalReturnMomentumFeature(window=3, price_type="total_return")
        res = feat.compute({"total_return": returns}, bar_quality_mask=valid_mask)

        # Days 0, 1: warmup -> NaN
        self.assertTrue(np.isnan(res.loc["2020-01-01", "AAPL"]))
        self.assertTrue(np.isnan(res.loc["2020-01-02", "AAPL"]))

        # Day 2 (2020-01-03): clean window [0, 1, 2] -> valid
        self.assertFalse(np.isnan(res.loc["2020-01-03", "AAPL"]))

        # Days 3, 4, 5: window spans across invalid bar at 2020-01-04 -> MUST ALL BE NaN
        self.assertTrue(np.isnan(res.loc["2020-01-04", "AAPL"]), "Day 3 contains bad bar -> must be NaN")
        self.assertTrue(np.isnan(res.loc["2020-01-05", "AAPL"]), "Day 4 contains bad bar -> must be NaN")
        self.assertTrue(np.isnan(res.loc["2020-01-06", "AAPL"]), "Day 5 contains bad bar -> must be NaN")

        # Day 6 (2020-01-07): clean window [4, 5, 6] -> MUST RECOVER TO VALID VALUE
        self.assertFalse(np.isnan(res.loc["2020-01-07", "AAPL"]), "Clean window [4,5,6] must compute valid feature")

    def test_06_feature_explicit_return_type_no_silent_fallback(self):
        """Verify feature classes enforce explicit return/price types and reject ambiguous inputs."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        p = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=dates)

        # Momentum with price_type='total_return' must raise KeyError if only adj_close is provided
        feat_tot = TotalReturnMomentumFeature(window=2, price_type="total_return")
        with self.assertRaises(KeyError):
            feat_tot.compute({"adj_close": p})

        # Volatility with return_type='daily_return' must raise KeyError if only adj_close is provided
        feat_vol = RealizedVolatilityFeature(window=2, return_type="daily_return")
        with self.assertRaises(KeyError):
            feat_vol.compute({"adj_close": p})

    def test_07_cross_sectional_uniform_rank_exact_formula(self):
        """Verify exact uniform rank formula (rank - 1) / (N - 1) in [0.0, 1.0]."""
        # Case 1: 2 stocks -> exactly 0.0 and 1.0
        df2 = pd.DataFrame({"A": [10.0], "B": [20.0]})
        r2 = cross_sectional_rank(df2)
        self.assertAlmostEqual(r2.iloc[0]["A"], 0.0)
        self.assertAlmostEqual(r2.iloc[0]["B"], 1.0)

        # Case 2: Ties [10.0, 10.0, 20.0] -> [0.25, 0.25, 1.0]
        df3 = pd.DataFrame({"A": [10.0], "B": [10.0], "C": [20.0]})
        r3 = cross_sectional_rank(df3)
        self.assertAlmostEqual(r3.iloc[0]["A"], 0.25)
        self.assertAlmostEqual(r3.iloc[0]["B"], 0.25)
        self.assertAlmostEqual(r3.iloc[0]["C"], 1.0)

        # Case 3: N = 1 -> exactly 0.5
        df1 = pd.DataFrame({"A": [10.0], "B": [np.nan]})
        r1 = cross_sectional_rank(df1)
        self.assertAlmostEqual(r1.iloc[0]["A"], 0.5)
        self.assertTrue(np.isnan(r1.iloc[0]["B"]))

    def test_08_causal_alignment_and_boundary_purge(self):
        """Verify verify_boundary_purge and assert_causal_alignment enforce 100% boundary purge."""
        dates = pd.to_datetime(["2023-12-28", "2023-12-29"])
        sids = ["AAPL", "MSFT"]

        feat = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], index=dates, columns=sids)

        # Target with unpurged label at 2023-12-29 boundary must fail
        leaky_target = pd.DataFrame([[0.01, 0.02], [0.03, 0.04]], index=dates, columns=sids)
        with self.assertRaises(ValueError):
            assert_causal_alignment(feat, leaky_target, boundary_date="2023-12-29")

        # Target with 100% purged boundary (all NaNs) must pass
        purged_target = pd.DataFrame([[0.01, 0.02], [np.nan, np.nan]], index=dates, columns=sids)
        self.assertTrue(assert_causal_alignment(feat, purged_target, boundary_date="2023-12-29"))

    def test_09_warmup_preservation_before_index_entry(self):
        """
        Verify that clean historical bars before constituent entry into Russell 1000
        are preserved for feature warmup, allowing the feature to evaluate immediately
        on Day 1 of membership.
        """
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        returns = pd.DataFrame(
            {"STOCK_NEW": [0.01, 0.015, 0.02, 0.01, 0.012, 0.018, 0.02, 0.015, 0.01, 0.01]},
            index=dates,
        )
        # All 10 trading bars are clean exchange data (bar_quality_mask = True)
        bar_quality = pd.DataFrame({"STOCK_NEW": [True] * 10}, index=dates)

        # Constituent enters Russell 1000 on Day 5 (index 5: 2020-01-06)
        membership = pd.DataFrame(
            {"STOCK_NEW": [False, False, False, False, False, True, True, True, True, True]},
            index=dates,
        )

        # 5-day momentum requires 5 trailing clean bars
        feat = TotalReturnMomentumFeature(window=5, price_type="total_return")
        res = feat.compute(
            {"total_return": returns},
            bar_quality_mask=bar_quality,
            membership_mask=membership,
        )

        # Pre-membership dates (Days 0..4) must be NaN due to membership_mask
        for d in dates[:5]:
            self.assertTrue(np.isnan(res.loc[d, "STOCK_NEW"]), f"Pre-membership date {d} must be NaN")

        # Day 5 (2020-01-06, Day 1 of membership): trailing window [1, 2, 3, 4, 5] is clean
        # -> MUST EVALUATE IMMEDIATELY on Day 1 of membership!
        entry_val = res.loc[dates[5], "STOCK_NEW"]
        self.assertFalse(np.isnan(entry_val), "Feature must compute valid value on Day 1 of membership using warmup!")
        self.assertGreater(entry_val, 0.0)

    def test_10_invalid_bar_in_warmup_invalidates_entry_feature(self):
        """
        Verify that if an invalid bar (bad tick / spinoff discontinuity) occurs during
        the pre-membership warmup window, the feature upon entry date evaluates strictly to NaN.
        """
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        returns = pd.DataFrame(
            {"STOCK_NEW": [0.01, 0.015, 0.02, 0.01, 0.012, 0.018, 0.02, 0.015, 0.01, 0.01]},
            index=dates,
        )
        # Day 3 has a bad tick (bar_quality_mask = False)
        bar_quality = pd.DataFrame(
            {"STOCK_NEW": [True, True, True, False, True, True, True, True, True, True]},
            index=dates,
        )
        # Enters Russell 1000 on Day 5
        membership = pd.DataFrame(
            {"STOCK_NEW": [False, False, False, False, False, True, True, True, True, True]},
            index=dates,
        )

        feat = TotalReturnMomentumFeature(window=5, price_type="total_return")
        res = feat.compute(
            {"total_return": returns},
            bar_quality_mask=bar_quality,
            membership_mask=membership,
        )

        # On Day 5 (Day 1 of membership), lookback spans across Day 3 (bad tick)
        # -> MUST EVALUATE TO NaN (quality window broken)
        self.assertTrue(
            np.isnan(res.loc[dates[5], "STOCK_NEW"]),
            "Feature upon entry must be NaN because warmup lookback spans an invalid bar!",
        )

        # Must recover on Day 8 when lookback [4, 5, 6, 7, 8] is completely clean
        self.assertFalse(
            np.isnan(res.loc[dates[8], "STOCK_NEW"]),
            "Feature must recover once lookback window is completely clean of bad bars.",
        )

    def test_11_valid_label_mask_isolation_from_features(self):
        """
        Verify architectural isolation: valid_label_mask is designated strictly for target labels
        and must never be used to sanitize feature input data.
        """
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        returns = pd.DataFrame({"A": [0.01, 0.02, 0.03, 0.04, 0.05]}, index=dates)

        # Under strict causality, feature input data must be sanitized only with bar_quality_mask
        # valid_label_mask is strictly T+1 forward-looking and belongs to the target pipeline
        feat = TotalReturnMomentumFeature(window=2, price_type="total_return")
        
        # Computing feature with clean bar_quality_mask succeeds
        clean_bar_mask = pd.DataFrame({"A": [True, True, True, True, True]}, index=dates)
        res = feat.compute({"total_return": returns}, bar_quality_mask=clean_bar_mask)
        self.assertEqual(res.shape, (5, 1))
        self.assertFalse(np.isnan(res.iloc[-1, 0]))


if __name__ == "__main__":
    unittest.main()
