"""
Test M2: Kiểm thử Phủ Thời gian & Số ngày Giao dịch Market Data (Time Coverage Test)
===================================================================================
Mục tiêu:
1. Thống kê số ngày giao dịch thực tế của thị trường Mỹ (Market Trading Days) theo từng năm (2000-2026).
2. Kiểm tra ngày bắt đầu (First Trading Date) và ngày kết thúc (Last Trading Date) của từng file Parquet năm.
3. Phân tích phân bố số ngày giao dịch per-ticker:
   - Full coverage (>= 240 ngày/năm).
   - Partial coverage (50 đến 239 ngày/năm).
   - Short history (< 50 ngày/năm).
4. Phát hiện các mã cổ phiếu có lịch sử giao dịch cực kỳ ngắn (< 10 ngày).
"""

import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

PARQUET_DIR = "data/processed/by_year"

def run_test_m2_time_coverage():
    years = list(range(2000, 2027))
    yearly_coverage_results = []
    short_history_tickers = []

    total_tickers_scanned = 0

    for yr in years:
        fp = os.path.join(PARQUET_DIR, f"russell1000_{yr}.parquet")
        if not os.path.exists(fp):
            print(f"[WARN] File không tồn tại: {fp}")
            continue

        df = pd.read_parquet(fp, columns=['date', 'ticker'])
        
        # Ensure date format
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])

        unique_dates = sorted(df['date'].unique())
        total_market_days = len(unique_dates)
        min_date = str(unique_dates[0])[:10] if unique_dates else "-"
        max_date = str(unique_dates[-1])[:10] if unique_dates else "-"

        # Group by ticker to count trading days
        days_per_ticker = df.groupby('ticker')['date'].nunique()
        num_tickers = len(days_per_ticker)
        total_tickers_scanned += num_tickers

        full_cov = (days_per_ticker >= 240).sum()
        partial_cov = ((days_per_ticker >= 50) & (days_per_ticker < 240)).sum()
        short_cov = (days_per_ticker < 50).sum()

        # Detect < 10 days tickers
        very_short = days_per_ticker[days_per_ticker < 10]
        for t, d_cnt in very_short.items():
            short_history_tickers.append({
                'year': yr,
                'ticker': t,
                'trading_days': d_cnt
            })

        yearly_coverage_results.append({
            'year': yr,
            'first_date': min_date,
            'last_date': max_date,
            'market_trading_days': total_market_days,
            'unique_tickers': num_tickers,
            'full_cov_ge240': full_cov,
            'partial_cov_50_240': partial_cov,
            'short_cov_lt50': short_cov,
            'avg_days_per_ticker': round(days_per_ticker.mean(), 1)
        })

    df_res = pd.DataFrame(yearly_coverage_results)
    df_short = pd.DataFrame(short_history_tickers)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST M2: KIỂM THỬ PHỦ THỜI GIAN & SỐ NGÀY GIAO DỊCH (2000 - 2026)")
    print("==================================================================================")
    print(df_res[['year', 'first_date', 'last_date', 'market_trading_days', 'unique_tickers', 'full_cov_ge240', 'partial_cov_50_240', 'short_cov_lt50', 'avg_days_per_ticker']].to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP PHÂN BỐ PHỦ THỜI GIAN MARKET DATA (OHLCV):")
    print(f" • Số ngày giao dịch trung bình của thị trường Mỹ / năm : {df_res['market_trading_days'].mean():.1f} ngày (Chuẩn 250-252d)")
    print(f" • Tổng số lượt cổ phiếu có full coverage (>= 240 ngày): {df_res['full_cov_ge240'].sum():,} lượt ({(df_res['full_cov_ge240'].sum()/df_res['unique_tickers'].sum()*100):.1f}%)")
    print(f" • Số lượt cổ phiếu giao dịch 1 phần năm (50-239 ngày) : {df_res['partial_cov_50_240'].sum():,} lượt")
    print(f" • Số lượt cổ phiếu lịch sử ngắn (< 50 ngày)             : {df_res['short_cov_lt50'].sum():,} lượt")
    print(f" • Số lượt cổ phiếu lịch sử cực ngắn (< 10 ngày)        : {len(df_short):,} lượt")
    print("----------------------------------------------------------------------------------\n")

    return df_res, df_short

if __name__ == "__main__":
    run_test_m2_time_coverage()
