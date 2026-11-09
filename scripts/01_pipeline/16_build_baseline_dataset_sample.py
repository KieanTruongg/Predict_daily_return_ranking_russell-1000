"""
Pipeline Script 16: Build Baseline Dataset Sample (Trial Verification)
====================================================================
Mục tiêu:
1. Thử nghiệm bộ sinh dataset baseline v1 trên 3 phiên giao dịch đại diện:
   - 2000-07-03: Phiên có cổ phiếu mới niêm yết có nhãn hợp lệ nhưng thiếu mom_12m (ví dụ: A, AGIL, AKAM).
   - 2015-06-15: Phiên giao dịch bình thường thanh khoản cao để đối chiếu.
   - 2023-12-29: Phiên cuối cùng của tập Development để kiểm tra cơ chế purge.
2. Kiểm tra tính toàn vẹn của logic xếp hạng target rank:
   - Tính rank cross-sectional trên toàn bộ U_label[T] (strict_membership & valid_label & isfinite(target_return)).
   - Chuẩn hóa rank về đoạn [0, 1] với average ties.
   - Chứng minh rank của các cổ phiếu đủ X không bị thay đổi khi loại bỏ các cổ phiếu thiếu X (No Re-ranking).
3. Phân biệt rõ ràng giữa Inference Eligibility tại T và Training Eligibility (Complete-case).
4. Sử dụng cơ chế predicate pushdown đọc Parquet chỉ cho các ngày được yêu cầu, kiểm tra tính hợp lệ
   của ngày trong Development window và đối soát độ đồng nhất trục ngày, SID giữa các ma trận.
5. Xuất bảng dữ liệu 17 cột theo đúng đặc tả docs/specifications/baseline_dataset_v1.md.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

from src.data.matrix_loader import get_matrices_dir, load_config, load_matrix
from src.quality.quality_window import OOSFreezeViolationError

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MATRICES_DIR = DATA_DIR / "matrices"
FEATURES_DIR = DATA_DIR / "features"

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


def validate_requested_dates(
    dates: List[pd.Timestamp],
    dev_start_date: str = "2000-07-01",
    dev_end_date: str = "2023-12-29",
) -> None:
    """Xác thực tất cả các ngày yêu cầu phải nằm trọn vẹn trong cửa sổ Development."""
    t_start = pd.Timestamp(dev_start_date)
    t_end = pd.Timestamp(dev_end_date)
    for d in dates:
        if d < t_start or d > t_end:
            raise ValueError(
                f"Ngày yêu cầu '{d.strftime('%Y-%m-%d')}' nằm ngoài cửa sổ Development "
                f"[{dev_start_date}, {dev_end_date}]."
            )


def load_matrix_with_pushdown(
    matrix_name: str,
    dates: List[pd.Timestamp],
    matrices_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Nạp dữ liệu ma trận Parquet dùng predicate pushdown thông qua src.data.matrix_loader.
    Chỉ nạp các dòng ứng với danh sách ngày được yêu cầu, không nạp toàn bộ ma trận rồi cắt.
    """
    return load_matrix(
        matrix_name=matrix_name,
        dates=dates,
        matrices_dir=matrices_dir,
    )


def compute_cross_sectional_target_rank(
    target_returns: pd.Series,
) -> pd.Series:
    """
    Tính thứ hạng lát cắt ngang của target_return trên tập nhãn hợp lệ U_label[T].
    - method='average' cho ties
    - Scale về đoạn [0.0, 1.0]
    - N = 1 -> 0.5
    - N = 0 -> Series rỗng
    """
    # Chỉ giữ các giá trị hữu hạn (np.isfinite)
    valid_returns = target_returns[target_returns.notna() & np.isfinite(target_returns)]
    n_label = len(valid_returns)

    if n_label == 0:
        return pd.Series(index=target_returns.index, dtype=float)
    if n_label == 1:
        res = pd.Series(np.nan, index=target_returns.index, dtype=float)
        res.loc[valid_returns.index] = 0.5
        return res

    ranks = valid_returns.rank(method="average", ascending=True)
    norm_ranks = (ranks - 1.0) / (float(n_label) - 1.0)

    res = pd.Series(np.nan, index=target_returns.index, dtype=float)
    res.loc[valid_returns.index] = norm_ranks
    return res


def build_baseline_sample(
    sample_dates: List[pd.Timestamp],
    filter_training_only: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, dict]]:
    """
    Xây dựng bảng dữ liệu phẳng cho các ngày chỉ định với predicate pushdown.

    Parameters
    ----------
    sample_dates : List[pd.Timestamp]
        Danh sách các ngày cần xử lý (phải nằm trong Development window).
    filter_training_only : bool
        Nếu True: chỉ giữ các dòng thỏa mãn Training Eligibility (complete case).
        Nếu False: giữ toàn bộ các dòng thuộc strict_membership_mask tại T,
                   kèm đầy đủ cột cờ hiệu eligibility để audit.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, dict]]
        DataFrame bảng phẳng và từ điển thống kê chi tiết theo ngày.
    """
    cfg = load_config()
    validate_requested_dates(sample_dates, cfg.dev_start_date, cfg.dev_end_date)

    log(f"Bắt đầu xây dựng baseline dataset sample cho {len(sample_dates)} phiên giao dịch (pushdown scan)...")

    # 1. Nạp các ma trận mặt nạ và giá/khối lượng dùng pushdown
    log("Nạp các ma trận mặt nạ và giá/khối lượng via predicate pushdown...")
    matrix_names = [
        "strict_membership_mask",
        "valid_label_mask",
        "target_next_return",
        "is_bad_data_period",
        "is_spinoff_discontinuity",
        "is_consecutive_session",
        "close",
        "volume",
    ]
    loaded_matrices: Dict[str, pd.DataFrame] = {}
    for mname in matrix_names:
        loaded_matrices[mname] = load_matrix_with_pushdown(mname, sample_dates, matrices_dir=MATRICES_DIR)

    # 2. Nạp 13 ma trận đặc trưng Close/Volume dùng pushdown
    log(f"Nạp {len(BASELINE_13_FEATURES)} ma trận đặc trưng Close/Volume via predicate pushdown...")
    feat_matrices: Dict[str, pd.DataFrame] = {}
    for feat_name in BASELINE_13_FEATURES:
        feat_matrices[feat_name] = load_matrix_with_pushdown(feat_name, sample_dates, matrices_dir=FEATURES_DIR)

    # 3. Kiểm tra đối soát trục ngày và SID khớp tuyệt đối giữa feature, mask và target
    ref_idx = loaded_matrices["strict_membership_mask"].index
    ref_cols = loaded_matrices["strict_membership_mask"].columns

    for name, mat in {**loaded_matrices, **feat_matrices}.items():
        if not mat.index.equals(ref_idx):
            raise ValueError(
                f"Lỗi không khớp trục ngày: Ma trận '{name}' có index {mat.index} "
                f"khác với index tham chiếu {ref_idx}."
            )
        if not mat.columns.equals(ref_cols):
            raise ValueError(
                f"Lỗi không khớp cột SID: Ma trận '{name}' có số cột {len(mat.columns)} "
                f"khác với cột tham chiếu {len(ref_cols)}."
            )

    strict_mem = loaded_matrices["strict_membership_mask"]
    valid_label = loaded_matrices["valid_label_mask"]
    target_ret = loaded_matrices["target_next_return"]
    is_bad = loaded_matrices["is_bad_data_period"]
    is_spinoff = loaded_matrices["is_spinoff_discontinuity"]
    is_consec = loaded_matrices["is_consecutive_session"]
    close = loaded_matrices["close"]
    volume = loaded_matrices["volume"]

    sids = ref_cols.tolist()
    daily_stats = {}
    rows_list = []

    for d in sample_dates:
        if d not in strict_mem.index:
            log(f"Cảnh báo: Ngày {d.strftime('%Y-%m-%d')} không có trong ma trận.")
            continue

        s_mem_row = strict_mem.loc[d] == True
        v_lbl_row = valid_label.loc[d] == True
        t_ret_row = target_ret.loc[d]

        # Kiểm tra tính hữu hạn của target_return bằng np.isfinite
        t_ret_finite = t_ret_row.notna() & np.isfinite(t_ret_row)

        # Tập nhãn hợp lệ U_label[T]: nằm trong strict membership, valid_label == True, và target_return hữu hạn
        u_label_mask = s_mem_row & v_lbl_row & t_ret_finite
        n_label = int(u_label_mask.sum())

        # BƯỚC QUAN TRỌNG: Tính target_rank trên TOÀN BỘ U_label[T] trước khi lọc X
        target_returns_for_ranking = t_ret_row.copy()
        target_returns_for_ranking[~u_label_mask] = np.nan
        target_ranks_row = compute_cross_sectional_target_rank(target_returns_for_ranking)

        # Tính toán cờ hiệu 13 features hữu hạn (np.isfinite)
        feat_valid_row = pd.Series(True, index=sids)
        feat_values_dict = {}
        for feat_name in BASELINE_13_FEATURES:
            vals = feat_matrices[feat_name].loc[d]
            feat_values_dict[feat_name] = vals
            feat_valid_row &= vals.notna() & np.isfinite(vals)

        # Điều kiện Inference Eligibility tại ngày T (Mục 5.1):
        # 1. strict_membership == True
        # 2. bar_quality: (~is_bad) & (~is_spinoff)
        # 3. is_consecutive_session == True
        # 4. close hữu hạn và > 0: np.isfinite(close) & (close > 0)
        # 5. volume hữu hạn và > 0: np.isfinite(volume) & (volume > 0)
        # 6. Tất cả 13 features hữu hạn (np.isfinite)
        c_close = close.loc[d]
        c_vol = volume.loc[d]

        bar_clean = (~is_bad.loc[d].fillna(False).astype(bool)) & (~is_spinoff.loc[d].fillna(False).astype(bool))
        price_clean = c_close.notna() & np.isfinite(c_close) & (c_close > 0)
        vol_clean = c_vol.notna() & np.isfinite(c_vol) & (c_vol > 0)
        consec_clean = is_consec.loc[d].fillna(False).astype(bool)

        clean_at_t = bar_clean & price_clean & vol_clean & consec_clean
        inference_elig_row = s_mem_row & clean_at_t & feat_valid_row

        # Điều kiện Training Eligibility (Mục 5.2):
        # Inference Eligibility AND Thuộc U_label[T]
        training_elig_row = inference_elig_row & u_label_mask

        # Thống kê chi tiết
        n_strict = int(s_mem_row.sum())
        n_inf_elig = int(inference_elig_row.sum())
        n_train_elig = int(training_elig_row.sum())
        n_valid_label_miss_x = int((u_label_mask & (~feat_valid_row)).sum())
        n_inf_no_label = int((inference_elig_row & (~u_label_mask)).sum())

        daily_stats[d.strftime("%Y-%m-%d")] = {
            "strict_membership_count": n_strict,
            "label_ranked_count": n_label,
            "inference_eligible_count": n_inf_elig,
            "training_eligible_count": n_train_elig,
            "valid_label_missing_x_count": n_valid_label_miss_x,
            "inference_eligible_no_label_count": n_inf_no_label,
        }

        # Chọn tập SID cần đưa vào bảng kết quả
        if filter_training_only:
            selected_sids = [s for s in sids if training_elig_row[s]]
        else:
            # Giữ tất cả thành viên strict membership
            selected_sids = [s for s in sids if s_mem_row[s]]

        for sid in selected_sids:
            row_dict = {
                "date": d,
                "canonical_sid": sid,
            }
            # 13 features
            for feat_name in BASELINE_13_FEATURES:
                row_dict[feat_name] = float(feat_values_dict[feat_name][sid])

            # Target
            row_dict["target_return"] = float(target_returns_for_ranking[sid])
            row_dict["target_rank"] = float(target_ranks_row[sid])

            # Metadata cờ hiệu phục vụ audit
            if not filter_training_only:
                row_dict["is_inference_eligible"] = bool(inference_elig_row[sid])
                row_dict["is_training_eligible"] = bool(training_elig_row[sid])
                row_dict["is_u_label"] = bool(u_label_mask[sid])
                row_dict["all_13_features_valid"] = bool(feat_valid_row[sid])

            rows_list.append(row_dict)

    df_out = pd.DataFrame(rows_list)
    if not df_out.empty:
        # Sắp xếp theo thứ tự ngày tăng dần, sau đó theo canonical_sid
        sort_cols = ["date", "canonical_sid"]
        df_out = df_out.sort_values(sort_cols).reset_index(drop=True)

    return df_out, daily_stats


def demonstrate_rank_stability(d: pd.Timestamp) -> dict:
    """
    Chứng minh thực nghiệm nguyên tắc No Re-ranking:
    So sánh thứ hạng chuẩn (tính trên toàn bộ U_label) với thứ hạng sai lệch
    (nếu ai đó tính lại rank chỉ trên tập các cổ phiếu có đủ X).
    """
    strict_mem = load_matrix_with_pushdown("strict_membership_mask", [d], MATRICES_DIR).loc[d] == True
    valid_label = load_matrix_with_pushdown("valid_label_mask", [d], MATRICES_DIR).loc[d] == True
    target_ret = load_matrix_with_pushdown("target_next_return", [d], MATRICES_DIR).loc[d]

    # 13 features validity
    feat_valid = pd.Series(True, index=strict_mem.index)
    for feat_name in BASELINE_13_FEATURES:
        vals = load_matrix_with_pushdown(feat_name, [d], FEATURES_DIR).loc[d]
        feat_valid &= vals.notna() & np.isfinite(vals)

    u_label_mask = strict_mem & valid_label & target_ret.notna() & np.isfinite(target_ret)
    train_mask = u_label_mask & feat_valid

    n_label = int(u_label_mask.sum())
    n_train = int(train_mask.sum())

    # 1. Thứ hạng đúng (Proper Ranking): Tính trên U_label (n_label cổ phiếu)
    ret_proper = target_ret[u_label_mask]
    ranks_proper = compute_cross_sectional_target_rank(ret_proper)

    # 2. Thứ hạng sai lệch (Improper Re-ranking): Tính lại chỉ trên train_mask (n_train cổ phiếu)
    ret_improper = target_ret[train_mask]
    ranks_improper = compute_cross_sectional_target_rank(ret_improper)

    # So sánh trên giao điểm (các cổ phiếu có mặt trong cả 2)
    common_sids = ret_improper.index
    proper_subset = ranks_proper.loc[common_sids]
    improper_subset = ranks_improper.loc[common_sids]
    diff = (proper_subset - improper_subset).abs()

    # Tìm một cổ phiếu tiêu biểu thiếu X (nằm trong u_label nhưng không nằm trong train_mask)
    missing_x_sids = [s for s in u_label_mask.index if u_label_mask[s] and not feat_valid[s]]
    sample_miss = missing_x_sids[0] if missing_x_sids else None

    return {
        "date": d.strftime("%Y-%m-%d"),
        "n_label": n_label,
        "n_train": n_train,
        "n_dropped_missing_x": len(missing_x_sids),
        "max_rank_distortion": float(diff.max()),
        "mean_rank_distortion": float(diff.mean()),
        "sample_missing_stock": sample_miss,
        "sample_missing_stock_return": float(target_ret.loc[sample_miss]) if sample_miss else None,
        "sample_missing_stock_rank": float(ranks_proper.loc[sample_miss]) if sample_miss else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Chạy thử nghiệm builder dataset baseline v1 trên các phiên đại diện.")
    parser.add_argument("--save-parquet", action="store_true", help="Lưu kết quả mẫu ra file Parquet để kiểm tra.")
    args = parser.parse_args()

    test_dates = [
        pd.Timestamp("2000-07-03"),  # Phiên có nhiều mã mới IPO thiếu mom_12m
        pd.Timestamp("2015-06-15"),  # Phiên giao dịch bình thường
        pd.Timestamp("2023-12-29"),  # Phiên cuối Development bị purge
    ]

    log("=" * 80)
    log("KIỂM TRA THỰC NGHIỆM BUILDER DATASET BASELINE V1 (3 PHIÊN ĐẠI DIỆN - PUSHDOWN SCAN)")
    log("=" * 80)

    # Chạy trích xuất toàn bộ thành viên kèm cờ hiệu
    df_audit, stats = build_baseline_sample(test_dates, filter_training_only=False)

    # In bảng thống kê tổng hợp theo ngày
    log("\n--- BẢNG THỐNG KÊ CHI TIẾT THEO NGÀY ---")
    stats_df = pd.DataFrame(stats).T
    print(stats_df.to_string())

    # Kiểm tra Rank Stability trên phiên 2000-07-03
    log("\n" + "=" * 80)
    log("ĐỐI SOÁT TÍNH ỔN ĐỊNH CỦA THỨ HẠNG (RANK STABILITY) TRÊN PHIÊN 2000-07-03")
    log("=" * 80)
    stability = demonstrate_rank_stability(pd.Timestamp("2000-07-03"))
    for k, v in stability.items():
        if isinstance(v, float):
            log(f"  {k}: {v:.6f}")
        else:
            log(f"  {k}: {v}")

    # In các ví dụ mẫu cụ thể
    log("\n" + "=" * 80)
    log("VÍ DỤ MẪU CÁC DÒNG QUAN SÁT TIÊU BIỂU (CANONICAL ROWS)")
    log("=" * 80)

    # 1. Cổ phiếu có nhãn nhưng thiếu mom_12m (ví dụ: Agilent A RPTMYV3VC57P ngày 2000-07-03)
    d1 = pd.Timestamp("2000-07-03")
    sid_a = "A RPTMYV3VC57P"
    row_a = df_audit[(df_audit["date"] == d1) & (df_audit["canonical_sid"] == sid_a)]
    if not row_a.empty:
        r = row_a.iloc[0]
        log(f"\n[Ca 1: Cổ phiếu có nhãn nhưng thiếu X] {sid_a} tại {d1.strftime('%Y-%m-%d')}:")
        log(f"  - ret_1d: {r['ret_1d']:.4f}, ret_20d: {r['ret_20d']:.4f}")
        log(f"  - mom_12m_skip_1m: {r['mom_12m_skip_1m']} (Thiếu do mới niêm yết ~150 phiên)")
        log(f"  - target_return: {r['target_return']:.6f}")
        log(f"  - target_rank (tính trên 931 mã): {r['target_rank']:.6f}")
        log(f"  - is_inference_eligible: {r['is_inference_eligible']} (False vì thiếu X)")
        log(f"  - is_training_eligible: {r['is_training_eligible']} (False vì complete-case loại bỏ)")
        log(f"  - Diễn giải: Tham gia xếp hạng N_label để cố định thang đo phân phối lợi suất thị trường,")
        log(f"               nhưng không đưa vào ma trận huấn luyện của Ridge vì vector X không trọn vẹn.")

    # 2. Cổ phiếu đủ 13 X nhưng volume phiên kế tiếp bằng 0 (ví dụ: CCB R735QTJ8XC9X ngày 2000-07-03)
    sid_ccb = "CCB R735QTJ8XC9X"
    row_ccb = df_audit[(df_audit["date"] == d1) & (df_audit["canonical_sid"] == sid_ccb)]
    if not row_ccb.empty:
        r = row_ccb.iloc[0]
        log(f"\n[Ca 2: Cổ phiếu đủ 13 X nhưng volume phiên kế tiếp bằng 0] {sid_ccb} tại {d1.strftime('%Y-%m-%d')}:")
        log(f"  - ret_1d: {r['ret_1d']:.4f}, mom_12m_skip_1m: {r['mom_12m_skip_1m']:.4f}")
        log(f"  - target_return: {r['target_return']} (NaN do volume phiên kế tiếp bằng 0)")
        log(f"  - target_rank: {r['target_rank']} (NaN)")
        log(f"  - is_inference_eligible: {r['is_inference_eligible']} (True: Đạt đầy đủ điều kiện dự đoán tại T)")
        log(f"  - is_training_eligible: {r['is_training_eligible']} (False: Thiếu nhãn thực tế để tính loss)")
        log(f"  - Diễn giải: Tại thời điểm chốt phiên T, mô hình hoàn toàn có thể sinh dự đoán y_hat.")
        log(f"               Tuy nhiên tại T+1 volume bằng 0 nên nhãn bị loại theo chính sách hiện tại")
        log(f"               (chưa kết luận halt nếu chưa có nguồn độc lập xác nhận).")

    # 3. Cổ phiếu hoàn chỉnh cho Training (ví dụ: AAPL R735QTJ8XC9X ngày 2000-07-03)
    sid_aapl = "AAPL R735QTJ8XC9X"
    row_aapl = df_audit[(df_audit["date"] == d1) & (df_audit["canonical_sid"] == sid_aapl)]
    if not row_aapl.empty:
        r = row_aapl.iloc[0]
        log(f"\n[Ca 3: Cổ phiếu hoàn chỉnh cho Training] {sid_aapl} tại {d1.strftime('%Y-%m-%d')}:")
        log(f"  - ret_1d: {r['ret_1d']:.4f}, mom_12m_skip_1m: {r['mom_12m_skip_1m']:.4f}, rsi_14d: {r['rsi_14d']:.2f}")
        log(f"  - target_return: {r['target_return']:.6f}")
        log(f"  - target_rank: {r['target_rank']:.6f}")
        log(f"  - is_inference_eligible: {r['is_inference_eligible']} (True)")
        log(f"  - is_training_eligible: {r['is_training_eligible']} (True)")

    # 4. Phiên cuối kỳ 2023-12-29 (Purge boundary test)
    d3 = pd.Timestamp("2023-12-29")
    row_last = df_audit[df_audit["date"] == d3].iloc[0]
    log(f"\n[Ca 4: Phiên cuối Development 2023-12-29 bị purge] Mã {row_last['canonical_sid']}:")
    log(f"  - ret_1d: {row_last['ret_1d']:.4f}, ret_20d: {row_last['ret_20d']:.4f}")
    log(f"  - target_return: {row_last['target_return']} (NaN do purge)")
    log(f"  - target_rank: {row_last['target_rank']} (NaN)")
    log(f"  - is_inference_eligible: {row_last['is_inference_eligible']} (True: Đạt điều kiện dự đoán tại T)")
    log(f"  - is_training_eligible: {row_last['is_training_eligible']} (False: Bị purge để bảo toàn ranh giới OOS)")

    # 5. Lưu mẫu dataset thuần huấn luyện nếu có yêu cầu
    out_sample_file = DATA_DIR / "sample_baseline_dataset_3days.parquet"
    if args.save_parquet:
        df_train_only, _ = build_baseline_sample(test_dates, filter_training_only=True)
        # Chỉ giữ 17 cột chuẩn
        df_train_only = df_train_only[SCHEMA_17_COLUMNS]

        # Kiểm tra tính trọn vẹn: không trùng (date, canonical_sid) và toàn bộ giá trị số hữu hạn
        dup_count = df_train_only.duplicated(subset=["date", "canonical_sid"]).sum()
        if dup_count > 0:
            raise ValueError(f"Phát hiện {dup_count} dòng trùng lặp cặp (date, canonical_sid)!")

        for col in BASELINE_13_FEATURES + ["target_return", "target_rank"]:
            non_finite = (~np.isfinite(df_train_only[col])).sum()
            if non_finite > 0:
                raise ValueError(f"Cột {col} chứa {non_finite} giá trị không hữu hạn!")

        df_train_only.to_parquet(out_sample_file, compression="snappy", index=False)
        log(f"\nĐã kiểm tra và lưu {len(df_train_only):,} dòng huấn luyện mẫu vào {out_sample_file}")

    log("\n" + "=" * 80)
    log("HOÀN THÀNH KIỂM TRA THỬ NGHIỆM BUILDER DATASET BASELINE V1")
    log("=" * 80)


if __name__ == "__main__":
    main()
