"""WorldQuant Brain-style quantitative operators for time-series and cross-sectional alpha computation."""
import numpy as np
import pandas as pd


def delta(df: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    """Returns today's value minus the value d days ago: x_t - x_{t-d}."""
    return df.diff(d)


def delay(df: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    """Returns the value d days ago: x_{t-d}."""
    return df.shift(d)


def ts_mean(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """Rolling time-series mean over window d."""
    return df.rolling(window=d, min_periods=max(1, d // 2)).mean()


def ts_std(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """Rolling time-series standard deviation over window d."""
    return df.rolling(window=d, min_periods=max(2, d // 2)).std()


def ts_zscore(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """Rolling z-score: (x - mean(x, d)) / std(x, d)."""
    mean = ts_mean(df, d)
    std = ts_std(df, d).replace(0, np.nan)
    return (df - mean) / std


def ts_rank(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """Rolling time-series percentile rank over the last d days (normalized to [0, 1])."""
    return df.rolling(window=d, min_periods=max(2, d // 2)).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
    )


def ts_corr(df_x: pd.DataFrame, df_y: pd.DataFrame, d: int) -> pd.DataFrame:
    """Rolling correlation between two cross-sectional panels over window d."""
    return df_x.rolling(window=d, min_periods=max(2, d // 2)).corr(df_y)


def decay_linear(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """
    Weighted moving average with linearly decaying weights:
    weight for day i is (d - i) for i in 0..d-1.
    """
    weights = np.arange(1, d + 1, dtype=float)
    weights /= weights.sum()

    def _weighted_avg(x):
        return np.dot(x, weights)

    return df.rolling(window=d, min_periods=d).apply(_weighted_avg, raw=True)


def cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-sectional percentile rank across stocks at each timestamp.
    Resulting values lie in [0, 1].
    """
    return df.rank(axis=1, pct=True, ascending=True)


def cs_demean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-sectional demeaning: alpha_i = alpha_i - mean(alpha).
    Guarantees sum(alpha_i) == 0 across stocks at each timestamp (Dollar-neutral long-short balance).
    """
    row_mean = df.mean(axis=1)
    return df.sub(row_mean, axis=0)


def cs_scale(df: pd.DataFrame, target_leverage: float = 1.0) -> pd.DataFrame:
    """
    Cross-sectional L1 scaling:
    scales weights so that sum(abs(weights)) == target_leverage for each timestamp.
    Preserves dollar neutrality if input is demeaned.
    """
    l1_sum = df.abs().sum(axis=1).replace(0, np.nan)
    return df.div(l1_sum, axis=0) * target_leverage
