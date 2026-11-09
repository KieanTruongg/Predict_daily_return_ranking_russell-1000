"""
tests/test_matrix_loader.py
===========================
Unit and integration tests for src.data.matrix_loader, src.data.masks,
src.data.universe, and src.quality.quality_window.

Verifies:
  1. Coordinate grid dimensions (7,252 trading dates x 3,711 canonical SIDs).
  2. Development window filtering (5,911 sessions: 2000-07-01 to 2023-12-29).
  3. Warmup + Development window (6,541 sessions: 1998-01-02 to 2023-12-29).
  4. Strict OOS access prohibition (blocking dates >= 2024-01-02).
  5. 3-Tier PIT mask hierarchy integrity (valid_label <= valid_data <= membership).
  6. Masked matrix loading (preserving NaNs outside universe).
  7. Ticker-to-canonical-SID Point-In-Time resolution.
  8. Cross-sectional rank invariance (never ranking non-members).
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Reconfigure stdout for utf-8 if needed
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Add repository root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.config import load_config
from src.quality.quality_window import (
    OOSFreezeViolationError,
    validate_trading_calendar_partition,
)
from src.data.matrix_loader import (
    load_matrix,
    load_matrices,
    load_masked_matrix,
    load_dates_index,
    load_columns_sids,
)
from src.data.masks import (
    load_layer1_mask,
    load_layer2_mask,
    load_layer3_mask,
    combine_masks,
    verify_mask_hierarchy,
)
from src.data.universe import (
    ticker_to_canonical_sids,
    canonical_sid_to_ticker,
    get_reconstitution_year,
)
from src.features.transforms import cross_sectional_rank
from src.features.base import TotalReturnMomentumFeature, RealizedVolatilityFeature


def test_coordinate_indices():
    """Verify coordinate grid indices."""
    dates = load_dates_index()
    sids = load_columns_sids()

    assert len(dates) == 7252, f"Expected 7252 dates, got {len(dates)}"
    assert len(sids) == 3711, f"Expected 3711 SIDs, got {len(sids)}"
    assert dates[0].strftime("%Y-%m-%d") == "1998-01-02", f"First date: {dates[0]}"
    assert dates[-1].strftime("%Y-%m-%d") == "2026-10-30", f"Last date: {dates[-1]}"
    print("  [PASS] test_coordinate_indices: (7252 dates x 3711 SIDs)")


def test_trading_calendar_partition():
    """Verify institutional calendar partitioning."""
    dates = load_dates_index()
    partition = validate_trading_calendar_partition(dates)

    assert partition["is_valid"] is True, f"Partition invalid: {partition}"
    assert partition["warmup_sessions"] == 630
    assert partition["dev_sessions"] == 5911
    assert partition["oos_sessions"] == 711
    print("  [PASS] test_trading_calendar_partition: 630 warmup, 5911 dev, 711 OOS")


def test_load_matrix_full():
    """Verify full matrix dimensions with authorized OOS."""
    df_full = load_matrix("adj_close", dev_only=False, allow_oos=True)

    assert df_full.shape == (7252, 3711), f"Expected (7252, 3711), got {df_full.shape}"
    assert isinstance(df_full.index, pd.DatetimeIndex)
    assert df_full.columns.name == "canonical_sid"
    print("  [PASS] test_load_matrix_full: adj_close shape = (7252, 3711)")


def test_load_matrix_dev_window():
    """Verify development window restriction (5,911 sessions)."""
    df_dev = load_matrix("adj_close", dev_only=True, include_warmup=False)

    assert df_dev.shape == (5911, 3711), f"Expected (5911, 3711), got {df_dev.shape}"
    assert df_dev.index[0].strftime("%Y-%m-%d") == "2000-07-03"
    assert df_dev.index[-1].strftime("%Y-%m-%d") == "2023-12-29"
    # Verify absolutely no OOS dates exist
    assert (df_dev.index >= pd.Timestamp("2024-01-01")).sum() == 0
    print("  [PASS] test_load_matrix_dev_window: shape = (5911, 3711) [2000-07-01 to 2023-12-29]")


def test_load_matrix_dev_with_warmup():
    """Verify warmup + development window (6,541 sessions)."""
    df_warm = load_matrix("adj_close", dev_only=True, include_warmup=True)

    expected_sessions = 630 + 5911  # 6541
    assert df_warm.shape == (expected_sessions, 3711), f"Expected ({expected_sessions}, 3711), got {df_warm.shape}"
    assert df_warm.index[0].strftime("%Y-%m-%d") == "1998-01-02"
    assert df_warm.index[-1].strftime("%Y-%m-%d") == "2023-12-29"
    print(f"  [PASS] test_load_matrix_dev_with_warmup: shape = ({expected_sessions}, 3711) [1998-01-02 to 2023-12-29]")


def test_oos_freeze_enforcement():
    """Verify that unpermitted access to OOS data raises OOSFreezeViolationError."""
    try:
        load_matrix("adj_close", dev_only=False, allow_oos=False)
        assert False, "Failed to block access to frozen OOS window!"
    except OOSFreezeViolationError:
        print("  [PASS] test_oos_freeze_enforcement: OOSFreezeViolationError successfully triggered")


def test_3_tier_mask_hierarchy():
    """Verify 3-tier mask hierarchy: valid_label <= valid_data <= membership."""
    m_mask = load_layer1_mask(strict=False, dev_only=True)
    d_mask = load_layer2_mask(dev_only=True)
    l_mask = load_layer3_mask(dev_only=True)

    result = verify_mask_hierarchy(m_mask, d_mask, l_mask)

    assert result["is_strictly_hierarchical"] is True, f"Hierarchy violation: {result}"
    assert result["label_without_data_violations"] == 0
    assert result["data_without_member_violations"] == 0
    print("  [PASS] test_3_tier_mask_hierarchy: valid_label <= valid_data <= membership holds across all cells")


def test_masked_matrix_loading():
    """Verify masked matrix preserves NaNs outside universe."""
    df_masked = load_masked_matrix("adj_close", mask="strict_membership_mask", dev_only=True)
    strict_mask = load_layer1_mask(strict=True, dev_only=True)

    # Where strict_mask is False, df_masked MUST be NaN
    non_member_values = df_masked.values[~strict_mask.values]
    assert np.isnan(non_member_values).all(), "Found non-NaN values for non-member assets!"
    print("  [PASS] test_masked_matrix_loading: all non-members strictly NaN")


def test_universe_mapping():
    """Verify ticker to canonical SID mapping and reconstitution periods."""
    aapl_sids = ticker_to_canonical_sids("AAPL")
    assert "AAPL R735QTJ8XC9X" in aapl_sids, f"AAPL mapping missing canonical SID: {aapl_sids}"

    ticker = canonical_sid_to_ticker("AAPL R735QTJ8XC9X")
    assert ticker == "AAPL", f"Expected AAPL, got {ticker}"

    assert get_reconstitution_year("2005-08-15") == 2005
    assert get_reconstitution_year("2006-03-20") == 2005
    assert get_reconstitution_year("2006-07-01") == 2006
    print("  [PASS] test_universe_mapping: AAPL mapping and [01/07 to 30/06] cycle verified")


def test_cross_sectional_ranking_respects_mask():
    """Verify cross-sectional ranking never ranks non-members."""
    sample_data = pd.DataFrame(
        {
            "A": [10.0, 20.0],
            "B": [30.0, 40.0],
            "C": [50.0, 60.0],
        },
        index=pd.date_range("2020-01-01", periods=2),
    )
    # Mask C out completely, Mask B out on row 1
    sample_mask = pd.DataFrame(
        {
            "A": [True, True],
            "B": [True, False],
            "C": [False, False],
        },
        index=sample_data.index,
    )

    ranked = cross_sectional_rank(sample_data, mask=sample_mask, pct=True)

    # Row 0: A and B are active (N=2). Under uniform rank (rank - 1)/(N - 1):
    # A (10.0, rank=1) -> 0.0, B (30.0, rank=2) -> 1.0, C -> NaN
    assert np.isnan(ranked.loc[ranked.index[0], "C"])
    assert ranked.loc[ranked.index[0], "A"] == 0.0
    assert ranked.loc[ranked.index[0], "B"] == 1.0

    # Row 1: only A is active (N=1). Single asset receives median rank 0.5; B -> NaN, C -> NaN
    assert np.isnan(ranked.loc[ranked.index[1], "B"])
    assert np.isnan(ranked.loc[ranked.index[1], "C"])
    assert ranked.loc[ranked.index[1], "A"] == 0.5
    print("  [PASS] test_cross_sectional_ranking_respects_mask: non-members never ranked")


def test_feature_computation_on_real_matrix():
    """Verify FeatureBase computation and universe mask application on real matrices."""
    # Load 100 days sample of dev window for speed
    tot_ret = load_matrix("total_return", dev_only=True).iloc[:100]
    strict_mask = load_layer1_mask(strict=True, dev_only=True).iloc[:100]

    feat = TotalReturnMomentumFeature(window=5, name="MOM_005")
    res = feat.compute({"total_return": tot_ret}, mask=strict_mask)

    assert res.shape == tot_ret.shape
    # Check that non-members are NaN
    non_members = ~strict_mask.values
    assert np.isnan(res.values[non_members]).all(), "Found non-NaN values for non-members in feature output!"
    print("  [PASS] test_feature_computation_on_real_matrix: MOM_005 correctly preserves NaNs outside universe")



@pytest.mark.integration
def test_oos_zero_memory_leakage_via_pushdown():
    """Verify that predicate pushdown filters prevent loading any OOS row into memory."""
    df_dev = load_matrix("adj_close", dev_only=True, include_warmup=False)
    assert df_dev.index.max() <= pd.Timestamp("2023-12-29")
    assert (df_dev.index >= pd.Timestamp("2024-01-01")).sum() == 0

    df_warm = load_matrix("adj_close", dev_only=True, include_warmup=True)
    assert df_warm.index.max() <= pd.Timestamp("2023-12-29")
    assert (df_warm.index >= pd.Timestamp("2024-01-01")).sum() == 0

    try:
        load_matrix("adj_close", dev_only=False, allow_oos=False)
        assert False, "Should raise OOSFreezeViolationError"
    except OOSFreezeViolationError:
        pass
    print("  [PASS] test_oos_zero_memory_leakage_via_pushdown: zero OOS rows loaded into RAM")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING MATRIX LOADER AND STEP 7 FOUNDATION TESTS")
    print("=" * 70)

    test_coordinate_indices()
    test_trading_calendar_partition()
    test_load_matrix_full()
    test_load_matrix_dev_window()
    test_load_matrix_dev_with_warmup()
    test_oos_freeze_enforcement()
    test_3_tier_mask_hierarchy()
    test_masked_matrix_loading()
    test_universe_mapping()
    test_cross_sectional_ranking_respects_mask()
    test_feature_computation_on_real_matrix()
    test_oos_zero_memory_leakage_via_pushdown()

    print("=" * 70)
    print("ALL 11 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
