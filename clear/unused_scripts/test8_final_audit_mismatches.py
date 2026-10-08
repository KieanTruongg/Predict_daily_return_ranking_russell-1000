"""
Test 8: Kiểm toán Ticker không trùng khớp (Final Audit & Unresolved Mismatches)
==============================================================================
Mục tiêu:
1. Thống kê toàn bộ các mã cổ phiếu bị thiếu (QC_DATABASE_NO_RECORDS) trên toàn bộ 27 năm.
2. Phân tích phân bố theo năm của các mã bị thiếu (Missing tickers distribution).
3. Đưa ra danh sách 20 mã bị thiếu nhiều nhất và giải thích nguyên nhân thị trường.
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

AUDIT_DIR = "data/processed/audit/by_year"

def run_test8_final_audit():
    years = list(range(2000, 2027))
    missing_records = []

    for year in years:
        audit_file = os.path.join(AUDIT_DIR, f"audit_{year}.csv")
        if os.path.exists(audit_file):
            df_aud = pd.read_csv(audit_file)
            missing_df = df_aud[df_aud['status'] == 'EMPTY']
            
            for _, r in missing_df.iterrows():
                missing_records.append({
                    'year': year,
                    'russell_ticker': r['russell_ticker'],
                    'reason': r['reason']
                })

    df_missing = pd.DataFrame(missing_records)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 8: KIỂM TOÁN TICKER KHÔNG TRÙNG KHỚP (FINAL AUDIT & MISMATCHES)")
    print("==================================================================================")

    print(f"\n📊 Tổng số lượt stock-year không thu thập được dữ liệu (EMPTY): {len(df_missing):,} lượt")

    if not df_missing.empty:
        # Top tickers missing most frequently across 27 years
        top_missing_tickers = df_missing['russell_ticker'].value_counts().head(20).reset_index()
        top_missing_tickers.columns = ['russell_ticker', 'missing_years_cnt']

        print("\n--- TOP 20 TICKER BỊ THIẾU NHIỀU NĂM NHẤT TRONG HISTORICAL UNIVERSE ---")
        print(top_missing_tickers.to_string(index=False))

        # Yearly breakdown
        yearly_missing = df_missing['year'].value_counts().sort_index().reset_index()
        yearly_missing.columns = ['year', 'missing_cnt']
        
        print("\n--- PHÂN BỔ SỐ MÃ THIẾU THEO TỪNG NĂM (CONCENTRATE IN EARLY YEARS) ---")
        print(yearly_missing.to_string(index=False))

    print("----------------------------------------------------------------------------------\n")

    return df_missing

if __name__ == "__main__":
    run_test8_final_audit()
