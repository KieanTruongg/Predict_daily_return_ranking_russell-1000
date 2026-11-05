"""
tests.test_walk_forward
=======================
Walk-forward CV, panel builder và baselines (src/models/) trên ma trận tổng hợp —
không cần data/processed/matrices.
"""

import numpy as np
import pandas as pd
import pytest

from src.models.baselines import ICSignEqualWeightModel, RidgeModel, SingleFactorModel
from src.models.feature_sets import reversal_5d
from src.models.panel import build_panel, target_next_rank
from src.models.walk_forward import daily_rank_ic, make_folds, run_walk_forward
from src.quality.quality_window import OOSFreezeViolationError


def _synthetic_matrices(n_days=1500, n_sids=60, seed=0, start="2005-01-03"):
    """Ma trận ngày × SID: 'good' dự báo được lợi suất T+1, 'noise' thì không."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n_days)
    sids = pd.Index([f"S{i:03d} X{i}" for i in range(n_sids)], name="canonical_sid")
    shape = (n_days, n_sids)
    good = pd.DataFrame(rng.normal(size=shape), index=dates, columns=sids)
    noise = pd.DataFrame(rng.normal(size=shape), index=dates, columns=sids)
    ret = pd.DataFrame(0.01 * (0.3 * good.to_numpy() + rng.normal(size=shape)), index=dates, columns=sids)
    universe = pd.DataFrame(rng.random(shape) > 0.1, index=dates, columns=sids)
    label = universe & ret.notna()
    return {"good": good, "noise": noise}, ret.where(label), label, universe


def test_make_folds_no_overlap_and_embargo():
    dates = pd.bdate_range("2005-01-03", "2023-12-29")
    folds = make_folds(dates, first_val_year=2010, last_val_year=2023, train_years=5, embargo_days=5)
    assert [f.val_start.year for f in folds] == list(range(2010, 2024))
    for f in folds:
        assert f.val_start.year == f.val_end.year
        assert f.train_end < f.val_start
        gap = len(dates[(dates > f.train_end) & (dates < f.val_start)])
        assert gap == 5                                   # đúng 5 phiên embargo
        assert f.train_start.year == f.val_start.year - 5  # rolling 5 năm
    exp = make_folds(dates, 2010, 2012, expanding=True)
    assert all(f.train_start == dates[0] for f in exp)


def test_make_folds_excludes_out_of_sample():
    dates = pd.bdate_range("2018-01-01", "2026-06-30")
    folds = make_folds(dates, 2020, 2026, train_years=2)
    assert max(f.val_end for f in folds) < pd.Timestamp("2024-01-02")
    assert [f.val_start.year for f in folds] == [2020, 2021, 2022, 2023]


def test_target_next_rank_spec_example():
    """Ví dụ mục 5 target_and_timing_v1: A=-2%, B=1%, C=3% → 0, 0.5, 1; ngoài mask → NaN."""
    d = pd.DatetimeIndex(["2010-01-04", "2010-01-05"])
    ret = pd.DataFrame({"A": [-0.02, 0.01], "B": [0.01, np.nan], "C": [0.03, 0.02], "D": [0.5, 0.0]}, index=d)
    label = pd.DataFrame({"A": [True, True], "B": [True, False], "C": [True, True], "D": [False, False]}, index=d)
    r = target_next_rank(ret, label)
    assert r.loc["2010-01-04", ["A", "B", "C"]].tolist() == [0.0, 0.5, 1.0]
    assert np.isnan(r.loc["2010-01-04", "D"])                       # ngoài tập nhãn
    assert r.loc["2010-01-05", ["A", "C"]].tolist() == [0.0, 1.0]   # N = 2


def test_build_panel_ranks_features_on_universe_not_label_mask():
    d = pd.DatetimeIndex(["2010-01-04"])
    feat = pd.DataFrame({"A": [1.0], "B": [2.0], "C": [3.0]}, index=d)
    ret = pd.DataFrame({"A": [0.01], "B": [0.02], "C": [np.nan]}, index=d)
    universe = pd.DataFrame({"A": [True], "B": [True], "C": [True]}, index=d)
    label = pd.DataFrame({"A": [True], "B": [True], "C": [False]}, index=d)
    panel, cols = build_panel({"f": feat}, ret, label, universe)
    assert cols == ["f"]
    assert panel["canonical_sid"].tolist() == ["A", "B"]          # chỉ dòng có nhãn
    # C không có nhãn nhưng vẫn thuộc tập dự đoán tại T → vẫn tham gia rank feature
    assert np.allclose(panel["f"].to_numpy(), [-0.5, 0.0])
    assert np.allclose(panel["target_next_rank"].to_numpy(), [0.0, 1.0])


def test_daily_rank_ic_matches_spearman():
    feats, ret, label, universe = _synthetic_matrices(n_days=30)
    panel, _ = build_panel(feats, ret, label, universe, rank_features=False)
    ic = daily_rank_ic(panel, "good", "target_next_return")
    ref = panel.groupby("date").apply(
        lambda g: g["good"].corr(g["target_next_return"], method="spearman"), include_groups=False)
    assert np.allclose(ic.sort_index().to_numpy(), ref.sort_index().to_numpy(), atol=1e-10)


def test_reversal_5d_uses_t5_and_t1_and_needs_clean_window():
    d = pd.bdate_range("2010-01-04", periods=8)
    p = pd.DataFrame({"A": [100, 101, 102, 103, 104, 80, 200, 300.0]}, index=d)
    r = reversal_5d(p)
    assert np.isclose(r["A"].iloc[6], 101 / 80 - 1)       # P[t-5]=101, P[t-1]=80; P[t] không dùng
    q = pd.DataFrame({"A": [True] * 8}, index=d)
    q.iloc[3, 0] = False                                    # bar lỗi trong cửa sổ
    assert np.isnan(reversal_5d(p, q)["A"].iloc[6])


class _SpyModel(RidgeModel):
    """Ghi lại ngày train lớn nhất để kiểm tra không train trên dữ liệu val."""
    seen = []

    def fit(self, X, y, dates):
        _SpyModel.seen.append(pd.Timestamp(dates.max()))
        super().fit(X, y, dates)


def test_walk_forward_learns_signal_without_leakage():
    feats, ret, label, universe = _synthetic_matrices()
    feats["neg_good"] = -feats["good"]
    panel, cols = build_panel(feats, ret, label, universe)
    folds = make_folds(panel["date"], 2007, 2009, train_years=2)
    _SpyModel.seen = []
    res = run_walk_forward(panel, _SpyModel, ["good", "noise"], folds, model_name="spy", verbose=False)

    for f, max_train in zip(folds, _SpyModel.seen):
        assert max_train < f.val_start
    val_dates = set().union(*[set(pd.bdate_range(f.val_start, f.val_end)) for f in folds])
    assert set(res.predictions["date"]).issubset(val_dates)
    assert res.overall("target_next_return")["mean_ic"] > 0.15
    assert res.fold_metrics["mean_ic"].min() > 0.1

    noise = run_walk_forward(panel, lambda: SingleFactorModel("noise"), cols, folds, verbose=False)
    assert abs(noise.overall("target_next_return")["mean_ic"]) < 0.03

    # dấu học từ train: neg_good phải bị lật dấu → IC dương
    ew = run_walk_forward(panel, ICSignEqualWeightModel, ["neg_good", "noise"], folds, verbose=False)
    assert ew.overall("target_next_return")["mean_ic"] > 0.05


def test_run_walk_forward_rejects_oos_dates():
    feats, ret, label, universe = _synthetic_matrices(n_days=20, start="2023-12-20")
    panel, cols = build_panel(feats, ret, label, universe)
    with pytest.raises(OOSFreezeViolationError):
        run_walk_forward(panel, ICSignEqualWeightModel, cols, [], verbose=False)
