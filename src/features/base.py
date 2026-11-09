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
        field_quality_masks: Optional[Dict[str, pd.DataFrame]] = None,
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
            field_quality_masks: Optional dictionary of field-specific boolean DataFrames (e.g. {'open': mask, 'low': mask})
                                 for field-level quarantine isolation.

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
        q_mask_aligned = None
        if q_mask is not None:
            q_mask_aligned = q_mask.reindex(index=ref_df.index, columns=ref_df.columns).fillna(False).astype(bool)

        for k, df in data.items():
            field_mask = None
            if field_quality_masks and k in field_quality_masks:
                field_mask = field_quality_masks[k].reindex(index=ref_df.index, columns=ref_df.columns).fillna(False).astype(bool)

            if q_mask_aligned is not None and field_mask is not None:
                clean_data[k] = df.where(q_mask_aligned & field_mask, other=np.nan)
            elif q_mask_aligned is not None:
                clean_data[k] = df.where(q_mask_aligned, other=np.nan)
            elif field_mask is not None:
                clean_data[k] = df.where(field_mask, other=np.nan)
            else:
                clean_data[k] = df

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
            # Requires clean continuous, finite, positive prices: if any intervening price is NaN/Inf/<=0, return NaN
            is_valid = np.isfinite(p) & (p > 0)
            valid_count = is_valid.rolling(window=self.window + 1, min_periods=self.window + 1).sum()
            mom = p / p.shift(self.window) - 1.0
            return mom.where((valid_count == (self.window + 1)) & np.isfinite(mom), other=np.nan)
        else:
            raise ValueError(f"Unknown price_type: {self.price_type}. Choose 'total_return' or 'adjusted_close'.")


class RealizedVolatilityFeature(FeatureBase):
    """
    Computes rolling realized volatility:
    vol = std(return_series, window=w, ddof=1)

    Per docs/specifications/features_v1.md Section 4.1:
    - Default is daily unit (annualize=False), not multiplied by sqrt(252).
    - Requires explicit specification of `return_type` to avoid economic ambiguity.
    """

    def __init__(
        self,
        window: int = 20,
        return_type: Literal["daily_return", "total_return"] = "daily_return",
        annualize: bool = False,
        name: Optional[str] = None,
    ):
        feat_name = name or (
            f"vol_realized_{window}d" if not annualize else (f"VOL_{window:03d}" if return_type == "daily_return" else f"VOL_TOT_{window:03d}")
        )
        desc = (
            f"{window}-day daily realized volatility from {return_type}"
            if not annualize
            else f"{window}-day annualized realized volatility from {return_type}"
        )
        super().__init__(
            name=feat_name,
            category="volatility",
            window=window,
            description=desc,
        )
        self.return_type = return_type
        self.annualize = annualize

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if self.return_type not in data:
            raise KeyError(
                f"RealizedVolatilityFeature(return_type='{self.return_type}') requires '{self.return_type}' in data. "
                f"Available keys: {list(data.keys())}."
            )
        ret = data[self.return_type]
        valid_ret = np.isfinite(ret)
        valid_count = valid_ret.rolling(window=self.window, min_periods=self.window).sum()
        rolling_std = ret.rolling(window=self.window, min_periods=self.window).std(ddof=1)
        res = rolling_std * (np.sqrt(252.0) if self.annualize else 1.0)
        return res.where((valid_count == self.window) & np.isfinite(res), other=np.nan)


class PriceRatioMomentumFeature(FeatureBase):
    """
    Computes rolling price ratio momentum:
    ret_Wd[i, T] = P[i, T] / P[i, T - W] - 1
    where P = adj_close.

    Per docs/specifications/features_v1.md Section 3.2:
    - Requires W + 1 clean, finite, positive, continuous prices from T - W to T.
    - If any intermediate bar is missing or has bar_quality_mask == False, returns NaN.
    - Constant prices on a clean window return 0.0.
    """

    def __init__(
        self,
        window: int = 20,
        name: Optional[str] = None,
    ):
        feat_name = name or f"ret_{window}d"
        super().__init__(
            name=feat_name,
            category="momentum",
            window=window,
            description=f"{window}-day price ratio momentum from adj_close",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "adj_close" not in data:
            raise KeyError("PriceRatioMomentumFeature requires 'adj_close' matrix in data.")
        p = data["adj_close"]
        is_valid = np.isfinite(p) & (p > 0)
        valid_count = is_valid.rolling(window=self.window + 1, min_periods=self.window + 1).sum()
        mom = p / p.shift(self.window) - 1.0
        return mom.where((valid_count == (self.window + 1)) & np.isfinite(mom), other=np.nan)


class AmihudIlliquidityFeature(FeatureBase):
    """
    Computes rolling Amihud illiquidity ratio:
    amihud_illiq_Wd = 1e6 * mean_W(abs(daily_return) / (raw_close * raw_volume))

    Per docs/specifications/features_v1.md Section 5.2:
    - Daily dollar volume DV = raw_close * raw_volume.
    - Daily ratio = abs(daily_return) / DV.
    - Requires W clean pairs of return and positive DV.
    - Requires both raw_close > 0 and raw_volume > 0 individually.
    - Zero return with positive DV contributes 0.0.
    - Zero volume (DV <= 0) or missing return makes the daily ratio NaN,
      which causes the rolling window to evaluate to NaN.
    """

    def __init__(
        self,
        window: int = 20,
        scale: float = 1e6,
        name: Optional[str] = None,
    ):
        feat_name = name or f"amihud_illiq_{window}d"
        super().__init__(
            name=feat_name,
            category="liquidity",
            window=window,
            description=f"{window}-day Amihud illiquidity ratio (scale={scale:.0e})",
        )
        self.scale = scale

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        required = ["daily_return", "close", "volume"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"AmihudIlliquidityFeature requires {missing} in data. Available: {list(data.keys())}")

        ret = data["daily_return"]
        p_raw = data["close"]
        v_raw = data["volume"]

        # Each input must be finite, and prices/volumes must be strictly positive
        valid_p = np.isfinite(p_raw) & (p_raw > 0)
        valid_v = np.isfinite(v_raw) & (v_raw > 0)
        valid_ret = np.isfinite(ret)
        valid_bar = valid_p & valid_v & valid_ret

        dv = p_raw * v_raw
        ratio = np.abs(ret) / dv
        ratio = ratio.where(valid_bar, other=np.nan)

        rolling_mean = ratio.rolling(window=self.window, min_periods=self.window).mean()
        res = rolling_mean * self.scale
        return res.where(np.isfinite(res), other=np.nan)


def _compute_wilder_rsi_1d(prices: np.ndarray, window: int = 14) -> np.ndarray:
    """
    Computes 1D Wilder RSI with strict state reset on gaps/invalid bars.
    Per docs/specifications/features_v1.md Section 6.3.
    """
    n = len(prices)
    rsi = np.full(n, np.nan, dtype=np.float64)
    seeded = False
    avg_gain = 0.0
    avg_loss = 0.0
    streak_deltas = []

    decay = float(window - 1)

    for t in range(1, n):
        p_prev = prices[t - 1]
        p_curr = prices[t]

        # Both bars must be finite and positive
        if not np.isfinite(p_prev) or not np.isfinite(p_curr) or p_prev <= 0 or p_curr <= 0:
            seeded = False
            avg_gain = 0.0
            avg_loss = 0.0
            streak_deltas = []
            continue

        delta = p_curr - p_prev
        streak_deltas.append(delta)

        if not seeded:
            if len(streak_deltas) == window:
                gains = [max(d, 0.0) for d in streak_deltas]
                losses = [max(-d, 0.0) for d in streak_deltas]
                avg_gain = float(np.mean(gains))
                avg_loss = float(np.mean(losses))
                seeded = True

                if avg_loss == 0.0 and avg_gain == 0.0:
                    rsi[t] = 50.0
                elif avg_loss == 0.0:
                    rsi[t] = 100.0
                elif avg_gain == 0.0:
                    rsi[t] = 0.0
                else:
                    rs = avg_gain / avg_loss
                    rsi[t] = 100.0 - 100.0 / (1.0 + rs)
        else:
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            avg_gain = (decay * avg_gain + gain) / window
            avg_loss = (decay * avg_loss + loss) / window

            if avg_loss == 0.0 and avg_gain == 0.0:
                rsi[t] = 50.0
            elif avg_loss == 0.0:
                rsi[t] = 100.0
            elif avg_gain == 0.0:
                rsi[t] = 0.0
            else:
                rs = avg_gain / avg_loss
                rsi[t] = 100.0 - 100.0 / (1.0 + rs)

    return rsi


class RSIFeature(FeatureBase):
    """
    Computes Wilder smoothed Relative Strength Index (RSI).
    Per docs/specifications/features_v1.md Section 6.3:
    - State reset on invalid bars / quality flags.
    - Seeds with average of W clean consecutive deltas (W + 1 prices).
    - Flat series -> 50.0; all gain -> 100.0; all loss -> 0.0.
    """

    def __init__(
        self,
        window: int = 14,
        name: Optional[str] = None,
    ):
        feat_name = name or f"rsi_{window}d"
        super().__init__(
            name=feat_name,
            category="technical",
            window=window,
            description=f"{window}-day Wilder smoothed RSI with state reset",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "adj_close" not in data:
            raise KeyError("RSIFeature requires 'adj_close' matrix in data.")
        p_df = data["adj_close"]
        results = {}
        for col in p_df.columns:
            results[col] = _compute_wilder_rsi_1d(p_df[col].values, window=self.window)
        return pd.DataFrame(results, index=p_df.index)


class BollingerPctBFeature(FeatureBase):
    """
    Computes Bollinger Bands %B:
    bollinger_pct_b_Wd = (adj_close - lower) / (upper - lower)
    where:
    middle = mean_W(adj_close)
    sigma = std_W(adj_close, ddof=0)
    upper = middle + 2 * sigma
    lower = middle - 2 * sigma

    Per docs/specifications/features_v1.md Section 6.4:
    - Uses ddof=0 for sigma on price levels.
    - If sigma == 0 (zero band width), returns NaN.
    - Values outside [0, 1] are valid and NOT clipped.
    """

    def __init__(
        self,
        window: int = 20,
        k: float = 2.0,
        name: Optional[str] = None,
    ):
        feat_name = name or f"bollinger_pct_b_{window}d"
        super().__init__(
            name=feat_name,
            category="technical",
            window=window,
            description=f"{window}-day Bollinger Bands %B (k={k}, ddof=0)",
        )
        self.k = k

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "adj_close" not in data:
            raise KeyError("BollingerPctBFeature requires 'adj_close' matrix in data.")
        p = data["adj_close"]
        is_valid = np.isfinite(p) & (p > 0)
        valid_count = is_valid.rolling(window=self.window, min_periods=self.window).sum()
        m = p.rolling(window=self.window, min_periods=self.window).mean()
        sigma = p.rolling(window=self.window, min_periods=self.window).std(ddof=0)
        upper = m + self.k * sigma
        lower = m - self.k * sigma
        band_width = upper - lower
        pct_b = (p - lower) / band_width
        return pct_b.where((valid_count == self.window) & (sigma > 0) & np.isfinite(pct_b), other=np.nan)

class Mom12mSkip1mFeature(FeatureBase):
    """
    Computes 12-month momentum with 1-month skip:
    mom_12m_skip_1m[i, T] = P[i, T - 21] / P[i, T - 252] - 1
    where P = adj_close.

    Per docs/specifications/features_v1.md Section 3.3:
    - Measures return from T - 252 to T - 21 (skipping most recent 21 trading sessions).
    - Requires 232 clean, finite, positive, continuous prices across [T - 252 .. T - 21].
    - Changing prices after T - 21 does NOT affect the calculation.
    - If any intermediate price in [T - 252 .. T - 21] is dirty/missing, evaluates to NaN.
    """

    def __init__(
        self,
        lookback: int = 252,
        skip: int = 21,
        name: Optional[str] = None,
    ):
        feat_name = name or "mom_12m_skip_1m"
        super().__init__(
            name=feat_name,
            category="momentum",
            window=lookback,
            description=f"12-month momentum (lookback={lookback}d) skipping recent {skip}d",
        )
        self.lookback = lookback
        self.skip = skip
        self.active_span = lookback - skip + 1  # 252 - 21 + 1 = 232 bars

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "adj_close" not in data:
            raise KeyError("Mom12mSkip1mFeature requires 'adj_close' matrix in data.")
        p = data["adj_close"]
        is_valid = np.isfinite(p) & (p > 0)
        # Shift valid indicator by `skip` so rolling sum covers [T - lookback .. T - skip]
        valid_count = is_valid.shift(self.skip).rolling(window=self.active_span, min_periods=self.active_span).sum()
        p_num = p.shift(self.skip)
        p_den = p.shift(self.lookback)
        mom = (p_num / p_den) - 1.0
        return mom.where((valid_count == self.active_span) & np.isfinite(mom), other=np.nan)


class ParkinsonVolatilityFeature(FeatureBase):
    """
    Computes Parkinson realized volatility from daily high/low:
    vol_parkinson_Wd = sqrt(mean_W(ln(adj_high / adj_low)^2) / (4 * ln(2)))

    Per docs/specifications/features_v1.md Section 4.2:
    - Uses W pairs of adj_high and adj_low.
    - Requires adj_high >= adj_low > 0 and finite for each session.
    - If adj_high == adj_low, ln(1)^2 = 0 (valid contribution).
    - If adj_high < adj_low or non-positive, bar is invalid -> window evaluates to NaN.
    - Daily unit, no annualization.
    """

    def __init__(
        self,
        window: int = 20,
        name: Optional[str] = None,
    ):
        feat_name = name or f"vol_parkinson_{window}d"
        super().__init__(
            name=feat_name,
            category="volatility",
            window=window,
            description=f"{window}-day Parkinson high-low volatility (daily unit)",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        required = ["adj_high", "adj_low"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"ParkinsonVolatilityFeature requires {missing} in data. Available: {list(data.keys())}")

        h = data["adj_high"]
        l = data["adj_low"]

        valid_bar = np.isfinite(h) & np.isfinite(l) & (h >= l) & (l > 0)
        ratio = (h / l).where(valid_bar, other=np.nan)
        log_ratio = np.log(ratio)
        term = (log_ratio ** 2) / (4.0 * np.log(2.0))
        term = term.where(valid_bar, other=np.nan)

        rolling_mean = term.rolling(window=self.window, min_periods=self.window).mean()
        rolling_mean_pos = rolling_mean.where(rolling_mean >= 0, other=0.0)
        vol = np.sqrt(rolling_mean_pos)
        return vol.where(rolling_mean.notna() & np.isfinite(vol), other=np.nan)


class DownsideDeviationFeature(FeatureBase):
    """
    Computes downside semi-deviation at threshold 0:
    downside_deviation_Wd = sqrt(sum_W(min(daily_return, 0)^2) / W)

    Per docs/specifications/features_v1.md Section 4.3:
    - Uses split-adjusted return (daily_return).
    - Threshold is 0.0, denominator is W (full window length, not count of negative days).
    - Does NOT subtract mean, does NOT use ddof=1, does NOT annualize.
    - If all returns in the window are >= 0, returns 0.0.
    - Any missing/dirty return causes the window to evaluate to NaN.
    """

    def __init__(
        self,
        window: int = 20,
        name: Optional[str] = None,
    ):
        feat_name = name or f"downside_deviation_{window}d"
        super().__init__(
            name=feat_name,
            category="volatility",
            window=window,
            description=f"{window}-day downside deviation at threshold 0 (daily unit)",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "daily_return" not in data:
            raise KeyError("DownsideDeviationFeature requires 'daily_return' matrix in data.")

        ret = data["daily_return"]
        valid_ret = np.isfinite(ret)
        valid_count = valid_ret.rolling(window=self.window, min_periods=self.window).sum()

        neg_ret = np.minimum(ret, 0.0)
        neg_sq = (neg_ret ** 2).where(valid_ret, other=np.nan)
        rolling_mean_sq = neg_sq.rolling(window=self.window, min_periods=self.window).mean()
        downside = np.sqrt(rolling_mean_sq)
        return downside.where((valid_count == self.window) & np.isfinite(downside), other=np.nan)


class VolumeRatioFeature(FeatureBase):
    """
    Computes volume ratio between short and long rolling windows:
    volume_ratio_5_20 = mean_5(adj_volume) / mean_20(adj_volume)

    Per docs/specifications/features_v1.md Section 5.3:
    - Uses split-adjusted volume (adj_volume).
    - Both rolling windows end at session T.
    - Requires 20 clean, positive, finite volume bars (v > 0).
    - Denominator must be > 0.
    """

    def __init__(
        self,
        fast_window: int = 5,
        slow_window: int = 20,
        name: Optional[str] = None,
    ):
        feat_name = name or f"volume_ratio_{fast_window}_{slow_window}"
        super().__init__(
            name=feat_name,
            category="volume",
            window=slow_window,
            description=f"Volume ratio mean_{fast_window}(adj_volume) / mean_{slow_window}(adj_volume)",
        )
        self.fast_window = fast_window
        self.slow_window = slow_window

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "adj_volume" not in data:
            raise KeyError("VolumeRatioFeature requires 'adj_volume' matrix in data.")

        v = data["adj_volume"]
        valid_v = np.isfinite(v) & (v > 0)
        valid_count_slow = valid_v.rolling(window=self.slow_window, min_periods=self.slow_window).sum()
        valid_count_fast = valid_v.rolling(window=self.fast_window, min_periods=self.fast_window).sum()

        v_clean = v.where(valid_v, other=np.nan)
        m_fast = v_clean.rolling(window=self.fast_window, min_periods=self.fast_window).mean()
        m_slow = v_clean.rolling(window=self.slow_window, min_periods=self.slow_window).mean()

        ratio = m_fast / m_slow
        is_ok = (valid_count_slow == self.slow_window) & (valid_count_fast == self.fast_window) & (m_slow > 0) & np.isfinite(ratio)
        return ratio.where(is_ok, other=np.nan)


class LogDollarVolumeFeature(FeatureBase):
    """
    Computes log of 20-day mean dollar volume:
    log_dollar_volume_20d = log1p(mean_20(raw_close * raw_volume))

    Per docs/specifications/features_v1.md Section 5.4:
    - Dollar volume DV = raw_close * raw_volume in USD.
    - Computes rolling arithmetic mean of DV over 20 days first, then applies log1p.
    - Requires 20 clean, positive, finite pairs of close and volume.
    """

    def __init__(
        self,
        window: int = 20,
        name: Optional[str] = None,
    ):
        feat_name = name or f"log_dollar_volume_{window}d"
        super().__init__(
            name=feat_name,
            category="volume",
            window=window,
            description=f"{window}-day log dollar volume log1p(mean_{window}(raw_close * raw_volume))",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        required = ["close", "volume"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"LogDollarVolumeFeature requires {missing} in data. Available: {list(data.keys())}")

        p = data["close"]
        v = data["volume"]
        valid_bar = np.isfinite(p) & (p > 0) & np.isfinite(v) & (v > 0)
        valid_count = valid_bar.rolling(window=self.window, min_periods=self.window).sum()

        dv = (p * v).where(valid_bar, other=np.nan)
        mean_dv = dv.rolling(window=self.window, min_periods=self.window).mean()
        log_dv = np.log1p(mean_dv)
        return log_dv.where((valid_count == self.window) & (mean_dv > 0) & np.isfinite(log_dv), other=np.nan)


class IntradayReturnFeature(FeatureBase):
    """
    Computes single-day intraday return:
    ret_intraday[T] = adj_close[T] / adj_open[T] - 1

    Per docs/specifications/features_v1.md Section 6.1:
    - Uses adj_close and adj_open of the same trading session T.
    - Requires both prices to be finite and > 0.
    """

    def __init__(
        self,
        name: Optional[str] = None,
    ):
        feat_name = name or "ret_intraday"
        super().__init__(
            name=feat_name,
            category="intraday",
            window=1,
            description="Single-session intraday return (adj_close / adj_open - 1)",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        required = ["adj_close", "adj_open"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"IntradayReturnFeature requires {missing} in data. Available: {list(data.keys())}")

        c = data["adj_close"]
        o = data["adj_open"]
        valid_bar = np.isfinite(c) & (c > 0) & np.isfinite(o) & (o > 0)
        ret = (c / o) - 1.0
        return ret.where(valid_bar & np.isfinite(ret), other=np.nan)


class OvernightReturnFeature(FeatureBase):
    """
    Computes single-day overnight return:
    ret_overnight[T] = adj_open[T] / adj_close[T - 1] - 1

    Per docs/specifications/features_v1.md Section 6.2:
    - Measures overnight price movement from close of T - 1 to open of T.
    - Requires adj_open[T] > 0 and adj_close[T - 1] > 0, both finite and clean.
    - Identity relation: (1 + ret_1d) approx (1 + ret_overnight) * (1 + ret_intraday).
    """

    def __init__(
        self,
        name: Optional[str] = None,
    ):
        feat_name = name or "ret_overnight"
        super().__init__(
            name=feat_name,
            category="intraday",
            window=1,
            description="Overnight return (adj_open[T] / adj_close[T-1] - 1)",
        )

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        required = ["adj_close", "adj_open"]
        missing = [k for k in required if k not in data]
        if missing:
            raise KeyError(f"OvernightReturnFeature requires {missing} in data. Available: {list(data.keys())}")

        c = data["adj_close"]
        o = data["adj_open"]
        valid_curr = np.isfinite(o) & (o > 0)
        valid_prev = np.isfinite(c) & (c > 0)
        valid_prev_shifted = valid_prev.shift(1)

        ret = (o / c.shift(1)) - 1.0
        return ret.where(valid_curr & valid_prev_shifted & np.isfinite(ret), other=np.nan)

