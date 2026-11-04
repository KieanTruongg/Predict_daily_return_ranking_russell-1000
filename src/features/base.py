"""
src.features.base
=================
Base class for 2D matrix feature engineering (T trading days x N canonical SIDs).
Guarantees strict Point-In-Time causality, independent bar-quality input sanitation,
and ensures NaNs outside universe masks or during invalid quality windows are never
filled with zeros or imputed constants.

DESIGN PRINCIPLES:
1. Input Data Hygiene: Sanitized using `bar_quality_mask` (independent of index membership).
   Valid historical bars before constituent entry date are preserved for feature warmup.
2. Quality Window Completeness: If any bar within the lookback window is invalid (bad tick,
   spinoff jump, or missing bar), the rolling feature evaluates to NaN.
3. Output Masking: `membership_mask` is applied STRICTLY at the output date T.
   Constituents with sufficient clean history compute valid features on day 1 of membership.
4. Target Isolation: `valid_label_mask` is strictly forbidden from filtering feature inputs.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Literal, Optional, Tuple, Union
import numpy as np
import pandas as pd


class FeatureBase(ABC):
    """
    Abstract base class for quantitative features evaluated over 2D matrices.

    Subclasses implement `_calculate(data)` where `data` is a dictionary of
    2D price/volume/return matrices. The base class enforces:
    1. Coordinate alignment across input matrices.
    2. Quality-window hygiene via `bar_quality_mask`: Any bar where bar_quality_mask == False
       is set to NaN BEFORE rolling calculations, preventing dirty bars from leaking into
       trailing windows while preserving pre-membership warmup history.
    3. Strict universe mask preservation: Non-members at output date T are set to np.nan.
    4. Output dimension and coordinate preservation.
    """

    def __init__(
        self,
        name: str,
        category: str = "custom",
        window: int = 1,
        description: str = "",
    ):
        self.name = name
        self.category = category
        self.window = window
        self.description = description

    @abstractmethod
    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Calculates raw feature matrix from input matrices.
        Must return pd.DataFrame with same index and columns as inputs.
        """
        raise NotImplementedError

    def compute(
        self,
        data: Dict[str, pd.DataFrame],
        bar_quality_mask: Optional[pd.DataFrame] = None,
        membership_mask: Optional[pd.DataFrame] = None,
        valid_data_mask: Optional[pd.DataFrame] = None,
        mask: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Computes feature matrix with decoupled input bar-quality sanitation and output membership masking.

        Parameters:
            data: Dictionary of 2D matrices (e.g. {'adj_close': df, 'total_return': df}).
            bar_quality_mask: Optional boolean DataFrame indicating clean trading bars (independent
                              of index membership). Cells where bar_quality_mask == False are replaced
                              with np.nan in all input data BEFORE rolling calculations.
                              Preserves historical pre-membership bars for warmup!
            membership_mask: Optional boolean DataFrame indicating active Russell 1000 membership.
                             Applied STRICTLY to the output at date T. Non-members receive np.nan.
            valid_data_mask: Deprecated/legacy alias for bar_quality_mask. If bar_quality_mask is
                             not provided, this parameter is used with a fallback warning.
            mask: Optional alias for membership_mask (output masking).

        Returns:
            pd.DataFrame of shape (T, N) matching input coordinates.
        """
        if not data:
            raise ValueError("Input data dictionary cannot be empty.")

        # Coordinate alignment verification
        first_key = next(iter(data))
        ref_df = data[first_key]
        for k, v in data.items():
            if not v.index.equals(ref_df.index):
                raise ValueError(f"Matrix '{k}' index misaligned with '{first_key}'.")
            if not v.columns.equals(ref_df.columns):
                raise ValueError(f"Matrix '{k}' columns misaligned with '{first_key}'.")

        # Step 1: Input Bar-Quality Hygiene (Independent of Membership)
        # Determine the active quality mask for input sanitation
        q_mask = bar_quality_mask if bar_quality_mask is not None else valid_data_mask
        
        clean_data = {}
        if q_mask is not None:
            q_mask_aligned = q_mask.reindex(index=ref_df.index, columns=ref_df.columns).fillna(False).astype(bool)
            for k, df in data.items():
                clean_data[k] = df.where(q_mask_aligned, other=np.nan)
        else:
            clean_data = data

        # Step 2: Compute raw feature values from sanitized inputs (with historical warmup intact)
        feat_df = self._calculate(clean_data)

        if not isinstance(feat_df, pd.DataFrame):
            raise TypeError(f"Feature calculation must return a pd.DataFrame, got {type(feat_df)}")

        # Ensure index & columns preserved
        if not feat_df.index.equals(ref_df.index) or not feat_df.columns.equals(ref_df.columns):
            feat_df = feat_df.reindex(index=ref_df.index, columns=ref_df.columns)

        # Step 3: Apply output universe membership mask strictly at date T
        target_mask = membership_mask if membership_mask is not None else mask
        if target_mask is not None:
            m_aligned = target_mask.reindex(index=ref_df.index, columns=ref_df.columns).fillna(False).astype(bool)
            # Strictly assign np.nan outside universe at date T — NEVER fill with 0.0 or constants
            feat_df = feat_df.where(m_aligned, other=np.nan)

        return feat_df

    def __repr__(self) -> str:
        return f"<Feature: {self.name} ({self.category}, window={self.window})>"


class TotalReturnMomentumFeature(FeatureBase):
    """
    Computes rolling multi-day cumulative momentum:
    Either via total_return: prod_{k=0}^{w-1} (1 + total_return_{t-k}) - 1
    Or via adj_close: (adj_close_t / adj_close_{t-w}) - 1

    Requires explicit specification of `price_type` to avoid economic ambiguity.
    """

    def __init__(
        self,
        window: int = 5,
        price_type: Literal["total_return", "adjusted_close"] = "total_return",
        name: Optional[str] = None,
    ):
        feat_name = name or (f"MOM_{window:03d}" if price_type == "total_return" else f"MOM_ADJ_{window:03d}")
        super().__init__(
            name=feat_name,
            category="momentum",
            window=window,
            description=f"{window}-day cumulative {price_type} momentum",
        )
        self.price_type = price_type

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if self.price_type == "total_return":
            if "total_return" not in data:
                raise KeyError(
                    "TotalReturnMomentumFeature(price_type='total_return') requires 'total_return' matrix. "
                    "Pass 'total_return' in data or explicitly specify price_type='adjusted_close'."
                )
            ret = data["total_return"]
            # Cumulative product via log returns: exp(sum(log1p)) - 1
            # If any bar in the window is NaN (e.g. from bar_quality_mask), sum(min_periods=w) returns NaN!
            log_ret = np.log1p(ret)
            rolling_log = log_ret.rolling(window=self.window, min_periods=self.window).sum()
            return np.expm1(rolling_log)

        elif self.price_type == "adjusted_close":
            if "adj_close" not in data:
                raise KeyError(
                    "TotalReturnMomentumFeature(price_type='adjusted_close') requires 'adj_close' matrix."
                )
            p = data["adj_close"]
            # Requires clean continuous prices: if any intervening price is NaN, return NaN
            valid_count = p.notna().rolling(window=self.window + 1, min_periods=self.window + 1).sum()
            mom = p / p.shift(self.window) - 1.0
            return mom.where(valid_count == (self.window + 1), other=np.nan)
        else:
            raise ValueError(f"Unknown price_type: {self.price_type}. Choose 'total_return' or 'adjusted_close'.")


class RealizedVolatilityFeature(FeatureBase):
    """
    Computes rolling annualised realized volatility:
    vol = std(return_series, window=w) * sqrt(252)

    Requires explicit specification of `return_type` to avoid economic ambiguity.
    """

    def __init__(
        self,
        window: int = 20,
        return_type: Literal["daily_return", "total_return"] = "daily_return",
        name: Optional[str] = None,
    ):
        feat_name = name or (f"VOL_{window:03d}" if return_type == "daily_return" else f"VOL_TOT_{window:03d}")
        super().__init__(
            name=feat_name,
            category="volatility",
            window=window,
            description=f"{window}-day annualized realized volatility from {return_type}",
        )
        self.return_type = return_type

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if self.return_type not in data:
            raise KeyError(
                f"RealizedVolatilityFeature(return_type='{self.return_type}') requires '{self.return_type}' in data. "
                f"Available keys: {list(data.keys())}."
            )
        ret = data[self.return_type]
        rolling_std = ret.rolling(window=self.window, min_periods=self.window).std(ddof=1)
        return rolling_std * np.sqrt(252.0)
