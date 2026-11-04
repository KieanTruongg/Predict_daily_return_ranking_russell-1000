"""
BACKTEST SIMULATION — BACKTEST TOÀN BỘ NĂM 2023 THEO TOP 10 / TOP 20
=====================================================================
Mô phỏng chiến lược đầu tư thực tế trong suốt 250 ngày giao dịch năm 2023:
1. Mỗi ngày t: Model chọn ra TOP 10 cổ phiếu có điểm dự báo cao nhất (Top Decile/Top 10).
2. Nắm giữ qua đêm đến ngày t+1 (Daily Rebalance).
3. So sánh hiệu năng tích lũy (Cumulative Return & Sharpe Ratio) với:
   - Thị trường chung Russell 1000 (Equal Weight Benchmark - Mua tất cả ~950 mã)
   - Nhóm Bottom 10 (10 mã model bảo bán / né)
"""
import sys
import time
import pandas as pd
import numpy as np
import lightgbm as lgb

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
    print("  📈 MÔ PHỎNG BACKTEST CHIẾN LƯỢC TOP 10 SUỐT CẢ NĂM 2023 (250 NGÀY)")
    print("=" * 75)

    print("\n[1/3] Đang nạp dữ liệu và huấn luyện mô hình LightGBM (Train 2018-2022)...")
    cols = ["date", "ticker", TARGET_COL, "target_forward_return"] + CORE_FEATURES
    df = pd.read_parquet(FEATURE_STORE_PATH, columns=cols)
    df["date_dt"] = pd.to_datetime(df["date"]).dt.date
    df = df.dropna(subset=[TARGET_COL, "target_forward_return"])

    train_mask = (df["date_dt"] >= pd.to_datetime("2018-01-01").date()) & (df["date_dt"] <= pd.to_datetime("2022-12-23").date())
    val_mask = (df["date_dt"] >= pd.to_datetime("2023-01-01").date()) & (df["date_dt"] <= pd.to_datetime("2023-12-31").date())

    df_train = df[train_mask]
    df_val = df[val_mask].copy()

    model = lgb.LGBMRegressor(
        n_estimators=150, learning_rate=0.03, num_leaves=31,
        max_depth=6, random_state=42, n_jobs=-1, verbose=-1
    )
    model.fit(df_train[CORE_FEATURES], df_train[TARGET_COL])

    print("\n[2/3] Chạy mô phỏng giao dịch từng ngày trong năm 2023...")
    df_val["pred_rank"] = model.predict(df_val[CORE_FEATURES])

    daily_results = []
    
    # Duyệt qua từng ngày giao dịch (250 ngày)
    for dt, group in df_val.groupby("date_dt"):
        if len(group) < 50:
            continue
        
        # Sắp xếp theo điểm dự báo của model
        sorted_group = group.sort_values(by="pred_rank", ascending=False)
        
        # 1. Top 10 mã model bảo MUA MẠNH NHẤT
        top10_ret = sorted_group.head(10)["target_forward_return"].mean()
        
        # 2. Top 20 mã model bảo MUA
        top20_ret = sorted_group.head(20)["target_forward_return"].mean()
        
        # 3. Bottom 10 mã model bảo BÁN / NÉ
        bottom10_ret = sorted_group.tail(10)["target_forward_return"].mean()
        
        # 4. Thị trường chung Russell 1000 (Trung bình tất cả ~950 mã ngày hôm đó)
        market_ret = sorted_group["target_forward_return"].mean()
        
        daily_results.append({
            "date": dt,
            "top10_ret": top10_ret,
            "top20_ret": top20_ret,
            "market_ret": market_ret,
            "bottom10_ret": bottom10_ret,
            "long_short_ret": top10_ret - bottom10_ret
        })

    res_df = pd.DataFrame(daily_results).sort_values(by="date")

    print("\n[3/3] Tổng kết hiệu năng đầu tư năm 2023:")
    
    # Tính lợi nhuận tích lũy (Cumulative Compounded Return)
    cum_top10 = (1 + res_df["top10_ret"]).prod() - 1
    cum_top20 = (1 + res_df["top20_ret"]).prod() - 1
    cum_market = (1 + res_df["market_ret"]).prod() - 1
    cum_bottom10 = (1 + res_df["bottom10_ret"]).prod() - 1
    
    # Tính Sharpe Ratio (Annualized: 252 ngày)
    def calc_sharpe(ret_series):
        std = ret_series.std()
        if std == 0 or np.isnan(std):
            return 0.0
        return (ret_series.mean() / std) * np.sqrt(252)

    sharpe_top10 = calc_sharpe(res_df["top10_ret"])
    sharpe_top20 = calc_sharpe(res_df["top20_ret"])
    sharpe_market = calc_sharpe(res_df["market_ret"])
    sharpe_ls = calc_sharpe(res_df["long_short_ret"])

    # Tỷ lệ ngày chiến thắng thị trường (Win Rate vs Market)
    win_vs_market = (res_df["top10_ret"] > res_df["market_ret"]).mean() * 100

    print("=" * 75)
    print(f"  {'Chiến lược đầu tư':<30} | {'Tổng Lợi Nhuận 2023':<20} | {'Sharpe Ratio'}")
    print("  " + "-" * 72)
    print(f"  {'1. Mua TOP 10 Model chọn':<30} | {cum_top10 * 100:>+17.2f}% | {sharpe_top10:>11.2f}")
    print(f"  {'2. Mua TOP 20 Model chọn':<30} | {cum_top20 * 100:>+17.2f}% | {sharpe_top20:>11.2f}")
    print(f"  {'3. Thị trường chung (Russell 1000)':<30} | {cum_market * 100:>+17.2f}% | {sharpe_market:>11.2f}")
    print(f"  {'4. Nhóm Đội Sổ (Bottom 10 Né)':<30} | {cum_bottom10 * 100:>+17.2f}% | {calc_sharpe(res_df['bottom10_ret']):>11.2f}")
    print("=" * 75)

    print("\n  💡 ĐÁNH GIÁ CHUYÊN MÔN:")
    alpha = (cum_top10 - cum_market) * 100
    print(f"  • Lợi nhuận vượt trội (Alpha vs Market):  {alpha:>+7.2f}%")
    print(f"  • Tỷ lệ ngày Top 10 thắng thị trường:     {win_vs_market:.1f}%")
    print(f"  • Chiến lược Long Top 10 / Short Bottom 10 Sharpe: {sharpe_ls:.2f}")

    if cum_top10 > cum_market:
        print("\n  🟢 KẾT LUẬN: MUA TOP 10 THEO MODEL CHIẾN THẮNG THỊ TRƯỜNG CHUNG ÁP ĐẢO!")
    else:
        print("\n  🟡 KẾT LUẬN: Hiệu năng chưa vượt trội, cần thêm tuning.")
    print("=" * 75)

if __name__ == "__main__":
    main()
