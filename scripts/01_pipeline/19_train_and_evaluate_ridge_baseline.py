"""
Pipeline Script 19: Train and Evaluate Ridge Baseline v1
=========================================================
Mục tiêu:
1. Huấn luyện mô hình Ridge Baseline v1 trên tập Train (2000-2018 sau purge, 4.307.308 dòng).
   - Pipeline: StandardScaler(with_mean=True, with_std=True) + Ridge(alpha=1.0, fit_intercept=True).
   - Biến độc lập X: Đúng 13 features Close/Volume theo baseline_dataset_v1.md.
   - Nhãn huấn luyện y: target_rank (cross-sectional rank chuẩn hóa [0, 1]).
   - Nhãn đánh giá: target_return (split-adjusted return từ Close T sang Close T+1).
2. Dự đoán trên tập Validation (2019-2023, 1.206.096 dòng).
   - Xuất điểm dự đoán Ridge gốc (ridge_score) phục vụ xếp hạng chéo ngang.
   - Lưu trữ pipeline đã fit và metadata cấu hình để tái lập 100%.
3. Đánh giá hiệu năng bằng Spearman Rank Information Coefficient (Rank IC):
   - Tính toán theo từng ngày giao dịch (cross-sectional daily IC) giữa ridge_score và target_return.
   - Tính benchmark IC cho tín hiệu đơn lẻ ret_20d (momentum 20 ngày, giá trị cao hơn = điểm cao hơn).
   - So sánh trên cùng tập mã và cùng ngày giao dịch hợp lệ.
   - Xử lý góc: Ngày có dưới 2 mã hoặc phương sai bằng 0 gán NaN và đếm riêng.
   - Báo cáo: Mean IC, Positive IC Ratio, IC IR, Annualized IC IR, t-statistic, số ngày tính được.
4. Kiểm định tính toàn vẹn kết quả và lưu trữ:
   - data/processed/val_predictions_ridge_v1.parquet (1.206.096 dòng)
   - outputs/reports/daily_ic_ridge_vs_ret20d_v1.csv
   - data/processed/daily_ic_ridge_vs_ret20d_v1.parquet
   - models/ridge_baseline_v1.joblib
   - configs/ridge_baseline_run_v1.yaml
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
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

TRAIN_FILE = DATA_DIR / "train_baseline_v1.parquet"
VAL_FILE = DATA_DIR / "val_baseline_v1.parquet"
SPLIT_CONFIG_FILE = CONFIGS_DIR / "baseline_split_v1.yaml"

MODEL_OUTPUT_FILE = MODELS_DIR / "ridge_baseline_v1.joblib"
RUN_CONFIG_FILE = CONFIGS_DIR / "ridge_baseline_run_v1.yaml"
VAL_PRED_OUTPUT_FILE = DATA_DIR / "val_predictions_ridge_v1.parquet"
DAILY_IC_CSV_FILE = REPORTS_DIR / "daily_ic_ridge_vs_ret20d_v1.csv"
DAILY_IC_PARQUET_FILE = DATA_DIR / "daily_ic_ridge_vs_ret20d_v1.parquet"

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

KEY_COLS = ["date", "canonical_sid"]
TARGET_RANK_COL = "target_rank"
TARGET_RETURN_COL = "target_return"
BENCHMARK_COL = "ret_20d"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def compute_daily_spearman_ic(
    df_preds: pd.DataFrame,
    score_col: str = "ridge_score",
    benchmark_col: str = BENCHMARK_COL,
    target_col: str = TARGET_RETURN_COL,
) -> Tuple[pd.DataFrame, Dict[str, dict]]:
    """
    Tính Spearman Rank Information Coefficient (Rank IC) theo từng ngày giao dịch
    giữa điểm dự đoán (ridge_score / benchmark) và lợi suất thực tế (target_return).
    """
    daily_records: List[dict] = []

    # Nhóm theo date
    for dt, group in df_preds.groupby("date", sort=True):
        # Lọc các dòng hợp lệ có đầy đủ giá trị hữu hạn
        mask_valid = (
            np.isfinite(group[score_col])
            & np.isfinite(group[target_col])
            & np.isfinite(group[benchmark_col])
        )
        sub = group.loc[mask_valid]
        n_stocks = len(sub)

        # Góc 1: Số mã < 2
        if n_stocks < 2:
            daily_records.append({
                "date": dt,
                "n_stocks": n_stocks,
                "ic_ridge": np.nan,
                "ic_ret_20d": np.nan,
                "is_valid": False,
                "reason": "less_than_2_stocks",
            })
            continue

        # Góc 2: Kiểm tra hằng số (phương sai = 0)
        y = sub[target_col].to_numpy()
        score_ridge = sub[score_col].to_numpy()
        score_bench = sub[benchmark_col].to_numpy()

        y_is_const = (np.ptp(y) == 0)
        ridge_is_const = (np.ptp(score_ridge) == 0)
        bench_is_const = (np.ptp(score_bench) == 0)

        # Tính Spearman IC cho Ridge
        if y_is_const or ridge_is_const:
            ic_ridge = np.nan
        else:
            ic_ridge, _ = stats.spearmanr(score_ridge, y)

        # Tính Spearman IC cho Benchmark (ret_20d)
        if y_is_const or bench_is_const:
            ic_bench = np.nan
        else:
            ic_bench, _ = stats.spearmanr(score_bench, y)

        is_valid = np.isfinite(ic_ridge) and np.isfinite(ic_bench)
        daily_records.append({
            "date": dt,
            "n_stocks": n_stocks,
            "ic_ridge": float(ic_ridge) if np.isfinite(ic_ridge) else np.nan,
            "ic_ret_20d": float(ic_bench) if np.isfinite(ic_bench) else np.nan,
            "is_valid": is_valid,
            "reason": "ok" if is_valid else "constant_values",
        })

    df_daily_ic = pd.DataFrame(daily_records)

    # Thống kê tổng hợp cho từng phương pháp
    stats_summary = {}
    for col, name in [("ic_ridge", "Ridge (13 features)"), ("ic_ret_20d", "Benchmark (ret_20d)")]:
        valid_series = df_daily_ic[col].dropna()
        n_total_days = len(df_daily_ic)
        n_valid_days = len(valid_series)
        n_undefined_days = n_total_days - n_valid_days

        if n_valid_days > 0:
            mean_ic = float(valid_series.mean())
            std_ic = float(valid_series.std(ddof=1)) if n_valid_days > 1 else 0.0
            median_ic = float(valid_series.median())
            pos_ratio = float((valid_series > 0).mean())
            ic_ir = float(mean_ic / std_ic) if std_ic > 1e-12 else 0.0
            annualized_ir = float(ic_ir * np.sqrt(252))
            t_stat = float(mean_ic / (std_ic / np.sqrt(n_valid_days))) if std_ic > 1e-12 else 0.0
        else:
            mean_ic = std_ic = median_ic = pos_ratio = ic_ir = annualized_ir = t_stat = np.nan

        stats_summary[col] = {
            "method_name": name,
            "total_trading_days": n_total_days,
            "evaluable_days": n_valid_days,
            "undefined_days": n_undefined_days,
            "mean_ic": mean_ic,
            "median_ic": median_ic,
            "std_ic": std_ic,
            "positive_ic_ratio": pos_ratio,
            "ic_ir_daily": ic_ir,
            "ic_ir_annualized": annualized_ir,
            "t_statistic": t_stat,
        }

    return df_daily_ic, stats_summary


def extract_example_date_details(
    df_preds: pd.DataFrame,
    example_date_str: str = "2019-01-02",
) -> dict:
    """
    Trích xuất chi tiết bước tính IC cho một phiên giao dịch ví dụ để đối chiếu.
    """
    example_dt = pd.Timestamp(example_date_str)
    sub = df_preds[df_preds["date"] == example_dt].copy()

    if sub.empty:
        raise ValueError(f"Không tìm thấy phiên {example_date_str} trong dữ liệu dự đoán!")

    n_stocks = len(sub)
    y = sub[TARGET_RETURN_COL].to_numpy()
    score_ridge = sub["ridge_score"].to_numpy()
    score_bench = sub[BENCHMARK_COL].to_numpy()

    # Xếp hạng thủ công (average rank)
    y_rank = pd.Series(y).rank(method="average").to_numpy()
    ridge_rank = pd.Series(score_ridge).rank(method="average").to_numpy()
    bench_rank = pd.Series(score_bench).rank(method="average").to_numpy()

    # Tính hệ số Pearson trên ranks
    pearson_ridge = float(np.corrcoef(ridge_rank, y_rank)[0, 1])
    pearson_bench = float(np.corrcoef(bench_rank, y_rank)[0, 1])

    spearman_ridge, pval_ridge = stats.spearmanr(score_ridge, y)
    spearman_bench, pval_bench = stats.spearmanr(score_bench, y)

    # Chọn 5 cổ phiếu cao nhất và 5 thấp nhất theo ridge_score để minh họa
    sub_sorted = sub.sort_values("ridge_score", ascending=False)
    top_5 = sub_sorted.head(5)[["canonical_sid", "ridge_score", TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL]].to_dict(orient="records")
    bottom_5 = sub_sorted.tail(5)[["canonical_sid", "ridge_score", TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL]].to_dict(orient="records")

    return {
        "example_date": example_date_str,
        "n_stocks": n_stocks,
        "ridge_ic_spearman": float(spearman_ridge),
        "ridge_p_value": float(pval_ridge),
        "ridge_pearson_on_ranks": pearson_ridge,
        "ret20d_ic_spearman": float(spearman_bench),
        "ret20d_p_value": float(pval_bench),
        "ret20d_pearson_on_ranks": pearson_bench,
        "verification_exact_match": bool(np.isclose(spearman_ridge, pearson_ridge) and np.isclose(spearman_bench, pearson_bench)),
        "top_5_samples": top_5,
        "bottom_5_samples": bottom_5,
    }


def train_and_evaluate_ridge(
    train_path: Path = TRAIN_FILE,
    val_path: Path = VAL_FILE,
    alpha: float = 1.0,
    fit_intercept: bool = True,
) -> Tuple[Pipeline, pd.DataFrame, pd.DataFrame, dict]:
    """
    Thực hiện huấn luyện Ridge baseline trên Train và đánh giá Spearman IC trên Validation.
    """
    t_start = time.time()
    log("=" * 80)
    log("BẮT ĐẦU HUẤN LUYỆN VÀ ĐÁNH GIÁ RIDGE BASELINE V1")
    log("=" * 80)

    # 1. Đọc dữ liệu Train
    log(f"[1/6] Nạp tập huấn luyện Train từ: {train_path}...")
    if not train_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file Train: {train_path}")

    df_train = pd.read_parquet(train_path)
    log(f"  -> Train đã nạp: {len(df_train):,} dòng, {len(df_train.columns)} cột.")
    log(f"  -> Ranh giới Train: {df_train['date'].min():%Y-%m-%d} đến {df_train['date'].max():%Y-%m-%d} ({df_train['date'].nunique()} phiên).")

    X_train = df_train[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)
    y_train = df_train[TARGET_RANK_COL].to_numpy(dtype=np.float64)

    # 2. Xây dựng và Huấn luyện Pipeline
    log(f"[2/6] Khởi tạo và huấn luyện Pipeline: StandardScaler + Ridge(alpha={alpha}, fit_intercept={fit_intercept})...")
    pipeline = Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("ridge", Ridge(alpha=alpha, fit_intercept=fit_intercept, copy_X=False)),
    ])

    t_fit_0 = time.time()
    pipeline.fit(X_train, y_train)
    fit_elapsed = time.time() - t_fit_0
    log(f"  -> Huấn luyện hoàn tất trong {fit_elapsed:.2f} giây.")

    ridge_model: Ridge = pipeline.named_steps["ridge"]
    log(f"  -> Hệ số tự do Intercept: {ridge_model.intercept_:.6f}")
    log("  -> Hệ số trọng số của 13 features (Ridge Coefs):")
    coef_dict = {}
    for feat_name, coef_val in zip(BASELINE_13_FEATURES, ridge_model.coef_):
        coef_dict[feat_name] = float(coef_val)
        log(f"      * {feat_name:24s}: {coef_val:+10.6f}")

    # Giải phóng bộ nhớ X_train, y_train, df_train
    del df_train, X_train, y_train

    # 3. Nạp tập Validation và Dự đoán
    log(f"[3/6] Nạp tập kiểm định Validation từ: {val_path}...")
    if not val_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file Validation: {val_path}")

    df_val = pd.read_parquet(val_path)
    n_val_rows = len(df_val)
    log(f"  -> Validation đã nạp: {n_val_rows:,} dòng, {len(df_val.columns)} cột.")
    log(f"  -> Ranh giới Validation: {df_val['date'].min():%Y-%m-%d} đến {df_val['date'].max():%Y-%m-%d} ({df_val['date'].nunique()} phiên).")

    log("[4/6] Thực hiện dự đoán trên tập Validation...")
    t_pred_0 = time.time()
    X_val = df_val[BASELINE_13_FEATURES].to_numpy(dtype=np.float64)
    ridge_scores = pipeline.predict(X_val)
    pred_elapsed = time.time() - t_pred_0
    log(f"  -> Dự đoán hoàn tất trong {pred_elapsed:.2f} giây.")

    # Gán điểm dự đoán
    df_val["ridge_score"] = ridge_scores

    # Chuẩn bị bảng kết quả dự đoán validation theo yêu cầu:
    # date, canonical_sid, ridge_score, target_return, target_rank, ret_20d
    val_pred_cols = [
        "date",
        "canonical_sid",
        "ridge_score",
        TARGET_RETURN_COL,
        TARGET_RANK_COL,
        BENCHMARK_COL,
    ]
    df_val_preds = df_val[val_pred_cols].copy()

    # Kiểm tra nhanh tính toàn vẹn của bảng dự đoán
    log("[Check toàn vẹn bảng dự đoán]")
    assert len(df_val_preds) == n_val_rows, f"Số dòng dự đoán {len(df_val_preds)} != Validation gốc {n_val_rows}"
    assert df_val_preds.duplicated(subset=KEY_COLS).sum() == 0, "Trùng lặp khóa (date, canonical_sid) trong dự đoán!"
    assert np.isfinite(df_val_preds["ridge_score"]).all(), "Tồn tại giá trị ridge_score không hữu hạn (NaN/Inf)!"
    assert np.isfinite(df_val_preds[TARGET_RETURN_COL]).all(), "Tồn tại target_return không hữu hạn!"
    assert np.isfinite(df_val_preds[BENCHMARK_COL]).all(), "Tồn tại ret_20d không hữu hạn!"
    log(f"  [OK] Bảng dự đoán hợp lệ 100%: {len(df_val_preds):,} dòng, khóa duy nhất, toàn bộ hữu hạn.")

    del df_val, X_val, ridge_scores

    # 4. Tính toán Spearman Rank IC theo ngày
    log("[5/6] Tính toán Spearman Rank IC theo ngày cho Ridge và Benchmark (ret_20d)...")
    t_ic_0 = time.time()
    df_daily_ic, ic_summary = compute_daily_spearman_ic(
        df_val_preds,
        score_col="ridge_score",
        benchmark_col=BENCHMARK_COL,
        target_col=TARGET_RETURN_COL,
    )
    ic_elapsed = time.time() - t_ic_0
    log(f"  -> Tính IC hoàn tất trong {ic_elapsed:.2f} giây.")

    # 5. Chi tiết phiên ví dụ
    example_details = extract_example_date_details(df_val_preds, example_date_str="2019-01-02")
    log(f"  -> Đối chiếu phiên ví dụ {example_details['example_date']}: N = {example_details['n_stocks']} mã.")
    log(f"      * Ridge Rank IC: {example_details['ridge_ic_spearman']:.6f} (Pearson on Ranks: {example_details['ridge_pearson_on_ranks']:.6f}, p-val: {example_details['ridge_p_value']:.4e})")
    log(f"      * ret_20d Rank IC: {example_details['ret20d_ic_spearman']:.6f} (Pearson on Ranks: {example_details['ret20d_pearson_on_ranks']:.6f}, p-val: {example_details['ret20d_p_value']:.4e})")

    # 6. Tổng hợp Run Config và Metadata
    total_elapsed = time.time() - t_start
    run_metadata = {
        "model_name": "ridge_baseline_v1",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": total_elapsed,
        "pipeline": {
            "steps": ["StandardScaler", "Ridge"],
            "scaler_params": {"with_mean": True, "with_std": True},
            "ridge_params": {"alpha": alpha, "fit_intercept": fit_intercept},
            "intercept": float(ridge_model.intercept_),
            "feature_coefficients": coef_dict,
        },
        "datasets": {
            "train_source": "data/processed/train_baseline_v1.parquet",
            "val_source": "data/processed/val_baseline_v1.parquet",
            "train_rows": 4307308,
            "val_rows": n_val_rows,
            "feature_columns": BASELINE_13_FEATURES,
            "target_col": TARGET_RANK_COL,
            "evaluation_col": TARGET_RETURN_COL,
            "benchmark_col": BENCHMARK_COL,
        },
        "evaluation_metrics": ic_summary,
        "example_verification_date": example_details,
    }

    return pipeline, df_val_preds, df_daily_ic, run_metadata


def main():
    parser = argparse.ArgumentParser(description="Huấn luyện và đánh giá Ridge Baseline v1 (Train 2000-2018 vs Val 2019-2023).")
    parser.add_argument("--alpha", type=float, default=1.0, help="Hệ số regularization L2 cho Ridge (mặc định: 1.0).")
    parser.add_argument("--save-artifacts", action="store_true", default=True, help="Lưu pipeline model, parquet dự đoán, và báo cáo IC.")
    args = parser.parse_args()

    # Đảm bảo các thư mục tồn tại
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    pipeline, df_val_preds, df_daily_ic, run_meta = train_and_evaluate_ridge(
        alpha=args.alpha,
        fit_intercept=True,
    )

    if args.save_artifacts:
        log("\n[6/6] Lưu trữ Artifacts mô hình, Bảng dự đoán và Báo cáo IC...")

        # 1. Lưu pipeline model
        joblib.dump(pipeline, MODEL_OUTPUT_FILE)
        model_size_kb = MODEL_OUTPUT_FILE.stat().st_size / 1024
        log(f"  -> Lưu Model Pipeline: {MODEL_OUTPUT_FILE} ({model_size_kb:.2f} KB)")

        # 2. Lưu config tái lập
        with open(RUN_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(run_meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Lưu Run Configuration: {RUN_CONFIG_FILE}")

        # 3. Lưu bảng dự đoán Validation Parquet
        df_val_preds.to_parquet(VAL_PRED_OUTPUT_FILE, compression="snappy", index=False)
        val_pred_mb = VAL_PRED_OUTPUT_FILE.stat().st_size / (1024 * 1024)
        log(f"  -> Lưu Validation Predictions: {VAL_PRED_OUTPUT_FILE} ({len(df_val_preds):,} dòng, {val_pred_mb:.2f} MB)")

        # 4. Lưu bảng daily IC
        df_daily_ic.to_csv(DAILY_IC_CSV_FILE, index=False, float_format="%.6f")
        df_daily_ic.to_parquet(DAILY_IC_PARQUET_FILE, compression="snappy", index=False)
        log(f"  -> Lưu Daily IC Table: {DAILY_IC_CSV_FILE} và {DAILY_IC_PARQUET_FILE}")

    # Báo cáo tổng kết ra console
    ridge_stats = run_meta["evaluation_metrics"]["ic_ridge"]
    bench_stats = run_meta["evaluation_metrics"]["ic_ret_20d"]

    log("\n" + "=" * 80)
    log("TỔNG KẾT KẾT QUẢ ĐÁNH GIÁ RIDGE BASELINE V1 SO VỚI BENCHMARK RET_20D")
    log("=" * 80)
    log(f"{'Chỉ số':<30} | {'Ridge Baseline (13 feats)':<25} | {'Benchmark (ret_20d)':<25}")
    log("-" * 86)
    log(f"{'Số ngày giao dịch tổng':<30} | {ridge_stats['total_trading_days']:<25} | {bench_stats['total_trading_days']:<25}")
    log(f"{'Số ngày tính được IC':<30} | {ridge_stats['evaluable_days']:<25} | {bench_stats['evaluable_days']:<25}")
    log(f"{'Số ngày IC không xác định':<30} | {ridge_stats['undefined_days']:<25} | {bench_stats['undefined_days']:<25}")
    log(f"{'Mean Daily Spearman IC':<30} | {ridge_stats['mean_ic']:<+25.6f} | {bench_stats['mean_ic']:<+25.6f}")
    log(f"{'Median Daily Spearman IC':<30} | {ridge_stats['median_ic']:<+25.6f} | {bench_stats['median_ic']:<+25.6f}")
    log(f"{'Std Daily Spearman IC':<30} | {ridge_stats['std_ic']:<25.6f} | {bench_stats['std_ic']:<25.6f}")
    log(f"{'Tỷ lệ ngày IC dương (> 0)':<30} | {ridge_stats['positive_ic_ratio']*100:<24.2f}% | {bench_stats['positive_ic_ratio']*100:<24.2f}%")
    log(f"{'Daily IC IR (Mean/Std)':<30} | {ridge_stats['ic_ir_daily']:<+25.4f} | {bench_stats['ic_ir_daily']:<+25.4f}")
    log(f"{'Annualized IC IR (IR * sqrt(252))':<30} | {ridge_stats['ic_ir_annualized']:<+25.4f} | {bench_stats['ic_ir_annualized']:<+25.4f}")
    log(f"{'t-statistic':<30} | {ridge_stats['t_statistic']:<+25.4f} | {bench_stats['t_statistic']:<+25.4f}")
    log("=" * 80)


if __name__ == "__main__":
    main()
