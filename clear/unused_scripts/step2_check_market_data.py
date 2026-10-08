"""
Bước 2: Kiểm tra Market Data OHLCV so với Russell 1000 Universe
==================================================================
Mục đích: 
1. Thống kê tỷ lệ khớp dữ liệu (Match Rate / Coverage Rate) giữa Universe và Market Data thực tế.
2. Trích xuất chi tiết lý do thất bại (NOT_FOUND, EXCLUDED, partial days...).
3. Vẽ biểu đồ so sánh Universe vs Actual Data và Coverage % qua các năm 2000-2026.
4. Xuất kết quả tổng hợp dạng JSON/print để đưa vào Báo cáo HTML.
"""

import json
import os
import glob
import sys
import pandas as pd
import matplotlib.pyplot as plt
# import seaborn as sns

sys.stdout.reconfigure(encoding='utf-8')

# Thiết lập thư mục
UNIVERSE_DIR = "data/raw/universe/by_year"
AUDIT_DIR = "data/processed/audit/by_year"
PARQUET_DIR = "data/processed/by_year"
FIGURE_DIR = "outputs/figures"
REPORT_DIR = "docs/Data report"

os.makedirs(FIGURE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def analyze_market_data_coverage():
    years = list(range(2000, 2027))
    summary_list = []
    reason_breakdown = {}

    for year in years:
        # 1. Universe count
        univ_file = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
        univ_tickers = []
        if os.path.exists(univ_file):
            with open(univ_file, 'r', encoding='utf-8') as f:
                univ_tickers = json.load(f)
        univ_count = len(univ_tickers)

        # 2. Audit file
        audit_file = os.path.join(AUDIT_DIR, f"audit_{year}.csv")
        success_count = 0
        failed_count = 0

        if os.path.exists(audit_file):
            df_audit = pd.read_csv(audit_file)
            # SUCCESS count
            success_df = df_audit[df_audit['status'] == 'SUCCESS']
            success_count = len(success_df)
            failed_df = df_audit[df_audit['status'] != 'SUCCESS']
            failed_count = len(failed_df)

            # Phân tích lý do
            for _, row in df_audit.iterrows():
                st = str(row.get('status', 'UNKNOWN'))
                rs = str(row.get('reason', 'UNKNOWN'))
                key = f"{st}: {rs}"
                reason_breakdown[key] = reason_breakdown.get(key, 0) + 1

        # 3. Parquet actual tickers count
        parquet_file = os.path.join(PARQUET_DIR, f"russell1000_{year}.parquet")
        parquet_ticker_count = 0
        if os.path.exists(parquet_file):
            df_pq = pd.read_parquet(parquet_file, columns=['ticker'])
            parquet_ticker_count = df_pq['ticker'].nunique()

        coverage_pct = (success_count / univ_count * 100) if univ_count > 0 else 0.0

        summary_list.append({
            'year': year,
            'universe_count': univ_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'parquet_ticker_count': parquet_ticker_count,
            'coverage_pct': round(coverage_pct, 2)
        })

    df_res = pd.DataFrame(summary_list)
    
    print("=== TỔNG HỢP KIỂM TRA DỮ LIỆU MARKET DATA VS UNIVERSE (2000 - 2026) ===")
    print(df_res.to_string(index=False))

    print("\n=== PHÂN TÍCH TỔNG HỢP LÝ DO / TRẠNG THÁI KHÔNG THÀNH CÔNG ===")
    for k, v in sorted(reason_breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f" - {k}: {v} lượt cổ phiếu")

    # --- VẼ BIỂU ĐỒ ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    width = 0.4
    x = df_res['year']
    
    ax1.bar(x - width/2, df_res['universe_count'], width=width, label='Russell 1000 Universe', color='#4a90e2', alpha=0.85)
    ax1.bar(x + width/2, df_res['success_count'], width=width, label='Market Data Extracted (Success)', color='#2ecc71', alpha=0.85)
    
    ax1.set_ylabel('Số lượng cổ phiếu (Tickers)', fontsize=12, fontweight='bold')
    ax1.set_title('Bước 2: So sánh Số lượng Cổ phiếu Universe vs Market Data Thực tế (2000–2026)', fontsize=14, fontweight='bold', pad=15)
    ax1.legend(loc='lower right', fontsize=11, frameon=True, facecolor='white', framealpha=0.9)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    ax1.set_ylim(650, 1100)

    for idx, row in df_res.iterrows():
        if row['year'] % 2 == 0:
            ax1.text(row['year'] + width/2, row['success_count'] + 5, f"{row['success_count']}", 
                     ha='center', va='bottom', fontsize=8, rotation=45, color='#1e8449', fontweight='bold')

    ax2.plot(df_res['year'], df_res['coverage_pct'], color='#e74c3c', marker='o', linewidth=2.5, markersize=5, label='Coverage Rate (%)')
    ax2.axhline(100.0, color='gray', linestyle=':', alpha=0.7, label='100% Target')
    ax2.set_ylabel('Tỷ lệ phủ (%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Năm', fontsize=12, fontweight='bold')
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=45)
    ax2.set_ylim(65, 105)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower right', fontsize=10)

    avg_cov = df_res['coverage_pct'].mean()
    min_cov = df_res['coverage_pct'].min()
    min_year = df_res.loc[df_res['coverage_pct'].idxmin(), 'year']
    
    ax2.text(0.02, 0.15, f"Trung binh phu: {avg_cov:.2f}%\nThap nhat: {min_cov:.2f}% (Nam {min_year})", 
             transform=ax2.transAxes, fontsize=10, verticalalignment='bottom',
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", edgecolor="orange", alpha=0.9))

    plt.tight_layout()
    chart_path = os.path.join(FIGURE_DIR, "step2_market_data_coverage.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"\n[OK] Đã xuất biểu đồ Step 2: {chart_path}")

    import shutil
    shutil.copy(chart_path, os.path.join(REPORT_DIR, "step2_market_data_coverage.png"))
    print(f"[OK] Đã sao chép biểu đồ tới {REPORT_DIR}/step2_market_data_coverage.png")

    return df_res, reason_breakdown

if __name__ == "__main__":
    analyze_market_data_coverage()
