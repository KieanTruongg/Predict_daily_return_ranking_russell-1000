"""
Script: scripts/01_pipeline/05_build_cross_sectional.py
Purpose: Build cross-sectional Date x Ticker matrices from the consolidated 
         daily OHLCV file and split into In-Sample / Out-of-Sample partitions.

Outputs:
  - data/processed/in_sample/   (8 parquet matrices: open, high, low, close, adj_close, volume, returns, forward_returns)
  - data/processed/out_sample/  (same 8 matrices, LOCKED for final evaluation only)
"""
import os
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add project root to path
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from src.data.loader import load_full_panel
from src.data.preprocessor import pivot_panel_to_matrices
from src.data.split import split_and_persist_data

IN_SAMPLE_DIR = os.path.join(BASE, "data", "processed", "in_sample")
OUT_SAMPLE_DIR = os.path.join(BASE, "data", "processed", "out_sample")
SPLIT_DATE = "2024-01-01"
MIN_TRADING_DAYS = 100  # Minimum days per ticker to be included


def main():
    print("=" * 80)
    print("PHASE 5: BUILD CROSS-SECTIONAL MATRICES & SPLIT IN/OUT-OF-SAMPLE")
    print("=" * 80)
    start_time = time.time()

    # Step 1: Load full panel
    print("\n📥 Step 1: Loading full panel data (2000-2026)...")
    df = load_full_panel(start_year=2000, end_year=2026, capitalize=True)
    print(f"   Loaded: {len(df):,} rows | {df['Ticker'].nunique():,} tickers")

    # Step 2: Pivot to cross-sectional matrices
    print(f"\n🔄 Step 2: Pivoting to Date x Ticker matrices (min_trading_days={MIN_TRADING_DAYS})...")
    container = pivot_panel_to_matrices(df, min_trading_days=MIN_TRADING_DAYS)

    # Step 3: Split and save
    print(f"\n✂️ Step 3: Splitting at {SPLIT_DATE} and saving to disk...")
    in_sample, out_sample = split_and_persist_data(
        container,
        cutoff_date=SPLIT_DATE,
        in_sample_dir=IN_SAMPLE_DIR,
        out_sample_dir=OUT_SAMPLE_DIR,
    )

    # Step 4: Final summary
    elapsed = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"✅ PHASE 5 COMPLETE ({elapsed:.1f}s)")
    print(f"{'=' * 80}")
    print(f"\n📁 Output Directories:")
    print(f"   In-Sample  : {IN_SAMPLE_DIR}")
    print(f"   Out-Sample : {OUT_SAMPLE_DIR}")

    # Print file sizes
    for label, d in [("In-Sample", IN_SAMPLE_DIR), ("Out-Sample", OUT_SAMPLE_DIR)]:
        total_size = 0
        files = []
        for f in sorted(os.listdir(d)):
            fpath = os.path.join(d, f)
            if os.path.isfile(fpath):
                sz = os.path.getsize(fpath) / (1024 * 1024)
                total_size += sz
                files.append((f, sz))
        print(f"\n   {label} ({total_size:.1f} MB total):")
        for fname, sz in files:
            print(f"     {fname:<25} {sz:>8.1f} MB")


if __name__ == "__main__":
    main()
