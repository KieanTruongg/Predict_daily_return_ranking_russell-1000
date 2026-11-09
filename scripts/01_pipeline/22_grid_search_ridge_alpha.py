"""
Pipeline Script 22: Grid Search Alpha for Ridge Baseline (5 Folds Walk-Forward)
================================================================================
Mục tiêu:
1. Thử nghiệm lưới siêu tham số regularization alpha cho Ridge Regression:
   alpha in [1, 1000, 10000, 100000, 1000000]
2. Giữ phép so sánh nhất quán tuyệt đối trên 5 fold Expanding Window:
   - Sử dụng đúng cấu hình configs/walk_forward_schedule_v1.yaml và dữ liệu baseline_dataset_v1.parquet.
   - Mỗi fold chỉ fit StandardScaler MỘT LẦN trên Train. Dùng chung tập train/val đã scale cho mọi giá trị alpha.
   - Fit từng Ridge với fit_intercept=True.
   - Tính Spearman Rank IC từng ngày giữa điểm Ridge của từng alpha và target_return trên cùng ngày và cùng mã.
3. Đối chiếu mốc alpha=1:
   - Đảm bảo khớp chính xác 1.253 phiên và Mean Daily Rank IC xấp xỉ +0.016497 từ lượt trước.
4. Đánh giá và lưu trữ:
   - configs/ridge_alpha_grid_search_run.yaml
   - outputs/reports/daily_ic_ridge_alpha_grid.csv & data/processed/daily_ic_ridge_alpha_grid.parquet
   - outputs/reports/summary_ridge_alpha_grid.csv
   - docs/reports/baseline/ridge_alpha_grid_search_report.md
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "configs"
MODELS_DIR = PROJECT_ROOT / "models" / "grid_search_ridge"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DOCS_REPORTS_DIR = PROJECT_ROOT / "docs" / "reports" / "baseline"

DATASET_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
SCHEDULE_CONFIG_FILE = CONFIGS_DIR / "walk_forward_schedule_v1.yaml"

OUTPUT_RUN_CONFIG_FILE = CONFIGS_DIR / "ridge_alpha_grid_search_run.yaml"
OUTPUT_DAILY_IC_CSV = REPORTS_DIR / "daily_ic_ridge_alpha_grid.csv"
OUTPUT_DAILY_IC_PARQUET = DATA_DIR / "daily_ic_ridge_alpha_grid.parquet"
OUTPUT_SUMMARY_CSV = REPORTS_DIR / "summary_ridge_alpha_grid.csv"
OUTPUT_REPORT_MD = DOCS_REPORTS_DIR / "ridge_alpha_grid_search_report.md"

BASELINE_13_FEATURES = [
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "mom_12m_skip_1m",
    "vol_realized_20d",
    "vol_realized_60d",
    "downside_deviation_20d",
    "amihud_illiq_20d",
    "volume_ratio_5_20",
    "log_dollar_volume_20d",
    "rsi_14d",
    "bollinger_pct_b_20d",
]

TARGET_RANK_COL = "target_rank"
TARGET_RETURN_COL = "target_return"
BENCHMARK_COL = "ret_20d"
ALPHA_GRID = [1.0, 1000.0, 10000.0, 100000.0, 1000000.0]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def summarize_series(s: pd.Series) -> dict:
    valid_s = s.dropna()
    n_tot = len(s)
    n_val = len(valid_s)
    if n_val > 0:
        mean_v = float(valid_s.mean())
        std_v = float(valid_s.std(ddof=1)) if n_val > 1 else 0.0
        pos_r = float((valid_s > 0).mean())
        ir_daily = float(mean_v / std_v) if std_v > 1e-12 else 0.0
        ir_ann = float(ir_daily * np.sqrt(252))
        t_stat = float(mean_v / (std_v / np.sqrt(n_val))) if std_v > 1e-12 else 0.0
    else:
        mean_v = std_v = pos_r = ir_daily = ir_ann = t_stat = np.nan

    return {
        "evaluable_days": n_val,
        "mean_ic": mean_v,
        "std_ic": std_v,
        "positive_ic_ratio": pos_r,
        "ic_ir_daily": ir_daily,
        "ic_ir_annualized": ir_ann,
        "t_statistic": t_stat,
    }


def run_ridge_alpha_grid_search(
    alpha_grid: List[float] = ALPHA_GRID,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Thực hiện grid search alpha trên 5 fold Walk-Forward.
    """
    t_start = time.time()
    log("=" * 90)
    log(f"BẮT ĐẦU GRID SEARCH ALPHA RIDGE TRÊN 5 FOLDS: alphas={alpha_grid}")
    log("=" * 90)

    # 1. Nạp lịch Walk-Forward
    if not SCHEDULE_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy lịch Walk-Forward: {SCHEDULE_CONFIG_FILE}")

    with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
        wf_cfg = yaml.safe_load(f)

    # 2. Nạp dataset gốc
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset nguồn: {DATASET_FILE}")

    log(f"[1/4] Nạp dataset nguồn từ: {DATASET_FILE}...")
    df_all = pd.read_parquet(DATASET_FILE)
    log(f"  -> Đã nạp: {len(df_all):,} dòng, {len(df_all.columns)} cột.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_daily_records: List[dict] = []
    # Lưu trọng số từng model
    fold_coefs: Dict[int, Dict[str, dict]] = {}

    log(f"[2/4] Huấn luyện và dự đoán 5 alpha trên 5 folds...")
    for fold in wf_cfg["folds"]:
        fid = fold["fold_id"]
        tr_info = fold["train"]
        vl_info = fold["validation"]
        val_year = int(vl_info["period_label"])

        log(f"\n--- [FOLD {fid}/5] Train {tr_info['period_label']} -> Val {val_year} ---")

        # Cắt Train
        df_train = df_all.query(f"date >= '{tr_info['actual_start']}' and date <= '{tr_info['actual_end']}'").copy()
        X_tr_raw = df_train[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)
        y_tr = df_train[TARGET_RANK_COL].to_numpy(dtype=np.float64)

        # Cắt Validation
        df_val = df_all.query(f"date >= '{vl_info['actual_start']}' and date <= '{vl_info['actual_end']}'").copy()
        X_vl_raw = df_val[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)

        # Fit StandardScaler MỘT LẦN DUY NHẤT trên Train của fold
        scaler = StandardScaler(with_mean=True, with_std=True)
        X_tr_scaled = scaler.fit_transform(X_tr_raw)
        X_vl_scaled = scaler.transform(X_vl_raw)

        # Lưu scaler
        scaler_path = MODELS_DIR / f"scaler_fold_{fid}.joblib"
        joblib.dump(scaler, scaler_path)

        del df_train, X_tr_raw, X_vl_raw

        fold_coefs[fid] = {}
        val_scores_dict: Dict[float, np.ndarray] = {}

        # Duyệt qua từng alpha trong grid
        for alpha in alpha_grid:
            alpha_str = f"{int(alpha)}" if alpha == int(alpha) else f"{alpha}"
            ridge = Ridge(alpha=alpha, fit_intercept=True, copy_X=False)
            ridge.fit(X_tr_scaled, y_tr)

            # Dự đoán
            scores = ridge.predict(X_vl_scaled)
            val_scores_dict[alpha] = scores

            # Lưu model
            model_path = MODELS_DIR / f"ridge_fold_{fid}_alpha_{alpha_str}.joblib"
            joblib.dump(ridge, model_path)

            coef_map = {feat: float(c) for feat, c in zip(BASELINE_13_FEATURES, ridge.coef_)}
            fold_coefs[fid][f"alpha_{alpha_str}"] = {
                "intercept": float(ridge.intercept_),
                "coefficients": coef_map,
            }

        del X_tr_scaled, X_vl_scaled, y_tr

        # Gán các cột dự đoán vào df_val
        for alpha, scores in val_scores_dict.items():
            alpha_str = f"{int(alpha)}" if alpha == int(alpha) else f"{alpha}"
            df_val[f"score_alpha_{alpha_str}"] = scores

        # Tính toán Daily Spearman IC cho từng alpha và benchmark
        for dt, group in df_val.groupby("date", sort=True):
            y_ret = group[TARGET_RETURN_COL].to_numpy()
            bench_ret20 = group[BENCHMARK_COL].to_numpy()
            n_stk = len(group)

            rec = {
                "date": dt.strftime("%Y-%m-%d"),
                "fold_id": fid,
                "val_year": val_year,
                "n_stocks": n_stk,
            }

            if n_stk < 2 or (np.ptp(y_ret) == 0):
                for alpha in alpha_grid:
                    a_s = f"{int(alpha)}" if alpha == int(alpha) else f"{alpha}"
                    rec[f"ic_alpha_{a_s}"] = np.nan
                rec["ic_ret_20d"] = np.nan
                rec["is_valid"] = False
            else:
                # Benchmark ret_20d
                if np.ptp(bench_ret20) == 0:
                    rec["ic_ret_20d"] = np.nan
                else:
                    rec["ic_ret_20d"] = float(stats.spearmanr(bench_ret20, y_ret)[0])

                # Từng alpha
                for alpha in alpha_grid:
                    a_s = f"{int(alpha)}" if alpha == int(alpha) else f"{alpha}"
                    sc = group[f"score_alpha_{a_s}"].to_numpy()
                    if np.ptp(sc) == 0:
                        rec[f"ic_alpha_{a_s}"] = np.nan
                    else:
                        rec[f"ic_alpha_{a_s}"] = float(stats.spearmanr(sc, y_ret)[0])

                rec["is_valid"] = True

            all_daily_records.append(rec)

        del df_val, val_scores_dict

    # 3. Tạo bảng Daily IC
    log("\n[3/4] Xây dựng bảng Daily IC và tính toán thống kê so sánh...")
    df_daily_ic = pd.DataFrame(all_daily_records)
    total_eval_sessions = len(df_daily_ic)

    # Kiểm tra đối chiếu mốc alpha=1.0 với kết quả trước đó
    mean_ic_alpha1 = float(df_daily_ic["ic_alpha_1"].mean())
    log(f"  [ĐỐI CHIẾU MỐC ALPHA=1.0]:")
    log(f"    - Số phiên tính được: {total_eval_sessions} (Kỳ vọng: 1253 phiên)")
    log(f"    - Mean Daily Rank IC alpha=1: {mean_ic_alpha1:+.6f} (Kỳ vọng: +0.016497)")
    assert total_eval_sessions == 1253, f"Số phiên {total_eval_sessions} != 1253!"
    assert np.isclose(mean_ic_alpha1, 0.01649668, atol=1e-5), f"Mean IC alpha=1 {mean_ic_alpha1} lệch khỏi mốc trước!"
    log("    -> XÁC NHẬN: Kết quả alpha=1.0 TRÙNG KHỚP HOÀN TOÀN với lượt trước!")

    # 4. Thống kê chi tiết theo Alpha và Năm
    years = [2019, 2020, 2021, 2022, 2023]
    summary_rows = []

    # Benchmark stats
    bench_overall = summarize_series(df_daily_ic["ic_ret_20d"])
    bench_by_year = {yr: summarize_series(df_daily_ic.loc[df_daily_ic["val_year"] == yr, "ic_ret_20d"]) for yr in years}

    for alpha in alpha_grid:
        a_s = f"{int(alpha)}" if alpha == int(alpha) else f"{alpha}"
        col_name = f"ic_alpha_{a_s}"
        diff_col = df_daily_ic[col_name] - df_daily_ic["ic_alpha_1"]

        ov_stats = summarize_series(df_daily_ic[col_name])
        ov_diff = float(diff_col.mean())

        row = {
            "alpha": float(alpha),
            "alpha_label": a_s,
            "overall_mean_ic": ov_stats["mean_ic"],
            "overall_diff_vs_alpha1": ov_diff,
            "overall_positive_ratio": ov_stats["positive_ic_ratio"],
            "overall_annual_ir": ov_stats["ic_ir_annualized"],
            "overall_t_stat": ov_stats["t_statistic"],
            "evaluable_days": ov_stats["evaluable_days"],
        }

        # Từng năm
        for yr in years:
            sub_yr = df_daily_ic[df_daily_ic["val_year"] == yr]
            yr_stats = summarize_series(sub_yr[col_name])
            yr_diff = float((sub_yr[col_name] - sub_yr["ic_alpha_1"]).mean())
            row[f"mean_ic_{yr}"] = yr_stats["mean_ic"]
            row[f"diff_{yr}_vs_alpha1"] = yr_diff
            row[f"pos_ratio_{yr}"] = yr_stats["positive_ic_ratio"]

        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows)

    # 5. Phân tích đề xuất lựa chọn alpha
    best_row = df_summary.loc[df_summary["overall_mean_ic"].idxmax()]
    best_alpha = float(best_row["alpha"])
    best_alpha_str = best_row["alpha_label"]
    best_mean_ic = float(best_row["overall_mean_ic"])
    best_diff = float(best_row["overall_diff_vs_alpha1"])

    # Đánh giá tính nhất quán qua các năm của best alpha so với alpha=1
    better_years_count = sum(best_row[f"diff_{yr}_vs_alpha1"] > 0 for yr in years)

    # Tổng kết metadata
    total_elapsed = time.time() - t_start
    grid_meta = {
        "experiment_name": "ridge_alpha_grid_search_5folds",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": total_elapsed,
        "alpha_grid": [float(a) for a in alpha_grid],
        "parity_check_alpha_1": {
            "expected_mean_ic": 0.016497,
            "actual_mean_ic": mean_ic_alpha1,
            "parity_passed": True,
        },
        "best_alpha_candidate": {
            "alpha": best_alpha,
            "alpha_str": best_alpha_str,
            "overall_mean_ic": best_mean_ic,
            "delta_vs_alpha1": best_diff,
            "better_years_count_out_of_5": int(better_years_count),
        },
        "oos_status": "STRICTLY_FROZEN (2024-2026)",
        "models_coefficients": fold_coefs,
        "summary_table": summary_rows,
    }

    return df_daily_ic, df_summary, grid_meta


def main():
    parser = argparse.ArgumentParser(description="Chạy Grid Search Alpha Ridge trên 5 Fold Walk-Forward.")
    parser.add_argument("--save-artifacts", action="store_true", default=True, help="Lưu artifacts.")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df_daily_ic, df_summary, meta = run_ridge_alpha_grid_search()

    if args.save_artifacts:
        log("\n[4/4] Lưu trữ các tệp kết quả Grid Search...")

        # 1. Lưu Daily IC
        df_daily_ic.to_csv(OUTPUT_DAILY_IC_CSV, index=False, float_format="%.6f")
        df_daily_ic.to_parquet(OUTPUT_DAILY_IC_PARQUET, compression="snappy", index=False)
        log(f"  -> Lưu Daily IC: {OUTPUT_DAILY_IC_CSV} và {OUTPUT_DAILY_IC_PARQUET}")

        # 2. Lưu Summary CSV
        df_summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, float_format="%.6f")
        log(f"  -> Lưu Bảng tổng hợp: {OUTPUT_SUMMARY_CSV}")

        # 3. Lưu YAML config
        with open(OUTPUT_RUN_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Lưu Cấu hình YAML: {OUTPUT_RUN_CONFIG_FILE}")

    # Báo cáo tổng kết ra console
    log("\n" + "=" * 115)
    log("KẾT QUẢ GRID SEARCH ALPHA CHO RIDGE TRÊN 5 FOLD WALK-FORWARD (DEVELOPMENT 2019-2023)")
    log("=" * 115)
    header = f"{'Alpha':<10} | {'Mean IC Toàn Bộ':<16} | {'Delta vs a=1':<14} | {'Tỷ lệ Dương':<12} | {'2019':<10} | {'2020':<10} | {'2021':<10} | {'2022':<10} | {'2023':<10}"
    log(header)
    log("-" * 115)

    for _, r in df_summary.iterrows():
        a_lbl = r["alpha_label"]
        log(f"{a_lbl:<10} | {r['overall_mean_ic']:<+16.6f} | {r['overall_diff_vs_alpha1']:<+14.6f} | {r['overall_positive_ratio']*100:>5.2f}%      | {r['mean_ic_2019']:<+10.4f} | {r['mean_ic_2020']:<+10.4f} | {r['mean_ic_2021']:<+10.4f} | {r['mean_ic_2022']:<+10.4f} | {r['mean_ic_2023']:<+10.4f}")

    log("=" * 115)
    best = meta["best_alpha_candidate"]
    log(f"  - Mức Alpha dẫn đầu: alpha = {best['alpha_str']} (Mean IC = {best['overall_mean_ic']:+.6f}, Delta = {best['delta_vs_alpha1']:+.6f})")
    log(f"  - Số năm cải thiện so với alpha=1: {best['better_years_count_out_of_5']}/5 năm")
    log("=" * 115)


if __name__ == "__main__":
    main()
