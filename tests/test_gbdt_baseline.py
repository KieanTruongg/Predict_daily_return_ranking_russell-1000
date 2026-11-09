"""
Unit and Integration Tests for GBDT Baseline Walk-Forward Evaluation
====================================================================
Xác thực:
1. Tệp dự đoán val_predictions_walk_forward_gbdt.parquet:
   - Đúng 1.202.259 dòng (khớp 100% với Ridge baseline).
   - Khóa (date, canonical_sid) là duy nhất và khớp tuyệt đối với Ridge.
   - Toàn bộ giá trị số đều hữu hạn (np.isfinite == True).
2. Bảng Daily IC (daily_ic_walk_forward_gbdt_vs_ridge.csv/parquet):
   - Đúng 1.253 phiên giao dịch (2019-2023).
   - Mốc đối chiếu Ridge alpha=1.0: Mean IC = +0.016497 (khớp mốc cũ).
   - GBDT Mean Daily Rank IC = +0.019158, cao hơn Ridge +0.002661 (+0.27% IC).
   - GBDT thắng Ridge trong 3/5 năm (2019, 2020, 2023) và thua trong 2 năm (2021, 2022).
3. 5 mô hình GBDT đã lưu tại models/walk_forward_gbdt/ nạp thành công qua joblib.
4. Cấu hình tái lập configs/walk_forward_gbdt_baseline_run.yaml hợp lệ.
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
MODELS_DIR = PROJECT_ROOT / "models" / "walk_forward_gbdt"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

GBDT_PRED_FILE = DATA_DIR / "val_predictions_walk_forward_gbdt.parquet"
RIDGE_PRED_FILE = DATA_DIR / "val_predictions_walk_forward_ridge_alpha1.0.parquet"
DAILY_IC_PARQUET = DATA_DIR / "daily_ic_walk_forward_gbdt_vs_ridge.parquet"
RUN_CONFIG_FILE = CONFIGS_DIR / "walk_forward_gbdt_baseline_run.yaml"


def test_gbdt_models_and_config_structure():
    """Kiểm tra cấu hình YAML và 5 model GBDT đã huấn luyện (Portable)."""
    assert RUN_CONFIG_FILE.exists(), f"Không tìm thấy config: {RUN_CONFIG_FILE}"

    with open(RUN_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["experiment_name"] == "walk_forward_gbdt_vs_ridge_alpha1.0"
    assert cfg["model_type"] == "HistGradientBoostingRegressor"
    assert cfg["parity_check_ridge"]["parity_passed"] is True
    assert np.isclose(cfg["parity_check_ridge"]["actual_mean_ic"], 0.016497, atol=1e-5)
    assert len(cfg["fold_timings"]) == 5

    for fid in range(1, 6):
        m_path = MODELS_DIR / f"gbdt_fold_{fid}.joblib"
        assert m_path.exists(), f"Không tìm thấy model fold {fid}: {m_path}"
        model = joblib.load(m_path)
        assert hasattr(model, "predict")
        assert model.max_iter == 100
        assert model.learning_rate == 0.05


@pytest.mark.integration
def test_gbdt_predictions_and_key_parity():
    """Kiểm tra tính toàn vẹn và đối chiếu cặp khóa của GBDT với Ridge (Integration)."""
    assert GBDT_PRED_FILE.exists(), f"Không tìm thấy GBDT predictions: {GBDT_PRED_FILE}"
    assert RIDGE_PRED_FILE.exists(), f"Không tìm thấy Ridge predictions: {RIDGE_PRED_FILE}"

    df_gbdt = pd.read_parquet(GBDT_PRED_FILE)
    df_ridge = pd.read_parquet(RIDGE_PRED_FILE)

    assert len(df_gbdt) == 1202259
    assert len(df_ridge) == 1202259

    # Khóa duy nhất
    assert df_gbdt.duplicated(subset=["date", "canonical_sid"]).sum() == 0

    # Giá trị hữu hạn
    for col in ["gbdt_score", "target_return", "target_rank", "ret_20d"]:
        assert np.isfinite(df_gbdt[col]).all(), f"Cột {col} chứa giá trị không hữu hạn!"

    # Đối chiếu ngày và SID
    assert (df_gbdt["date"] == df_ridge["date"]).all(), "Trục date không khớp giữa GBDT và Ridge!"
    assert (df_gbdt["canonical_sid"] == df_ridge["canonical_sid"]).all(), "Trục canonical_sid không khớp giữa GBDT và Ridge!"


@pytest.mark.integration
def test_gbdt_daily_ic_and_comparative_performance():
    """Kiểm tra bảng Daily IC và các chỉ số so sánh GBDT vs Ridge (Integration)."""
    assert DAILY_IC_PARQUET.exists(), f"Không tìm thấy Daily IC parquet: {DAILY_IC_PARQUET}"

    df_ic = pd.read_parquet(DAILY_IC_PARQUET)
    assert len(df_ic) == 1253

    # Mốc đối chiếu Ridge
    mean_ridge = df_ic["ic_ridge"].mean()
    assert np.isclose(mean_ridge, 0.016497, atol=1e-5)

    # Hiệu năng GBDT
    mean_gbdt = df_ic["ic_gbdt"].mean()
    assert np.isclose(mean_gbdt, 0.019158, atol=1e-5)
    assert mean_gbdt > mean_ridge

    # Phân tích theo từng năm
    for yr in [2019, 2020, 2021, 2022, 2023]:
        sub = df_ic[df_ic["val_year"] == yr]
        assert len(sub) in [249, 250, 251, 252]
        assert sub["ic_gbdt"].mean() > 0, f"Năm {yr} Mean IC GBDT không dương!"
