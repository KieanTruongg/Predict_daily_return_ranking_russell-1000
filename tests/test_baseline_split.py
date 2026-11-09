"""
Unit and Integration Tests for Baseline Dataset v1 Train/Validation Split
========================================================================
Mục tiêu kiểm thử:
1. Cấu hình baseline_split_v1.yaml hợp lệ và đầy đủ metadata.
2. Hai file train_baseline_v1.parquet và val_baseline_v1.parquet tồn tại, đúng 17 cột.
3. Ranh giới ngày rời nhau hoàn toàn (disjoint dates), không trùng lặp phiên nào.
4. Cơ chế Causal Boundary Purge:
   - Phiên 2018-12-31 (có nhãn R_{T+1} rơi vào 2019-01-02) bị loại bỏ khỏi Train (920 dòng).
   - Phiên 2023-12-29 (có nhãn rơi vào 2024-01-02 OOS) có 0 dòng trong Val.
5. Số lượng dòng khớp chính xác:
   - Train nominal: 4,308,228 -> Train sau purge: 4,307,308 dòng (4,652 phiên).
   - Validation: 1,206,096 dòng (1,257 phiên).
   - Tổng giữ lại: 5,513,404 dòng.
6. Tính toàn vẹn dữ liệu:
   - Khóa (date, canonical_sid) là duy nhất.
   - Toàn bộ giá trị 17 cột là hữu hạn (np.isfinite == True).
   - Giá trị target_rank nằm trong đoạn [0.0, 1.0].
   - Số dòng 3 phiên mẫu: 2000-07-03 (862 dòng), 2015-06-15 (965 dòng), 2023-12-29 (0 dòng).
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

DATA_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "configs"

CONFIG_FILE = CONFIGS_DIR / "baseline_split_v1.yaml"
TRAIN_FILE = DATA_DIR / "train_baseline_v1.parquet"
VAL_FILE = DATA_DIR / "val_baseline_v1.parquet"

EXPECTED_17_COLUMNS = [
    "date",
    "canonical_sid",
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
    "target_return",
    "target_rank",
]


def test_baseline_split_config():
    """Kiểm tra tính hợp lệ của tệp cấu hình configs/baseline_split_v1.yaml."""
    assert CONFIG_FILE.exists(), f"Không tìm thấy cấu hình {CONFIG_FILE}"
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["split_method"] == "purged_time_split"
    assert cfg["train"]["period_label"] == "2000-2018"
    assert cfg["train"]["actual_start_date"] == "2000-07-03"
    assert cfg["train"]["actual_end_date"] == "2018-12-28"
    assert cfg["train"]["rows_before_purge"] == 4308228
    assert cfg["train"]["rows_after_purge"] == 4307308
    assert cfg["train"]["purged_rows"] == 920
    assert "2018-12-31" in cfg["train"]["purged_sessions"]

    assert cfg["validation"]["period_label"] == "2019-2023"
    assert cfg["validation"]["actual_start_date"] == "2019-01-02"
    assert cfg["validation"]["actual_end_date"] == "2023-12-28"
    assert cfg["validation"]["rows"] == 1206096

    assert cfg["integrity_summary"]["is_disjoint"] is True
    assert cfg["integrity_summary"]["common_dates_count"] == 0
    assert cfg["integrity_summary"]["total_raw_rows"] == 5514324
    assert cfg["integrity_summary"]["total_retained_rows"] == 5513404
    assert cfg["integrity_summary"]["total_purged_rows"] == 920


@pytest.mark.integration
def test_baseline_split_parquet_integrity():
    """Kiểm tra trực tiếp dữ liệu Parquet của 2 tập Train và Validation."""
    assert TRAIN_FILE.exists(), f"Không tìm thấy tệp {TRAIN_FILE}"
    assert VAL_FILE.exists(), f"Không tìm thấy tệp {VAL_FILE}"

    # Đọc metadata và các cột date, canonical_sid, target_rank
    df_train = pd.read_parquet(TRAIN_FILE)
    df_val = pd.read_parquet(VAL_FILE)

    # 1. Kiểm tra kích thước và cột
    assert list(df_train.columns) == EXPECTED_17_COLUMNS
    assert list(df_val.columns) == EXPECTED_17_COLUMNS
    assert len(df_train) == 4307308, f"Train row count sai: {len(df_train)}"
    assert len(df_val) == 1206096, f"Validation row count sai: {len(df_val)}"

    # 2. Kiểm tra tính rời nhau về ngày (zero overlap)
    train_dates = set(df_train["date"])
    val_dates = set(df_val["date"])
    common_dates = train_dates.intersection(val_dates)
    assert len(common_dates) == 0, f"Trùng ngày giữa Train và Val: {common_dates}"

    # 3. Kiểm tra ranh giới ngày chính xác
    assert df_train["date"].min() == pd.Timestamp("2000-07-03")
    assert df_train["date"].max() == pd.Timestamp("2018-12-28")
    assert df_val["date"].min() == pd.Timestamp("2019-01-02")
    assert df_val["date"].max() == pd.Timestamp("2023-12-28")

    # 4. Xác nhận phiên purge không có mặt
    assert pd.Timestamp("2018-12-31") not in train_dates
    assert pd.Timestamp("2018-12-31") not in val_dates
    assert pd.Timestamp("2023-12-29") not in train_dates
    assert pd.Timestamp("2023-12-29") not in val_dates

    # 5. Khóa (date, canonical_sid) là duy nhất
    assert df_train.duplicated(subset=["date", "canonical_sid"]).sum() == 0
    assert df_val.duplicated(subset=["date", "canonical_sid"]).sum() == 0

    # 6. Toàn bộ các giá trị số đều hữu hạn (np.isfinite)
    for col in EXPECTED_17_COLUMNS:
        if col not in ["date", "canonical_sid"]:
            assert np.isfinite(df_train[col]).all(), f"Train cột {col} có giá trị không hữu hạn"
            assert np.isfinite(df_val[col]).all(), f"Val cột {col} có giá trị không hữu hạn"

    # 7. Phân phối target_rank [0.0, 1.0]
    assert df_train["target_rank"].min() >= 0.0
    assert df_train["target_rank"].max() <= 1.0
    assert df_val["target_rank"].min() >= 0.0
    assert df_val["target_rank"].max() <= 1.0

    # 8. Đối chiếu 3 phiên mẫu
    assert (df_train["date"] == pd.Timestamp("2000-07-03")).sum() == 862
    assert (df_train["date"] == pd.Timestamp("2015-06-15")).sum() == 965
    assert (df_val["date"] == pd.Timestamp("2023-12-29")).sum() == 0
