"""
Pipeline Script 25: Refit Final Models on Full Development (2000-2023)
======================================================================
Mục tiêu:
1. Huấn luyện lại (Refit) hai mô hình chính thức đã chốt sau kiểm định Walk-Forward:
   - Ridge Baseline (alpha=1.0) kèm StandardScaler(with_mean=True, with_std=True).
   - GBDT Candidate (HistGradientBoostingRegressor với max_leaf_nodes=7, max_iter=100,
     learning_rate=0.05, min_samples_leaf=100, early_stopping=False, random_state=42).
2. Dữ liệu huấn luyện:
   - Toàn bộ tập Development sạch từ baseline_dataset_v1.parquet (5.514.324 dòng, 2000-07-03 -> 2023-12-28).
   - Đúng 13 features Close/Volume chuẩn hóa theo thứ tự quy chuẩn.
   - Nhãn huấn luyện: target_rank in [0, 1].
3. Lưu trữ artifacts sản xuất:
   - models/oos_production/ridge_refit_dev_alpha1.0.joblib
   - models/oos_production/gbdt_refit_dev_leaf7.joblib
   - configs/oos_production_models_manifest.yaml
   - models/oos_production/manifest.yaml
4. Trạng thái OOS: Đóng băng tuyệt đối (2024-01-02 -> 2026-10-30, 711 phiên).
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
from sklearn.ensemble import HistGradientBoostingRegressor
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
MODELS_DIR = PROJECT_ROOT / "models" / "oos_production"

DATASET_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
OUTPUT_RIDGE_FILE = MODELS_DIR / "ridge_refit_dev_alpha1.0.joblib"
OUTPUT_GBDT_FILE = MODELS_DIR / "gbdt_refit_dev_leaf7.joblib"
OUTPUT_MANIFEST_CONFIG = CONFIGS_DIR / "oos_production_models_manifest.yaml"
OUTPUT_MANIFEST_MODELS = MODELS_DIR / "manifest.yaml"

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
EXPECTED_ROWS = 5_514_324
EXPECTED_START_DATE = "2000-07-03"
EXPECTED_END_DATE = "2023-12-28"

GBDT_PARAMS = {
    "loss": "squared_error",
    "max_iter": 100,
    "learning_rate": 0.05,
    "max_leaf_nodes": 7,
    "min_samples_leaf": 100,
    "early_stopping": False,
    "random_state": 42,
}


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    t_start = time.time()
    log("=" * 80)
    log("Pipeline 25: Refit Final Models (Ridge alpha=1.0 & GBDT leaf=7) on Development")
    log("=" * 80)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Đọc dữ liệu huấn luyện
    log(f"\n[1/4] Nạp dữ liệu huấn luyện từ: {DATASET_FILE}...")
    if not DATASET_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset nguồn: {DATASET_FILE}")

    req_cols = ["date", "canonical_sid", TARGET_RANK_COL] + BASELINE_13_FEATURES
    t0_read = time.time()
    df_dev = pd.read_parquet(DATASET_FILE, columns=req_cols)
    read_sec = time.time() - t0_read
    log(f"  Đã nạp {len(df_dev):,} dòng trong {read_sec:.2f}s")

    # Kiểm tra kích thước và tính toàn vẹn
    assert len(df_dev) == EXPECTED_ROWS, f"Số dòng dữ liệu {len(df_dev)} != {EXPECTED_ROWS}"
    df_dev["date"] = pd.to_datetime(df_dev["date"])
    actual_min_date = df_dev["date"].min().strftime("%Y-%m-%d")
    actual_max_date = df_dev["date"].max().strftime("%Y-%m-%d")
    log(f"  Khoảng thời gian: [{actual_min_date} -> {actual_max_date}]")
    assert actual_min_date == EXPECTED_START_DATE, f"Ngày bắt đầu lệch: {actual_min_date} != {EXPECTED_START_DATE}"
    assert actual_max_date == EXPECTED_END_DATE, f"Ngày kết thúc lệch: {actual_max_date} != {EXPECTED_END_DATE}"

    # Chuẩn bị ma trận X và vector y
    log("\n[2/4] Chuẩn bị ma trận X (13 features) và vector y (target_rank)...")
    X_dev = df_dev[BASELINE_13_FEATURES].to_numpy(dtype=np.float32)
    y_dev = df_dev[TARGET_RANK_COL].to_numpy(dtype=np.float32)

    assert np.isfinite(X_dev).all(), "Ma trận X chứa NaN hoặc Inf!"
    assert np.isfinite(y_dev).all(), "Vector y chứa NaN hoặc Inf!"
    assert np.all((y_dev >= 0.0) & (y_dev <= 1.0)), "target_rank nằm ngoài khoảng [0, 1]!"

    del df_dev  # Giải phóng RAM

    # 2. Refit Ridge Pipeline
    log("\n[3/4] Huấn luyện Ridge Pipeline (StandardScaler -> Ridge alpha=1.0)...")
    ridge_pipeline = Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("ridge", Ridge(alpha=1.0, fit_intercept=True)),
    ])

    t0_ridge = time.time()
    ridge_pipeline.fit(X_dev, y_dev)
    ridge_fit_sec = time.time() - t0_ridge
    log(f"  -> Huấn luyện Ridge Pipeline xong trong {ridge_fit_sec:.2f}s")

    # Trích xuất hệ số Ridge và thống kê Scaler
    scaler_fitted: StandardScaler = ridge_pipeline.named_steps["scaler"]
    ridge_fitted: Ridge = ridge_pipeline.named_steps["ridge"]

    ridge_intercept = float(ridge_fitted.intercept_)
    ridge_coefs = {feat: float(coef) for feat, coef in zip(BASELINE_13_FEATURES, ridge_fitted.coef_)}
    scaler_means = {feat: float(m) for feat, m in zip(BASELINE_13_FEATURES, scaler_fitted.mean_)}
    scaler_scales = {feat: float(s) for feat, s in zip(BASELINE_13_FEATURES, scaler_fitted.scale_)}

    joblib.dump(ridge_pipeline, OUTPUT_RIDGE_FILE)
    log(f"  -> Đã lưu Ridge Pipeline: {OUTPUT_RIDGE_FILE} ({OUTPUT_RIDGE_FILE.stat().st_size / 1024:.1f} KB)")

    # 3. Refit GBDT Model
    log("\n[4/4] Huấn luyện GBDT Model (HistGradientBoostingRegressor max_leaf_nodes=7)...")
    gbdt_model = HistGradientBoostingRegressor(**GBDT_PARAMS)

    t0_gbdt = time.time()
    gbdt_model.fit(X_dev, y_dev)
    gbdt_fit_sec = time.time() - t0_gbdt
    log(f"  -> Huấn luyện GBDT xong trong {gbdt_fit_sec:.2f}s (Số vòng lặp thực tế: {gbdt_model.n_iter_})")

    joblib.dump(gbdt_model, OUTPUT_GBDT_FILE)
    log(f"  -> Đã lưu GBDT Model: {OUTPUT_GBDT_FILE} ({OUTPUT_GBDT_FILE.stat().st_size / 1024:.1f} KB)")

    # 4. Tạo Manifest ghi nhận đầy đủ siêu dữ liệu
    log("\n[5/5] Tạo Manifest mô hình sản xuất...")
    total_elapsed = time.time() - t_start

    manifest = {
        "manifest_version": "1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_elapsed_sec": float(total_elapsed),
        "data_source": {
            "file_path": "data/processed/baseline_dataset_v1.parquet",
            "total_rows": int(EXPECTED_ROWS),
            "date_range": {
                "start_date": EXPECTED_START_DATE,
                "end_date": EXPECTED_END_DATE,
            },
            "purged_final_session": "2023-12-29",
            "purge_reason": "Avoid T+1 label leakage into OOS (2024-01-02)",
        },
        "target": {
            "name": TARGET_RANK_COL,
            "domain": "[0.0, 1.0]",
            "type": "Cross-sectional uniform rank normalized on valid label universe at T",
        },
        "features": {
            "count": len(BASELINE_13_FEATURES),
            "order": BASELINE_13_FEATURES,
        },
        "models": {
            "ridge_alpha1_0": {
                "file_path": "models/oos_production/ridge_refit_dev_alpha1.0.joblib",
                "model_type": "Pipeline(StandardScaler, Ridge)",
                "hyperparameters": {
                    "alpha": 1.0,
                    "fit_intercept": True,
                },
                "fit_time_sec": float(ridge_fit_sec),
                "intercept": ridge_intercept,
                "coefficients": ridge_coefs,
                "scaler_means": scaler_means,
                "scaler_scales": scaler_scales,
            },
            "gbdt_leaf7": {
                "file_path": "models/oos_production/gbdt_refit_dev_leaf7.joblib",
                "model_type": "HistGradientBoostingRegressor",
                "hyperparameters": GBDT_PARAMS,
                "actual_iterations": int(gbdt_model.n_iter_),
                "fit_time_sec": float(gbdt_fit_sec),
            },
        },
        "oos_contract": {
            "status": "STRICTLY_FROZEN",
            "date_range": {
                "start_date": "2024-01-02",
                "end_date": "2026-10-30",
            },
            "total_sessions": 711,
            "policy": "One-shot blind evaluation for reporting; no hyperparameter tuning allowed",
        },
    }

    # Lưu manifest vào cả 2 vị trí (configs và models/oos_production)
    with open(OUTPUT_MANIFEST_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, default_flow_style=False)
    with open(OUTPUT_MANIFEST_MODELS, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, default_flow_style=False)

    log(f"  -> Đã lưu manifest tại: {OUTPUT_MANIFEST_CONFIG}")
    log(f"  -> Đã lưu manifest tại: {OUTPUT_MANIFEST_MODELS}")

    log("\n" + "=" * 80)
    log("TỔNG KẾT HỆ SỐ RIDGE VÀ THÔNG SỐ GBDT:")
    log(f"  Ridge Intercept: {ridge_intercept:+.6f}")
    log("  Top 5 hệ số Ridge có độ lớn cao nhất:")
    sorted_coefs = sorted(ridge_coefs.items(), key=lambda kv: abs(kv[1]), reverse=True)
    for feat, val in sorted_coefs[:5]:
        log(f"    - {feat:<25}: {val:+.6f}")
    log(f"  GBDT Actual Iterations: {gbdt_model.n_iter_}")
    log("=" * 80)
    log(f"\nHoàn thành Refit trong {total_elapsed:.2f} giây.")


if __name__ == "__main__":
    main()
