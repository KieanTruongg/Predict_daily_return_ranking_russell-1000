"""
Test 3: Kiểm thử tính Point-In-Time (PIT) & Turnover (Added / Removed) của Russell 1000 Universe
================================================================================================
Mục tiêu:
1. Tính số cổ phiếu được Thêm mới (Added_t = S_t - S_{t-1}) và Loại bỏ (Removed_t = S_{t-1} - S_t) giữa 2 năm liên tiếp.
2. Tính Tỷ lệ biến động thành viên (Turnover Rate %).
3. Thống kê vòng đời cổ phiếu (First Year Seen, Last Year Seen, Total Active Years, Flickering Tickers).
4. Vẽ biểu đồ trực quan hóa số lượng Added / Removed và Turnover Rate (%) qua các năm 2001-2026.
"""

import json
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import shutil

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
FIGURE_DIR = "outputs/figures"
REPORT_DIR = "docs/Data report"

os.makedirs(FIGURE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def run_test3_universe_pit_turnover():
    years = list(range(2000, 2027))
    universe_by_year = {}

    for year in years:
        filepath = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                universe_by_year[year] = set(json.load(f))

    # 1. Turnover analysis
    turnover_records = []
    for i in range(1, len(years)):
        prev_yr = years[i-1]
        curr_yr = years[i]

        prev_set = universe_by_year.get(prev_yr, set())
        curr_set = universe_by_year.get(curr_yr, set())

        added = curr_set - prev_set
        removed = prev_set - curr_set
        retained = curr_set & prev_set

        added_cnt = len(added)
        removed_cnt = len(removed)
        retained_cnt = len(retained)
        total_curr = len(curr_set)

        turnover_rate = ((added_cnt + removed_cnt) / (len(prev_set) + len(curr_set)) * 100) if (len(prev_set) + len(curr_set)) > 0 else 0.0

        turnover_records.append({
            'period': f"{prev_yr}→{curr_yr}",
            'year': curr_yr,
            'prev_count': len(prev_set),
            'curr_count': total_curr,
            'retained': retained_cnt,
            'added': added_cnt,
            'removed': removed_cnt,
            'turnover_rate_pct': round(turnover_rate, 2),
            'added_samples': ", ".join(sorted(list(added))[:5]),
            'removed_samples': ", ".join(sorted(list(removed))[:5])
        })

    df_turnover = pd.DataFrame(turnover_records)

    # 2. Individual Stock Life Span & Flickering Check
    all_tickers = set().union(*universe_by_year.values())
    ticker_history = {}

    for ticker in all_tickers:
        active_years = [y for y in years if ticker in universe_by_year[y]]
        active_years.sort()
        
        first_yr = active_years[0]
        last_yr = active_years[-1]
        total_yrs = len(active_years)
        span_yrs = last_yr - first_yr + 1
        
        # Flickering check: if total_yrs < span_yrs (left and re-entered)
        is_flickering = total_yrs < span_yrs

        ticker_history[ticker] = {
            'first_year': first_yr,
            'last_year': last_yr,
            'active_years_cnt': total_yrs,
            'span_years': span_yrs,
            'is_flickering': is_flickering,
            'years_list': active_years
        }

    flickering_cnt = sum(1 for v in ticker_history.values() if v['is_flickering'])

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 3: PHÂN TÍCH TÍNH POINT-IN-TIME (PIT) & TURNOVER CỦA RUSSELL 1000")
    print("==================================================================================")
    print(df_turnover[['period', 'prev_count', 'curr_count', 'retained', 'added', 'removed', 'turnover_rate_pct']].to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP VỀ TURNOVER & VÒNG ĐỜI CỔ PHIẾU (2000 - 2026):")
    print(f" • Tổng số ticker độc nhất xuất hiện toàn chu kỳ : {len(all_tickers):,} mã")
    print(f" • Trung bình cổ phiếu được thêm mới (Added) / năm  : {df_turnover['added'].mean():.1f} mã")
    print(f" • Trung bình cổ phiếu bị loại bỏ (Removed) / năm   : {df_turnover['removed'].mean():.1f} mã")
    print(f" • Tỷ lệ Turnover trung bình hàng năm              : {df_turnover['turnover_rate_pct'].mean():.2f}%")
    print(f" • Số cổ phiếu duy trì liên tục suốt 27 năm (2000-2026): {sum(1 for v in ticker_history.values() if v['active_years_cnt'] == 27)} mã")
    print(f" • Số cổ phiếu có hiện tượng Flicker (Ra/Vào lại)  : {flickering_cnt} mã")
    print("----------------------------------------------------------------------------------\n")

    # --- VẼ BIỂU ĐỒ TURNOVER ---
    fig, ax1 = plt.subplots(figsize=(14, 6))

    x = df_turnover['year']
    width = 0.35

    rects1 = ax1.bar(x - width/2, df_turnover['added'], width, label='Thêm mới (Added)', color='#2ecc71', alpha=0.85)
    rects2 = ax1.bar(x + width/2, df_turnover['removed'], width, label='Loại bỏ (Removed)', color='#e74c3c', alpha=0.85)

    ax1.set_ylabel('Số lượng cổ phiếu (Tickers)', fontsize=12, fontweight='bold')
    ax1.set_title('Test 3: Biến động Thành viên Russell 1000 Universe (Added vs Removed) qua các năm', fontsize=14, fontweight='bold', pad=15)
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_turnover['period'], rotation=45, ha='right', fontsize=9)
    ax1.legend(loc='upper left', fontsize=11)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Line chart overlay: Turnover Rate %
    ax2 = ax1.twinx()
    ax2.plot(x, df_turnover['turnover_rate_pct'], color='#3498db', marker='s', linewidth=2, label='Turnover Rate (%)')
    ax2.set_ylabel('Tỷ lệ Turnover (%)', fontsize=12, fontweight='bold', color='#2980b9')
    ax2.tick_params(axis='y', labelcolor='#2980b9')
    ax2.set_ylim(0, 20)
    ax2.legend(loc='upper right', fontsize=11)

    plt.tight_layout()
    chart_path = os.path.join(FIGURE_DIR, "test3_universe_turnover.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"[OK] Đã xuất biểu đồ Test 3: {chart_path}")
    shutil.copy(chart_path, os.path.join(REPORT_DIR, "test3_universe_turnover.png"))

    return df_turnover, ticker_history

if __name__ == "__main__":
    run_test3_universe_pit_turnover()
