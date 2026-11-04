"""
src.data.universe
=================
Point-In-Time Universe querying, Security Identifier (SID) resolution,
and ticker-to-canonical-SID mapping utilities.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from src.data.matrix_loader import load_matrix
from src.quality.quality_window import OOSFreezeViolationError
from src.utils.config import Config, get_project_root, load_config


def load_canonical_security_mapping(config: Optional[Config] = None) -> pd.DataFrame:
    """
    Loads the official canonical security mapping table:
    docs/Data report/market_data_audit/tables/canonical_security_mapping.csv
    """
    cfg = config or load_config()
    table_path = cfg.project_root / "docs" / "Data report" / "market_data_audit" / "tables" / "canonical_security_mapping.csv"
    if not table_path.exists():
        raise FileNotFoundError(f"Canonical security mapping table not found: {table_path}")
    return pd.read_csv(table_path)


def load_temporal_mapping(config: Optional[Config] = None) -> pd.DataFrame:
    """
    Loads the official temporal constituent mapping table:
    docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv
    """
    cfg = config or load_config()
    table_path = cfg.project_root / "docs" / "Data report" / "market_data_audit" / "tables" / "universe_constituent_temporal_mapping.csv"
    if not table_path.exists():
        raise FileNotFoundError(f"Temporal mapping table not found: {table_path}")
    return pd.read_csv(table_path, encoding="utf-8")


def load_pit_by_year_json(config: Optional[Config] = None) -> Dict[str, List[str]]:
    """
    Loads raw universe constituents by year (2000 to 2026) from JSON.
    """
    cfg = config or load_config()
    json_path = cfg.get_pit_by_year_json_path()
    if not json_path.exists():
        raise FileNotFoundError(f"Universe PIT JSON not found: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ticker_to_canonical_sids(
    ticker: str,
    as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Config] = None,
) -> List[str]:
    """
    Maps a ticker symbol to canonical SID(s).
    
    If as_of_date is provided:
        Resolves Point-In-Time identity based strictly on the active date range [min_date, max_date].
        If no mapping is active on as_of_date, returns an empty list [] (unresolved/inactive).
        Does NOT silently fall back to historical SIDs.
    If as_of_date is None:
        Returns all canonical SIDs ever associated with this ticker across history.
    """
    df = load_canonical_security_mapping(config=config)
    matches = df[df["original_ticker"].str.upper() == ticker.upper()]

    if matches.empty:
        return []

    if as_of_date is not None:
        dt = pd.Timestamp(as_of_date).strftime("%Y-%m-%d")
        dt_matches = matches[(matches["min_date"] <= dt) & (matches["max_date"] >= dt)]
        if not dt_matches.empty:
            return dt_matches["canonical_sid"].unique().tolist()
        return []  # Strict PIT semantics: no active SID on as_of_date -> return empty

    return matches["canonical_sid"].unique().tolist()


def canonical_sid_to_ticker(
    canonical_sid: str,
    as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Config] = None,
) -> Optional[str]:
    """
    Returns the primary ticker symbol associated with a canonical SID.
    
    If as_of_date is provided:
        Returns the ticker valid as of that specific trading date.
        If the SID was inactive on as_of_date, returns None.
    If as_of_date is None:
        Returns the primary representative ticker from the canonical mapping table.
    """
    df = load_canonical_security_mapping(config=config)
    matches = df[df["canonical_sid"] == canonical_sid]

    if matches.empty:
        # Fallback to string extraction only if as_of_date is None
        if as_of_date is None:
            parts = canonical_sid.split()
            return parts[0] if parts else None
        return None

    if as_of_date is not None:
        dt = pd.Timestamp(as_of_date).strftime("%Y-%m-%d")
        dt_matches = matches[(matches["min_date"] <= dt) & (matches["max_date"] >= dt)]
        if not dt_matches.empty:
            return str(dt_matches["original_ticker"].iloc[0])
        
        # Check temporal mapping as secondary PIT source
        try:
            t_df = load_temporal_mapping(config=config)
            t_matches = t_df[
                (t_df["assigned_canonical_sid"] == canonical_sid)
                & (t_df["period_start"] <= dt)
                & (t_df["period_end"] >= dt)
            ]
            if not t_matches.empty:
                return str(t_matches["source_ticker"].iloc[0])
        except Exception:
            pass
        return None

    return str(matches["original_ticker"].iloc[0])


def get_reconstitution_year(date: Union[str, pd.Timestamp]) -> int:
    """
    Calculates the reconstitution cycle year for a given date according to
    the institutional convention [01/07/Y to 30/06/Y+1].

    Examples:
      - 2005-08-15 -> 2005
      - 2006-03-20 -> 2005
      - 2006-07-01 -> 2006
    """
    ts = pd.Timestamp(date)
    if ts.month >= 7:
        return ts.year
    else:
        return ts.year - 1


def get_active_constituents(
    date: Union[str, pd.Timestamp],
    strict: bool = True,
    allow_oos: bool = False,
    config: Optional[Config] = None,
) -> List[str]:
    """
    Queries canonical SIDs active in the Russell 1000 on a specific trading date
    from the 2D membership mask matrix.

    Handles OOS boundary cleanly:
    - If date is in the development period (date < oos_start_date), loads only the
      development/warmup slice, eliminating false-positive OOS freeze violations.
    - If date is in the OOS period (date >= oos_start_date) and allow_oos is False,
      raises OOSFreezeViolationError.
    """
    cfg = config or load_config()
    ts = pd.Timestamp(date)
    oos_threshold = pd.Timestamp(cfg.oos_start_date)

    if ts >= oos_threshold:
        if cfg.oos_strictly_frozen and not allow_oos:
            raise OOSFreezeViolationError(
                f"OOS FREEZE VIOLATION: Query for active constituents on {ts.strftime('%Y-%m-%d')} "
                f"falls in the strictly frozen Out-of-Sample window (starting {cfg.oos_start_date}). "
                f"Set allow_oos=True only during authorized post-development evaluations."
            )
        # Explicitly allowed OOS access
        matrix_name = "strict_membership_mask" if strict else "membership_mask"
        mask_df = load_matrix(matrix_name, dev_only=False, allow_oos=True, config=cfg)
    else:
        # Development query: load dev + warmup window safely without triggering OOS check
        matrix_name = "strict_membership_mask" if strict else "membership_mask"
        mask_df = load_matrix(matrix_name, dev_only=True, include_warmup=True, allow_oos=False, config=cfg)

    if ts not in mask_df.index:
        # Find nearest previous trading day
        valid_dates = mask_df.index[mask_df.index <= ts]
        if len(valid_dates) == 0:
            raise KeyError(f"Date {ts.strftime('%Y-%m-%d')} precedes all available trading dates.")
        ts = valid_dates[-1]

    row = mask_df.loc[ts]
    return row.index[row.astype(bool)].tolist()
