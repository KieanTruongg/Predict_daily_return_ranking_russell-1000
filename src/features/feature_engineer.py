"""Feature Engineering Store for ML Alpha Modeling (Phase 2).
Generates price-based, moving average, technical, volume, volatility, and cross-sectional features.
"""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class FeatureEngineer:
    """
    Computes a comprehensive feature matrix for cross-sectional return prediction.
    Features:
    - Price-based (returns: 1d, 5d, 20d, 60d)
    - Moving averages (SMA 5/10/20/50, EMA, crossovers)
    - Technical Indicators (RSI, Bollinger Bands, ATR proxy)
    - Volume-based (Volume SMA ratios, VWAP proxy distance)
    - Volatility (Realized volatility: 5d, 20d, 60d)
    - Cross-sectional ranking features
    - Target labels: forward return (r_{t+1}) and cross-sectional percentile rank of forward return
    """
    def __init__(self, forward_lookahead: int = 1):
        self.forward_lookahead = forward_lookahead

    def build_features_for_ticker(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Builds time-series features for a single stock OHLCV DataFrame.
        """
        feats = pd.DataFrame(index=df.index)
        close = df["Close"]
        adj_close = df["Adj Close"] if "Adj Close" in df.columns else close
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # 1. Price-based returns
        for d in [1, 2, 3, 5, 10, 20, 60]:
            feats[f"ret_{d}d"] = adj_close.pct_change(d)

        # 2. Moving Averages & ratios
        for w in [5, 10, 20, 50, 200]:
            sma = adj_close.rolling(w).mean()
            feats[f"sma_{w}"] = sma
            feats[f"close_to_sma_{w}"] = adj_close / sma - 1.0

        feats["ema_12"] = adj_close.ewm(span=12, adjust=False).mean()
        feats["ema_26"] = adj_close.ewm(span=26, adjust=False).mean()
        feats["macd"] = feats["ema_12"] - feats["ema_26"]
        feats["macd_signal"] = feats["macd"].ewm(span=9, adjust=False).mean()
        feats["macd_hist"] = feats["macd"] - feats["macd_signal"]

        # 3. Technical Indicators (RSI, Bollinger Bands, Range)
        # RSI 14
        delta = adj_close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        feats["rsi_14"] = 100 - (100 / (1 + rs))

        # Bollinger Bands (20d, 2 std)
        bb_mid = adj_close.rolling(20).mean()
        bb_std = adj_close.rolling(20).std()
        feats["bb_upper"] = bb_mid + 2 * bb_std
        feats["bb_lower"] = bb_mid - 2 * bb_std
        feats["bb_pct_b"] = (adj_close - feats["bb_lower"]) / (feats["bb_upper"] - feats["bb_lower"]).replace(0, np.nan)
        feats["bb_bandwidth"] = (feats["bb_upper"] - feats["bb_lower"]) / bb_mid

        # Intraday Normalized Range
        feats["hl_spread"] = (high - low) / close.replace(0, np.nan)
        feats["close_to_high"] = (high - close) / (high - low).replace(0, np.nan)

        # 4. Volume-based features
        vol_ma5 = volume.rolling(5).mean()
        vol_ma20 = volume.rolling(20).mean()
        feats["vol_ratio_5_20"] = vol_ma5 / vol_ma20.replace(0, np.nan)
        feats["vol_zscore_20"] = (volume - vol_ma20) / volume.rolling(20).std().replace(0, np.nan)

        # VWAP proxy (typical price * volume)
        typical_p = (high + low + close) / 3.0
        pv = typical_p * volume
        vwap_5 = pv.rolling(5).sum() / volume.rolling(5).sum().replace(0, np.nan)
        feats["close_to_vwap_5"] = close / vwap_5 - 1.0

        # 5. Volatility features
        daily_ret = adj_close.pct_change()
        for v in [5, 20, 60]:
            feats[f"realized_vol_{v}d"] = daily_ret.rolling(v).std() * np.sqrt(252)

        # 6. Targets / Labels
        # Forward return: (P_{t+1} - P_t) / P_t
        feats["target_forward_return"] = adj_close.shift(-self.forward_lookahead) / adj_close - 1.0

        return feats

    def build_cross_sectional_dataset(
        self,
        panel_dict: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Combines ticker-level features and adds cross-sectional rank features and ranking target.
        Returns a single unified DataFrame indexed by (Date, Ticker).
        """
        dfs = []
        for ticker, df in panel_dict.items():
            t_feats = self.build_features_for_ticker(df)
            t_feats["Ticker"] = ticker
            t_feats["Date"] = t_feats.index
            dfs.append(t_feats)

        if not dfs:
            return pd.DataFrame()

        full_df = pd.concat(dfs, ignore_index=True)
        full_df["Date"] = pd.to_datetime(full_df["Date"])
        full_df = full_df.sort_values(["Date", "Ticker"]).reset_index(drop=True)

        # Cross-sectional target: Percentile rank of future return per Date [0, 1]
        full_df["target_return_rank"] = full_df.groupby("Date")["target_forward_return"].rank(pct=True)

        # Cross-sectional rank of momentum/reversal features
        for f in ["ret_1d", "ret_5d", "ret_20d", "rsi_14"]:
            if f in full_df.columns:
                full_df[f"{f}_cs_rank"] = full_df.groupby("Date")[f].rank(pct=True)

        return full_df
