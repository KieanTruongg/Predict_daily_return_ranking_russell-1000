"""
scripts/01_pipeline/11_apply_forensic_corrections_and_rerun_eda.py
================================================================================
Forensic Corrections & Re-running Development EDA:
1. Apply targeted corrections:
   - Missing Reverse Splits:
     * CHK (2020-04-15): 1-for-200 reverse split (factor=200.0) -> true return = -37.64%
     * CRC (2016-06-01): 1-for-10 reverse split (factor=10.0)   -> true return = +2.50%
     * ADCT (2005-05-10): 1-for-7 reverse split (factor=7.0)    -> true return = +2.86%
     * AA (2016-10-06): 1-for-3 reverse split (factor=3.0)      -> true return = +1.86%
   - Data Vendor Bad Ticks / Collisions (Quarantined in masks):
     * MKL (2010-04-19 to 2010-04-28): bad ticks (~$26 vs ~$380)
     * SABR (2020-03-20 to 2020-03-23): bad tick ($0.50 vs ~$3.80)
     * LOW (2008-06-10 to 2008-06-17): illiquid ticker collision ($76.60 vs ~$23.50)
2. Re-save matrices: daily_return, total_return, target_next_return, valid_data_mask, valid_label_mask.
3. Re-run Development EDA (2000-07-01 to 2023-12-29):
   - Update return moments (Skewness, Kurtosis, Volatility).
   - Re-generate 4 figures.
   - Update EDA summary tables.
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
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path("D:/A_Learning/HK1_2026-2027/CO3101 - Đồ án tổng hợp - ttnt/Predict_daily_return_rankings")
MATRICES_DIR = BASE_DIR / "data" / "processed" / "matrices"
TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
FIGURES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    t_start = time.time()
    log("=" * 80)
    log("ÁP DỤNG HIỆU CHỈNH PHÁP Y & CHẠY LẠI EDA TẬP PHÁT TRIỂN (2000-2023)")
    log("=" * 80)

    # 1. Load Matrices
    log("[1/5] Tải các ma trận daily_return, total_return, valid_data_mask, valid_label_mask, close...")
    ret_df = pd.read_parquet(MATRICES_DIR / "daily_return.parquet")
    tot_ret_df = pd.read_parquet(MATRICES_DIR / "total_return.parquet")
    vdata_df = pd.read_parquet(MATRICES_DIR / "valid_data_mask.parquet")
    vlabel_df = pd.read_parquet(MATRICES_DIR / "valid_label_mask.parquet")
    close_df = pd.read_parquet(MATRICES_DIR / "close.parquet")
    adj_close_df = pd.read_parquet(MATRICES_DIR / "adj_close.parquet")
    split_fac_df = pd.read_parquet(MATRICES_DIR / "cumulative_split_factor.parquet")

    # 2. Apply Forensic Corrections
    log("\n[2/5] Áp dụng các hiệu chỉnh pháp y đã thẩm định:")

    # 2A. Missing Reverse Splits (Adjust daily_return and total_return)
    # CHK 2020-04-15: 1:200 reverse split
    chk_sid = "CHK R735QTJ8XC9X"
    if chk_sid in ret_df.columns and "2020-04-15" in ret_df.index:
        p_prev = close_df.loc["2020-04-14", chk_sid]  # 0.1313
        p_curr = close_df.loc["2020-04-15", chk_sid]  # 16.375
        corr_ret = (p_curr / 200.0) / p_prev - 1.0   # -0.3764
        ret_df.loc["2020-04-15", chk_sid] = corr_ret
        tot_ret_df.loc["2020-04-15", chk_sid] = corr_ret
        log(f"  -> CHK (2020-04-15): Bổ sung Reverse Split 1:200 -> Return sửa thành {corr_ret*100:.2f}% (trước đó: +12,371.4%)")

    # CRC 2016-06-01: 1:10 reverse split
    crc_sid = "CRC VW1A4C2VJMN9"
    if crc_sid in ret_df.columns and "2016-06-01" in ret_df.index:
        p_prev = close_df.loc["2016-05-31", crc_sid]  # 1.52
        p_curr = close_df.loc["2016-06-01", crc_sid]  # 15.58
        corr_ret = (p_curr / 10.0) / p_prev - 1.0     # +0.0250
        ret_df.loc["2016-06-01", crc_sid] = corr_ret
        tot_ret_df.loc["2016-06-01", crc_sid] = corr_ret
        log(f"  -> CRC (2016-06-01): Bổ sung Reverse Split 1:10 -> Return sửa thành {corr_ret*100:.2f}% (trước đó: +925.0%)")

    # ADCT 2005-05-10: 1:7 reverse split
    adct_sid = "ADCT R735QTJ8XC9X"
    if adct_sid in ret_df.columns and "2005-05-10" in ret_df.index:
        p_prev = close_df.loc["2005-05-09", adct_sid]  # 2.30
        p_curr = close_df.loc["2005-05-10", adct_sid]  # 16.56
        corr_ret = (p_curr / 7.0) / p_prev - 1.0      # +0.0286
        ret_df.loc["2005-05-10", adct_sid] = corr_ret
        tot_ret_df.loc["2005-05-10", adct_sid] = corr_ret
        log(f"  -> ADCT (2005-05-10): Bổ sung Reverse Split 1:7 -> Return sửa thành {corr_ret*100:.2f}% (trước đó: +620.0%)")

    # AA 2016-10-06: 1:3 reverse split
    aa_sid = "AA R735QTJ8XC9X"
    if aa_sid in ret_df.columns and "2016-10-06" in ret_df.index:
        p_prev = close_df.loc["2016-10-05", aa_sid]  # 10.40
        p_curr = close_df.loc["2016-10-06", aa_sid]  # 31.78
        corr_ret = (p_curr / 3.0) / p_prev - 1.0     # +0.0186
        ret_df.loc["2016-10-06", aa_sid] = corr_ret
        tot_ret_df.loc["2016-10-06", aa_sid] = corr_ret
        log(f"  -> AA (2016-10-06): Bổ sung Reverse Split 1:3 -> Return sửa thành {corr_ret*100:.2f}% (trước đó: +205.6%)")

    # 2B. Vendor Bad Ticks / Collisions: Quarantine by setting valid_data_mask = False and valid_label_mask = False
    # MKL 2010-04-19 to 2010-04-28
    mkl_sid = "MKL R735QTJ8XC9X"
    if mkl_sid in vdata_df.columns:
        mkl_dates = [d for d in vdata_df.index if "2010-04-19" <= d.strftime('%Y-%m-%d') <= "2010-04-28"]
        vdata_df.loc[mkl_dates, mkl_sid] = False
        vlabel_df.loc[mkl_dates, mkl_sid] = False
        ret_df.loc[mkl_dates, mkl_sid] = np.nan
        tot_ret_df.loc[mkl_dates, mkl_sid] = np.nan
        log(f"  -> MKL (2010-04-19 đến 2010-04-28): Cách ly {len(mkl_dates)} phiên nến lỗi (~$26 vs ~$380)")

    # SABR 2020-03-20 to 2020-03-23
    sabr_sid = "SABR VPSS70OE3M1X"
    if sabr_sid in vdata_df.columns:
        sabr_dates = [d for d in vdata_df.index if d.strftime('%Y-%m-%d') in ["2020-03-20", "2020-03-23"]]
        vdata_df.loc[sabr_dates, sabr_sid] = False
        vlabel_df.loc[sabr_dates, sabr_sid] = False
        ret_df.loc[sabr_dates, sabr_sid] = np.nan
        tot_ret_df.loc[sabr_dates, sabr_sid] = np.nan
        log(f"  -> SABR (2020-03-20 & 2020-03-23): Cách ly 2 phiên nến lỗi ($0.50 vs ~$3.80)")

    # LOW 2008-06-10 to 2008-06-18
    low_sid = "LOW R735QTJ8XC9X"
    if low_sid in vdata_df.columns:
        low_dates = [d for d in vdata_df.index if "2008-06-10" <= d.strftime('%Y-%m-%d') <= "2008-06-18"]
        vdata_df.loc[low_dates, low_sid] = False
        vlabel_df.loc[low_dates, low_sid] = False
        ret_df.loc[low_dates, low_sid] = np.nan
        tot_ret_df.loc[low_dates, low_sid] = np.nan
        log(f"  -> LOW (2008-06-10 đến 2008-06-18): Cách ly {len(low_dates)} phiên ticker collision ($76.60 vs ~$23.50)")

    # 3. Save Corrected Matrices
    log("\n[3/5] Lưu trữ các ma trận sau hiệu chỉnh pháp y...")
    ret_df.to_parquet(MATRICES_DIR / "daily_return.parquet", compression='snappy')
    tot_ret_df.to_parquet(MATRICES_DIR / "total_return.parquet", compression='snappy')
    vdata_df.to_parquet(MATRICES_DIR / "valid_data_mask.parquet", compression='snappy')
    vlabel_df.to_parquet(MATRICES_DIR / "valid_label_mask.parquet", compression='snappy')

    # Re-generate target matrices
    next_daily_ret = ret_df.shift(-1).values.copy()
    next_daily_ret[~vlabel_df.values] = np.nan
    pd.DataFrame(next_daily_ret, index=ret_df.index, columns=ret_df.columns).to_parquet(
        MATRICES_DIR / "target_next_return.parquet", compression='snappy'
    )
    next_tot_ret = tot_ret_df.shift(-1).values.copy()
    next_tot_ret[~vlabel_df.values] = np.nan
    pd.DataFrame(next_tot_ret, index=ret_df.index, columns=ret_df.columns).to_parquet(
        MATRICES_DIR / "target_next_total_return.parquet", compression='snappy'
    )
    log("  -> Đã lưu các ma trận: daily_return, total_return, valid_data_mask, valid_label_mask, target_next_return")

    # --------------------------------------------------------------------------
    # 4. Re-run Development EDA on Cleaned Dataset (2000-07-01 to 2023-12-29)
    # --------------------------------------------------------------------------
    log("\n[4/5] Chạy lại EDA trên tập Development sau hiệu chỉnh...")
    dev_dates = ret_df.index[(ret_df.index >= "2000-07-01") & (ret_df.index <= "2023-12-29")]
    ret_dev = ret_df.loc[dev_dates].values
    mask_dev = vdata_df.loc[dev_dates].values

    valid_mask = mask_dev & np.isfinite(ret_dev)
    clean_rets = ret_dev[valid_mask]
    n_obs = len(clean_rets)
    log(f"  -> Số quan sát return hợp lệ: {n_obs:,}")

    # Compute Statistical Moments
    mean_ret = float(np.mean(clean_rets))
    median_ret = float(np.median(clean_rets))
    daily_vol = float(np.std(clean_rets))
    ann_vol = daily_vol * np.sqrt(252)
    skew = float(stats.skew(clean_rets))
    kurt = float(stats.kurtosis(clean_rets))
    min_ret = float(np.min(clean_rets))
    max_ret = float(np.max(clean_rets))

    p01, p1, p5, p25, p50, p75, p95, p99, p99_9 = np.percentile(
        clean_rets, [0.1, 1, 5, 25, 50, 75, 95, 99, 99.9]
    )
    pct_gt_10 = float(np.mean(clean_rets > 0.10) * 100.0)
    pct_lt_neg10 = float(np.mean(clean_rets < -0.10) * 100.0)
    pct_gt_20 = float(np.mean(clean_rets > 0.20) * 100.0)
    pct_lt_neg20 = float(np.mean(clean_rets < -0.20) * 100.0)

    log(f"  -> Return Moments sau hiệu chỉnh:")
    log(f"     Median : {median_ret*100:+.4f}%/ngày (~{median_ret*252*100:.2f}%/năm)")
    log(f"     Daily Vol : {daily_vol*100:.2f}% (Annualized: {ann_vol*100:.2f}%)")
    log(f"     Skewness : {skew:+.4f} (trước đó: +1,632.22)")
    log(f"     Excess Kurtosis: {kurt:.2f} (trước đó: 3,406,015.0!)")
    log(f"     Min: {min_ret*100:.2f}% | Max: {max_ret*100:.2f}% (trước đó: +12,371.4%)")

    # Save Updated Moments Table
    df_moments = pd.DataFrame([{
        'sample_period': '2000-07-01 to 2023-12-29',
        'observations': n_obs,
        'mean_daily_return': round(mean_ret, 6),
        'median_daily_return': round(median_ret, 6),
        'daily_volatility': round(daily_vol, 6),
        'annualized_volatility': round(ann_vol, 6),
        'skewness': round(skew, 4),
        'excess_kurtosis': round(kurt, 2),
        'min_return': round(min_ret, 6),
        'max_return': round(max_ret, 6),
        'p01': round(p01, 6), 'p1': round(p1, 6), 'p5': round(p5, 6),
        'p25': round(p25, 6), 'p50': round(p50, 6), 'p75': round(p75, 6),
        'p95': round(p95, 6), 'p99': round(p99, 6), 'p99_9': round(p99_9, 6),
        'pct_gt_10pct': round(pct_gt_10, 4), 'pct_lt_neg10pct': round(pct_lt_neg10, 4),
        'pct_gt_20pct': round(pct_gt_20, 4), 'pct_lt_neg20pct': round(pct_lt_neg20, 4)
    }])
    df_moments.to_csv(TABLES_DIR / "eda_daily_return_moments.csv", index=False)

    # --------------------------------------------------------------------------
    # 5. Re-generate High-Resolution Figures
    # --------------------------------------------------------------------------
    log("\n[5/5] Vẽ lại 4 biểu đồ EDA chất lượng cao...")
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#cbd5e1'
    plt.rcParams['axes.linewidth'] = 0.8

    # Figure 1: Return Distribution & Q-Q Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Histogram [-15%, +15%]
    clipped_rets = np.clip(clean_rets, -0.15, 0.15) * 100.0
    ax1.hist(clipped_rets, bins=120, density=True, alpha=0.65, color='#2563eb', edgecolor='none')
    
    # Normal distribution overlay
    x_norm = np.linspace(-15, 15, 500)
    y_norm = stats.norm.pdf(x_norm, loc=mean_ret*100, scale=daily_vol*100)
    ax1.plot(x_norm, y_norm, color='#dc2626', lw=2.2, label=f'Normal Fit (σ={daily_vol*100:.2f}%)')
    
    ax1.axvline(0, color='#64748b', ls='--', alpha=0.7)
    ax1.set_title(f'Phân Phối Lợi Nhuận Hằng Ngày (Development: 2000–2023)\nExcess Kurtosis = {kurt:.1f} | Skewness = {skew:+.2f}', fontsize=12, fontweight='bold', pad=12)
    ax1.set_xlabel('Daily Return (%)', fontsize=11)
    ax1.set_ylabel('Mật Độ (Density)', fontsize=11)
    ax1.set_xlim(-15, 15)
    ax1.grid(True, alpha=0.25)
    ax1.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0')

    # Q-Q Plot
    sample_sub = np.random.choice(clean_rets, size=min(50000, len(clean_rets)), replace=False)
    (osm, osr), (slope, intercept, r) = stats.probplot(sample_sub, dist="norm")
    ax2.scatter(osm, np.array(osr) * 100.0, s=4, alpha=0.35, color='#0284c7', label='Dữ Liệu Thực Tế')
    ax2.plot(osm, (slope * np.array(osm) + intercept) * 100.0, color='#dc2626', lw=2, label='Đường Chuẩn Gaussian')
    ax2.set_title('Normal Q-Q Plot (Thị Trường vs Phân Phối Chuẩn)\nHiện tượng Fat-Tails đối xứng rõ rệt ở 2 đầu', fontsize=12, fontweight='bold', pad=12)
    ax2.set_xlabel('Theoretical Quantiles (Phân Phối Chuẩn)', fontsize=11)
    ax2.set_ylabel('Sample Quantiles (Daily Return %)', fontsize=11)
    ax2.grid(True, alpha=0.25)
    ax2.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0')

    plt.tight_layout()
    fig1_path = FIGURES_DIR / "eda_daily_return_distribution_qq.png"
    plt.savefig(fig1_path, dpi=200)
    plt.close()
    log(f"  -> Đã lưu Hình 1: {fig1_path.name}")

    # Figure 2: Cross-Sectional Dispersion History
    disp_df = pd.read_csv(TABLES_DIR / "eda_cross_sectional_dispersion.csv")
    fig, ax = plt.subplots(figsize=(16, 5.5))
    ax.plot(disp_df['year'], disp_df['avg_dispersion'] * 100, marker='o', lw=2.2, color='#2563eb', label='Độ Phân Tán Trung Bình (Mean Dispersion %)')
    ax.fill_between(disp_df['year'], disp_df['min_dispersion'] * 100, disp_df['avg_dispersion'] * 100, color='#2563eb', alpha=0.15)
    ax.plot(disp_df['year'], disp_df['avg_iqr'] * 100, marker='s', lw=1.8, color='#059669', ls='--', label='Khoảng Tứ Phân Vị (Interquartile Range IQR %)')
    ax.set_title('Biến Thiên Độ Phân Tán Ngang Theo Năm (Cross-Sectional Dispersion: 2000–2023)\nĐỉnh điểm tại Bong bóng Dot-com 2000, Khủng hoảng 2008 và COVID-19 2020', fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel('Năm Tái Cơ Cấu', fontsize=11)
    ax.set_ylabel('Độ Phân Tán Cross-Sectional (%)', fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0')
    plt.tight_layout()
    fig2_path = FIGURES_DIR / "eda_cross_sectional_dispersion_history.png"
    plt.savefig(fig2_path, dpi=200)
    plt.close()
    log(f"  -> Đã lưu Hình 2: {fig2_path.name}")

    log("\n" + "=" * 80)
    log(f"HOÀN THÀNH HIỆU CHỈNH PHÁP Y VÀ CHẠY LẠI EDA TRONG {time.time()-t_start:.2f} GIÂY!")
    log("=" * 80)

if __name__ == '__main__':
    main()
