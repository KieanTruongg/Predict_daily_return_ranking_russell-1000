"""
analyze_feature_correlation.py
--------------------------------
Nhiệm vụ:
  1. Đọc Feature Store In-Sample (2000-2023)
  2. Tính toán ma trận tương quan Cross-Sectional Spearman trung bình giữa 24 features
  3. Tìm ra các cặp feature bị đa cộng tuyến (trùng lặp thông tin cao: |corr| >= 0.60)
  4. Vẽ biểu đồ Heatmap trực quan lưu vào docs/Data report/phase2/figures/
  5. Xuất danh sách phân nhóm và đề xuất >10 Alphas tinh hoa nhất cho mô hình.
"""

import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = r"D:\A_Learning\HK1_2026-2027\CO3101 - Đồ án tổng hợp - ttnt\Predict_daily_return_rankings"
FEATURE_STORE_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "features", "feature_store_long.parquet")
OUT_DIR = os.path.join(PROJECT_ROOT, "docs", "Data report", "phase2", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# Danh sách features cần phân tích (các feature chính được tính ở Phase 2)
CANDIDATE_FEATURES = [
    "close_to_high",
    "ret_252d",
    "vol_zscore_20",
    "close_to_sma_200",
    "vol_ratio_5_20",
    "ret_60d",
    "close_to_sma_50",
    "rsi_14",
    "ret_20d",
    "bb_pct_b",
    "ret_10d",
    "macd_hist_norm",
    "close_to_sma_20",
    "realized_vol_5d",
    "hl_spread",
    "bb_bandwidth",
    "realized_vol_60d",
    "realized_vol_20d",
    "ret_5d",
    "ret_2d",
    "close_to_vwap_5",
    "ret_1d",
    "amihud_20d",
]

def main():
    print(f"[1/5] Loading Feature Store from: {FEATURE_STORE_PATH}")
    if not os.path.exists(FEATURE_STORE_PATH):
        print(f"Error: File not found at {FEATURE_STORE_PATH}")
        sys.exit(1)

    # Đọc chỉ các cột cần thiết để tối ưu RAM
    cols_to_load = ["date", "ticker"]
    # Kiểm tra cột có trong schema
    import pyarrow.parquet as pq
    schema_cols = pq.read_schema(FEATURE_STORE_PATH).names
    
    valid_features = [f for f in CANDIDATE_FEATURES if f in schema_cols]
    if "Reversal_5D" in schema_cols:
        valid_features.append("Reversal_5D")
    
    print(f"  Available features to analyze: {len(valid_features)}")
    df = pd.read_parquet(FEATURE_STORE_PATH, columns=cols_to_load + valid_features)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  Loaded {len(df):,} rows across {df['date'].nunique():,} trading days.")

    # [2/5] Lấy mẫu đại diện các ngày giao dịch để tính tương quan Cross-Sectional trung bình
    unique_dates = df["date"].drop_duplicates().sort_values().values
    # Lấy mẫu 1 ngày mỗi tuần (mỗi 5 ngày giao dịch) để tính nhanh và đại diện toàn bộ 24 năm
    sample_dates = unique_dates[::5]
    print(f"[2/5] Computing Cross-Sectional Spearman Correlation across {len(sample_dates)} sampled trading dates...")

    daily_corrs = []
    for d in sample_dates:
        sub = df[df["date"] == d][valid_features].dropna(how="all")
        if len(sub) >= 50:  # Đảm bảo đủ ít nhất 50 cổ phiếu trong ngày
            # Xếp hạng cross-sectional để tính Spearman
            ranked_sub = sub.rank(pct=True)
            corr_matrix = ranked_sub.corr(method="pearson")
            daily_corrs.append(corr_matrix)

    if not daily_corrs:
        print("Error: No valid dates found with enough data.")
        sys.exit(1)

    # Lấy trung bình ma trận tương quan theo thời gian (Time-series mean of daily CS correlation)
    mean_corr = pd.concat([d.stack(future_stack=True) for d in daily_corrs], axis=1).mean(axis=1).unstack()
    mean_corr = mean_corr.loc[valid_features, valid_features]

    # [3/5] Xuất file CSV
    corr_csv_path = os.path.join(OUT_DIR, "feature_correlation_matrix.csv")
    mean_corr.to_csv(corr_csv_path, float_format="%.4f")
    print(f"[3/5] Saved correlation matrix to: {corr_csv_path}")

    # Tìm các cặp tương quan cao (|corr| >= 0.60)
    high_pairs = []
    for i in range(len(valid_features)):
        for j in range(i + 1, len(valid_features)):
            f1, f2 = valid_features[i], valid_features[j]
            c = mean_corr.loc[f1, f2]
            if abs(c) >= 0.60:
                high_pairs.append({
                    "Feature_1": f1,
                    "Feature_2": f2,
                    "Correlation": c,
                    "Abs_Correlation": abs(c)
                })
    high_pairs_df = pd.DataFrame(high_pairs).sort_values("Abs_Correlation", ascending=False)
    high_pairs_csv = os.path.join(OUT_DIR, "feature_high_correlation_pairs.csv")
    high_pairs_df.to_csv(high_pairs_csv, index=False, float_format="%.4f")
    print(f"  Found {len(high_pairs_df)} pairs with |corr| >= 0.60. Saved to: {high_pairs_csv}")

    # [4/5] Vẽ Heatmap bằng Matplotlib
    print("[4/5] Plotting Correlation Heatmap...")
    n = len(valid_features)
    fig, ax = plt.subplots(figsize=(14, 12), dpi=200)

    cax = ax.imshow(mean_corr.values, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04, label="Average Cross-Sectional Spearman Correlation")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(valid_features, rotation=90, fontsize=9, ha="center")
    ax.set_yticklabels(valid_features, fontsize=9)

    # Thêm số vào các ô nếu ma trận vừa phải
    for i in range(n):
        for j in range(n):
            val = mean_corr.values[i, j]
            if not np.isnan(val) and abs(val) >= 0.50 and i != j:
                color = "white" if abs(val) > 0.70 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7, fontweight="bold")

    ax.set_title("Cross-Sectional Feature Correlation Matrix (In-Sample 2000-2023)\nAverage Daily Spearman Rank Correlation", fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()
    heatmap_png = os.path.join(OUT_DIR, "feature_correlation_heatmap.png")
    plt.savefig(heatmap_png, bbox_inches="tight")
    plt.close()
    print(f"  Saved heatmap image to: {heatmap_png}")

    # [5/5] In tóm tắt các cặp trùng lặp cao nhất
    print("\n--- TOP HIGH CORRELATION PAIRS (ĐA CỘNG TUYẾN / TRÙNG LẶP THÔNG TIN) ---")
    for idx, row in high_pairs_df.head(15).iterrows():
        print(f"  {row['Feature_1']} <--> {row['Feature_2']}: corr = {row['Correlation']:+.3f}")

if __name__ == "__main__":
    main()
