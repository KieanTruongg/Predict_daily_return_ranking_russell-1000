"""
Unit and Integration Tests for GBDT max_leaf_nodes Grid Search (5 Folds Walk-Forward)
====================================================================================
Kiểm thử tính toàn vẹn của kết quả thực nghiệm grid search max_leaf_nodes in [7, 15, 31]:
1. Cấu hình YAML và 15 model files (3 leaf configs x 5 folds).
2. Bảng dự đoán hợp nhất 5 fold (1.202.259 dòng, 0 NaN, khóa khớp 100%).
3. Tính nhất quán số học của mốc Leaf 15 (+0.019158) và Ridge alpha=1.0 (+0.016497).
4. Bảng Daily IC (1.253 phiên) và bảng tổng hợp 5 năm.
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = ROOT / "configs" / "walk_forward_gbdt_leaf_grid_run.yaml"
PREDS_PATH = ROOT / "data" / "processed" / "val_predictions_gbdt_leaf_grid.parquet"
DAILY_IC_CSV = ROOT / "outputs" / "reports" / "daily_ic_gbdt_leaf_grid.csv"
DAILY_IC_PARQUET = ROOT / "data" / "processed" / "daily_ic_gbdt_leaf_grid.parquet"
SUMMARY_CSV = ROOT / "outputs" / "reports" / "summary_gbdt_leaf_grid.csv"
MODELS_DIR = ROOT / "models" / "walk_forward_gbdt_leaf_grid"
BASE_GBDT15_PREDS = ROOT / "data" / "processed" / "val_predictions_walk_forward_gbdt.parquet"


def test_gbdt_leaf_grid_config_and_models():
    """Kiểm tra cấu hình YAML và 15 file model trên đĩa."""
    assert CONFIG_PATH.exists(), f"Thiếu file cấu hình: {CONFIG_PATH}"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["experiment_name"] == "gbdt_max_leaf_nodes_grid_search"
    assert cfg["leaf_grid"] == [7, 15, 31]
    assert cfg["baseline_leaf"] == 15
    assert cfg["parity_check"]["parity_passed"] is True
    assert np.isclose(cfg["parity_check"]["actual_mean_ic_leaf15"], 0.01915783, atol=1e-5)
    assert np.isclose(cfg["parity_check"]["actual_mean_ic_ridge"], 0.01649668, atol=1e-5)

    assert MODELS_DIR.exists()
    for leaf in [7, 15, 31]:
        for fid in range(1, 6):
            model_file = MODELS_DIR / f"gbdt_leaf_{leaf}_fold_{fid}.joblib"
            assert model_file.exists(), f"Thiếu model file: {model_file}"
            m = joblib.load(model_file)
            assert m.get_params()["max_leaf_nodes"] == leaf
            assert m.get_params()["learning_rate"] == 0.05
            assert m.get_params()["min_samples_leaf"] == 100


def test_gbdt_leaf_grid_predictions_integrity():
    """Kiểm tra bảng dự đoán hợp nhất 5 fold và tính đồng nhất với mốc Leaf 15."""
    assert PREDS_PATH.exists(), f"Thiếu file predictions: {PREDS_PATH}"
    df = pd.read_parquet(PREDS_PATH)

    assert len(df) == 1_202_259, f"Số dòng dự đoán {len(df)} != 1.202.259"
    expected_cols = [
        "date", "canonical_sid", "fold_id", "val_year",
        "score_leaf_7", "score_leaf_15", "score_leaf_31",
        "ridge_score", "target_return", "target_rank", "ret_20d",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Thiếu cột {col} trong {PREDS_PATH}"

    # Không có null
    for col in ["score_leaf_7", "score_leaf_15", "score_leaf_31", "ridge_score", "target_return", "target_rank"]:
        assert df[col].notna().all(), f"Cột {col} chứa null!"

    # Đối chiếu số học mốc Leaf 15 gốc
    assert BASE_GBDT15_PREDS.exists()
    df_base15 = pd.read_parquet(BASE_GBDT15_PREDS)
    np.testing.assert_allclose(
        df["score_leaf_15"].to_numpy(),
        df_base15["gbdt_score"].to_numpy(),
        atol=1e-6,
        err_msg="Dự đoán score_leaf_15 bị lệch so với mốc val_predictions_walk_forward_gbdt.parquet!"
    )


def test_gbdt_leaf_grid_daily_ic_and_summary():
    """Kiểm tra bảng Daily IC (1.253 phiên) và bảng tổng hợp summary_gbdt_leaf_grid.csv."""
    assert DAILY_IC_CSV.exists()
    assert DAILY_IC_PARQUET.exists()
    assert SUMMARY_CSV.exists()

    df_ic = pd.read_csv(DAILY_IC_CSV)
    assert len(df_ic) == 1_253, f"Số phiên {len(df_ic)} != 1.253"
    assert df_ic["is_valid"].all()

    # Kiểm tra mốc Leaf 15 và Ridge alpha=1.0
    mean_ic_15 = df_ic["ic_leaf_15"].mean()
    mean_ic_rd = df_ic["ic_ridge_alpha1"].mean()
    assert np.isclose(mean_ic_15, 0.01915783, atol=1e-5), f"Lệch mốc Leaf 15: {mean_ic_15}"
    assert np.isclose(mean_ic_rd, 0.01649668, atol=1e-5), f"Lệch mốc Ridge: {mean_ic_rd}"

    # Kiểm tra summary table
    df_sum = pd.read_csv(SUMMARY_CSV)
    assert len(df_sum) == 6  # 5 năm + TỔNG 5 NĂM
    assert "TỔNG 5 NĂM" in df_sum["period"].values
    tot_row = df_sum[df_sum["period"] == "TỔNG 5 NĂM"].iloc[0]
    assert tot_row["evaluable_days"] == 1253
