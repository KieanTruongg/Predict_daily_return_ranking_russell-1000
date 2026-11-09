"""
Pipeline Script 23: Train and Evaluate GBDT Baseline (5 Folds Walk-Forward)
==========================================================================
Mục tiêu:
1. Huấn luyện mô hình phi tuyến đầu tiên (GBDT Regression) trên 5 fold Expanding Window:
   - Thuật toán: sklearn.ensemble.HistGradientBoostingRegressor
   - Siêu tham số cố định:
     loss="squared_error", max_iter=100, learning_rate=0.05, max_leaf_nodes=15,
     min_samples_leaf=100, early_stopping=False, random_state=42
   - Tập biến X: Đúng 13 features Close/Volume thô từ baseline_dataset_v1.parquet (không cần scale).
   - Nhãn huấn luyện y: target_rank in [0, 1].
   - Nhãn đánh giá: target_return (Close-to-Close return T -> T+1).
2. Đối chiếu nghiêm ngặt với mốc Ridge alpha=1.0:
   - Kiểm tra cặp khóa (date, canonical_sid) khớp 100% với bảng dự đoán của Ridge (1.202.259 dòng, 1.253 phiên).
   - Đảm bảo tính công bằng: cùng tập dữ liệu, cùng ranh giới purge, cùng tập mã, cùng ngày giao dịch.
   - Đối chiếu mốc Ridge: Mean Daily Rank IC = +0.016497 trên 1.253 phiên.
3. Đánh giá Spearman Rank IC theo ngày:
   - Tính Rank IC của GBDT và đối chiếu với Ridge alpha=1.0 và Benchmark ret_20d trên từng phiên.
   - Báo cáo chi tiết từng năm (2019-2023) và tổng hợp toàn bộ 5 năm:
     Mean Daily Rank IC, Tỷ lệ ngày dương, Delta IC vs Ridge, Win-rate vs Ridge, Annualized IR, t-statistic.
   - Ghi nhận thời gian fit/predict cho từng fold.
4. Lưu trữ artifacts:
   - configs/walk_forward_gbdt_baseline_run.yaml
   - data/processed/val_predictions_walk_forward_gbdt.parquet
   - outputs/reports/daily_ic_walk_forward_gbdt_vs_ridge.csv & parquet
   - outputs/reports/summary_walk_forward_gbdt_vs_ridge.csv
   - models/walk_forward_gbdt/gbdt_fold_{k}.joblib
   - docs/reports/baseline/walk_forward_gbdt_vs_ridge_report.md
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
from sklearn.ensemble import HistGradientBoostingRegressor
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
MODELS_DIR = PROJECT_ROOT / "models" / "walk_forward_gbdt"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DOCS_REPORTS_DIR = PROJECT_ROOT / "docs" / "reports" / "baseline"

DATASET_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
SCHEDULE_CONFIG_FILE = CONFIGS_DIR / "walk_forward_schedule_v1.yaml"
RIDGE_PREDS_FILE = DATA_DIR / "val_predictions_walk_forward_ridge_alpha1.0.parquet"

OUTPUT_RUN_CONFIG_FILE = CONFIGS_DIR / "walk_forward_gbdt_baseline_run.yaml"
OUTPUT_PREDS_FILE = DATA_DIR / "val_predictions_walk_forward_gbdt.parquet"
OUTPUT_DAILY_IC_CSV = REPORTS_DIR / "daily_ic_walk_forward_gbdt_vs_ridge.csv"
OUTPUT_DAILY_IC_PARQUET = DATA_DIR / "daily_ic_walk_forward_gbdt_vs_ridge.parquet"
OUTPUT_SUMMARY_CSV = REPORTS_DIR / "summary_walk_forward_gbdt_vs_ridge.csv"
OUTPUT_REPORT_MD = DOCS_REPORTS_DIR / "walk_forward_gbdt_vs_ridge_report.md"

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

GBDT_PARAMS = {
    "loss": "squared_error",
    "max_iter": 100,
    "learning_rate": 0.05,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 100,
    "early_stopping": False,
    "random_state": 42,
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def summarize_ic_series(s: pd.Series) -> dict:
    valid_s = s.dropna()
    n_tot = len(s)
    n_val = len(valid_s)
    if n_val > 0:
        mean_v = float(valid_s.mean())
        std_v = float(valid_s.std(ddof=1)) if n_val > 1 else 0.0
        median_v = float(valid_s.median())
        pos_r = float((valid_s > 0).mean())
        ir_daily = float(mean_v / std_v) if std_v > 1e-12 else 0.0
        ir_ann = float(ir_daily * np.sqrt(252))
        t_stat = float(mean_v / (std_v / np.sqrt(n_val))) if std_v > 1e-12 else 0.0
    else:
        mean_v = std_v = median_v = pos_r = ir_daily = ir_ann = t_stat = np.nan

    return {
        "evaluable_days": n_val,
        "mean_ic": mean_v,
        "median_ic": median_v,
        "std_ic": std_v,
        "positive_ic_ratio": pos_r,
        "ic_ir_daily": ir_daily,
        "ic_ir_annualized": ir_ann,
        "t_statistic": t_stat,
    }


def run_gbdt_walk_forward_evaluation() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Thực hiện huấn luyện và đánh giá GBDT regression trên 5 fold Walk-Forward,
    so sánh đối chiếu trực tiếp với Ridge alpha=1.0.
    """
    t_start = time.time()
    log("=" * 95)
    log("BẮT ĐẦU CHẠY WALK-FORWARD GBDT BASELINE (HISTGRADIENTBOOSTING) TRÊN 5 FOLDS")
    log("=" * 95)

    # 1. Nạp cấu hình Walk-Forward
    if not SCHEDULE_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy cấu hình: {SCHEDULE_CONFIG_FILE}")

    with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
        wf_cfg = yaml.safe_load(f)

    # 2. Nạp dataset gốc
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset nguồn: {DATASET_FILE}")

    log(f"[1/5] Nạp dataset nguồn từ: {DATASET_FILE}...")
    df_all = pd.read_parquet(DATASET_FILE)
    log(f"  -> Đã nạp: {len(df_all):,} dòng, {len(df_all.columns)} cột.")

    # 3. Nạp dự đoán của Ridge để đối soát cặp khóa
    log(f"[2/5] Nạp dự đoán của Ridge baseline từ: {RIDGE_PREDS_FILE}...")
    if not RIDGE_PREDS_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy predictions của Ridge: {RIDGE_PREDS_FILE}")

    df_ridge_preds = pd.read_parquet(RIDGE_PREDS_FILE)
    n_expected_val_rows = len(df_ridge_preds)
    log(f"  -> Ridge predictions: {n_expected_val_rows:,} dòng, {df_ridge_preds['date'].nunique()} phiên.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_val_preds_list: List[pd.DataFrame] = []
    all_daily_records: List[dict] = []
    fold_timing_records: List[dict] = []

    # 4. Lặp qua từng fold
    log(f"[3/5] Huấn luyện và dự đoán GBDT trên 5 folds...")
    for fold in wf_cfg["folds"]:
        fid = fold["fold_id"]
        tr_info = fold["train"]
        vl_info = fold["validation"]
        val_year = int(vl_info["period_label"])

        log(f"\n--- [FOLD {fid}/5] Train {tr_info['period_label']} -> Val {val_year} ---")

        # Cắt Train (dùng 13 feature thô)
        df_train = df_all.query(f"date >= '{tr_info['actual_start']}' and date <= '{tr_info['actual_end']}'").copy()
        assert len(df_train) == tr_info["clean_rows"], f"Fold {fid} train rows lệch!"

        X_train = df_train[BASELINE_13_FEATURES].to_numpy(dtype=np.float32)
        y_train = df_train[TARGET_RANK_COL].to_numpy(dtype=np.float32)

        # Khởi tạo model GBDT
        model = HistGradientBoostingRegressor(**GBDT_PARAMS)

        # Fit model
        t_fit_0 = time.time()
        model.fit(X_train, y_train)
        fit_sec = time.time() - t_fit_0
        log(f"  -> Fit GBDT Train ({len(df_train):,} dòng) hoàn tất trong {fit_sec:.2f}s.")

        # Lưu model
        model_path = MODELS_DIR / f"gbdt_fold_{fid}.joblib"
        joblib.dump(model, model_path)

        del df_train, X_train, y_train

        # Cắt Validation
        df_val = df_all.query(f"date >= '{vl_info['actual_start']}' and date <= '{vl_info['actual_end']}'").copy()
        assert len(df_val) == vl_info["clean_rows"], f"Fold {fid} val rows lệch!"

        X_val = df_val[BASELINE_13_FEATURES].to_numpy(dtype=np.float32)

        # Predict
        t_pred_0 = time.time()
        gbdt_scores = model.predict(X_val)
        pred_sec = time.time() - t_pred_0
        log(f"  -> Predict GBDT Val ({len(df_val):,} dòng) hoàn tất trong {pred_sec:.2f}s.")

        df_val["gbdt_score"] = gbdt_scores
        df_val["fold_id"] = fid
        df_val["val_year"] = val_year

        fold_timing_records.append({
            "fold_id": fid,
            "val_year": val_year,
            "train_rows": tr_info["clean_rows"],
            "val_rows": vl_info["clean_rows"],
            "fit_time_sec": float(fit_sec),
            "predict_time_sec": float(pred_sec),
        })

        # Lưu dự đoán fold
        keep_cols = ["date", "canonical_sid", "fold_id", "val_year", "gbdt_score", TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL]
        all_val_preds_list.append(df_val[keep_cols].copy())

        del df_val, X_val, gbdt_scores

    # 5. Hợp nhất dự đoán GBDT và đối chiếu khóa với Ridge
    log("\n[4/5] Hợp nhất dự đoán và đối chiếu cặp khóa với Ridge alpha=1.0...")
    df_all_gbdt_preds = pd.concat(all_val_preds_list, ignore_index=True)
    assert len(df_all_gbdt_preds) == n_expected_val_rows, f"Số dòng dự đoán {len(df_all_gbdt_preds)} != Ridge {n_expected_val_rows}"

    # Merge với Ridge predictions để lấy ridge_score cho từng dòng
    df_merged = pd.merge(
        df_all_gbdt_preds,
        df_ridge_preds[["date", "canonical_sid", "ridge_score"]],
        on=["date", "canonical_sid"],
        how="inner",
    )

    assert len(df_merged) == n_expected_val_rows, (
        f"Lệch cặp khóa giữa GBDT và Ridge! Khớp được {len(df_merged)}/{n_expected_val_rows} dòng."
    )
    log(f"  [OK] Cặp khóa (date, canonical_sid) KHỚP CHÍNH XÁC 100% với Ridge ({len(df_merged):,} dòng, 1.253 phiên).")

    # 6. Tính toán Spearman Rank IC theo ngày cho GBDT, Ridge và Benchmark
    log("[5/5] Tính toán Spearman Rank IC theo ngày và phân tích so sánh...")
    for dt, group in df_merged.groupby("date", sort=True):
        y_ret = group[TARGET_RETURN_COL].to_numpy()
        gbdt_sc = group["gbdt_score"].to_numpy()
        ridge_sc = group["ridge_score"].to_numpy()
        bench_ret20 = group[BENCHMARK_COL].to_numpy()
        n_stk = len(group)
        fid = int(group["fold_id"].iloc[0])
        val_yr = int(group["val_year"].iloc[0])

        rec = {
            "date": dt.strftime("%Y-%m-%d"),
            "fold_id": fid,
            "val_year": val_yr,
            "n_stocks": n_stk,
        }

        if n_stk < 2 or (np.ptp(y_ret) == 0):
            rec["ic_gbdt"] = np.nan
            rec["ic_ridge"] = np.nan
            rec["ic_ret_20d"] = np.nan
            rec["diff_gbdt_vs_ridge"] = np.nan
            rec["gbdt_beats_ridge"] = False
            rec["is_valid"] = False
        else:
            ic_gb = float(stats.spearmanr(gbdt_sc, y_ret)[0]) if np.ptp(gbdt_sc) > 0 else np.nan
            ic_rd = float(stats.spearmanr(ridge_sc, y_ret)[0]) if np.ptp(ridge_sc) > 0 else np.nan
            ic_bm = float(stats.spearmanr(bench_ret20, y_ret)[0]) if np.ptp(bench_ret20) > 0 else np.nan

            diff = ic_gb - ic_rd if (np.isfinite(ic_gb) and np.isfinite(ic_rd)) else np.nan
            beats = (ic_gb > ic_rd) if (np.isfinite(ic_gb) and np.isfinite(ic_rd)) else False

            rec["ic_gbdt"] = ic_gb
            rec["ic_ridge"] = ic_rd
            rec["ic_ret_20d"] = ic_bm
            rec["diff_gbdt_vs_ridge"] = diff
            rec["gbdt_beats_ridge"] = beats
            rec["is_valid"] = True

        all_daily_records.append(rec)

    df_daily_ic = pd.DataFrame(all_daily_records)
    total_eval_sessions = len(df_daily_ic)

    # Đối chiếu mốc Ridge
    mean_ic_ridge_actual = float(df_daily_ic["ic_ridge"].mean())
    log(f"  [ĐỐI CHIẾU MỐC RIDGE ALPHA=1.0]:")
    log(f"    - Số phiên tính được: {total_eval_sessions} (Kỳ vọng: 1.253)")
    log(f"    - Mean Daily Rank IC Ridge: {mean_ic_ridge_actual:+.6f} (Kỳ vọng: +0.016497)")
    assert np.isclose(mean_ic_ridge_actual, 0.01649668, atol=1e-5), "Lệch mốc Ridge!"
    log("    -> XÁC NHẬN: Mốc đối chiếu Ridge alpha=1.0 TRÙNG KHỚP HOÀN TOÀN!")

    # 7. Thống kê theo năm và tổng thể
    years = [2019, 2020, 2021, 2022, 2023]
    summary_rows = []

    for yr in years:
        sub = df_daily_ic[df_daily_ic["val_year"] == yr]
        gb_s = summarize_ic_series(sub["ic_gbdt"])
        rd_s = summarize_ic_series(sub["ic_ridge"])
        bm_s = summarize_ic_series(sub["ic_ret_20d"])

        diff_mean = float((sub["ic_gbdt"] - sub["ic_ridge"]).mean())
        win_rate = float(sub["gbdt_beats_ridge"].mean())

        summary_rows.append({
            "period": str(yr),
            "evaluable_days": gb_s["evaluable_days"],
            "gbdt_mean_ic": gb_s["mean_ic"],
            "gbdt_pos_ratio": gb_s["positive_ic_ratio"],
            "gbdt_annual_ir": gb_s["ic_ir_annualized"],
            "ridge_mean_ic": rd_s["mean_ic"],
            "ridge_pos_ratio": rd_s["positive_ic_ratio"],
            "ridge_annual_ir": rd_s["ic_ir_annualized"],
            "diff_gbdt_minus_ridge": diff_mean,
            "gbdt_win_rate_vs_ridge": win_rate,
            "bench_mean_ic": bm_s["mean_ic"],
        })

    # Tổng kết 5 năm
    gb_tot = summarize_ic_series(df_daily_ic["ic_gbdt"])
    rd_tot = summarize_ic_series(df_daily_ic["ic_ridge"])
    bm_tot = summarize_ic_series(df_daily_ic["ic_ret_20d"])
    tot_diff = float((df_daily_ic["ic_gbdt"] - df_daily_ic["ic_ridge"]).mean())
    tot_win = float(df_daily_ic["gbdt_beats_ridge"].mean())

    summary_rows.append({
        "period": "TỔNG 5 NĂM",
        "evaluable_days": gb_tot["evaluable_days"],
        "gbdt_mean_ic": gb_tot["mean_ic"],
        "gbdt_pos_ratio": gb_tot["positive_ic_ratio"],
        "gbdt_annual_ir": gb_tot["ic_ir_annualized"],
        "ridge_mean_ic": rd_tot["mean_ic"],
        "ridge_pos_ratio": rd_tot["positive_ic_ratio"],
        "ridge_annual_ir": rd_tot["ic_ir_annualized"],
        "diff_gbdt_minus_ridge": tot_diff,
        "gbdt_win_rate_vs_ridge": tot_win,
        "bench_mean_ic": bm_tot["mean_ic"],
    })

    df_summary = pd.DataFrame(summary_rows)

    total_elapsed = time.time() - t_start

    run_meta = {
        "experiment_name": "walk_forward_gbdt_vs_ridge_alpha1.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": total_elapsed,
        "model_type": "HistGradientBoostingRegressor",
        "model_hyperparameters": GBDT_PARAMS,
        "input_features": BASELINE_13_FEATURES,
        "feature_scaling": "None (raw features for trees, compared against scaled Ridge)",
        "oos_status": "STRICTLY_FROZEN (2024-2026)",
        "parity_check_ridge": {
            "expected_mean_ic": 0.016497,
            "actual_mean_ic": mean_ic_ridge_actual,
            "parity_passed": True,
        },
        "fold_timings": fold_timing_records,
        "summary_table": summary_rows,
    }

    return df_all_gbdt_preds, df_daily_ic, df_summary, run_meta


def main():
    parser = argparse.ArgumentParser(description="Chạy Walk-Forward GBDT Baseline so với Ridge alpha=1.0.")
    parser.add_argument("--save-artifacts", action="store_true", default=True, help="Lưu artifacts.")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df_preds, df_daily_ic, df_summary, meta = run_gbdt_walk_forward_evaluation()

    if args.save_artifacts:
        log("\n[Lưu Trữ Artifacts]")

        # 1. Lưu predictions Parquet
        df_preds.to_parquet(OUTPUT_PREDS_FILE, compression="snappy", index=False)
        p_mb = OUTPUT_PREDS_FILE.stat().st_size / (1024 * 1024)
        log(f"  -> Lưu GBDT Predictions: {OUTPUT_PREDS_FILE} ({len(df_preds):,} dòng, {p_mb:.2f} MB)")

        # 2. Lưu Daily IC
        df_daily_ic.to_csv(OUTPUT_DAILY_IC_CSV, index=False, float_format="%.6f")
        df_daily_ic.to_parquet(OUTPUT_DAILY_IC_PARQUET, compression="snappy", index=False)
        log(f"  -> Lưu Daily IC: {OUTPUT_DAILY_IC_CSV} và {OUTPUT_DAILY_IC_PARQUET}")

        # 3. Lưu Summary CSV
        df_summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, float_format="%.6f")
        log(f"  -> Lưu Bảng tổng hợp: {OUTPUT_SUMMARY_CSV}")

        # 4. Lưu Run Config YAML
        with open(OUTPUT_RUN_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Lưu Cấu hình YAML: {OUTPUT_RUN_CONFIG_FILE}")

    # Báo cáo tổng kết ra console
    log("\n" + "=" * 115)
    log("TỔNG HỢP KẾT QUẢ WALK-FORWARD GBDT REGRESSION SO VỚI RIDGE ALPHA=1.0 (2019-2023)")
    log("=" * 115)
    header = f"{'Giai Đoạn':<11} | {'Số Ngày':<8} | {'Mean IC (GBDT)':<15} | {'Dương GBDT':<11} | {'Mean IC (Ridge)':<16} | {'Dương Ridge':<12} | {'Delta (GBDT - Ridge)':<22} | {'Win Rate'}"
    log(header)
    log("-" * 115)

    for _, r in df_summary.iterrows():
        log(
            f"{r['period']:<11} | {r['evaluable_days']:<8} | {r['gbdt_mean_ic']:<+15.6f} | "
            f"{r['gbdt_pos_ratio']*100:>5.2f}%     | {r['ridge_mean_ic']:<+16.6f} | "
            f"{r['ridge_pos_ratio']*100:>5.2f}%      | {r['diff_gbdt_minus_ridge']:<+22.6f} | {r['gbdt_win_rate_vs_ridge']*100:>5.2f}%"
        )

    log("=" * 115)


if __name__ == "__main__":
    main()
