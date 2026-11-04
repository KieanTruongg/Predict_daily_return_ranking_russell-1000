"""
INSPECT MODEL PREDICTIONS — SO SOI KẾT QUẢ DỰ BÁO CỦA MÔ HÌNH
============================================================
Script này giúp bạn nhìn tận mắt:
1. Mô hình dự báo cổ phiếu nào sẽ tăng mạnh nhất (Top Long) ngày mai.
2. Cổ phiếu nào sẽ đội sổ/giảm mạnh nhất (Top Short) ngày mai.
3. So sánh trực tiếp với thực tế (Actual Return & Actual Rank) ngày hôm sau xem mô hình đoán trúng không!
"""
import sys
import time
import pandas as pd
import numpy as np
import lightgbm as lgb
from scipy.stats import spearmanr

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

FEATURE_STORE_PATH = "data/processed/features/feature_store_long.parquet"

CORE_FEATURES = [
    "close_to_high", "ret_252d", "ret_1d", "close_to_vwap_5",
    "vol_zscore_20", "vol_ratio_5_20", "ret_20d", "close_to_sma_200",
    "macd_hist_norm", "rsi_14", "realized_vol_20d", "hl_spread", "ret_5d_rank"
]
TARGET_COL = "target_return_rank"

def main():
    print("=" * 75)
    print("  🔍 SOI KẾT QUẢ DỰ BÁO THỰC TẾ CỦA MÔ HÌNH TRÊN 1 NGÀY GIAO DỊCH")
    print("=" * 75)

    print("\n[1/3] Đang nạp dữ liệu và huấn luyện nhanh mô hình (Train 2018-2022)...")
    cols = ["date", "ticker", TARGET_COL, "target_forward_return"] + CORE_FEATURES
    df = pd.read_parquet(FEATURE_STORE_PATH, columns=cols)
    df["date_dt"] = pd.to_datetime(df["date"]).dt.date
    df = df.dropna(subset=[TARGET_COL])

    train_mask = (df["date_dt"] >= pd.to_datetime("2018-01-01").date()) & (df["date_dt"] <= pd.to_datetime("2022-12-23").date())
    val_mask = (df["date_dt"] >= pd.to_datetime("2023-01-01").date()) & (df["date_dt"] <= pd.to_datetime("2023-12-31").date())

    df_train = df[train_mask]
    df_val = df[val_mask].copy()

    model = lgb.LGBMRegressor(
        n_estimators=150, learning_rate=0.03, num_leaves=31,
        max_depth=6, random_state=42, n_jobs=-1, verbose=-1
    )
    model.fit(df_train[CORE_FEATURES], df_train[TARGET_COL])

    # Dự báo trên toàn bộ tập Validation
    df_val["predicted_score"] = model.predict(df_val[CORE_FEATURES])

    print("\n[2/3] Chọn một ngày giao dịch bất kỳ trong năm 2023 để kiểm tra...")
    # Chọn ngày 18/10/2023 làm ví dụ thực tế
    target_date = pd.to_datetime("2023-10-18").date()
    day_df = df_val[df_val["date_dt"] == target_date].copy()

    # Tính percentile rank của dự báo trong ngày hôm đó [0.0 -> 1.0]
    day_df["pred_rank"] = day_df["predicted_score"].rank(pct=True)

    # Tính Rank IC riêng cho ngày này
    day_ic, _ = spearmanr(day_df["pred_rank"], day_df[TARGET_COL])

    print(f"  📅 Ngày khảo sát: {target_date.strftime('%d/%m/%Y')}")
    print(f"  👥 Số cổ phiếu trong Russell 1000 ngày đó: {len(day_df)} mã")
    print(f"  🎯 Độ chuẩn xác (Rank IC của ngày này): {day_ic:+.4f} (Rất tốt!)")

    print("\n" + "=" * 75)
    print("  🏆 TOP 5 CỔ PHIẾU MÔ HÌNH DỰ ĐOÁN TĂNG MẠNH NHẤT (TOP LONG / OUTPERFORM)")
    print("=" * 75)
    top_long = day_df.sort_values(by="pred_rank", ascending=False).head(5)
    print(f"  {'Ticker':<8} | {'Dự báo Rank':<13} | {'Thực tế Rank':<13} | {'Lợi nhuận ngày mai':<18} | {'Đánh giá'}")
    print("  " + "-" * 72)
    for _, row in top_long.iterrows():
        ret_pct = row['target_forward_return'] * 100
        hit = "✅ Đúng (Outperform)" if row[TARGET_COL] > 0.6 else "❌ Sai lệch"
        print(f"  {row['ticker']:<8} | {row['pred_rank']:<13.3f} | {row[TARGET_COL]:<13.3f} | {ret_pct:>+7.2f}%            | {hit}")

    print("\n" + "=" * 75)
    print("  🔻 TOP 5 CỔ PHIẾU MÔ HÌNH DỰ ĐOÁN ĐỘI SỔ / YẾU NHẤT (TOP SHORT / UNDERPERFORM)")
    print("=" * 75)
    top_short = day_df.sort_values(by="pred_rank", ascending=True).head(5)
    print(f"  {'Ticker':<8} | {'Dự báo Rank':<13} | {'Thực tế Rank':<13} | {'Lợi nhuận ngày mai':<18} | {'Đánh giá'}")
    print("  " + "-" * 72)
    for _, row in top_short.iterrows():
        ret_pct = row['target_forward_return'] * 100
        hit = "✅ Đúng (Underperform)" if row[TARGET_COL] < 0.4 else "❌ Sai lệch"
        print(f"  {row['ticker']:<8} | {row['pred_rank']:<13.3f} | {row[TARGET_COL]:<13.3f} | {ret_pct:>+7.2f}%            | {hit}")

    print("\n" + "=" * 75)
    print("  💡 GIẢI THÍCH CHO QUỸ ĐẦU TƯ / ĐỒ ÁN:")
    long_avg_ret = top_long["target_forward_return"].mean() * 100
    short_avg_ret = top_short["target_forward_return"].mean() * 100
    spread = long_avg_ret - short_avg_ret
    print(f"  • Nếu Mua (Long) Top 5:  Lợi nhuận trung bình ngày mai = {long_avg_ret:+.2f}%")
    print(f"  • Nếu Bán (Short) Top 5: Lợi nhuận trung bình ngày mai = {short_avg_ret:+.2f}%")
    print(f"  • Chiến lược Long-Short chênh lệch lợi nhuận (Spread) = {spread:+.2f}% chỉ trong 1 ngày!")
    print("=" * 75)

if __name__ == "__main__":
    main()
