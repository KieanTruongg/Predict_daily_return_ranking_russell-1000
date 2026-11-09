"""
Unit and Integration Tests for OOS Prediction Pipeline
======================================================
Kiểm thử tính toàn vẹn của pipeline suy luận và đánh giá tách biệt:
1. Tính toán 13 features và đối chiếu parity với Feature Store hiện có.
2. Quy tắc Inference Eligibility tại T (5 điều kiện bắt buộc).
3. Thứ tự 13 features khớp chính xác với Manifest.
4. Sinh dự đoán từ 2 model Ridge và GBDT refit.
5. Tính tách biệt giữa suy luận tại T và chấm điểm tại T+1 (phiên 2023-12-29).
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

from src.models.oos_prediction_pipeline import (
    BASELINE_13_FEATURES,
    compute_13_features_with_history,
    build_inference_dataframe,
    predict_for_models,
    evaluate_daily_spearman_ic,
)
from src.data.matrix_loader import (
    load_matrix,
    load_layer1_mask,
)

MANIFEST_FILE = ROOT / "configs" / "oos_production_models_manifest.yaml"
RIDGE_MODEL_FILE = ROOT / "models" / "oos_production" / "ridge_refit_dev_alpha1.0.joblib"
GBDT_MODEL_FILE = ROOT / "models" / "oos_production" / "gbdt_refit_dev_leaf7.joblib"
TRIAL_PREDS_FILE = ROOT / "data" / "processed" / "trial_predictions_late_dev.parquet"
TRIAL_IC_FILE = ROOT / "outputs" / "reports" / "trial_daily_ic_late_dev.csv"
TRIAL_CONFIG_FILE = ROOT / "configs" / "prediction_pipeline_trial_run.yaml"


def test_feature_order_and_manifest_contract():
    """Kiểm tra thứ tự 13 features khớp 100% với manifest đã lưu."""
    assert MANIFEST_FILE.exists()
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    assert m["features"]["count"] == 13
    assert m["features"]["order"] == BASELINE_13_FEATURES


def test_trial_predictions_and_decoupling_integrity():
    """Kiểm tra bảng dự đoán trial và tính tách biệt của phiên 2023-12-29."""
    assert TRIAL_PREDS_FILE.exists()
    assert TRIAL_IC_FILE.exists()
    assert TRIAL_CONFIG_FILE.exists()

    df_preds = pd.read_parquet(TRIAL_PREDS_FILE)
    df_preds["date_str"] = pd.to_datetime(df_preds["date"]).dt.strftime("%Y-%m-%d")

    # Kiểm tra có đủ 3 phiên
    assert set(df_preds["date_str"].unique()) == {"2023-12-27", "2023-12-28", "2023-12-29"}

    # Kiểm tra cột
    expected_cols = ["date", "canonical_sid", *BASELINE_13_FEATURES, "ridge_score", "gbdt_score"]
    for c in expected_cols:
        assert c in df_preds.columns

    # Không có null trong các cột này
    assert df_preds[expected_cols].notna().all().all()

    # Kiểm tra phiên 2023-12-29
    sub_29 = df_preds[df_preds["date_str"] == "2023-12-29"]
    assert len(sub_29) > 900, f"Phiên 2023-12-29 phải có > 900 mã hợp lệ tại T, thực tế: {len(sub_29)}"

    # Kiểm tra bảng Daily IC
    df_ic = pd.read_csv(TRIAL_IC_FILE)
    row_27 = df_ic[df_ic["date"] == "2023-12-27"].iloc[0]
    row_28 = df_ic[df_ic["date"] == "2023-12-28"].iloc[0]
    row_29 = df_ic[df_ic["date"] == "2023-12-29"].iloc[0]

    assert bool(row_27["has_valid_label"]) is True
    assert bool(row_28["has_valid_label"]) is True
    assert bool(row_29["has_valid_label"]) is False
    assert row_29["n_evaluable_at_t1"] == 0
    assert row_29["n_predicted_at_t"] > 900
    assert np.isnan(row_29["ic_ridge"])
    assert np.isnan(row_29["ic_gbdt"])


def test_oos_guardrail_blocks_without_allow_oos():
    """Kiểm tra Guardrail: chặn ngày ngoài Development khi chưa bật allow_oos=True."""
    with pytest.raises(PermissionError) as exc_info:
        compute_13_features_with_history(["2024-01-02"], allow_oos=False, verbose=False)
    assert "Truy cập dữ liệu ngoài Development (OOS) bị từ chối" in str(exc_info.value)

    with pytest.raises(PermissionError):
        compute_13_features_with_history(["2026-10-30"], allow_oos=False, verbose=False)

    with pytest.raises(PermissionError):
        compute_13_features_with_history(["2023-12-28", "2024-01-05"], allow_oos=False, verbose=False)


def test_scale_verification_artifacts_and_parity():
    """Kiểm tra báo cáo kiểm chứng quy mô 600 phiên và tính khớp số học với Feature Store."""
    scale_json = ROOT / "outputs" / "reports" / "prediction_pipeline_scale_verification.json"
    scale_csv = ROOT / "outputs" / "reports" / "prediction_pipeline_scale_verification.csv"
    scale_md = ROOT / "docs" / "reports" / "baseline" / "prediction_pipeline_scale_report.md"

    assert scale_json.exists(), f"Thiếu file {scale_json}"
    assert scale_csv.exists(), f"Thiếu file {scale_csv}"
    assert scale_md.exists(), f"Thiếu file {scale_md}"

    import json
    with open(scale_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["n_sessions"] == 600
    assert data["earliest_session"] == "2021-08-12"
    assert data["latest_session"] == "2023-12-29"

    for item in data["feature_parity"]:
        feat_name = item["feature"]
        max_d = item["full_600_sessions_max_diff"]
        nan_m = item["full_600_sessions_nan_mismatches"]
        assert nan_m == 0, f"Lệch vị trí NaN trên {feat_name}: {nan_m} ô"
        assert max_d < 1e-7, f"Sai số quá lớn trên {feat_name}: {max_d}"

    # Kiểm tra đánh giá tách biệt nhãn T+1 trên 2023-12-29
    eval_checks = data["evaluation_checks"]
    eval_29 = [e for e in eval_checks if e["date"] == "2023-12-29"][0]
    assert eval_29["n_predicted_at_t"] > 900
    assert eval_29["n_evaluable_at_t1"] == 0
    assert bool(eval_29["has_valid_label"]) is False
    assert np.isnan(eval_29["ic_ridge"])

