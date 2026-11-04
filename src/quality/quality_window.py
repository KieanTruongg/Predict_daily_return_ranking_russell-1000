"""
src.quality.quality_window
==========================
Strict institutional window enforcement and forward-looking leakage prevention.

Rules:
1. Warmup window (1998-01-02 to 2000-06-30): 630 NYSE trading sessions.
   Used exclusively for feature warmup (e.g. 252-day momentum, trailing volatility).
2. Development window (2000-07-01 to 2023-12-29): 5,911 NYSE trading sessions.
   Used for feature research, model training, cross-validation, and hyperparameter tuning.
3. Out-of-Sample (OOS) window (2024-01-02 to 2026-10-30): 711 NYSE trading sessions.
   STRICTLY FROZEN during research and development. Any access without explicit authorization
   raises OOSFreezeViolationError to prevent look-ahead bias and data snooping.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Union
import numpy as np
import pandas as pd

from src.utils.config import Config, load_config


class OOSFreezeViolationError(PermissionError):
    """Raised when an operation attempts to access strictly frozen Out-of-Sample data."""
    pass


# Global freeze flag (can only be overridden via explicit context manager)
_OOS_ACCESS_ALLOWED: bool = False


class allow_oos_context:
    """
    Context manager to explicitly permit OOS data access during authorized
    evaluation / final audit phases only.
    """
    def __enter__(self):
        global _OOS_ACCESS_ALLOWED
        self._prev = _OOS_ACCESS_ALLOWED
        _OOS_ACCESS_ALLOWED = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _OOS_ACCESS_ALLOWED
        _OOS_ACCESS_ALLOWED = self._prev


def check_oos_access(
    dates: Union[pd.DatetimeIndex, pd.Series, Iterable[Any]],
    oos_start: str = "2024-01-02",
    allow_oos: bool = False,
) -> None:
    """
    Verifies that none of the provided dates fall in the strictly frozen OOS window.

    Raises:
        OOSFreezeViolationError: If any date >= oos_start and access is not authorized.
    """
    if allow_oos or _OOS_ACCESS_ALLOWED:
        return

    if not isinstance(dates, pd.DatetimeIndex):
        dt_index = pd.to_datetime(dates)
    else:
        dt_index = dates

    oos_threshold = pd.Timestamp(oos_start)
    oos_violations = dt_index[dt_index >= oos_threshold]

    if len(oos_violations) > 0:
        first_bad = oos_violations[0].strftime("%Y-%m-%d")
        count_bad = len(oos_violations)
        raise OOSFreezeViolationError(
            f"OOS FREEZE VIOLATION: Attempted access to {count_bad} date(s) in the strictly "
            f"frozen Out-of-Sample window (starting at {first_bad} >= {oos_start}). "
            f"Access to OOS data is strictly prohibited during research and feature engineering "
            f"to guarantee zero forward-looking leakage and prevent snooping bias."
        )


def filter_dev_window(
    df_or_series: Union[pd.DataFrame, pd.Series],
    include_warmup: bool = False,
    config: Optional[Config] = None,
) -> Union[pd.DataFrame, pd.Series]:
    """
    Filters a DataFrame or Series (with DatetimeIndex) strictly to the development window.

    Parameters:
        df_or_series: Object with DatetimeIndex to filter.
        include_warmup: If True, includes warmup period (1998-01-02 to 2023-12-29).
                        If False, strictly development period (2000-07-01 to 2023-12-29).
        config: Optional Config instance.

    Returns:
        Filtered DataFrame or Series containing only dates within the development window.
    """
    cfg = config or load_config()

    if not isinstance(df_or_series.index, pd.DatetimeIndex):
        raise TypeError("Object must have a pd.DatetimeIndex for development window filtering.")

    start_date = pd.Timestamp(cfg.start_date) if include_warmup else pd.Timestamp(cfg.dev_start_date)
    end_date = pd.Timestamp(cfg.dev_end_date)

    idx = df_or_series.index
    mask = (idx >= start_date) & (idx <= end_date)
    return df_or_series.loc[mask]


def validate_trading_calendar_partition(
    dates_index: Union[pd.DatetimeIndex, pd.Series, Iterable[Any]],
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Validates the exact partitioning of the 7,252 NYSE trading sessions:
    - Warmup: 630 sessions (1998-01-02 to 2000-06-30)
    - Development: 5,911 sessions (2000-07-01 to 2023-12-29)
    - Out-of-Sample: 711 sessions (2024-01-02 to 2026-10-30)

    Returns:
        Summary dict containing counts and verification boolean flags.
    """
    if config is None:
        cfg = load_config()
    else:
        cfg = config

    if not isinstance(dates_index, pd.DatetimeIndex):
        dts = pd.to_datetime(pd.Series(dates_index))
    else:
        dts = dates_index.to_series()

    warmup_mask = (dts >= pd.Timestamp(cfg.start_date)) & (dts <= pd.Timestamp(cfg.warmup_end_date))
    dev_mask = (dts >= pd.Timestamp(cfg.dev_start_date)) & (dts <= pd.Timestamp(cfg.dev_end_date))
    oos_mask = (dts >= pd.Timestamp(cfg.oos_start_date)) & (dts <= pd.Timestamp(cfg.oos_end_date))

    warmup_count = int(warmup_mask.sum())
    dev_count = int(dev_mask.sum())
    oos_count = int(oos_mask.sum())
    total_count = len(dts)

    is_valid = (
        warmup_count == 630
        and dev_count == 5911
        and oos_count == 711
        and total_count == 7252
    )

    return {
        "total_sessions": total_count,
        "warmup_sessions": warmup_count,
        "expected_warmup": 630,
        "dev_sessions": dev_count,
        "expected_dev": 5911,
        "oos_sessions": oos_count,
        "expected_oos": 711,
        "is_valid": is_valid,
        "warmup_start": cfg.start_date,
        "warmup_end": cfg.warmup_end_date,
        "dev_start": cfg.dev_start_date,
        "dev_end": cfg.dev_end_date,
        "oos_start": cfg.oos_start_date,
        "oos_end": cfg.oos_end_date,
    }


def assert_coordinate_alignment(
    matrix_a: pd.DataFrame,
    matrix_b: pd.DataFrame,
) -> bool:
    """
    Checks that two 2D matrices have identical row (date) and column (canonical SID) coordinates.
    Note: This is a coordinate alignment check, not a full causal leakage audit.
    """
    if not matrix_a.index.equals(matrix_b.index):
        raise ValueError("Matrices have misaligned date indices.")
    if not matrix_a.columns.equals(matrix_b.columns):
        raise ValueError("Matrices have misaligned canonical SID columns.")
    return True


def verify_boundary_purge(
    target_matrix_or_mask: pd.DataFrame,
    boundary_date: str = "2023-12-29",
) -> bool:
    """
    Verifies that target labels or valid_label_mask at the development boundary
    (default: 2023-12-29) are 100% purged (all NaNs or all False).
    This guarantees that the target for the final development session does not
    contain information from the first trading session of 2024 (OOS).
    """
    ts = pd.Timestamp(boundary_date)
    if ts not in target_matrix_or_mask.index:
        return True  # If boundary date not in matrix, no boundary leakage risk

    row = target_matrix_or_mask.loc[ts]
    # Check if boolean mask or float matrix
    if row.dtype == bool:
        valid_count = int(row.sum())
    else:
        valid_count = int(row.notna().sum())

    if valid_count > 0:
        raise ValueError(
            f"BOUNDARY PURGE VIOLATION: Target on boundary date {boundary_date} contains "
            f"{valid_count} valid labels. It must be 100% purged (all NaN / all False) "
            f"to prevent forward-looking leakage into 2024 OOS."
        )
    return True


def assert_causal_alignment(
    feature_matrix: pd.DataFrame,
    target_matrix: pd.DataFrame,
    check_boundary: bool = True,
    boundary_date: str = "2023-12-29",
) -> bool:
    """
    Asserts causality between feature and target matrices:
    1. Coordinate alignment: both matrices must share identical index and columns.
    2. Boundary purge: target on boundary_date must contain zero valid entries to prevent
       spillover into Out-of-Sample data.
    """
    assert_coordinate_alignment(feature_matrix, target_matrix)
    if check_boundary:
        verify_boundary_purge(target_matrix, boundary_date=boundary_date)
    return True
