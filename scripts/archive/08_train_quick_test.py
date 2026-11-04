"""
QUICK TEST BASELINE MODEL — LIGHTGBM ON RUSSELL 1000 PIT
========================================================
- Dữ liệu: data/processed/features/feature_store_long.parquet (Sạch PIT)
- Features: 13 Core Alphas (đã khử đa cộng tuyến & chuẩn hóa hướng)
- Target: target_return_rank (Cross-Sectional Percentile Rank [0, 1])
- Split:
    + Train Window: 2018-01-01 -> 2022-12-31 (5 năm)
    + Purge Gap:    5 ngày giao dịch (loại bỏ forward overlap)
    + Val Window:   2023-01-01 -> 2023-12-31 (1 năm In-Sample cuối cùng)
- Đánh giá: Daily Cross-Sectional Rank IC (Spearman) trên tập Validation
"""
import sys
import time
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import lightgbm as lgb

FEATURE_STORE_PATH = "data/processed/features/feature_store_long.parquet"

# 13 Core Alphas tinh hoa đã chọn lọc từ bước T6
CORE_FEATURES = [
    "close_to_high",          # Intraday momentum bias (+)
    "ret_252d",               # Long-term momentum (+)
    "ret_1d",                 # Short-term reversal (cần đảo dấu nếu là raw)
    "close_to_vwap_5",        # Liquidity-weighted mean reversion
    "vol_zscore_20",          # Volume shock (+)
    "vol_ratio_5_20",         # Short/medium volume surge (+)
    "ret_20d",                # 1-month momentum / reversal
    "close_to_sma_200",       # Macro trend signal (+)
    "macd_hist_norm",         # Trend exhaustion
    "rsi_14",                 # Oversold / Overbought
    "realized_vol_20d",       # Volatility risk
    "hl_spread",              # Intraday range uncertainty
    "ret_5d_rank"             # Multi-day reversal rank
]

TARGET_COL = "target_return_rank"

def compute_daily_rank_ic(df_val: pd.DataFrame, pred_col: str, target_col: str) -> pd.Series:
    """Tính Spearman Rank IC theo từng ngày giao dịch (Cross-Sectional)."""
    ics = {}
    for dt, group in df_val.groupby("date"):
        sub = group[[pred_col, target_col]].dropna()
        if len(sub) >= 20:  # Đảm bảo đủ số lượng cổ phiếu để rank có ý nghĩa
            corr, _ = spearmanr(sub[pred_col], sub[target_col])
            if not np.isnan(corr):
                ics[dt] = corr
    return pd.Series(ics)

def main():
    print("=" * 70)
    print("  🚀 CHẠY THỬ NGHIỆM HUẤN LUYỆN MODEL LIGHTGBM BASELINE")
    print("=" * 70)

    t0 = time.time()
    print("\n[1/4] Đang nạp Feature Store...")
    # Chỉ load các cột cần thiết để tiết kiệm RAM và tăng tốc tối đa
    cols_to_load = ["date", "ticker", TARGET_COL] + CORE_FEATURES
    df = pd.read_parquet(FEATURE_STORE_PATH, columns=cols_to_load)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  ✓ Đã nạp {len(df):,} dòng ({time.time() - t0:.1f}s)")

    # Lọc bỏ các dòng NaN ở target (mã ngoài rổ hoặc không có forward return)
    df = df.dropna(subset=[TARGET_COL])

    print("\n[2/4] Phân chia Train / Validation (Purged Time-Series Split)...")
    # Train: 2018 - 2022 (5 năm)
    train_mask = (df["date"] >= "2018-01-01") & (df["date"] <= "2022-12-23") # Purge 5 ngày trước 2023
    val_mask = (df["date"] >= "2023-01-01") & (df["date"] <= "2023-12-31")

    df_train = df[train_mask].copy()
    df_val = df[val_mask].copy()

    X_train, y_train = df_train[CORE_FEATURES], df_train[TARGET_COL]
    X_val, y_val = df_val[CORE_FEATURES], df_val[TARGET_COL]

    print(f"  Tập Train (2018 - 2022): {len(X_train):,} mẫu (~{len(df_train['date'].unique())} ngày)")
    print(f"  Tập Val   (2023):        {len(X_val):,} mẫu (~{len(df_val['date'].unique())} ngày)")

    print("\n[3/4] Đang huấn luyện LightGBM Regressor...")
    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )

    t_train = time.time()
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)]
    )
    print(f"  ✓ Huấn luyện hoàn tất trong {time.time() - t_train:.1f} giây!")

    print("\n[4/4] Đánh giá hiệu năng dự báo trên tập Validation (Năm 2023)...")
    df_val["pred_rank"] = model.predict(X_val)

    # Tính Daily Rank IC
    daily_ic = compute_daily_rank_ic(df_val, "pred_rank", TARGET_COL)
    mean_ic = daily_ic.mean()
    std_ic = daily_ic.std()
    icir = mean_ic / (std_ic + 1e-9)
    pos_pct = (daily_ic > 0).mean() * 100

    print("-" * 55)
    print(f"  Mean Rank IC (Val 2023):  {mean_ic:+.5f}")
    print(f"  IC Volatility (Std):      {std_ic:.5f}")
    print(f"  ICIR (Annualized-like):   {icir:+.4f}")
    print(f"  Tỷ lệ ngày IC Dương (%):  {pos_pct:.1f}%")
    print("-" * 55)

    # So sánh với Benchmark Reversal 5D
    print("\n  📊 SO SÁNH VỚI BENCHMARK:")
    print(f"  - Reversal 5D (Công thức thầy năm 2023): IC = +0.00094")
    print(f"  - Model LightGBM (13 Core Alphas 2023): IC = {mean_ic:+.5f}")
    if mean_ic > 0.00094:
        print(f"  ==> 🟢 XUẤT SẮC! Mô hình vượt trội gấp {mean_ic / 0.00094:.1f} lần so với Benchmark!")
    else:
        print("  ==> 🟡 Cần tinh chỉnh thêm hyperparameters hoặc threshold.")

    # In Feature Importance
    print("\n  🔍 TOP ĐẶC TRƯNG QUAN TRỌNG NHẤT (FEATURE IMPORTANCE):")
    importance = pd.Series(model.feature_importances_, index=CORE_FEATURES).sort_values(ascending=False)
    for feat, imp in importance.items():
        print(f"    • {feat:<20}: {imp:>5} splits")

    print("\n" + "=" * 70)
    print("  ✅ HOÀN THÀNH CHẠY THỬ NGHIỆM!")
    print("=" * 70)

if __name__ == "__main__":
    main()
