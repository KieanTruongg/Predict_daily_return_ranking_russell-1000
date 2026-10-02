"""Script 02: Download >= 10 years of daily data from Yahoo Finance and split into In-Sample / Out-Sample."""
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.universe import build_or_load_universe
from src.data.loader import download_universe_batch
from src.data.preprocessor import pivot_panel_to_matrices
from src.data.split import split_and_persist_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download market data from Yahoo Finance.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tickers to download (for fast prototyping)")
    parser.add_argument("--start-date", type=str, default="2013-01-01", help="Start date (>= 10 years)")
    parser.add_argument("--split-date", type=str, default="2024-01-01", help="In-sample / Out-sample boundary date")
    parser.add_argument("--batch-size", type=int, default=40, help="Batch download size")
    args = parser.parse_args()

    print("=" * 60)
    print("STEP 2: DOWNLOADING MARKET DATA & PARTITIONING SAMPLES")
    print(f"Data Source   : Yahoo Finance")
    print(f"History Start : {args.start_date} (>= 10 Years)")
    print(f"Split Boundary: {args.split_date} (>= 2024-01-01 Out-of-Sample LOCKED)")
    print("=" * 60)

    # 1. Load universe
    tickers = build_or_load_universe(min_stocks=500)
    if args.limit is not None and args.limit > 0:
        print(f"[Note] Limiting universe to top {args.limit} stocks for testing.")
        tickers = tickers[:args.limit]

    # 2. Download historical data
    panel_df = download_universe_batch(
        tickers=tickers,
        start_date=args.start_date,
        batch_size=args.batch_size
    )

    # 3. Pivot to aligned 2D matrices
    print("\nPivoting panel into aligned cross-sectional matrices (Date x Ticker)...")
    container = pivot_panel_to_matrices(panel_df, min_trading_days=200)

    # 4. Split and persist
    print("\nSplitting into In-Sample and Out-of-Sample datasets...")
    ins, oos = split_and_persist_data(
        container,
        cutoff_date=args.split_date,
        in_sample_dir=os.path.join("data", "processed", "in_sample"),
        out_sample_dir=os.path.join("data", "processed", "out_sample")
    )

    print("\n[Complete] Data downloaded, aligned, and strictly partitioned.")
