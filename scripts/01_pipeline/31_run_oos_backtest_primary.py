"""
Script 31: Official OOS Backtest on Primary Scope (16 Corporate Halt Events)
===========================================================================
Thực thi kiểm thử danh mục đầu tư chính thức trên Phạm vi Ngoài mẫu Chính (Primary OOS Scope):
- Tín hiệu T sinh từ 2024-01-02 đến 2026-06-29 (624 phiên thực thi T+1 từ 2024-01-03 đến 2026-06-30).
- Mô hình so sánh: Ridge (alpha=1.0), GBDT (7 leaves), ret_20d (Benchmark).
- Vốn khởi tạo: 100,000 USD mỗi mô hình.
- Luật Top 20, ngân sách tối đa 5% NAV mỗi mã (self-financing gồm phí mua).
- Mua tại Open T+1, thoát tại Close T+1.
- Áp dụng đầy đủ 16 sự kiện đình chỉ giao dịch halt_flags từ reconciliation_open_positions.csv:
  * RCM (2024-11-19), FYBR (2026-01-20), COG (2026-05-07) cùng 13 mã trước đó.
  * Lệnh mua bị chặn: ghi CANCELLED_BUY, giữ ngân sách bằng tiền mặt, phí=0, trượt giá=0, tác động tiền mặt=0.
  * Giữ nguyên danh sách Top 20 đã chọn tại T, không đôn mã thay thế.
- Chạy 2 kịch bản chi phí:
  1. 0 bps: Không phí, không trượt giá.
  2. 20 bps: Vòng mua-bán 20 bps (5 bps phí + 5 bps trượt giá mỗi chiều).
- Báo cáo và so sánh:
  * Bảng tổng hợp 6 dòng chuẩn mực theo yêu cầu.
  * Đối chiếu các lệnh RCM, FYBR, COG trong sổ lệnh.
  * Rà soát các vị thế còn mở cuối kỳ.
  * Giải thích cơ chế chênh lệch giữa 0 bps và 20 bps.
"""

from __future__ import annotations

import sys
import time
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


def run_primary_backtest() -> None:
    start_total = time.time()
    print("=" * 110)
    print("CHẠY LẠI BACKTEST TRÊN 624 PHIÊN PHẠM VI OOS CHÍNH (2024-01-03 -> 2026-06-30)")
    print("Áp dụng 18 sự kiện halt_flags (bổ sung MRTX, RCM, FYBR, CFLT, COG) cho cả 3 tín hiệu ở 0 bps & 20 bps")
    print("=" * 110)

    out_dir = PROJECT_ROOT / "outputs" / "reports" / "backtest_primary_scope"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tải bảng đối soát và lập từ điển halt_flags
    recon_path = out_dir / "reconciliation_open_positions.csv"
    if not recon_path.exists():
        raise FileNotFoundError(f"Không tìm thấy bảng đối soát: {recon_path}")

    df_recon = pd.read_csv(recon_path)
    halt_flags: dict[tuple[str, str], bool] = {}

    for _, row in df_recon.iterrows():
        if row["buy_order_status"] == "LỆNH MUA KHÔNG KHỢP":
            exec_d = str(row["execution_date_T_plus_1"]).strip()
            sid = str(row["canonical_sid"]).strip()
            halt_flags[(exec_d, sid)] = True

    print(f"\n[1/6] Đã nạp {len(halt_flags)} sự kiện đình chỉ giao dịch (halt_flags) từ {recon_path.name}:")
    for (d, s) in sorted(halt_flags.keys()):
        print(f"  * Phiên {d}: {s} -> LỆNH MUA BỊ CHẶN (CANCELLED_BUY, Giữ tiền mặt)")

    # 2. Tải bảng dự đoán OOS đã lưu
    pred_path = PROJECT_ROOT / "data" / "processed" / "oos_predictions_2024_2026.parquet"
    if not pred_path.exists():
        raise FileNotFoundError(f"Không tìm thấy bảng dự đoán: {pred_path}")

    print(f"\n[2/6] Đang tải bảng dự đoán OOS: {pred_path.name}...")
    df_preds = pd.read_parquet(pred_path)

    # Lịch giao dịch
    dates_idx = load_dates_index()
    all_market_dates = list(dates_idx)

    # Xác định các ngày tín hiệu T thỏa mãn T+1 <= 2026-06-30
    primary_end_exec = pd.Timestamp("2026-06-30")
    primary_signal_dates = []

    for d in sorted(df_preds["date"].unique()):
        d_ts = pd.Timestamp(d)
        if d_ts in all_market_dates:
            loc = all_market_dates.index(d_ts)
            if loc + 1 < len(all_market_dates):
                t_plus_1 = all_market_dates[loc + 1]
                if t_plus_1 <= primary_end_exec:
                    primary_signal_dates.append(d_ts)

    print(f" -> Số ngày tín hiệu T trong Primary Scope: {len(primary_signal_dates)} phiên.")
    print(f"    Từ {primary_signal_dates[0].strftime('%Y-%m-%d')} đến {primary_signal_dates[-1].strftime('%Y-%m-%d')}")

    sessions = [primary_signal_dates[0].strftime("%Y-%m-%d")]
    for sd in primary_signal_dates:
        loc = all_market_dates.index(sd)
        t_plus_1 = all_market_dates[loc + 1]
        sessions.append(t_plus_1.strftime("%Y-%m-%d"))

    exec_dates = sessions[1:]
    print(f" -> Số phiên thực thi T+1 trong Primary Scope: {len(exec_dates)} phiên.")
    print(f"    Từ {exec_dates[0]} đến {exec_dates[-1]}")

    # 3. Tải ma trận giá và chất lượng dữ liệu
    t_load = time.time()
    print("\n[3/6] Đang tải các ma trận giá và chất lượng dữ liệu (allow_oos=True)...")
    open_mat = load_matrix("open", allow_oos=True)
    close_mat = load_matrix("close", allow_oos=True)
    vol_mat = load_matrix("volume", allow_oos=True)
    bad_mat = load_matrix("is_bad_data_period", allow_oos=True)
    spinoff_mat = load_matrix("is_spinoff_discontinuity", allow_oos=True)
    cf_mat = load_matrix("cumulative_split_factor", allow_oos=True)
    adj_div_mat = load_matrix("adj_dividend", allow_oos=True)
    print(f" -> Tải ma trận xong trong {time.time() - t_load:.2f}s.")

    # 4. Chuẩn hóa dữ liệu nhanh bằng Numpy (Vectorized / Direct Indexing)
    t_prep = time.time()
    print("\n[4/6] Chuẩn hóa dữ liệu giá và Corporate Actions (Tối ưu hóa Numpy)...")
    sub_dates = [pd.Timestamp(d) for d in sessions]
    open_sub = open_mat.reindex(index=sub_dates)
    close_sub = close_mat.reindex(index=sub_dates)
    vol_sub = vol_mat.reindex(index=sub_dates)
    bad_sub = bad_mat.reindex(index=sub_dates)
    spinoff_sub = spinoff_mat.reindex(index=sub_dates)
    cf_sub = cf_mat.reindex(index=sub_dates)
    adj_div_sub = adj_div_mat.reindex(index=sub_dates)

    cols = list(open_sub.columns)
    open_vals = open_sub.values
    close_vals = close_sub.values
    vol_vals = vol_sub.values
    bad_vals = bad_sub.values
    spinoff_vals = spinoff_sub.values
    cf_vals = cf_sub.values
    div_vals = adj_div_sub.values

    open_prices = {}
    close_prices = {}
    volume_data = {}
    bad_data_flags = {}
    split_factors = {}
    dividend_data = {}

    for t_idx in range(1, len(sessions)):
        prev_idx = t_idx - 1
        curr_idx = t_idx
        curr_d_str = sessions[curr_idx]

        for j, sid in enumerate(cols):
            o_v = open_vals[curr_idx, j]
            c_v = close_vals[curr_idx, j]
            v_v = vol_vals[curr_idx, j]
            b_v = bad_vals[curr_idx, j]
            sp_v = spinoff_vals[curr_idx, j]

            if np.isfinite(o_v) and o_v > 0:
                open_prices[(curr_d_str, sid)] = float(o_v)
            if np.isfinite(c_v) and c_v > 0:
                close_prices[(curr_d_str, sid)] = float(c_v)
            if np.isfinite(v_v):
                volume_data[(curr_d_str, sid)] = float(v_v)
            if b_v or sp_v:
                bad_data_flags[(curr_d_str, sid)] = True

            cf_p = cf_vals[prev_idx, j]
            cf_c = cf_vals[curr_idx, j]
            if np.isfinite(cf_p) and np.isfinite(cf_c) and cf_p > 0:
                s_factor = cf_c / cf_p
                if abs(s_factor - 1.0) > 1e-5:
                    split_factors[(curr_d_str, sid)] = float(s_factor)

            div_adj = div_vals[curr_idx, j]
            if np.isfinite(div_adj) and div_adj > 0 and np.isfinite(cf_c) and cf_c > 0:
                dividend_data[(curr_d_str, sid)] = float(div_adj / cf_c)

    print(f" -> Chuẩn hóa xong trong {time.time() - t_prep:.2f}s.")

    # 5. Trích xuất danh sách dự đoán Top 20 tại T cho từng mô hình
    print("\n[5/6] Trích xuất danh sách Top 20 tại T cho từng mô hình...")
    models_config = {
        "Ridge (alpha=1.0)": "ridge_score",
        "GBDT (7 leaves)": "gbdt_score",
        "ret_20d (Benchmark)": "ret_20d",
    }

    set_primary_dates = set(primary_signal_dates)
    df_preds_primary = df_preds[df_preds["date"].isin(set_primary_dates)].copy()

    preds_by_model: dict[str, dict[str, list[tuple[str, float]]]] = {}

    for model_name, score_col in models_config.items():
        preds_by_model[model_name] = {}
        for sd in primary_signal_dates:
            sd_str = sd.strftime("%Y-%m-%d")
            day_df = df_preds_primary[df_preds_primary["date"] == sd].sort_values(by=score_col, ascending=False)
            top_sids = list(zip(day_df["canonical_sid"], day_df[score_col]))
            preds_by_model[model_name][sd_str] = top_sids

    # 6. Thực thi mô phỏng qua 2 kịch bản chi phí
    print("\n[6/6] Chạy mô phỏng PortfolioSimulator cho 3 mô hình ở 2 kịch bản (0 bps & 20 bps)...")
    scenarios = [
        {
            "name": "20 bps (Baseline)",
            "suffix": "20bps",
            "fee_buy": 0.0005,
            "slip_buy": 0.0005,
            "fee_sell": 0.0005,
            "slip_sell": 0.0005,
        },
        {
            "name": "0 bps (Không chi phí)",
            "suffix": "0bps",
            "fee_buy": 0.0,
            "slip_buy": 0.0,
            "fee_sell": 0.0,
            "slip_sell": 0.0,
        },
    ]

    all_summary_records = []
    all_open_positions = []
    trade_logs_dict = {}

    for sc in scenarios:
        sc_name = sc["name"]
        sc_suffix = sc["suffix"]
        print(f"\n>>> THỰC THI KỊCH BẢN: {sc_name} <<<")

        for model_name, preds_dict in preds_by_model.items():
            safe_name = model_name.split()[0].lower()
            t_sim_start = time.time()

            sim = PortfolioSimulator(
                initial_capital=100_000.0,
                top_k=20,
                fee_rate_buy=sc["fee_buy"],
                slippage_rate_buy=sc["slip_buy"],
                fee_rate_sell=sc["fee_sell"],
                slippage_rate_sell=sc["slip_sell"],
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
                halt_flags=halt_flags,
            )

            df_trades = sim.get_trade_log_df()
            trade_logs_dict[(model_name, sc_suffix)] = df_trades

            # Lưu sổ cái và sổ lệnh theo từng kịch bản
            df_ledger.to_csv(out_dir / f"ledger_{safe_name}_{sc_suffix}.csv", index=False)
            df_trades.to_csv(out_dir / f"trades_{safe_name}_{sc_suffix}.csv", index=False)

            if sc_suffix == "20bps":
                df_ledger.to_csv(out_dir / f"ledger_{safe_name}.csv", index=False)
                df_trades.to_csv(out_dir / f"trades_{safe_name}.csv", index=False)

            final_nav = float(df_ledger.iloc[-1]["nav"])
            total_pnl = final_nav - 100_000.0
            cum_return = (final_nav / 100_000.0 - 1.0) * 100.0
            n_days = len(df_ledger)

            ann_factor = 252.0 / n_days
            cagr = ((final_nav / 100_000.0) ** ann_factor - 1.0) * 100.0

            rets = df_ledger["daily_return"].values
            mean_ret = np.mean(rets)
            std_ret = np.std(rets, ddof=1) if len(rets) > 1 else np.nan
            daily_sharpe = (mean_ret / std_ret) if (std_ret and std_ret > 0) else 0.0
            ann_sharpe = daily_sharpe * np.sqrt(252.0)

            nav_series = df_ledger["nav"].values
            cummax = np.maximum.accumulate(nav_series)
            drawdowns = (nav_series - cummax) / cummax
            mdd = np.min(drawdowns) * 100.0

            total_fees = float(df_trades["fee"].sum())
            total_slippage = float(df_trades["slippage_cost"].sum())
            total_buys_filled = int(df_ledger["n_buys_filled"].sum())
            df_cancelled = df_trades[df_trades["action"] == "CANCELLED_BUY"]
            total_buys_cancelled = len(df_cancelled)
            total_halt_blocked = int(df_cancelled["note"].str.contains("MARKET_HALT", na=False).sum())
            total_missing_open = int(df_cancelled["note"].str.contains("SIMULATION_CONDITION", na=False).sum())
            total_sells_filled = int(df_ledger["n_sells_filled"].sum())
            final_cash = float(sim.cash)

            open_positions_end = list(sim.positions.values())
            n_open_end = len(open_positions_end)
            open_invested_val = sum(p.shares * p.last_price for p in open_positions_end)

            for pos in open_positions_end:
                all_open_positions.append({
                    "kịch_bản": sc_name,
                    "mô_hình": model_name,
                    "canonical_sid": pos.canonical_sid,
                    "shares": float(pos.shares),
                    "entry_date": pos.entry_date,
                    "entry_price": float(pos.entry_price_raw),
                    "last_price": float(pos.last_price),
                    "invested_value": float(pos.shares * pos.last_price),
                })

            all_summary_records.append({
                "Kịch bản": sc_name,
                "Mô hình": model_name,
                "Số phiên": n_days,
                "NAV Cuối ($)": final_nav,
                "Lợi nhuận ($)": total_pnl,
                "Tỷ suất (%)": cum_return,
                "CAGR (%)": cagr,
                "Sharpe": ann_sharpe,
                "Max Drawdown (%)": mdd,
                "Tổng Phí ($)": total_fees,
                "Tổng Trượt giá ($)": total_slippage,
                "Tổng Chi phí ($)": total_fees + total_slippage,
                "Tiền mặt cuối ($)": final_cash,
                "Giá trị mở cuối ($)": open_invested_val,
                "Vị thế mở cuối": n_open_end,
                "Lệnh Mua Khớp": total_buys_filled,
                "Lệnh Bị Chặn (Tổng)": total_buys_cancelled,
                "Bị chặn do Halt M&A": total_halt_blocked,
                "Bị chặn do thiếu giá Open": total_missing_open,
                "Lệnh Bán Khớp": total_sells_filled,
            })
            print(f"    Done {model_name} in {time.time() - t_sim_start:.2f}s: Final NAV = ${final_nav:,.2f}, Open positions = {n_open_end}")

    # 7. Xuất bảng tổng hợp 6 dòng chuẩn
    df_all_summary = pd.DataFrame(all_summary_records)
    df_all_summary.to_csv(out_dir / "performance_summary_all_scenarios.csv", index=False)

    df_summary_20bps = df_all_summary[df_all_summary["Kịch bản"] == "20 bps (Baseline)"].copy()
    df_summary_20bps.to_csv(out_dir / "performance_summary.csv", index=False)

    df_summary_0bps = df_all_summary[df_all_summary["Kịch bản"] == "0 bps (Không chi phí)"].copy()
    df_summary_0bps.to_csv(out_dir / "performance_summary_0bps.csv", index=False)

    df_open_all = pd.DataFrame(all_open_positions)
    df_open_all.to_csv(out_dir / "open_positions_summary.csv", index=False)

    # 8. Bảng 6 dòng theo yêu cầu người dùng
    print("\n" + "=" * 110)
    print("BẢNG TỔNG HỢP 6 DÒNG CHUẨN MỰC THEO YÊU CẦU (NAV, TỶ SUẤT, DRAWDOWN, CHI PHÍ, LỆNH CHẶN, VỊ THẾ MỞ):")
    print("=" * 110)
    table_6_cols = [
        "Kịch bản", "Mô hình", "NAV Cuối ($)", "Tỷ suất (%)", "Max Drawdown (%)",
        "Tổng Phí ($)", "Tổng Trượt giá ($)", "Lệnh Bị Chặn (Tổng)", "Bị chặn do Halt M&A", "Bị chặn do thiếu giá Open", "Vị thế mở cuối"
    ]
    df_table_6 = df_all_summary[table_6_cols].copy()
    print(df_table_6.to_string(index=False))

    # 9. Đối chiếu các lệnh MRTX, RCM, FYBR, CFLT, COG trong sổ lệnh
    print("\n" + "=" * 110)
    print("ĐỐI CHIẾU CÁC LỆNH MRTX, RCM, FYBR, CFLT, COG TRONG SỔ LỆNH RIDGE (20 BPS):")
    print("=" * 110)
    trades_ridge_20 = trade_logs_dict[("Ridge (alpha=1.0)", "20bps")]
    target_sids = [
        ("2024-01-23", "MRTX VIA09B2Z24X1"),
        ("2024-01-24", "MRTX VIA09B2Z24X1"),
        ("2024-11-19", "RCM WIVGEEITFLNP"),
        ("2026-01-20", "FYBR XO78VO8V1L5X"),
        ("2026-03-17", "CFLT XPKH8CJAVB6T"),
        ("2026-05-07", "COG R735QTJ8XC9X"),
    ]
    checked_rows = []
    for d, sid in target_sids:
        match = trades_ridge_20[(trades_ridge_20["date"] == d) & (trades_ridge_20["canonical_sid"] == sid)]
        if len(match) > 0:
            checked_rows.append(match.iloc[0].to_dict())
        else:
            checked_rows.append({
                "date": d,
                "canonical_sid": sid,
                "action": "NO_ORDER",
                "timing": "-",
                "price_raw": 0.0,
                "shares": 0.0,
                "fee": 0.0,
                "slippage_cost": 0.0,
                "cash_impact": 0.0,
                "note": "Không phát sinh lệnh mua/bán (Vị thế không tồn tại)"
            })

    df_checked = pd.DataFrame(checked_rows)
    cols_disp = ["date", "canonical_sid", "action", "timing", "price_raw", "shares", "fee", "slippage_cost", "cash_impact", "note"]
    print(df_checked[[c for c in cols_disp if c in df_checked.columns]].to_string(index=False))

    # 10. So sánh Bản cũ (17 halts) vs Bản mới (18 halts - bổ sung MRTX) ở 20 bps
    archive_dir_17 = out_dir / "archive_run3_17halts"
    if (archive_dir_17 / "performance_summary.csv").exists():
        df_old_perf = pd.read_csv(archive_dir_17 / "performance_summary.csv")
        print("\n" + "=" * 110)
        print("SO SÁNH LƯỢT TRƯỚC (17 HALTS) VS LƯỢT MỚI (18 HALTS - BỔ SUNG MRTX) Ở 20 BPS:")
        print("=" * 110)
        comp_halts = []
        for model_name, _ in models_config.items():
            r_old = df_old_perf[df_old_perf["Mô hình"] == model_name].iloc[0]
            r_new = df_summary_20bps[df_summary_20bps["Mô hình"] == model_name].iloc[0]
            
            nav_old = float(r_old["NAV Cuối ($)"])
            nav_new = float(r_new["NAV Cuối ($)"])
            ret_old = float(r_old["Tỷ suất (%)"])
            ret_new = float(r_new["Tỷ suất (%)"])
            mdd_old = float(r_old["Max Drawdown (%)"])
            mdd_new = float(r_new["Max Drawdown (%)"])
            open_old = int(r_old["Vị thế mở cuối"])
            open_new = int(r_new["Vị thế mở cuối"])
            halt_old = int(r_old.get("Bị chặn do Halt M&A", r_old.get("Lệnh Bị Chặn (Halt)", 0)))
            halt_new = int(r_new["Bị chặn do Halt M&A"])
            
            comp_halts.append({
                "Mô hình": model_name,
                "NAV Trước (17 Halts) ($)": f"{nav_old:,.2f}",
                "NAV Mới (18 Halts) ($)": f"{nav_new:,.2f}",
                "Chênh lệch NAV ($)": f"{(nav_new - nav_old):+,.2f}",
                "Tỷ suất Trước (%)": f"{ret_old:+.2f}%",
                "Tỷ suất Mới (%)": f"{ret_new:+.2f}%",
                "Max DD Trước (%)": f"{mdd_old:.2f}%",
                "Max DD Mới (%)": f"{mdd_new:.2f}%",
                "Lệnh Halt Trước": halt_old,
                "Lệnh Halt Mới": halt_new,
                "Vị thế mở Trước": open_old,
                "Vị thế mở Mới": open_new,
            })
        df_comp_halts = pd.DataFrame(comp_halts)
        print(df_comp_halts.to_string(index=False))
        df_comp_halts.to_csv(out_dir / "comparison_17halts_vs_18halts_20bps.csv", index=False)

    # 11. So sánh 0 bps vs 20 bps mới
    print("\n" + "=" * 110)
    print("BẢNG SO SÁNH 0 BPS (GROSS) VS 20 BPS (NET) TRÊN BẢN MỚI 18 HALTS:")
    print("=" * 110)
    comp_0_20 = []
    for model_name, _ in models_config.items():
        r_0 = df_summary_0bps[df_summary_0bps["Mô hình"] == model_name].iloc[0]
        r_20 = df_summary_20bps[df_summary_20bps["Mô hình"] == model_name].iloc[0]
        nav_0 = float(r_0["NAV Cuối ($)"])
        nav_20 = float(r_20["NAV Cuối ($)"])
        ret_0 = float(r_0["Tỷ suất (%)"])
        ret_20 = float(r_20["Tỷ suất (%)"])
        mdd_0 = float(r_0["Max Drawdown (%)"])
        mdd_20 = float(r_20["Max Drawdown (%)"])
        total_cost_20 = float(r_20["Tổng Chi phí ($)"])

        comp_0_20.append({
            "Mô hình": model_name,
            "NAV 0 bps ($)": f"{nav_0:,.2f}",
            "NAV 20 bps ($)": f"{nav_20:,.2f}",
            "Chênh lệch NAV ($)": f"{(nav_20 - nav_0):+,.2f}",
            "Tỷ suất 0 bps (%)": f"{ret_0:+.2f}%",
            "Tỷ suất 20 bps (%)": f"{ret_20:+.2f}%",
            "Chênh lệch Tỷ suất (%)": f"{(ret_20 - ret_0):+.2f}%",
            "Max DD 0 bps (%)": f"{mdd_0:.2f}%",
            "Max DD 20 bps (%)": f"{mdd_20:.2f}%",
            "Phí 20bps ($)": f"{float(r_20['Tổng Phí ($)']):,.2f}",
            "Trượt giá 20bps ($)": f"{float(r_20['Tổng Trượt giá ($)']):,.2f}",
            "Tổng Chi phí 20bps ($)": f"{total_cost_20:,.2f}",
        })
    df_comp_0_20 = pd.DataFrame(comp_0_20)
    print(df_comp_0_20.to_string(index=False))
    df_comp_0_20.to_csv(out_dir / "comparison_0bps_vs_20bps.csv", index=False)

    print(f"\n -> HOÀN TẤT TOÀN BỘ QUY TRÌNH TRONG {time.time() - start_total:.2f} GIÂY!")
    print("=" * 110)


if __name__ == "__main__":
    run_primary_backtest()
