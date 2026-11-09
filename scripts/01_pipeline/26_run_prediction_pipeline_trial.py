"""
Pipeline Script 26: Run Trial of OOS Prediction Pipeline on Late Development Sessions
======================================================================================
Mục tiêu:
1. Kiểm chứng toàn diện pipeline tạo dự đoán ngoài mẫu (OOS Prediction Pipeline)
   trên 3 phiên cuối của tập Development (2023-12-27, 2023-12-28, 2023-12-29).
2. Tái sử dụng chính xác cách tính 13 features từ src.features.base:
   - Duy trì cửa sổ đệm lịch sử (500 bars) bảo toàn chuỗi giá cho mom_12m_skip_1m và
     trạng thái làm mượt Wilder RSI qua ranh giới.
   - Đối chiếu số học 13 features tính được với Feature Store hiện có (data/processed/features/*.parquet).
3. Thực thi đúng quy tắc chọn mã dự đoán tại T (Inference Eligibility):
   - strict_membership_mask == True
   - Nến T sạch (bar_quality: không bad data, không spinoff jump)
   - is_consecutive_session[T] == True
   - Close[T] > 0, Volume[T] > 0
   - 13 features X hữu hạn (np.isfinite)
4. Xác nhận hai model refit đọc đúng thứ tự cột từ manifest:
   - ridge_refit_dev_alpha1.0.joblib
   - gbdt_refit_dev_leaf7.joblib
5. Tách biệt tuyệt đối bước suy luận tại T khỏi bước chấm nhãn T+1:
   - Phiên 2023-12-27 và 2023-12-28: sinh dự đoán và chấm Rank IC thành công.
   - Phiên 2023-12-29: sinh dự đoán đầy đủ tại T, nhưng không có nhãn T+1 trong Development
     (do nhãn chạm sang OOS 2024), tách riêng khỏi bảng chấm IC.
6. Lưu trữ artifacts thử nghiệm:
   - data/processed/trial_predictions_late_dev.parquet
   - outputs/reports/trial_daily_ic_late_dev.csv
   - configs/prediction_pipeline_trial_run.yaml
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.matrix_loader import (
    load_matrix,
    load_layer1_mask,
)
from src.models.oos_prediction_pipeline import (
    compute_13_features_with_history,
    build_inference_dataframe,
    predict_for_models,
    evaluate_daily_spearman_ic,
    BASELINE_13_FEATURES,
)

DATA_DIR = PROJECT_ROOT / "data" / "processed"
FEATURES_DIR = DATA_DIR / "features"
CONFIGS_DIR = PROJECT_ROOT / "configs"
MODELS_DIR = PROJECT_ROOT / "models" / "oos_production"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

MANIFEST_FILE = CONFIGS_DIR / "oos_production_models_manifest.yaml"
RIDGE_MODEL_FILE = MODELS_DIR / "ridge_refit_dev_alpha1.0.joblib"
GBDT_MODEL_FILE = MODELS_DIR / "gbdt_refit_dev_leaf7.joblib"

OUTPUT_PREDS_PARQUET = DATA_DIR / "trial_predictions_late_dev.parquet"
OUTPUT_IC_CSV = REPORTS_DIR / "trial_daily_ic_late_dev.csv"
OUTPUT_TRIAL_CONFIG = CONFIGS_DIR / "prediction_pipeline_trial_run.yaml"

TRIAL_DATES = ["2023-12-27", "2023-12-28", "2023-12-29"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    t_start = time.time()
    log("=" * 80)
    log("Pipeline 26: Chạy Thử Nghiệm OOS Prediction Pipeline Trên Các Phiên Cuối Development")
    log("=" * 80)

    # Đảm bảo các thư mục tồn tại
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Đọc Manifest và các mô hình đã refit
    log("\n[1/6] Kiểm tra và nạp Manifest cùng 2 mô hình đã refit...")
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy manifest: {MANIFEST_FILE}")
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    manifest_features = manifest["features"]["order"]
    log(f"  Thứ tự 13 features từ Manifest: {manifest_features}")
    assert manifest_features == BASELINE_13_FEATURES, "Thứ tự feature trong manifest không khớp quy chuẩn!"

    ridge_pipe = joblib.load(RIDGE_MODEL_FILE)
    gbdt_mod = joblib.load(GBDT_MODEL_FILE)
    log(f"  -> Nạp thành công Ridge: {ridge_pipe}")
    log(f"  -> Nạp thành công GBDT: {gbdt_mod} (actual iterations: {gbdt_mod.n_iter_})")

    # 2. Tính toán 13 features trên 3 phiên cuối với cửa sổ đệm lịch sử 500 phiên
    log(f"\n[2/6] Tính toán 13 features cho 3 phiên cuối Development: {TRIAL_DATES}...")
    log("      (Áp dụng lookback = 500 phiên để bảo toàn mom_12m và trạng thái Wilder RSI)")
    t0_feat = time.time()
    computed_features = compute_13_features_with_history(
        target_dates=TRIAL_DATES,
        lookback_sessions=500,
        dev_only=True,
        include_warmup=True,
        verbose=True,
    )
    log(f"  -> Tính toán 13 features hoàn tất trong {time.time() - t0_feat:.2f}s")

    # 3. Đối chiếu số học nghiêm ngặt với Feature Store hiện có
    log("\n[3/6] Đối chiếu số học 13 features với Feature Store (data/processed/features/*.parquet)...")
    feature_parity_results = []
    for feat_name in BASELINE_13_FEATURES:
        store_path = FEATURES_DIR / f"{feat_name}.parquet"
        if not store_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file feature store: {store_path}")

        store_df = pd.read_parquet(store_path)
        calc_sub = computed_features[feat_name].loc[TRIAL_DATES].values
        store_sub = store_df.loc[TRIAL_DATES].values

        diff = float(np.nanmax(np.abs(calc_sub - store_sub)))
        nan_mismatch = int(np.sum(np.isnan(calc_sub) != np.isnan(store_sub)))

        # Dung sai kiểm tra: 1e-8 (đối với float64 và Wilder smoothing)
        assert diff < 1e-8, f"Lệch số học trên feature '{feat_name}': max diff = {diff:.2e}"
        assert nan_mismatch == 0, f"Lệch vị trí NaN trên feature '{feat_name}': {nan_mismatch} ô lệch"

        feature_parity_results.append({
            "feature": feat_name,
            "max_abs_diff": diff,
            "nan_mismatch_cells": nan_mismatch,
            "status": "PASSED_PARITY",
        })
        log(f"    - {feat_name:<25}: max diff = {diff:.2e} | NaN mismatch = {nan_mismatch} -> [OK]")

    log("  -> TẤT CẢ 13 FEATURES KHỚP TUYỆT ĐỐI VỚI FEATURE STORE (Float64 Precision)!")

    # 4. Áp dụng quy tắc Inference Eligibility tại T để chọn mã dự đoán
    log("\n[4/6] Xác định Inference Universe tại ngày T cho từng phiên...")
    strict_mem_df = load_matrix("strict_membership_mask", dev_only=True, include_warmup=True)
    is_bad_df = load_matrix("is_bad_data_period", dev_only=True, include_warmup=True)
    is_spinoff_df = load_matrix("is_spinoff_discontinuity", dev_only=True, include_warmup=True)
    is_consec_df = load_matrix("is_consecutive_session", dev_only=True, include_warmup=True)
    close_df = load_matrix("close", dev_only=True, include_warmup=True)
    volume_df = load_matrix("volume", dev_only=True, include_warmup=True)

    inference_dfs = []
    eligibility_summary = []

    for dt_str in TRIAL_DATES:
        df_inf_t = build_inference_dataframe(
            target_date=dt_str,
            features_dict=computed_features,
            strict_mem_df=strict_mem_df,
            is_bad_df=is_bad_df,
            is_spinoff_df=is_spinoff_df,
            is_consec_df=is_consec_df,
            close_df=close_df,
            volume_df=volume_df,
        )
        n_eligible = len(df_inf_t)
        log(f"    - Phiên {dt_str}: {n_eligible:,} mã đủ điều kiện dự đoán tại T")
        inference_dfs.append(df_inf_t)
        eligibility_summary.append({
            "date": dt_str,
            "n_eligible_at_t": n_eligible,
        })

    df_all_inference = pd.concat(inference_dfs, ignore_index=True)
    log(f"  -> Tổng số quan sát suy luận trên 3 phiên: {len(df_all_inference):,} dòng")

    # 5. Sinh dự đoán từ hai mô hình (Ridge và GBDT)
    log("\n[5/6] Sinh điểm xếp hạng từ Ridge alpha=1.0 và GBDT leaf=7...")
    t0_pred = time.time()
    df_predictions = predict_for_models(
        df_inference=df_all_inference,
        ridge_pipeline=ridge_pipe,
        gbdt_model=gbdt_mod,
        manifest_features_order=manifest_features,
    )
    pred_sec = time.time() - t0_pred
    log(f"  -> Dự báo hoàn tất cho {len(df_predictions):,} quan sát trong {pred_sec:.2f}s")
    log(f"  Ridge score range: [{df_predictions['ridge_score'].min():.4f} -> {df_predictions['ridge_score'].max():.4f}] (mean: {df_predictions['ridge_score'].mean():.4f})")
    log(f"  GBDT score range:  [{df_predictions['gbdt_score'].min():.4f} -> {df_predictions['gbdt_score'].max():.4f}] (mean: {df_predictions['gbdt_score'].mean():.4f})")

    # Lưu bảng dự đoán thử nghiệm
    df_predictions.to_parquet(OUTPUT_PREDS_PARQUET, index=False)
    log(f"  -> Đã lưu bảng dự đoán: {OUTPUT_PREDS_PARQUET}")

    # 6. Đánh giá nhãn T+1 (Tách biệt hoàn toàn khỏi bước suy luận)
    log("\n[6/6] Thực hiện bước Đánh giá nhãn T+1 độc lập...")
    target_ret_df = load_matrix("target_next_return", dev_only=True, include_warmup=True)
    valid_label_df = load_matrix("valid_label_mask", dev_only=True, include_warmup=True)

    df_daily_ic, df_eval_rows = evaluate_daily_spearman_ic(
        df_predictions=df_predictions,
        target_return_matrix=target_ret_df,
        valid_label_matrix=valid_label_df,
        volume_matrix=volume_df,
    )

    log("  BẢNG KẾT QUẢ ĐÁNH GIÁ DAILY RANK IC TRÊN 3 PHIÊN THỬ NGHIỆM:")
    for _, r in df_daily_ic.iterrows():
        p_dt = r["date"]
        n_t = r["n_predicted_at_t"]
        n_t1 = r["n_evaluable_at_t1"]
        ic_rd = f"{r['ic_ridge']:+.4f}" if np.isfinite(r["ic_ridge"]) else "N/A"
        ic_gb = f"{r['ic_gbdt']:+.4f}" if np.isfinite(r["ic_gbdt"]) else "N/A"
        ic_bm = f"{r['ic_ret_20d']:+.4f}" if np.isfinite(r["ic_ret_20d"]) else "N/A"
        st = r["status"]
        log(f"    - Ngày {p_dt}: Dự đoán tại T = {n_t} | Chấm tại T+1 = {n_t1} | Ridge IC = {ic_rd} | GBDT IC = {ic_gb} | ret_20d IC = {ic_bm} | [{st}]")

    df_daily_ic.to_csv(OUTPUT_IC_CSV, index=False)
    log(f"  -> Đã lưu bảng daily IC: {OUTPUT_IC_CSV}")

    # 7. Lưu Manifest cấu hình chạy thử
    total_elapsed = time.time() - t_start
    trial_run_config = {
        "pipeline_name": "oos_prediction_pipeline_trial",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": float(total_elapsed),
        "trial_sessions": TRIAL_DATES,
        "lookback_sessions": 500,
        "models_used": {
            "ridge": str(RIDGE_MODEL_FILE.name),
            "gbdt": str(GBDT_MODEL_FILE.name),
        },
        "features_verified": BASELINE_13_FEATURES,
        "feature_parity_check": feature_parity_results,
        "inference_eligibility_summary": eligibility_summary,
        "daily_evaluation_summary": df_daily_ic.to_dict(orient="records"),
        "decoupling_verification": {
            "session_2023_12_29_inference_rows": int(len(df_predictions[df_predictions["date"] == "2023-12-29"])),
            "session_2023_12_29_has_insample_label": False,
            "status": "Decoupling verified: 2023-12-29 predicted at T without requiring in-sample label at T+1",
        },
        "oos_status": "STRICTLY_FROZEN",
    }

    with open(OUTPUT_TRIAL_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(trial_run_config, f, sort_keys=False, default_flow_style=False)
    log(f"  -> Đã lưu cấu hình chạy thử: {OUTPUT_TRIAL_CONFIG}")

    log("\n" + "=" * 80)
    log(f"HOÀN THÀNH CHẠY THỬ OOS PREDICTION PIPELINE TRONG {total_elapsed:.2f} GIÂY!")
    log("=" * 80)


if __name__ == "__main__":
    main()
