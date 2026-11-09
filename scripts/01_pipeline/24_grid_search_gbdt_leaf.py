"""
Pipeline Script 24: Grid Search max_leaf_nodes for GBDT (5 Folds Walk-Forward)
=============================================================================
Mục tiêu:
1. Thử nghiệm siêu tham số độ phức tạp của cây quyết định:
   max_leaf_nodes in [7, 15, 31]
   cho HistGradientBoostingRegressor trên đúng 5 fold walk-forward đã chốt.
2. Giữ nguyên tính công bằng tuyệt đối:
   - Dữ liệu: baseline_dataset_v1.parquet (13 features Close/Volume thô).
   - Lịch walk-forward: configs/walk_forward_schedule_v1.yaml.
   - Nhãn học: target_rank in [0, 1].
   - Nhãn đánh giá: target_return (Close-to-Close return T -> T+1).
   - Ranh giới purge, tập mã và ngày giao dịch đồng nhất 100%.
   - Cố định toàn bộ các siêu tham số GBDT khác:
     loss="squared_error", max_iter=100, learning_rate=0.05,
     min_samples_leaf=100, early_stopping=False, random_state=42.
3. Đối chiếu và kiểm tra tính nhất quán:
   - Sử dụng max_leaf_nodes=15 làm mốc chuẩn (Mean Daily Rank IC ~ +0.019158 trên 1.253 phiên).
   - Giữ Ridge alpha=1.0 làm mốc tham chiếu phụ (Mean Daily Rank IC ~ +0.016497).
   - Tái sử dụng/đối chiếu dự đoán leaf=15 và Ridge alpha=1.0 đã lưu trên đúng cặp khóa (date, canonical_sid).
4. Đánh giá và lưu trữ:
   - configs/walk_forward_gbdt_leaf_grid_run.yaml
   - data/processed/val_predictions_gbdt_leaf_grid.parquet
   - outputs/reports/daily_ic_gbdt_leaf_grid.csv & data/processed/daily_ic_gbdt_leaf_grid.parquet
   - outputs/reports/summary_gbdt_leaf_grid.csv
   - models/walk_forward_gbdt_leaf_grid/gbdt_leaf_{leaf}_fold_{k}.joblib
   - docs/reports/baseline/gbdt_leaf_grid_report.md
"""

from __future__ import annotations

import argparse
import shutil
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
MODELS_GRID_DIR = PROJECT_ROOT / "models" / "walk_forward_gbdt_leaf_grid"
MODELS_GBDT15_DIR = PROJECT_ROOT / "models" / "walk_forward_gbdt"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DOCS_REPORTS_DIR = PROJECT_ROOT / "docs" / "reports" / "baseline"

DATASET_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
SCHEDULE_CONFIG_FILE = CONFIGS_DIR / "walk_forward_schedule_v1.yaml"
GBDT15_PREDS_FILE = DATA_DIR / "val_predictions_walk_forward_gbdt.parquet"
RIDGE_PREDS_FILE = DATA_DIR / "val_predictions_walk_forward_ridge_alpha1.0.parquet"

OUTPUT_RUN_CONFIG_FILE = CONFIGS_DIR / "walk_forward_gbdt_leaf_grid_run.yaml"
OUTPUT_PREDS_FILE = DATA_DIR / "val_predictions_gbdt_leaf_grid.parquet"
OUTPUT_DAILY_IC_CSV = REPORTS_DIR / "daily_ic_gbdt_leaf_grid.csv"
OUTPUT_DAILY_IC_PARQUET = DATA_DIR / "daily_ic_gbdt_leaf_grid.parquet"
OUTPUT_SUMMARY_CSV = REPORTS_DIR / "summary_gbdt_leaf_grid.csv"
OUTPUT_REPORT_MD = DOCS_REPORTS_DIR / "gbdt_leaf_grid_report.md"

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

LEAF_GRID = [7, 15, 31]
BASELINE_LEAF = 15

GBDT_FIXED_PARAMS = {
    "loss": "squared_error",
    "max_iter": 100,
    "learning_rate": 0.05,
    "min_samples_leaf": 100,
    "early_stopping": False,
    "random_state": 42,
}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_schedule_config() -> dict:
    if not SCHEDULE_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy cấu hình lịch walk-forward: {SCHEDULE_CONFIG_FILE}")
    with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def summarize_ic_series(ic_series: pd.Series) -> dict:
    valid_ic = ic_series.dropna().to_numpy()
    n_days = len(valid_ic)
    if n_days == 0:
        return {
            "evaluable_days": 0,
            "mean_ic": np.nan,
            "std_ic": np.nan,
            "positive_ic_ratio": np.nan,
            "ic_ir_annualized": np.nan,
            "t_stat": np.nan,
            "p_val": np.nan,
        }

    mean_ic = float(np.mean(valid_ic))
    std_ic = float(np.std(valid_ic, ddof=1)) if n_days > 1 else 0.0
    pos_ratio = float(np.mean(valid_ic > 0))
    ir_ann = float((mean_ic / std_ic) * np.sqrt(252)) if std_ic > 0 else np.nan

    if n_days > 1 and std_ic > 0:
        se = std_ic / np.sqrt(n_days)
        t_stat = float(mean_ic / se)
        p_val = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=n_days - 1)))
    else:
        t_stat = np.nan
        p_val = np.nan

    return {
        "evaluable_days": int(n_days),
        "mean_ic": mean_ic,
        "std_ic": std_ic,
        "positive_ic_ratio": pos_ratio,
        "ic_ir_annualized": ir_ann,
        "t_stat": t_stat,
        "p_val": p_val,
    }


def main() -> None:
    start_time = time.time()
    log("=" * 80)
    log("Pipeline 24: Grid Search max_leaf_nodes in [7, 15, 31] cho GBDT (5 Folds)")
    log("=" * 80)

    # Đảm bảo các thư mục tồn tại
    MODELS_GRID_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Đọc lịch walk-forward
    log("\n[1/5] Đọc cấu hình lịch 5-fold walk-forward...")
    sched = load_schedule_config()
    folds_info = sched["folds"]
    log(f"  Số lượng fold: {len(folds_info)} (2019 đến 2023)")

    # 2. Đọc bảng dự đoán mốc leaf=15 và Ridge alpha=1.0 để đối chiếu
    log("\n[2/5] Đọc dự đoán mốc leaf=15 và Ridge alpha=1.0 để đối chiếu tính tương thích...")
    if not GBDT15_PREDS_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file dự đoán GBDT leaf=15: {GBDT15_PREDS_FILE}")
    if not RIDGE_PREDS_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file dự đoán Ridge alpha=1.0: {RIDGE_PREDS_FILE}")

    df_gbdt15_preds = pd.read_parquet(GBDT15_PREDS_FILE)
    df_ridge_preds = pd.read_parquet(RIDGE_PREDS_FILE)

    log(f"  GBDT leaf=15 shape: {df_gbdt15_preds.shape}")
    log(f"  Ridge alpha=1 shape: {df_ridge_preds.shape}")
    assert len(df_gbdt15_preds) == len(df_ridge_preds), "Số dòng GBDT và Ridge không bằng nhau!"
    n_expected_val_rows = len(df_gbdt15_preds)

    # 3. Đọc dữ liệu baseline_dataset_v1.parquet
    log("\n[3/5] Đọc baseline_dataset_v1.parquet...")
    req_cols = list(dict.fromkeys(["date", "canonical_sid", TARGET_RANK_COL, TARGET_RETURN_COL] + BASELINE_13_FEATURES))
    t0_read = time.time()
    df_full = pd.read_parquet(DATASET_FILE, columns=req_cols)
    log(f"  Đã tải {len(df_full):,} dòng trong {time.time() - t0_read:.2f}s")
    df_full["date"] = pd.to_datetime(df_full["date"])

    # 4. Vòng lặp 5 folds cho leaf in [7, 31] và tái sử dụng/copy leaf=15
    log("\n[4/5] Huấn luyện và dự đoán 5 folds với max_leaf_nodes in [7, 15, 31]...")
    fold_timings: List[dict] = []
    all_val_preds_list: List[pd.DataFrame] = []

    for fold in folds_info:
        fid = int(fold["fold_id"])
        tr_info = fold["train"]
        vl_info = fold["validation"]
        val_yr = int(vl_info["period_label"])
        train_start = pd.Timestamp(tr_info["actual_start"])
        train_end = pd.Timestamp(tr_info["actual_end"])
        val_start = pd.Timestamp(vl_info["actual_start"])
        val_end = pd.Timestamp(vl_info["actual_end"])

        log(f"\n--- FOLD {fid}/5 (Năm Validation: {val_yr}) ---")
        log(f"  Train: [{train_start.strftime('%Y-%m-%d')} -> {train_end.strftime('%Y-%m-%d')}]")
        log(f"  Val:   [{val_start.strftime('%Y-%m-%d')} -> {val_end.strftime('%Y-%m-%d')}]")

        # Cắt tập Train
        mask_train = (df_full["date"] >= train_start) & (df_full["date"] <= train_end)
        df_train = df_full.loc[mask_train]
        n_train = len(df_train)
        assert n_train == tr_info["clean_rows"], f"Fold {fid} train rows lệch: {n_train} != {tr_info['clean_rows']}"
        log(f"  Kích thước Train: {n_train:,} dòng")

        # Cắt tập Validation
        mask_val = (df_full["date"] >= val_start) & (df_full["date"] <= val_end)
        df_val = df_full.loc[mask_val].copy()
        n_val = len(df_val)
        assert n_val == vl_info["clean_rows"], f"Fold {fid} val rows lệch: {n_val} != {vl_info['clean_rows']}"
        log(f"  Kích thước Val:   {n_val:,} dòng")

        X_train = df_train[BASELINE_13_FEATURES].to_numpy(dtype=np.float32)
        y_train = df_train[TARGET_RANK_COL].to_numpy(dtype=np.float32)
        X_val = df_val[BASELINE_13_FEATURES].to_numpy(dtype=np.float32)

        del df_train  # giải phóng RAM

        timing_record = {
            "fold_id": fid,
            "val_year": val_yr,
            "train_rows": n_train,
            "val_rows": n_val,
            "leaf_models": {},
        }

        # Lưu trữ điểm dự đoán cho từng leaf
        leaf_scores: Dict[int, np.ndarray] = {}

        # 4.1. Xử lý leaf=15 (tái sử dụng model đã fit hoặc load model)
        leaf15_model_src = MODELS_GBDT15_DIR / f"gbdt_fold_{fid}.joblib"
        leaf15_model_dst = MODELS_GRID_DIR / f"gbdt_leaf_15_fold_{fid}.joblib"
        t0_pred15 = time.time()
        if leaf15_model_src.exists():
            log(f"  [Leaf 15]: Tải model đã huấn luyện từ {leaf15_model_src.name}...")
            model_15 = joblib.load(leaf15_model_src)
            shutil.copyfile(leaf15_model_src, leaf15_model_dst)
            scores_15 = model_15.predict(X_val)
            pred_time_15 = time.time() - t0_pred15
            fit_time_15 = 0.0  # Tái sử dụng
            leaf_scores[15] = scores_15
        else:
            log(f"  [Leaf 15]: Huấn luyện mới...")
            t0_fit15 = time.time()
            model_15 = HistGradientBoostingRegressor(max_leaf_nodes=15, **GBDT_FIXED_PARAMS)
            model_15.fit(X_train, y_train)
            fit_time_15 = time.time() - t0_fit15
            joblib.dump(model_15, leaf15_model_dst)
            scores_15 = model_15.predict(X_val)
            pred_time_15 = time.time() - t0_pred15
            leaf_scores[15] = scores_15

        timing_record["leaf_models"][15] = {
            "fit_time_sec": float(fit_time_15),
            "predict_time_sec": float(pred_time_15),
        }
        log(f"  [Leaf 15] Dự báo xong {n_val:,} dòng trong {pred_time_15:.2f}s")

        # 4.2. Huấn luyện và dự đoán cho leaf in [7, 31]
        for leaf in [7, 31]:
            log(f"  [Leaf {leaf}]: Huấn luyện HistGradientBoostingRegressor (max_leaf_nodes={leaf})...")
            t0_fit = time.time()
            model = HistGradientBoostingRegressor(max_leaf_nodes=leaf, **GBDT_FIXED_PARAMS)
            model.fit(X_train, y_train)
            fit_time = time.time() - t0_fit

            model_dst = MODELS_GRID_DIR / f"gbdt_leaf_{leaf}_fold_{fid}.joblib"
            joblib.dump(model, model_dst)

            t0_pred = time.time()
            scores = model.predict(X_val)
            pred_time = time.time() - t0_pred
            leaf_scores[leaf] = scores

            timing_record["leaf_models"][leaf] = {
                "fit_time_sec": float(fit_time),
                "predict_time_sec": float(pred_time),
            }
            log(f"  [Leaf {leaf}] Fit: {fit_time:.2f}s | Predict: {pred_time:.2f}s | Saved: {model_dst.name}")

        fold_timings.append(timing_record)

        # Gán cột dự đoán vào df_val
        df_val["fold_id"] = fid
        df_val["val_year"] = val_yr
        df_val["score_leaf_7"] = leaf_scores[7]
        df_val["score_leaf_15"] = leaf_scores[15]
        df_val["score_leaf_31"] = leaf_scores[31]

        keep_cols = [
            "date", "canonical_sid", "fold_id", "val_year",
            "score_leaf_7", "score_leaf_15", "score_leaf_31",
            TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL,
        ]
        all_val_preds_list.append(df_val[keep_cols].copy())

        del df_val, X_train, y_train, X_val

    del df_full  # Giải phóng RAM

    # 5. Hợp nhất dự đoán và đối chiếu khóa với Ridge và GBDT leaf=15 mốc
    log("\n[5/5] Hợp nhất dự đoán, đối chiếu khóa và tính toán Spearman Rank IC...")
    df_all_preds = pd.concat(all_val_preds_list, ignore_index=True)
    assert len(df_all_preds) == n_expected_val_rows, f"Số dòng dự đoán {len(df_all_preds)} != {n_expected_val_rows}"

    # Merge với Ridge predictions để lấy ridge_score
    df_merged = pd.merge(
        df_all_preds,
        df_ridge_preds[["date", "canonical_sid", "ridge_score"]],
        on=["date", "canonical_sid"],
        how="inner",
    )
    assert len(df_merged) == n_expected_val_rows, "Lệch khóa sau khi merge với Ridge!"

    # Merge với GBDT15 gốc để kiểm tra tính nhất quán tuyệt đối của leaf=15
    df_merged = pd.merge(
        df_merged,
        df_gbdt15_preds[["date", "canonical_sid", "gbdt_score"]].rename(columns={"gbdt_score": "orig_gbdt15_score"}),
        on=["date", "canonical_sid"],
        how="inner",
    )
    assert len(df_merged) == n_expected_val_rows, "Lệch khóa sau khi merge với GBDT15 gốc!"

    # Kiểm tra sai khác số học giữa score_leaf_15 và orig_gbdt15_score
    max_diff_15 = np.max(np.abs(df_merged["score_leaf_15"].to_numpy() - df_merged["orig_gbdt15_score"].to_numpy()))
    log(f"  Sai khác số học tuyệt đối lớn nhất giữa leaf=15 tái tạo và leaf=15 mốc: {max_diff_15:.2e}")
    assert max_diff_15 < 1e-6, "Điểm dự báo leaf=15 không khớp với mốc!"

    # Lưu bảng dự đoán hợp nhất
    cols_to_save = [
        "date", "canonical_sid", "fold_id", "val_year",
        "score_leaf_7", "score_leaf_15", "score_leaf_31",
        "ridge_score", TARGET_RETURN_COL, TARGET_RANK_COL, BENCHMARK_COL,
    ]
    df_merged[cols_to_save].to_parquet(OUTPUT_PREDS_FILE, index=False)
    log(f"  Đã lưu bảng dự đoán: {OUTPUT_PREDS_FILE} ({len(df_merged):,} dòng)")

    # 6. Tính toán Rank IC theo từng ngày
    log("  Tính toán Spearman Rank IC theo ngày cho từng cấu hình lá...")
    all_daily_records: List[dict] = []

    for dt, group in df_merged.groupby("date", sort=True):
        y_ret = group[TARGET_RETURN_COL].to_numpy()
        sc_7 = group["score_leaf_7"].to_numpy()
        sc_15 = group["score_leaf_15"].to_numpy()
        sc_31 = group["score_leaf_31"].to_numpy()
        sc_ridge = group["ridge_score"].to_numpy()
        sc_bench = group[BENCHMARK_COL].to_numpy()
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
            rec["ic_leaf_7"] = np.nan
            rec["ic_leaf_15"] = np.nan
            rec["ic_leaf_31"] = np.nan
            rec["ic_ridge_alpha1"] = np.nan
            rec["ic_ret_20d"] = np.nan
            rec["diff_leaf7_vs_15"] = np.nan
            rec["diff_leaf31_vs_15"] = np.nan
            rec["diff_leaf15_vs_ridge"] = np.nan
            rec["leaf7_beats_15"] = False
            rec["leaf31_beats_15"] = False
            rec["leaf15_beats_ridge"] = False
            rec["is_valid"] = False
        else:
            ic_7 = float(stats.spearmanr(sc_7, y_ret)[0]) if np.ptp(sc_7) > 0 else np.nan
            ic_15 = float(stats.spearmanr(sc_15, y_ret)[0]) if np.ptp(sc_15) > 0 else np.nan
            ic_31 = float(stats.spearmanr(sc_31, y_ret)[0]) if np.ptp(sc_31) > 0 else np.nan
            ic_rd = float(stats.spearmanr(sc_ridge, y_ret)[0]) if np.ptp(sc_ridge) > 0 else np.nan
            ic_bm = float(stats.spearmanr(sc_bench, y_ret)[0]) if np.ptp(sc_bench) > 0 else np.nan

            diff_7_15 = ic_7 - ic_15 if (np.isfinite(ic_7) and np.isfinite(ic_15)) else np.nan
            diff_31_15 = ic_31 - ic_15 if (np.isfinite(ic_31) and np.isfinite(ic_15)) else np.nan
            diff_15_rd = ic_15 - ic_rd if (np.isfinite(ic_15) and np.isfinite(ic_rd)) else np.nan

            rec["ic_leaf_7"] = ic_7
            rec["ic_leaf_15"] = ic_15
            rec["ic_leaf_31"] = ic_31
            rec["ic_ridge_alpha1"] = ic_rd
            rec["ic_ret_20d"] = ic_bm
            rec["diff_leaf7_vs_15"] = diff_7_15
            rec["diff_leaf31_vs_15"] = diff_31_15
            rec["diff_leaf15_vs_ridge"] = diff_15_rd
            rec["leaf7_beats_15"] = (ic_7 > ic_15) if (np.isfinite(ic_7) and np.isfinite(ic_15)) else False
            rec["leaf31_beats_15"] = (ic_31 > ic_15) if (np.isfinite(ic_31) and np.isfinite(ic_15)) else False
            rec["leaf15_beats_ridge"] = (ic_15 > ic_rd) if (np.isfinite(ic_15) and np.isfinite(ic_rd)) else False
            rec["is_valid"] = True

        all_daily_records.append(rec)

    df_daily_ic = pd.DataFrame(all_daily_records)
    total_eval_sessions = len(df_daily_ic)

    # Đối chiếu mốc leaf=15 và Ridge alpha=1
    mean_ic_15_actual = float(df_daily_ic["ic_leaf_15"].mean())
    mean_ic_rd_actual = float(df_daily_ic["ic_ridge_alpha1"].mean())
    log(f"\n  [KIỂM CHỨNG TÍNH NHẤT QUÁN CỦA CÁC MỐC THAM CHIẾU]:")
    log(f"    - Tổng số phiên: {total_eval_sessions} (Kỳ vọng: 1.253)")
    log(f"    - Mean Rank IC Leaf 15: {mean_ic_15_actual:+.6f} (Kỳ vọng: +0.019158)")
    log(f"    - Mean Rank IC Ridge:   {mean_ic_rd_actual:+.6f} (Kỳ vọng: +0.016497)")
    assert np.isclose(mean_ic_15_actual, 0.01915783, atol=1e-5), "Lệch mốc Leaf 15!"
    assert np.isclose(mean_ic_rd_actual, 0.01649668, atol=1e-5), "Lệch mốc Ridge alpha=1.0!"
    log("    -> XÁC NHẬN: Cả 2 mốc Leaf 15 và Ridge alpha=1.0 ĐỒNG NHẤT TUYỆT ĐỐI!")

    # Lưu Daily IC
    df_daily_ic.to_csv(OUTPUT_DAILY_IC_CSV, index=False)
    df_daily_ic.to_parquet(OUTPUT_DAILY_IC_PARQUET, index=False)
    log(f"  Đã lưu daily IC: {OUTPUT_DAILY_IC_CSV}")

    # 7. Thống kê theo năm và tổng thể
    years = [2019, 2020, 2021, 2022, 2023]
    summary_rows: List[dict] = []

    for yr in years:
        sub = df_daily_ic[df_daily_ic["val_year"] == yr]
        s_7 = summarize_ic_series(sub["ic_leaf_7"])
        s_15 = summarize_ic_series(sub["ic_leaf_15"])
        s_31 = summarize_ic_series(sub["ic_leaf_31"])
        s_rd = summarize_ic_series(sub["ic_ridge_alpha1"])
        s_bm = summarize_ic_series(sub["ic_ret_20d"])

        diff_7 = float((sub["ic_leaf_7"] - sub["ic_leaf_15"]).mean())
        win_7 = float(sub["leaf7_beats_15"].mean())

        diff_31 = float((sub["ic_leaf_31"] - sub["ic_leaf_15"]).mean())
        win_31 = float(sub["leaf31_beats_15"].mean())

        diff_15_rd = float((sub["ic_leaf_15"] - sub["ic_ridge_alpha1"]).mean())

        summary_rows.append({
            "period": str(yr),
            "evaluable_days": s_15["evaluable_days"],
            "leaf_7_mean_ic": s_7["mean_ic"],
            "leaf_7_pos_ratio": s_7["positive_ic_ratio"],
            "leaf_7_annual_ir": s_7["ic_ir_annualized"],
            "diff_leaf7_vs_15": diff_7,
            "win_rate_leaf7_vs_15": win_7,
            "leaf_15_mean_ic": s_15["mean_ic"],
            "leaf_15_pos_ratio": s_15["positive_ic_ratio"],
            "leaf_15_annual_ir": s_15["ic_ir_annualized"],
            "leaf_31_mean_ic": s_31["mean_ic"],
            "leaf_31_pos_ratio": s_31["positive_ic_ratio"],
            "leaf_31_annual_ir": s_31["ic_ir_annualized"],
            "diff_leaf31_vs_15": diff_31,
            "win_rate_leaf31_vs_15": win_31,
            "ridge_mean_ic": s_rd["mean_ic"],
            "ridge_pos_ratio": s_rd["positive_ic_ratio"],
            "ridge_annual_ir": s_rd["ic_ir_annualized"],
            "diff_leaf15_vs_ridge": diff_15_rd,
            "ret_20d_mean_ic": s_bm["mean_ic"],
        })

    # Tổng kết 5 năm
    tot_7 = summarize_ic_series(df_daily_ic["ic_leaf_7"])
    tot_15 = summarize_ic_series(df_daily_ic["ic_leaf_15"])
    tot_31 = summarize_ic_series(df_daily_ic["ic_leaf_31"])
    tot_rd = summarize_ic_series(df_daily_ic["ic_ridge_alpha1"])
    tot_bm = summarize_ic_series(df_daily_ic["ic_ret_20d"])

    tot_diff_7 = float((df_daily_ic["ic_leaf_7"] - df_daily_ic["ic_leaf_15"]).mean())
    tot_win_7 = float(df_daily_ic["leaf7_beats_15"].mean())

    tot_diff_31 = float((df_daily_ic["ic_leaf_31"] - df_daily_ic["ic_leaf_15"]).mean())
    tot_win_31 = float(df_daily_ic["leaf31_beats_15"].mean())

    tot_diff_15_rd = float((df_daily_ic["ic_leaf_15"] - df_daily_ic["ic_ridge_alpha1"]).mean())

    summary_rows.append({
        "period": "TỔNG 5 NĂM",
        "evaluable_days": tot_15["evaluable_days"],
        "leaf_7_mean_ic": tot_7["mean_ic"],
        "leaf_7_pos_ratio": tot_7["positive_ic_ratio"],
        "leaf_7_annual_ir": tot_7["ic_ir_annualized"],
        "diff_leaf7_vs_15": tot_diff_7,
        "win_rate_leaf7_vs_15": tot_win_7,
        "leaf_15_mean_ic": tot_15["mean_ic"],
        "leaf_15_pos_ratio": tot_15["positive_ic_ratio"],
        "leaf_15_annual_ir": tot_15["ic_ir_annualized"],
        "leaf_31_mean_ic": tot_31["mean_ic"],
        "leaf_31_pos_ratio": tot_31["positive_ic_ratio"],
        "leaf_31_annual_ir": tot_31["ic_ir_annualized"],
        "diff_leaf31_vs_15": tot_diff_31,
        "win_rate_leaf31_vs_15": tot_win_31,
        "ridge_mean_ic": tot_rd["mean_ic"],
        "ridge_pos_ratio": tot_rd["positive_ic_ratio"],
        "ridge_annual_ir": tot_rd["ic_ir_annualized"],
        "diff_leaf15_vs_ridge": tot_diff_15_rd,
        "ret_20d_mean_ic": tot_bm["mean_ic"],
    })

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUTPUT_SUMMARY_CSV, index=False)
    log(f"  Đã lưu bảng tổng hợp: {OUTPUT_SUMMARY_CSV}")

    # In kết quả ra màn hình
    log("\n" + "=" * 120)
    log("KẾT QUẢ ĐÁNH GIÁ SO SÁNH MAX_LEAF_NODES = [7, 15, 31] TRÊN 5 FOLDS WALK-FORWARD")
    log("=" * 120)
    for _, r in df_summary.iterrows():
        p = r["period"]
        l7 = r["leaf_7_mean_ic"]
        l15 = r["leaf_15_mean_ic"]
        l31 = r["leaf_31_mean_ic"]
        l7_pos = r["leaf_7_pos_ratio"] * 100
        l15_pos = r["leaf_15_pos_ratio"] * 100
        l31_pos = r["leaf_31_pos_ratio"] * 100
        d7 = r["diff_leaf7_vs_15"]
        d31 = r["diff_leaf31_vs_15"]
        w7 = r["win_rate_leaf7_vs_15"] * 100
        w31 = r["win_rate_leaf31_vs_15"] * 100
        log(f"{p:<12} | Leaf 7: {l7:+.6f} ({l7_pos:.1f}%) | Leaf 15: {l15:+.6f} ({l15_pos:.1f}%) | Leaf 31: {l31:+.6f} ({l31_pos:.1f}%) | d(7-15): {d7:+.6f} (w:{w7:.1f}%) | d(31-15): {d31:+.6f} (w:{w31:.1f}%)")
    log("=" * 120)

    # 8. Lưu cấu hình thực nghiệm ra YAML
    total_elapsed = time.time() - start_time
    run_config = {
        "experiment_name": "gbdt_max_leaf_nodes_grid_search",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": float(total_elapsed),
        "model_type": "HistGradientBoostingRegressor",
        "leaf_grid": LEAF_GRID,
        "baseline_leaf": BASELINE_LEAF,
        "fixed_hyperparameters": GBDT_FIXED_PARAMS,
        "input_features": BASELINE_13_FEATURES,
        "oos_status": "STRICTLY_FROZEN (2024-2026)",
        "parity_check": {
            "expected_mean_ic_leaf15": 0.019158,
            "actual_mean_ic_leaf15": float(mean_ic_15_actual),
            "expected_mean_ic_ridge": 0.016497,
            "actual_mean_ic_ridge": float(mean_ic_rd_actual),
            "parity_passed": True,
        },
        "fold_timings": fold_timings,
        "summary_table": summary_rows,
    }

    with open(OUTPUT_RUN_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(run_config, f, sort_keys=False, default_flow_style=False)
    log(f"\n  Đã lưu cấu hình chạy: {OUTPUT_RUN_CONFIG_FILE}")

    log(f"\nHoàn thành Grid Search max_leaf_nodes trong {total_elapsed:.2f} giây.")


if __name__ == "__main__":
    main()
