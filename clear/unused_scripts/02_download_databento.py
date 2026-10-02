"""
Script: 02_download_databento.py
Description: Download institutional-grade, Survivorship-Bias-Free US Equities Daily OHLCV Bars
             from Databento (EQUS.SUMMARY dataset) covering 2000-2024.
"""

import os
import sys
import json
import argparse
import pandas as pd
import numpy as np

try:
    import databento as db
except ImportError:
    print("[Error] databento library not installed. Run 'pip install databento'.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Download US Equities daily data from Databento")
    parser.add_argument("--api-key", type=str, default=os.getenv("DATABENTO_API_KEY"), help="Databento API Key")
    parser.add_argument("--start-date", type=str, default="2000-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2024-01-01", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    api_key = args.api_key
    if not api_key:
        print("="*75)
        print("[ACTION REQUIRED] DATABENTO API KEY NEEDED")
        print("="*75)
        print("1. Sign up at https://databento.com/ using your .edu email.")
        print("2. Get your FREE $125 credit API key from your portal.")
        print("3. Run this script passing your key:")
        print("   python scripts/02_download_databento.py --api-key YOUR_API_KEY")
        print("="*75)
        return

    print("="*75)
    print("STEP 2 (INSTITUTIONAL): DOWNLOADING SURVIVORSHIP-BIAS-FREE DATA VIA DATABENTO")
    print(f"Dataset      : EQUS.SUMMARY (Daily OHLCV Bars)")
    print(f"Start Date   : {args.start_date}")
    print(f"End Date     : {args.end_date}")
    print("="*75)

    # Load PIT master ticker list
    universe_path = 'data/raw/universe/russell1000_constituents.csv'
    if not os.path.exists(universe_path):
        print(f"[Error] Universe file not found at {universe_path}. Run 01_build_universe.py first.")
        return

    universe_df = pd.read_csv(universe_path)
    tickers = sorted(universe_df['ticker'].unique().tolist())
    print(f"[Universe] Loaded {len(tickers):,} unique historical tickers from Russell 1000 PIT archive.")

    client = db.Historical(key=api_key)

    # Fetch daily OHLCV bars
    print(f"[Databento] Requesting daily OHLCV bars from {args.start_date} to {args.end_date}...")
    try:
        data = client.timeseries.get_range(
            dataset="EQUS.SUMMARY",
            symbols=tickers,
            schema="ohlcv-1d",
            start=args.start_date,
            end=args.end_date,
            stype_in="raw_symbol",
        )
        
        df = data.to_df()
        print(f"[Success] Downloaded {len(df):,} total records from Databento.")

        # Pivot into cross-sectional matrices
        print("Pivoting data into aligned Cross-Sectional matrices...")
        close_df = df.pivot(index='ts_event', columns='symbol', values='close')
        open_df = df.pivot(index='ts_event', columns='symbol', values='open')
        high_df = df.pivot(index='ts_event', columns='symbol', values='high')
        low_df = df.pivot(index='ts_event', columns='symbol', values='low')
        vol_df = df.pivot(index='ts_event', columns='symbol', values='volume')

        close_df.index = pd.to_datetime(close_df.index).tz_localize(None)
        returns_df = close_df.pct_change()
        forward_returns = close_df.pct_change().shift(-1)

        out_dir = "data/processed/in_sample"
        os.makedirs(out_dir, exist_ok=True)

        close_df.to_parquet(os.path.join(out_dir, "close.parquet"))
        open_df.to_parquet(os.path.join(out_dir, "open.parquet"))
        high_df.to_parquet(os.path.join(out_dir, "high.parquet"))
        low_df.to_parquet(os.path.join(out_dir, "low.parquet"))
        vol_df.to_parquet(os.path.join(out_dir, "volume.parquet"))
        returns_df.to_parquet(os.path.join(out_dir, "returns.parquet"))
        forward_returns.to_parquet(os.path.join(out_dir, "forward_returns.parquet"))

        print(f"[Complete] Clean, Survivorship-Bias-Free institutional dataset saved to '{out_dir}'.")

    except Exception as e:
        print(f"[Databento Error] {str(e)}")

if __name__ == "__main__":
    main()
