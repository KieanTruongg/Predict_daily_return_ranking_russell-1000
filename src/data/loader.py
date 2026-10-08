# ⚠️ SCHEMA WARNING: This file uses OLD schema (capitalized columns: Close, Adj Close, Volume, High, Low).
# v4 Pipeline (Phase 1/2) uses LOWERCASE schema: close, high, low, volume.
# This file has NOT been updated to v4 and is NOT used in Phase 1/2 pipeline.
# DO NOT use for feature engineering — use src/features/feature_engineer.py instead.
# Reserved for potential Phase 3 refactoring. Last schema used: v3.

"""Data loader for Russell 1000 OHLCV dataset (QuantConnect v4 Parquet files).

Primary data source: Pre-processed Parquet files in data/processed/by_year/
Consolidated source: data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet

Legacy loaders (Stooq, Yahoo Finance) are preserved in clear/v1_src_data/loader.py
for backward compatibility reference.
"""
import os
import glob
from typing import List, Dict, Optional, Tuple
import pandas as pd

# ── Path constants ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BY_YEAR_DIR = os.path.join(BASE_DIR, "data", "processed", "by_year")
DAILY_OHLCV_DIR = os.path.join(BASE_DIR, "data", "processed", "daily_ohlcv")
CONSOLIDATED_FILE = os.path.join(DAILY_OHLCV_DIR, "russell1000_daily_2000_2026.parquet")

# ── Standard column spec ────────────────────────────────────────────────────
# Internal schema (lowercase, as stored in Parquet):
#   date, ticker, open, high, low, close, volume, year
#
# CrossSectionalDataContainer expects (capitalized):
#   Date, Ticker, Open, High, Low, Close, Adj Close, Volume

_RENAME_TO_UPPER = {
    "date": "Date",
    "ticker": "Ticker",
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume",
    "year": "Year",
}


def _standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names and add Adj Close (= Close for SplitAdjusted data)."""
    # Lowercase all columns first
    df.columns = [c.lower().strip() for c in df.columns]

    # Handle 'time' -> 'date'
    if "time" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"time": "date"})

    df["date"] = pd.to_datetime(df["date"])

    # Rename to capitalized for downstream compatibility
    df = df.rename(columns=_RENAME_TO_UPPER)

    # Add Adj Close = Close (data is already SplitAdjusted from QuantConnect)
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    return df


# ═════════════════════════════════════════════════════════════════════════════
#  PRIMARY LOADERS (QuantConnect v4 Parquet)
# ═════════════════════════════════════════════════════════════════════════════

def load_full_panel(
    start_year: int = 2000,
    end_year: int = 2026,
    capitalize: bool = True,
) -> pd.DataFrame:
    """
    Load the full consolidated daily OHLCV panel (2000-2026).

    Parameters
    ----------
    start_year : int
        First year to include (default: 2000).
    end_year : int
        Last year to include (default: 2026).
    capitalize : bool
        If True, return capitalized column names (Date, Ticker, Open, ...)
        compatible with CrossSectionalDataContainer.
        If False, return lowercase column names (date, ticker, open, ...).

    Returns
    -------
    pd.DataFrame
        Combined panel DataFrame with columns:
        [Date, Ticker, Open, High, Low, Close, Adj Close, Volume, Year]
    """
    if os.path.exists(CONSOLIDATED_FILE):
        print(f"[Loader] Reading consolidated file: {CONSOLIDATED_FILE}")
        df = pd.read_parquet(CONSOLIDATED_FILE)
    else:
        print(f"[Loader] Consolidated file not found. Building from by_year/ files...")
        df = load_by_year_range(start_year, end_year, capitalize=False)

    # Apply year filter
    if "year" not in df.columns:
        df.columns = [c.lower().strip() for c in df.columns]
    yr_col = "year" if "year" in df.columns else "Year"
    df = df[(df[yr_col] >= start_year) & (df[yr_col] <= end_year)]

    if capitalize:
        df = _standardize_schema(df)
    else:
        df.columns = [c.lower().strip() for c in df.columns]
        if "time" in df.columns and "date" not in df.columns:
            df = df.rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(["Date" if capitalize else "date",
                         "Ticker" if capitalize else "ticker"]).reset_index(drop=True)

    n_tickers = df["Ticker" if capitalize else "ticker"].nunique()
    print(f"[Loader] Loaded {len(df):,} rows | {n_tickers:,} unique tickers | "
          f"Years: {start_year}–{end_year}")

    return df


def load_by_year_range(
    start_year: int = 2000,
    end_year: int = 2026,
    capitalize: bool = True,
) -> pd.DataFrame:
    """
    Load data from individual yearly Parquet files and concatenate.

    Parameters
    ----------
    start_year, end_year : int
        Year range to load (inclusive).
    capitalize : bool
        If True, return capitalized column names.

    Returns
    -------
    pd.DataFrame
    """
    frames = []
    for year in range(start_year, end_year + 1):
        fpath = os.path.join(BY_YEAR_DIR, f"russell1000_{year}.parquet")
        if os.path.exists(fpath):
            df_year = pd.read_parquet(fpath)
            frames.append(df_year)
        else:
            print(f"[Loader] Warning: {fpath} not found, skipping year {year}")

    if not frames:
        raise FileNotFoundError(
            f"No parquet files found in {BY_YEAR_DIR} for years {start_year}–{end_year}"
        )

    combined = pd.concat(frames, ignore_index=True)
    if capitalize:
        combined = _standardize_schema(combined)

    print(f"[Loader] Loaded {len(frames)} yearly files | "
          f"{len(combined):,} total rows | "
          f"{combined['Ticker' if capitalize else 'ticker'].nunique()} tickers")

    return combined


def load_single_year(
    year: int,
    capitalize: bool = True,
) -> pd.DataFrame:
    """
    Load data for a single year from the yearly Parquet file.

    Parameters
    ----------
    year : int
        The year to load.
    capitalize : bool
        If True, return capitalized column names.

    Returns
    -------
    pd.DataFrame
    """
    fpath = os.path.join(BY_YEAR_DIR, f"russell1000_{year}.parquet")
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"File not found: {fpath}")

    df = pd.read_parquet(fpath)
    if capitalize:
        df = _standardize_schema(df)

    return df


def load_ticker_history(
    ticker: str,
    start_year: int = 2000,
    end_year: int = 2026,
) -> Optional[pd.DataFrame]:
    """
    Load OHLCV history for a single ticker across multiple years.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. 'AAPL').
    start_year, end_year : int
        Year range (inclusive).

    Returns
    -------
    pd.DataFrame or None
        Single-ticker DataFrame with columns [Date, Open, High, Low, Close, Adj Close, Volume].
    """
    df = load_full_panel(start_year, end_year, capitalize=True)
    ticker_df = df[df["Ticker"] == ticker.upper()].copy()

    if ticker_df.empty:
        return None

    ticker_df = ticker_df.set_index("Date").sort_index()
    return ticker_df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]


def get_available_tickers(year: Optional[int] = None) -> List[str]:
    """
    Get list of available tickers, optionally filtered by year.

    Parameters
    ----------
    year : int, optional
        If specified, return tickers available in that year only.

    Returns
    -------
    List[str]
        Sorted list of ticker symbols.
    """
    if year is not None:
        df = load_single_year(year, capitalize=True)
        return sorted(df["Ticker"].unique().tolist())
    else:
        df = load_full_panel(capitalize=True)
        return sorted(df["Ticker"].unique().tolist())


def get_data_summary() -> pd.DataFrame:
    """
    Return a summary DataFrame with per-year statistics.

    Returns
    -------
    pd.DataFrame
        Columns: year, tickers, rows, date_min, date_max
    """
    stats = []
    for year in range(2000, 2027):
        fpath = os.path.join(BY_YEAR_DIR, f"russell1000_{year}.parquet")
        if os.path.exists(fpath):
            df = pd.read_parquet(fpath, columns=["date", "ticker"])
            if "date" not in df.columns and "time" in df.columns:
                df = df.rename(columns={"time": "date"})
            stats.append({
                "year": year,
                "tickers": df["ticker"].nunique(),
                "rows": len(df),
                "date_min": pd.to_datetime(df["date"]).min().strftime("%Y-%m-%d"),
                "date_max": pd.to_datetime(df["date"]).max().strftime("%Y-%m-%d"),
            })
    return pd.DataFrame(stats)
