"""
Unit and Integration Tests for Walk-Forward Evaluation of Ridge Baseline (alpha=1.0)
===================================================================================
Xác thực:
1. Tệp kết quả dự đoán val_predictions_walk_forward_ridge_alpha1.0.parquet:
   - Đúng 1.202.259 dòng (khớp chính xác tổng 5 fold sau purge ranh giới).
   - Khóa (date, canonical_sid) là duy nhất 100%.
   - Toàn bộ giá trị điểm dự đoán và nhãn đều hữu hạn (np.isfinite == True).
2. Bảng Daily IC (daily_ic_walk_forward_ridge_alpha1.0.csv/parquet):
   - Đúng 1.253 phiên giao dịch (2019: 251, 2020: 252, 2021: 251, 2022: 250, 2023: 249).
   - Không có ngày nào bị undefined (undefined_days == 0).
   - Mean IC của Ridge Baseline dương trong CẢ 5 NĂM (100% các năm đều dương).
   - Mean IC tổng thể của Ridge (~+0.0165) vượt trội so với Benchmark ret_20d (~-0.0044).
3. 5 tệp Model Pipeline tương ứng 5 fold tồn tại và nạp thành công qua joblib.
4. Cấu hình tái lập walk_forward_ridge_alpha1.0_run.yaml hợp lệ và đầy đủ thống kê.
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "configs"
MODELS_DIR = PROJECT_ROOT / "models" / "walk_forward"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

PRED_FILE = DATA_DIR / "val_predictions_walk_forward_ridge_alpha1.0.parquet"
DAILY_IC_CSV = REPORTS_DIR / "daily_ic_walk_forward_ridge_alpha1.0.csv"
DAILY_IC_PARQUET = DATA_DIR / "daily_ic_walk_forward_ridge_alpha1.0.parquet"
RUN_CONFIG_FILE = CONFIGS_DIR / "walk_forward_ridge_alpha1.0_run.yaml"

EXPECTED_YEAR_DAYS = {
    2019: 251,
    2020: 252,
    2021: 251,
    2022: 250,
    2023: 249,
}


def test_walk_forward_run_config_and_models():
    """Kiểm tra cấu hình YAML và 5 model pipeline đã huấn luyện (Portable)."""
    assert RUN_CONFIG_FILE.exists(), f"Không tìm thấy file cấu hình: {RUN_CONFIG_FILE}"

    with open(RUN_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["evaluation_name"] == "walk_forward_ridge_alpha1.0"
    assert cfg["alpha"] == 1.0
    assert cfg["number_of_folds"] == 5
    assert cfg["overall_summary"]["total_trading_sessions"] == 1253
    assert cfg["overall_summary"]["total_validation_rows"] == 1202259

    # Kiểm tra 5 model pipeline
    for fid in range(1, 6):
        model_path = MODELS_DIR / f"ridge_fold_{fid}_alpha1.0.joblib"
        assert model_path.exists(), f"Không tìm thấy model fold {fid}: {model_path}"
        pipeline = joblib.load(model_path)
        assert hasattr(pipeline, "named_steps")
        assert "scaler" in pipeline.named_steps
        assert "ridge" in pipeline.named_steps
        assert len(pipeline.named_steps["ridge"].coef_) == 13
        assert np.isclose(pipeline.named_steps["ridge"].intercept_, 0.5, atol=0.01)


@pytest.mark.integration
def test_walk_forward_predictions_integrity():
    """Kiểm tra tính toàn vẹn của bảng dự đoán Validation Parquet (Integration)."""
    assert PRED_FILE.exists(), f"Không tìm thấy predictions file: {PRED_FILE}"

    df_preds = pd.read_parquet(PRED_FILE)
    expected_cols = ["date", "canonical_sid", "fold_id", "val_year", "ridge_score", "target_return", "target_rank", "ret_20d"]

    assert list(df_preds.columns) == expected_cols
    assert len(df_preds) == 1202259, f"Số dòng dự đoán {len(df_preds)} != 1,202,259"
    assert df_preds.duplicated(subset=["date", "canonical_sid"]).sum() == 0

    for col in ["ridge_score", "target_return", "target_rank", "ret_20d"]:
        assert np.isfinite(df_preds[col]).all(), f"Cột {col} chứa giá trị không hữu hạn!"


@pytest.mark.integration
def test_walk_forward_daily_ic_and_per_year_performance():
    """Kiểm tra bảng Daily IC và hiệu suất từng năm của Ridge so với Benchmark (Integration)."""
    assert DAILY_IC_CSV.exists(), f"Không tìm thấy CSV daily IC: {DAILY_IC_CSV}"
    assert DAILY_IC_PARQUET.exists(), f"Không tìm thấy Parquet daily IC: {DAILY_IC_PARQUET}"

    df_ic = pd.read_parquet(DAILY_IC_PARQUET)

    # 1. Tổng số phiên
    assert len(df_ic) == 1253
    assert df_ic["ic_ridge"].notna().all()
    assert df_ic["ic_ret_20d"].notna().all()

    # 2. Số phiên từng năm
    for yr, exp_days in EXPECTED_YEAR_DAYS.items():
        sub = df_ic[df_ic["val_year"] == yr]
        assert len(sub) == exp_days, f"Năm {yr} có {len(sub)} phiên != {exp_days}"
        mean_ridge_yr = sub["ic_ridge"].mean()
        # Mean IC Ridge dương trong CẢ 5 NĂM
        assert mean_ridge_yr > 0, f"Năm {yr} Mean IC Ridge không dương: {mean_ridge_yr}"

    # 3. Tổng thể 5 năm
    overall_mean_ridge = df_ic["ic_ridge"].mean()
    overall_mean_bench = df_ic["ic_ret_20d"].mean()

    assert np.isclose(overall_mean_ridge, 0.016497, atol=1e-5)
    assert np.isclose(overall_mean_bench, -0.004447, atol=1e-5)
    assert overall_mean_ridge > overall_mean_bench
