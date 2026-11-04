# scripts/audit_step1_warehouse_and_pit_coverage.py
# Dynamic, empirical verification of the Raw Market Data Warehouse and
# daily Point-In-Time (PIT) membership coverage per annual Russell 1000 reconstitution window.
# Rule: Snapshot Year Y applies strictly from YYYY-07-01 to (YYYY+1)-06-30.

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

BASE = Path(r"D:\A_Learning\HK1_2026-2027\CO3101 - Đồ án tổng hợp - ttnt\Predict_daily_return_rankings")
PARQUET_PATH = BASE / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_1998_2026.parquet"
PIT_JSON_PATH = BASE / "data" / "raw" / "universe" / "russell1000_pit_by_year.json"
TABLES_DIR = BASE / "docs" / "Data report" / "market_data_audit" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("="*80)
    print("STEP 1: DYNAMIC VERIFICATION OF RAW MARKET DATA WAREHOUSE")
    print("="*80)
    
    print(f"Loading master dataset from: {PARQUET_PATH.name}...")
    df = pd.read_parquet(PARQUET_PATH)
    total_rows = len(df)
    print(f"Total Rows: {total_rows:,} | Total Columns: {df.shape[1]}")
    
    # 1. Dynamic Null Checks
    print("\n--- 1. Live Null Checks Across All Columns ---")
    null_counts = df.isnull().sum()
    null_df = pd.DataFrame({'column': null_counts.index, 'null_count': null_counts.values, 'null_pct': (null_counts.values / total_rows * 100).round(4)})
    print(null_df.to_string(index=False))
    
    # 2. Dynamic Price Sanity Checks
    print("\n--- 2. Live Price Sanity Constraints ---")
    sanity_checks = {
        'high_lt_low': (df['high'] < df['low']).sum(),
        'high_lt_open': (df['high'] < df['open']).sum(),
        'high_lt_close': (df['high'] < df['close']).sum(),
        'low_gt_open': (df['low'] > df['open']).sum(),
        'low_gt_close': (df['low'] > df['close']).sum(),
        'open_le_zero': (df['open'] <= 0).sum(),
        'close_le_zero': (df['close'] <= 0).sum(),
        'volume_lt_zero': (df['volume'] < 0).sum()
    }
    sanity_df = pd.DataFrame(list(sanity_checks.items()), columns=['constraint', 'violations'])
    print(sanity_df.to_string(index=False))
    
    # 3. Duplicate checks
    print("\n--- 3. Primary Key Uniqueness ---")
    dup_ticker_date = df.duplicated(subset=['date', 'original_ticker']).sum()
    dup_sid_date = df.duplicated(subset=['date', 'sid']).sum()
    print(f"Duplicates on (date, original_ticker): {dup_ticker_date}")
    print(f"Duplicates on (date, sid):            {dup_sid_date}")
    
    # 4. Temporal Coverage
    min_date = df['date'].min().strftime('%Y-%m-%d')
    max_date = df['date'].max().strftime('%Y-%m-%d')
    trading_days_all = df['date'].nunique()
    unique_tickers_all = df['original_ticker'].nunique()
    unique_sids_all = df['sid'].nunique()
    print(f"\nTime span: {min_date} to {max_date} | Total Unique Trading Days: {trading_days_all:,}")
    print(f"Unique Original Tickers with Data: {unique_tickers_all:,} | Unique SIDs: {unique_sids_all:,}")

    # Save warehouse sanity check table
    sanity_output = pd.concat([
        null_df.assign(category='null_check').rename(columns={'column': 'test_item', 'null_count': 'violation_count'}),
        sanity_df.assign(category='price_sanity', null_pct=0.0).rename(columns={'constraint': 'test_item', 'violations': 'violation_count'})
    ], ignore_index=True)
    sanity_output.to_csv(TABLES_DIR / "warehouse_sanity_check.csv", index=False)
    print("Saved: warehouse_sanity_check.csv")

    print("\n" + "="*80)
    print("STEP 2: POINT-IN-TIME (PIT) DAILY MEMBERSHIP COVERAGE MEASUREMENT")
    print("Rule: Snapshot Year Y applies strictly from YYYY-07-01 to (YYYY+1)-06-30")
    print("="*80)
    
    with open(PIT_JSON_PATH, encoding='utf-8') as f:
        pit_universe = json.load(f)
        
    # Build dictionary of market trading days and available tickers per day
    # Pre-index OHLCV for fast day-by-day lookup
    print("Building day-by-day market availability index...")
    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    market_day_tickers = df.groupby('date_str')['original_ticker'].apply(set).to_dict()
    all_market_dates = sorted(market_day_tickers.keys())
    
    period_summaries = []
    zero_bar_records = []
    
    total_expected_stock_days = 0
    total_actual_stock_days = 0
    
    snapshot_years = sorted([int(y) for y in pit_universe.keys()])
    
    for y in snapshot_years:
        constituents = set(t.strip().upper() for t in pit_universe[str(y)])
        num_constituents = len(constituents)
        
        # Define membership window
        p_start = f"{y}-07-01"
        if y < max(snapshot_years):
            p_end = f"{y+1}-06-30"
        else:
            # For 2026 snapshot, window runs from 2026-07-01 to latest available date
            p_end = max_date
            
        # Get market trading days within this window
        trading_days_in_period = [d for d in all_market_dates if p_start <= d <= p_end]
        num_days = len(trading_days_in_period)
        
        if num_days == 0:
            print(f"Warning: No market trading days found for period {p_start} to {p_end}")
            continue
            
        # Track daily coverage
        daily_active_counts = []
        constituent_bar_counts = {t: 0 for t in constituents}
        
        for d in trading_days_in_period:
            active_today = market_day_tickers.get(d, set())
            # Constituents active today
            covered_today = constituents.intersection(active_today)
            daily_active_counts.append(len(covered_today))
            for t in covered_today:
                constituent_bar_counts[t] += 1
                
        # Period stats
        expected_stock_days = num_constituents * num_days
        actual_stock_days = sum(daily_active_counts)
        period_coverage_pct = (actual_stock_days / expected_stock_days) * 100
        
        total_expected_stock_days += expected_stock_days
        total_actual_stock_days += actual_stock_days
        
        # Categorize constituent presence
        full_coverage = sum(1 for c, bars in constituent_bar_counts.items() if bars == num_days)
        partial_coverage = sum(1 for c, bars in constituent_bar_counts.items() if 0 < bars < num_days)
        zero_coverage = sum(1 for c, bars in constituent_bar_counts.items() if bars == 0)
        
        # Record zero-bar constituents
        for c, bars in constituent_bar_counts.items():
            if bars == 0:
                zero_bar_records.append({
                    'snapshot_year': y,
                    'period_start': p_start,
                    'period_end': p_end,
                    'ticker': c,
                    'reason': 'ZERO_BARS_IN_MEMBERSHIP_WINDOW'
                })
                
        period_summaries.append({
            'snapshot_year': y,
            'period_start': p_start,
            'period_end': p_end,
            'trading_days': num_days,
            'official_constituents': num_constituents,
            'expected_stock_days': expected_stock_days,
            'actual_stock_days': actual_stock_days,
            'daily_coverage_pct': round(period_coverage_pct, 2),
            'avg_active_per_day': round(np.mean(daily_active_counts), 1),
            'min_active_day': min(daily_active_counts),
            'max_active_day': max(daily_active_counts),
            'constituents_full_period': full_coverage,
            'constituents_partial_period': partial_coverage,
            'constituents_zero_bars': zero_coverage
        })
        
    df_period = pd.DataFrame(period_summaries)
    print("\n--- ANNUAL RECONSTITUTION PERIOD COVERAGE (01/07/Y -> 30/06/Y+1) ---")
    cols_to_print = ['snapshot_year', 'period_start', 'period_end', 'trading_days', 'official_constituents', 'avg_active_per_day', 'daily_coverage_pct', 'constituents_zero_bars', 'constituents_partial_period']
    print(df_period[cols_to_print].to_string(index=False))
    
    # Save period summary CSV
    df_period.to_csv(TABLES_DIR / "daily_pit_coverage_by_period.csv", index=False)
    print("\nSaved: daily_pit_coverage_by_period.csv")
    
    # Save zero-bar records CSV
    df_zero = pd.DataFrame(zero_bar_records)
    df_zero.to_csv(TABLES_DIR / "zero_bar_constituents_by_period.csv", index=False)
    print(f"Saved: zero_bar_constituents_by_period.csv ({len(df_zero)} records)")
    
    # Global PIT Daily Coverage
    global_coverage_pct = (total_actual_stock_days / total_expected_stock_days) * 100
    print("\n" + "="*80)
    print("=== GLOBAL POINT-IN-TIME (PIT) DAILY MEMBERSHIP METRICS ===")
    print("="*80)
    print(f"Total Reconstitution Periods Evaluated: {len(df_period)} (2000 to 2026)")
    print(f"Total Expected Constituent-Day Observations: {total_expected_stock_days:,}")
    print(f"Total Actual Constituent-Day Bars with Data: {total_actual_stock_days:,}")
    print(f"TRUE GLOBAL DAILY PIT MEMBERSHIP COVERAGE:   {global_coverage_pct:.2f}%")
    print(f"Average Daily Active Constituents in Index:  {total_actual_stock_days / df_period['trading_days'].sum():.1f} / ~1,000 stocks")
    print("="*80)

if __name__ == '__main__':
    main()
