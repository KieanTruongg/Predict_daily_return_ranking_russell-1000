"""Cross-sectional matrix transformation and alignment for fast alpha computation."""
import os
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class CrossSectionalDataContainer:
    """
    Container storing aligned 2D matrices (Date x Ticker) for OHLCV, Adj Close, and Returns.
    This layout allows vectorized array operations across time and universe.
    """
    def __init__(
        self,
        open_: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        close: pd.DataFrame,
        adj_close: pd.DataFrame,
        volume: pd.DataFrame,
        returns: Optional[pd.DataFrame] = None,
        forward_returns: Optional[pd.DataFrame] = None,
    ):
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.adj_close = adj_close
        self.volume = volume

        # Compute 1-day simple returns if not provided: (P_t - P_{t-1}) / P_{t-1}
        if returns is None:
            self.returns = self.adj_close.pct_change(fill_method=None)
        else:
            self.returns = returns

        # Compute 1-day forward return: (P_{t+1} - P_t) / P_t
        if forward_returns is None:
            self.forward_returns = self.returns.shift(-1)
        else:
            self.forward_returns = forward_returns

    def get_dates(self) -> pd.DatetimeIndex:
        return self.close.index

    def get_tickers(self) -> List[str]:
        return list(self.close.columns)

    def save(self, directory: str):
        """Saves matrix tables to Parquet files in the specified directory."""
        os.makedirs(directory, exist_ok=True)
        self.open.to_parquet(os.path.join(directory, "open.parquet"))
        self.high.to_parquet(os.path.join(directory, "high.parquet"))
        self.low.to_parquet(os.path.join(directory, "low.parquet"))
        self.close.to_parquet(os.path.join(directory, "close.parquet"))
        self.adj_close.to_parquet(os.path.join(directory, "adj_close.parquet"))
        self.volume.to_parquet(os.path.join(directory, "volume.parquet"))
        self.returns.to_parquet(os.path.join(directory, "returns.parquet"))
        self.forward_returns.to_parquet(os.path.join(directory, "forward_returns.parquet"))

    @classmethod
    def load(cls, directory: str) -> "CrossSectionalDataContainer":
        """Loads matrix tables from Parquet directory."""
        return cls(
            open_=pd.read_parquet(os.path.join(directory, "open.parquet")),
            high=pd.read_parquet(os.path.join(directory, "high.parquet")),
            low=pd.read_parquet(os.path.join(directory, "low.parquet")),
            close=pd.read_parquet(os.path.join(directory, "close.parquet")),
            adj_close=pd.read_parquet(os.path.join(directory, "adj_close.parquet")),
            volume=pd.read_parquet(os.path.join(directory, "volume.parquet")),
            returns=pd.read_parquet(os.path.join(directory, "returns.parquet")),
            forward_returns=pd.read_parquet(os.path.join(directory, "forward_returns.parquet")),
        )


def pivot_panel_to_matrices(df: pd.DataFrame, min_trading_days: int = 250) -> CrossSectionalDataContainer:
    """
    Pivots long panel DataFrame into aligned Date x Ticker matrices.
    Filters out illiquid tickers with fewer than min_trading_days.
    """
    df = df.copy()
    if "Ticker" not in df.columns:
        raise ValueError("DataFrame must contain 'Ticker' column")

    # Group and filter tickers with sufficient history
    ticker_counts = df.groupby("Ticker").size()
    valid_tickers = ticker_counts[ticker_counts >= min_trading_days].index.tolist()
    df = df[df["Ticker"].isin(valid_tickers)]

    df_work = df.reset_index() if "Date" not in df.columns else df.copy()
    df_work["Date"] = pd.to_datetime(df_work["Date"])

    def _pivot_field(field_name: str) -> pd.DataFrame:
        p = df_work.pivot(index="Date", columns="Ticker", values=field_name)
        return p.sort_index()

    open_ = _pivot_field("Open")
    high = _pivot_field("High")
    low = _pivot_field("Low")
    close = _pivot_field("Close")
    adj_close = _pivot_field("Adj Close") if "Adj Close" in df.columns else close
    volume = _pivot_field("Volume")

    # Forward fill missing values up to 5 days to handle temporary halts, then keep NaN
    adj_close = adj_close.ffill(limit=5)
    close = close.ffill(limit=5)

    return CrossSectionalDataContainer(
        open_=open_,
        high=high,
        low=low,
        close=close,
        adj_close=adj_close,
        volume=volume,
    )
