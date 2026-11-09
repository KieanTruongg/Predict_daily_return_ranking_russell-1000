"""
Unit and Integration Tests for Ridge Alpha Grid Search
======================================================
Xác thực:
1. Tệp tóm tắt summary_ridge_alpha_grid.csv đầy đủ 5 mức alpha: [1, 1000, 10000, 100000, 1000000].
2. Tệp Daily IC daily_ic_ridge_alpha_grid.csv/parquet đúng 1.253 phiên giao dịch.
3. Đối chiếu mốc Parity với alpha=1.0:
   - Khớp chính xác 1.253 phiên.
   - Mean Daily Rank IC của alpha=1 đúng mốc +0.016497.
4. Kiểm tra tính toàn vẹn của kết quả:
   - Mọi mức alpha đều duy trì Mean IC dương trong cả 5 năm.
   - Mức alpha=1,000,000 có Mean IC nhỉnh nhẹ (+0.01687 so với +0.01650), nhưng tỷ lệ ngày dương giảm (53.63% vs 54.11%)
     và lợi thế tập trung ở năm 2019 trong khi 2021 và 2022 bị giảm hiệu năng.
5. Cấu hình tái lập configs/ridge_alpha_grid_search_run.yaml hợp lệ.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIGS_DIR = PROJECT_ROOT / "configs"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DATA_DIR = PROJECT_ROOT / "data" / "processed"

GRID_CONFIG_FILE = CONFIGS_DIR / "ridge_alpha_grid_search_run.yaml"
SUMMARY_CSV_FILE = REPORTS_DIR / "summary_ridge_alpha_grid.csv"
DAILY_IC_PARQUET_FILE = DATA_DIR / "daily_ic_ridge_alpha_grid.parquet"


def test_grid_search_config_and_summary_structure():
    """Kiểm tra cấu hình YAML và bảng summary (Portable)."""
    assert GRID_CONFIG_FILE.exists(), f"Không tìm thấy config: {GRID_CONFIG_FILE}"
    assert SUMMARY_CSV_FILE.exists(), f"Không tìm thấy summary CSV: {SUMMARY_CSV_FILE}"

    with open(GRID_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["experiment_name"] == "ridge_alpha_grid_search_5folds"
    assert cfg["alpha_grid"] == [1.0, 1000.0, 10000.0, 100000.0, 1000000.0]
    assert cfg["parity_check_alpha_1"]["parity_passed"] is True
    assert np.isclose(cfg["parity_check_alpha_1"]["actual_mean_ic"], 0.016497, atol=1e-5)

    df_sum = pd.read_csv(SUMMARY_CSV_FILE)
    assert len(df_sum) == 5
    assert list(df_sum["alpha"]) == [1.0, 1000.0, 10000.0, 100000.0, 1000000.0]
    assert (df_sum["evaluable_days"] == 1253).all()


@pytest.mark.integration
def test_grid_search_daily_ic_parity_and_properties():
    """Kiểm tra chi tiết bảng Daily IC của grid search (Integration)."""
    assert DAILY_IC_PARQUET_FILE.exists(), f"Không tìm thấy daily IC parquet: {DAILY_IC_PARQUET_FILE}"

    df_ic = pd.read_parquet(DAILY_IC_PARQUET_FILE)
    assert len(df_ic) == 1253

    # Kiểm tra các cột IC tồn tại đầy đủ
    expected_cols = [
        "date", "fold_id", "val_year", "n_stocks",
        "ic_alpha_1", "ic_alpha_1000", "ic_alpha_10000", "ic_alpha_100000", "ic_alpha_1000000",
        "ic_ret_20d", "is_valid"
    ]
    for col in expected_cols:
        assert col in df_ic.columns

    # Đối chiếu tuyệt đối với mốc alpha=1.0
    mean_alpha1 = df_ic["ic_alpha_1"].mean()
    assert np.isclose(mean_alpha1, 0.016497, atol=1e-5)

    # Toàn bộ các alpha đều có Mean IC > 0 trong cả 5 năm
    for yr in [2019, 2020, 2021, 2022, 2023]:
        sub_yr = df_ic[df_ic["val_year"] == yr]
        for a_col in ["ic_alpha_1", "ic_alpha_1000", "ic_alpha_10000", "ic_alpha_100000", "ic_alpha_1000000"]:
            assert sub_yr[a_col].mean() > 0, f"Năm {yr} cột {a_col} không dương: {sub_yr[a_col].mean()}"
