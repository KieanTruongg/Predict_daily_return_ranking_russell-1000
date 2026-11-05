"""
src.models.walk_forward
=======================
Walk-forward cross-validation dùng chung cho mọi model xếp hạng (Phase 3).

Thiết kế:
  - Fold theo năm: validation = 1 năm dương lịch (mặc định 2010 … 2023, chỉ trong Development).
  - Train = `train_years` năm liền trước (rolling) hoặc từ đầu Development (expanding).
  - Embargo `embargo_days` phiên giữa train và val: nhãn tại T dùng giá T+1, nên ≥ 1 phiên
    là đủ để nhãn train không chạm kỳ val; mặc định 5 để an toàn hơn.
  - OOS (≥ oos_start_date trong configs/base_config.yaml) bị chặn bằng check_oos_access
    → OOSFreezeViolationError, giống matrix_loader.

Input là panel long (một dòng / (date, canonical_sid) có nhãn hợp lệ) do
src.models.panel.build_panel tạo từ các ma trận 2D.

Interface model (mọi model của nhóm theo đúng 2 hàm này):
    model.fit(X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> None
    model.predict(X: pd.DataFrame, dates: pd.Series) -> np.ndarray
  Tuỳ chọn: thuộc tính `input_cols` (list cột) nếu model cần cột khác feature_cols
  (vd. baseline 1 tín hiệu).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.quality.quality_window import check_oos_access
from src.utils.config import load_config


@dataclass(frozen=True)
class Fold:
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp

    def __str__(self) -> str:
        return (f"fold {self.fold_id:02d} | train {self.train_start.date()} → {self.train_end.date()}"
                f" | val {self.val_start.date()} → {self.val_end.date()}")


def make_folds(
    dates: Sequence,
    first_val_year: int = 2010,
    last_val_year: int = 2023,
    train_years: int = 5,
    expanding: bool = False,
    embargo_days: int = 5,
    oos_start: Optional[str] = None,
) -> List[Fold]:
    """
    Tạo các fold walk-forward trên lịch phiên giao dịch `dates`.
    Năm val nào chạm OOS hoặc không đủ dữ liệu train sẽ bị bỏ qua.
    """
    oos_ts = pd.Timestamp(oos_start or load_config().oos_start_date)
    cal = pd.DatetimeIndex(pd.unique(pd.DatetimeIndex(dates))).sort_values()
    cal = cal[cal < oos_ts]

    folds: List[Fold] = []
    for year in range(first_val_year, last_val_year + 1):
        if pd.Timestamp(year=year, month=12, day=31) >= oos_ts:
            break                                   # chỉ dùng năm val nằm trọn trước OOS
        val = cal[cal.year == year]
        if len(val) == 0:
            continue
        before = cal[cal < val[0]]
        if len(before) <= embargo_days:
            continue
        train_end = before[-(embargo_days + 1)]
        if expanding:
            train_start = cal[0]
        else:
            start_cands = cal[cal.year >= year - train_years]
            train_start = start_cands[0]
        if train_start > train_end:
            continue
        folds.append(Fold(len(folds), train_start, train_end, val[0], val[-1]))
    return folds


# ---------------------------------------------------------------------------
# Metrics trên panel long
# ---------------------------------------------------------------------------

def daily_rank_ic(
    df: pd.DataFrame,
    score_col: str,
    ret_col: str,
    date_col: str = "date",
    min_names: int = 10,
) -> pd.Series:
    """Spearman Rank IC theo từng ngày giữa score và lợi suất thực tế (bỏ ngày < min_names mã)."""
    d = df[[date_col, score_col, ret_col]].dropna()
    g = d.groupby(date_col)
    n = g[score_col].transform("size")
    d = d[n >= min_names]
    if d.empty:
        return pd.Series(dtype=float, name="ic")
    g = d.groupby(date_col)
    rs = g[score_col].rank()
    rr = g[ret_col].rank()
    tmp = pd.DataFrame({date_col: d[date_col].values, "a": rs.values, "b": rr.values})
    tmp["a"] -= tmp.groupby(date_col)["a"].transform("mean")
    tmp["b"] -= tmp.groupby(date_col)["b"].transform("mean")
    tmp["ab"] = tmp["a"] * tmp["b"]
    tmp["aa"] = tmp["a"] ** 2
    tmp["bb"] = tmp["b"] ** 2
    s = tmp.groupby(date_col)[["ab", "aa", "bb"]].sum()
    ic = s["ab"] / np.sqrt(s["aa"] * s["bb"])
    return ic.replace([np.inf, -np.inf], np.nan).dropna().rename("ic")


def daily_decile_spread(
    df: pd.DataFrame,
    score_col: str,
    ret_col: str,
    date_col: str = "date",
    q: float = 0.1,
    min_names: int = 10,
) -> pd.Series:
    """Lợi suất TB nhóm top q trừ nhóm bottom q theo score, mỗi ngày (chưa trừ phí)."""
    d = df[[date_col, score_col, ret_col]].dropna()
    g = d.groupby(date_col)
    n = g[score_col].transform("size")
    d = d[n >= min_names]
    if d.empty:
        return pd.Series(dtype=float, name="spread")
    pct = d.groupby(date_col)[score_col].rank(pct=True)
    top = d[pct > 1 - q].groupby(date_col)[ret_col].mean()
    bot = d[pct <= q].groupby(date_col)[ret_col].mean()
    return (top - bot).dropna().rename("spread")


def ic_summary(ic: pd.Series) -> Dict[str, float]:
    """Mean IC, độ lệch chuẩn, ICIR (daily), t-stat, tỷ lệ ngày IC > 0."""
    ic = ic.dropna()
    n = len(ic)
    mean = float(ic.mean()) if n else np.nan
    std = float(ic.std(ddof=1)) if n > 1 else np.nan
    icir = mean / std if std and std > 0 else np.nan
    return {
        "mean_ic": mean,
        "ic_std": std,
        "icir": icir,
        "ic_tstat": icir * np.sqrt(n) if n > 1 else np.nan,
        "positive_ic_ratio": float((ic > 0).mean()) if n else np.nan,
        "days_evaluated": n,
    }


def summarize_predictions(pred: pd.DataFrame, ret_col: str, score_col: str = "score") -> Dict[str, float]:
    """Gộp IC + spread top−bottom decile cho một tập dự đoán."""
    out = ic_summary(daily_rank_ic(pred, score_col, ret_col))
    spread = daily_decile_spread(pred, score_col, ret_col)
    out["spread_mean_daily"] = float(spread.mean()) if len(spread) else np.nan
    sd = spread.std(ddof=1) if len(spread) > 1 else np.nan
    out["spread_ann_sharpe"] = float(spread.mean() / sd * np.sqrt(252)) if sd and sd > 0 else np.nan
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardResult:
    model_name: str
    predictions: pd.DataFrame       # date, canonical_sid, fold, score, <eval_col>
    fold_metrics: pd.DataFrame      # 1 dòng / fold
    daily_ic: pd.Series             # IC theo ngày, toàn bộ các kỳ val

    def overall(self, ret_col: str) -> Dict[str, float]:
        out = {"model": self.model_name}
        out.update(summarize_predictions(self.predictions, ret_col))
        return out

    def ic_by_year(self) -> pd.DataFrame:
        ic = self.daily_ic
        return ic.groupby(ic.index.year).agg(mean_ic="mean", ic_std="std", days="size")


def run_walk_forward(
    df: pd.DataFrame,
    model_factory: Callable[[], object],
    feature_cols: List[str],
    folds: List[Fold],
    target_col: str = "target_next_rank",
    eval_col: str = "target_next_return",
    date_col: str = "date",
    id_col: str = "canonical_sid",
    model_name: Optional[str] = None,
    verbose: bool = True,
) -> WalkForwardResult:
    """
    Train một model MỚI cho mỗi fold trên [train_start, train_end], dự đoán [val_start, val_end].
    `target_col` là nhãn để học; `eval_col` là lợi suất thực tế để tính IC/spread.
    """
    check_oos_access(pd.DatetimeIndex(pd.unique(df[date_col])), oos_start=load_config().oos_start_date)

    dates = df[date_col]
    preds, rows = [], []
    name = model_name
    for f in folds:
        t0 = time.time()
        tr = df[(dates >= f.train_start) & (dates <= f.train_end) & df[target_col].notna()]
        va = df[(dates >= f.val_start) & (dates <= f.val_end)]
        if tr.empty or va.empty:
            continue

        model = model_factory()
        name = name or getattr(model, "name", type(model).__name__)
        cols = list(getattr(model, "input_cols", None) or feature_cols)
        model.fit(tr[cols], tr[target_col], tr[date_col])
        score = np.asarray(model.predict(va[cols], va[date_col]), dtype=float)

        p = va[[date_col, id_col, eval_col]].copy()
        p["fold"] = f.fold_id
        p["score"] = score
        preds.append(p)

        m = summarize_predictions(p, eval_col)
        m.update(fold=f.fold_id, val_year=f.val_start.year, train_start=f.train_start.date(),
                 train_end=f.train_end.date(), n_train=len(tr), n_val=len(va))
        rows.append(m)
        if verbose:
            print(f"  [{name}] {f} | IC={m['mean_ic']:+.4f} ICIR={m['icir']:+.3f} "
                  f"spread={m['spread_mean_daily'] * 1e4:+.1f}bps ({time.time() - t0:.1f}s)")

    pred = (pd.concat(preds, ignore_index=True) if preds
            else pd.DataFrame(columns=[date_col, id_col, eval_col, "fold", "score"]))
    lead = ["fold", "val_year", "train_start", "train_end", "n_train", "n_val"]
    fm = pd.DataFrame(rows)
    if not fm.empty:
        fm = fm[lead + [c for c in fm.columns if c not in lead]]
    daily = daily_rank_ic(pred, "score", eval_col, date_col) if len(pred) else pd.Series(dtype=float)
    return WalkForwardResult(name or "model", pred, fm, daily)
