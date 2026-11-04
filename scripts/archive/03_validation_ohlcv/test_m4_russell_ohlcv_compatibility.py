"""
Test M4: Kiểm thử Độ Tương thích Russell 1000 PIT x Market Data OHLCV (Compatibility Test)
========================================================================================
Mục tiêu:
1. Thực hiện INNER JOIN giữa Russell 1000 Universe PIT Ticker list và Market Data OHLCV Ticker list cho toàn bộ 27 năm.
2. Thống kê số lượng: Russell Count, Extracted OHLCV Count, Intersection, Missing Tickers Count.
3. Giải phẫu chi tiết lý do của các mã bị thiếu (Missing Breakdown):
   - QC Database không có dữ liệu lịch sử (QC_DATABASE_NO_RECORDS).
   - Không đủ số ngày giao dịch tối thiểu (EXCLUDED_FEW_DAYS).
   - Lỗi mapping ký tự ticker format.
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
PARQUET_DIR = "data/processed/by_year"
AUDIT_DIR = "data/processed/audit/by_year"

def run_test_m4_compatibility():
    years = list(range(2000, 2027))
    compatibility_results = []
    missing_breakdown_detail = {}

    for yr in years:
        # 1. Load Russell Universe JSON
        univ_fp = os.path.join(UNIVERSE_DIR, f"russell1000_{yr}.json")
        univ_set = set()
        if os.path.exists(univ_fp):
            with open(univ_fp, 'r', encoding='utf-8') as f:
                univ_set = set(json.load(f))
        
        # 2. Load OHLCV Parquet Tickers
        pq_fp = os.path.join(PARQUET_DIR, f"russell1000_{yr}.parquet")
        pq_set = set()
        if os.path.exists(pq_fp):
            df_pq = pd.read_parquet(pq_fp, columns=['ticker'])
            pq_set = set(df_pq['ticker'].unique())

        # 3. Load Audit CSV to breakdown missing reasons
        audit_fp = os.path.join(AUDIT_DIR, f"audit_{yr}.csv")
        missing_reasons_year = {}
        if os.path.exists(audit_fp):
            df_aud = pd.read_csv(audit_fp)
            missing_df = df_aud[df_aud['status'] != 'SUCCESS']
            for _, r in missing_df.iterrows():
                rs = str(r.get('reason', 'UNKNOWN'))
                missing_reasons_year[rs] = missing_reasons_year.get(rs, 0) + 1
                missing_breakdown_detail[rs] = missing_breakdown_detail.get(rs, 0) + 1

        intersection = univ_set & pq_set
        missing = univ_set - pq_set
        extra = pq_set - univ_set

        match_rate = (len(intersection) / len(univ_set) * 100) if len(univ_set) > 0 else 0.0

        compatibility_results.append({
            'year': yr,
            'russell_count': len(univ_set),
            'ohlcv_parquet_count': len(pq_set),
            'intersection': len(intersection),
            'missing_cnt': len(missing),
            'extra_cnt': len(extra),
            'compatibility_rate_pct': round(match_rate, 2),
            'top_missing_reason': max(missing_reasons_year.items(), key=lambda x: x[1])[0] if missing_reasons_year else "-"
        })

    df_res = pd.DataFrame(compatibility_results)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST M4: KIỂM THỬ ĐỘ TƯƠNG THÍCH RUSSELL 1000 PIT x MARKET DATA OHLCV")
    print("==================================================================================")
    print(df_res.to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 PHÂN TÍCH NGUYÊN NHÂN CỤ THỂ CỦA CÁC MÃ BỊ THIẾU (MISSING REASONS BREAKDOWN):")
    for k, v in sorted(missing_breakdown_detail.items(), key=lambda x: x[1], reverse=True):
        print(f" • {k}: {v:,} lượt cổ phiếu")
    print("----------------------------------------------------------------------------------\n")

    return df_res, missing_breakdown_detail

if __name__ == "__main__":
    run_test_m4_compatibility()
