"""
Test 7: Chuẩn hóa Định dạng Ticker (Mapping Format & Delimiter Normalization)
=============================================================================
Mục tiêu:
1. Thống kê toàn bộ các Ticker có ký tự đặc biệt (Dấu gạch ngang '-', dấu chấm '.', khoảng trắng, v.v.).
2. Kiểm tra xem giữa Russell 1000 Universe thô và QuantConnect QC Candidate có sự biến đổi định dạng nào không (ví dụ: BRK-A -> BRK.A hay BRK_A).
3. Đảm bảo quy trình Mapping không làm mất dữ liệu của các mã cổ phiếu đa lớp (Multi-class shares).
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
AUDIT_DIR = "data/processed/audit/by_year"

def run_test7_ticker_format_mapping():
    years = list(range(2000, 2027))
    hyphen_audit_cases = []

    for year in years:
        audit_file = os.path.join(AUDIT_DIR, f"audit_{year}.csv")
        if os.path.exists(audit_file):
            df_aud = pd.read_csv(audit_file)
            
            # Filter tickers containing hyphens '-' or dots '.'
            special_df = df_aud[df_aud['russell_ticker'].str.contains(r'[-.]', regex=True, na=False)]
            
            for _, row in special_df.iterrows():
                hyphen_audit_cases.append({
                    'year': year,
                    'russell_ticker': row['russell_ticker'],
                    'qc_candidate': row['qc_candidate'],
                    'qc_symbol': row['qc_symbol'],
                    'status': row['status'],
                    'trading_days': row['trading_days']
                })

    df_special = pd.DataFrame(hyphen_audit_cases)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 7: CHUẨN HÓA ĐỊNH DẠNG TICKER (MAPPING FORMAT & DELIMITERS)")
    print("==================================================================================")
    
    if not df_special.empty:
        unique_special_tickers = df_special['russell_ticker'].unique()
        print(f"\n--- Danh sách {len(unique_special_tickers)} Ticker có ký tự đặc biệt (- / .) ---")
        print(", ".join(sorted(unique_special_tickers)))

        print("\n--- Mẫu ánh xạ giữa Russell Ticker vs QC Candidate vs QC Symbol ---")
        print(df_special[['year', 'russell_ticker', 'qc_candidate', 'qc_symbol', 'status', 'trading_days']].head(15).to_string(index=False))

        success_special = len(df_special[df_special['status'] == 'SUCCESS'])
        print(f"\n📊 Tổng số lượt ticker đặc biệt: {len(df_special)} lượt")
        print(f"   • Số lượt thu thập SUCCESS: {success_special} / {len(df_special)} ({(success_special/len(df_special)*100):.1f}%)")
    else:
        print("\nKhông tìm thấy ticker đặc biệt nào.")

    print("----------------------------------------------------------------------------------\n")

    return df_special

if __name__ == "__main__":
    run_test7_ticker_format_mapping()
