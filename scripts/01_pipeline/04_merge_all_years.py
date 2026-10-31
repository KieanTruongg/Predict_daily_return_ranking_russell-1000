"""
Script: scripts/01_pipeline/04_merge_all_years.py
Purpose: Merge 27 yearly Parquet files (russell1000_2000..2026.parquet) into a single
         consolidated daily OHLCV file for the entire 2000-2026 period.
         Standardizes column names and validates data integrity after merge.
Output:  data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BY_YEAR_DIR = os.path.join(BASE, "data", "processed", "by_year")
OUT_DIR = os.path.join(BASE, "data", "processed", "daily_ohlcv")
os.makedirs(OUT_DIR, exist_ok=True)

STANDARD_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume", "year"]


def standardize_columns(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Standardize column names to lowercase and ensure consistent schema."""
    df.columns = [c.lower().strip() for c in df.columns]

    # Handle 'time' -> 'date' rename (old schema)
    if "time" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"time": "date"})

    # Ensure date is datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    # Ensure year column
    if "year" not in df.columns:
        df["year"] = year

    # Select and order standard columns
    available = [c for c in STANDARD_COLUMNS if c in df.columns]
    df = df[available]

    return df


def merge_all_years():
    print("=" * 80)
    print("PHASE 1: MERGE 27 YEARLY PARQUET FILES → CONSOLIDATED DAILY OHLCV")
    print(f"Source : {BY_YEAR_DIR}")
    print(f"Output : {OUT_DIR}")
    print("=" * 80)

    start_time = time.time()

    # Find all yearly parquet files
    parquet_files = sorted([
        f for f in os.listdir(BY_YEAR_DIR)
        if f.startswith("russell1000_") and f.endswith(".parquet")
    ])

    if not parquet_files:
        print(f"⚠️ No parquet files found in {BY_YEAR_DIR}")
        return

    print(f"\n📂 Found {len(parquet_files)} yearly files to merge\n")

    all_frames = []
    stats = []

    for pf in parquet_files:
        year_str = pf.replace("russell1000_", "").replace(".parquet", "")
        year = int(year_str)
        fpath = os.path.join(BY_YEAR_DIR, pf)

        df = pd.read_parquet(fpath)
        df = standardize_columns(df, year)

        n_tickers = df["ticker"].nunique()
        n_rows = len(df)
        date_min = df["date"].min().strftime("%Y-%m-%d") if "date" in df.columns else "N/A"
        date_max = df["date"].max().strftime("%Y-%m-%d") if "date" in df.columns else "N/A"

        stats.append({
            "year": year,
            "tickers": n_tickers,
            "rows": n_rows,
            "date_min": date_min,
            "date_max": date_max,
        })

        all_frames.append(df)
        print(f"  ✅ {year}: {n_tickers:>5} tickers | {n_rows:>8,} rows | {date_min} → {date_max}")

    # Concatenate all years
    print(f"\n🔗 Merging {len(all_frames)} DataFrames...")
    combined = pd.concat(all_frames, ignore_index=True)

    # Sort by date, then ticker
    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)

    # Export v5 lấy cửa sổ recon(Y) - lookback → recon(Y+1), nên các năm chồng lấn nhau:
    # cùng (date, ticker) có thể xuất hiện ở nhiều file năm → giữ 1 dòng (pivot yêu cầu unique).
    n_before = len(combined)
    combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last").reset_index(drop=True)
    print(f"  Dedup (date, ticker): bỏ {n_before - len(combined):,} dòng trùng do cửa sổ chồng lấn")

    # Final validation
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    print(f"  Total rows          : {len(combined):>12,}")
    print(f"  Unique tickers      : {combined['ticker'].nunique():>12,}")
    print(f"  Years covered       : {combined['year'].nunique():>12} ({combined['year'].min()} → {combined['year'].max()})")
    print(f"  Date range          : {combined['date'].min().strftime('%Y-%m-%d')} → {combined['date'].max().strftime('%Y-%m-%d')}")
    print(f"  Columns             : {list(combined.columns)}")
    print(f"  Dtypes              :")
    for col in combined.columns:
        print(f"    {col:<12} : {combined[col].dtype}")

    # Check for nulls
    null_counts = combined.isnull().sum()
    has_nulls = null_counts.sum() > 0
    print(f"\n  Null values         : {'⚠️ YES' if has_nulls else '✅ NONE'}")
    if has_nulls:
        for col, cnt in null_counts.items():
            if cnt > 0:
                print(f"    {col}: {cnt:,} nulls")

    # Check for negative prices
    for price_col in ["open", "high", "low", "close"]:
        neg_count = (combined[price_col] <= 0).sum()
        if neg_count > 0:
            print(f"  ⚠️ {price_col} <= 0 : {neg_count:,} rows")

    # Save
    out_path = os.path.join(OUT_DIR, "russell1000_daily_2000_2026.parquet")
    combined.to_parquet(out_path, index=False, compression="snappy")

    file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
    elapsed = time.time() - start_time

    print(f"\n{'=' * 80}")
    print(f"✅ SAVED: {out_path}")
    print(f"   File size: {file_size_mb:.1f} MB | Time: {elapsed:.1f}s")
    print(f"{'=' * 80}")

    # Print stats table
    df_stats = pd.DataFrame(stats)
    print(f"\n📋 Per-Year Summary:")
    print(df_stats.to_string(index=False))

    return combined


if __name__ == "__main__":
    merge_all_years()
