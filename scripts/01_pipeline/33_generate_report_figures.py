"""
Script 33: Tạo các biểu đồ trực quan hóa phục vụ Báo cáo Kết quả Thực nghiệm Ngoài mẫu (OOS).
Tác vụ:
1. Hình 1: Biểu đồ cột Mean Rank IC theo giai đoạn (2024, 2025, Nửa đầu 2026 và Toàn bộ OOS).
2. Hình 2: Biểu đồ chuỗi thời gian Rolling 63-day Rank IC (làm mượt quan sát xu hướng).
3. Hình 3: Biểu đồ đường biến động NAV 624 phiên theo thời gian (2 ô: 0 bps vs 20 bps).
4. Hình 4: Biểu đồ cột so sánh Lợi suất lũy kế Trước vs Sau chi phí giả định.
"""

import io
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Thiết lập style trực quan học thuật
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#eeeeee'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7

# Đường dẫn thư mục
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FIG_DIR = BASE_DIR / "docs" / "reports" / "baseline" / "figures"
OUTPUT_FIG_DIR.mkdir(parents=True, exist_ok=True)

# Màu sắc chuẩn mực thống nhất cho 3 mô hình
COLORS = {
    'Ridge': '#1f77b4',       # Xanh dương đậm
    'GBDT': '#2ca02c',        # Xanh lá cây
    'ret_20d': '#ff7f0e'      # Cam đậm
}


def load_oos_ic_data():
    csv_path = BASE_DIR / "outputs" / "reports" / "oos_daily_ic_2024_2026.csv"
    df = pd.read_csv(csv_path)
    df_strict = df[df['is_primary_strict_t1'] == True].copy()
    df_strict['t1_date_dt'] = pd.to_datetime(df_strict['t1_date_str'])
    df_strict['t1_year'] = df_strict['t1_date_dt'].dt.year
    df_strict = df_strict.sort_values('t1_date_dt').reset_index(drop=True)
    return df_strict


def plot_fig1_ic_by_period(df):
    """Hình 1: Biểu đồ cột Mean Rank IC theo từng giai đoạn."""
    periods = [
        ('Năm 2024\n(251 phiên)', df[df['t1_year'] == 2024]),
        ('Năm 2025\n(250 phiên)', df[df['t1_year'] == 2025]),
        ('Nửa đầu 2026\n(123 phiên)', df[df['t1_year'] == 2026]),
        ('Toàn bộ OOS\n(624 phiên)', df)
    ]
    
    period_labels = [p[0] for p in periods]
    models = ['Ridge', 'GBDT', 'ret_20d']
    model_labels = ['Ridge (alpha=1.0)', 'GBDT (7 leaves)', 'ret_20d (Benchmark)']
    
    means = {m: [] for m in models}
    
    for _, sub_df in periods:
        means['Ridge'].append(sub_df['ic_ridge'].mean())
        means['GBDT'].append(sub_df['ic_gbdt'].mean())
        means['ret_20d'].append(sub_df['ic_ret_20d'].mean())
        
    x = np.arange(len(period_labels))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    
    rects1 = ax.bar(x - width, means['Ridge'], width, label=model_labels[0], color=COLORS['Ridge'], alpha=0.9, edgecolor='black', linewidth=0.5)
    rects2 = ax.bar(x, means['GBDT'], width, label=model_labels[1], color=COLORS['GBDT'], alpha=0.9, edgecolor='black', linewidth=0.5)
    rects3 = ax.bar(x + width, means['ret_20d'], width, label=model_labels[2], color=COLORS['ret_20d'], alpha=0.9, edgecolor='black', linewidth=0.5)
    
    ax.axhline(0, color='black', linewidth=0.8, linestyle='-')
    ax.set_ylabel('Mean Spearman Rank IC', fontsize=11, fontweight='bold')
    ax.set_title('Hình 1: Mean Rank IC Theo Từng Giai Đoạn Nhãn T+1 (OOS 2024 - 2026)', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(period_labels, fontsize=10)
    ax.legend(frameon=True, facecolor='white', edgecolor='#dddddd', fontsize=9.5, loc='upper right')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax.set_ylim(-0.015, 0.045)
    
    # Hiển thị số liệu trên đầu cột
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            va = 'bottom' if height >= 0 else 'top'
            offset = 0.001 if height >= 0 else -0.001
            ax.annotate(f'{height:+.4f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height + offset),
                        xytext=(0, 0), textcoords="offset points",
                        ha='center', va=va, fontsize=8.5, fontweight='bold')
            
    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)
    
    plt.tight_layout()
    out_path = OUTPUT_FIG_DIR / "fig1_mean_rank_ic_by_year.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[Done] Saved: {out_path}")


def plot_fig2_rolling_ic(df):
    """Hình 2: Biểu đồ chuỗi thời gian Rolling 63-day Rank IC."""
    df_sorted = df.copy()
    
    # Tính rolling 63 phiên
    df_sorted['ridge_roll63'] = df_sorted['ic_ridge'].rolling(window=63, min_periods=21).mean()
    df_sorted['gbdt_roll63'] = df_sorted['ic_gbdt'].rolling(window=63, min_periods=21).mean()
    df_sorted['ret20d_roll63'] = df_sorted['ic_ret_20d'].rolling(window=63, min_periods=21).mean()
    
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
    
    dates = df_sorted['t1_date_dt']
    
    ax.plot(dates, df_sorted['ridge_roll63'], label='Ridge Baseline (alpha=1.0)', color=COLORS['Ridge'], linewidth=1.8)
    ax.plot(dates, df_sorted['gbdt_roll63'], label='GBDT Candidate (7 leaves)', color=COLORS['GBDT'], linewidth=1.8)
    ax.plot(dates, df_sorted['ret20d_roll63'], label='ret_20d (Momentum Benchmark)', color=COLORS['ret_20d'], linewidth=1.5, linestyle='--')
    
    ax.axhline(0, color='black', linewidth=0.9, linestyle=':')
    
    ax.set_ylabel('Rolling Mean Rank IC', fontsize=11, fontweight='bold')
    ax.set_title('Hình 2: Biến Động Rank IC Chuỗi Thời Gian (Cửa Sổ Trượt Tối Đa 63 Phiên, Bắt Đầu Từ Phiên 21)', fontsize=11, fontweight='bold', pad=15)
    ax.legend(frameon=True, facecolor='white', edgecolor='#dddddd', fontsize=9.5, loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Định dạng trục thời gian
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    
    # Chú thích xu hướng theo số liệu đo lường
    ax.annotate('Đạt đỉnh làm mượt ~+0.08 trong 2024', 
                xy=(pd.to_datetime('2024-05-15'), 0.075),
                xytext=(pd.to_datetime('2024-02-01'), 0.090),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=0.8),
                fontsize=8.5, bbox=dict(boxstyle="round,pad=0.3", fc="#f8f9fa", ec="#b0bec5", lw=0.5))

    ax.annotate('IC đo được ở các giai đoạn sau thấp hơn\n(Dao động quanh +0.01 đến +0.02)', 
                xy=(pd.to_datetime('2026-03-01'), 0.005),
                xytext=(pd.to_datetime('2025-07-01'), -0.025),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=0.8),
                fontsize=8.5, bbox=dict(boxstyle="round,pad=0.3", fc="#f8f9fa", ec="#b0bec5", lw=0.5))

    ax.set_ylim(-0.05, 0.11)
    plt.tight_layout()
    out_path = OUTPUT_FIG_DIR / "fig2_rolling_rank_ic_63d.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[Done] Saved: {out_path}")


def plot_fig3_nav_trajectory():
    """Hình 3: Đường NAV 624 phiên chia làm 2 ô (Trước vs Sau chi phí)."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.5), dpi=300, sharex=True)
    
    models = ['ridge', 'gbdt', 'ret_20d']
    labels = {
        'ridge': 'Ridge Baseline (alpha=1.0)',
        'gbdt': 'GBDT Candidate (7 leaves)',
        'ret_20d': 'ret_20d (Benchmark)'
    }
    
    start_date = pd.to_datetime('2024-01-02')
    
    # Ô 1: Trước chi phí (0 bps)
    for m in models:
        p = BASE_DIR / "outputs" / "reports" / "backtest_primary_scope" / f"ledger_{m}_0bps.csv"
        df = pd.read_csv(p)
        df['dt'] = pd.to_datetime(df['date'])
        
        # Thêm điểm mốc xuất phát T0 = $100,000
        dates = [start_date] + df['dt'].tolist()
        navs = [100000.0] + df['nav'].tolist()
        
        c = COLORS['Ridge'] if m == 'ridge' else (COLORS['GBDT'] if m == 'gbdt' else COLORS['ret_20d'])
        ls = '-' if m != 'ret_20d' else '--'
        ax1.plot(dates, navs, label=labels[m], color=c, linewidth=1.8, linestyle=ls)
        
        # Đánh dấu NAV cuối kỳ
        final_val = navs[-1]
        ax1.scatter([dates[-1]], [final_val], color=c, s=30, zorder=5)
        ax1.annotate(f'${final_val:,.0f}', 
                     xy=(dates[-1], final_val), 
                     xytext=(5, -2 if m == 'gbdt' else 2), 
                     textcoords='offset points', 
                     fontsize=8.5, fontweight='bold', color=c)
        
    ax1.axhline(100000, color='#d32f2f', linestyle=':', linewidth=1.2, label='Vốn khởi tạo ($100,000)')
    ax1.set_ylabel('NAV ($)', fontsize=11, fontweight='bold')
    ax1.set_title('A. Danh mục Top 20 TRƯỚC Chi Phí (0 bps / Gross Alpha)', fontsize=11, fontweight='bold', loc='left', color='#1a237e')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#dddddd', fontsize=9)
    ax1.set_ylim(70000, 155000)
    ax1.yaxis.set_major_formatter('${x:,.0f}')
    
    # Ô 2: Sau chi phí giả định 20 bps
    for m in models:
        p = BASE_DIR / "outputs" / "reports" / "backtest_primary_scope" / f"ledger_{m}_20bps.csv"
        df = pd.read_csv(p)
        df['dt'] = pd.to_datetime(df['date'])
        
        dates = [start_date] + df['dt'].tolist()
        navs = [100000.0] + df['nav'].tolist()
        
        c = COLORS['Ridge'] if m == 'ridge' else (COLORS['GBDT'] if m == 'gbdt' else COLORS['ret_20d'])
        ls = '-' if m != 'ret_20d' else '--'
        ax2.plot(dates, navs, label=labels[m], color=c, linewidth=1.8, linestyle=ls)
        
        final_val = navs[-1]
        ax2.scatter([dates[-1]], [final_val], color=c, s=30, zorder=5)
        ax2.annotate(f'${final_val:,.0f}', 
                     xy=(dates[-1], final_val), 
                     xytext=(5, 3 if m == 'ridge' else (-6 if m == 'gbdt' else -2)), 
                     textcoords='offset points', 
                     fontsize=8.5, fontweight='bold', color=c)
        
    ax2.axhline(100000, color='#d32f2f', linestyle=':', linewidth=1.2, label='Vốn khởi tạo ($100,000)')
    ax2.set_ylabel('NAV ($)', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Thời Gian (Phiên Thực Thi Ngoài Mẫu)', fontsize=11, fontweight='bold')
    ax2.set_title('B. Danh mục Top 20 SAU Chi Phí Giả Định (20 bps Round-trip / Net Tradable PnL)', fontsize=11, fontweight='bold', loc='left', color='#b71c1c')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#dddddd', fontsize=9)
    ax2.set_ylim(20000, 105000)
    ax2.yaxis.set_major_formatter('${x:,.0f}')
    
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=30)
    
    plt.suptitle('Hình 3: Quỹ Đạo Đường NAV 624 Phiên Ngoài Mẫu Của 3 Tín Hiệu (2024-01-03 đến 2026-06-30)', fontsize=12.5, fontweight='bold', y=0.995)
    plt.tight_layout()
    out_path = OUTPUT_FIG_DIR / "fig3_nav_trajectory_0bps_vs_20bps.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[Done] Saved: {out_path}")


def plot_fig4_cumulative_returns():
    """Hình 4: Biểu đồ cột so sánh Lợi suất lũy kế Trước vs Sau chi phí."""
    models = ['Ridge (alpha=1.0)', 'GBDT (7 leaves)', 'ret_20d (Benchmark)']
    returns_0bps = [+34.93, -7.83, +12.90]
    returns_20bps = [-61.19, -73.53, -67.58]
    
    x = np.arange(len(models))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    
    rects1 = ax.bar(x - width/2, returns_0bps, width, label='Trước chi phí (Gross / 0 bps)', color='#2b5c8f', edgecolor='black', linewidth=0.5)
    rects2 = ax.bar(x + width/2, returns_20bps, width, label='Sau chi phí giả định (Net / 20 bps)', color='#c0392b', edgecolor='black', linewidth=0.5)
    
    ax.axhline(0, color='black', linewidth=0.9)
    ax.set_ylabel('Lợi Suất Lũy Kế (%)', fontsize=11, fontweight='bold')
    ax.set_title('Hình 4: Tác Động Bào Mòn Của Chi Phí Giả Định 20 bps Đối Với Lợi Suất Lũy Kế', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=10.5, fontweight='bold')
    ax.legend(frameon=True, facecolor='white', edgecolor='#dddddd', fontsize=9.5, loc='upper right')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax.set_ylim(-85, 48)
    
    # Hiển thị số liệu
    for rect in rects1:
        height = rect.get_height()
        va = 'bottom' if height >= 0 else 'top'
        offset = 1.5 if height >= 0 else -3.0
        ax.annotate(f'{height:+.2f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height + offset),
                    ha='center', va=va, fontsize=9.5, fontweight='bold', color='#1a237e')
        
    for rect in rects2:
        height = rect.get_height()
        va = 'bottom' if height >= 0 else 'top'
        offset = 1.5 if height >= 0 else -3.5
        ax.annotate(f'{height:+.2f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height + offset),
                    ha='center', va=va, fontsize=9.5, fontweight='bold', color='#b71c1c')
        
    plt.tight_layout()
    out_path = OUTPUT_FIG_DIR / "fig4_cumulative_returns_cost_impact.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[Done] Saved: {out_path}")


def main():
    print("=== Đang nạp dữ liệu OOS và Backtest ===")
    df_ic = load_oos_ic_data()
    print(f"Tổng số phiên OOS đã lọc (is_primary_strict_t1): {len(df_ic)}")
    
    print("\n1. Đang vẽ Hình 1: Mean Rank IC theo từng giai đoạn...")
    plot_fig1_ic_by_period(df_ic)
    
    print("\n2. Đang vẽ Hình 2: Rolling 63-day Rank IC...")
    plot_fig2_rolling_ic(df_ic)
    
    print("\n3. Đang vẽ Hình 3: Quỹ đạo NAV 624 phiên (0 bps vs 20 bps)...")
    plot_fig3_nav_trajectory()
    
    print("\n4. Đang vẽ Hình 4: So sánh Lợi suất lũy kế Trước vs Sau chi phí...")
    plot_fig4_cumulative_returns()
    
    print("\n=== Hoàn tất tạo toàn bộ 4 biểu đồ báo cáo ===")


if __name__ == '__main__':
    main()
