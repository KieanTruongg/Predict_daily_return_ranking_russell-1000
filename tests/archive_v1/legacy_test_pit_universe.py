"""Unit tests cho PIT membership mask (src/data/pit_universe.py)."""
import io
import os

import numpy as np
import pandas as pd

from src.data.pit_universe import (
    build_pit_mask,
    load_pit_lists,
    membership_year_for_dates,
    reconstitution_date,
)
from src.features.feature_engineer import FeatureEngineer

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BY_YEAR_DIR = os.path.join(BASE, "data", "raw", "universe", "by_year")
IWB_CSV = os.path.join(BASE, "data", "raw", "etf", "iwb_holdings_2026-09-30.csv")


def test_reconstitution_date_is_last_friday_of_june():
    assert reconstitution_date(2000) == pd.Timestamp("2000-06-30")
    assert reconstitution_date(2024) == pd.Timestamp("2024-06-28")
    assert reconstitution_date(2025) == pd.Timestamp("2025-06-27")
    assert reconstitution_date(2026) == pd.Timestamp("2026-06-26")
    for y in range(2000, 2027):
        d = reconstitution_date(y)
        assert d.weekday() == 4 and d.month == 6 and d.day >= 24


def test_mask_switches_after_reconstitution():
    lists = {2020: {"A", "B"}, 2021: {"B", "C"}}
    dates = pd.to_datetime(["2020-03-02", "2020-06-26", "2020-06-29",
                            "2021-06-25", "2021-06-28"])
    m = build_pit_mask(dates, ["A", "B", "C"], pit_lists=lists)
    # Trước recon 2020 (26/6/2020): chưa có list hợp lệ
    assert not m.loc["2020-03-02"].any()
    assert not m.loc["2020-06-26"].any()
    # Sau recon 2020 → list 2020
    assert m.loc["2020-06-29"].tolist() == [True, True, False]
    # Ngày recon 2021 (25/6/2021) vẫn dùng list 2020
    assert m.loc["2021-06-25"].tolist() == [True, True, False]
    # Phiên kế tiếp → list 2021
    assert m.loc["2021-06-28"].tolist() == [False, True, True]


def test_no_look_ahead_on_real_lists():
    lists = load_pit_lists(BY_YEAR_DIR)
    dates = pd.bdate_range("2000-01-03", "2026-09-30")
    eff = membership_year_for_dates(dates, lists.keys()).dropna()
    recon = pd.DatetimeIndex([reconstitution_date(int(y)) for y in eff.values])
    # List đang dùng luôn có recon trước ngày đó (đã được công bố & có hiệu lực)
    assert (recon < eff.index).all()
    # Nửa đầu năm Y (sau năm đầu tiên) phải dùng list Y-1, không phải list Y
    jan = eff[(eff.index.month == 1) & (eff.index.year > 2000)]
    assert (jan.values == jan.index.year - 1).all()


def test_feature_engineer_respects_mask():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2021-01-04", periods=300)
    tickers = ["A", "B", "C", "D"]
    close = pd.DataFrame(100 * np.exp(rng.normal(0, 0.01, (300, 4)).cumsum(0)),
                         index=dates, columns=tickers)
    fwd = close.shift(-1) / close - 1
    mask = pd.DataFrame(True, index=dates, columns=tickers)
    mask["D"] = False                      # D không thuộc universe
    fe = FeatureEngineer(min_valid_days=20)
    feats = fe.build_feature_matrix(close, close * 1.01, close * 0.99,
                                    close * 0 + 1e6, fwd, universe_mask=mask)
    tr = feats["target_return_rank"]
    assert tr["D"].isna().all()
    assert feats["ret_5d"]["D"].isna().all()
    # Rank chỉ trong 3 member → giá trị thuộc {1/3, 2/3, 1}
    vals = set(np.round(tr[["A", "B", "C"]].dropna().values.ravel(), 6))
    assert vals <= {round(1 / 3, 6), round(2 / 3, 6), 1.0}


def test_2026_list_overlaps_iwb_holdings():
    if not os.path.exists(IWB_CSV):
        print("  (skip) missing IWB snapshot")
        return
    with open(IWB_CSV, encoding="utf-8") as f:
        lines = f.read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Ticker,"))
    iwb = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    iwb = iwb[iwb["Asset Class"].str.strip().str.lower() == "equity"]
    iwb_set = {str(t).strip().upper().replace(" ", "-").replace(".", "-") for t in iwb["Ticker"]}
    pit_2026 = {t.replace(".", "-") for t in load_pit_lists(BY_YEAR_DIR)[2026]}
    overlap = len(pit_2026 & iwb_set) / len(pit_2026)
    print(f"  PIT 2026 & IWB 2026-09-30 overlap: {overlap:.1%} ({len(pit_2026)} vs {len(iwb_set)} tickers)")
    assert overlap >= 0.95, f"overlap {overlap:.1%} < 95%"
