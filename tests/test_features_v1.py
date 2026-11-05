"""
tests.test_features_v1
======================
Đối chiếu số học 16 features v1 (src/features/v1.py) với giá trị tính tay hoặc
cài đặt tham chiếu độc lập (vòng lặp scalar), theo mục 7.1 của features_v1.md.
Không cần data/processed.
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.features.v1 import (
    AmihudIlliquidity, BollingerPctB, DownsideDeviation, IntradayReturn, LogDollarVolume,
    MomentumSkipMonth, OvernightReturn, ParkinsonVol, PriceReturn, RealizedVol, VolumeRatio,
    WilderRSI, features_v1,
)
from src.models.feature_sets import FEATURES_V1


def _frame(**cols):
    n = len(next(iter(cols.values())))
    return pd.DataFrame({k: np.asarray(v, dtype=float) for k, v in cols.items()},
                        index=pd.bdate_range("2010-01-04", periods=n))


def _px(prices):
    return {"adj_close": _frame(A=prices)}


def _prices_from_returns(rets, p0=100.0):
    return list(p0 * np.cumprod([1.0] + list(1.0 + np.asarray(rets))))


def test_feature_list_matches_spec():
    names = [f.name for f in features_v1()]
    assert names == FEATURES_V1 and len(set(names)) == 16


# --------------------------------------------------------------------------- momentum

def test_ret_5d_spec_example_gap_constant_and_ipo():
    out = PriceReturn(5).compute(_px([100, 101, 102, 103, 104, 105]))["A"]
    assert math.isclose(out.iloc[5], 0.05) and out.iloc[:5].isna().all()     # IPO thiếu lịch sử → NaN
    gap = PriceReturn(5).compute(_px([100, 101, np.nan, 103, 104, 105]))["A"]
    assert np.isnan(gap.iloc[5])                                             # hai đầu mút có giá vẫn NaN
    flat = PriceReturn(5).compute(_px([50.0] * 6))["A"]
    assert flat.iloc[5] == 0.0                                               # giá không đổi → 0, không NaN


def test_mom_skip_month_uses_only_measured_segment():
    f = MomentumSkipMonth(lookback=6, skip=2)                                # T-6 … T-2
    base = [100, 110, 120, 125, 130, 90, 300]
    assert math.isclose(f.compute(_px(base))["A"].iloc[6], 0.30)
    changed = base[:-2] + [1.0, 999.0]                                       # đổi P[T-1], P[T]
    assert math.isclose(f.compute(_px(changed))["A"].iloc[6], 0.30)
    hole = base.copy(); hole[2] = np.nan                                     # lỗ trong đoạn đo
    assert np.isnan(f.compute(_px(hole))["A"].iloc[6])
    # đúng 252/21 phiên của spec
    p = np.linspace(80, 140, 260); p[260 - 1 - 252] = 100.0; p[260 - 1 - 21] = 130.0
    assert math.isclose(MomentumSkipMonth().compute(_px(p))["A"].iloc[-1], 0.30)


# --------------------------------------------------------------------------- volatility

def test_realized_vol_matches_sample_std():
    rets = [0.01, -0.02, 0.015, 0.0, 0.03]
    out = RealizedVol(5).compute(_px(_prices_from_returns(rets)))["A"]
    assert math.isclose(out.iloc[-1], float(np.std(rets, ddof=1)), rel_tol=1e-9)
    assert out.iloc[:-1].isna().all()
    flat = RealizedVol(5).compute(_px([10.0] * 6))["A"]
    assert flat.iloc[-1] == 0.0


def test_downside_deviation_spec_example():
    rets = [0.02, -0.01, 0.03, -0.04]
    out = DownsideDeviation(4).compute(_px(_prices_from_returns(rets)))["A"]
    assert math.isclose(out.iloc[-1], 0.0206155, abs_tol=1e-7)
    up = DownsideDeviation(4).compute(_px(_prices_from_returns([0.01, 0.0, 0.02, 0.03])))["A"]
    assert up.iloc[-1] == 0.0


def test_parkinson_high_low_rules():
    data = {"adj_high": _frame(A=[110, 105, 120]), "adj_low": _frame(A=[100, 105, 125])}
    out = ParkinsonVol(2).compute(data)["A"]
    expected = math.sqrt((math.log(1.1) ** 2 + 0.0) / 2 / (4 * math.log(2)))
    assert math.isclose(out.iloc[1], expected, rel_tol=1e-12)               # high = low đóng góp 0
    assert np.isnan(out.iloc[2])                                             # high < low → NaN


# --------------------------------------------------------------------------- liquidity

def test_amihud_ratio_then_mean_and_zero_volume():
    data = {"adj_close": _frame(A=[100, 101, 101]), "close": _frame(A=[100, 101, 101]),
            "volume": _frame(A=[10, 1000, 500])}
    out = AmihudIlliquidity(2).compute(data)["A"]
    expected = 1e6 * (0.01 / (101 * 1000) + 0.0 / (101 * 500)) / 2
    assert math.isclose(out.iloc[2], expected, rel_tol=1e-12)
    data["volume"] = _frame(A=[10, 0, 500])
    assert np.isnan(AmihudIlliquidity(2).compute(data)["A"].iloc[2])


def test_amihud_uses_raw_dollar_volume_across_split():
    # split 2:1 giữa phiên 1 và 2: giá thô 200 → 100, adj_close liên tục
    data = {"adj_close": _frame(A=[100, 100, 100]), "close": _frame(A=[200, 200, 100]),
            "volume": _frame(A=[5, 5, 10])}
    out = AmihudIlliquidity(2).compute(data)["A"]
    assert out.iloc[2] == 0.0                                                # không có bước nhảy giả


def test_volume_ratio_and_log_dollar_volume():
    v = {"adj_volume": _frame(A=[1, 1, 3, 3])}
    assert math.isclose(VolumeRatio(2, 4).compute(v)["A"].iloc[3], 1.5)
    v0 = {"adj_volume": _frame(A=[1, 0, 3, 3])}
    assert np.isnan(VolumeRatio(2, 4).compute(v0)["A"].iloc[3])
    dv = {"close": _frame(A=[10, 20]), "volume": _frame(A=[100, 400])}
    out = LogDollarVolume(2).compute(dv)["A"].iloc[1]
    assert math.isclose(out, math.log1p((1000 + 8000) / 2))                  # log của trung bình


# --------------------------------------------------------------------------- intraday

def test_intraday_overnight_and_identity():
    o, c = [99, 101, 98], [100, 103, 97]
    data = {"adj_open": _frame(A=o), "adj_close": _frame(A=c)}
    intra = IntradayReturn().compute(data)["A"]
    over = OvernightReturn().compute(data)["A"]
    assert math.isclose(intra.iloc[1], 103 / 101 - 1) and np.isnan(over.iloc[0])
    assert math.isclose(over.iloc[1], 101 / 100 - 1)
    ret1 = PriceReturn(1).compute({"adj_close": data["adj_close"]})["A"]
    for t in (1, 2):
        assert math.isclose(1 + ret1.iloc[t], (1 + over.iloc[t]) * (1 + intra.iloc[t]), rel_tol=1e-12)
    gap = {"adj_open": _frame(A=o), "adj_close": _frame(A=[np.nan, 103, 97])}
    assert np.isnan(OvernightReturn().compute(gap)["A"].iloc[1])


# --------------------------------------------------------------------------- RSI

def _rsi_reference(prices, w=14):
    """Cài đặt scalar độc lập theo đặc tả (dùng để đối chiếu)."""
    out = [math.nan] * len(prices)
    run, gains, losses, ag, al = 0, [], [], None, None
    for t in range(1, len(prices)):
        a, b = prices[t - 1], prices[t]
        if not (np.isfinite(a) and np.isfinite(b)):
            run, gains, losses, ag, al = 0, [], [], None, None
            continue
        d = b - a
        g, l = max(d, 0.0), max(-d, 0.0)
        run += 1
        if run < w:
            gains.append(g); losses.append(l)
            continue
        if run == w:
            gains.append(g); losses.append(l)
            ag, al = sum(gains) / w, sum(losses) / w
        else:
            ag, al = ((w - 1) * ag + g) / w, ((w - 1) * al + l) / w
        if al == 0 and ag == 0:
            out[t] = 50.0
        elif al == 0:
            out[t] = 100.0
        elif ag == 0:
            out[t] = 0.0
        else:
            out[t] = 100 - 100 / (1 + ag / al)
    return out


def test_rsi_matches_reference_with_reset():
    rng = np.random.default_rng(3)
    p = list(100 * np.cumprod(1 + 0.02 * rng.normal(size=80)))
    p[40] = np.nan                                                           # gap → reset
    out = WilderRSI().compute(_px(p))["A"].to_numpy()
    ref = np.array(_rsi_reference(p))
    assert np.allclose(out, ref, equal_nan=True, atol=1e-10)
    assert np.isnan(out[41:55]).all() and np.isfinite(out[55])               # cần 14 delta sạch sau reset
    assert np.nanmin(out) >= 0 and np.nanmax(out) <= 100


def test_rsi_edge_cases():
    assert WilderRSI().compute(_px(list(range(1, 20))))["A"].iloc[-1] == 100.0
    assert WilderRSI().compute(_px(list(range(40, 21, -1))))["A"].iloc[-1] == 0.0
    assert WilderRSI().compute(_px([7.0] * 20))["A"].iloc[-1] == 50.0


# --------------------------------------------------------------------------- Bollinger

def test_bollinger_formula_flat_and_no_clip():
    p = [10.0, 12.0, 11.0, 18.0]
    out = BollingerPctB(3).compute(_px(p))["A"]
    w = np.array(p[1:]); m, s = w.mean(), w.std(ddof=0)
    assert math.isclose(out.iloc[3], (18 - (m - 2 * s)) / (4 * s), rel_tol=1e-9)
    assert out.iloc[3] > 0.5
    spike = BollingerPctB(3).compute(_px([10.0, 10.0, 10.0, 10.0]))["A"]
    assert np.isnan(spike.iloc[3])                                           # dải = 0 → NaN


# --------------------------------------------------------------------------- masks

def test_warmup_before_entry_and_output_membership():
    p = _px([100, 101, 102, 103, 104, 105, 106, 107])
    member = _frame(A=[False] * 5 + [True] * 3).astype(bool)
    quality = _frame(A=[True] * 8).astype(bool)
    out = PriceReturn(5).compute(p, bar_quality_mask=quality, membership_mask=member)["A"]
    assert out.iloc[:5].isna().all()                                         # ngoài membership
    assert math.isclose(out.iloc[5], 105 / 100 - 1)                          # dùng warm-up trước khi vào rổ

    dirty = quality.copy(); dirty.iloc[2, 0] = False                         # bar lỗi trước ngày vào rổ
    out2 = PriceReturn(5).compute(p, bar_quality_mask=dirty, membership_mask=member)["A"]
    assert np.isnan(out2.iloc[5]) and np.isnan(out2.iloc[7])
    p10 = _px(list(range(100, 110)))
    q10 = _frame(A=[True] * 10).astype(bool); q10.iloc[2, 0] = False
    rec = PriceReturn(5).compute(p10, bar_quality_mask=q10)["A"]
    assert np.isnan(rec.iloc[7]) and math.isclose(rec.iloc[8], 108 / 103 - 1)  # phục hồi khi lỗi ra khỏi cửa sổ
