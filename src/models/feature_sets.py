"""
src.models.feature_sets
=======================
Danh sách feature cho Phase 3 và các tín hiệu baseline không cần feature store.

FEATURES_V1: 16 ứng viên theo docs/specifications/features_v1.md (chưa có full store).
  Mỗi feature dự kiến lưu dạng ma trận 2D tại data/processed/features/<tên>.parquet
  (cùng trục ngày × canonical_sid với data/processed/matrices).
  Không gán dấu cố định: model tự học hướng trong từng fold (tránh chọn dấu bằng IC toàn kỳ).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from src.utils.config import load_config

FEATURES_V1: List[str] = [
    "ret_1d", "ret_5d", "ret_20d", "ret_60d", "mom_12m_skip_1m",
    "vol_realized_20d", "vol_realized_60d", "vol_parkinson_20d", "downside_deviation_20d",
    "amihud_illiq_20d", "volume_ratio_5_20", "log_dollar_volume_20d",
    "ret_intraday", "ret_overnight", "rsi_14d", "bollinger_pct_b_20d",
]


def features_dir() -> Path:
    return load_config().resolve_path("data/processed/features")


def available_features(names: List[str] = FEATURES_V1, directory: Optional[Path] = None) -> List[str]:
    d = directory or features_dir()
    return [n for n in names if (d / f"{n}.parquet").exists()]


def load_feature_matrix(
    name: str,
    dates: pd.DatetimeIndex,
    sids: pd.Index,
    directory: Optional[Path] = None,
) -> pd.DataFrame:
    """Đọc một ma trận feature và căn theo (dates, sids) — bỏ mọi ngày ngoài `dates`."""
    m = pd.read_parquet((directory or features_dir()) / f"{name}.parquet")
    m.index = pd.to_datetime(m.index)
    return m.reindex(index=dates, columns=sids)


def load_feature_matrices(
    names: List[str],
    dates: pd.DatetimeIndex,
    sids: pd.Index,
    directory: Optional[Path] = None,
    lazy: bool = False,
) -> Dict[str, Union[pd.DataFrame, Callable[[], pd.DataFrame]]]:
    """
    Đọc nhiều ma trận feature. lazy=True trả về hàm nạp cho từng feature để build_panel
    đọc lần lượt (16 ma trận ngày × SID cùng lúc tốn vài GB RAM).
    """
    if lazy:
        return {n: (lambda n=n: load_feature_matrix(n, dates, sids, directory)) for n in names}
    return {n: load_feature_matrix(n, dates, sids, directory) for n in names}


def reversal_5d(adj_close: pd.DataFrame, bar_quality_mask: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Baseline Reversal_5D của thầy, dạng tỷ số: P[t-5] / P[t-1] − 1.

    Công thức gốc (P[t-5] − P[t-1]) / 5 phụ thuộc mức giá tuyệt đối; với giá back-adjusted
    mức giá quá khứ chứa hệ số split TƯƠNG LAI → rank chéo giữa các mã bị nhiễm look-ahead.
    Dạng tỷ số giữ nguyên dấu/ý nghĩa (giá giảm 4 phiên trước T → điểm cao) và bất biến với
    hệ số điều chỉnh. Cần đủ 5 giá sạch liên tiếp P[t-5..t-1], thiếu → NaN.
    """
    p = adj_close.where(bar_quality_mask.reindex_like(adj_close).fillna(False).astype(bool)) \
        if bar_quality_mask is not None else adj_close
    p = p.where(p > 0)
    lag = p.shift(1)
    full = lag.notna().rolling(5, min_periods=5).sum() == 5
    return (p.shift(5) / lag - 1.0).where(full)
