"""
Test 5: Kiểm thử Cổ phiếu Hủy niêm yết / M&A (Historical Survivorship Analysis)
================================================================================
Mục tiêu:
1. Phát hiện danh sách các cổ phiếu biến mất vĩnh viễn khỏi Russell 1000 (Delisted / M&A / Phá sản).
2. Kiểm tra trên audit data xem QuantConnect có lưu trữ dữ liệu giá lịch sử cho đến ngày hủy niêm yết hay không.
3. Phân tích tác động của hiện tượng Survivorship Bias đối với việc huấn luyện mô hình ML.
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
AUDIT_DIR = "data/processed/audit/by_year"

# Danh sách các công ty giải thể / thâu tóm / phá sản nổi tiếng
FAMOUS_DELISTED_STOCKS = [
    ("LEH", "Lehman Brothers (Phá sản 2008)"),
    ("MER", "Merrill Lynch (Bị BofA thâu tóm 2008)"),
    ("BSC", "Bear Stearns (Bị JPM thâu tóm 2008)"),
    ("TWTR", "Twitter (Bị Elon Musk mua tư nhân hóa 2022)"),
    ("SUNW", "Sun Microsystems (Bị Oracle thâu tóm 2010)"),
    ("DTV", "DirecTV (Bị AT&T thâu tóm 2015)"),
    ("HCN", "Welltower Inc (Đổi tên/M&A)"),
]

def run_test5_historical_survivorship():
    years = list(range(2000, 2027))
    universe_by_year = {}

    for year in years:
        filepath = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                universe_by_year[year] = set(json.load(f))

    # 1. Tìm các cổ phiếu xuất hiện ở quá khứ nhưng đã biến mất vĩnh viễn (Last seen < 2026)
    all_tickers = set().union(*universe_by_year.values())
    delisted_candidates = []

    for t in all_tickers:
        active_yrs = [y for y in years if t in universe_by_year[y]]
        last_yr = max(active_yrs)
        if last_yr < 2026: # Đã rời khỏi chỉ số và không có mặt ở năm 2026
            delisted_candidates.append({
                'ticker': t,
                'first_year': min(active_yrs),
                'last_year': last_yr,
                'active_years_cnt': len(active_yrs)
            })

    df_delisted = pd.DataFrame(delisted_candidates)

    # 2. Rà soát danh sách các ca tiêu biểu trên audit data
    audit_survivorship_results = []

    for t, company_desc in FAMOUS_DELISTED_STOCKS:
        # Tìm các năm t xuất hiện trong universe
        in_univ_years = [y for y in years if t in universe_by_year.get(y, set())]
        last_univ_yr = max(in_univ_years) if in_univ_years else None

        # Kiểm tra audit record ở năm cuối cùng
        last_audit_status = "Không có"
        trading_days = 0
        if last_univ_yr:
            audit_file = os.path.join(AUDIT_DIR, f"audit_{last_univ_yr}.csv")
            if os.path.exists(audit_file):
                df_aud = pd.read_csv(audit_file)
                row = df_aud[df_aud['russell_ticker'] == t]
                if not row.empty:
                    last_audit_status = row.iloc[0]['status']
                    trading_days = row.iloc[0]['trading_days']

        audit_survivorship_results.append({
            'company': company_desc,
            'ticker': t,
            'in_universe_years': f"{min(in_univ_years)}→{last_univ_yr}" if in_univ_years else "Không",
            'last_year': last_univ_yr if last_univ_yr else "-",
            'audit_status_last_year': last_audit_status,
            'trading_days_last_year': trading_days
        })

    df_famous_surv = pd.DataFrame(audit_survivorship_results)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 5: KIỂM THỬ CỔ PHIẾU HỦY NIÊM YẾT / M&A (HISTORICAL SURVIVORSHIP)")
    print("==================================================================================")
    print("\n--- 1. RÀ SOÁT CÁC CỔ PHIẾU HỦY NIÊM YẾT / THÂU TÓM TIÊU BIỂU ---")
    print(df_famous_surv.to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP VỀ CỔ PHIẾU ĐÃ HỦY NIÊM YẾT / RỜI CHỈ SỐ:")
    print(f" • Tổng số mã rời chỉ số vĩnh viễn trước 2026 : {len(df_delisted):,} mã / 2,884 mã ({(len(df_delisted)/2884*100):.1f}%)")
    print(f" • Số mã rời chỉ số trong giai đoạn 2000 - 2010 : {len(df_delisted[df_delisted['last_year'] <= 2010]):,} mã")
    print(f" • Số mã rời chỉ số trong giai đoạn 2011 - 2025 : {len(df_delisted[df_delisted['last_year'] > 2010]):,} mã")
    print("----------------------------------------------------------------------------------\n")

    return df_famous_surv, df_delisted

if __name__ == "__main__":
    run_test5_historical_survivorship()
