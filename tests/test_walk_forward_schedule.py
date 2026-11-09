"""
Unit and Integration Tests for 5-Fold Walk-Forward Validation Schedule
======================================================================
Mục tiêu kiểm thử:
1. Cấu hình configs/walk_forward_schedule_v1.yaml hợp lệ, đầy đủ 5 fold Expanding Window.
2. Mỗi fold đảm bảo tính nhân quả tuyệt đối:
   - Hai tập Train và Val không trùng lặp phiên (zero session overlap).
   - Phiên kết thúc Train luôn đi trước phiên bắt đầu Val (actual_end < actual_start).
3. Đối chiếu mốc Fold 1 Train:
   - Đúng 4.307.308 dòng sạch sau khi purge phiên 2018-12-31 (920 dòng).
4. Kiểm tra quy tắc Causal Boundary Purge cho cả 5 fold:
   - Train purge: Phiên cuối chạm sang Validation (2018-12-31, 2019-12-31, 2020-12-31, 2021-12-31, 2022-12-30).
   - Val purge: Phiên cuối có nhãn vượt qua năm validation (2019-12-31, 2020-12-31, 2021-12-31, 2022-12-30; riêng 2023 là 0 dòng do 2023-12-29 đã bị purge ở nguồn).
5. Kiểm tra khả năng tái lập (@pytest.mark.integration):
   - Truy vấn trực tiếp từ baseline_dataset_v1.parquet qua query_filter cho ra đúng số dòng của từng fold mà không cần sinh 10 file Parquet trung gian.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = PROJECT_ROOT / "configs" / "walk_forward_schedule_v1.yaml"
DATASET_FILE = PROJECT_ROOT / "data" / "processed" / "baseline_dataset_v1.parquet"

EXPECTED_FOLDS_METRICS = {
    1: {
        "train_clean_rows": 4307308,
        "train_clean_sessions": 4652,
        "train_purged_rows": 920,
        "train_purged_sessions": ["2018-12-31"],
        "val_clean_rows": 235052,
        "val_clean_sessions": 251,
        "val_purged_rows": 945,
        "val_purged_sessions": ["2019-12-31"],
    },
    2: {
        "train_clean_rows": 4543280,
        "train_clean_sessions": 4904,
        "train_purged_rows": 945,
        "train_purged_sessions": ["2019-12-31"],
        "val_clean_rows": 240034,
        "val_clean_sessions": 252,
        "val_purged_rows": 958,
        "val_purged_sessions": ["2020-12-31"],
    },
    3: {
        "train_clean_rows": 4784259,
        "train_clean_sessions": 5157,
        "train_purged_rows": 958,
        "train_purged_sessions": ["2020-12-31"],
        "val_clean_rows": 239721,
        "val_clean_sessions": 251,
        "val_purged_rows": 955,
        "val_purged_sessions": ["2021-12-31"],
    },
    4: {
        "train_clean_rows": 5024938,
        "train_clean_sessions": 5409,
        "train_purged_rows": 955,
        "train_purged_sessions": ["2021-12-31"],
        "val_clean_rows": 243971,
        "val_clean_sessions": 250,
        "val_purged_rows": 979,
        "val_purged_sessions": ["2022-12-30"],
    },
    5: {
        "train_clean_rows": 5269864,
        "train_clean_sessions": 5660,
        "train_purged_rows": 979,
        "train_purged_sessions": ["2022-12-30"],
        "val_clean_rows": 243481,
        "val_clean_sessions": 249,
        "val_purged_rows": 0,
        "val_purged_sessions": [],
    },
}


def test_walk_forward_config_structure():
    """Kiểm tra tính hợp lệ của tệp cấu hình walk_forward_schedule_v1.yaml (Portable)."""
    assert CONFIG_FILE.exists(), f"Không tìm thấy cấu hình: {CONFIG_FILE}"

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["schedule_name"] == "walk_forward_expanding_5folds_v1"
    assert cfg["number_of_folds"] == 5
    assert len(cfg["folds"]) == 5
    assert cfg["oos_frozen_period"]["status"] == "STRICTLY_FROZEN"

    for fold in cfg["folds"]:
        fid = fold["fold_id"]
        exp = EXPECTED_FOLDS_METRICS[fid]
        tr = fold["train"]
        vl = fold["validation"]

        assert tr["clean_rows"] == exp["train_clean_rows"]
        assert tr["clean_sessions"] == exp["train_clean_sessions"]
        assert tr["purged_rows"] == exp["train_purged_rows"]
        assert tr["purged_sessions"] == exp["train_purged_sessions"]

        assert vl["clean_rows"] == exp["val_clean_rows"]
        assert vl["clean_sessions"] == exp["val_clean_sessions"]
        assert vl["purged_rows"] == exp["val_purged_rows"]
        assert vl["purged_sessions"] == exp["val_purged_sessions"]

        # Không trùng phiên và tính nhân quả thời gian
        assert pd.Timestamp(tr["actual_end"]) < pd.Timestamp(vl["actual_start"])
        assert fold["integrity"]["common_sessions"] == 0
        assert fold["integrity"]["is_disjoint"] is True


@pytest.mark.integration
def test_walk_forward_query_filter_reproducibility():
    """Kiểm tra khả năng tái lập dữ liệu từng fold từ baseline_dataset_v1.parquet qua query_filter."""
    assert DATASET_FILE.exists(), f"Không tìm thấy dataset nguồn: {DATASET_FILE}"

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Đọc cột date để kiểm tra tái lập nhanh
    df = pd.read_parquet(DATASET_FILE, columns=["date"])

    for fold in cfg["folds"]:
        fid = fold["fold_id"]
        tr = fold["train"]
        vl = fold["validation"]

        # Áp dụng query_filter trực tiếp
        tr_df = df.query(f"date >= '{tr['actual_start']}' and date <= '{tr['actual_end']}'")
        vl_df = df.query(f"date >= '{vl['actual_start']}' and date <= '{vl['actual_end']}'")

        assert len(tr_df) == tr["clean_rows"], f"Fold {fid} Train query_filter row count lệch: {len(tr_df)} != {tr['clean_rows']}"
        assert len(vl_df) == vl["clean_rows"], f"Fold {fid} Val query_filter row count lệch: {len(vl_df)} != {vl['clean_rows']}"
        assert tr_df["date"].nunique() == tr["clean_sessions"]
        assert vl_df["date"].nunique() == vl["clean_sessions"]
