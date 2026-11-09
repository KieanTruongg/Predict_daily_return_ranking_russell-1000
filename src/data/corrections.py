"""
src.data.corrections
====================
Unified Market Data Corrections and Quarantine Subsystem.

Provides:
1. Structured parsing of market_data_corrections_and_exceptions.csv.
2. Clear distinction between:
   - Full-bar quarantine (quarantine_bar): sets is_bad_data_period=True,
     invalidates daily_return and total_return, and optionally invalidates
     the recovery session return.
   - Field-level quarantine (quarantine_fields): isolates ONLY the specified
     fields (e.g. open, low, adj_open, adj_low) to NaN, leaving close,
     adj_close, volume, daily_return, and total_return completely intact.
3. Pure functions for upstream pipeline integration (06_process_corporate_actions,
   07_build_2d_matrices) and matrix loaders (matrix_loader.py).
4. Idempotent application and zero side-effects.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

DEFAULT_CORRECTIONS_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "Data report"
    / "market_data_audit"
    / "tables"
    / "market_data_corrections_and_exceptions.csv"
)

# Standard price and adjusted field mappings
FIELD_ADJ_PAIRS = {
    "open": "adj_open",
    "adj_open": "open",
    "high": "adj_high",
    "adj_high": "high",
    "low": "adj_low",
    "adj_low": "low",
    "close": "adj_close",
    "adj_close": "close",
    "volume": "adj_volume",
    "adj_volume": "volume",
}


@dataclass
class CorrectionEntry:
    event_id: str
    source_ticker: str
    canonical_sid: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    correction_layer: str
    parameter_name: str
    parameter_value: str
    evidence_source: str
    forensic_explanation: str
    action_taken: str

    @property
    def is_split(self) -> bool:
        return self.correction_layer == "CORPORATE_ACTIONS_SPLIT"

    @property
    def is_spinoff(self) -> bool:
        return self.correction_layer == "SPECIAL_CORPORATE_SPINOFF"

    @property
    def is_bar_quarantine(self) -> bool:
        """True if the entire trading bar is invalid."""
        if self.is_split or self.is_spinoff:
            return False
        param_name = str(self.parameter_name).strip().lower()
        param_val = str(self.parameter_value).strip().lower()
        if param_name in ["quarantine_bar", "quarantine_bad_data_period", "quarantine_bad_tick"]:
            if param_val in ["all", "true"]:
                return True
        return False

    @property
    def is_field_quarantine(self) -> bool:
        """True if only specific fields within the bar are invalid."""
        if self.is_split or self.is_spinoff:
            return False
        param_name = str(self.parameter_name).strip().lower()
        return param_name == "quarantine_fields"

    @property
    def target_fields(self) -> List[str]:
        """List of canonical lower-case field names targeted for quarantine."""
        if self.is_bar_quarantine:
            return ["open", "high", "low", "close", "volume", "adj_open", "adj_high", "adj_low", "adj_close", "adj_volume"]
        if self.is_field_quarantine:
            raw_fields = [f.strip().lower() for f in str(self.parameter_value).split(",") if f.strip()]
            # Automatically expand to include both raw and adjusted pairs
            expanded = set(raw_fields)
            for f in raw_fields:
                if f in FIELD_ADJ_PAIRS:
                    expanded.add(FIELD_ADJ_PAIRS[f])
            return sorted(list(expanded))
        return []

    @property
    def quarantine_recovery_return(self) -> bool:
        """
        Universal return contract: Any full-bar quarantine invalidates its Close price.
        Since daily return at t+1 = (P_{t+1} - P_t) / P_t uses P_t as denominator,
        any return at t+1 following an invalid/quarantined bar must be NaN.
        Does NOT rely on heuristic keyword matching like 'rebound' or 'hồi phục'.
        """
        return self.is_bar_quarantine


def load_market_corrections(csv_path: Optional[Union[str, Path]] = None) -> List[CorrectionEntry]:
    """
    Loads and parses market_data_corrections_and_exceptions.csv into structured CorrectionEntry objects.
    """
    path = Path(csv_path) if csv_path is not None else DEFAULT_CORRECTIONS_CSV
    if not path.exists():
        return []

    df = pd.read_csv(path, dtype=str)
    entries: List[CorrectionEntry] = []
    for _, row in df.iterrows():
        entries.append(
            CorrectionEntry(
                event_id=str(row.get("event_id", "")).strip(),
                source_ticker=str(row.get("source_ticker", "")).strip(),
                canonical_sid=str(row.get("canonical_sid", "")).strip(),
                start_date=pd.to_datetime(str(row.get("start_date", "")).strip()),
                end_date=pd.to_datetime(str(row.get("end_date", "")).strip()),
                correction_layer=str(row.get("correction_layer", "")).strip(),
                parameter_name=str(row.get("parameter_name", "")).strip(),
                parameter_value=str(row.get("parameter_value", "")).strip(),
                evidence_source=str(row.get("evidence_source", "")).strip(),
                forensic_explanation=str(row.get("forensic_explanation", "")).strip(),
                action_taken=str(row.get("action_taken", "")).strip(),
            )
        )
    return entries


def apply_corrections_to_dataframe(
    df_prices: pd.DataFrame,
    corrections: Optional[List[CorrectionEntry]] = None,
    corrections_csv: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Applies the full set of corrections to a long OHLCV DataFrame (date, canonical_sid, ...)
    with strict separation between:
    1. Special Corporate Actions (Spin-offs)
    2. Full-bar Quarantine (is_bad_data_period=True, return=NaN, optional recovery return=NaN)
    3. Field-level Quarantine (only target fields and adjusted counterparts=NaN, close/returns preserved)

    Idempotent and safe to run multiple times.
    """
    df = df_prices.copy()
    corrs = corrections if corrections is not None else load_market_corrections(corrections_csv)
    if not corrs or df.empty:
        return df

    if "is_bad_data_period" not in df.columns:
        df["is_bad_data_period"] = False
    if "is_spinoff_discontinuity" not in df.columns:
        df["is_spinoff_discontinuity"] = False
    if "quality_flag" not in df.columns:
        df["quality_flag"] = "CLEAN"

    # Pre-build index lookup for fast row identification
    sid_grouped_indices = df.groupby("canonical_sid").indices
    dates_arr = pd.to_datetime(df["date"]).values

    for entry in corrs:
        c_sid = entry.canonical_sid
        if c_sid not in sid_grouped_indices:
            continue

        sid_idx_arr = sid_grouped_indices[c_sid]
        sid_dates = dates_arr[sid_idx_arr]
        in_win = (sid_dates >= np.datetime64(entry.start_date)) & (sid_dates <= np.datetime64(entry.end_date))
        win_indices = sid_idx_arr[in_win]
        if len(win_indices) == 0:
            continue

        # Case 1: Spinoff Discontinuity
        if entry.is_spinoff:
            df.loc[win_indices, "is_spinoff_discontinuity"] = True
            df.loc[win_indices, "quality_flag"] = "SPINOFF_DISCONTINUITY"
            if "daily_return" in df.columns:
                df.loc[win_indices, "daily_return"] = np.nan
            if "total_return" in df.columns:
                df.loc[win_indices, "total_return"] = np.nan
            if "is_consecutive_session" in df.columns:
                df.loc[win_indices, "is_consecutive_session"] = False

        # Case 2: Full-bar Quarantine (e.g. MKL, SABR, HOMS pre-IPO, TR)
        elif entry.is_bar_quarantine:
            df.loc[win_indices, "is_bad_data_period"] = True
            df.loc[win_indices, "quality_flag"] = entry.correction_layer
            if "daily_return" in df.columns:
                df.loc[win_indices, "daily_return"] = np.nan
            if "total_return" in df.columns:
                df.loc[win_indices, "total_return"] = np.nan
            if "is_consecutive_session" in df.columns:
                df.loc[win_indices, "is_consecutive_session"] = False

            if entry.quarantine_recovery_return:
                max_win_idx = win_indices[-1]
                loc_in_sid = np.where(sid_idx_arr == max_win_idx)[0][0]
                if loc_in_sid + 1 < len(sid_idx_arr):
                    recov_idx = sid_idx_arr[loc_in_sid + 1]
                    if "daily_return" in df.columns:
                        df.loc[recov_idx, "daily_return"] = np.nan
                    if "total_return" in df.columns:
                        df.loc[recov_idx, "total_return"] = np.nan
                    if "is_consecutive_session" in df.columns:
                        df.loc[recov_idx, "is_consecutive_session"] = False

        # Case 3: Field-level Quarantine (e.g. GMT open/low, RGC open/low, CEPH open/high/low, FRT high/low)
        elif entry.is_field_quarantine:
            target_cols = [c for c in entry.target_fields if c in df.columns]
            for col in target_cols:
                df.loc[win_indices, col] = np.nan
            # Note: is_bad_data_period remains False; close and returns remain valid!

    return df


def get_field_quarantine_mask(
    field_name: str,
    index: pd.DatetimeIndex,
    columns: pd.Index,
    corrections: Optional[List[CorrectionEntry]] = None,
    corrections_csv: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Constructs a 2D boolean DataFrame (dates x sids) indicating clean cells for a specific field.
    Returns True where the field is valid/clean, and False where the field has been quarantined.
    """
    mask_df = pd.DataFrame(True, index=index, columns=columns, dtype=bool)
    corrs = corrections if corrections is not None else load_market_corrections(corrections_csv)
    if not corrs:
        return mask_df

    norm_field = field_name.strip().lower()

    for entry in corrs:
        if not entry.is_field_quarantine:
            continue
        # Check if this field or its pair is targeted
        if norm_field in entry.target_fields:
            c_sid = entry.canonical_sid
            if c_sid in columns:
                date_mask = (index >= entry.start_date) & (index <= entry.end_date)
                mask_df.loc[date_mask, c_sid] = False

    return mask_df
