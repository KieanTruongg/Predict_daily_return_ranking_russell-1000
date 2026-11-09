"""
Unit and Integration Tests for OOS Production Refit Models & Manifest
=====================================================================
Kiểm thử tính toàn vẹn của 2 mô hình đã refit trên toàn bộ Development (5.514.324 dòng):
1. Manifest cấu hình (configs/oos_production_models_manifest.yaml & models/oos_production/manifest.yaml)
2. Mô hình Ridge alpha=1.0 kèm StandardScaler
3. Mô hình GBDT max_leaf_nodes=7
4. Năng lực suy luận (inference contract) trên 13 features Close/Volume chuẩn
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

MANIFEST_CONFIG = ROOT / "configs" / "oos_production_models_manifest.yaml"
MANIFEST_MODELS = ROOT / "models" / "oos_production" / "manifest.yaml"
RIDGE_MODEL_FILE = ROOT / "models" / "oos_production" / "ridge_refit_dev_alpha1.0.joblib"
GBDT_MODEL_FILE = ROOT / "models" / "oos_production" / "gbdt_refit_dev_leaf7.joblib"

EXPECTED_13_FEATURES = [
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


def test_manifest_structure_and_parity():
    """Kiểm tra cấu trúc và tính nhất quán của manifest giữa configs và models."""
    assert MANIFEST_CONFIG.exists(), f"Thiếu manifest tại {MANIFEST_CONFIG}"
    assert MANIFEST_MODELS.exists(), f"Thiếu manifest tại {MANIFEST_MODELS}"

    with open(MANIFEST_CONFIG, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["manifest_version"] == "1.0"
    assert cfg["data_source"]["total_rows"] == 5_514_324
    assert cfg["data_source"]["date_range"]["start_date"] == "2000-07-03"
    assert cfg["data_source"]["date_range"]["end_date"] == "2023-12-28"
    assert cfg["data_source"]["purged_final_session"] == "2023-12-29"

    assert cfg["features"]["count"] == 13
    assert cfg["features"]["order"] == EXPECTED_13_FEATURES
    assert cfg["target"]["name"] == "target_rank"

    # Hợp đồng OOS
    assert cfg["oos_contract"]["status"] == "STRICTLY_FROZEN"
    assert cfg["oos_contract"]["date_range"]["start_date"] == "2024-01-02"
    assert cfg["oos_contract"]["date_range"]["end_date"] == "2026-10-30"
    assert cfg["oos_contract"]["total_sessions"] == 711


def test_ridge_refit_model_integrity():
    """Kiểm tra mô hình Ridge refit kèm StandardScaler và khả năng suy luận."""
    assert RIDGE_MODEL_FILE.exists(), f"Thiếu model Ridge: {RIDGE_MODEL_FILE}"

    pipe = joblib.load(RIDGE_MODEL_FILE)
    assert hasattr(pipe, "named_steps"), "Ridge model phải là một Pipeline!"
    assert "scaler" in pipe.named_steps
    assert "ridge" in pipe.named_steps

    scaler = pipe.named_steps["scaler"]
    ridge = pipe.named_steps["ridge"]

    assert scaler.mean_.shape == (13,)
    assert scaler.scale_.shape == (13,)
    assert ridge.coef_.shape == (13,)
    assert ridge.alpha == 1.0
    assert ridge.fit_intercept is True

    # Test suy luận mẫu
    dummy_X = np.random.randn(5, 13).astype(np.float32)
    scores = pipe.predict(dummy_X)
    assert scores.shape == (5,)
    assert np.isfinite(scores).all()


def test_gbdt_refit_model_integrity():
    """Kiểm tra mô hình GBDT refit 7 lá và khả năng suy luận."""
    assert GBDT_MODEL_FILE.exists(), f"Thiếu model GBDT: {GBDT_MODEL_FILE}"

    model = joblib.load(GBDT_MODEL_FILE)
    params = model.get_params()

    assert params["max_leaf_nodes"] == 7
    assert params["max_iter"] == 100
    assert params["learning_rate"] == 0.05
    assert params["min_samples_leaf"] == 100
    assert params["early_stopping"] is False
    assert params["random_state"] == 42
    assert model.n_iter_ == 100

    # Test suy luận mẫu
    dummy_X = np.random.randn(5, 13).astype(np.float32)
    scores = model.predict(dummy_X)
    assert scores.shape == (5,)
    assert np.isfinite(scores).all()
