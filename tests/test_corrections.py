# -*- coding: utf-8 -*-
"""
tests/test_corrections.py
=========================
Unit tests for the unified market data corrections subsystem (src.data.corrections).
Verifies:
1. Loading and parsing of market_data_corrections_and_exceptions.csv.
2. Field-level quarantine nullifies ONLY target fields and preserves unaffected fields.
3. Full-bar quarantine sets is_bad_data_period=True and nullifies returns.
4. Idempotency: applying corrections repeatedly yields identical results.
5. Deterministic reproduction from unmodified inputs.
"""

import numpy as np
import pandas as pd
import pytest

from src.data.corrections import (
    CorrectionEntry,
    load_market_corrections,
    apply_corrections_to_dataframe,
    get_field_quarantine_mask,
)


def test_load_market_corrections_structure():
    """Verify market corrections load properly from CSV with typed properties."""
    corrs = load_market_corrections()
    assert len(corrs) >= 19, f"Expected at least 19 corrections, found {len(corrs)}"

    event_ids = [c.event_id for c in corrs]
    assert "CORR_014" in event_ids  # GMT
    assert "CORR_015" in event_ids  # HOMS
    assert "CORR_016" in event_ids  # RGC
    assert "CORR_017" in event_ids  # CEPH
    assert "CORR_018" in event_ids  # FRT
    assert "CORR_019" in event_ids  # TR

    corr_gmt = next(c for c in corrs if c.event_id == "CORR_014")
    assert corr_gmt.is_field_quarantine is True
    assert corr_gmt.is_bar_quarantine is False
    assert "open" in corr_gmt.target_fields
    assert "low" in corr_gmt.target_fields
    assert "adj_open" in corr_gmt.target_fields
    assert "adj_low" in corr_gmt.target_fields

    corr_homs = next(c for c in corrs if c.event_id == "CORR_015")
    assert corr_homs.is_bar_quarantine is True
    assert corr_homs.is_field_quarantine is False

    corr_rgc = next(c for c in corrs if c.event_id == "CORR_016")
    assert corr_rgc.is_field_quarantine is True
    assert "open" in corr_rgc.target_fields

    corr_ceph = next(c for c in corrs if c.event_id == "CORR_017")
    assert corr_ceph.is_field_quarantine is True
    assert "high" in corr_ceph.target_fields
    assert "open" in corr_ceph.target_fields
    assert "low" in corr_ceph.target_fields

    corr_frt = next(c for c in corrs if c.event_id == "CORR_018")
    assert corr_frt.is_field_quarantine is True
    assert "high" in corr_frt.target_fields
    assert "low" in corr_frt.target_fields

    corr_tr = next(c for c in corrs if c.event_id == "CORR_019")
    assert corr_tr.is_bar_quarantine is True
    assert corr_tr.quarantine_recovery_return is True


def test_field_quarantine_preserves_unaffected_fields():
    """
    CRITICAL INVARIANT:
    Field-level quarantine MUST set specified fields (e.g. open, low, adj_open, adj_low) to NaN,
    while leaving close, adj_close, volume, daily_return, and total_return 100% UNTOUCHED!
    is_bad_data_period must remain False!
    """
    dates = pd.date_range("2007-01-20", periods=5, freq="B")
    sid = "TEST_SID"

    df_raw = pd.DataFrame({
        "date": dates,
        "canonical_sid": sid,
        "open": [45.0, 46.0, 0.01, 45.5, 46.0],
        "high": [45.5, 46.5, 46.0, 46.0, 46.5],
        "low": [44.8, 45.8, 0.01, 45.0, 45.8],
        "close": [45.2, 46.32, 44.25, 45.8, 46.2],
        "adj_open": [45.0, 46.0, 0.01, 45.5, 46.0],
        "adj_high": [45.5, 46.5, 46.0, 46.0, 46.5],
        "adj_low": [44.8, 45.8, 0.01, 45.0, 45.8],
        "adj_close": [45.2, 46.32, 44.25, 45.8, 46.2],
        "volume": [1000.0, 2000.0, 4820200.0, 1500.0, 1200.0],
        "daily_return": [0.01, 0.024779, -0.044689, 0.035028, 0.008734],
        "total_return": [0.01, 0.024779, -0.044689, 0.035028, 0.008734],
        "is_consecutive_session": [True, True, True, True, True],
    })

    corr_entry = CorrectionEntry(
        event_id="TEST_CORR_FIELD",
        source_ticker="TEST",
        canonical_sid=sid,
        start_date=dates[2],
        end_date=dates[2],
        correction_layer="QUALITY_FLAG_BAD_TICK",
        parameter_name="quarantine_fields",
        parameter_value="open,low",
        evidence_source="Unit Test",
        forensic_explanation="Errant 0.01 print on open and low",
        action_taken="Field-level quarantine",
    )

    df_cleaned = apply_corrections_to_dataframe(df_raw, corrections=[corr_entry])

    # 1. Affected fields must be NaN at index 2
    assert np.isnan(df_cleaned.loc[2, "open"])
    assert np.isnan(df_cleaned.loc[2, "low"])
    assert np.isnan(df_cleaned.loc[2, "adj_open"])
    assert np.isnan(df_cleaned.loc[2, "adj_low"])

    # 2. Unaffected fields at index 2 must be IDENTICAL to raw
    assert df_cleaned.loc[2, "close"] == 44.25
    assert df_cleaned.loc[2, "adj_close"] == 44.25
    assert df_cleaned.loc[2, "high"] == 46.0
    assert df_cleaned.loc[2, "adj_high"] == 46.0
    assert df_cleaned.loc[2, "volume"] == 4820200.0
    assert df_cleaned.loc[2, "daily_return"] == -0.044689
    assert df_cleaned.loc[2, "total_return"] == -0.044689
    assert df_cleaned.loc[2, "is_consecutive_session"] == True

    # 3. is_bad_data_period must be False
    assert df_cleaned.loc[2, "is_bad_data_period"] == False

    # 4. Other rows must be completely untouched
    for i in [0, 1, 3, 4]:
        for col in ["open", "high", "low", "close", "daily_return"]:
            assert df_cleaned.loc[i, col] == df_raw.loc[i, col]


def test_bar_quarantine_affects_full_bar():
    """Verify full-bar quarantine sets is_bad_data_period=True and invalidates returns."""
    dates = pd.date_range("2020-03-18", periods=5, freq="B")
    sid = "TEST_BAR"

    df_raw = pd.DataFrame({
        "date": dates,
        "canonical_sid": sid,
        "open": [5.0, 5.0, 0.75, 5.2, 5.3],
        "close": [5.1, 5.2, 0.75, 5.3, 5.4],
        "daily_return": [0.01, 0.0196, -0.8557, 6.0667, 0.0188],
        "total_return": [0.01, 0.0196, -0.8557, 6.0667, 0.0188],
        "is_consecutive_session": [True, True, True, True, True],
    })

    corr_entry = CorrectionEntry(
        event_id="TEST_CORR_BAR",
        source_ticker="TEST",
        canonical_sid=sid,
        start_date=dates[2],
        end_date=dates[2],
        correction_layer="QUALITY_FLAG_BAD_TICK",
        parameter_name="quarantine_bad_tick",
        parameter_value="True",
        evidence_source="Unit Test",
        forensic_explanation="Errant close print with fake rebound",
        action_taken="Quarantine bar and rebound return",
    )

    df_cleaned = apply_corrections_to_dataframe(df_raw, corrections=[corr_entry])

    # Bar at index 2 must be bad
    assert df_cleaned.loc[2, "is_bad_data_period"] == True
    assert np.isnan(df_cleaned.loc[2, "daily_return"])
    assert np.isnan(df_cleaned.loc[2, "total_return"])
    assert df_cleaned.loc[2, "is_consecutive_session"] == False

    # Next session (index 3) recovery return must also be NaN
    assert np.isnan(df_cleaned.loc[3, "daily_return"])
    assert np.isnan(df_cleaned.loc[3, "total_return"])
    assert df_cleaned.loc[3, "is_consecutive_session"] == False


def test_corrections_idempotency():
    """Verify that applying corrections repeatedly produces identical results."""
    dates = pd.date_range("2008-07-20", periods=5, freq="B")
    sid = "RGC SEIRNAFAFF51"

    df_raw = pd.DataFrame({
        "date": dates,
        "canonical_sid": sid,
        "open": [16.08, 16.17, 0.01, 16.27, 17.00],
        "close": [15.98, 16.14, 16.37, 16.94, 16.32],
        "low": [15.75, 15.97, 0.01, 16.27, 16.25],
        "daily_return": [0.01, 0.01, 0.0142, 0.0348, -0.0366],
    })

    corrs = load_market_corrections()
    df_once = apply_corrections_to_dataframe(df_raw, corrections=corrs)
    df_twice = apply_corrections_to_dataframe(df_once, corrections=corrs)

    pd.testing.assert_frame_equal(df_once, df_twice)


def test_field_quarantine_mask_generation():
    """Verify 2D field quarantine mask generates properly for specific fields."""
    dates = pd.date_range("2007-01-20", periods=10, freq="B")
    cols = pd.Index(["GMT R735QTJ8XC9X", "AAPL R735QTJ8XC9X"])

    mask_open = get_field_quarantine_mask("open", dates, cols)
    mask_close = get_field_quarantine_mask("close", dates, cols)

    # For GMT on 2007-01-25: open is False, close is True!
    gmt_date = pd.Timestamp("2007-01-25")
    assert mask_open.loc[gmt_date, "GMT R735QTJ8XC9X"] == False
    assert mask_close.loc[gmt_date, "GMT R735QTJ8XC9X"] == True

    # For AAPL on 2007-01-25: both are True
    assert mask_open.loc[gmt_date, "AAPL R735QTJ8XC9X"] == True
    assert mask_close.loc[gmt_date, "AAPL R735QTJ8XC9X"] == True


def test_universal_input_based_return_rule_low_cpth_homs_gmt():
    """
    Verify regression on LOW, CPTH, HOMS, and GMT under the universal return rule:
    1. LOW (2008-06-10..17 quarantined): return on 2008-06-18 must be NaN without stitching.
    2. CPTH (2001-02-02..14 quarantined): return on 2001-02-15 must be NaN without stitching.
    3. HOMS (1999-08-04 pre-IPO quarantined): return on 1999-08-05 must be NaN without stitching.
    4. GMT (2007-01-25 open/low quarantined): Close and returns on 2007-01-25 and 2007-01-26 MUST be valid!
    """
    corrs = load_market_corrections()
    corr_dict = {c.event_id: c for c in corrs}

    # 1. LOW
    corr_low = corr_dict["CORR_012"]
    assert corr_low.is_bar_quarantine is True
    assert corr_low.quarantine_recovery_return is True

    # 2. CPTH
    corr_cpth = corr_dict["CORR_013"]
    assert corr_cpth.is_bar_quarantine is True
    assert corr_cpth.quarantine_recovery_return is True

    # 3. HOMS
    corr_homs = corr_dict["CORR_015"]
    assert corr_homs.is_bar_quarantine is True
    assert corr_homs.quarantine_recovery_return is True

    # 4. GMT
    corr_gmt = corr_dict["CORR_014"]
    assert corr_gmt.is_field_quarantine is True
    assert corr_gmt.is_bar_quarantine is False
    assert corr_gmt.quarantine_recovery_return is False

    # 5. Synthetic 4-bar simulation of an errant close at session 2
    dates = pd.date_range("2008-06-16", periods=4, freq="B")
    df_sim = pd.DataFrame({
        "date": dates,
        "canonical_sid": "LOW R735QTJ8XC9X",
        "open": [72.0, 71.65, 23.33, 23.10],
        "close": [70.65, 71.74, 23.11, 23.57],
        "adj_close": [70.65, 71.74, 23.11, 23.57],
        "daily_return": [0.01, 0.0154, -0.6778, 0.0199],
        "total_return": [0.01, 0.0154, -0.6778, 0.0199],
        "is_consecutive_session": [True, True, True, True],
    })

    sim_corr = CorrectionEntry(
        event_id="SIM_LOW",
        source_ticker="LOW",
        canonical_sid="LOW R735QTJ8XC9X",
        start_date=dates[0],
        end_date=dates[1],
        correction_layer="QUALITY_FLAG_COLLISION",
        parameter_name="quarantine_bad_data_period",
        parameter_value="True",
        evidence_source="Unit Test",
        forensic_explanation="Simulated rogue collision",
        action_taken="Quarantine bar",
    )

    df_res = apply_corrections_to_dataframe(df_sim, corrections=[sim_corr])

    # Indices 0 and 1 were quarantined
    assert np.isnan(df_res.loc[0, "daily_return"])
    assert np.isnan(df_res.loc[1, "daily_return"])
    assert df_res.loc[1, "is_consecutive_session"] == False

    # Index 2 (recovery session, 2008-06-18) MUST be NaN without stitching!
    assert np.isnan(df_res.loc[2, "daily_return"])
    assert np.isnan(df_res.loc[2, "total_return"])
    assert df_res.loc[2, "is_consecutive_session"] == False

    # Index 3 (subsequent clean session, 2008-06-19) MUST be valid!
    assert not np.isnan(df_res.loc[3, "daily_return"])
    assert np.isclose(df_res.loc[3, "daily_return"], 0.0199, atol=1e-4)
    assert df_res.loc[3, "is_consecutive_session"] == True

