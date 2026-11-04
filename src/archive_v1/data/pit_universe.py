"""
Point-in-Time (PIT) membership mask cho Russell 1000.

Vấn đề cần sửa:
  Danh sách membership năm Y (data/raw/universe/by_year/russell1000_{Y}.json) được
  Russell chốt ở Rank Day (~30/4) và chỉ CÓ HIỆU LỰC sau reconstitution
  (sau phiên đóng cửa thứ Sáu cuối cùng của tháng 6). Trước đây pipeline áp list năm Y
  cho cả 01/01 → 31/12 năm Y  ⇒  look-ahead bias ở nửa đầu năm.

Quy ước dùng ở đây:
  Ngày giao dịch d thuộc universe của list năm Y  ⇔  recon(Y) < d <= recon(Y+1)
  (recon(Y) = thứ Sáu cuối tháng 6 năm Y; list mới có hiệu lực từ phiên kế tiếp).
  Các ngày trước recon(năm đầu tiên) không có list hợp lệ → mask = False.

Output chính:
  build_pit_mask(dates, tickers) → DataFrame bool Date×Ticker,
  True nếu ticker thuộc Russell 1000 tại ngày đó (theo thông tin đã biết tại ngày đó).
"""
from __future__ import annotations

import glob
import json
import os
import re
from datetime import date, timedelta
from typing import Dict, Iterable, Optional, Set

import numpy as np
import pandas as pd

BY_YEAR_DIR = os.path.join("data", "raw", "universe", "by_year")

# Ghi đè ngày reconstitution nếu lịch thực tế của FTSE Russell khác quy tắc
# "thứ Sáu cuối tháng 6" (vd. trùng ngày nghỉ lễ). Format: {year: date(...)}.
RECON_DATE_OVERRIDES: Dict[int, date] = {}


def reconstitution_date(year: int) -> pd.Timestamp:
    """Ngày reconstitution năm `year` = thứ Sáu cuối cùng của tháng 6 (trừ khi bị override)."""
    if year in RECON_DATE_OVERRIDES:
        return pd.Timestamp(RECON_DATE_OVERRIDES[year])
    d = date(year, 6, 30)
    d -= timedelta(days=(d.weekday() - 4) % 7)  # lùi về thứ Sáu gần nhất (weekday 4)
    return pd.Timestamp(d)


def load_pit_lists(by_year_dir: str = BY_YEAR_DIR) -> Dict[int, Set[str]]:
    """Đọc russell1000_{year}.json → {year: set(tickers)}."""
    lists: Dict[int, Set[str]] = {}
    for fpath in sorted(glob.glob(os.path.join(by_year_dir, "russell1000_*.json"))):
        m = re.search(r"russell1000_(\d{4})\.json$", os.path.basename(fpath))
        if not m:
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            lists[int(m.group(1))] = {str(t).strip().upper() for t in json.load(f)}
    if not lists:
        raise FileNotFoundError(f"Không tìm thấy russell1000_*.json trong {by_year_dir}")
    return lists


def membership_year_for_dates(dates: Iterable, years: Iterable[int]) -> pd.Series:
    """
    Với mỗi ngày d, trả về năm Y của list đang có hiệu lực (recon(Y) < d), NaN nếu chưa có list.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(list(dates)))
    years = sorted(years)
    recon = pd.DatetimeIndex([reconstitution_date(y) for y in years])
    # số list có recon(Y) < d  → vị trí list đang hiệu lực
    # (so sánh trực tiếp DatetimeIndex, tránh lệch đơn vị ns/us của asi8 giữa các bản pandas)
    pos = recon.searchsorted(idx, side="left") - 1
    eff = np.where(pos >= 0, np.array(years)[np.clip(pos, 0, None)], np.nan)
    return pd.Series(eff, index=idx, name="membership_year")


def build_pit_mask(
    dates: Iterable,
    tickers: Iterable[str],
    pit_lists: Optional[Dict[int, Set[str]]] = None,
    by_year_dir: str = BY_YEAR_DIR,
) -> pd.DataFrame:
    """
    Tạo mask bool Date×Ticker: True nếu ticker thuộc list Russell 1000 đang có hiệu lực tại ngày đó.
    """
    if pit_lists is None:
        pit_lists = load_pit_lists(by_year_dir)
    idx = pd.DatetimeIndex(pd.to_datetime(list(dates)))
    cols = pd.Index(list(tickers))
    eff_year = membership_year_for_dates(idx, pit_lists.keys())

    mask = np.zeros((len(idx), len(cols)), dtype=bool)
    upper_cols = cols.astype(str).str.upper()
    for y, members in pit_lists.items():
        rows = (eff_year.values == y)
        if rows.any():
            mask[np.ix_(rows, upper_cols.isin(members))] = True
    return pd.DataFrame(mask, index=idx, columns=cols)


def mask_coverage_report(mask: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    """
    Thống kê theo (năm, nửa năm): số member trung bình mỗi ngày và % member có giá close.
    Dùng để phát hiện thiếu dữ liệu: mã bị loại ở recon năm Y vẫn là member trong
    H1 năm Y nhưng có thể không được export giá cho khoảng thời gian đó.
    """
    close = close.reindex(index=mask.index, columns=mask.columns)
    n_members = mask.sum(axis=1)
    n_with_price = (mask & close.notna()).sum(axis=1)
    df = pd.DataFrame({"members": n_members, "with_price": n_with_price})
    df = df[df["members"] > 0]
    df["year"] = df.index.year
    df["half"] = np.where(df.index.month <= 6, "H1", "H2")
    out = df.groupby(["year", "half"]).agg(
        avg_members=("members", "mean"),
        avg_with_price=("with_price", "mean"),
    )
    out["coverage_pct"] = 100 * out["avg_with_price"] / out["avg_members"]
    return out.round(1)
