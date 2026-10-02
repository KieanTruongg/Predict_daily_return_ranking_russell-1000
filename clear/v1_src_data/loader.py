"""Data loader for local Stooq dataset archive and Yahoo Finance fallback."""
import os
import glob
import time
from typing import List, Dict, Optional
import pandas as pd
import yfinance as yf

RAW_DATA_DIR = os.path.join("data", "raw", "market_data")
STOOQ_US_DIR = os.path.join(RAW_DATA_DIR, "data", "daily", "us")


def build_stooq_file_index(stooq_dir: str = STOOQ_US_DIR) -> Dict[str, str]:
    """
    Scans local Stooq extracted directory and maps ticker symbol (lower) -> file path.
    """
    if not os.path.exists(stooq_dir):
        return {}

    txt_files = glob.glob(os.path.join(stooq_dir, "**", "*.txt"), recursive=True)
    index_map = {}
    for f in txt_files:
        base = os.path.basename(f).lower()
        if base.endswith(".us.txt"):
            symbol = base[:-7]
            index_map[symbol] = f
            # Also add cleaned version without hyphen/dot
            index_map[symbol.replace("-", "")] = f
            index_map[symbol.replace(".", "")] = f
    return index_map


def load_stooq_ticker_history(
    ticker: str,
    stooq_index: Dict[str, str],
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Loads daily OHLCV from local Stooq text file for a single ticker.
    """
    clean_t = ticker.lower().strip()
    fpath = stooq_index.get(clean_t) or stooq_index.get(clean_t.replace("-", "")) or stooq_index.get(clean_t.replace(".", ""))

    if not fpath or not os.path.exists(fpath):
        return None

    try:
        df = pd.read_csv(fpath)
        if df.empty or "<DATE>" not in df.columns:
            return None

        df["Date"] = pd.to_datetime(df["<DATE>"].astype(str), format="%Y%m%d")
        df = df.rename(columns={
            "<OPEN>": "Open",
            "<HIGH>": "High",
            "<LOW>": "Low",
            "<CLOSE>": "Close",
            "<VOL>": "Volume"
        })

        df["Adj Close"] = df["Close"]
        df["Ticker"] = ticker.upper()
        df = df.set_index("Date").sort_index()

        ts_start = pd.to_datetime(start_date)
        df = df[df.index >= ts_start]

        if end_date:
            ts_end = pd.to_datetime(end_date)
            df = df[df.index <= ts_end]

        if len(df) > 30:
            return df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Ticker"]]
    except Exception as e:
        pass

    return None


def download_ticker_history(
    ticker: str,
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None,
    cache_dir: str = RAW_DATA_DIR,
    force_reload: bool = False
) -> Optional[pd.DataFrame]:
    """
    Downloads historical daily OHLCV for a single ticker with local Parquet caching.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{ticker}.parquet")

    if not force_reload and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    try:
        df = yf.download(
            tickers=ticker,
            start=start_date,
            end=end_date,
            auto_adjust=False,
            progress=False
        )
        if df is not None and not df.empty and len(df) > 30:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)
            df.index.name = "Date"
            df["Ticker"] = ticker
            df.to_parquet(cache_file)
            return df
    except Exception as e:
        pass

    return None


def download_universe_batch(
    tickers: List[str],
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None,
    batch_size: int = 50,
    cache_dir: str = RAW_DATA_DIR,
    sleep_between_batches: float = 0.0
) -> pd.DataFrame:
    """
    Loads historical data from local Stooq dataset archive (if available) or Yahoo Finance fallback.
    Returns a combined panel DataFrame.
    """
    os.makedirs(cache_dir, exist_ok=True)
    stooq_index = build_stooq_file_index()
    using_stooq = len(stooq_index) > 0

    if using_stooq:
        print(f"[Loader] Detected local Stooq dataset archive with {len(stooq_index)} symbols.")
        print(f"[Loader] Loading OHLCV history for {len(tickers)} Russell 1000 tickers (from {start_date})...")

    dfs = []
    loaded_count = 0

    for idx, ticker in enumerate(tickers):
        df = None
        if using_stooq:
            df = load_stooq_ticker_history(ticker, stooq_index, start_date=start_date, end_date=end_date)

        if df is None and not using_stooq:
            df = download_ticker_history(ticker, start_date=start_date, end_date=end_date, cache_dir=cache_dir)

        if df is not None and not df.empty:
            dfs.append(df)
            loaded_count += 1

        if (idx + 1) % 500 == 0 or (idx + 1) == len(tickers):
            print(f"  Processed {idx + 1}/{len(tickers)} tickers (Successfully loaded: {loaded_count})...")

    if not dfs:
        raise ValueError("No stock data could be loaded. Check dataset files or internet connection.")

    combined = pd.concat(dfs, axis=0)
    print(f"\n[Complete] Data load successful! Loaded {loaded_count} tickers, Total records: {len(combined):,}")
    return combined
