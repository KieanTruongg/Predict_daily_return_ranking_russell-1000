"""
src.features.transforms
=======================
Cross-sectional transforms respecting Point-In-Time universe masks.

CRITICAL INVARIANT:
Assets outside the active universe mask (or with missing data) MUST NEVER be ranked,
standardized, or winsorized alongside valid members. Non-members remain strictly np.nan.

RANKING FORMULA CONVENTION:
Uniform Cross-Sectional Rank in [0.0, 1.0]:
    rank_norm = (rank - 1) / (N - 1)
where N is the number of valid (non-NaN) constituents on that date.
Ties are resolved via average ranking (method='average').
For N = 1, rank_norm = 0.5.
For N = 0, all values remain NaN.
"""

from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
import pandas as pd


def _apply_mask(matrix: pd.DataFrame, mask: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Helper to strictly set non-member cells to np.nan."""
    if mask is None:
        return matrix.copy()
    mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
    return matrix.where(mask_aligned, other=np.nan)


def cross_sectional_rank(
    matrix: pd.DataFrame,
    mask: Optional[pd.DataFrame] = None,
    pct: bool = True,
    ascending: bool = True,
    method: str = "average",
) -> pd.DataFrame:
    """
    Computes cross-sectional ranking across stocks for each date (row-wise).

    Parameters:
        matrix: 2D feature DataFrame (dates x canonical SIDs).
        mask: Optional boolean mask DataFrame. Only cells where mask == True participate in ranking.
        pct: If True, returns normalized uniform ranks in [0.0, 1.0] using:
                 (rank - 1) / (N - 1)
             where N is the count of valid non-NaN elements on that row.
             Ties receive the average rank.
             If False, returns raw 1-based ranks (1 .. N).
        ascending: If True, smallest value gets lowest rank (rank=1 or 0.0).
        method: Tie-breaking method for pandas.DataFrame.rank ('average', 'min', 'max', 'first', 'dense').
                Default: 'average'.

    Returns:
        pd.DataFrame of cross-sectional ranks. Non-members strictly remain np.nan.
    """
    masked = _apply_mask(matrix, mask)

    # 1-based ranks along cross-section (axis=1), keeping NaNs untouched
    raw_ranks = masked.rank(axis=1, ascending=ascending, pct=False, method=method, na_option="keep")

    if not pct:
        if mask is not None:
            mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
            raw_ranks = raw_ranks.where(mask_aligned, other=np.nan)
        return raw_ranks

    # Count valid (non-NaN) assets per date
    n_valid = masked.notna().sum(axis=1)

    # Vectorized uniform normalization: (rank - 1) / (N - 1)
    # Where N > 1 -> (rank - 1) / (N - 1)
    # Where N == 1 -> 0.5
    # Where N == 0 -> NaN
    denom = (n_valid - 1.0).replace(0.0, np.nan)
    norm_ranks = raw_ranks.sub(1.0, axis=0).div(denom, axis=0)

    # Handle N == 1 case: exactly 0.5 for the single valid asset
    single_asset_mask = n_valid == 1
    if single_asset_mask.any():
        for dt in n_valid.index[single_asset_mask]:
            valid_col = masked.loc[dt].dropna().index
            norm_ranks.loc[dt, valid_col] = 0.5

    # Strictly re-enforce mask to guarantee zero imputation or leakage
    if mask is not None:
        mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
        norm_ranks = norm_ranks.where(mask_aligned, other=np.nan)

    return norm_ranks


def cross_sectional_demean(
    matrix: pd.DataFrame,
    mask: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Subtracts the cross-sectional mean (computed strictly over active universe members)
    for each date. Non-members remain np.nan.
    """
    masked = _apply_mask(matrix, mask)
    row_means = masked.mean(axis=1, skipna=True)
    demeaned = masked.sub(row_means, axis=0)

    if mask is not None:
        mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
        demeaned = demeaned.where(mask_aligned, other=np.nan)

    return demeaned


def cross_sectional_zscore(
    matrix: pd.DataFrame,
    mask: Optional[pd.DataFrame] = None,
    ddof: int = 1,
) -> pd.DataFrame:
    """
    Normalizes each cross-section to zero mean and unit variance strictly across
    active universe members. Non-members remain np.nan.
    """
    masked = _apply_mask(matrix, mask)
    row_means = masked.mean(axis=1, skipna=True)
    row_stds = masked.std(axis=1, ddof=ddof, skipna=True).replace(0.0, np.nan)

    zscores = masked.sub(row_means, axis=0).div(row_stds, axis=0)

    if mask is not None:
        mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
        zscores = zscores.where(mask_aligned, other=np.nan)

    return zscores


def cross_sectional_winsorize(
    matrix: pd.DataFrame,
    mask: Optional[pd.DataFrame] = None,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> pd.DataFrame:
    """
    Winsorizes cross-sectional outliers at specified quantile thresholds.
    Computed strictly across active universe members for each date.
    """
    masked = _apply_mask(matrix, mask)

    lower_bounds = masked.quantile(lower_quantile, axis=1)
    upper_bounds = masked.quantile(upper_quantile, axis=1)

    winsorized = masked.clip(lower=lower_bounds, upper=upper_bounds, axis=0)

    if mask is not None:
        mask_aligned = mask.reindex(index=matrix.index, columns=matrix.columns).fillna(False).astype(bool)
        winsorized = winsorized.where(mask_aligned, other=np.nan)

    return winsorized
