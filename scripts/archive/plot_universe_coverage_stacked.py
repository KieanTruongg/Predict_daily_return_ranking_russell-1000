"""
scripts/01_pipeline/plot_universe_coverage_stacked.py
Tạo biểu đồ trực quan hóa Stacked Bar & Độ bao phủ (Coverage) 27 năm Russell 1000.
Panel 1: Cột xếp chồng thể hiện cấu phần (QC Matched vs PIT-Only Delisted/M&A).
Panel 2: Tỷ lệ bao phủ chi tiết (%) kèm đường chuẩn 99.0%.
"""

import sys
import io
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Handle stdout unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def generate_coverage_chart():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    csv_path = os.path.join(repo_root, "data", "raw", "universe", "extraction_quality_report.csv")
    out_dir = os.path.join(repo_root, "docs", "Data report", "phase1", "figures")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "universe_constituents_coverage.png")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True, gridspec_kw={'height_ratios': [2.2, 1.2]})

    years = df['year'].values
    matched = df['matched'].values
    missing = df['missing'].values
    total = df['pit_tickers'].values
    coverage = df['coverage_pct'].values

    # Panel 1: Stacked Bar Chart
    ax1.bar(years, matched, color='#1e88e5', width=0.65, label='QC Market Data Khớp (Có đầy đủ OHLCV)', edgecolor='none')
    ax1.bar(years, missing, bottom=matched, color='#ef5350', width=0.65, label='PIT-Only (Mã Delisted/M&A/Phá sản)', edgecolor='none')

    ax1.set_ylabel('Số lượng cổ phiếu (Mã)', fontsize=11, fontweight='bold', color='#1a237e')
    ax1.set_ylim(850, 1080)
    ax1.set_title('BÓC TÁCH RUSSELL 1000 & ĐỘ BAO PHỦ QUANTCONNECT (2000 - 2026)', fontsize=13, fontweight='bold', pad=12, color='#0d47a1')
    ax1.legend(loc='lower right', frameon=True, framealpha=0.95, facecolor='white', edgecolor='#e0e0e0', fontsize=9.5)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Label on top of bars
    for i, y in enumerate(years):
        ax1.text(y, total[i] + 4, str(total[i]), ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#37474f')

    # Panel 2: Coverage rate zoom
    ax2.plot(years, coverage, color='#00897b', marker='o', linewidth=2.2, markersize=5, label='Tỷ lệ bao phủ thực tế (%)')
    ax2.fill_between(years, 98.8, coverage, color='#80cbc4', alpha=0.3)
    ax2.axhline(99.0, color='#e53935', linestyle=':', linewidth=1.5, label='Ngưỡng chuẩn tối thiểu (99.0%)')

    ax2.set_ylabel('Tỷ lệ khớp (%)', fontsize=10, fontweight='bold', color='#004d40')
    ax2.set_ylim(98.8, 100.1)
    ax2.set_xlabel('Năm Tái Cơ Cấu (Russell Reconstitution Year)', fontsize=11, fontweight='bold', color='#263238', labelpad=6)
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=45, ha='right', fontsize=9)
    ax2.legend(loc='lower right', frameon=True, framealpha=0.95, facecolor='white', edgecolor='#e0e0e0', fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close()
    print(f"Successfully generated stacked coverage chart at: {out_path}")

if __name__ == "__main__":
    generate_coverage_chart()
