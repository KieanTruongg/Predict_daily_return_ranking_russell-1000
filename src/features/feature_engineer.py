"""
Feature Engineering Store for ML Alpha Modeling — v4 (Matrix-based, vectorized).

Thay đổi so với v3:
  - Fix schema: dùng lowercase columns (close, high, low, volume) theo v4 Parquet API
  - Approach: vectorized trên toàn bộ Date×Ticker matrix thay vì ticker-by-ticker
  - Thêm winsorize return tại P1%/P99% (cross-sectional per day)
  - Thêm filter: tickers có < min_valid_days bị gán NaN toàn bộ trong ngày đó
  - Handle volume = 0 → gán NaN cho Amihud / VWAP features
  - Thêm Amihud Illiquidity, Turnover proxy

Quyết định thiết kế (từ Sanity Checks S1–S7 & EDA T1–T2):
  - adj_close ≡ close → chỉ dùng `close` cho tất cả features
  - Winsorize: clip daily return tại P1%/P99% per cross-section trước khi tính momentum
  - Ngưỡng lọc ticker: ≥ 252 ngày non-NaN trong cửa sổ lookback
  - volume = 0 → Amihud, VWAP = NaN
"""

from __future__ import annotations
from typing import Dict, Optional
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Helper: winsorize a DataFrame row-wise (cross-sectional per day)
# ──────────────────────────────────────────────────────────────────────────────
def _cs_winsorize(df: pd.DataFrame, lo: float = 0.01, hi: float = 0.99) -> pd.DataFrame:
    """Clip each row at [lo, hi] quantile cross-sectionally (per trading day)."""
    q_lo = df.quantile(lo, axis=1)
    q_hi = df.quantile(hi, axis=1)
    return df.clip(lower=q_lo, upper=q_hi, axis=0)


def _cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile rank per day, result in [0, 1]."""
    return df.rank(axis=1, pct=True, na_option="keep")


def _rolling_std_matrix(df: pd.DataFrame, window: int, min_periods: int | None = None) -> pd.DataFrame:
    """Column-wise rolling std on a Date×Ticker matrix."""
    return df.rolling(window, min_periods=min_periods or window // 2).std()


def _rolling_mean_matrix(df: pd.DataFrame, window: int, min_periods: int | None = None) -> pd.DataFrame:
    return df.rolling(window, min_periods=min_periods or window // 2).mean()


# ──────────────────────────────────────────────────────────────────────────────
class FeatureEngineer:
    """
    Computes a comprehensive feature matrix for cross-sectional return prediction.

    Input  : Dict of Date×Ticker matrices (close, high, low, volume, returns,
             forward_returns) — all lowercase, v4 schema.
    Output : Long-format DataFrame indexed by (date, ticker) with all features.

    Features computed:
      Momentum/Reversal : ret_1d, ret_5d, ret_20d, ret_60d, ret_252d
      Moving Averages   : close_to_sma_20, close_to_sma_50, close_to_sma_200
      Technical         : rsi_14, bb_pct_b, bb_bandwidth, hl_spread, close_to_high
      Volume            : vol_ratio_5_20, vol_zscore_20, amihud_20d, close_to_vwap_5
      Volatility        : realized_vol_5d, realized_vol_20d, realized_vol_60d
      CS Rank features  : ret_1d_rank, ret_5d_rank, ret_20d_rank, rsi_14_rank, vol_rank
      Target            : target_forward_return, target_return_rank
    """

    def __init__(
        self,
        forward_lookahead: int = 1,
        winsorize_pct: float = 0.01,
        min_valid_days: int = 252,
    ):
        self.forward_lookahead = forward_lookahead
        self.winsorize_pct     = winsorize_pct
        self.min_valid_days    = min_valid_days

    # ──────────────────────────────────────────────────────────────────────────
    def build_feature_matrix(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        volume: pd.DataFrame,
        forward_returns: pd.DataFrame,
    ) -> Dict[str, pd.DataFrame]:
        """
        Vectorized feature computation on Date×Ticker matrices.

        Parameters
        ----------
        close, high, low, volume, forward_returns : pd.DataFrame
            Date×Ticker matrices (index=date, columns=ticker), v4 schema (lowercase).

        Returns
        -------
        Dict[str, pd.DataFrame]
            {feature_name: Date×Ticker matrix}
        """
        features: Dict[str, pd.DataFrame] = {}

        # ── 0. Preprocessing ─────────────────────────────────────────────────
        # Tính daily return từ close (v4: close = SplitAdjusted)
        ret = close.pct_change()

        # Winsorize cross-sectionally per day
        ret_w = _cs_winsorize(ret, self.winsorize_pct, 1 - self.winsorize_pct)

        # Mask volume = 0 → NaN (cho Amihud / VWAP)
        vol_clean = volume.replace(0, np.nan)

        # ── 1. Momentum / Reversal features ──────────────────────────────────
        for d in [1, 2, 5, 10, 20, 60, 252]:
            # Tính compound return qua d ngày từ winsorized daily returns
            # (1+r1)*(1+r2)*...*(1+rd) - 1  ≈ sum for small d, exact cho large d
            log_ret = np.log1p(ret_w.fillna(0))
            roll_sum = log_ret.rolling(d, min_periods=max(1, d // 2)).sum()
            features[f"ret_{d}d"] = np.expm1(roll_sum).where(ret.notna().rolling(d).sum() >= d // 2)

        # ── 2. Moving Averages & price ratios ─────────────────────────────────
        for w in [20, 50, 200]:
            sma = _rolling_mean_matrix(close, w)
            features[f"close_to_sma_{w}"] = (close / sma - 1.0).where(sma > 0)

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd  = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        features["macd_hist_norm"] = (macd - macd_signal) / close.replace(0, np.nan)

        # ── 3. RSI 14 ─────────────────────────────────────────────────────────
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14, min_periods=7).mean()
        loss  = (-delta.clip(upper=0)).rolling(14, min_periods=7).mean()
        rs    = gain / loss.replace(0, np.nan)
        features["rsi_14"] = 100 - (100 / (1 + rs))

        # ── 4. Bollinger Bands ────────────────────────────────────────────────
        bb_mid = _rolling_mean_matrix(close, 20)
        bb_std = _rolling_std_matrix(close, 20)
        bb_up  = bb_mid + 2 * bb_std
        bb_lo  = bb_mid - 2 * bb_std
        bb_rng = (bb_up - bb_lo).replace(0, np.nan)
        features["bb_pct_b"]    = (close - bb_lo) / bb_rng
        features["bb_bandwidth"] = bb_rng / bb_mid.replace(0, np.nan)

        # ── 5. Intraday range features ────────────────────────────────────────
        hl = (high - low).replace(0, np.nan)
        features["hl_spread"]     = hl / close.replace(0, np.nan)
        features["close_to_high"] = (high - close) / hl

        # ── 6. Volume features ────────────────────────────────────────────────
        vol_ma5  = _rolling_mean_matrix(vol_clean, 5)
        vol_ma20 = _rolling_mean_matrix(vol_clean, 20)
        vol_std20 = _rolling_std_matrix(vol_clean, 20)
        features["vol_ratio_5_20"] = (vol_ma5 / vol_ma20.replace(0, np.nan)).clip(0, 10)
        features["vol_zscore_20"]  = (vol_clean - vol_ma20) / vol_std20.replace(0, np.nan)

        # VWAP 5-day proxy: sum(typical_price * volume) / sum(volume)
        typical_p = (high + low + close) / 3.0
        pv        = typical_p * vol_clean
        vwap_5    = pv.rolling(5, min_periods=3).sum() / vol_clean.rolling(5, min_periods=3).sum()
        features["close_to_vwap_5"] = (close / vwap_5.replace(0, np.nan) - 1.0).clip(-0.5, 0.5)

        # Amihud Illiquidity: mean(|ret| / dollar_volume) over 20d
        dollar_vol  = close * vol_clean
        amihud_daily = ret_w.abs() / dollar_vol.replace(0, np.nan)
        features["amihud_20d"] = amihud_daily.rolling(20, min_periods=10).mean() * 1e6  # scale

        # ── 7. Realized Volatility ────────────────────────────────────────────
        for v in [5, 20, 60]:
            features[f"realized_vol_{v}d"] = (
                _rolling_std_matrix(ret_w, v, min_periods=v // 2) * np.sqrt(252)
            )

        # ── 8. Cross-sectional rank features (per day) ────────────────────────
        for fname in ["ret_1d", "ret_5d", "ret_20d", "rsi_14", "realized_vol_20d", "amihud_20d"]:
            if fname in features:
                features[f"{fname}_rank"] = _cs_rank(features[fname])

        # ── 9. Target ─────────────────────────────────────────────────────────
        features["target_forward_return"] = forward_returns
        features["target_return_rank"]    = _cs_rank(forward_returns)

        # ── 10. Ticker validity mask (≥ min_valid_days non-NaN in rolling window) ─
        valid_mask = close.notna().rolling(self.min_valid_days, min_periods=1).sum() >= self.min_valid_days
        for k in list(features.keys()):
            if k not in ("target_forward_return", "target_return_rank"):
                features[k] = features[k].where(valid_mask)

        return features

    # ──────────────────────────────────────────────────────────────────────────
    def build_features_for_ticker(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Legacy per-ticker interface — kept for backward compatibility.
        Accepts a single-ticker DataFrame with lowercase columns: close, high, low, volume.
        """
        feats = pd.DataFrame(index=df.index)
        close  = df["close"] if "close" in df.columns else df["Close"]
        high   = df["high"]  if "high"  in df.columns else df["High"]
        low    = df["low"]   if "low"   in df.columns else df["Low"]
        volume = df["volume"] if "volume" in df.columns else df["Volume"]

        ret = close.pct_change()

        for d in [1, 2, 5, 10, 20, 60, 252]:
            feats[f"ret_{d}d"] = close.pct_change(d)

        for w in [20, 50, 200]:
            sma = close.rolling(w, min_periods=w // 2).mean()
            feats[f"close_to_sma_{w}"] = close / sma - 1.0

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14, min_periods=7).mean()
        loss  = (-delta.clip(upper=0)).rolling(14, min_periods=7).mean()
        rs    = gain / loss.replace(0, np.nan)
        feats["rsi_14"] = 100 - (100 / (1 + rs))

        bb_mid = close.rolling(20, min_periods=10).mean()
        bb_std = close.rolling(20, min_periods=10).std()
        bb_up  = bb_mid + 2 * bb_std
        bb_lo  = bb_mid - 2 * bb_std
        bb_rng = (bb_up - bb_lo).replace(0, np.nan)
        feats["bb_pct_b"]     = (close - bb_lo) / bb_rng
        feats["bb_bandwidth"] = bb_rng / bb_mid.replace(0, np.nan)

        hl = (high - low).replace(0, np.nan)
        feats["hl_spread"]     = hl / close.replace(0, np.nan)
        feats["close_to_high"] = (high - close) / hl

        vol_clean = volume.replace(0, np.nan)
        vol_ma5   = vol_clean.rolling(5,  min_periods=3).mean()
        vol_ma20  = vol_clean.rolling(20, min_periods=10).mean()
        feats["vol_ratio_5_20"] = (vol_ma5 / vol_ma20.replace(0, np.nan)).clip(0, 10)
        feats["vol_zscore_20"]  = (vol_clean - vol_ma20) / vol_clean.rolling(20).std().replace(0, np.nan)

        for v in [5, 20, 60]:
            feats[f"realized_vol_{v}d"] = ret.rolling(v, min_periods=v // 2).std() * np.sqrt(252)

        feats["target_forward_return"] = close.shift(-self.forward_lookahead) / close - 1.0

        return feats
