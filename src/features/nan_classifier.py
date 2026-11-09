"""
src.features.nan_classifier
===========================
Production NaN Classification Engine for Tier 3 Feature Store.

Deconstructs all NaNs occurring within Russell 1000 index membership into
exact, mutually exclusive causal categories based on the mathematical contract
of each feature:
1. nan_due_to_quality_at_t: Bad bar or field-level quarantine at date T.
2. nan_due_to_lack_of_history: Insufficient trading history since listing/IPO (< window size W).
3. nan_due_to_window_defect_or_halt: History exists, but required window endpoints (T-W) or
   clean bar thresholds inside the lookback window are breached (halts, gaps, defects).
4. nan_due_to_zero_denom_or_invalid: Zero volume (volume=0 in Amihud/Volume Ratio) or zero price
   variance (sigma=0 in Bollinger Bands).
5. nan_due_to_rsi_state_reset: Interruption of Wilder recursive smoothing state.
6. nan_unclassified: Residual cases not matched by strict contract rules (audit check).

No catch-all else branches. True causal accounting.
"""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


# Feature window requirements
FEATURE_WINDOW_SPECS = {
    "ret_1d": {"window": 1, "inputs": ["adj_close"], "min_clean": 2, "check_t": True},
    "ret_5d": {"window": 5, "inputs": ["adj_close"], "min_clean": 6, "check_t": True},
    "ret_20d": {"window": 20, "inputs": ["adj_close"], "min_clean": 21, "check_t": True},
    "ret_60d": {"window": 60, "inputs": ["adj_close"], "min_clean": 61, "check_t": True},
    "mom_12m_skip_1m": {"window": 252, "inputs": ["adj_close"], "min_clean": 232, "check_t": False},
    "vol_realized_20d": {"window": 20, "inputs": ["adj_close"], "min_clean": 20, "check_t": True},
    "vol_realized_60d": {"window": 60, "inputs": ["adj_close"], "min_clean": 60, "check_t": True},
    "vol_parkinson_20d": {"window": 20, "inputs": ["adj_high", "adj_low"], "min_clean": 20, "check_t": True},
    "downside_deviation_20d": {"window": 20, "inputs": ["adj_close"], "min_clean": 20, "check_t": True},
    "amihud_illiq_20d": {"window": 20, "inputs": ["adj_close", "adj_volume"], "min_clean": 20, "check_t": True},
    "volume_ratio_5_20": {"window": 20, "inputs": ["adj_volume"], "min_clean": 20, "check_t": True},
    "log_dollar_volume_20d": {"window": 20, "inputs": ["adj_close", "adj_volume"], "min_clean": 20, "check_t": True},
    "ret_intraday": {"window": 1, "inputs": ["adj_open", "adj_close"], "min_clean": 1, "check_t": True},
    "ret_overnight": {"window": 1, "inputs": ["adj_open", "adj_close"], "min_clean": 2, "check_t": True},
    "rsi_14d": {"window": 14, "inputs": ["adj_close"], "min_clean": 15, "check_t": True},
    "bollinger_pct_b_20d": {"window": 20, "inputs": ["adj_close"], "min_clean": 20, "check_t": True},
}


def classify_cell_nan(
    feature_name: str,
    t_idx: int,
    sid_idx: int,
    raw_inputs: Dict[str, np.ndarray],
    bar_quality_mask: np.ndarray,
    first_valid_idx: int,
    field_quality_masks: Optional[Dict[str, np.ndarray]] = None,
) -> str:
    """
    Classifies a single NaN cell into its exact mathematical cause.
    `t_idx` is the absolute row index into `raw_inputs` and `bar_quality_mask` (including warm-up offset).
    """
    spec = FEATURE_WINDOW_SPECS.get(feature_name)
    if spec is None:
        return "nan_unclassified"

    w = spec["window"]
    check_t = spec["check_t"]
    req_inputs = spec["inputs"]

    # 1. Condition 1: nan_due_to_quality_at_t
    if check_t:
        # Check full bar quality at date T
        if not bar_quality_mask[t_idx, sid_idx]:
            return "nan_due_to_quality_at_t"
        # Check required fields at date T (including field-level quarantine)
        for inp_name in req_inputs:
            if field_quality_masks and inp_name in field_quality_masks:
                if not field_quality_masks[inp_name][t_idx, sid_idx]:
                    return "nan_due_to_quality_at_t"
            if inp_name in raw_inputs:
                val = raw_inputs[inp_name][t_idx, sid_idx]
                if not np.isfinite(val) or val <= 0.0:
                    return "nan_due_to_quality_at_t"

    # 2. Condition 2: nan_due_to_lack_of_history
    if first_valid_idx < 0:
        return "nan_due_to_lack_of_history"
    history_len = t_idx - first_valid_idx
    if history_len < w:
        return "nan_due_to_lack_of_history"

    # 3. Feature-specific checks
    # A. Multi-day Returns (ret_1d, ret_5d, ret_20d, ret_60d)
    if feature_name in ["ret_1d", "ret_5d", "ret_20d", "ret_60d"]:
        start_idx = t_idx - w
        # Endpoint T-W check
        if not bar_quality_mask[start_idx, sid_idx]:
            return "nan_due_to_window_defect_or_halt"
        p_start = raw_inputs["adj_close"][start_idx, sid_idx]
        if not np.isfinite(p_start) or p_start <= 0.0:
            return "nan_due_to_window_defect_or_halt"
        # Intermediate bars check
        win_q = bar_quality_mask[start_idx : t_idx + 1, sid_idx]
        if not np.all(win_q):
            return "nan_due_to_window_defect_or_halt"

    # B. 12-Month Momentum (mom_12m_skip_1m)
    elif feature_name == "mom_12m_skip_1m":
        # Strictly evaluates [T-252, T-21]
        win_start = t_idx - 252
        win_end = t_idx - 21
        win_q = bar_quality_mask[win_start : win_end + 1, sid_idx]
        clean_count = int(np.sum(win_q))
        if clean_count < 232:
            return "nan_due_to_window_defect_or_halt"

    # C. Parkinson Volatility (vol_parkinson_20d)
    elif feature_name == "vol_parkinson_20d":
        win_start = t_idx - w + 1
        for i in range(win_start, t_idx + 1):
            if not bar_quality_mask[i, sid_idx]:
                return "nan_due_to_window_defect_or_halt"
            for inp_name in ["adj_high", "adj_low"]:
                if field_quality_masks and inp_name in field_quality_masks:
                    if not field_quality_masks[inp_name][i, sid_idx]:
                        return "nan_due_to_window_defect_or_halt"
                if inp_name in raw_inputs:
                    v = raw_inputs[inp_name][i, sid_idx]
                    if not np.isfinite(v) or v <= 0.0:
                        return "nan_due_to_window_defect_or_halt"

    # D. Volatility & Downside Deviation
    elif feature_name in ["vol_realized_20d", "vol_realized_60d", "downside_deviation_20d"]:
        win_start = t_idx - w
        win_q = bar_quality_mask[win_start : t_idx + 1, sid_idx]
        if not np.all(win_q):
            return "nan_due_to_window_defect_or_halt"

    # E. Volume & Liquidity Features (Amihud, Volume Ratio, Dollar Volume)
    elif feature_name in ["amihud_illiq_20d", "volume_ratio_5_20", "log_dollar_volume_20d"]:
        win_start = t_idx - w + 1
        win_q = bar_quality_mask[win_start : t_idx + 1, sid_idx]
        if not np.all(win_q):
            return "nan_due_to_window_defect_or_halt"
        if "adj_volume" in raw_inputs:
            win_vol = raw_inputs["adj_volume"][win_start : t_idx + 1, sid_idx]
            if np.any(np.isnan(win_vol)) or np.any(win_vol <= 0.0):
                return "nan_due_to_zero_denom_or_invalid"

    # F. Bollinger %B
    elif feature_name == "bollinger_pct_b_20d":
        win_start = t_idx - w + 1
        win_q = bar_quality_mask[win_start : t_idx + 1, sid_idx]
        if not np.all(win_q):
            return "nan_due_to_window_defect_or_halt"
        win_prices = raw_inputs["adj_close"][win_start : t_idx + 1, sid_idx]
        if np.std(win_prices) == 0.0:
            return "nan_due_to_zero_denom_or_invalid"

    # G. RSI (rsi_14d)
    elif feature_name == "rsi_14d":
        # Requires 14 clean return deltas (15 clean prices in [T-14, T]) to seed/maintain Wilder recursion
        win_start = max(0, t_idx - 14)
        win_q = bar_quality_mask[win_start : t_idx + 1, sid_idx]
        if not np.all(win_q):
            return "nan_due_to_rsi_state_reset"

    # H. Overnight Return (ret_overnight)
    elif feature_name == "ret_overnight":
        if not bar_quality_mask[t_idx - 1, sid_idx]:
            return "nan_due_to_window_defect_or_halt"
        prev_c = raw_inputs["adj_close"][t_idx - 1, sid_idx]
        if not np.isfinite(prev_c) or prev_c <= 0.0:
            return "nan_due_to_window_defect_or_halt"

    return "nan_unclassified"


def classify_feature_nans(
    feature_name: str,
    feature_matrix: pd.DataFrame,
    input_matrices: Dict[str, pd.DataFrame],
    bar_quality_mask: pd.DataFrame,
    membership_mask: pd.DataFrame,
    field_quality_masks: Optional[Dict[str, pd.DataFrame]] = None,
) -> Dict[str, Union[int, float, bool]]:
    """
    Classifies all NaNs of a given feature matrix within active index membership.
    Automatically aligns warmup lookback periods between full input matrices and feature slice.
    """
    n_feat_rows, n_sids = feature_matrix.shape
    total_cells = feature_matrix.size

    # Align membership mask to feature matrix rows
    if membership_mask.shape[0] != n_feat_rows:
        mem_aligned = membership_mask.reindex(index=feature_matrix.index, columns=feature_matrix.columns).fillna(False)
    else:
        mem_aligned = membership_mask

    mem_arr = mem_aligned.values.astype(bool)
    feat_arr = feature_matrix.values
    bar_q_arr = bar_quality_mask.values.astype(bool)

    member_cells = int(np.sum(mem_arr))
    non_member_cells = total_cells - member_cells
    valid_cells = int(np.sum(mem_arr & np.isfinite(feat_arr)))
    coverage_pct = round((valid_cells / member_cells) * 100.0, 2) if member_cells > 0 else 0.0

    nan_total = total_cells - valid_cells
    nan_outside_mem = non_member_cells
    nan_inside_mem = member_cells - valid_cells

    # Warmup offset calculation
    warmup_offset = bar_quality_mask.shape[0] - n_feat_rows
    if warmup_offset < 0:
        warmup_offset = 0

    # Prepare raw input arrays
    raw_inputs = {k: v.values for k, v in input_matrices.items()}
    field_q_arrs = {k: v.values.astype(bool) for k, v in field_quality_masks.items()} if field_quality_masks else None

    # First valid bar index per SID across full warmup grid
    p_ref = raw_inputs.get("adj_close", next(iter(raw_inputs.values())))
    has_bar_2d = np.isfinite(p_ref) & (p_ref > 0.0) & bar_q_arr
    first_valid_per_sid = np.full(n_sids, -1, dtype=int)
    for c in range(n_sids):
        valid_rows = np.where(has_bar_2d[:, c])[0]
        if len(valid_rows) > 0:
            first_valid_per_sid[c] = valid_rows[0]

    # Find all NaN cells inside membership
    nan_member_mask = mem_arr & (~np.isfinite(feat_arr))
    nan_coords = np.argwhere(nan_member_mask)

    cat_counts = {
        "nan_due_to_quality_at_t": 0,
        "nan_due_to_lack_of_history": 0,
        "nan_due_to_window_defect_or_halt": 0,
        "nan_due_to_zero_denom_or_invalid": 0,
        "nan_due_to_rsi_state_reset": 0,
        "nan_unclassified": 0,
    }

    for r, c in nan_coords:
        t_abs = r + warmup_offset
        f_idx = first_valid_per_sid[c]
        if f_idx < 0:
            cat_counts["nan_due_to_lack_of_history"] += 1
            continue

        cat = classify_cell_nan(
            feature_name=feature_name,
            t_idx=t_abs,
            sid_idx=c,
            raw_inputs=raw_inputs,
            bar_quality_mask=bar_q_arr,
            first_valid_idx=f_idx,
            field_quality_masks=field_q_arrs,
        )
        cat_counts[cat] += 1

    decomp_sum = sum(cat_counts.values())
    matches = (decomp_sum == nan_inside_mem)

    return {
        "feature": feature_name,
        "total_cells": total_cells,
        "non_member_cells": non_member_cells,
        "member_cells": member_cells,
        "valid_cells": valid_cells,
        "coverage_pct": coverage_pct,
        "nan_total": nan_total,
        "nan_outside_membership": nan_outside_mem,
        "nan_inside_membership": nan_inside_mem,
        "nan_due_to_quality_at_t": cat_counts["nan_due_to_quality_at_t"],
        "nan_due_to_lack_of_history": cat_counts["nan_due_to_lack_of_history"],
        "nan_due_to_window_defect_or_halt": cat_counts["nan_due_to_window_defect_or_halt"],
        "nan_due_to_zero_denom_or_invalid": cat_counts["nan_due_to_zero_denom_or_invalid"],
        "nan_due_to_rsi_state_reset": cat_counts["nan_due_to_rsi_state_reset"],
        "nan_unclassified": cat_counts["nan_unclassified"],
        "decomposition_matches_total": matches,
    }
