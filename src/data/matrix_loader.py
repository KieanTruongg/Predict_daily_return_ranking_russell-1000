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

from src.quality.quality_window import check_oos_access, filter_dev_window, OOSFreezeViolationError
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
    dates: Optional[Iterable[Union[pd.Timestamp, str]]] = None,
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

    if dates is not None:
        # Normalize and validate requested dates before reading from disk
        dates_list = [pd.Timestamp(d) for d in dates]
        if not dates_list:
            raise ValueError("dates parameter was provided but is empty.")

        dev_start = pd.Timestamp(cfg.dev_start_date)
        dev_end = pd.Timestamp(cfg.dev_end_date)
        warmup_start = pd.Timestamp(cfg.start_date)
        effective_start = warmup_start if include_warmup else dev_start

        for d in dates_list:
            if d > dev_end:
                if cfg.oos_strictly_frozen and not allow_oos:
                    raise OOSFreezeViolationError(
                        f"OOS Freeze Violation: Requested date '{d.strftime('%Y-%m-%d')}' "
                        f"is in Out-of-Sample window (> {dev_end.strftime('%Y-%m-%d')}). "
                        f"Access strictly blocked."
                    )
                raise ValueError(
                    f"Requested date '{d.strftime('%Y-%m-%d')}' exceeds dev_end_date "
                    f"'{dev_end.strftime('%Y-%m-%d')}'."
                )
            if d < effective_start:
                raise ValueError(
                    f"Requested date '{d.strftime('%Y-%m-%d')}' precedes valid start date "
                    f"'{effective_start.strftime('%Y-%m-%d')}' (include_warmup={include_warmup})."
                )

        import pyarrow.parquet as pq
        parquet_file = pq.ParquetFile(target_path)
        arrow_schema = parquet_file.schema_arrow
        index_col = None
        if arrow_schema.pandas_metadata:
            idx_cols = arrow_schema.pandas_metadata.get("index_columns", [])
            if idx_cols and isinstance(idx_cols[0], str) and idx_cols[0] in arrow_schema.names:
                index_col = idx_cols[0]
            elif idx_cols and isinstance(idx_cols[0], dict) and "field_name" in idx_cols[0] and idx_cols[0]["field_name"] in arrow_schema.names:
                index_col = idx_cols[0]["field_name"]

        if index_col is None:
            if "date" in arrow_schema.names:
                index_col = "date"
            elif "__index_level_0__" in arrow_schema.names:
                index_col = "__index_level_0__"

        if index_col is None:
            raise RuntimeError(
                f"Cannot determine date index column in Parquet file '{target_path.name}' "
                f"to apply pushdown filter for dates mode. Schema names: {arrow_schema.names}"
            )

        filters = [(index_col, "in", dates_list)]
        try:
            df = pd.read_parquet(target_path, filters=filters)
        except Exception as e:
            raise RuntimeError(
                f"Predicate pushdown failed for dates read on '{target_path.name}': {e}. "
                f"Unbounded fallback read is strictly blocked to prevent OOS leakage."
            ) from e

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        missing = [d for d in dates_list if d not in df.index]
        if missing:
            raise KeyError(
                f"Matrix '{target_path.name}' is missing requested dates: "
                f"{[m.strftime('%Y-%m-%d') for m in missing]}."
            )
        df = df.loc[dates_list]

    elif dev_only:
        # Predicate pushdown: filter by date index at parquet scan level
        # to ensure OOS rows (> dev_end_date) are never loaded into memory.
        import pyarrow.parquet as pq
        parquet_file = pq.ParquetFile(target_path)
        arrow_schema = parquet_file.schema_arrow
        index_col = None
        if arrow_schema.pandas_metadata:
            idx_cols = arrow_schema.pandas_metadata.get("index_columns", [])
            if idx_cols and isinstance(idx_cols[0], str) and idx_cols[0] in arrow_schema.names:
                index_col = idx_cols[0]
            elif idx_cols and isinstance(idx_cols[0], dict) and "field_name" in idx_cols[0] and idx_cols[0]["field_name"] in arrow_schema.names:
                index_col = idx_cols[0]["field_name"]

        if index_col is None:
            if "date" in arrow_schema.names:
                index_col = "date"
            elif "__index_level_0__" in arrow_schema.names:
                index_col = "__index_level_0__"

        if index_col is None:
            raise RuntimeError(
                f"Cannot determine date index column in Parquet file '{target_path.name}' "
                f"to apply pushdown filter for dev_only mode. Schema names: {arrow_schema.names}"
            )

        filters = []
        if not include_warmup:
            filters.append((index_col, ">=", pd.Timestamp(cfg.dev_start_date)))
        filters.append((index_col, "<=", pd.Timestamp(cfg.dev_end_date)))

        try:
            df = pd.read_parquet(target_path, filters=filters)
        except Exception as e:
            raise RuntimeError(
                f"Predicate pushdown failed for dev_only read on '{target_path.name}': {e}. "
                f"Unbounded fallback read is strictly blocked to prevent OOS leakage."
            ) from e
    else:
        if cfg.oos_strictly_frozen and not allow_oos:
            raise OOSFreezeViolationError(
                f"OOS Freeze Violation: Cannot read full matrix '{matrix_name}' "
                f"from disk while oos_strictly_frozen=True and allow_oos=False. "
                f"Use dev_only=True to read only Development/warmup data."
            )
        df = pd.read_parquet(target_path)

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Ensure column index is clean string index
    if not isinstance(df.columns, pd.Index):
        df.columns = pd.Index(df.columns.astype(str), name="canonical_sid")
    elif df.columns.name != "canonical_sid":
        df.columns.name = "canonical_sid"

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
    dates: Optional[Iterable[Union[pd.Timestamp, str]]] = None,
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
            dates=dates,
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
    field: Optional[str] = None,
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

    If `field` is specified (e.g. 'open', 'low', 'adj_open', 'adj_low'), applies field-level
    quarantine exceptions (e.g. CORR_014 for GMT on 2007-01-25) without invalidating unaffected fields.
    """
    cfg = config or load_config()
    adj_close = load_matrix("adj_close", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)
    is_bad = load_matrix("is_bad_data_period", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)
    is_spinoff = load_matrix("is_spinoff_discontinuity", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos, matrices_dir=matrices_dir, config=cfg)

    # Valid bar: has positive price and is not flagged as bad tick or spinoff discontinuity
    has_bar = adj_close.notna() & (adj_close > 0.0)
    clean_bar = has_bar & (~is_bad.fillna(False).astype(bool)) & (~is_spinoff.fillna(False).astype(bool))

    if field is not None:
        from src.data.corrections import get_field_quarantine_mask
        field_mask = get_field_quarantine_mask(field, clean_bar.index, clean_bar.columns)
        return clean_bar & field_mask

    return clean_bar


def load_field_quality_mask(
    field: str,
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    matrices_dir: Optional[Path] = None,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Convenience loader for field-specific quality masks.
    Enforces field-level quarantine rules while preserving backward compatibility.
    """
    return load_bar_quality_mask(
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
        matrices_dir=matrices_dir,
        config=config,
        field=field,
    )


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
