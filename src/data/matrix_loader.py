"""
src.data.matrix_loader
======================
High-performance loader for 2D matrices (7,252 trading dates x 3,711 canonical SIDs).
Provides full alignment checks, development window filtering, and strict OOS protection.
Supports independent bar_quality_mask construction for feature warmups.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.quality.quality_window import check_oos_access, filter_dev_window
from src.utils.config import Config, load_config


def get_matrices_dir(config: Optional[Config] = None) -> Path:
    """Returns the absolute Path to data/processed/matrices/."""
    cfg = config or load_config()
    return cfg.get_matrices_dir()


def get_matrix_path(matrix_name: str, matrices_dir: Optional[Path] = None) -> Path:
    """
    Resolves the absolute path for a matrix parquet file.
    Appends '.parquet' if not already present.
    """
    m_dir = matrices_dir or get_matrices_dir()
    fname = matrix_name if matrix_name.endswith(".parquet") else f"{matrix_name}.parquet"
    target = m_dir / fname
    if not target.exists():
        raise FileNotFoundError(f"Matrix file not found: {target}")
    return target


def load_dates_index(matrices_dir: Optional[Path] = None) -> pd.DatetimeIndex:
    """
    Loads the 7,252 trading session dates as a DatetimeIndex.
    """
    path = get_matrix_path("matrix_dates_index.parquet", matrices_dir)
    df = pd.read_parquet(path)
    col = "date" if "date" in df.columns else df.columns[0]
    return pd.DatetimeIndex(pd.to_datetime(df[col]))


def load_columns_sids(matrices_dir: Optional[Path] = None) -> pd.Index:
    """
    Loads the 3,711 canonical security identifiers (SIDs) as a pandas Index.
    """
    path = get_matrix_path("matrix_columns_sids.parquet", matrices_dir)
    df = pd.read_parquet(path)
    col = "canonical_sid" if "canonical_sid" in df.columns else df.columns[0]
    return pd.Index(df[col].astype(str), name="canonical_sid")


def load_matrix(
    matrix_name: str,
    dev_only: bool = False,
    include_warmup: bool = False,
    as_numpy: bool = False,
    allow_oos: bool = False,
    matrices_dir: Optional[Path] = None,
    config: Optional[Config] = None,
) -> Union[pd.DataFrame, np.ndarray]:
    """
    Loads a 2D matrix from parquet storage.

    Parameters:
        matrix_name: Base name of matrix (e.g. 'adj_close', 'total_return', 'strict_membership_mask').
        dev_only: If True, restricts rows strictly to development window (default: False).
        include_warmup: When dev_only=True, if True includes warmup (1998-01-02 to 2023-12-29).
                        If False, strictly development (2000-07-01 to 2023-12-29, 5,911 sessions).
        as_numpy: If True, returns underlying numpy array (values).
        allow_oos: If True, bypasses OOS freeze verification when dev_only=False.
        matrices_dir: Optional custom path to matrices directory.
        config: Optional Config instance.

    Returns:
        pd.DataFrame (index=DatetimeIndex, columns=canonical SIDs) or np.ndarray.
    """
    cfg = config or load_config()
    target_path = get_matrix_path(matrix_name, matrices_dir or cfg.get_matrices_dir())

    df = pd.read_parquet(target_path)

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Ensure column index is clean string index
    if not isinstance(df.columns, pd.Index):
        df.columns = pd.Index(df.columns.astype(str), name="canonical_sid")
    elif df.columns.name != "canonical_sid":
        df.columns.name = "canonical_sid"

    if dev_only:
        df = filter_dev_window(df, include_warmup=include_warmup, config=cfg)
    else:
        # Check OOS access if oos_strictly_frozen is enabled
        if cfg.oos_strictly_frozen and not allow_oos:
            check_oos_access(df.index, oos_start=cfg.oos_start_date, allow_oos=allow_oos)

    if as_numpy:
        return df.values

    return df


def load_matrices(
    matrix_names: Iterable[str],
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    matrices_dir: Optional[Path] = None,
    config: Optional[Config] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Loads multiple 2D matrices into a dictionary keyed by matrix name.
    Validates that all loaded matrices have identical dimensions and indices.
    """
    cfg = config or load_config()
    results: Dict[str, pd.DataFrame] = {}

    first_idx: Optional[pd.DatetimeIndex] = None
    first_cols: Optional[pd.Index] = None

    for name in matrix_names:
        clean_name = name.replace(".parquet", "")
        df = load_matrix(
            clean_name,
            dev_only=dev_only,
            include_warmup=include_warmup,
            as_numpy=False,
            allow_oos=allow_oos,
            matrices_dir=matrices_dir,
            config=cfg,
        )
        if first_idx is None:
            first_idx = df.index
            first_cols = df.columns
        else:
            if not df.index.equals(first_idx):
                raise ValueError(f"Matrix {name} has index mismatch with previous matrices.")
            if not df.columns.equals(first_cols):
                raise ValueError(f"Matrix {name} has column mismatch with previous matrices.")

        results[clean_name] = df

    return results


def load_bar_quality_mask(
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    matrices_dir: Optional[Path] = None,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Constructs the independent Bar Quality Mask:
    True if the security has a valid trading price bar (> 0) on the exchange AND is free
    from both bad tick periods and spinoff discontinuities.

    CRITICAL INVARIANT:
    This mask is 100% INDEPENDENT of Russell 1000 index membership.
    It preserves legitimate historical pre-membership trading bars so that multi-day
    rolling features (e.g. 20d momentum, 252d volatility) have sufficient warmup history
    and can evaluate immediately upon index entry.
    """
    cfg = config or load_config()
    adj_close = load_matrix("adj_close", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)
    is_bad = load_matrix("is_bad_data_period", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)
    is_spinoff = load_matrix("is_spinoff_discontinuity", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)

    # Valid bar: has positive price and is not flagged as bad tick or spinoff discontinuity
    has_bar = adj_close.notna() & (adj_close > 0.0)
    clean_bar = has_bar & (~is_bad.fillna(False).astype(bool)) & (~is_spinoff.fillna(False).astype(bool))
    return clean_bar


def load_masked_matrix(
    matrix_name: str,
    mask: Optional[Union[str, pd.DataFrame]] = None,
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    matrices_dir: Optional[Path] = None,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Loads a matrix and applies a mask. Non-members (where mask is False, 0, or NaN)
    are replaced with np.nan, strictly preserving missingness for out-of-universe assets.
    """
    cfg = config or load_config()
    df = load_matrix(
        matrix_name,
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
        matrices_dir=matrices_dir,
        config=cfg,
    )

    if mask is None:
        return df

    if isinstance(mask, str):
        mask_df = load_matrix(
            mask,
            dev_only=dev_only,
            include_warmup=include_warmup,
            allow_oos=allow_oos,
            matrices_dir=matrices_dir,
            config=cfg,
        )
    else:
        mask_df = mask

    # Align mask to matrix
    mask_aligned = mask_df.reindex(index=df.index, columns=df.columns).fillna(False).astype(bool)
    return df.where(mask_aligned, other=np.nan)


def load_layer1_mask(strict: bool = True, dev_only: bool = False, include_warmup: bool = False, allow_oos: bool = False, config: Optional[Config] = None) -> pd.DataFrame:
    """Loads Layer 1 PIT Membership Mask (Russell 1000 calendar reconstitution)."""
    name = "strict_membership_mask" if strict else "membership_mask"
    return load_matrix(name, dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, config=config)


def load_layer2_mask(dev_only: bool = False, include_warmup: bool = False, allow_oos: bool = False, config: Optional[Config] = None) -> pd.DataFrame:
    """Loads Layer 2 Valid Data Mask (Membership + clean trading bar)."""
    return load_matrix("valid_data_mask", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, config=config)


def load_layer3_mask(dev_only: bool = False, include_warmup: bool = False, allow_oos: bool = False, config: Optional[Config] = None) -> pd.DataFrame:
    """Loads Layer 3 Valid Label Mask (Layer 2 at T + valid return at T+1)."""
    return load_matrix("valid_label_mask", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, config=config)
