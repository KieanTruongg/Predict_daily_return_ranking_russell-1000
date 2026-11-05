"""
Test M1: Kiểm thử Cấu trúc Dữ liệu OHLCV (Market Data Structure Test)
===================================================================
Mục tiêu:
1. Schema & Columns: Xác nhận các file Parquet chứa đúng các cột required: date, ticker, open, high, low, close, volume.
2. Duplicate (Date, Ticker): Đảm bảo không có 2 dòng giá trùng nhau cho cùng một mã cổ phiếu trong cùng 1 ngày giao dịch (Duplicate = 0).
3. Null / NaN / Inf: Đảm bảo 0% giá trị thiếu trong các cột OHLCV.
4. Logic Tài chính OHLCV:
   - Price <= 0 violation (Giá âm hoặc bằng 0).
   - High < Low violation (Giá đỉnh thấp hơn giá đáy).
   - Open/Close range out-of-bounds (Open hoặc Close nằm ngoài khoảng [Low, High]).
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

PARQUET_DIR = "data/processed/by_year"

def run_test_m1_ohlcv_structure():
    years = list(range(2000, 2027))
    summary_results = []

    total_rows = 0
    total_duplicates = 0
    total_nulls = 0
    total_price_le_zero = 0
    total_high_lt_low = 0
    total_open_oob = 0
    total_close_oob = 0

    for yr in years:
        fp = os.path.join(PARQUET_DIR, f"russell1000_{yr}.parquet")
        if not os.path.exists(fp):
            print(f"[WARN] File không tồn tại: {fp}")
            continue

        df = pd.read_parquet(fp)
        num_rows = len(df)
        total_rows += num_rows

        # 1. Columns check
        expected_cols = {'date', 'ticker', 'open', 'high', 'low', 'close', 'volume'}
        actual_cols = set(df.columns)
        has_cols = expected_cols.issubset(actual_cols)

        # 2. Duplicate (Date, Ticker) check
        dup_cnt = df.duplicated(subset=['date', 'ticker']).sum()
        total_duplicates += dup_cnt

        # 3. Null / NaN check
        null_cnt = df[list(expected_cols)].isna().sum().sum()
        total_nulls += null_cnt

        # 4. Financial Logic checks
        # Price <= 0
        price_le_zero = ((df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)).sum()
        total_price_le_zero += price_le_zero

        # High < Low
        high_lt_low = (df['high'] < df['low']).sum()
        total_high_lt_low += high_lt_low

        # Open out of bounds [low, high]
        open_oob = ((df['open'] < df['low']) | (df['open'] > df['high'])).sum()
        total_open_oob += open_oob

        # Close out of bounds [low, high]
        close_oob = ((df['close'] < df['low']) | (df['close'] > df['high'])).sum()
        total_close_oob += close_oob

        summary_results.append({
            'year': yr,
            'rows': num_rows,
            'unique_tickers': df['ticker'].nunique(),
            'has_all_cols': '✅' if has_cols else '❌',
            'duplicates': dup_cnt,
            'nulls': null_cnt,
            'price_le_zero': price_le_zero,
            'high_lt_low': high_lt_low,
            'open_oob': open_oob,
            'close_oob': close_oob
        })

    df_res = pd.DataFrame(summary_results)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST M1: KIỂM THỬ CẤU TRÚC & LOGIC GIÁ CỦA MARKET DATA OHLCV (2000-2026)")
    print("==================================================================================")
    print(df_res.to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP TOÀN BỘ 27 NĂM MARKET DATA OHLCV:")
    print(f" • Tổng số dòng giá (OHLCV Bars) quét : {total_rows:,} dòng")
    print(f" • Trùng lặp (Date, Ticker) Duplicate : {total_duplicates}")
    print(f" • Giá trị NULL / NaN / Missing       : {total_nulls}")
    print(f" • Vi phạm giá âm / bằng 0 (Price <= 0): {total_price_le_zero}")
    print(f" • Vi phạm High < Low                 : {total_high_lt_low}")
    print(f" • Vi phạm Open nằm ngoài [Low, High] : {total_open_oob}")
    print(f" • Vi phạm Close nằm ngoài [Low, High]: {total_close_oob}")
    print("----------------------------------------------------------------------------------\n")

    return df_res

if __name__ == "__main__":
    run_test_m1_ohlcv_structure()
