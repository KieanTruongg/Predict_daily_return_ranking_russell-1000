"""
Pipeline Script 17: Build Baseline Dataset v1 (Development Full 5,911 Sessions)
=============================================================================
Mục tiêu:
1. Sinh bảng phẳng Parquet đầy đủ của Dataset Baseline v1 trên toàn bộ tập Development:
   - Khoảng thời gian: 2000-07-01 đến 2023-12-29 (5.911 phiên giao dịch).
   - Universe: Rổ Russell 1000 chính thức (strict_membership_mask == True tại ngày T).
   - Nhóm đặc trưng: 13 features Close/Volume chuẩn đã nghiệm thu.
   - Nhãn mục tiêu: target_return (masked next return) và target_rank (chuẩn hóa [0.0, 1.0]).
2. Tuân thủ tuyệt đối các nguyên tắc thiết kế bất biến:
   - Target rank tính trên toàn bộ U_label[T] trước khi lọc thiếu X (No Re-ranking).
   - Phiên cuối Development 2023-12-29 bị purge nhãn (0 mẫu huấn luyện).
   - Khóa duy nhất (date, canonical_sid).
   - 100% complete-case: toàn bộ 17 cột trong tập huấn luyện đều hữu hạn (np.isfinite).
3. Lưu kết quả ra file chuẩn: data/processed/baseline_dataset_v1.parquet.
4. Đối chiếu tính toàn vẹn với lát cắt mẫu 3 phiên (sample_baseline_dataset_3days.parquet).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đường dẫn thư mục dự án
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.matrix_loader import load_config, load_matrix

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MATRICES_DIR = DATA_DIR / "matrices"
FEATURES_DIR = DATA_DIR / "features"
OUTPUT_FILE = DATA_DIR / "baseline_dataset_v1.parquet"

# Danh sách 13 features Close/Volume chuẩn
BASELINE_13_FEATURES = [
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

SCHEMA_17_COLUMNS = [
    "date",
    "canonical_sid",
    *BASELINE_13_FEATURES,
    "target_return",
    "target_rank",
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def compute_cross_sectional_target_rank_matrix(
    target_ret: np.ndarray,
    u_label_mask: np.ndarray,
) -> np.ndarray:
    """
    Tính ma trận thứ hạng chéo ngang chuẩn hóa [0.0, 1.0] trên tập U_label[T] cho toàn bộ 5.911 phiên.
    - method='average' cho ties
    - N = 1 -> 0.5
    - N = 0 -> toàn bộ NaN (ví dụ: ngày 2023-12-29 bị purge)
    """
    n_dates, n_sids = target_ret.shape
    target_rank = np.full((n_dates, n_sids), np.nan, dtype=np.float64)

    for t in range(n_dates):
        valid_idx = np.where(u_label_mask[t])[0]
        n_label = len(valid_idx)
        if n_label == 0:
            continue
        elif n_label == 1:
            target_rank[t, valid_idx[0]] = 0.5
        else:
            rets = target_ret[t, valid_idx]
            ranks = pd.Series(rets).rank(method="average", ascending=True).values
            target_rank[t, valid_idx] = (ranks - 1.0) / (float(n_label) - 1.0)

    return target_rank


def build_full_baseline_dataset() -> Tuple[pd.DataFrame, dict]:
    """
    Xây dựng toàn bộ bảng phẳng baseline dataset v1 trên tập Development (5.911 phiên).
    """
    t_start = time.time()
    cfg = load_config()
    log(f"Bắt đầu xây dựng Baseline Dataset v1 trên tập Development [{cfg.dev_start_date} -> {cfg.dev_end_date}]...")

    # 1. Nạp các ma trận nền tảng (dev_only=True, không bao gồm warmup)
    log("[1/6] Nạp các ma trận rổ chỉ số, nến và nhãn...")
    strict_mem_df = load_matrix("strict_membership_mask", dev_only=True, matrices_dir=MATRICES_DIR)
    valid_label_df = load_matrix("valid_label_mask", dev_only=True, matrices_dir=MATRICES_DIR)
    target_ret_df = load_matrix("target_next_return", dev_only=True, matrices_dir=MATRICES_DIR)
    is_bad_df = load_matrix("is_bad_data_period", dev_only=True, matrices_dir=MATRICES_DIR)
    is_spinoff_df = load_matrix("is_spinoff_discontinuity", dev_only=True, matrices_dir=MATRICES_DIR)
    is_consec_df = load_matrix("is_consecutive_session", dev_only=True, matrices_dir=MATRICES_DIR)
    close_df = load_matrix("close", dev_only=True, matrices_dir=MATRICES_DIR)
    volume_df = load_matrix("volume", dev_only=True, matrices_dir=MATRICES_DIR)

    unique_dates = strict_mem_df.index
    unique_sids = strict_mem_df.columns
    n_dates = len(unique_dates)
    n_sids = len(unique_sids)

    log(f"  -> Không gian ma trận: {n_dates:,} phiên giao dịch x {n_sids:,} mã SIDs ({n_dates * n_sids:,} ô)")

    strict_mem = strict_mem_df.values == True
    valid_label = valid_label_df.values == True
    target_ret = target_ret_df.values
    is_bad = is_bad_df.values
    is_spinoff = is_spinoff_df.values
    is_consec = is_consec_df.values
    close = close_df.values
    volume = volume_df.values

    # 2. Xác định tập nhãn hợp lệ U_label[T]
    log("[2/6] Xác định tập nhãn hợp lệ U_label[T]...")
    target_ret_finite = np.isfinite(target_ret)
    u_label_mask = strict_mem & valid_label & target_ret_finite
    n_total_u_label = int(u_label_mask.sum())
    log(f"  -> Tổng số ô có nhãn hợp lệ U_label[T]: {n_total_u_label:,} ô")

    # 3. Tính toán target_rank chéo ngang trên toàn bộ U_label[T] (No Re-ranking)
    log("[3/6] Tính toán ma trận Target Rank chéo ngang trên toàn bộ U_label[T]...")
    t_rank_0 = time.time()
    target_rank = compute_cross_sectional_target_rank_matrix(target_ret, u_label_mask)
    log(f"  -> Hoàn thành tính Target Rank trong {time.time() - t_rank_0:.2f}s")
    assert np.isfinite(target_rank).sum() == n_total_u_label, "Mismatch giữa U_label và số ô target_rank hữu hạn!"

    # 4. Nạp 13 ma trận đặc trưng Close/Volume và kiểm tra tính hữu hạn
    log(f"[4/6] Nạp {len(BASELINE_13_FEATURES)} ma trận đặc trưng Close/Volume...")
    feat_arrays: Dict[str, np.ndarray] = {}
    feat_valid = np.ones((n_dates, n_sids), dtype=bool)

    for feat_name in BASELINE_13_FEATURES:
        f_df = load_matrix(feat_name, dev_only=True, matrices_dir=FEATURES_DIR)
        # Kiểm tra khớp trục
        if not f_df.index.equals(unique_dates):
            raise ValueError(f"Feature '{feat_name}' có trục ngày không khớp với strict_membership_mask.")
        if not f_df.columns.equals(unique_sids):
            raise ValueError(f"Feature '{feat_name}' có trục SIDs không khớp với strict_membership_mask.")
        arr = f_df.values
        feat_arrays[feat_name] = arr
        feat_valid &= np.isfinite(arr)

    # 5. Xác định điều kiện Inference Eligibility và Training Eligibility
    log("[5/6] Đánh giá điều kiện Inference Eligibility tại T và Training Eligibility...")
    bar_clean = (~np.nan_to_num(is_bad, nan=False).astype(bool)) & (~np.nan_to_num(is_spinoff, nan=False).astype(bool))
    price_clean = np.isfinite(close) & (close > 0)
    vol_clean = np.isfinite(volume) & (volume > 0)
    consec_clean = np.nan_to_num(is_consec, nan=False).astype(bool)

    clean_at_t = bar_clean & price_clean & vol_clean & consec_clean
    inference_eligible = strict_mem & clean_at_t & feat_valid
    train_eligible = inference_eligible & u_label_mask

    n_inf_elig = int(inference_eligible.sum())
    n_train_elig = int(train_eligible.sum())
    log(f"  -> Tổng số ô Inference-Eligible tại T: {n_inf_elig:,} ô")
    log(f"  -> Tổng số ô Training-Eligible (Complete-Case): {n_train_elig:,} ô")

    # 6. Trích xuất bảng phẳng 17 cột
    log("[6/6] Trích xuất bảng phẳng 17 cột và dựng DataFrame...")
    t_flat_0 = time.time()
    row_idx, col_idx = np.where(train_eligible)

    dates_flat = unique_dates[row_idx]
    sids_flat = unique_sids[col_idx].values

    data_dict = {
        "date": dates_flat,
        "canonical_sid": sids_flat,
    }
    for feat_name in BASELINE_13_FEATURES:
        data_dict[feat_name] = feat_arrays[feat_name][row_idx, col_idx]

    data_dict["target_return"] = target_ret[row_idx, col_idx]
    data_dict["target_rank"] = target_rank[row_idx, col_idx]

    df_out = pd.DataFrame(data_dict)

    # Đảm bảo sắp xếp tăng dần theo date và canonical_sid
    df_out = df_out.sort_values(["date", "canonical_sid"]).reset_index(drop=True)
    log(f"  -> Trích xuất hoàn tất trong {time.time() - t_flat_0:.2f}s. Kích thước DataFrame: {df_out.shape}")

    stats = {
        "total_sessions": n_dates,
        "total_sids": n_sids,
        "strict_membership_cells": int(strict_mem.sum()),
        "valid_label_cells": n_total_u_label,
        "inference_eligible_cells": n_inf_elig,
        "training_eligible_cells": n_train_elig,
        "missing_x_in_label_cells": int((u_label_mask & (~feat_valid)).sum()),
        "inf_eligible_missing_label_cells": int((inference_eligible & (~u_label_mask)).sum()),
        "total_build_time_sec": time.time() - t_start,
    }
    return df_out, stats


def verify_dataset_integrity(df: pd.DataFrame) -> None:
    """Kiểm tra tính toàn vẹn của dataset theo các tiêu chuẩn khắt khe nhất."""
    log("=" * 80)
    log("KIỂM ĐỊNH TÍNH TOÀN VẸN CỦA DATASET BASELINE V1")
    log("=" * 80)

    # 1. Kiểm tra 17 cột
    assert list(df.columns) == SCHEMA_17_COLUMNS, f"Schema không khớp! Hiện tại: {list(df.columns)}"
    log("  [Check 1/6] Đúng 17 cột schema chuẩn.")

    # 2. Kiểm tra không có bất kỳ giá trị NaN / Inf nào
    for col in SCHEMA_17_COLUMNS:
        n_null = df[col].isna().sum()
        assert n_null == 0, f"Cột {col} chứa {n_null} giá trị NaN!"
        if col not in ["date", "canonical_sid"]:
            n_non_finite = (~np.isfinite(df[col])).sum()
            assert n_non_finite == 0, f"Cột {col} chứa {n_non_finite} giá trị không hữu hạn!"
    log("  [Check 2/6] Toàn bộ 17 cột đều là giá trị hữu hạn (np.isfinite, zero NaN/Inf).")

    # 3. Kiểm tra khóa (date, canonical_sid) duy nhất
    n_dups = df.duplicated(subset=["date", "canonical_sid"]).sum()
    assert n_dups == 0, f"Phát hiện {n_dups} dòng trùng lặp cặp khóa (date, canonical_sid)!"
    log("  [Check 3/6] Cặp khóa (date, canonical_sid) là DUY NHẤT 100% (zero duplicate).")

    # 4. Kiểm tra biên target_rank trong [0.0, 1.0]
    min_rank = df["target_rank"].min()
    max_rank = df["target_rank"].max()
    assert min_rank >= 0.0 and max_rank <= 1.0, f"Target rank vượt biên [0, 1]: [{min_rank}, {max_rank}]"
    log(f"  [Check 4/6] Target rank nằm chuẩn xác trong đoạn [{min_rank:.6f}, {max_rank:.6f}].")

    # 5. Đối chiếu với lát cắt mẫu 3 phiên (sample_baseline_dataset_3days.parquet)
    sample_path = DATA_DIR / "sample_baseline_dataset_3days.parquet"
    if sample_path.exists():
        df_sample = pd.read_parquet(sample_path)
        sample_dates = df_sample["date"].unique()
        df_sub = df[df["date"].isin(sample_dates)].sort_values(["date", "canonical_sid"]).reset_index(drop=True)
        df_sample_sorted = df_sample.sort_values(["date", "canonical_sid"]).reset_index(drop=True)

        assert len(df_sub) == len(df_sample_sorted), (
            f"Số dòng trên 3 phiên mẫu không khớp! Full: {len(df_sub)}, Sample: {len(df_sample_sorted)}"
        )
        # So sánh độ sai khác số học giữa full và sample
        for col in BASELINE_13_FEATURES + ["target_return", "target_rank"]:
            max_abs_diff = (df_sub[col] - df_sample_sorted[col]).abs().max()
            assert max_abs_diff < 1e-12, f"Sai khác số học tại cột {col}: {max_abs_diff}"
        log(f"  [Check 5/6] Đối chiếu 3 phiên mẫu ({len(sample_dates)} ngày, {len(df_sub):,} dòng) TRÙNG KHỚP TUYỆT ĐỐI (diff < 1e-12).")
    else:
        log("  [Check 5/6] Bỏ qua đối chiếu (không tìm thấy sample_baseline_dataset_3days.parquet).")

    # 6. Kiểm tra phiên purge cuối kỳ 2023-12-29
    purge_date = pd.Timestamp("2023-12-29")
    n_purge_rows = (df["date"] == purge_date).sum()
    assert n_purge_rows == 0, f"Phiên cuối Development 2023-12-29 chứa {n_purge_rows} dòng (đúng ra phải là 0 do purge)!"
    log("  [Check 6/6] Xác nhận ngày 2023-12-29 có ĐÚNG 0 MẪU HUẤN LUYỆN (purge bảo vệ OOS hoàn hảo).")

    log("=" * 80)
    log("TẤT CẢ 6 TIÊU CHÍ TOÀN VẸN ĐỀU PASSED 100%!")
    log("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Sinh Dataset Baseline v1 đầy đủ trên toàn bộ 5.911 phiên Development.")
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Đường dẫn file Parquet đầu ra.")
    args = parser.parse_args()

    out_file = Path(args.output)
    df, stats = build_full_baseline_dataset()

    # Kiểm tra tính toàn vẹn
    verify_dataset_integrity(df)

    # Lưu file Parquet
    log(f"\nLưu dataset ({len(df):,} dòng x {len(df.columns)} cột) vào: {out_file}...")
    t_save_0 = time.time()
    df.to_parquet(out_file, compression="snappy", index=False)
    save_time = time.time() - t_save_0
    file_size_mb = out_file.stat().st_size / (1024 * 1024)

    log(f"  -> Lưu thành công trong {save_time:.2f}s! Dung lượng file Parquet: {file_size_mb:.2f} MB")

    # In báo cáo tổng hợp
    log("\n" + "=" * 80)
    log("TỔNG KẾT BÀN GIAO DATASET BASELINE V1 (DEVELOPMENT FULL)")
    log("=" * 80)
    log(f"  - Tổng số phiên giao dịch: {stats['total_sessions']:,}")
    log(f"  - Tổng số mã cổ phiếu (SIDs): {stats['total_sids']:,}")
    log(f"  - Tổng số dòng thực tế trong dataset: {len(df):,}")
    log(f"  - Số cột: {len(df.columns)} ({', '.join(SCHEMA_17_COLUMNS[:4])} ... {SCHEMA_17_COLUMNS[-1]})")
    log(f"  - Kích thước tệp trên đĩa: {file_size_mb:.2f} MB (Snappy compressed)")
    log(f"  - Tổng thời gian thực thi: {stats['total_build_time_sec']:.2f}s")
    log("=" * 80)


if __name__ == "__main__":
    main()
