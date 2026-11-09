# -*- coding: utf-8 -*-
"""
scripts/01_pipeline/14_feature_eda.py
======================================
Executes comprehensive Exploratory Data Analysis (EDA) on the 16-feature Tier 3
Feature Store across the Development period (2000-07-01 to 2023-12-29).

Analyses performed:
1. Coverage Analysis:
   - Daily, annual, and overall coverage metrics with active membership denominator.
2. Distributional Metrics & Outlier Profiling:
   - Mean, std, skewness, kurtosis, quantiles (min, 1%, 5%, 25%, 50%, 75%, 95%, 99%, max).
   - Extreme outlier identification (IQR method).
   - Strictly NO clipping, winsorizing, or scaling applied at this stage.
3. Rigorous Mutually-Exclusive NaN Decomposition:
   - Evaluates true feature lookback windows (e.g. [T-252, T-21] for mom_12m_skip_1m).
   - Categories: bad quality at T, lack of history (IPO/listing), window defect/halts,
     zero denominator / invalid inputs, RSI state interruption, unclassified.
   - Validates that category sum matches total membership NaNs exactly.
4. Cross-Sectional Pairwise Correlation:
   - Daily cross-sectional Pearson and Spearman rank correlation computed across
     valid stock pairs on each date T (min_periods=30), without zero substitution.
   - Separate aggregation over valid dates per pair.
   - Stores pairwise metadata: valid days count, stock count distribution (min, mean, max).
5. Comprehensive Visualizations:
   - fig1_coverage_by_feature_and_year.png
   - fig2_daily_coverage_timeseries.png
   - fig3_feature_distribution_histograms.png
   - fig4_cross_sectional_correlation_spearman.png
   - fig5_cross_sectional_correlation_pearson.png
   - fig6_market_regimes_volatility_and_liquidity.png

Zero target return leakage, zero IC computation at this stage.
"""

import sys
import gc
import json
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data.matrix_loader import (
    load_matrix,
    load_bar_quality_mask,
    load_field_quality_mask,
    load_layer1_mask,
)
from src.features.nan_classifier import classify_feature_nans

FEATURES_DIR = ROOT_DIR / "data" / "processed" / "features"
REPORTS_DIR = ROOT_DIR / "docs" / "reports" / "feature_eda"
FIGURES_DIR = REPORTS_DIR / "figures"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DEV_START_DATE = "2000-07-01"
DEV_END_DATE = "2023-12-29"

ALL_FEATURES = [
    "ret_1d", "ret_5d", "ret_20d", "ret_60d", "mom_12m_skip_1m",
    "vol_realized_20d", "vol_realized_60d", "vol_parkinson_20d", "downside_deviation_20d",
    "amihud_illiq_20d", "volume_ratio_5_20", "log_dollar_volume_20d",
    "ret_intraday", "ret_overnight", "rsi_14d", "bollinger_pct_b_20d",
]

LOOKBACK_SPECS = {
    "ret_1d": (1, 1),
    "ret_5d": (5, 4),
    "ret_20d": (20, 16),
    "ret_60d": (60, 48),
    "mom_12m_skip_1m": (252, 232),
    "vol_realized_20d": (20, 16),
    "vol_realized_60d": (60, 48),
    "vol_parkinson_20d": (20, 16),
    "downside_deviation_20d": (20, 16),
    "amihud_illiq_20d": (20, 16),
    "volume_ratio_5_20": (20, 16),
    "log_dollar_volume_20d": (20, 16),
    "ret_intraday": (1, 1),
    "ret_overnight": (2, 2),
    "rsi_14d": (14, 14),
    "bollinger_pct_b_20d": (20, 16),
}


def run_eda():
    print("=" * 80)
    print("BẮT ĐẦU EXPLORATORY DATA ANALYSIS (EDA) TRÊN TẬP DEVELOPMENT (2000-2023)")
    print("=" * 80)
    t_start = time.time()

    # 1. Load masks and reference matrices
    print("\n1. Nạp mặt nạ rổ strict_membership_mask và bar_quality_mask...")
    strict_mem = load_layer1_mask(strict=True, dev_only=True, include_warmup=False)
    bar_quality_dev = load_bar_quality_mask(dev_only=True, include_warmup=False)
    dates = strict_mem.index
    sids = strict_mem.columns
    n_sessions, n_sids = strict_mem.shape
    daily_member_counts = strict_mem.sum(axis=1)
    total_member_cells = int(daily_member_counts.sum())
    total_cells = n_sessions * n_sids
    non_member_cells = total_cells - total_member_cells

    print(f"   Tổng số ô: {total_cells:,} ({n_sessions} phiên x {n_sids} mã)")
    print(f"   Ô thuộc membership: {total_member_cells:,} ({total_member_cells / total_cells * 100:.2f}%)")
    print(f"   Ô ngoài membership: {non_member_cells:,} ({non_member_cells / total_cells * 100:.2f}%)")

    # Load warmup matrices for exact lookback inspection
    print("   Nạp ma trận warmup để phân tích nguyên nhân NaN chính xác theo cửa sổ...")
    bar_quality_warm_df = load_bar_quality_mask(dev_only=True, include_warmup=True)
    field_open_quality_warm_df = load_field_quality_mask("adj_open", dev_only=True, include_warmup=True)
    field_low_quality_warm_df = load_field_quality_mask("adj_low", dev_only=True, include_warmup=True)
    field_high_quality_warm_df = load_field_quality_mask("adj_high", dev_only=True, include_warmup=True)

    input_mats_warm = {
        "adj_close": load_matrix("adj_close", dev_only=True, include_warmup=True),
        "adj_open": load_matrix("adj_open", dev_only=True, include_warmup=True),
        "adj_high": load_matrix("adj_high", dev_only=True, include_warmup=True),
        "adj_low": load_matrix("adj_low", dev_only=True, include_warmup=True),
        "adj_volume": load_matrix("adj_volume", dev_only=True, include_warmup=True),
        "close": load_matrix("close", dev_only=True, include_warmup=True),
        "open": load_matrix("open", dev_only=True, include_warmup=True),
        "volume": load_matrix("volume", dev_only=True, include_warmup=True),
        "daily_return": load_matrix("daily_return", dev_only=True, include_warmup=True),
    }
    field_q_masks_warm = {
        "adj_open": field_open_quality_warm_df,
        "adj_low": field_low_quality_warm_df,
        "adj_high": field_high_quality_warm_df,
    }

    # 2. Load feature matrices and compute coverage & distributions
    print("\n2. Tính toán độ phủ, phân tách NaN chính xác và thống kê phân phối cho 16 features...")
    feature_matrices = {}
    coverage_annual_dict = {}
    daily_coverage_df = pd.DataFrame(index=dates)
    dist_records = []
    nan_records = []

    for idx, feat_name in enumerate(ALL_FEATURES, start=1):
        t_feat = time.time()
        feat_path = FEATURES_DIR / f"{feat_name}.parquet"
        df = pd.read_parquet(feat_path)
        feature_matrices[feat_name] = df

        # Daily valid counts
        daily_valid = df.notna().sum(axis=1)
        daily_cov = (daily_valid / daily_member_counts) * 100.0
        daily_coverage_df[feat_name] = daily_cov

        # Annual coverage
        df_years = daily_cov.groupby(dates.year).mean()
        coverage_annual_dict[feat_name] = df_years

        # Overall coverage metrics
        valid_cells = int(daily_valid.sum())
        nan_inside_mem = total_member_cells - valid_cells
        cov_overall = (valid_cells / total_member_cells) * 100.0

        # Rigorous Mutually-Exclusive NaN Decomposition via Shared Production Engine
        nan_res = classify_feature_nans(
            feature_name=feat_name,
            feature_matrix=df,
            input_matrices=input_mats_warm,
            bar_quality_mask=bar_quality_warm_df,
            membership_mask=strict_mem,
            field_quality_masks=field_q_masks_warm,
        )
        nan_records.append(nan_res)

        # Distribution metrics on valid cells
        flat_vals = df.values[df.notna().values]
        n_obs = len(flat_vals)
        mean_v = float(np.mean(flat_vals))
        std_v = float(np.std(flat_vals, ddof=1))
        skew_v = float(stats.skew(flat_vals))
        kurt_v = float(stats.kurtosis(flat_vals))

        qs = np.percentile(flat_vals, [0, 1, 5, 25, 50, 75, 95, 99, 100])
        iqr = qs[5] - qs[3]
        lower_bound = qs[3] - 3.0 * iqr
        upper_bound = qs[5] + 3.0 * iqr
        extreme_outliers = np.sum((flat_vals < lower_bound) | (flat_vals > upper_bound))
        outlier_pct = (extreme_outliers / n_obs) * 100.0

        dist_records.append({
            "feature": feat_name,
            "n_observations": n_obs,
            "mean": round(mean_v, 6),
            "std": round(std_v, 6),
            "skewness": round(skew_v, 4),
            "kurtosis": round(kurt_v, 4),
            "min": round(float(qs[0]), 6),
            "p01": round(float(qs[1]), 6),
            "p05": round(float(qs[2]), 6),
            "q25": round(float(qs[3]), 6),
            "median_p50": round(float(qs[4]), 6),
            "q75": round(float(qs[5]), 6),
            "p95": round(float(qs[6]), 6),
            "p99": round(float(qs[7]), 6),
            "max": round(float(qs[8]), 6),
            "iqr": round(float(iqr), 6),
            "extreme_outliers_count": int(extreme_outliers),
            "extreme_outliers_pct": round(float(outlier_pct), 3),
        })

        print(f"   [{idx:02d}/16] {feat_name:<22}: Cov={cov_overall:6.2f}% | Mean={mean_v:10.4f} | Med={qs[4]:10.4f} | Std={std_v:8.4f} | NaN Match={nan_res['decomposition_matches_total']} ({time.time() - t_feat:.2f}s)")

    # Save coverage by year table
    cov_annual_df = pd.DataFrame(coverage_annual_dict).round(2)
    cov_annual_df.index.name = "year"
    cov_annual_df.to_csv(REPORTS_DIR / "coverage_by_year.csv", encoding="utf-8")

    # Save distributions table
    dist_df = pd.DataFrame(dist_records)
    dist_df.to_csv(REPORTS_DIR / "feature_distributions.csv", index=False, encoding="utf-8")

    # Save NaN breakdown table
    nan_df = pd.DataFrame(nan_records)
    nan_df.to_csv(REPORTS_DIR / "nan_breakdown.csv", index=False, encoding="utf-8")

    # 3. Cross-Sectional Correlation Analysis
    print("\n3. Tính toán tương quan chéo ngang (Cross-Sectional Pearson & Spearman, N_min=30, không điền 0)...")
    t_corr = time.time()
    n_feats = len(ALL_FEATURES)

    # Accumulators for pairwise correlation matrices
    spearman_sum = np.zeros((n_feats, n_feats), dtype=np.float64)
    pearson_sum = np.zeros((n_feats, n_feats), dtype=np.float64)
    valid_days_sp = np.zeros((n_feats, n_feats), dtype=np.int32)
    valid_days_pe = np.zeros((n_feats, n_feats), dtype=np.int32)

    obs_min = np.full((n_feats, n_feats), 999999, dtype=np.int32)
    obs_max = np.zeros((n_feats, n_feats), dtype=np.int32)
    obs_sum = np.zeros((n_feats, n_feats), dtype=np.float64)

    # Stack features into 3D array: [days, stocks, features]
    stacked_features = np.stack([feature_matrices[f].values for f in ALL_FEATURES], axis=-1)

    for d_idx in range(n_sessions):
        day_mem = strict_mem.values[d_idx]
        if np.sum(day_mem) < 30:
            continue

        day_slice = stacked_features[d_idx, day_mem, :]  # [n_members, 16]
        df_day = pd.DataFrame(day_slice, columns=ALL_FEATURES)

        pe = df_day.corr(method="pearson", min_periods=30).values
        sp = df_day.corr(method="spearman", min_periods=30).values

        valid_pe = np.isfinite(pe)
        valid_sp = np.isfinite(sp)

        pearson_sum[valid_pe] += pe[valid_pe]
        valid_days_pe[valid_pe] += 1

        spearman_sum[valid_sp] += sp[valid_sp]
        valid_days_sp[valid_sp] += 1

        # Track overlap stock counts
        notna_m = np.isfinite(day_slice).astype(np.int32)
        overlap = notna_m.T @ notna_m

        obs_sum[valid_sp] += overlap[valid_sp]
        obs_min[valid_sp] = np.minimum(obs_min[valid_sp], overlap[valid_sp])
        obs_max[valid_sp] = np.maximum(obs_max[valid_sp], overlap[valid_sp])

    mean_spearman = np.full((n_feats, n_feats), np.nan, dtype=np.float64)
    mean_pearson = np.full((n_feats, n_feats), np.nan, dtype=np.float64)

    for i in range(n_feats):
        for j in range(n_feats):
            if valid_days_sp[i, j] > 0:
                mean_spearman[i, j] = spearman_sum[i, j] / valid_days_sp[i, j]
            if valid_days_pe[i, j] > 0:
                mean_pearson[i, j] = pearson_sum[i, j] / valid_days_pe[i, j]

    df_spearman = pd.DataFrame(mean_spearman, index=ALL_FEATURES, columns=ALL_FEATURES).round(4)
    df_pearson = pd.DataFrame(mean_pearson, index=ALL_FEATURES, columns=ALL_FEATURES).round(4)

    df_spearman.to_csv(REPORTS_DIR / "spearman_correlation_matrix.csv", encoding="utf-8")
    df_pearson.to_csv(REPORTS_DIR / "pearson_correlation_matrix.csv", encoding="utf-8")

    # Pairwise metadata table
    pairwise_records = []
    for i in range(n_feats):
        for j in range(n_feats):
            f1 = ALL_FEATURES[i]
            f2 = ALL_FEATURES[j]
            v_days = int(valid_days_sp[i, j])
            min_stk = int(obs_min[i, j]) if v_days > 0 else 0
            max_stk = int(obs_max[i, j]) if v_days > 0 else 0
            mean_stk = round(float(obs_sum[i, j] / v_days), 1) if v_days > 0 else 0.0
            pairwise_records.append({
                "feature_1": f1,
                "feature_2": f2,
                "valid_days": v_days,
                "total_days": n_sessions,
                "pct_valid_days": round(float(v_days / n_sessions * 100.0), 2),
                "min_valid_stocks": min_stk,
                "mean_valid_stocks": mean_stk,
                "max_valid_stocks": max_stk,
                "mean_spearman": round(float(mean_spearman[i, j]), 4),
                "mean_pearson": round(float(mean_pearson[i, j]), 4),
            })
    df_meta = pd.DataFrame(pairwise_records)
    df_meta.to_csv(REPORTS_DIR / "pairwise_correlation_metadata.csv", index=False, encoding="utf-8")
    print(f"   -> Đã tính toán và lưu metadata qua {n_sessions} phiên trong {time.time() - t_corr:.2f}s")

    # 4. Generate Figures
    print("\n4. Tạo các biểu đồ trực quan hóa chuẩn học thuật...")

    # Fig 1: Annual Coverage Heatmap
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
    cax = ax.imshow(cov_annual_df.T.values, cmap="YlGnBu", aspect="auto", vmin=70, vmax=100)
    ax.set_xticks(range(len(cov_annual_df.index)))
    ax.set_xticklabels(cov_annual_df.index, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n_feats))
    ax.set_yticklabels(ALL_FEATURES, fontsize=9)
    ax.set_title("Độ Phủ Hàng Năm (% Membership) của 16 Features trên Development (2000–2023)", fontsize=13, pad=12, fontweight="bold")
    cbar = fig.colorbar(cax, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("Coverage (%)", fontsize=10)
    plt.tight_layout()
    fig1_path = FIGURES_DIR / "fig1_coverage_by_feature_and_year.png"
    plt.savefig(fig1_path)
    plt.close()
    print(f"   -> Đã lưu {fig1_path.name}")

    # Fig 2: Daily Coverage Time Series
    fig, ax = plt.subplots(figsize=(14, 6), dpi=200)
    sample_features = ["ret_1d", "ret_20d", "mom_12m_skip_1m", "vol_realized_20d", "amihud_illiq_20d", "rsi_14d"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for sf, c in zip(sample_features, colors):
        ax.plot(dates, daily_coverage_df[sf], label=sf, color=c, alpha=0.85, linewidth=1.1)
    ax.set_ylim(60, 101)
    ax.set_ylabel("Coverage (% Membership)", fontsize=10)
    ax.set_xlabel("Năm Giao Dịch", fontsize=10)
    ax.set_title("Chuỗi Thời Gian Độ Phủ Hàng Ngày (2000–2023) theo Nhóm Đặc Trưng Đại Diện", fontsize=12, pad=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
    plt.tight_layout()
    fig2_path = FIGURES_DIR / "fig2_daily_coverage_timeseries.png"
    plt.savefig(fig2_path)
    plt.close()
    print(f"   -> Đã lưu {fig2_path.name}")

    # Fig 3: Distribution Histograms (4x4 grid)
    fig, axes = plt.subplots(4, 4, figsize=(18, 14), dpi=200)
    axes = axes.flatten()
    for idx, f_name in enumerate(ALL_FEATURES):
        ax = axes[idx]
        vals = feature_matrices[f_name].values[feature_matrices[f_name].notna().values]
        p01, p99 = np.percentile(vals, [1, 99])
        vals_clipped = np.clip(vals, p01, p99)

        ax.hist(vals_clipped, bins=40, color="#2b5c8f", alpha=0.75, edgecolor="none", density=True)
        ax.axvline(np.median(vals), color="#d62728", linestyle="--", linewidth=1.2, label=f"Median: {np.median(vals):.3f}")
        ax.set_title(f_name, fontsize=10, fontweight="bold")
        ax.tick_params(axis="both", labelsize=8)
        ax.legend(fontsize=7, loc="upper right")
    plt.suptitle("Phân Phối Thực Nghiệm 16 Features trên Development (Kẹp p01–p99 cho Trực Quan Hóa)", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout()
    fig3_path = FIGURES_DIR / "fig3_feature_distribution_histograms.png"
    plt.savefig(fig3_path)
    plt.close()
    print(f"   -> Đã lưu {fig3_path.name}")

    # Fig 4: Cross-Sectional Spearman Correlation Heatmap
    fig, ax = plt.subplots(figsize=(12, 10), dpi=200)
    cax = ax.imshow(df_spearman.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(n_feats))
    ax.set_yticks(range(n_feats))
    ax.set_xticklabels(ALL_FEATURES, rotation=90, fontsize=9)
    ax.set_yticklabels(ALL_FEATURES, fontsize=9)
    for i in range(n_feats):
        for j in range(n_feats):
            val = df_spearman.values[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7)
    ax.set_title("Ma Trận Tương Quan Thứ Hạng Spearman Trung Bình Hàng Ngày (2000–2023, N_min=30)", fontsize=12, pad=12, fontweight="bold")
    fig.colorbar(cax, ax=ax, fraction=0.03, pad=0.02)
    plt.tight_layout()
    fig4_path = FIGURES_DIR / "fig4_cross_sectional_correlation_spearman.png"
    plt.savefig(fig4_path)
    plt.close()
    print(f"   -> Đã lưu {fig4_path.name}")

    # Fig 5: Cross-Sectional Pearson Correlation Heatmap
    fig, ax = plt.subplots(figsize=(12, 10), dpi=200)
    cax = ax.imshow(df_pearson.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(n_feats))
    ax.set_yticks(range(n_feats))
    ax.set_xticklabels(ALL_FEATURES, rotation=90, fontsize=9)
    ax.set_yticklabels(ALL_FEATURES, fontsize=9)
    for i in range(n_feats):
        for j in range(n_feats):
            val = df_pearson.values[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7)
    ax.set_title("Ma Trận Tương Quan Tuyến Tính Pearson Trung Bình Hàng Ngày (2000–2023, N_min=30)", fontsize=12, pad=12, fontweight="bold")
    fig.colorbar(cax, ax=ax, fraction=0.03, pad=0.02)
    plt.tight_layout()
    fig5_path = FIGURES_DIR / "fig5_cross_sectional_correlation_pearson.png"
    plt.savefig(fig5_path)
    plt.close()
    print(f"   -> Đã lưu {fig5_path.name}")

    # Fig 6: Market Regimes Volatility and Liquidity Tracking
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), dpi=200, sharex=True)
    med_vol_real = feature_matrices["vol_realized_20d"].median(axis=1)
    med_vol_park = feature_matrices["vol_parkinson_20d"].median(axis=1)
    med_amihud = feature_matrices["amihud_illiq_20d"].median(axis=1)

    ax1.plot(dates, med_vol_real, label="Median Realized Vol 20d", color="#d62728", linewidth=1.1, alpha=0.9)
    ax1.plot(dates, med_vol_park, label="Median Parkinson Vol 20d", color="#ff7f0e", linewidth=1.1, alpha=0.9)
    ax1.set_ylabel("Biến Động Ngày (Daily Vol)", fontsize=10)
    ax1.set_title("Diễn Biến Biến Động Trung Vị Thị Trường Qua Các Khủng Hoảng (2000–2023)", fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=9)

    regimes = [
        ("2000-09-01", "2002-10-09", "Dot-com Bust", "#7f7f7f"),
        ("2007-10-09", "2009-03-09", "2008 GFC", "#bcbd22"),
        ("2020-02-19", "2020-04-30", "COVID Shock", "#17becf"),
        ("2022-01-03", "2022-10-12", "2022 Inflation/Rate Hikes", "#e377c2"),
    ]
    for start_r, end_r, label_r, col_r in regimes:
        ax1.axvspan(pd.to_datetime(start_r), pd.to_datetime(end_r), color=col_r, alpha=0.15, label=f"Regime: {label_r}")
        ax2.axvspan(pd.to_datetime(start_r), pd.to_datetime(end_r), color=col_r, alpha=0.15)

    ax2.plot(dates, med_amihud, label="Median Amihud Illiquidity 20d", color="#2ca02c", linewidth=1.1, alpha=0.9)
    ax2.set_ylabel("Amihud Illiquidity (Scale 1e6)", fontsize=10)
    ax2.set_xlabel("Năm Giao Dịch", fontsize=10)
    ax2.set_title("Diễn Biến Thanh Khoản Trung Vị Thị Trường Qua Thời Gian", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    fig6_path = FIGURES_DIR / "fig6_market_regimes_volatility_and_liquidity.png"
    plt.savefig(fig6_path)
    plt.close()
    print(f"   -> Đã lưu {fig6_path.name}")

    print("\n" + "=" * 80)
    print("HOÀN TẤT EDA FEATURES DEVELOPMENT THÀNH CÔNG!")
    print(f"Tổng thời gian: {time.time() - t_start:.2f}s")
    print(f"Đã lưu các bảng thống kê vào: {REPORTS_DIR.relative_to(ROOT_DIR)}")
    print(f"Đã lưu 6 biểu đồ trực quan vào: {FIGURES_DIR.relative_to(ROOT_DIR)}")
    print("=" * 80)


if __name__ == "__main__":
    run_eda()
