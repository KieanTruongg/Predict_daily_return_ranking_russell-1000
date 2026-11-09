"""
Pipeline Script 18: Split Baseline Dataset v1 (Train 2000-2018 vs Validation 2019-2023)
======================================================================================
Mục tiêu:
1. Phân chia tập dữ liệu baseline v1 (data/processed/baseline_dataset_v1.parquet) theo chuỗi thời gian:
   - Tập Huấn luyện (Train): 2000-07-01 đến 2018-12-31.
   - Tập Kiểm định (Validation): 2019-01-01 đến 2023-12-29.
2. Thực thi cơ chế Purge bảo vệ ranh giới nhân quả (Causal Boundary Purge):
   - Sử dụng lịch giao dịch chuẩn của dự án để xác định phiên kết thúc nhãn (T+1).
   - Nhãn R_{T+1} tại phiên T = 2018-12-31 có ngày đóng cửa T+1 = 2019-01-02 (phiên đầu tiên của Validation).
   - Loại bỏ toàn bộ các dòng thuộc phiên 2018-12-31 khỏi tập Train (920 dòng) để triệt tiêu lookahead rò rỉ sang Validation.
3. Bảo toàn nguyên vẹn 13 features và target rank đã tính (không tính lại rank, không scale).
4. Kiểm định tính toàn vẹn:
   - Hai tập hoàn toàn không trùng ngày (disjoint trading dates).
   - Khóa (date, canonical_sid) duy nhất 100%.
   - Toàn bộ 17 cột đều hữu hạn (np.isfinite, zero NaN/Inf).
   - Đối chiếu số dòng 3 phiên mẫu (2000-07-03, 2015-06-15, 2023-12-29).
5. Xuất các file Parquet phân tách và cấu hình YAML chia tập:
   - data/processed/train_baseline_v1.parquet
   - data/processed/val_baseline_v1.parquet
   - configs/baseline_split_v1.yaml
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.matrix_loader import load_dates_index

DATA_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "configs"

INPUT_FILE = DATA_DIR / "baseline_dataset_v1.parquet"
TRAIN_OUTPUT_FILE = DATA_DIR / "train_baseline_v1.parquet"
VAL_OUTPUT_FILE = DATA_DIR / "val_baseline_v1.parquet"
CONFIG_OUTPUT_FILE = CONFIGS_DIR / "baseline_split_v1.yaml"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def split_baseline_dataset(
    dataset_path: Path = INPUT_FILE,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Thực hiện phân tách dataset baseline v1 theo thời gian kèm purge ranh giới.
    """
    t0 = time.time()
    log("=" * 80)
    log("BẮT ĐẦU PHÂN TÁCH DATASET BASELINE V1 (TRAIN 2000-2018 vs VALIDATION 2019-2023)")
    log("=" * 80)

    # 1. Nạp dataset baseline v1
    log(f"[1/5] Nạp dataset đầy đủ từ: {dataset_path}...")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file dataset: {dataset_path}")

    df = pd.read_parquet(dataset_path)
    n_total_rows = len(df)
    log(f"  -> Tổng số dòng nạp: {n_total_rows:,} dòng, {len(df.columns)} cột.")

    # 2. Nạp lịch giao dịch thị trường để xác định T+1
    log("[2/5] Nạp lịch giao dịch thị trường và thiết lập ánh xạ T -> T+1...")
    calendar_dates = list(load_dates_index())
    date_to_next = {calendar_dates[i]: calendar_dates[i + 1] for i in range(len(calendar_dates) - 1)}

    # Cấu hình ranh giới thời gian
    train_nominal_start = pd.Timestamp("2000-07-01")
    train_nominal_end = pd.Timestamp("2018-12-31")
    val_nominal_start = pd.Timestamp("2019-01-01")
    val_nominal_end = pd.Timestamp("2023-12-29")

    # 3. Phân tách danh nghĩa và phát hiện các dòng cần purge
    log("[3/5] Áp dụng mặt nạ thời gian và xác định các dòng nhãn chạm Validation...")
    train_nominal_mask = (df["date"] >= train_nominal_start) & (df["date"] <= train_nominal_end)
    val_mask = (df["date"] >= val_nominal_start) & (df["date"] <= val_nominal_end)

    n_train_nominal = int(train_nominal_mask.sum())
    n_val = int(val_mask.sum())
    log(f"  -> Số dòng Train danh nghĩa (2000-2018): {n_train_nominal:,} dòng")
    log(f"  -> Số dòng Validation danh nghĩa (2019-2023): {n_val:,} dòng")
    assert n_train_nominal + n_val == n_total_rows, "Tổng số dòng danh nghĩa không khớp với dataset ban đầu!"

    # Ánh xạ T+1 cho các dòng train
    train_dates = df.loc[train_nominal_mask, "date"]
    train_next_dates = train_dates.map(date_to_next)

    # Dòng train có T+1 >= val_nominal_start (tức chạm vào giai đoạn validation)
    touch_val_mask = train_next_dates >= val_nominal_start
    n_purged_rows = int(touch_val_mask.sum())
    purged_sessions = [d.strftime("%Y-%m-%d") for d in train_dates[touch_val_mask].unique()]

    log(f"  -> Phát hiện {n_purged_rows:,} dòng có nhãn chạm sang Validation tại phiên: {purged_sessions}")
    log(f"  -> Thực hiện purge {n_purged_rows:,} dòng khỏi tập huấn luyện.")

    # Tập train sạch sau purge
    clean_train_indices = train_dates[~touch_val_mask].index
    df_train = df.loc[clean_train_indices].sort_values(["date", "canonical_sid"]).reset_index(drop=True)
    df_val = df.loc[val_mask].sort_values(["date", "canonical_sid"]).reset_index(drop=True)

    n_train_clean = len(df_train)
    log(f"  -> Số dòng Train thực tế sau purge: {n_train_clean:,} dòng")
    log(f"  -> Số dòng Validation thực tế: {n_val:,} dòng")

    # 4. Kiểm định tính toàn vẹn (Integrity Checks)
    log("[4/5] Thực hiện kiểm tra tính toàn vẹn và đối soát...")
    # Check 1: Không trùng ngày
    train_dates_set = set(df_train["date"])
    val_dates_set = set(df_val["date"])
    common_dates = train_dates_set.intersection(val_dates_set)
    assert len(common_dates) == 0, f"Phát hiện {len(common_dates)} ngày trùng lặp giữa Train và Val: {common_dates}!"
    log(f"  [Check 1/5] Hai tập KHÔNG TRÙNG NGÀY (zero date overlap).")

    # Check 2: Khóa duy nhất
    assert df_train.duplicated(subset=["date", "canonical_sid"]).sum() == 0, "Trùng lặp khóa trong Train!"
    assert df_val.duplicated(subset=["date", "canonical_sid"]).sum() == 0, "Trùng lặp khóa trong Val!"
    log(f"  [Check 2/5] Khóa (date, canonical_sid) là DUY NHẤT trong cả Train và Val.")

    # Check 3: Toàn bộ giá trị hữu hạn
    for col in df_train.columns:
        if col not in ["date", "canonical_sid"]:
            assert np.isfinite(df_train[col]).all(), f"Cột {col} trong Train có giá trị không hữu hạn!"
            assert np.isfinite(df_val[col]).all(), f"Cột {col} trong Val có giá trị không hữu hạn!"
    log(f"  [Check 3/5] Toàn bộ 17 cột đều là giá trị hữu hạn (np.isfinite, zero NaN/Inf).")

    # Check 4: Ranh giới ngày
    train_min_date = df_train["date"].min().strftime("%Y-%m-%d")
    train_max_date = df_train["date"].max().strftime("%Y-%m-%d")
    val_min_date = df_val["date"].min().strftime("%Y-%m-%d")
    val_max_date = df_val["date"].max().strftime("%Y-%m-%d")

    assert train_max_date == "2018-12-28", f"Ngày kết thúc Train sau purge không phải 2018-12-28: {train_max_date}"
    assert val_min_date == "2019-01-02", f"Ngày bắt đầu Val không phải 2019-01-02: {val_min_date}"
    log(f"  [Check 4/5] Ranh giới ngày chuẩn xác: Train [{train_min_date} -> {train_max_date}], Val [{val_min_date} -> {val_max_date}].")

    # Check 5: Đối chiếu 3 phiên mẫu
    n_sample_2000_07_03 = (df_train["date"] == "2000-07-03").sum()
    n_sample_2015_06_15 = (df_train["date"] == "2015-06-15").sum()
    n_sample_2023_12_29 = (df_val["date"] == "2023-12-29").sum()

    assert n_sample_2000_07_03 == 862, f"Số dòng 2000-07-03 sai: {n_sample_2000_07_03}"
    assert n_sample_2015_06_15 == 965, f"Số dòng 2015-06-15 sai: {n_sample_2015_06_15}"
    assert n_sample_2023_12_29 == 0, f"Số dòng 2023-12-29 sai: {n_sample_2023_12_29}"
    log(f"  [Check 5/5] Đối chiếu 3 phiên mẫu TRÙNG KHỚP: 2000-07-03 (862 dòng), 2015-06-15 (965 dòng), 2023-12-29 (0 dòng).")

    # 5. Cấu hình metadata kết quả
    try:
        rel_dataset_path = str(dataset_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        rel_dataset_path = str(dataset_path).replace("\\", "/")

    split_metadata = {
        "dataset_source": rel_dataset_path,
        "split_method": "purged_time_split",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "train": {
            "period_label": "2000-2018",
            "nominal_start_date": str(train_nominal_start)[:10],
            "nominal_end_date": str(train_nominal_end)[:10],
            "actual_start_date": train_min_date,
            "actual_end_date": train_max_date,
            "total_trading_sessions": len(train_dates_set),
            "rows_before_purge": n_train_nominal,
            "rows_after_purge": n_train_clean,
            "purged_rows": n_purged_rows,
            "purged_sessions": purged_sessions,
            "purge_reason": "Label R_{T+1} touches Validation session 2019-01-02",
        },
        "validation": {
            "period_label": "2019-2023",
            "nominal_start_date": str(val_nominal_start)[:10],
            "nominal_end_date": str(val_nominal_end)[:10],
            "actual_start_date": val_min_date,
            "actual_end_date": val_max_date,
            "total_trading_sessions": len(val_dates_set),
            "rows": n_val,
            "final_session_purge": "2023-12-29 already purged in baseline_dataset_v1 (0 rows)",
        },
        "integrity_summary": {
            "total_raw_rows": n_total_rows,
            "total_retained_rows": n_train_clean + n_val,
            "total_purged_rows": n_purged_rows,
            "common_dates_count": len(common_dates),
            "is_disjoint": True,
            "num_columns": 17,
        },
        "elapsed_time_sec": time.time() - t0,
    }

    return df_train, df_val, split_metadata


def main():
    parser = argparse.ArgumentParser(description="Phân chia baseline dataset v1 theo thời gian (Train 2000-2018 vs Val 2019-2023).")
    parser.add_argument("--save-parquet", action="store_true", default=True, help="Lưu các file Parquet phân tách.")
    args = parser.parse_args()

    df_train, df_val, meta = split_baseline_dataset()

    if args.save_parquet:
        log("\n[5/5] Lưu các tệp Parquet và tệp cấu hình YAML...")
        # Lưu train
        t_save = time.time()
        df_train.to_parquet(TRAIN_OUTPUT_FILE, compression="snappy", index=False)
        train_mb = TRAIN_OUTPUT_FILE.stat().st_size / (1024 * 1024)
        log(f"  -> Lưu Train Parquet: {TRAIN_OUTPUT_FILE} ({len(df_train):,} dòng, {train_mb:.2f} MB)")

        # Lưu validation
        df_val.to_parquet(VAL_OUTPUT_FILE, compression="snappy", index=False)
        val_mb = VAL_OUTPUT_FILE.stat().st_size / (1024 * 1024)
        log(f"  -> Lưu Val Parquet: {VAL_OUTPUT_FILE} ({len(df_val):,} dòng, {val_mb:.2f} MB)")

        # Lưu config YAML
        with open(CONFIG_OUTPUT_FILE, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Lưu cấu hình chia tập: {CONFIG_OUTPUT_FILE}")

    # Báo cáo tổng hợp
    log("\n" + "=" * 80)
    log("TỔNG KẾT BÀN GIAO PHÂN CHIA THỜI GIAN BASELINE V1 (PURGED TRAIN / VAL SPLIT)")
    log("=" * 80)
    log(f"  - Tập Huấn Luyện (Train 2000-2018):")
    log(f"      * Ranh giới ngày: {meta['train']['actual_start_date']} đến {meta['train']['actual_end_date']} ({meta['train']['total_trading_sessions']} phiên)")
    log(f"      * Số dòng trước purge: {meta['train']['rows_before_purge']:,}")
    log(f"      * Số dòng bị purge: {meta['train']['purged_rows']:,} (phiên 2018-12-31 do T+1 chạm 2019-01-02)")
    log(f"      * Số dòng sau purge: {meta['train']['rows_after_purge']:,}")
    log(f"  - Tập Kiểm Định (Validation 2019-2023):")
    log(f"      * Ranh giới ngày: {meta['validation']['actual_start_date']} đến {meta['validation']['actual_end_date']} ({meta['validation']['total_trading_sessions']} phiên)")
    log(f"      * Số dòng: {meta['validation']['rows']:,}")
    log(f"  - Trùng lặp ngày: {meta['integrity_summary']['common_dates_count']} (Rời nhau hoàn toàn)")
    log(f"  - Tổng số dòng giữ lại: {meta['integrity_summary']['total_retained_rows']:,} / {meta['integrity_summary']['total_raw_rows']:,}")
    log("=" * 80)


if __name__ == "__main__":
    main()
