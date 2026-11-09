"""
Script 30: OOS Backtest Trial Slice Verification (Ridge vs GBDT vs ret_20d)
===========================================================================
Nối bộ mô phỏng PortfolioSimulator với bảng dự đoán OOS đã lưu (oos_predictions_2024_2026.parquet)
và hệ thống ma trận giá (open, close, volume, is_bad_data_period, corporate actions).

Nguyên tắc phương pháp luận:
1. Chọn Top 20 tại T trước khi đọc bất kỳ điều kiện khớp lệnh nào tại T+1.
2. Dùng giá Open/Close hữu hạn, dương và áp đúng corrections theo từng trường.
   Giữ nguyên Close nếu chỉ Open bị cách ly.
3. Phân biệt tường minh:
   - MISSING_SIM_PRICE: Dữ liệu giá mô phỏng bị thiếu, NaN, <= 0 hoặc bị quarantine.
   - EVIDENCE_UNFILLED: Bằng chứng thực tế cổ phiếu bị halt / ngừng giao dịch / vol = 0.
4. Xử lý vị thế qua đêm khi gặp Stock Split hoặc Cổ tức tiền mặt trên ngày ex-date.
5. Chạy thử lát cắt 5 phiên đầu OOS trên cùng quy tắc cho Ridge alpha=1.0, GBDT 7 lá, và ret_20d.
6. Bàn giao danh sách Top 20, sổ lệnh, tiền mặt, phí và NAV để đối chiếu.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd

from src.backtest.simulator import PortfolioSimulator
from src.data.matrix_loader import load_dates_index, load_matrix


def run_trial_slice(n_sessions_to_test: int = 5) -> None:
    print("=" * 95)
    print("CHẠY THỬ NGHIỆM LÁT CẮT OOS BACKTEST (TRIAL SLICE: 5 PHIÊN ĐẦU NĂM 2024)")
    print("=" * 95)

    # 1. Tải bảng dự đoán OOS đã lưu
    pred_path = PROJECT_ROOT / "data" / "processed" / "oos_predictions_2024_2026.parquet"
    if not pred_path.exists():
        raise FileNotFoundError(f"Không tìm thấy bảng dự đoán: {pred_path}")

    print(f"\n[1/6] Đang tải bảng dự đoán OOS: {pred_path.name}...")
    df_preds = pd.read_parquet(pred_path)
    all_pred_dates = sorted(pd.to_datetime(df_preds["date"].unique()))
    print(f" -> Tổng số phiên có dự đoán trong OOS: {len(all_pred_dates)} phiên.")

    # Lấy n_sessions_to_test ngày tín hiệu T đầu tiên
    signal_dates = all_pred_dates[:n_sessions_to_test]
    print(f" -> Danh sách {n_sessions_to_test} ngày tín hiệu T: {[d.strftime('%Y-%m-%d') for d in signal_dates]}")

    # 2. Xác định các ngày thực thi T+1
    dates_idx = load_dates_index()
    all_market_dates = list(dates_idx)

    # Chuỗi các ngày thực thi [T_0, T_1, T_2, ... T_n]
    # Lệnh sinh tại T_0 sẽ khớp tại T_1, ..., lệnh sinh tại T_{n-1} khớp tại T_n
    sessions = []
    first_signal = signal_dates[0]
    sessions.append(first_signal.strftime("%Y-%m-%d"))

    for sd in signal_dates:
        loc = all_market_dates.index(sd)
        t_plus_1 = all_market_dates[loc + 1]
        sessions.append(t_plus_1.strftime("%Y-%m-%d"))

    exec_dates = sessions[1:]
    print(f" -> Danh sách {n_sessions_to_test} ngày thực thi T+1: {exec_dates}")

    # 3. Tải ma trận giá và chất lượng dữ liệu
    print("\n[2/6] Đang tải các ma trận giá và chất lượng dữ liệu (allow_oos=True)...")
    open_mat = load_matrix("open", allow_oos=True)
    close_mat = load_matrix("close", allow_oos=True)
    vol_mat = load_matrix("volume", allow_oos=True)
    bad_mat = load_matrix("is_bad_data_period", allow_oos=True)
    spinoff_mat = load_matrix("is_spinoff_discontinuity", allow_oos=True)
    cf_mat = load_matrix("cumulative_split_factor", allow_oos=True)
    adj_div_mat = load_matrix("adj_dividend", allow_oos=True)

    # 4. Chuẩn bị từ điển giá và sự kiện doanh nghiệp cho các phiên thực thi
    print("\n[3/6] Chuẩn hóa dữ liệu giá, cờ chất lượng và Corporate Actions...")
    open_prices = {}
    close_prices = {}
    volume_data = {}
    bad_data_flags = {}
    split_factors = {}
    dividend_data = {}

    for t_idx in range(1, len(sessions)):
        prev_d_str = sessions[t_idx - 1]
        curr_d_str = sessions[t_idx]

        prev_ts = pd.Timestamp(prev_d_str)
        curr_ts = pd.Timestamp(curr_d_str)

        # Lấy tất cả canonical SIDs
        for sid in open_mat.columns:
            o_val = open_mat.loc[curr_ts, sid] if curr_ts in open_mat.index else np.nan
            c_val = close_mat.loc[curr_ts, sid] if curr_ts in close_mat.index else np.nan
            v_val = vol_mat.loc[curr_ts, sid] if curr_ts in vol_mat.index else np.nan
            b_val = bad_mat.loc[curr_ts, sid] if curr_ts in bad_mat.index else False
            sp_val = spinoff_mat.loc[curr_ts, sid] if curr_ts in spinoff_mat.index else False

            open_prices[(curr_d_str, sid)] = float(o_val) if (pd.notna(o_val) and np.isfinite(o_val)) else np.nan
            close_prices[(curr_d_str, sid)] = float(c_val) if (pd.notna(c_val) and np.isfinite(c_val)) else np.nan
            volume_data[(curr_d_str, sid)] = float(v_val) if (pd.notna(v_val) and np.isfinite(v_val)) else 0.0
            bad_data_flags[(curr_d_str, sid)] = bool(b_val or sp_val)

            # Corporate Actions giữa prev_d (trước) và curr_d (sau)
            cf_prev = cf_mat.loc[prev_ts, sid] if prev_ts in cf_mat.index else 1.0
            cf_curr = cf_mat.loc[curr_ts, sid] if curr_ts in cf_mat.index else 1.0
            if pd.notna(cf_prev) and pd.notna(cf_curr) and cf_prev > 0:
                s_factor = cf_curr / cf_prev  # CF_sau / CF_trước theo quy ước adj_close = raw_close * CF
            else:
                s_factor = 1.0
            split_factors[(curr_d_str, sid)] = float(s_factor)

            div_adj = adj_div_mat.loc[curr_ts, sid] if curr_ts in adj_div_mat.index else 0.0
            if pd.notna(div_adj) and div_adj > 0 and pd.notna(cf_curr) and cf_curr > 0:
                div_raw = div_adj / cf_curr
            else:
                div_raw = 0.0
            dividend_data[(curr_d_str, sid)] = float(div_raw)

    # 5. Xây dựng danh sách dự đoán Top 20 tại T cho từng mô hình
    print("\n[4/6] Trích xuất danh sách Top 20 tại T trước khi đọc điều kiện khớp T+1...")
    models_config = {
        "Ridge (alpha=1.0)": "ridge_score",
        "GBDT (7 leaves)": "gbdt_score",
        "ret_20d (Benchmark)": "ret_20d",
    }

    preds_by_model: dict[str, dict[str, list[tuple[str, float]]]] = {}
    top20_summary_records = []

    for model_name, score_col in models_config.items():
        preds_by_model[model_name] = {}
        for sd in signal_dates:
            sd_str = sd.strftime("%Y-%m-%d")
            day_df = df_preds[df_preds["date"] == sd].sort_values(by=score_col, ascending=False)
            top_sids = list(zip(day_df["canonical_sid"], day_df[score_col]))
            preds_by_model[model_name][sd_str] = top_sids

            # Lưu thông tin Top 20 để báo cáo
            for rank, (s, sc) in enumerate(top_sids[:20], 1):
                top20_summary_records.append({
                    "model": model_name,
                    "signal_date_T": sd_str,
                    "rank": rank,
                    "canonical_sid": s,
                    "score": float(sc),
                })

    df_top20_all = pd.DataFrame(top20_summary_records)
    out_dir = PROJECT_ROOT / "outputs" / "reports" / "backtest_trial_slice"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_top20_all.to_csv(out_dir / "top20_candidates_trial_slice.csv", index=False)
    print(f" -> Đã lưu danh sách Top 20 của 3 mô hình: {out_dir / 'top20_candidates_trial_slice.csv'}")

    # 6. Chạy mô phỏng cho từng mô hình
    print("\n[5/6] Chạy mô phỏng PortfolioSimulator cho 3 mô hình trên cùng quy tắc...")
    results_comparison = []
    trade_logs_dict = {}
    daily_ledgers_dict = {}

    for model_name, preds_dict in preds_by_model.items():
        sim = PortfolioSimulator(
            initial_capital=100_000.0,
            top_k=20,
            fee_rate_buy=0.0005,       # 5 bps
            slippage_rate_buy=0.0005,  # 5 bps
            fee_rate_sell=0.0005,      # 5 bps
            slippage_rate_sell=0.0005, # 5 bps
        )

        df_ledger = sim.simulate(
            sessions=sessions,
            predictions_by_date=preds_dict,
            open_prices=open_prices,
            close_prices=close_prices,
            bad_data_flags=bad_data_flags,
            volume_data=volume_data,
            split_factors=split_factors,
            dividend_data=dividend_data,
        )

        df_trades = sim.get_trade_log_df()

        safe_name = model_name.split()[0].lower()
        df_ledger.to_csv(out_dir / f"ledger_{safe_name}.csv", index=False)
        df_trades.to_csv(out_dir / f"trades_{safe_name}.csv", index=False)

        trade_logs_dict[model_name] = df_trades
        daily_ledgers_dict[model_name] = df_ledger

        # Thống kê tổng hợp lát cắt
        final_nav = df_ledger.iloc[-1]["nav"]
        total_pnl = final_nav - 100_000.0
        cum_return = (final_nav / 100_000.0 - 1.0) * 100.0
        total_fees = df_ledger["total_fees_paid"].sum()
        total_buys = df_ledger["n_buys_filled"].sum()
        total_unfilled = df_ledger["n_buys_unfilled"].sum()
        total_sells = df_ledger["n_sells_filled"].sum()
        carried_overnight = df_ledger["n_carried_forward"].sum()

        results_comparison.append({
            "Mô hình": model_name,
            "NAV Cuối ($)": f"{final_nav:,.2f}",
            "Lợi nhuận PnL ($)": f"{total_pnl:+,.2f}",
            "Tỷ suất (%)": f"{cum_return:+.3f}%",
            "Tổng phí hoa hồng ($)": f"{total_fees:,.2f}",
            "Lệnh Mua Khớp": total_buys,
            "Lệnh Mua Hủy": total_unfilled,
            "Lệnh Bán Khớp": total_sells,
            "Vị thế Kẹt Qua Đêm": carried_overnight,
        })

    df_comp = pd.DataFrame(results_comparison)
    print("\n" + "=" * 95)
    print("BẢNG TỔNG HỢP SO SÁNH 3 MÔ HÌNH TRÊN LÁT CẮT 5 PHIÊN THỬ NGHIỆM:")
    print("=" * 95)
    print(df_comp.to_string(index=False))

    # 7. Trích lục chi tiết từng phiên của từng mô hình
    print("\n" + "=" * 95)
    print("SỔ CÁI HẰNG NGÀY (DAILY LEDGER) CỦA TỪNG MÔ HÌNH:")
    print("=" * 95)
    for model_name, df_l in daily_ledgers_dict.items():
        print(f"\n--- {model_name} ---")
        disp_cols = ["date", "cash_start", "cash_end", "invested_value", "nav", "daily_return", "n_buys_filled", "n_sells_filled", "total_fees_paid"]
        print(df_l[disp_cols].to_string(index=False))

    # 8. Trích lục mẫu sổ lệnh (Trade Log) của Ridge
    print("\n" + "=" * 95)
    print("TRÍCH LỤC SỔ LỆNH ĐẠI DIỆN PHIÊN 1 (2024-01-03) CỦA RIDGE (ALPHA=1.0):")
    print("=" * 95)
    ridge_trades_day1 = trade_logs_dict["Ridge (alpha=1.0)"]
    day1_mask = ridge_trades_day1["date"] == "2024-01-03"
    disp_trade_cols = ["date", "canonical_sid", "action", "timing", "price_raw", "price_exec", "shares", "notional", "fee", "cash_impact", "note"]
    print(ridge_trades_day1[day1_mask].head(6)[disp_trade_cols].to_string(index=False))
    print("...")
    print(ridge_trades_day1[day1_mask].tail(6)[disp_trade_cols].to_string(index=False))


if __name__ == "__main__":
    run_trial_slice(n_sessions_to_test=5)
