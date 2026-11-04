"""
Test 4: Kiểm thử Danh tính Chứng khoán & Sự kiện Đổi Ticker (Security Identity & Ticker Changes)
================================================================================================
Mục tiêu:
1. Nhận diện các cổ phiếu có sự thay đổi Ticker Symbol trong lịch sử (ví dụ: FB -> META, ANTM -> ELV, CBS -> PARA).
2. Kiểm tra xem sự thay đổi ticker có tạo ra khe hở (Gap) hoặc làm biến mất cổ phiếu không.
3. Kiểm tra ánh xạ giữa Ticker gốc (Russell Ticker) vs QC Candidate / QC Symbol trong các file Audit.
4. Thống kê danh sách các trường hợp đổi ticker tiêu biểu trong giai đoạn 2000-2026.
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
AUDIT_DIR = "data/processed/audit/by_year"

# Danh sách một số ca đổi ticker nổi tiếng trên thị trường Mỹ 2000-2026
KNOWN_TICKER_CHANGES = [
    ("FB", "META", 2022, "Meta Platforms (ex-Facebook)"),
    ("GOOG", "GOOGL", 2014, "Alphabet Class A / C split"),
    ("ANTM", "ELV", 2022, "Elevance Health (ex-Anthem)"),
    ("CBS", "PARA", 2022, "Paramount Global (ex-CBS/Viacom)"),
    ("LB", "BBWI", 2021, "Bath & Body Works (ex-L Brands)"),
    ("BIF", "KMI", 2014, "Kinder Morgan"),
    ("MWW", "TRN", 2018, "Trinity Industries"),
    ("KFT", "MDLZ", 2012, "Mondelez (ex-Kraft Foods)"),
    ("DTV", "T", 2015, "DirecTV acquired by AT&T"),
]

def run_test4_security_identity():
    years = list(range(2000, 2027))
    universe_by_year = {}

    for year in years:
        filepath = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                universe_by_year[year] = set(json.load(f))

    # 1. Inspect Known Ticker Changes in Universe Data
    change_audit_results = []
    for old_t, new_t, change_yr, company_name in KNOWN_TICKER_CHANGES:
        old_last_seen = max([y for y in years if old_t in universe_by_year.get(y, set())], default=None)
        new_first_seen = min([y for y in years if new_t in universe_by_year.get(y, set())], default=None)
        
        has_transition = (old_last_seen is not None and new_first_seen is not None and abs(new_first_seen - old_last_seen) <= 2)

        change_audit_results.append({
            'company': company_name,
            'old_ticker': old_t,
            'new_ticker': new_t,
            'expected_year': change_yr,
            'old_last_seen': old_last_seen if old_last_seen else "Không có",
            'new_first_seen': new_first_seen if new_first_seen else "Không có",
            'status': '✅ Khớp chuyển giao' if has_transition else '⚠️ Cần kiểm tra'
        })

    df_known_changes = pd.DataFrame(change_audit_results)

    # 2. Inspect Audit Mapping (Russell Ticker vs QC Symbol mapping)
    audit_mapping_stats = []
    total_symbol_discrepancies = 0

    for year in years:
        audit_file = os.path.join(AUDIT_DIR, f"audit_{year}.csv")
        if os.path.exists(audit_file):
            df_audit = pd.read_csv(audit_file)
            
            # Check where russell_ticker != qc_symbol
            mismatched = df_audit[df_audit['russell_ticker'] != df_audit['qc_symbol']]
            mismatch_cnt = len(mismatched)
            total_symbol_discrepancies += mismatch_cnt

            audit_mapping_stats.append({
                'year': year,
                'total_tickers': len(df_audit),
                'mismatched_symbols_cnt': mismatch_cnt,
                'sample_mismatch': ", ".join([f"{r.russell_ticker}->{r.qc_symbol}" for _, r in mismatched.head(3).iterrows()]) if mismatch_cnt > 0 else "-"
            })

    df_audit_stats = pd.DataFrame(audit_mapping_stats)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 4: KIỂM THỬ DANH TÍNH CHỨNG KHOÁN & SỰ KIỆN ĐỔI TICKER")
    print("==================================================================================")
    print("\n--- 1. KIỂM TRA CÁC CA ĐỔI TICKER TIÊU BIỂU TRÊN UNIVERSE DATA ---")
    print(df_known_changes.to_string(index=False))

    print("\n--- 2. TỔNG HỢP ÁNH XẠ TICKER UNIVERSE VS QC SYMBOL QUA CÁC NĂM ---")
    print(df_audit_stats.to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP KẾT QUẢ TEST 4:")
    print(f" • Số lượt ticker có sự sai biệt giữa Ticker gốc & QC Symbol mapping: {total_symbol_discrepancies:,} lượt")
    print(f" • Nhận xét: QuantConnect Security Master sử dụng hệ thống Symbol Map Lịch sử (Ticker Map History)")
    print(f"   giúp nối liền lịch sử giá ngay cả khi cổ phiếu thay đổi Ticker Symbol.")
    print("----------------------------------------------------------------------------------\n")

    return df_known_changes, df_audit_stats

if __name__ == "__main__":
    run_test4_security_identity()
