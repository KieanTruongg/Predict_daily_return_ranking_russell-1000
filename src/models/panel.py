"""
src.models.panel
================
Cầu nối giữa kho ma trận 2D (ngày × canonical_sid) và panel long dùng để train model.

Quy ước (docs/specifications/target_and_timing_v1.md):
  - target_next_rank[T] = (rank − 1) / (N[T] − 1) của target_next_return trên tập nhãn hợp lệ
    (valid_label_mask) của ngày T; N = 1 → 0.5; ngoài tập → NaN.
  - Feature tại T được rank cross-sectional trong tập dự đoán tại T (`universe_mask`,
    thường là valid_data_mask). KHÔNG dùng valid_label_mask để biến đổi feature.
  - Panel chỉ giữ các dòng có nhãn hợp lệ (để train/đánh giá); feature thiếu → 0 sau rank
    (trung tính), chỉ ở bước tạo input cho model, không ghi ngược vào feature store.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.features.transforms import cross_sectional_rank


def target_next_rank(target_next_return: pd.DataFrame, valid_label_mask: pd.DataFrame) -> pd.DataFrame:
    """Nhãn thứ hạng uniform [0, 1] theo ngày, chỉ trên ô nhãn hợp lệ."""
    return cross_sectional_rank(target_next_return, mask=valid_label_mask, pct=True)


def _aligned(m: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    if m.index.equals(ref.index) and m.columns.equals(ref.columns):
        return m
    return m.reindex(index=ref.index, columns=ref.columns)


def build_panel(
    features: Dict[str, Union[pd.DataFrame, Callable[[], pd.DataFrame]]],
    target_next_return: pd.DataFrame,
    valid_label_mask: pd.DataFrame,
    universe_mask: pd.DataFrame,
    rank_features: bool = True,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    `features`: tên → ma trận, hoặc tên → hàm không đối số trả về ma trận (nạp lần lượt, tiết kiệm RAM).
    Trả về (panel, feature_cols). panel gồm: date, canonical_sid, <features>,
    target_next_return, target_next_rank — mỗi dòng là 1 ô valid_label_mask == True.

    rank_features=True: feature = cross_sectional_rank(feature, universe_mask) − 0.5, NaN → 0.
    rank_features=False: giữ giá trị gốc (NaN giữ nguyên) cho model tự xử lý.
    """
    ref = target_next_return
    label = _aligned(valid_label_mask, ref).fillna(False).astype(bool)
    keep = label.to_numpy().copy()
    if start is not None:
        keep[ref.index < pd.Timestamp(start)] = False
    if end is not None:
        keep[ref.index > pd.Timestamp(end)] = False

    r_idx, c_idx = np.nonzero(keep)
    panel = pd.DataFrame({
        "date": ref.index.values[r_idx],
        "canonical_sid": ref.columns.values[c_idx],
    })

    universe = _aligned(universe_mask, ref).fillna(False).astype(bool)
    names = list(features)
    for name in names:
        f = features[name]
        f = _aligned(f() if callable(f) else f, ref)
        if rank_features:
            f = cross_sectional_rank(f, mask=universe, pct=True) - 0.5
            panel[name] = np.nan_to_num(f.to_numpy(dtype=np.float32)[r_idx, c_idx], nan=0.0)
        else:
            panel[name] = f.to_numpy(dtype=np.float32)[r_idx, c_idx]

    panel["target_next_return"] = ref.to_numpy(dtype=float)[r_idx, c_idx]
    panel["target_next_rank"] = target_next_rank(ref, label).to_numpy(dtype=float)[r_idx, c_idx]
    return panel, names
