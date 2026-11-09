"""
Pipeline Script 20: Build Walk-Forward Validation Schedule for Baseline v1
==========================================================================
Mục tiêu:
1. Thiết lập lịch Walk-Forward mở rộng (Expanding Window Walk-Forward) gồm 5 folds trên tập Development:
   - Fold 1: Train 2000-2018 -> Validation 2019
   - Fold 2: Train 2000-2019 -> Validation 2020
   - Fold 3: Train 2000-2020 -> Validation 2021
   - Fold 4: Train 2000-2021 -> Validation 2022
   - Fold 5: Train 2000-2022 -> Validation 2023
2. Thực thi nghiêm ngặt các quy tắc ranh giới nhân quả (Causal Boundary Purge):
   - Phân chia theo phiên giao dịch (toàn bộ cổ phiếu cùng ngày quyết định T nằm chung tập).
   - Ánh xạ phiên kết thúc nhãn T+1 từ lịch giao dịch chuẩn của dự án.
   - Tập Train: Loại bỏ các phiên có nhãn chạm sang Validation (T+1 >= val_start).
   - Tập Validation: Loại bỏ các phiên có nhãn kết thúc sau năm validation đó (T+1 > val_end).
   - Phiên cuối Development 2023-12-29 đã được loại bỏ ở dataset nguồn (0 dòng).
   - Giữ nguyên target_rank đã tính toán, không thực hiện re-ranking sau khi chia.
3. Xuất tệp cấu hình configs/walk_forward_schedule_v1.yaml và bảng đối soát:
   - Cho phép tái tạo chính xác từng tập train/val từ data/processed/baseline_dataset_v1.parquet
     thông qua các bộ lọc ngày mà không cần lưu thêm 10 bản Parquet vật lý.
   - Đối chiếu mốc Fold 1 Train sạch khớp đúng 4.307.308 dòng sau purge.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

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

INPUT_DATASET = DATA_DIR / "baseline_dataset_v1.parquet"
OUTPUT_SCHEDULE_YAML = CONFIGS_DIR / "walk_forward_schedule_v1.yaml"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def build_walk_forward_schedule(
    dataset_path: Path = INPUT_DATASET,
) -> Tuple[List[dict], dict]:
    """
    Xây dựng cấu hình 5 fold Walk-Forward và tính toán chính xác số phiên, số dòng trước/sau purge.
    """
    t0 = time.time()
    log("=" * 80)
    log("BẮT ĐẦU XÂY DỰNG LỊCH WALK-FORWARD CHO RIDGE BASELINE V1 (5 FOLDS EXPANDING)")
    log("=" * 80)

    # 1. Nạp lịch giao dịch và lập ánh xạ T -> T+1
    log("[1/4] Nạp lịch giao dịch thị trường chuẩn...")
    calendar_dates = list(load_dates_index())
    date_to_next = {calendar_dates[i]: calendar_dates[i + 1] for i in range(len(calendar_dates) - 1)}

    # 2. Nạp trục ngày và thống kê số lượng dòng theo phiên
    log(f"[2/4] Nạp dữ liệu ngày từ dataset nguồn: {dataset_path}...")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset: {dataset_path}")

    df_dates = pd.read_parquet(dataset_path, columns=["date"])
    total_raw_rows = len(df_dates)
    log(f"  -> Tổng số dòng dataset nguồn: {total_raw_rows:,} dòng, {df_dates['date'].nunique()} phiên.")

    # Đếm số dòng theo từng ngày giao dịch
    session_row_counts = df_dates["date"].value_counts().sort_index()
    unique_sessions = session_row_counts.index

    # Định nghĩa 5 folds theo yêu cầu
    folds_spec = [
        {"fold_id": 1, "train_end_year": 2018, "val_year": 2019},
        {"fold_id": 2, "train_end_year": 2019, "val_year": 2020},
        {"fold_id": 3, "train_end_year": 2020, "val_year": 2021},
        {"fold_id": 4, "train_end_year": 2021, "val_year": 2022},
        {"fold_id": 5, "train_end_year": 2022, "val_year": 2023},
    ]

    log("[3/4] Tính toán ranh giới, số phiên, số dòng và kiểm tra purge cho 5 folds...")
    folds_summary: List[dict] = []

    for spec in folds_spec:
        f_id = spec["fold_id"]
        train_end_year = spec["train_end_year"]
        val_year = spec["val_year"]

        train_nominal_start_str = "2000-07-01"
        train_nominal_end_str = f"{train_end_year}-12-31"
        val_nominal_start_str = f"{val_year}-01-01"
        val_nominal_end_str = f"{val_year}-12-31"

        train_nom_start = pd.Timestamp(train_nominal_start_str)
        train_nom_end = pd.Timestamp(train_nominal_end_str)
        val_nom_start = pd.Timestamp(val_nominal_start_str)
        val_nom_end = pd.Timestamp(val_nominal_end_str)

        # ----------------- TRAIN SET -----------------
        # Các phiên danh nghĩa của Train
        train_nom_sessions = unique_sessions[(unique_sessions >= train_nom_start) & (unique_sessions <= train_nom_end)]
        train_nom_rows = int(session_row_counts.loc[train_nom_sessions].sum())

        # Purge train: phiên có T+1 >= val_nom_start (chạm sang validation)
        train_purged_sessions = [d for d in train_nom_sessions if date_to_next.get(d) is not None and date_to_next[d] >= val_nom_start]
        train_purged_rows = int(session_row_counts.loc[train_purged_sessions].sum()) if train_purged_sessions else 0

        train_clean_sessions = [d for d in train_nom_sessions if d not in set(train_purged_sessions)]
        train_clean_rows = int(session_row_counts.loc[train_clean_sessions].sum())

        train_actual_start = train_clean_sessions[0].strftime("%Y-%m-%d")
        train_actual_end = train_clean_sessions[-1].strftime("%Y-%m-%d")

        # ----------------- VALIDATION SET -----------------
        # Các phiên danh nghĩa của Validation
        val_nom_sessions = unique_sessions[(unique_sessions >= val_nom_start) & (unique_sessions <= val_nom_end)]
        val_nom_rows = int(session_row_counts.loc[val_nom_sessions].sum())

        # Purge val: phiên có T+1 > val_nom_end (nhãn kết thúc sau năm validation đó)
        val_purged_sessions = [d for d in val_nom_sessions if date_to_next.get(d) is not None and date_to_next[d] > val_nom_end]
        val_purged_rows = int(session_row_counts.loc[val_purged_sessions].sum()) if val_purged_sessions else 0

        val_clean_sessions = [d for d in val_nom_sessions if d not in set(val_purged_sessions)]
        val_clean_rows = int(session_row_counts.loc[val_clean_sessions].sum())

        val_actual_start = val_clean_sessions[0].strftime("%Y-%m-%d")
        val_actual_end = val_clean_sessions[-1].strftime("%Y-%m-%d")

        # Kiểm tra không trùng lặp ngày giữa Train và Val của fold
        common_sessions = set(train_clean_sessions).intersection(set(val_clean_sessions))
        assert len(common_sessions) == 0, f"Fold {f_id} bị trùng lặp phiên giữa Train và Val: {common_sessions}"

        # Kiểm tra tính liên tục ranh giới: phiên kết thúc train < phiên bắt đầu val
        assert pd.Timestamp(train_actual_end) < pd.Timestamp(val_actual_start), f"Fold {f_id} ranh giới bị đảo!"

        # Đối chiếu mốc Fold 1 Train: khớp đúng 4.307.308 dòng
        if f_id == 1:
            assert train_clean_rows == 4307308, f"Fold 1 train clean rows {train_clean_rows} != 4,307,308!"
            assert train_actual_end == "2018-12-28", f"Fold 1 train actual end {train_actual_end} != 2018-12-28!"

        fold_info = {
            "fold_id": f_id,
            "fold_label": f"Fold {f_id} (Train 2000-{train_end_year} -> Val {val_year})",
            "train": {
                "period_label": f"2000-{train_end_year}",
                "nominal_start": train_nominal_start_str,
                "nominal_end": train_nominal_end_str,
                "actual_start": train_actual_start,
                "actual_end": train_actual_end,
                "nominal_sessions": len(train_nom_sessions),
                "clean_sessions": len(train_clean_sessions),
                "nominal_rows": train_nom_rows,
                "purged_rows": train_purged_rows,
                "clean_rows": train_clean_rows,
                "purged_sessions": [d.strftime("%Y-%m-%d") for d in train_purged_sessions],
                "purge_reason": f"Label T+1 >= {val_nominal_start_str} (touches Validation)",
                "query_filter": f"(date >= '{train_actual_start}') & (date <= '{train_actual_end}')",
            },
            "validation": {
                "period_label": str(val_year),
                "nominal_start": val_nominal_start_str,
                "nominal_end": val_nominal_end_str,
                "actual_start": val_actual_start,
                "actual_end": val_actual_end,
                "nominal_sessions": len(val_nom_sessions),
                "clean_sessions": len(val_clean_sessions),
                "nominal_rows": val_nom_rows,
                "purged_rows": val_purged_rows,
                "clean_rows": val_clean_rows,
                "purged_sessions": [d.strftime("%Y-%m-%d") for d in val_purged_sessions],
                "purge_reason": f"Label T+1 > {val_nominal_end_str} (ends after validation year)" if val_purged_sessions else "Final dev session 2023-12-29 already purged at source",
                "query_filter": f"(date >= '{val_actual_start}') & (date <= '{val_actual_end}')",
            },
            "integrity": {
                "common_sessions": 0,
                "is_disjoint": True,
            }
        }
        folds_summary.append(fold_info)

        log(f"  [Fold {f_id}] Train [{train_actual_start} -> {train_actual_end}] ({len(train_clean_sessions)} phiên, {train_clean_rows:,} dòng) | "
            f"Val [{val_actual_start} -> {val_actual_end}] ({len(val_clean_sessions)} phiên, {val_clean_rows:,} dòng)")

    # 3. Tạo cấu hình metadata tổng thể
    total_schedule_meta = {
        "schedule_name": "walk_forward_expanding_5folds_v1",
        "dataset_source": "data/processed/baseline_dataset_v1.parquet",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": "expanding_window_walk_forward",
        "number_of_folds": 5,
        "input_features": [
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
        ],
        "target_train_col": "target_rank",
        "target_eval_col": "target_return",
        "benchmark_eval_col": "ret_20d",
        "oos_frozen_period": {
            "period_label": "2024-2026",
            "status": "STRICTLY_FROZEN",
            "reason": "Reserved exclusively for final unseen out-of-sample evaluation",
        },
        "subsequent_execution_policy": {
            "scaling_policy": "Fit StandardScaler on Train of each fold independently, transform Val",
            "model_policy": "Fit Ridge(alpha=1.0) on Train of each fold independently, predict Val",
            "evaluation_metric": "Daily Spearman Rank IC between ridge_score and target_return",
            "benchmark_metric": "Daily Spearman Rank IC between ret_20d and target_return",
        },
        "folds": folds_summary,
    }

    return folds_summary, total_schedule_meta


def main():
    parser = argparse.ArgumentParser(description="Tạo lịch 5-fold Walk-Forward cho Ridge Baseline v1.")
    parser.add_argument("--save-yaml", action="store_true", default=True, help="Lưu cấu hình YAML.")
    args = parser.parse_args()

    folds, meta = build_walk_forward_schedule()

    if args.save_yaml:
        log("\n[4/4] Lưu tệp cấu hình YAML tái lập...")
        CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_SCHEDULE_YAML, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, default_flow_style=False, sort_keys=False)
        log(f"  -> Đã lưu cấu hình: {OUTPUT_SCHEDULE_YAML}")

    # In bảng tóm tắt 5 fold ra console
    log("\n" + "=" * 105)
    log("BẢNG TỔNG HỢP LỊCH WALK-FORWARD 5 FOLDS (EXPANDING WINDOW) CHO RIDGE BASELINE V1")
    log("=" * 105)
    header = f"{'Fold':<8} | {'Tập':<5} | {'Khoảng Ngày Thực Tế':<25} | {'Số Phiên':<10} | {'Dòng Danh Nghĩa':<16} | {'Dòng Purge':<12} | {'Dòng Sạch':<15} | {'Phiên Bị Purge'}"
    log(header)
    log("-" * 105)

    for f in folds:
        fid = f["fold_id"]
        tr = f["train"]
        vl = f["validation"]
        log(f"{fid:<8} | {'Train':<5} | {tr['actual_start']} -> {tr['actual_end']:<10} | {tr['clean_sessions']:<10} | {tr['nominal_rows']:<16,} | {tr['purged_rows']:<12,} | {tr['clean_rows']:<15,} | {tr['purged_sessions']}")
        log(f"{'':<8} | {'Val':<5} | {vl['actual_start']} -> {vl['actual_end']:<10} | {vl['clean_sessions']:<10} | {vl['nominal_rows']:<16,} | {vl['purged_rows']:<12,} | {vl['clean_rows']:<15,} | {vl['purged_sessions']}")
        log("-" * 105)

    log("\n" + "=" * 105)
    log("XÁC NHẬN ĐỐI CHIẾU MỐC (BENCHMARK CHECK):")
    log(f"  - Fold 1 Train sạch: {folds[0]['train']['clean_rows']:,} dòng (Mốc: 4,307,308 dòng) -> TRÙNG KHỚP 100%.")
    log(f"  - Tập OOS 2024-2026: ĐÓNG BĂNG TUYỆT ĐỐI (STRICTLY FROZEN).")
    log("=" * 105)


if __name__ == "__main__":
    main()
