"""Diversified Alpha Library consisting of 10 quantitative signals (WorldQuant IQC style)."""
import pandas as pd
import numpy as np
from typing import Dict, List
from src.alphas.base import AlphaStrategy
from src.data.preprocessor import CrossSectionalDataContainer
from src.alphas.reversal_5d import Reversal5D
from src.alphas.operators import (
    ts_mean, ts_std, ts_zscore, ts_rank, ts_corr, delta, delay, decay_linear, cs_rank
)


class Alpha01_Reversal5D(Reversal5D):
    """Alpha 1: Classic 5-day reversal benchmark."""
    pass


class Alpha02_Momentum1M(AlphaStrategy):
    """Alpha 2: 1-Month intermediate momentum (excluding latest 2 days to avoid short-term microstructure noise)."""
    def __init__(self, momentum_window: int = 21, skip_days: int = 2):
        super().__init__(name="Alpha_02_Momentum_1M", category="momentum")
        self.momentum_window = momentum_window
        self.skip_days = skip_days

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        # P_{t - 2} / P_{t - 21} - 1
        p_skip = data.adj_close.shift(self.skip_days)
        p_base = data.adj_close.shift(self.momentum_window)
        return (p_skip - p_base) / p_base


class Alpha03_VolumePriceTrend(AlphaStrategy):
    """Alpha 3: Negative correlation between returns and volume change over 10 days (volume exhaustion reversal)."""
    def __init__(self, window: int = 10):
        super().__init__(name="Alpha_03_VolumePriceTrend", category="volume_price")
        self.window = window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        ret = data.returns
        vol_change = delta(data.volume, 1) / data.volume.shift(1).replace(0, np.nan)
        # Invert correlation: stocks where price fell on rising volume are oversold
        return -ts_corr(ret, vol_change, self.window)


class Alpha04_VolNormalizedReversal(AlphaStrategy):
    """Alpha 4: 5-Day return reversal normalized by 20-day historical volatility."""
    def __init__(self, reversal_window: int = 5, vol_window: int = 20):
        super().__init__(name="Alpha_04_VolNormalizedReversal", category="volatility_adjusted")
        self.reversal_window = reversal_window
        self.vol_window = vol_window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        ret_5d = (data.adj_close - data.adj_close.shift(self.reversal_window)) / data.adj_close.shift(self.reversal_window)
        vol_20d = ts_std(data.returns, self.vol_window)
        # Negative sign for reversal
        return -ret_5d / vol_20d.replace(0, np.nan)


class Alpha05_MeanReversionBollinger(AlphaStrategy):
    """Alpha 5: Bollinger Band distance (negative z-score of price relative to 20-day moving average)."""
    def __init__(self, window: int = 20):
        super().__init__(name="Alpha_05_MeanReversionBollinger", category="mean_reversion")
        self.window = window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        zscore = ts_zscore(data.adj_close, self.window)
        return -zscore  # Buy when below moving average, sell when above


class Alpha06_VWAPReversion(AlphaStrategy):
    """Alpha 6: Price divergence from proxy VWAP over 5 days."""
    def __init__(self, window: int = 5):
        super().__init__(name="Alpha_06_VWAPReversion", category="vwap_reversion")
        self.window = window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        typical_price = (data.high + data.low + data.close) / 3.0
        pv = typical_price * data.volume
        rolling_pv = ts_mean(pv, self.window)
        rolling_vol = ts_mean(data.volume, self.window)
        vwap_proxy = rolling_pv / rolling_vol.replace(0, np.nan)
        # Buy stocks trading below rolling VWAP
        return -(data.close - vwap_proxy) / vwap_proxy.replace(0, np.nan)


class Alpha07_LiquiditySurge(AlphaStrategy):
    """Alpha 7: Abnormal trading volume surge indicator with directional price reaction."""
    def __init__(self, short_window: int = 5, long_window: int = 20):
        super().__init__(name="Alpha_07_LiquiditySurge", category="liquidity")
        self.short_window = short_window
        self.long_window = long_window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        vol_short = ts_mean(data.volume, self.short_window)
        vol_long = ts_mean(data.volume, self.long_window)
        surge_ratio = vol_short / vol_long.replace(0, np.nan)
        ret_short = (data.adj_close - data.adj_close.shift(self.short_window)) / data.adj_close.shift(self.short_window)
        # Contrarian signal on unusual volume surges
        return -ret_short * surge_ratio


class Alpha08_RangeReversal(AlphaStrategy):
    """Alpha 8: Intraday Close position relative to High-Low range (Stochastic %K-like cross-sectional reversal)."""
    def __init__(self, window: int = 14):
        super().__init__(name="Alpha_08_RangeReversal", category="intraday_range")
        self.window = window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        highest_high = data.high.rolling(self.window).max()
        lowest_low = data.low.rolling(self.window).min()
        channel_pos = (data.close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
        # Contrarian: buy oversold in channel (near lower band)
        return -(channel_pos - 0.5)


class Alpha09_DualMACrossover(AlphaStrategy):
    """Alpha 9: Medium-term trend following using exponential decay linear moving averages."""
    def __init__(self, fast_window: int = 10, slow_window: int = 50):
        super().__init__(name="Alpha_09_DualMACrossover", category="trend_following")
        self.fast_window = fast_window
        self.slow_window = slow_window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        ma_fast = decay_linear(data.adj_close, self.fast_window)
        ma_slow = decay_linear(data.adj_close, self.slow_window)
        return (ma_fast - ma_slow) / ma_slow.replace(0, np.nan)


class Alpha10_MarketNeutralResidualReversal(AlphaStrategy):
    """Alpha 10: Pure idiosyncratic return reversal after stripping out equal-weighted cross-sectional market return."""
    def __init__(self, window: int = 3):
        super().__init__(name="Alpha_10_ResidualReversal", category="idiosyncratic_reversal")
        self.window = window

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        cum_ret = (data.adj_close - data.adj_close.shift(self.window)) / data.adj_close.shift(self.window)
        market_ret = cum_ret.mean(axis=1)
        residual_ret = cum_ret.sub(market_ret, axis=0)
        return -residual_ret


def get_all_alphas() -> List[AlphaStrategy]:
    """Returns the set of 10 diversified alpha strategies."""
    return [
        Alpha01_Reversal5D(),
        Alpha02_Momentum1M(),
        Alpha03_VolumePriceTrend(),
        Alpha04_VolNormalizedReversal(),
        Alpha05_MeanReversionBollinger(),
        Alpha06_VWAPReversion(),
        Alpha07_LiquiditySurge(),
        Alpha08_RangeReversal(),
        Alpha09_DualMACrossover(),
        Alpha10_MarketNeutralResidualReversal(),
    ]
