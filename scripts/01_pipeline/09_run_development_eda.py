"""
09_run_development_eda.py
================================================================================
Step 6: Development EDA (Exploratory Data Analysis) 2000-2023

STRICT QUANT RULE: Zero Data Snooping!
All statistics, dispersion regimes, return distributions, missingness profiles,
and liquidity deciles are calculated strictly on the Development period:
  Window: 2000-07-01 to 2023-12-29 (24 years, 5,913 trading sessions).
  Out-of-sample deployment period (2024-2026) is 100% untouched and unseen.

Outputs:
  - Tables: docs/Data report/market_data_audit/tables/eda_*
  - Figures: docs/Data report/market_data_audit/figures/eda_*
================================================================================
"""

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MATRICES_DIR = BASE_DIR / "data" / "processed" / "matrices"
PIT_JSON_PATH = BASE_DIR / "data" / "raw" / "universe" / "russell1000_pit_by_year.json"
TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
FIGURES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "figures"

# Development Boundaries
DEV_START = pd.Timestamp("2000-07-01")
DEV_END = pd.Timestamp("2023-12-29")

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    t_start = time.time()
    log("=" * 80)
    log("STEP 6: EDA CHUYÊN SÂU TRÊN TẬP PHÁT TRIỂN (DEVELOPMENT: 2000-2023)")
    log("=" * 80)
    log(f"  -> Ranh giới khảo sát: {DEV_START.strftime('%Y-%m-%d')} đến {DEV_END.strftime('%Y-%m-%d')}")
    log("  -> NGUYÊN TẮC: Tuyệt đối không chạm vào giai đoạn 2024-2026 (Zero Snooping)!")

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Style configuration
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#cccccc'
    plt.rcParams['axes.linewidth'] = 0.8

    # --------------------------------------------------------------------------
    # 1. Load Development Slice of Matrices & Masks
    # --------------------------------------------------------------------------
    log("[1/5] Tải dữ liệu ma trận và lọc vùng Development...")
    unique_dates = pd.read_parquet(MATRICES_DIR / "matrix_dates_index.parquet")['date'].values
    dev_mask_dates = (unique_dates >= DEV_START) & (unique_dates <= DEV_END)
    dev_dates = unique_dates[dev_mask_dates]
    log(f"  -> Số phiên giao dịch Development: {len(dev_dates):,} phiên")

    # Load only development date slice
    membership_mask = pd.read_parquet(MATRICES_DIR / "membership_mask.parquet").loc[dev_dates]
    valid_data_mask = pd.read_parquet(MATRICES_DIR / "valid_data_mask.parquet").loc[dev_dates]
    valid_label_mask = pd.read_parquet(MATRICES_DIR / "valid_label_mask.parquet").loc[dev_dates]
    daily_return = pd.read_parquet(MATRICES_DIR / "daily_return.parquet").loc[dev_dates]
    adj_close = pd.read_parquet(MATRICES_DIR / "adj_close.parquet").loc[dev_dates]
    adj_volume = pd.read_parquet(MATRICES_DIR / "adj_volume.parquet").loc[dev_dates]

    # --------------------------------------------------------------------------
    # 2. Universe Dynamics & Constituent Churn Rate (2000-2023)
    # --------------------------------------------------------------------------
    log("[2/5] Phân tích Universe Dynamics & Tỷ lệ thay thế thành viên (Churn)...")
    with open(PIT_JSON_PATH, 'r', encoding='utf-8') as f:
        pit_json = json.load(f)

    # Build annual churn table
    churn_records = []
    prev_constituents = None
    dev_years = [y for y in sorted([int(k) for k in pit_json.keys()]) if 2000 <= y <= 2023]

    for y in dev_years:
        curr_constituents = set(pit_json[str(y)])
        p_start = pd.Timestamp(f"{y}-07-01")
        p_end = pd.Timestamp(f"{y+1}-06-30") if y < 2023 else DEV_END
        p_dates = [d for d in dev_dates if p_start <= d <= p_end]
        
        m_active = membership_mask.loc[p_dates].values.sum(axis=1).mean() if p_dates else 0
        d_active = valid_data_mask.loc[p_dates].values.sum(axis=1).mean() if p_dates else 0
        l_active = valid_label_mask.loc[p_dates].values.sum(axis=1).mean() if p_dates else 0

        if prev_constituents is None:
            added = 0
            removed = 0
            churn_pct = 0.0
        else:
            added = len(curr_constituents - prev_constituents)
            removed = len(prev_constituents - curr_constituents)
            churn_pct = (added + removed) / (len(curr_constituents) + len(prev_constituents)) * 100

        churn_records.append({
            'snapshot_year': y,
            'official_constituents': len(curr_constituents),
            'entering_stocks': added,
            'exiting_stocks': removed,
            'annual_churn_pct': round(churn_pct, 2),
            'avg_daily_members': round(m_active, 1),
            'avg_daily_valid_data': round(d_active, 1),
            'avg_daily_valid_label': round(l_active, 1)
        })
        prev_constituents = curr_constituents

    df_churn = pd.DataFrame(churn_records)
    df_churn.to_csv(TABLES_DIR / "eda_universe_dynamics_by_year.csv", index=False)
    log(f"  -> Churn bình quân hằng năm: {df_churn['annual_churn_pct'].mean():.2f}%")
    log(f"  -> Số cổ phiếu mới gia nhập rổ bình quân/năm: {df_churn['entering_stocks'].mean():.1f} mã")

    # Plot Universe Turnover
    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)
    x = df_churn['snapshot_year'][1:]
    ax.bar(x - 0.2, df_churn['entering_stocks'][1:], width=0.4, label='Gia nhập mới (In)', color='#10b981', alpha=0.85)
    ax.bar(x + 0.2, df_churn['exiting_stocks'][1:], width=0.4, label='Rút lui khỏi rổ (Out)', color='#ef4444', alpha=0.85)
    ax.plot(x, df_churn['annual_churn_pct'][1:], color='#3b82f6', marker='o', linewidth=2, label='Tỷ lệ Churn (%)')
    ax.set_title('Biến Động Thành Viên Russell 1000 Hằng Năm (2001–2023)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Năm Tái Cơ Cấu (Snapshot Year)', fontsize=11)
    ax.set_ylabel('Số lượng cổ phiếu / Tỷ lệ Churn (%)', fontsize=11)
    ax.legend(frameon=True, facecolor='white', loc='upper right')
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_universe_turnover_and_active_count.png")
    plt.close(fig)

    # --------------------------------------------------------------------------
    # 3. Daily Return Distribution, Outliers & Fat Tails
    # --------------------------------------------------------------------------
    log("[3/5] Phân tích phân phối Return, Fat-Tails và Outliers...")
    # Extract all valid returns within valid_data_mask
    valid_returns = daily_return.values[valid_data_mask.values]
    valid_returns = valid_returns[np.isfinite(valid_returns)]
    n_obs = len(valid_returns)
    log(f"  -> Số quan sát return hợp lệ trong Development: {n_obs:,}")

    # Calculate statistical moments
    ret_mean = np.mean(valid_returns)
    ret_median = np.median(valid_returns)
    ret_std = np.std(valid_returns)
    ret_ann_vol = ret_std * np.sqrt(252)
    ret_skew = stats.skew(valid_returns)
    ret_kurt = stats.kurtosis(valid_returns) # excess kurtosis

    percentiles = [0.01, 0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9, 99.99]
    pct_values = np.percentile(valid_returns, percentiles)

    # Extreme jumps
    gt_10pct = np.mean(valid_returns > 0.10) * 100
    lt_neg10pct = np.mean(valid_returns < -0.10) * 100
    gt_20pct = np.mean(valid_returns > 0.20) * 100
    lt_neg20pct = np.mean(valid_returns < -0.20) * 100

    moments_df = pd.DataFrame([{
        'sample_period': '2000-07-01 to 2023-12-29',
        'observations': n_obs,
        'mean_daily_return': ret_mean,
        'median_daily_return': ret_median,
        'daily_volatility': ret_std,
        'annualized_volatility': ret_ann_vol,
        'skewness': ret_skew,
        'excess_kurtosis': ret_kurt,
        'min_return': np.min(valid_returns),
        'max_return': np.max(valid_returns),
        'p01': pct_values[0],
        'p1': pct_values[2],
        'p5': pct_values[3],
        'p25': pct_values[5],
        'p50': pct_values[6],
        'p75': pct_values[7],
        'p95': pct_values[9],
        'p99': pct_values[10],
        'p99_9': pct_values[11],
        'pct_gt_10pct': gt_10pct,
        'pct_lt_neg10pct': lt_neg10pct,
        'pct_gt_20pct': gt_20pct,
        'pct_lt_neg20pct': lt_neg20pct
    }])
    moments_df.to_csv(TABLES_DIR / "eda_daily_return_moments.csv", index=False)
    log(f"  -> Daily Vol: {ret_std*100:.2f}% (Annualized: {ret_ann_vol*100:.2f}%)")
    log(f"  -> Skewness: {ret_skew:.3f} | Excess Kurtosis: {ret_kurt:.2f} (Đuôi cực dày!)")
    log(f"  -> Tần suất return vượt |10%|: {gt_10pct+lt_neg10pct:.3f}% (~{int(n_obs*(gt_10pct+lt_neg10pct)/100):,} phiên-mã)")

    # Plot Distribution & Q-Q Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=300)
    # Clip for clean visualization
    viz_returns = np.clip(valid_returns, -0.15, 0.15)
    ax1.hist(viz_returns, bins=150, density=True, alpha=0.65, color='#3b82f6', edgecolor='none', label='Phân phối thực tế')
    x_plot = np.linspace(-0.15, 0.15, 500)
    ax1.plot(x_plot, stats.norm.pdf(x_plot, ret_mean, ret_std), color='#ef4444', linewidth=2, label=f'Chuẩn lý thuyết (Normal N(0, {ret_std:.3f}))')
    ax1.set_title(f'Phân Phối Return Hằng Ngày (Excess Kurtosis = {ret_kurt:.1f})', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Daily Return (Capped at ±15% for display)')
    ax1.set_ylabel('Mật độ xác suất (Density)')
    ax1.legend(frameon=True, facecolor='white')

    # QQ plot sample 10,000 points
    sample_qq = np.random.choice(valid_returns, size=15000, replace=False)
    stats.probplot(sample_qq, dist="norm", plot=ax2)
    ax2.get_lines()[0].set_color('#3b82f6')
    ax2.get_lines()[0].set_markersize(2)
    ax2.get_lines()[1].set_color('#ef4444')
    ax2.get_lines()[1].set_linewidth(2)
    ax2.set_title('Biểu Đồ Q-Q So Với Phân Phối Chuẩn (Heavy Tails)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Theoretical Quantiles (Phân vị lý thuyết)')
    ax2.set_ylabel('Ordered Values (Phân vị thực nghiệm)')

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_daily_return_distribution_qq.png")
    plt.close(fig)

    # --------------------------------------------------------------------------
    # 4. Cross-Sectional Dispersion Across Market Regimes
    # --------------------------------------------------------------------------
    log("[4/5] Phân tích Cross-Sectional Dispersion & Chế độ thị trường...")
    # Calculate daily Cross-Sectional Volatility
    # sigma_t = std across valid active stocks on date t
    cs_dispersion = []
    for dt_val in dev_dates:
        mask_t = valid_data_mask.loc[dt_val].values
        if mask_t.sum() >= 50:
            rets_t = daily_return.loc[dt_val].values[mask_t]
            rets_t = rets_t[np.isfinite(rets_t)]
            cs_dispersion.append({
                'date': dt_val,
                'active_count': len(rets_t),
                'cs_mean_return': np.mean(rets_t),
                'cs_std_dispersion': np.std(rets_t),
                'cs_iqr_dispersion': np.percentile(rets_t, 75) - np.percentile(rets_t, 25)
            })

    df_cs = pd.DataFrame(cs_dispersion)
    df_cs['year'] = pd.to_datetime(df_cs['date']).dt.year
    annual_cs = df_cs.groupby('year').agg(
        avg_dispersion=('cs_std_dispersion', 'mean'),
        max_dispersion=('cs_std_dispersion', 'max'),
        min_dispersion=('cs_std_dispersion', 'min'),
        avg_iqr=('cs_iqr_dispersion', 'mean')
    ).reset_index()
    annual_cs.to_csv(TABLES_DIR / "eda_cross_sectional_dispersion.csv", index=False)

    # Plot Cross-Sectional Dispersion Time-Series
    fig, ax = plt.subplots(figsize=(14, 5), dpi=300)
    df_cs['roll_disp_20d'] = df_cs['cs_std_dispersion'].rolling(20, min_periods=5).mean()
    ax.plot(pd.to_datetime(df_cs['date']), df_cs['cs_std_dispersion'] * 100, color='#94a3b8', alpha=0.35, linewidth=0.8, label='Độ phân tán hàng ngày')
    ax.plot(pd.to_datetime(df_cs['date']), df_cs['roll_disp_20d'] * 100, color='#2563eb', linewidth=1.8, label='Độ phân tán MA(20 ngày)')
    
    # Highlight major crisis regimes
    ax.axvspan(pd.Timestamp("2000-09-01"), pd.Timestamp("2002-10-31"), color='#fecaca', alpha=0.3, label='Dot-com Crash')
    ax.axvspan(pd.Timestamp("2008-09-01"), pd.Timestamp("2009-06-30"), color='#fed7aa', alpha=0.3, label='Khủng hoảng 2008 (GFC)')
    ax.axvspan(pd.Timestamp("2020-02-15"), pd.Timestamp("2020-05-31"), color='#fef08a', alpha=0.3, label='COVID-19 Shock')
    ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-10-31"), color='#e9d5ff', alpha=0.3, label='Fed Rate Hikes 2022')

    ax.set_title('Độ Phân Tán Chéo Của Lợi Nhuận Hằng Ngày (Cross-Sectional Dispersion: 2000–2023)', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Năm (Development Horizon)')
    ax.set_ylabel('Độ lệch chuẩn chéo CS Volatility (%)')
    ax.legend(frameon=True, facecolor='white', loc='upper right', ncol=3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_cross_sectional_dispersion_history.png")
    plt.close(fig)

    # --------------------------------------------------------------------------
    # 5. Liquidity Deciles & Market Structure Analysis
    # --------------------------------------------------------------------------
    log("[5/5] Phân loại thanh khoản (Liquidity Deciles) và khuyến nghị mô hình...")
    # Calculate dollar volume matrix
    dollar_vol = adj_close * adj_volume
    # Compute median daily dollar volume per canonical_sid over development period
    sid_liq = []
    for s in valid_data_mask.columns:
        m_s = valid_data_mask[s].values
        if m_s.sum() >= 20:
            d_vol_s = dollar_vol[s].values[m_s]
            p_s = adj_close[s].values[m_s]
            r_s = daily_return[s].values[m_s]
            sid_liq.append({
                'canonical_sid': s,
                'active_days': int(m_s.sum()),
                'median_dollar_vol': float(np.nanmedian(d_vol_s)),
                'median_price': float(np.nanmedian(p_s)),
                'return_volatility': float(np.nanstd(r_s))
            })

    df_liq = pd.DataFrame(sid_liq)
    df_liq['liquidity_decile'] = pd.qcut(df_liq['median_dollar_vol'], 10, labels=[f"D{i}" for i in range(1, 11)])
    decile_summary = df_liq.groupby('liquidity_decile').agg(
        stock_count=('canonical_sid', 'count'),
        median_daily_dollar_vol_mil=('median_dollar_vol', lambda x: np.median(x) / 1e6),
        median_price=('median_price', 'median'),
        avg_annual_volatility=('return_volatility', lambda x: np.mean(x) * np.sqrt(252) * 100)
    ).reset_index()
    decile_summary.to_csv(TABLES_DIR / "eda_liquidity_deciles.csv", index=False)

    # Plot Liquidity vs Volatility
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    bars = ax.bar(decile_summary['liquidity_decile'], decile_summary['avg_annual_volatility'], color='#6366f1', alpha=0.85)
    ax.set_title('Biến Động Hằng Năm Theo Nhóm Thanh Khoản (Liquidity Deciles: D1 Thấp Nhất -> D10 Cao Nhất)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Decile Thanh Khoản (D1: Kém thanh khoản nhất trong Russell 1000 | D10: Mega-cap)')
    ax.set_ylabel('Độ biến động hàng năm Annualized Vol (%)')
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{yval:.1f}%", ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "eda_liquidity_vs_volatility_deciles.png")
    plt.close(fig)

    log("\n" + "=" * 80)
    log("TỔNG KẾT EDA DEVELOPMENT (2000-2023) & ĐỀ XUẤT CHO BƯỚC 7:")
    log("=" * 80)
    log(f"1. Phân phối có Excess Kurtosis cực cao ({ret_kurt:.1f}): Đề xuất bắt buộc chuyển đổi Target sang Rank Cross-Sectional Uniform [0, 1].")
    log(f"2. Độ phân tán biến thiên mạnh (từ {df_cs['cs_std_dispersion'].min()*100:.2f}% đến {df_cs['cs_std_dispersion'].max()*100:.2f}%): Feature cần được chuẩn hóa Z-score/Rank theo từng ngày T.")
    log(f"3. Nhóm thanh khoản thấp nhất D1 có vol cao hơn đáng kể ({decile_summary['avg_annual_volatility'].iloc[0]:.1f}% vs {decile_summary['avg_annual_volatility'].iloc[-1]:.1f}%): Cần trọng số hoặc liquidity gate trong portfolio sizing.")
    log(f"4. Bảng và biểu đồ đã lưu vào: docs/Data report/market_data_audit/ (tables & figures)")
    log(f"TOÀN BỘ BƯỚC 6 HOÀN THÀNH XUẤT SẮC TRONG {time.time()-t_start:.2f} GIÂY!")

if __name__ == "__main__":
    main()
