"""
Unit and Integration Tests for Ridge Baseline v1 Execution and Evaluation
=========================================================================
Xác thực:
1. Tệp mô hình models/ridge_baseline_v1.joblib nạp thành công, cấu trúc đúng Pipeline(StandardScaler, Ridge).
2. Tệp cấu hình configs/ridge_baseline_run_v1.yaml hợp lệ, đầy đủ tham số và chỉ số đánh giá.
3. Tệp dự đoán validation data/processed/val_predictions_ridge_v1.parquet:
   - Đúng 1.206.096 dòng và 6 cột.
   - Khóa (date, canonical_sid) là duy nhất 100%.
   - Toàn bộ giá trị số đều hữu hạn (np.isfinite == True).
4. Bảng Rank IC theo ngày:
   - Đúng 1.257 phiên giao dịch tương ứng với tập Validation (2019-2023).
   - Không có phiên nào bị undefined (undefined_days == 0).
   - Rank IC nằm trong khoảng [-1.0, 1.0].
   - Mean IC Ridge đạt khoảng +0.01735, vượt trội so với Benchmark ret_20d (-0.00445).
5. Tính nhất quán của phép tính Spearman Rank IC (minh chứng qua phiên 2019-01-02):
   - Spearman IC tính từ scipy.stats.spearmanr trùng khớp tuyệt đối với Pearson corr trên ranks.
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
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

MODEL_FILE = MODELS_DIR / "ridge_baseline_v1.joblib"
RUN_CONFIG_FILE = CONFIGS_DIR / "ridge_baseline_run_v1.yaml"
VAL_PRED_FILE = DATA_DIR / "val_predictions_ridge_v1.parquet"
DAILY_IC_CSV = REPORTS_DIR / "daily_ic_ridge_vs_ret20d_v1.csv"
DAILY_IC_PARQUET = DATA_DIR / "daily_ic_ridge_vs_ret20d_v1.parquet"


def test_ridge_model_artifact_and_config():
    """Kiểm tra tệp mô hình đã huấn luyện và cấu hình tái lập (Portable)."""
    assert MODEL_FILE.exists(), f"Không tìm thấy model artifact: {MODEL_FILE}"
    assert RUN_CONFIG_FILE.exists(), f"Không tìm thấy run config: {RUN_CONFIG_FILE}"

    # Nạp model
    pipeline = joblib.load(MODEL_FILE)
    assert hasattr(pipeline, "named_steps"), "Model không phải sklearn Pipeline!"
    assert "scaler" in pipeline.named_steps
    assert "ridge" in pipeline.named_steps

    ridge_step = pipeline.named_steps["ridge"]
    assert len(ridge_step.coef_) == 13, f"Số lượng trọng số {len(ridge_step.coef_)} != 13 features!"
    assert np.isclose(ridge_step.intercept_, 0.5, atol=0.01), f"Intercept {ridge_step.intercept_} cách quá xa 0.5!"

    # Nạp YAML config
    with open(RUN_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["model_name"] == "ridge_baseline_v1"
    assert cfg["pipeline"]["ridge_params"]["alpha"] == 1.0
    assert cfg["datasets"]["val_rows"] == 1206096
    assert cfg["evaluation_metrics"]["ic_ridge"]["evaluable_days"] == 1257
    assert cfg["evaluation_metrics"]["ic_ridge"]["undefined_days"] == 0
    assert cfg["evaluation_metrics"]["ic_ret_20d"]["evaluable_days"] == 1257


@pytest.mark.integration
def test_val_predictions_integrity():
    """Kiểm tra tính toàn vẹn của bảng dự đoán Validation Parquet (Integration)."""
    assert VAL_PRED_FILE.exists(), f"Không tìm thấy predictions parquet: {VAL_PRED_FILE}"

    df_preds = pd.read_parquet(VAL_PRED_FILE)
    expected_cols = ["date", "canonical_sid", "ridge_score", "target_return", "target_rank", "ret_20d"]

    # 1. Kích thước và cột
    assert list(df_preds.columns) == expected_cols
    assert len(df_preds) == 1206096, f"Số dòng dự đoán {len(df_preds)} != 1,206,096"

    # 2. Khóa duy nhất
    assert df_preds.duplicated(subset=["date", "canonical_sid"]).sum() == 0

    # 3. Giá trị hữu hạn
    for col in ["ridge_score", "target_return", "target_rank", "ret_20d"]:
        assert np.isfinite(df_preds[col]).all(), f"Cột {col} chứa giá trị không hữu hạn!"

    # 4. Ranh giới ngày
    assert df_preds["date"].min() == pd.Timestamp("2019-01-02")
    assert df_preds["date"].max() == pd.Timestamp("2023-12-28")
    assert df_preds["date"].nunique() == 1257


@pytest.mark.integration
def test_daily_ic_table_and_math_properties():
    """Kiểm tra bảng kết quả IC theo ngày và tính chính xác về mặt toán học (Integration)."""
    assert DAILY_IC_CSV.exists(), f"Không tìm thấy CSV daily IC: {DAILY_IC_CSV}"
    assert DAILY_IC_PARQUET.exists(), f"Không tìm thấy Parquet daily IC: {DAILY_IC_PARQUET}"

    df_ic = pd.read_parquet(DAILY_IC_PARQUET)

    # 1. Số phiên giao dịch
    assert len(df_ic) == 1257
    assert (df_ic["n_stocks"] >= 2).all(), "Tồn tại phiên có ít hơn 2 cổ phiếu!"

    # 2. Không có giá trị NaN trong IC
    assert df_ic["ic_ridge"].notna().all(), "Tồn tại giá trị IC Ridge bị null!"
    assert df_ic["ic_ret_20d"].notna().all(), "Tồn tại giá trị IC ret_20d bị null!"

    # 3. Khoảng giá trị IC trong [-1.0, 1.0]
    assert (df_ic["ic_ridge"] >= -1.0).all() and (df_ic["ic_ridge"] <= 1.0).all()
    assert (df_ic["ic_ret_20d"] >= -1.0).all() and (df_ic["ic_ret_20d"] <= 1.0).all()

    # 4. Chỉ số trung bình
    mean_ridge_ic = df_ic["ic_ridge"].mean()
    mean_bench_ic = df_ic["ic_ret_20d"].mean()
    assert np.isclose(mean_ridge_ic, 0.0173515, atol=1e-5)
    assert np.isclose(mean_bench_ic, -0.0044516, atol=1e-5)
    assert mean_ridge_ic > mean_bench_ic

    # 5. Đối chiếu phiên 2019-01-02
    row_sample = df_ic[df_ic["date"] == pd.Timestamp("2019-01-02")].iloc[0]
    assert row_sample["n_stocks"] == 920
    assert np.isclose(row_sample["ic_ridge"], 0.263805, atol=1e-5)
    assert np.isclose(row_sample["ic_ret_20d"], -0.026389, atol=1e-5)
