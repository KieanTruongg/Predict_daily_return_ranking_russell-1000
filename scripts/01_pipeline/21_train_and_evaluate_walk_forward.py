"""
Pipeline Script 21: Train and Evaluate Walk-Forward Baseline v1 (5 Folds Expanding)
==================================================================================
Mục tiêu:
1. Đọc lịch phân chia 5 fold từ configs/walk_forward_schedule_v1.yaml.
2. Với mỗi fold (Fold 1 đến Fold 5):
   - Cắt tập Train và Validation trực tiếp từ data/processed/baseline_dataset_v1.parquet qua ranh giới ngày thực tế.
   - Khởi tạo mới StandardScaler(with_mean=True, with_std=True) và Ridge(alpha=1.0, fit_intercept=True).
   - Fit pipeline trên Train của fold đó (biến X là 13 features Close/Volume, nhãn y là target_rank).
   - Dự đoán trên tập Validation của năm tương ứng để lấy điểm xếp hạng ridge_score.
3. Tính Spearman Rank IC theo từng ngày giao dịch độc lập cho từng năm:
   - Tính Rank IC giữa ridge_score và target_return.
   - Tính Rank IC giữa tín hiệu benchmark ret_20d và target_return trên cùng ngày và cùng mã.
   - Báo cáo: Mean Daily Rank IC, Tỷ lệ ngày IC dương (>0), và Số ngày giao dịch được chấm cho từng năm (2019-2023)
     và tổng hợp toàn bộ 5 năm.
4. Lưu trữ kết quả:
   - Bảng Daily IC: outputs/reports/daily_ic_walk_forward_ridge_alpha1.0.csv và Parquet tương ứng.
   - Bảng Dự đoán Validation: data/processed/val_predictions_walk_forward_ridge_alpha1.0.parquet.
   - Các tệp Model Pipeline đã fit: models/walk_forward/ridge_fold_{k}_alpha1.0.joblib.
   - Cấu hình và tổng hợp kết quả YAML: configs/walk_forward_ridge_alpha1.0_run.yaml.
   - Báo cáo đánh giá: docs/reports/baseline/walk_forward_ridge_alpha1.0_report.md.
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
from sklearn.pipeline import Pipeline
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
MODELS_DIR = PROJECT_ROOT / "models" / "walk_forward"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DOCS_REPORTS_DIR = PROJECT_ROOT / "docs" / "reports" / "baseline"

DATASET_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
SCHEDULE_CONFIG_FILE = CONFIGS_DIR / "walk_forward_schedule_v1.yaml"

OUTPUT_RUN_CONFIG_FILE = CONFIGS_DIR / "walk_forward_ridge_alpha1.0_run.yaml"
OUTPUT_PREDS_FILE = DATA_DIR / "val_predictions_walk_forward_ridge_alpha1.0.parquet"
OUTPUT_DAILY_IC_CSV = REPORTS_DIR / "daily_ic_walk_forward_ridge_alpha1.0.csv"
OUTPUT_DAILY_IC_PARQUET = DATA_DIR / "daily_ic_walk_forward_ridge_alpha1.0.parquet"
OUTPUT_REPORT_MD = DOCS_REPORTS_DIR / "walk_forward_ridge_alpha1.0_report.md"

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


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def compute_spearman_ic_for_series(
    df_val_preds: pd.DataFrame,
    fold_id: int,
    val_year: int,
) -> Tuple[List[dict], dict, dict]:
    """
    Tính Spearman Rank IC theo ngày cho một fold validation.
    """
    daily_records: List[dict] = []

    for dt, group in df_val_preds.groupby("date", sort=True):
        mask = (
            np.isfinite(group["ridge_score"])
            & np.isfinite(group[TARGET_RETURN_COL])
            & np.isfinite(group[BENCHMARK_COL])
        )
        sub = group.loc[mask]
        n_stocks = len(sub)

        if n_stocks < 2:
            daily_records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "fold_id": fold_id,
                "val_year": val_year,
                "n_stocks": n_stocks,
                "ic_ridge": np.nan,
                "ic_ret_20d": np.nan,
                "is_valid": False,
                "reason": "less_than_2_stocks",
            })
            continue

        y = sub[TARGET_RETURN_COL].to_numpy()
        score_ridge = sub["ridge_score"].to_numpy()
        score_bench = sub[BENCHMARK_COL].to_numpy()

        y_is_const = (np.ptp(y) == 0)
        ridge_is_const = (np.ptp(score_ridge) == 0)
        bench_is_const = (np.ptp(score_bench) == 0)

        ic_ridge = np.nan if (y_is_const or ridge_is_const) else float(stats.spearmanr(score_ridge, y)[0])
        ic_bench = np.nan if (y_is_const or bench_is_const) else float(stats.spearmanr(score_bench, y)[0])

        is_valid = np.isfinite(ic_ridge) and np.isfinite(ic_bench)
        daily_records.append({
            "date": dt.strftime("%Y-%m-%d"),
            "fold_id": fold_id,
            "val_year": val_year,
            "n_stocks": n_stocks,
            "ic_ridge": float(ic_ridge) if np.isfinite(ic_ridge) else np.nan,
            "ic_ret_20d": float(ic_bench) if np.isfinite(ic_bench) else np.nan,
            "is_valid": is_valid,
            "reason": "ok" if is_valid else "constant_values",
        })

    # Tính thống kê tổng kết cho fold
    df_records = pd.DataFrame(daily_records)
    ridge_summary = summarize_ic_series(df_records["ic_ridge"])
    bench_summary = summarize_ic_series(df_records["ic_ret_20d"])

    return daily_records, ridge_summary, bench_summary


def summarize_ic_series(series: pd.Series) -> dict:
    valid_s = series.dropna()
    n_total = len(series)
    n_valid = len(valid_s)
    n_undefined = n_total - n_valid

    if n_valid > 0:
        mean_ic = float(valid_s.mean())
        std_ic = float(valid_s.std(ddof=1)) if n_valid > 1 else 0.0
        median_ic = float(valid_s.median())
        pos_ratio = float((valid_s > 0).mean())
        ic_ir = float(mean_ic / std_ic) if std_ic > 1e-12 else 0.0
        annualized_ir = float(ic_ir * np.sqrt(252))
        t_stat = float(mean_ic / (std_ic / np.sqrt(n_valid))) if std_ic > 1e-12 else 0.0
    else:
        mean_ic = std_ic = median_ic = pos_ratio = ic_ir = annualized_ir = t_stat = np.nan

    return {
        "total_days": n_total,
        "evaluable_days": n_valid,
        "undefined_days": n_undefined,
        "mean_ic": mean_ic,
        "median_ic": median_ic,
        "std_ic": std_ic,
        "positive_ic_ratio": pos_ratio,
        "ic_ir_daily": ic_ir,
        "ic_ir_annualized": annualized_ir,
        "t_statistic": t_stat,
    }


def run_walk_forward_evaluation(
    alpha: float = 1.0,
    fit_intercept: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Thực thi toàn bộ quy trình Walk-Forward cho mô hình Ridge(alpha=1.0).
    """
    t_start = time.time()
    log("=" * 80)
    log(f"BẮT ĐẦU CHẠY WALK-FORWARD EVALUATION: RIDGE(alpha={alpha}) TRÊN 5 FOLDS")
    log("=" * 80)

    # 1. Nạp cấu hình Walk-Forward
    log(f"[1/5] Nạp cấu hình lịch Walk-Forward từ: {SCHEDULE_CONFIG_FILE}...")
    if not SCHEDULE_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {SCHEDULE_CONFIG_FILE}")

    with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
        wf_cfg = yaml.safe_load(f)

    # 2. Nạp dataset gốc
    log(f"[2/5] Nạp dataset gốc từ: {DATASET_FILE}...")
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset nguồn: {DATASET_FILE}")

    df_all = pd.read_parquet(DATASET_FILE)
    log(f"  -> Dataset đã nạp: {len(df_all):,} dòng, {len(df_all.columns)} cột.")

    all_val_preds_list: List[pd.DataFrame] = []
    all_daily_ic_records: List[dict] = []
    per_fold_results: List[dict] = []

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Lặp qua từng fold
    log(f"[3/5] Thực hiện huấn luyện và dự đoán độc lập trên từng fold...")
    for fold in wf_cfg["folds"]:
        fid = fold["fold_id"]
        tr_info = fold["train"]
        vl_info = fold["validation"]
        val_year = int(vl_info["period_label"])

        log(f"\n--- [FOLD {fid}/5] Train {tr_info['period_label']} -> Val {val_year} ---")

        # Cắt dữ liệu Train
        t_tr_0 = time.time()
        tr_start = tr_info["actual_start"]
        tr_end = tr_info["actual_end"]
        df_train = df_all.query(f"date >= '{tr_start}' and date <= '{tr_end}'").copy()
        assert len(df_train) == tr_info["clean_rows"], f"Fold {fid} train rows lệch!"

        X_train = df_train[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)
        y_train = df_train[TARGET_RANK_COL].to_numpy(dtype=np.float64)

        # Khởi tạo Pipeline độc lập
        pipeline = Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("ridge", Ridge(alpha=alpha, fit_intercept=fit_intercept, copy_X=False)),
        ])

        pipeline.fit(X_train, y_train)
        tr_elapsed = time.time() - t_tr_0
        ridge_model: Ridge = pipeline.named_steps["ridge"]
        log(f"  -> Huấn luyện Train ({len(df_train):,} dòng) hoàn tất trong {tr_elapsed:.2f}s.")
        log(f"  -> Intercept: {ridge_model.intercept_:.6f}")

        # Lưu model pipeline của fold
        model_path = MODELS_DIR / f"ridge_fold_{fid}_alpha1.0.joblib"
        joblib.dump(pipeline, model_path)

        del df_train, X_train, y_train

        # Cắt dữ liệu Validation
        t_vl_0 = time.time()
        vl_start = vl_info["actual_start"]
        vl_end = vl_info["actual_end"]
        df_val = df_all.query(f"date >= '{vl_start}' and date <= '{vl_end}'").copy()
        assert len(df_val) == vl_info["clean_rows"], f"Fold {fid} val rows lệch!"

        X_val = df_val[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)
        ridge_scores = pipeline.predict(X_val)
        pred_elapsed = time.time() - t_vl_0
        log(f"  -> Dự đoán Validation ({len(df_val):,} dòng, {df_val['date'].nunique()} phiên) hoàn tất trong {pred_elapsed:.2f}s.")

        df_val["ridge_score"] = ridge_scores
        df_val["fold_id"] = fid
        df_val["val_year"] = val_year

        # Bảng dự đoán chuẩn
        keep_cols = ["date", "canonical_sid", "fold_id", "val_year", "ridge_score", TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL]
        sub_preds = df_val[keep_cols].copy()
        all_val_preds_list.append(sub_preds)

        # Tính Rank IC theo ngày
        daily_records, ridge_sum, bench_sum = compute_spearman_ic_for_series(sub_preds, fold_id=fid, val_year=val_year)
        all_daily_ic_records.extend(daily_records)

        log(f"  -> Kết quả IC Năm {val_year} ({ridge_sum['evaluable_days']} phiên):")
        log(f"      * Ridge Rank IC:  Mean = {ridge_sum['mean_ic']:+.6f} | Dương = {ridge_sum['positive_ic_ratio']*100:.2f}% | Annual IR = {ridge_sum['ic_ir_annualized']:+.4f} | t-stat = {ridge_sum['t_statistic']:+.4f}")
        log(f"      * ret_20d (Bench): Mean = {bench_sum['mean_ic']:+.6f} | Dương = {bench_sum['positive_ic_ratio']*100:.2f}% | Annual IR = {bench_sum['ic_ir_annualized']:+.4f} | t-stat = {bench_sum['t_statistic']:+.4f}")

        # Ghi nhận trọng số
        coef_dict = {f: float(c) for f, c in zip(BASELINE_13_FEATURES, ridge_model.coef_)}
        per_fold_results.append({
            "fold_id": fid,
            "val_year": val_year,
            "train_sessions": tr_info["clean_sessions"],
            "train_rows": tr_info["clean_rows"],
            "val_sessions": vl_info["clean_sessions"],
            "val_rows": vl_info["clean_rows"],
            "intercept": float(ridge_model.intercept_),
            "coefficients": coef_dict,
            "ridge_ic_metrics": ridge_sum,
            "bench_ic_metrics": bench_sum,
        })

        del df_val, X_val, ridge_scores

    # 4. Hợp nhất bảng kết quả
    log("\n[4/5] Hợp nhất bảng dự đoán và bảng Daily IC toàn giai đoạn...")
    df_all_val_preds = pd.concat(all_val_preds_list, ignore_index=True)
    df_all_daily_ic = pd.DataFrame(all_daily_ic_records)

    total_eval_sessions = len(df_all_daily_ic)
    total_val_rows = len(df_all_val_preds)
    log(f"  -> Tổng số dòng dự đoán hợp nhất: {total_val_rows:,} dòng.")
    log(f"  -> Tổng số phiên giao dịch được chấm: {total_eval_sessions} phiên.")

    # Thống kê tổng hợp toàn bộ 5 năm
    overall_ridge_metrics = summarize_ic_series(df_all_daily_ic["ic_ridge"])
    overall_bench_metrics = summarize_ic_series(df_all_daily_ic["ic_ret_20d"])

    total_elapsed = time.time() - t_start

    run_meta = {
        "evaluation_name": "walk_forward_ridge_alpha1.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": total_elapsed,
        "alpha": alpha,
        "fit_intercept": fit_intercept,
        "number_of_folds": 5,
        "overall_summary": {
            "total_validation_rows": total_val_rows,
            "total_trading_sessions": total_eval_sessions,
            "ridge_overall_metrics": overall_ridge_metrics,
            "bench_overall_metrics": overall_bench_metrics,
        },
        "per_year_breakdown": per_fold_results,
    }

    return df_all_val_preds, df_all_daily_ic, run_meta


def main():
    parser = argparse.ArgumentParser(description="Chạy Walk-Forward 5 Folds cho Ridge(alpha=1.0).")
    parser.add_argument("--save-artifacts", action="store_true", default=True, help="Lưu các tệp artifacts.")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df_preds, df_daily_ic, run_meta = run_walk_forward_evaluation(alpha=1.0, fit_intercept=True)

    if args.save_artifacts:
        log("\n[5/5] Lưu trữ Artifacts Bảng dự đoán, Bảng Daily IC, Cấu hình YAML và Báo cáo...")

        # 1. Lưu predictions Parquet
        df_preds.to_parquet(OUTPUT_PREDS_FILE, compression="snappy", index=False)
        preds_mb = OUTPUT_PREDS_FILE.stat().st_size / (1024 * 1024)
        log(f"  -> Đã lưu Validation Predictions: {OUTPUT_PREDS_FILE} ({len(df_preds):,} dòng, {preds_mb:.2f} MB)")

        # 2. Lưu Daily IC CSV & Parquet
        df_daily_ic.to_csv(OUTPUT_DAILY_IC_CSV, index=False, float_format="%.6f")
        df_daily_ic.to_parquet(OUTPUT_DAILY_IC_PARQUET, compression="snappy", index=False)
        log(f"  -> Đã lưu Daily IC Table: {OUTPUT_DAILY_IC_CSV} và {OUTPUT_DAILY_IC_PARQUET}")

        # 3. Lưu YAML config
        with open(OUTPUT_RUN_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(run_meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Đã lưu Cấu hình tái lập: {OUTPUT_RUN_CONFIG_FILE}")

    # In Bảng Tóm Tắt Ra Console
    log("\n" + "=" * 105)
    log("TỔNG HỢP KẾT QUẢ WALK-FORWARD RIDGE(alpha=1.0) SO VỚI BENCHMARK RET_20D THEO TỪNG NĂM")
    log("=" * 105)
    header = f"{'Năm':<6} | {'Số Ngày':<8} | {'Mean IC (Ridge)':<16} | {'Tỷ lệ Dương (Ridge)':<20} | {'Mean IC (ret_20d)':<18} | {'Tỷ lệ Dương (ret_20d)'}"
    log(header)
    log("-" * 105)

    for fold in run_meta["per_year_breakdown"]:
        yr = fold["val_year"]
        r = fold["ridge_ic_metrics"]
        b = fold["bench_ic_metrics"]
        log(f"{yr:<6} | {r['evaluable_days']:<8} | {r['mean_ic']:<+16.6f} | {r['positive_ic_ratio']*100:>6.2f}%              | {b['mean_ic']:<+18.6f} | {b['positive_ic_ratio']*100:>6.2f}%")

    log("-" * 105)
    ov_r = run_meta["overall_summary"]["ridge_overall_metrics"]
    ov_b = run_meta["overall_summary"]["bench_overall_metrics"]
    log(f"{'TỔNG':<6} | {ov_r['evaluable_days']:<8} | {ov_r['mean_ic']:<+16.6f} | {ov_r['positive_ic_ratio']*100:>6.2f}%              | {ov_b['mean_ic']:<+18.6f} | {ov_b['positive_ic_ratio']*100:>6.2f}%")
    log("=" * 105)


if __name__ == "__main__":
    main()
