# 03_process_10_batches_to_parquet.py
# Merges the 10 QuantConnect batch ZIP files (russell_market_batch_01_of_10.zip .. batch_10_of_10.zip)
# into a clean, unified, split-adjusted Parquet dataset for Feature Engineering.

import os
import glob
import zipfile
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_BATCH_DIR = BASE_DIR / 'data' / 'raw' / 'market_data'
OUT_DIR = BASE_DIR / 'data' / 'processed' / 'constituents_market_data'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=== Processing 10 QuantConnect Export Batches ===")
    zip_files = sorted(glob.glob(str(RAW_BATCH_DIR / 'russell_market_batch_*.zip')))
    
    if not zip_files:
        print(f"No ZIP files found in {RAW_BATCH_DIR} matching 'russell_market_batch_*.zip'!")
        print("Please download the batch ZIPs from QuantConnect Research and place them in data/raw/market_data/")
        return
        
    print(f"Found {len(zip_files)} batch ZIP files:")
    for z in zip_files:
        print(f" - {os.path.basename(z)} ({os.path.getsize(z):,} bytes)")
        
    yearly_dfs = {}
    total_raw_rows = 0
    audit_statuses = []
    audit_identities = []
    
    for zf_path in zip_files:
        batch_name = os.path.basename(zf_path)
        print(f"\nExtracting and parsing {batch_name}...")
        with zipfile.ZipFile(zf_path, 'r') as z:
            for fname in z.namelist():
                # Process raw OHLCV CSVs
                if fname.startswith('raw/year=') and fname.endswith('.csv'):
                    year = int(fname.split('/')[1].replace('year=', ''))
                    with z.open(fname) as f:
                        df = pd.read_csv(f, keep_default_na=False, na_values=[''])
                        total_raw_rows += len(df)
                        if year not in yearly_dfs:
                            yearly_dfs[year] = []
                        yearly_dfs[year].append(df)
                # Collect audit status
                elif fname.startswith('audit/') and fname.endswith('_status.csv'):
                    with z.open(fname) as f:
                        audit_statuses.append(pd.read_csv(f, keep_default_na=False, na_values=['']))
                # Collect audit identities
                elif fname.startswith('audit/') and fname.endswith('_identity.csv'):
                    with z.open(fname) as f:
                        audit_identities.append(pd.read_csv(f, keep_default_na=False, na_values=['']))
                        
    print("\n" + "="*80)
    print(f"Consolidating by year across all batches (Total raw rows: {total_raw_rows:,})...")
    
    all_year_frames = []
    partition_dir = OUT_DIR / 'by_year'
    partition_dir.mkdir(exist_ok=True)
    
    for year, frames in sorted(yearly_dfs.items()):
        year_df = pd.concat(frames, ignore_index=True)
        # Deduplicate on date and ticker
        year_df = year_df.drop_duplicates(subset=['date', 'original_ticker']).sort_values(['original_ticker', 'date'])
        
        # Save partitioned Parquet
        year_parquet = partition_dir / f"russell_ohlcv_{year}.parquet"
        year_df.to_parquet(year_parquet, index=False, engine='pyarrow', compression='snappy')
        print(f"Year {year}: {len(year_df):>8,} rows | Tickers: {year_df['original_ticker'].nunique():>4} -> {year_parquet.name}")
        all_year_frames.append(year_df)
        
    # Build unified Master Parquet
    master_df = pd.concat(all_year_frames, ignore_index=True)
    master_df['date'] = pd.to_datetime(master_df['date'])
    master_df = master_df.sort_values(['original_ticker', 'date']).reset_index(drop=True)
    
    master_parquet = OUT_DIR / "russell1000_constituents_daily_ohlcv_1998_2026.parquet"
    master_df.to_parquet(master_parquet, index=False, engine='pyarrow', compression='snappy')
    
    # Save unified audit tables
    if audit_statuses:
        master_status = pd.concat(audit_statuses, ignore_index=True)
        master_status.to_csv(OUT_DIR / "master_batch_status.csv", index=False)
    if audit_identities:
        master_identity = pd.concat(audit_identities, ignore_index=True)
        master_identity.to_csv(OUT_DIR / "master_batch_identity.csv", index=False)
        
    print("\n" + "="*80)
    print("=== PIPELINE COMPLETION SUMMARY ===")
    print("="*80)
    print(f"Master Dataset saved to: {master_parquet.name}")
    print(f"Master File Size:        {os.path.getsize(master_parquet) / (1024*1024):.2f} MB")
    print(f"Total Rows:              {len(master_df):,}")
    print(f"Date Range:              {master_df['date'].min().strftime('%Y-%m-%d')} to {master_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"Unique Tickers with Data:{master_df['original_ticker'].nunique():,}")
    print("Columns:", master_df.columns.tolist())
    print("="*80)

if __name__ == '__main__':
    main()
