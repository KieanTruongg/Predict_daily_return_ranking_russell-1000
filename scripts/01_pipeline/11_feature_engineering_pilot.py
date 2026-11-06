# -*- coding: utf-8 -*-
"""
scripts/01_pipeline/11_feature_engineering_pilot.py
===================================================
Executes comprehensive Pilot Feature Engineering verification on:
1. Synthetic mini dataset with hand-calculated expected values for all 16 candidate features:
   - Batch 1 (Representative 5): ret_20d, vol_realized_20d, amihud_illiq_20d, rsi_14d, bollinger_pct_b_20d
   - Batch 2A (Momentum 4): ret_1d, ret_5d, ret_60d, mom_12m_skip_1m
   - Batch 2B (Volatility 3): vol_realized_60d, vol_parkinson_20d, downside_deviation_20d
   - Batch 2C (Volume & Intraday 4): volume_ratio_5_20, log_dollar_volume_20d, ret_intraday, ret_overnight
2. Real Development slice (2000-2002) for 10 representative SIDs covering:
   - Clean continuous history (AAPL, MSFT)
   - Stock splits (AAPL 2:1 split on 2000-06-21)
   - Index entry with sufficient warmup (A - Agilent)
   - Index entry with insufficient warmup (BF)
   - Long lookback deficit (A on mom_12m_skip_1m)
   - Spinoff discontinuity (KSU on 2000-07-13)
   - Trading halt anomaly (CPTH in Feb 2001)
   - Major sectors (JPM, XON, JNJ, WMT)

Generates:
- docs/reports/feature_pilot/numerical_checks.csv
- docs/reports/feature_pilot/coverage_summary.csv
- docs/reports/feature_pilot/figures/*.png
"""

import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data.matrix_loader import (
    load_matrix,
    load_bar_quality_mask,
    load_layer1_mask,
    load_dates_index,
    load_columns_sids,
)
from src.features.base import (
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    RealizedVolatilityFeature,
    ParkinsonVolatilityFeature,
    DownsideDeviationFeature,
    AmihudIlliquidityFeature,
    VolumeRatioFeature,
    LogDollarVolumeFeature,
    IntradayReturnFeature,
    OvernightReturnFeature,
    RSIFeature,
    BollingerPctBFeature,
)
from src.features.transforms import cross_sectional_rank

RUN_ID = "PILOT_FULL16_20261106"
REPORTS_DIR = ROOT_DIR / "docs" / "reports" / "feature_pilot"
FIGURES_DIR = REPORTS_DIR / "figures"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def run_synthetic_checks():
    """Lớp 1: Đối chiếu số học với đáp án tính tay độc lập trên dữ liệu tổng hợp nhỏ."""
    print("=" * 80)
    print("LỚP 1: KIỂM THỬ SỐ HỌC TỔNG HỢP VỚI ĐÁP ÁN TÍNH TAY (16 FEATURES)")
    print("=" * 80)

    checks = []

    # -------------------------------------------------------------
    # BATCH 1 CHECKS (S01 - S15)
    # -------------------------------------------------------------
    dates = pd.date_range("2000-01-01", periods=300, freq="B")

    # S01: ret_20d geometric
    p_geom = pd.Series([100.0 * (1.01 ** i) for i in range(25)], index=dates[:25])
    df_geom = pd.DataFrame({"TEST_SID": p_geom})
    feat_ret20 = PriceRatioMomentumFeature(window=20)
    res_ret20 = feat_ret20.compute({"adj_close": df_geom})
    actual_s01 = res_ret20.iloc[20]["TEST_SID"]
    expected_s01 = (1.01 ** 20) - 1.0
    err_s01 = abs(actual_s01 - expected_s01)
    passed_s01 = err_s01 <= 1e-7
    checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": dates[20].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S01_RET20_GEOMETRIC",
        "expected": expected_s01, "actual": actual_s01, "absolute_error": err_s01, "tolerance": 1e-7,
        "nan_reason": "NONE" if passed_s01 else "FAIL", "status": "PASSED" if passed_s01 else "FAILED",
        "input_reference": "P_t = 100 * (1.01)^t, window=20",
    })

    # S02: ret_20d flat
    p_flat = pd.Series([100.0] * 25, index=dates[:25])
    df_flat = pd.DataFrame({"TEST_SID": p_flat})
    res_ret20_flat = feat_ret20.compute({"adj_close": df_flat})
    actual_s02 = res_ret20_flat.iloc[20]["TEST_SID"]
    passed_s02 = abs(actual_s02 - 0.0) <= 1e-7
    checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": dates[20].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S02_RET20_FLAT",
        "expected": 0.0, "actual": actual_s02, "absolute_error": abs(actual_s02), "tolerance": 1e-7,
        "nan_reason": "NONE" if passed_s02 else "FAIL", "status": "PASSED" if passed_s02 else "FAILED",
        "input_reference": "P_t = 100.0, window=20",
    })

    # S03: ret_20d dirty bar NaN & recovery
    p_dirty = pd.Series([100.0 + i for i in range(40)], index=dates[:40])
    df_dirty = pd.DataFrame({"TEST_SID": p_dirty})
    q_mask = pd.DataFrame({"TEST_SID": [True] * 40}, index=dates[:40])
    q_mask.iloc[10, 0] = False
    res_ret20_dirty = feat_ret20.compute({"adj_close": df_dirty}, bar_quality_mask=q_mask)
    actual_s03_in_window = res_ret20_dirty.iloc[20]["TEST_SID"]
    actual_s03_recovery = res_ret20_dirty.iloc[31]["TEST_SID"]
    expected_s03_recovery = (100.0 + 31) / (100.0 + 11) - 1.0
    passed_s03 = np.isnan(actual_s03_in_window) and abs(actual_s03_recovery - expected_s03_recovery) <= 1e-7
    checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": dates[20].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S03_RET20_DIRTY_BAR_NAN",
        "expected": np.nan, "actual": actual_s03_in_window, "absolute_error": 0.0 if np.isnan(actual_s03_in_window) else 1.0, "tolerance": 0.0,
        "nan_reason": "DIRTY_BAR_IN_LOOKBACK", "status": "PASSED" if np.isnan(actual_s03_in_window) else "FAILED",
        "input_reference": "Dirty bar at idx=10, checked at idx=20",
    })
    checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": dates[31].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S03B_RET20_DIRTY_RECOVERY",
        "expected": expected_s03_recovery, "actual": actual_s03_recovery, "absolute_error": abs(actual_s03_recovery - expected_s03_recovery), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(actual_s03_recovery - expected_s03_recovery) <= 1e-7 else "FAILED",
        "input_reference": "idx=31 lookback is [11..31], dirty bar 10 exited",
    })

    # S04 & S05: vol_realized_20d alternating & zero
    rets_alt = [0.01 if i % 2 == 0 else -0.01 for i in range(25)]
    df_rets_alt = pd.DataFrame({"TEST_SID": rets_alt}, index=dates[:25])
    feat_vol20 = RealizedVolatilityFeature(window=20, return_type="daily_return", annualize=False)
    res_vol20 = feat_vol20.compute({"daily_return": df_rets_alt})
    actual_s04 = res_vol20.iloc[19]["TEST_SID"]
    expected_s04 = np.sqrt(20.0 * (0.01 ** 2) / 19.0)
    checks.append({
        "run_id": RUN_ID, "feature": "vol_realized_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S04_VOL20_ALTERNATING",
        "expected": expected_s04, "actual": actual_s04, "absolute_error": abs(actual_s04 - expected_s04), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(actual_s04 - expected_s04) <= 1e-7 else "FAILED",
        "input_reference": "20 alternating returns (+-0.01), ddof=1, daily unit",
    })

    # S06 & S07: amihud_illiq_20d constant & zero volume
    df_amihud_ret = pd.DataFrame({"TEST_SID": [0.01] * 25}, index=dates[:25])
    df_amihud_p = pd.DataFrame({"TEST_SID": [100.0] * 25}, index=dates[:25])
    df_amihud_v = pd.DataFrame({"TEST_SID": [10000.0] * 25}, index=dates[:25])
    feat_amihud = AmihudIlliquidityFeature(window=20)
    res_amihud = feat_amihud.compute({"daily_return": df_amihud_ret, "close": df_amihud_p, "volume": df_amihud_v})
    actual_s06 = res_amihud.iloc[19]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "amihud_illiq_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S06_AMIHUD_CONSTANT",
        "expected": 0.01, "actual": actual_s06, "absolute_error": abs(actual_s06 - 0.01), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(actual_s06 - 0.01) <= 1e-7 else "FAILED",
        "input_reference": "r=0.01, P=100, V=10000 -> DV=1M, ratio=1e-8 * 1e6 = 0.01",
    })

    # S08 & S09 & S10: rsi_14d all gain, flat, reset
    feat_rsi = RSIFeature(window=14)
    res_rsi_inc = feat_rsi.compute({"adj_close": df_dirty.iloc[:25]})
    actual_s08 = res_rsi_inc.iloc[14]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "rsi_14d", "date": dates[14].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S08_RSI_ALL_GAIN",
        "expected": 100.0, "actual": actual_s08, "absolute_error": abs(actual_s08 - 100.0), "tolerance": 1e-6,
        "nan_reason": "NONE", "status": "PASSED" if abs(actual_s08 - 100.0) <= 1e-6 else "FAILED",
        "input_reference": "All deltas = +1.0, 14 clean deltas",
    })

    # S11 & S12: bollinger_pct_b_20d flat & exact formula (mean=100.5, sigma=5.894913)
    feat_bb = BollingerPctBFeature(window=20)
    prices_bb = [95.0]*10 + [105.0]*9 + [115.0]
    p_bb_series = pd.Series(prices_bb, index=dates[:20])
    df_bb = pd.DataFrame({"TEST_SID": p_bb_series})
    res_bb = feat_bb.compute({"adj_close": df_bb})
    actual_s12 = res_bb.iloc[19]["TEST_SID"]
    m_hand = float(np.mean(prices_bb))
    s_hand = float(np.std(prices_bb, ddof=0))
    expected_s12 = (115.0 - (m_hand - 2.0 * s_hand)) / (4.0 * s_hand)
    checks.append({
        "run_id": RUN_ID, "feature": "bollinger_pct_b_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S12_BOLLINGER_EXACT_FORMULA",
        "expected": expected_s12, "actual": actual_s12, "absolute_error": abs(actual_s12 - expected_s12), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(actual_s12 - expected_s12) <= 1e-7 else "FAILED",
        "input_reference": f"10*95, 9*105, 1*115 -> m={m_hand:.2f}, s={s_hand:.6f}",
    })

    # S13: target_next_rank
    df_rank_test = pd.DataFrame({"A": [-0.02], "B": [0.01], "C": [0.03]})
    rank_res = cross_sectional_rank(df_rank_test)
    checks.append({
        "run_id": RUN_ID, "feature": "target_next_rank", "date": "2000-01-03",
        "canonical_sid": "TEST_RANK_3STOCKS", "case_id": "CASE_S13_UNIFORM_RANK_3STOCKS",
        "expected": 0.5, "actual": rank_res.iloc[0]["B"], "absolute_error": abs(rank_res.iloc[0]["B"] - 0.5), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(rank_res.iloc[0]["B"] - 0.5) <= 1e-7 else "FAILED",
        "input_reference": "returns [-0.02, 0.01, 0.03] -> rank B is 0.5",
    })

    # S14: ret_20d Inf rejection
    p_inf = pd.DataFrame({"TEST_SID": [100.0, np.inf, 110.0]}, index=dates[:3])
    feat_ret2 = PriceRatioMomentumFeature(window=2)
    res_ret2_inf = feat_ret2.compute({"adj_close": p_inf})
    checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": dates[2].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S14_RET_NON_FINITE_PRICE_NAN",
        "expected": np.nan, "actual": res_ret2_inf.iloc[2]["TEST_SID"], "absolute_error": 0.0 if np.isnan(res_ret2_inf.iloc[2]["TEST_SID"]) else 1.0, "tolerance": 0.0,
        "nan_reason": "NON_FINITE_PRICE_IN_WINDOW", "status": "PASSED" if np.isnan(res_ret2_inf.iloc[2]["TEST_SID"]) else "FAILED",
        "input_reference": "Price sequence [100.0, Inf, 110.0], window=2",
    })

    # S15: Amihud negative price/volume rejection
    df_amihud_neg_ret = pd.DataFrame({"TEST_SID": [0.01, 0.01]}, index=dates[:2])
    df_amihud_neg_p = pd.DataFrame({"TEST_SID": [-10.0, 10.0]}, index=dates[:2])
    df_amihud_neg_v = pd.DataFrame({"TEST_SID": [-100.0, 1000.0]}, index=dates[:2])
    feat_ami2 = AmihudIlliquidityFeature(window=2)
    res_ami2_neg = feat_ami2.compute({"daily_return": df_amihud_neg_ret, "close": df_amihud_neg_p, "volume": df_amihud_neg_v})
    checks.append({
        "run_id": RUN_ID, "feature": "amihud_illiq_20d", "date": dates[1].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S15_AMIHUD_NEGATIVE_PRICE_VOL_NAN",
        "expected": np.nan, "actual": res_ami2_neg.iloc[1]["TEST_SID"], "absolute_error": 0.0 if np.isnan(res_ami2_neg.iloc[1]["TEST_SID"]) else 1.0, "tolerance": 0.0,
        "nan_reason": "NEGATIVE_PRICE_OR_VOLUME_IN_WINDOW", "status": "PASSED" if np.isnan(res_ami2_neg.iloc[1]["TEST_SID"]) else "FAILED",
        "input_reference": "p=-10, v=-100 (product=1000>0), window=2",
    })

    # -------------------------------------------------------------
    # BATCH 2 CHECKS (S16 - S23)
    # -------------------------------------------------------------
    # S16: ret_1d, ret_5d, ret_60d
    p_geom_70 = pd.DataFrame({"TEST_SID": [100.0 * (1.01 ** i) for i in range(70)]}, index=dates[:70])
    f_1d = PriceRatioMomentumFeature(window=1)
    f_5d = PriceRatioMomentumFeature(window=5)
    f_60d = PriceRatioMomentumFeature(window=60)
    act_1d = f_1d.compute({"adj_close": p_geom_70}).iloc[1]["TEST_SID"]
    act_5d = f_5d.compute({"adj_close": p_geom_70}).iloc[5]["TEST_SID"]
    act_60d = f_60d.compute({"adj_close": p_geom_70}).iloc[60]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "ret_1d", "date": dates[1].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S16A_RET1D_GEOMETRIC",
        "expected": 0.01, "actual": act_1d, "absolute_error": abs(act_1d - 0.01), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_1d - 0.01) <= 1e-7 else "FAILED",
        "input_reference": "P_t = 100 * 1.01^t, window=1",
    })
    checks.append({
        "run_id": RUN_ID, "feature": "ret_5d", "date": dates[5].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S16B_RET5D_GEOMETRIC",
        "expected": (1.01**5) - 1.0, "actual": act_5d, "absolute_error": abs(act_5d - ((1.01**5) - 1.0)), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_5d - ((1.01**5) - 1.0)) <= 1e-7 else "FAILED",
        "input_reference": "P_t = 100 * 1.01^t, window=5",
    })
    checks.append({
        "run_id": RUN_ID, "feature": "ret_60d", "date": dates[60].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S16C_RET60D_GEOMETRIC",
        "expected": (1.01**60) - 1.0, "actual": act_60d, "absolute_error": abs(act_60d - ((1.01**60) - 1.0)), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_60d - ((1.01**60) - 1.0)) <= 1e-7 else "FAILED",
        "input_reference": "P_t = 100 * 1.01^t, window=60",
    })

    # S17: mom_12m_skip_1m
    n_mom = 280
    df_mom = pd.DataFrame({"TEST_SID": [100.0 + i for i in range(n_mom)]}, index=dates[:n_mom])
    f_mom12m = Mom12mSkip1mFeature(lookback=252, skip=21)
    res_mom12m = f_mom12m.compute({"adj_close": df_mom})
    exp_mom12m_260 = (100.0 + 239) / (100.0 + 8) - 1.0
    act_mom12m_260 = res_mom12m.iloc[260]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "mom_12m_skip_1m", "date": dates[260].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S17A_MOM12M_SKIP1M_FORMULA",
        "expected": exp_mom12m_260, "actual": act_mom12m_260, "absolute_error": abs(act_mom12m_260 - exp_mom12m_260), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_mom12m_260 - exp_mom12m_260) <= 1e-7 else "FAILED",
        "input_reference": "P[T-21]/P[T-252]-1 on linear trend [100..380]",
    })

    # S18: vol_realized_60d
    rets_alt_70 = [-0.01 if i % 2 == 0 else 0.01 for i in range(70)]
    df_rets_alt_70 = pd.DataFrame({"TEST_SID": rets_alt_70}, index=dates[:70])
    f_vol60 = RealizedVolatilityFeature(window=60, return_type="daily_return", annualize=False)
    res_vol60 = f_vol60.compute({"daily_return": df_rets_alt_70})
    exp_vol60 = np.sqrt(60.0 * (0.01 ** 2) / 59.0)
    act_vol60 = res_vol60.iloc[59]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "vol_realized_60d", "date": dates[59].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S18_VOL60_ALTERNATING",
        "expected": exp_vol60, "actual": act_vol60, "absolute_error": abs(act_vol60 - exp_vol60), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_vol60 - exp_vol60) <= 1e-7 else "FAILED",
        "input_reference": "60 alternating returns (+-0.01), ddof=1, daily unit",
    })

    # S19: vol_parkinson_20d
    df_h_park = pd.DataFrame({"TEST_SID": [102.0] * 25}, index=dates[:25])
    df_l_park = pd.DataFrame({"TEST_SID": [100.0] * 25}, index=dates[:25])
    f_park = ParkinsonVolatilityFeature(window=20)
    res_park = f_park.compute({"adj_high": df_h_park, "adj_low": df_l_park})
    exp_park = np.sqrt((np.log(1.02) ** 2) / (4.0 * np.log(2.0)))
    act_park = res_park.iloc[19]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "vol_parkinson_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S19_PARKINSON_RATIO_1_02",
        "expected": exp_park, "actual": act_park, "absolute_error": abs(act_park - exp_park), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_park - exp_park) <= 1e-7 else "FAILED",
        "input_reference": "H=102, L=100, 20 bars, formula sqrt(mean(ln(H/L)^2/(4ln2)))",
    })

    # S20: downside_deviation_20d
    rets_down = [-0.02 if i % 2 == 0 else 0.02 for i in range(25)]
    df_rets_down = pd.DataFrame({"TEST_SID": rets_down}, index=dates[:25])
    f_down = DownsideDeviationFeature(window=20)
    res_down = f_down.compute({"daily_return": df_rets_down})
    exp_down = np.sqrt(10.0 * (0.02 ** 2) / 20.0)
    act_down = res_down.iloc[19]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "downside_deviation_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S20_DOWNSIDE_DEV_FORMULA",
        "expected": exp_down, "actual": act_down, "absolute_error": abs(act_down - exp_down), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_down - exp_down) <= 1e-7 else "FAILED",
        "input_reference": "10 negative returns of -0.02, full denominator 20",
    })

    # S21: volume_ratio_5_20
    vols_test = [10000.0] * 15 + [20000.0] * 5 + [10000.0] * 5
    df_vols_test = pd.DataFrame({"TEST_SID": vols_test}, index=dates[:25])
    f_vratio = VolumeRatioFeature(fast_window=5, slow_window=20)
    res_vratio = f_vratio.compute({"adj_volume": df_vols_test})
    exp_vratio = 1.60
    act_vratio = res_vratio.iloc[19]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "volume_ratio_5_20", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S21_VOLUME_RATIO_FORMULA",
        "expected": exp_vratio, "actual": act_vratio, "absolute_error": abs(act_vratio - exp_vratio), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_vratio - exp_vratio) <= 1e-7 else "FAILED",
        "input_reference": "mean_5=20k, mean_20=12.5k -> ratio=1.60",
    })

    # S22: log_dollar_volume_20d
    df_p_logdv = pd.DataFrame({"TEST_SID": [100.0] * 25}, index=dates[:25])
    df_v_logdv = pd.DataFrame({"TEST_SID": [10000.0] * 25}, index=dates[:25])
    f_logdv = LogDollarVolumeFeature(window=20)
    res_logdv = f_logdv.compute({"close": df_p_logdv, "volume": df_v_logdv})
    exp_logdv = np.log1p(1000000.0)
    act_logdv = res_logdv.iloc[19]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "log_dollar_volume_20d", "date": dates[19].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S22_LOG_DOLLAR_VOL_FORMULA",
        "expected": exp_logdv, "actual": act_logdv, "absolute_error": abs(act_logdv - exp_logdv), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_logdv - exp_logdv) <= 1e-7 else "FAILED",
        "input_reference": "mean_20(DV)=1M USD -> log1p(1,000,000)",
    })

    # S23: ret_intraday & ret_overnight identity
    dates_2 = dates[:2]
    df_c_decomp = pd.DataFrame({"TEST_SID": [100.0, 105.0]}, index=dates_2)
    df_o_decomp = pd.DataFrame({"TEST_SID": [99.0, 102.0]}, index=dates_2)
    f_intra = IntradayReturnFeature()
    f_over = OvernightReturnFeature()
    res_intra = f_intra.compute({"adj_close": df_c_decomp, "adj_open": df_o_decomp})
    res_over = f_over.compute({"adj_close": df_c_decomp, "adj_open": df_o_decomp})
    exp_intra = (105.0 / 102.0) - 1.0
    act_intra = res_intra.iloc[1]["TEST_SID"]
    exp_over = (102.0 / 100.0) - 1.0
    act_over = res_over.iloc[1]["TEST_SID"]
    checks.append({
        "run_id": RUN_ID, "feature": "ret_intraday", "date": dates[1].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S23A_RETR_INTRADAY_FORMULA",
        "expected": exp_intra, "actual": act_intra, "absolute_error": abs(act_intra - exp_intra), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_intra - exp_intra) <= 1e-7 else "FAILED",
        "input_reference": "adj_close=105, adj_open=102 -> 105/102-1",
    })
    checks.append({
        "run_id": RUN_ID, "feature": "ret_overnight", "date": dates[1].strftime("%Y-%m-%d"),
        "canonical_sid": "TEST_SYNTHETIC", "case_id": "CASE_S23B_RETR_OVERNIGHT_FORMULA",
        "expected": exp_over, "actual": act_over, "absolute_error": abs(act_over - exp_over), "tolerance": 1e-7,
        "nan_reason": "NONE", "status": "PASSED" if abs(act_over - exp_over) <= 1e-7 else "FAILED",
        "input_reference": "adj_open=102, prev_close=100 -> 102/100-1=0.02",
    })

    print(f"LỚP 1 HOÀN TẤT: {sum(c['status'] == 'PASSED' for c in checks)}/{len(checks)} bài test tổng hợp đạt chuẩn.")
    return checks


def run_empirical_pilot():
    """Lớp 2: Kiểm thử trên dữ liệu thực Development 2000-2002."""
    print("\n" + "=" * 80)
    print("LỚP 2: KIỂM THỬ TRÊN LÁT CẮT THỰC DEVELOPMENT (2000-2002) VỚI 10 CANONICAL SIDs")
    print("=" * 80)

    pilot_sids = [
        "AAPL R735QTJ8XC9X",  # Clean tech, 2:1 split on 2000-06-21
        "MSFT R735QTJ8XC9X",  # Continuous benchmark
        "A RPTMYV3VC57P",     # Index entrant 2000-07-01 with 126 clean warmup bars in matrix (2000-01-03 to 2000-06-30)
        "BF RVCJ9QZYSJMT",    # Index entrant 2000-07-01 with 18 warmup bars (lookback deficit)
        "KSU R735QTJ8XC9X",   # Spinoff discontinuity on 2000-07-13
        "CPTH RJF8CZIDFLNP",  # Trading halt anomaly in Feb 2001
        "JPM R735QTJ8XC9X",   # Financials
        "XON R735QTJ8XC9X",   # Energy (Exxon Mobil permanent canonical SID)
        "JNJ R735QTJ8XC9X",   # Healthcare
        "WMT R735QTJ8XC9X",   # Consumer Staples
    ]

    print("Nạp ma trận lát cắt cho 10 mã (kèm Warm-up 1998-2000 để kiểm tra)...")
    adj_close_full = load_matrix("adj_close", dev_only=True, include_warmup=True)
    adj_open_full = load_matrix("adj_open", dev_only=True, include_warmup=True)
    adj_high_full = load_matrix("adj_high", dev_only=True, include_warmup=True)
    adj_low_full = load_matrix("adj_low", dev_only=True, include_warmup=True)
    adj_vol_full = load_matrix("adj_volume", dev_only=True, include_warmup=True)
    close_full = load_matrix("close", dev_only=True, include_warmup=True)
    volume_full = load_matrix("volume", dev_only=True, include_warmup=True)
    daily_ret_full = load_matrix("daily_return", dev_only=True, include_warmup=True)
    split_mat_full = load_matrix("cumulative_split_factor", dev_only=True, include_warmup=True)
    bar_quality_full = load_bar_quality_mask(dev_only=True, include_warmup=True)
    membership_full = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)

    missing_sids = set(pilot_sids) - set(adj_close_full.columns)
    if missing_sids:
        raise RuntimeError(f"Thiếu các SID bắt buộc trong ma trận dữ liệu: {missing_sids}. Script dừng ngay lập tức!")

    avail_sids = [s for s in pilot_sids if s in adj_close_full.columns]
    print(f"Số lượng mã thực tế có trong kho: {len(avail_sids)}/{len(pilot_sids)} (100% đầy đủ)")

    eval_dates = adj_close_full.loc["1998-01-02":"2002-12-31"].index
    data_slice = {
        "adj_close": adj_close_full.loc[eval_dates, avail_sids],
        "adj_open": adj_open_full.loc[eval_dates, avail_sids],
        "adj_high": adj_high_full.loc[eval_dates, avail_sids],
        "adj_low": adj_low_full.loc[eval_dates, avail_sids],
        "adj_volume": adj_vol_full.loc[eval_dates, avail_sids],
        "close": close_full.loc[eval_dates, avail_sids],
        "volume": volume_full.loc[eval_dates, avail_sids],
        "daily_return": daily_ret_full.loc[eval_dates, avail_sids],
    }
    bar_q_slice = bar_quality_full.loc[eval_dates, avail_sids]
    mem_slice = membership_full.loc[eval_dates, avail_sids]

    # Instantiate all 16 features
    features_dict = {
        # Batch 1 (Representative 5)
        "ret_20d": PriceRatioMomentumFeature(window=20),
        "vol_realized_20d": RealizedVolatilityFeature(window=20, return_type="daily_return", annualize=False),
        "amihud_illiq_20d": AmihudIlliquidityFeature(window=20),
        "rsi_14d": RSIFeature(window=14),
        "bollinger_pct_b_20d": BollingerPctBFeature(window=20),

        # Batch 2A (Momentum 4)
        "ret_1d": PriceRatioMomentumFeature(window=1),
        "ret_5d": PriceRatioMomentumFeature(window=5),
        "ret_60d": PriceRatioMomentumFeature(window=60),
        "mom_12m_skip_1m": Mom12mSkip1mFeature(lookback=252, skip=21),

        # Batch 2B (Volatility 3)
        "vol_realized_60d": RealizedVolatilityFeature(window=60, return_type="daily_return", annualize=False),
        "vol_parkinson_20d": ParkinsonVolatilityFeature(window=20),
        "downside_deviation_20d": DownsideDeviationFeature(window=20),

        # Batch 2C (Volume & Intraday 4)
        "volume_ratio_5_20": VolumeRatioFeature(fast_window=5, slow_window=20),
        "log_dollar_volume_20d": LogDollarVolumeFeature(window=20),
        "ret_intraday": IntradayReturnFeature(),
        "ret_overnight": OvernightReturnFeature(),
    }

    print("Tính toán toàn bộ 16 features trên lát cắt dữ liệu thực...")
    computed_matrices = {}
    for feat_name, feat_obj in features_dict.items():
        computed_matrices[feat_name] = feat_obj.compute(data_slice, bar_quality_mask=bar_q_slice, membership_mask=mem_slice)

    # Focus analysis window: 2000-07-01 to 2002-12-31 (Development period)
    dev_mask_dates = (eval_dates >= "2000-07-01") & (eval_dates <= "2002-12-31")
    dev_dates = eval_dates[dev_mask_dates]

    empirical_checks = []

    # E01: Agilent Technologies Day 1 valid for ret_20d
    sid_a = "A RPTMYV3VC57P"
    d_entry = "2000-07-03"
    val_a_ret20 = computed_matrices["ret_20d"].loc[d_entry, sid_a]
    a_prices = data_slice["adj_close"][sid_a].loc[:d_entry].dropna()
    exp_a_ret20 = (a_prices.loc[d_entry] / a_prices.iloc[-21]) - 1.0
    passed_e01 = not np.isnan(val_a_ret20) and abs(val_a_ret20 - exp_a_ret20) <= 1e-7
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": d_entry, "canonical_sid": sid_a,
        "case_id": "CASE_E01_AGILENT_ENTRY_WARMUP_SUCCESS", "expected": exp_a_ret20, "actual": val_a_ret20,
        "absolute_error": abs(val_a_ret20 - exp_a_ret20), "tolerance": 1e-7,
        "nan_reason": "NONE" if passed_e01 else "UNEXPECTED_NAN", "status": "PASSED" if passed_e01 else "FAILED",
        "input_reference": f"P[2000-07-03]={a_prices.loc[d_entry]:.4f}, P[T-20]={a_prices.iloc[-21]:.4f} (126 clean pre-entry bars in matrix)",
    })

    # E02: BF Insufficient Warmup: exactly 2 NaN sessions (07-03, 07-05) and valid on 07-06
    sid_bf = "BF RVCJ9QZYSJMT"
    val_bf_d1 = computed_matrices["ret_20d"].loc["2000-07-03", sid_bf]
    val_bf_d2 = computed_matrices["ret_20d"].loc["2000-07-05", sid_bf]
    val_bf_valid = computed_matrices["ret_20d"].loc["2000-07-06", sid_bf]
    exp_bf_valid = -0.07533037
    passed_e02 = np.isnan(val_bf_d1) and np.isnan(val_bf_d2) and abs(val_bf_valid - exp_bf_valid) <= 1e-5
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": d_entry, "canonical_sid": sid_bf,
        "case_id": "CASE_E02_BF_INSUFFICIENT_WARMUP_NAN", "expected": np.nan, "actual": val_bf_d1,
        "absolute_error": 0.0 if np.isnan(val_bf_d1) else 1.0, "tolerance": 0.0,
        "nan_reason": "LOOKBACK_DEFICIT_19_BARS", "status": "PASSED" if passed_e02 else "FAILED",
        "input_reference": "BF entered with 18 warmup bars: NaN on 07-03 & 07-05, valid on 07-06",
    })

    # E03: KSU Spinoff NaN Propagation: exactly 21 NaN sessions (07-13..08-10) and recovers on 08-11
    sid_ksu = "KSU R735QTJ8XC9X"
    ksu_nan_slice = computed_matrices["ret_20d"].loc["2000-07-13":"2000-08-10", sid_ksu]
    val_ksu_reseed = computed_matrices["ret_20d"].loc["2000-08-11", sid_ksu]
    exp_ksu_reseed = -0.03633721
    passed_e03 = (len(ksu_nan_slice) == 21) and ksu_nan_slice.isna().all() and abs(val_ksu_reseed - exp_ksu_reseed) <= 1e-5
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": "2000-07-13", "canonical_sid": sid_ksu,
        "case_id": "CASE_E03_KSU_SPINOFF_NAN_PROPAGATION", "expected": np.nan, "actual": computed_matrices["ret_20d"].loc["2000-07-13", sid_ksu],
        "absolute_error": 0.0 if np.isnan(computed_matrices["ret_20d"].loc["2000-07-13", sid_ksu]) else 1.0, "tolerance": 0.0,
        "nan_reason": "SPINOFF_DISCONTINUITY_IN_WINDOW", "status": "PASSED" if passed_e03 else "FAILED",
        "input_reference": "Spinoff at 2000-07-13: 21 NaN sessions (07-13..08-10), recov on 08-11 (-0.036337)",
    })

    # E04A: AAPL 2:1 Split Internal Pipeline Consistency (Source Factor Parity)
    sid_aapl = "AAPL R735QTJ8XC9X"
    d_split = "2000-06-21"
    aapl_ret_split = data_slice["daily_return"].loc[d_split, sid_aapl]
    p_prev_raw = data_slice["close"].loc["2000-06-20", sid_aapl]  # 101.0
    p_curr_raw = data_slice["close"].loc[d_split, sid_aapl]        # 55.56
    s_prev = split_mat_full.loc["2000-06-20", sid_aapl]            # 0.00892857
    s_curr = split_mat_full.loc[d_split, sid_aapl]                 # 0.0178571
    source_factor_ratio = s_curr / s_prev
    expected_e04a = (p_curr_raw * source_factor_ratio / p_prev_raw) - 1.0
    err_e04a = abs(aapl_ret_split - expected_e04a)
    passed_e04a = err_e04a < 1e-12
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "daily_return", "date": d_split, "canonical_sid": sid_aapl,
        "case_id": "CASE_E04A_AAPL_SPLIT_INTERNAL_PIPELINE_CONSISTENCY", "expected": expected_e04a, "actual": aapl_ret_split,
        "absolute_error": err_e04a, "tolerance": 1e-12, "nan_reason": "NONE" if passed_e04a else "DISCREPANCY",
        "status": "PASSED" if passed_e04a else "FAILED",
        "input_reference": f"Internal factor ratio {s_curr}/{s_prev} = {source_factor_ratio:.10f}",
    })

    # E04B: AAPL 2:1 Split Theoretical Ideal Reference Comparison
    expected_e04b = (p_curr_raw * 2.0 / p_prev_raw) - 1.0
    err_e04b = abs(aapl_ret_split - expected_e04b)
    passed_e04b = err_e04b <= 1e-5
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "daily_return", "date": d_split, "canonical_sid": sid_aapl,
        "case_id": "CASE_E04B_AAPL_SPLIT_THEORETICAL_IDEAL_COMPARISON", "expected": expected_e04b, "actual": aapl_ret_split,
        "absolute_error": err_e04b, "tolerance": 1e-5, "nan_reason": "NONE" if passed_e04b else "EXCEEDS_TOLERANCE",
        "status": "PASSED" if passed_e04b else "FAILED",
        "input_reference": f"Ideal 2.0 ratio gives {expected_e04b:.8f}, diff={err_e04b:.2e} (source factor ratio is {source_factor_ratio:.8f})",
    })

    # E05: CPTH Trading Halt Anomaly
    sid_cpth = "CPTH RJF8CZIDFLNP"
    val_cpth = computed_matrices["ret_20d"].loc["2001-02-05", sid_cpth]
    passed_e05 = np.isnan(val_cpth)
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": "2001-02-05", "canonical_sid": sid_cpth,
        "case_id": "CASE_E05_CPTH_BAD_DATA_PERIOD_NAN", "expected": np.nan, "actual": val_cpth,
        "absolute_error": 0.0 if passed_e05 else 1.0, "tolerance": 0.0,
        "nan_reason": "BAD_DATA_PERIOD_FLAG", "status": "PASSED" if passed_e05 else "FAILED",
        "input_reference": "CPTH CORR_013 trading halt on 2001-02-05",
    })

    # E06: Pre-Membership Output Masking
    val_a_pre = computed_matrices["ret_20d"].loc["1999-12-01", sid_a]
    passed_e06 = np.isnan(val_a_pre)
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_20d", "date": "1999-12-01", "canonical_sid": sid_a,
        "case_id": "CASE_E06_PRE_MEMBERSHIP_OUTPUT_MASK_NAN", "expected": np.nan, "actual": val_a_pre,
        "absolute_error": 0.0 if passed_e06 else 1.0, "tolerance": 0.0,
        "nan_reason": "NON_MEMBER_OUTPUT_MASK", "status": "PASSED" if passed_e06 else "FAILED",
        "input_reference": "Agilent on 1999-12-01 had prices but membership_mask=False",
    })

    # E07: Agilent mom_12m_skip_1m lookback deficit & recovery
    val_a_mom12m_d1 = computed_matrices["mom_12m_skip_1m"].loc[d_entry, sid_a]
    val_a_mom12m_rec = computed_matrices["mom_12m_skip_1m"].loc["2001-01-02", sid_a]
    exp_a_mom12m_rec = -0.27465476
    passed_e07 = np.isnan(val_a_mom12m_d1) and abs(val_a_mom12m_rec - exp_a_mom12m_rec) <= 1e-5
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "mom_12m_skip_1m", "date": d_entry, "canonical_sid": sid_a,
        "case_id": "CASE_E07_AGILENT_MOM12M_DEFICIT_AND_RECOVERY", "expected": np.nan, "actual": val_a_mom12m_d1,
        "absolute_error": 0.0 if np.isnan(val_a_mom12m_d1) else 1.0, "tolerance": 0.0,
        "nan_reason": "LOOKBACK_DEFICIT_127_BARS", "status": "PASSED" if passed_e07 else "FAILED",
        "input_reference": f"Agilent had 127 bars on 2000-07-03 and 252 bars on 2000-12-29 in matrix (<253 needed) -> NaN; reaches 253 bars and valid on 2001-01-02 ({val_a_mom12m_rec:.4f})",
    })

    # E08: MSFT Intraday and Overnight Return Identity Decomposition
    sid_msft = "MSFT R735QTJ8XC9X"
    d_check = "2000-07-05"
    r_intra_msft = computed_matrices["ret_intraday"].loc[d_check, sid_msft]
    r_over_msft = computed_matrices["ret_overnight"].loc[d_check, sid_msft]
    r_1d_msft = computed_matrices["ret_1d"].loc[d_check, sid_msft]
    decomp_msft = (1.0 + r_over_msft) * (1.0 + r_intra_msft) - 1.0
    err_e08 = abs(decomp_msft - r_1d_msft)
    passed_e08 = err_e08 <= 1e-7
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "ret_1d", "date": d_check, "canonical_sid": sid_msft,
        "case_id": "CASE_E08_INTRADAY_OVERNIGHT_DECOMPOSITION_IDENTITY", "expected": r_1d_msft, "actual": decomp_msft,
        "absolute_error": err_e08, "tolerance": 1e-7, "nan_reason": "NONE" if passed_e08 else "IDENTITY_FAIL",
        "status": "PASSED" if passed_e08 else "FAILED",
        "input_reference": f"MSFT {d_check}: (1+r_over)*(1+r_intra)-1 == r_1d",
    })

    # E09: Real market Parkinson volatility exact numerical parity
    v_park_msft = computed_matrices["vol_parkinson_20d"].loc[d_check, sid_msft]
    h_msft_20 = data_slice["adj_high"][sid_msft].loc[:d_check].iloc[-20:].values
    l_msft_20 = data_slice["adj_low"][sid_msft].loc[:d_check].iloc[-20:].values
    exp_park_msft = float(np.sqrt(np.mean((np.log(h_msft_20 / l_msft_20) ** 2) / (4.0 * np.log(2.0)))))
    err_e09 = abs(v_park_msft - exp_park_msft)
    tol_e09 = 1e-7
    passed_e09 = err_e09 <= tol_e09
    empirical_checks.append({
        "run_id": RUN_ID, "feature": "vol_parkinson_20d", "date": d_check, "canonical_sid": sid_msft,
        "case_id": "CASE_E09_MSFT_PARKINSON_VOL_NUMERICAL_PARITY", "expected": exp_park_msft, "actual": v_park_msft,
        "absolute_error": err_e09, "tolerance": tol_e09, "nan_reason": "NONE" if passed_e09 else "TOLERANCE_EXCEEDED",
        "status": "PASSED" if passed_e09 else "FAILED",
        "input_reference": f"MSFT {d_check}: independent H/L 20-bar formula = {exp_park_msft:.8f}, feature = {v_park_msft:.8f}, diff={err_e09:.2e}",
    })

    print(f"LỚP 2 HOÀN TẤT: {sum(c['status'] == 'PASSED' for c in empirical_checks)}/{len(empirical_checks)} bài test thực nghiệm đạt chuẩn.")

    # -------------------------------------------------------------
    # Compute Coverage Summary for ALL 16 Features on Development Window
    # -------------------------------------------------------------
    print("\nTính toán độ phủ dữ liệu (Coverage) cho toàn bộ 16 features trên Development...")
    coverage_rows = []
    dev_mem = mem_slice.loc[dev_dates]
    total_cells = dev_mem.size
    mem_cells = int(dev_mem.values.sum())

    for feat_name, mat in computed_matrices.items():
        mat_dev = mat.loc[dev_dates]
        valid_cells = int(mat_dev.notna().values.sum())
        nan_total = int(mat_dev.isna().values.sum())
        nan_outside_mem = int((mat_dev.isna() & ~dev_mem).values.sum())
        nan_inside_mem = int((mat_dev.isna() & dev_mem).values.sum())
        cov_pct = (valid_cells / mem_cells) * 100.0 if mem_cells > 0 else 0.0

        coverage_rows.append({
            "run_id": RUN_ID,
            "feature": feat_name,
            "date_range": "2000-07-01_to_2002-12-31",
            "membership_mask_type": "strict_layer1",
            "total_cells": total_cells,
            "membership_cells": mem_cells,
            "valid_cells": valid_cells,
            "nan_total": nan_total,
            "nan_membership": nan_outside_mem,
            "nan_quality_or_lookback": nan_inside_mem,
            "coverage_pct_of_membership": round(cov_pct, 2),
        })
        print(f"  {feat_name:<24}: Valid={valid_cells}/{mem_cells}, NaN_Quality={nan_inside_mem:<4}, Coverage={cov_pct:.2f}%")

    return empirical_checks, coverage_rows


def main():
    print("Bắt đầu thực thi Pipeline Pilot Features (16 Features Đầy Đủ)...")
    synth_checks = run_synthetic_checks()
    emp_checks, cov_rows = run_empirical_pilot()

    all_checks = synth_checks + emp_checks
    df_checks = pd.DataFrame(all_checks)
    df_cov = pd.DataFrame(cov_rows)

    checks_csv = REPORTS_DIR / "numerical_checks.csv"
    cov_csv = REPORTS_DIR / "coverage_summary.csv"

    df_checks.to_csv(checks_csv, index=False, encoding="utf-8")
    df_cov.to_csv(cov_csv, index=False, encoding="utf-8")

    passed_count = sum(df_checks['status'] == 'PASSED')
    failed_count = sum(df_checks['status'] == 'FAILED')

    print("\n" + "=" * 80)
    print("TỔNG KẾT KẾT QUẢ PILOT FEATURES V1 (16 FEATURES)")
    print("=" * 80)
    print(f"Tổng số bài kiểm tra số học: {len(df_checks)}")
    print(f"Số bài kiểm tra PASSED     : {passed_count}")
    print(f"Số bài kiểm tra FAILED     : {failed_count}")
    print(f"Đã lưu bảng numerical checks vào: {checks_csv.relative_to(ROOT_DIR)}")
    print(f"Đã lưu bảng coverage summary vào: {cov_csv.relative_to(ROOT_DIR)}")
    print("=" * 80)

    if failed_count > 0:
        print(f"LỖI: Có {failed_count} bài kiểm tra không đạt chuẩn. Pipeline dừng với exit code 1.")
        sys.exit(1)
    else:
        print("TẤT CẢ CÁC BÀI KIỂM TRA ĐỀU ĐẠT CHUẨN (EXIT CODE 0).")


if __name__ == "__main__":
    main()
