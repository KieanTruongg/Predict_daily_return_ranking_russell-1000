# ⚠️ SCHEMA WARNING: This file uses OLD schema (capitalized columns: Close, Adj Close, Volume).
# v4 Pipeline (Phase 1/2) uses LOWERCASE schema. NOT used in current pipeline.
# Reserved for Phase 3. Use src/features/feature_engineer.py for current feature work.

"""Cross-sectional matrix transformation and alignment for fast alpha computation.

Supports both schema formats:
  - v4 (lowercase): date, ticker, open, high, low, close, volume
  - Legacy (capitalized): Date, Ticker, Open, High, Low, Close, Adj Close, Volume

Automatically detects and normalizes to the capitalized format used by
CrossSectionalDataContainer.
"""
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

    def get_n_dates(self) -> int:
        return len(self.close.index)

    def get_n_tickers(self) -> int:
        return len(self.close.columns)

    def summary(self) -> str:
        """Return a human-readable summary string."""
        dates = self.get_dates()
        return (
            f"CrossSectionalDataContainer:\n"
            f"  Trading days : {self.get_n_dates():,}\n"
            f"  Tickers      : {self.get_n_tickers():,}\n"
            f"  Date range   : {dates[0].strftime('%Y-%m-%d')} → {dates[-1].strftime('%Y-%m-%d')}\n"
            f"  NaN % (close): {self.close.isna().sum().sum() / self.close.size * 100:.2f}%"
        )

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


def _detect_and_normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-detect column schema (lowercase v4 or capitalized legacy) and
    normalize to the capitalized format expected by pivot_panel_to_matrices.
    """
    cols_lower = {c.lower().strip() for c in df.columns}

    # Already capitalized?
    if "Ticker" in df.columns and "Date" in df.columns:
        return df

    # v4 lowercase schema
    df = df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # Handle 'time' -> 'date'
    if "time" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"time": "date"})

    rename_map = {
        "date": "Date",
        "ticker": "Ticker",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    df = df.rename(columns=rename_map)
    df["Date"] = pd.to_datetime(df["Date"])

    # Add Adj Close if missing (SplitAdjusted data: Adj Close == Close)
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    return df


def pivot_panel_to_matrices(
    df: pd.DataFrame,
    min_trading_days: int = 100,
) -> CrossSectionalDataContainer:
    """
    Pivots long panel DataFrame into aligned Date x Ticker matrices.
    Filters out tickers with fewer than min_trading_days.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format panel with columns: Date/date, Ticker/ticker, Open/open,
        High/high, Low/low, Close/close, Volume/volume.
        Automatically detects schema format (v4 lowercase or legacy capitalized).
    min_trading_days : int
        Minimum number of trading days required per ticker (default: 100).

    Returns
    -------
    CrossSectionalDataContainer
        Container with aligned Date x Ticker 2D matrices.
    """
    df = _detect_and_normalize_schema(df)

    # Filter tickers with sufficient history
    ticker_counts = df.groupby("Ticker").size()
    valid_tickers = ticker_counts[ticker_counts >= min_trading_days].index.tolist()
    n_removed = len(ticker_counts) - len(valid_tickers)
    if n_removed > 0:
        print(f"[Preprocessor] Filtered out {n_removed} tickers with < {min_trading_days} trading days")
    df = df[df["Ticker"].isin(valid_tickers)]

    df_work = df.reset_index(drop=True) if "Date" not in df.columns else df.copy()
    if df_work.index.name == "Date":
        df_work = df_work.reset_index()
    df_work["Date"] = pd.to_datetime(df_work["Date"])

    def _pivot_field(field_name: str) -> pd.DataFrame:
        p = df_work.pivot(index="Date", columns="Ticker", values=field_name)
        return p.sort_index()

    open_ = _pivot_field("Open")
    high = _pivot_field("High")
    low = _pivot_field("Low")
    close = _pivot_field("Close")
    adj_close = _pivot_field("Adj Close") if "Adj Close" in df_work.columns else close.copy()
    volume = _pivot_field("Volume")

    # Forward fill missing values up to 5 days to handle temporary halts, then keep NaN
    adj_close = adj_close.ffill(limit=5)
    close = close.ffill(limit=5)

    container = CrossSectionalDataContainer(
        open_=open_,
        high=high,
        low=low,
        close=close,
        adj_close=adj_close,
        volume=volume,
    )

    print(f"[Preprocessor] Built cross-sectional matrices:")
    print(f"  {container.summary()}")

    return container
