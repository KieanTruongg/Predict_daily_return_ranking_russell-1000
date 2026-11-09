# -*- coding: utf-8 -*-
"""
scripts/01_pipeline/15_extended_causal_tests.py
================================================
Reproducible Point-In-Time (PIT) causality verification for all 16 candidate features.

Methodology:
For each feature and test coordinate (Date T, Canonical SID):
1. Compute baseline feature value V_orig from clean inputs.
   CRITICAL: Assert V_orig is finite and non-NaN (preventing trivial NaN pass).
2. Future Perturbation Test: Corrupt/mutate all market inputs for future dates t > T.
   Recompute feature -> V_corrupt.
   Assert |V_corrupt - V_orig| <= 1e-11.
3. Future Truncation Test: Truncate all input series strictly at date T (no future exists).
   Recompute feature -> V_trunc.
   Assert |V_trunc - V_orig| <= 1e-11.

CLI Usage:
    python scripts/01_pipeline/15_extended_causal_tests.py --seed 42
"""

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data.matrix_loader import (
    load_matrix,
    load_bar_quality_mask,
    load_layer1_mask,
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

ALL_FEATURE_SPECS = [
    ("ret_1d", PriceRatioMomentumFeature, {"window": 1}, ["adj_close"]),
    ("ret_5d", PriceRatioMomentumFeature, {"window": 5}, ["adj_close"]),
    ("ret_20d", PriceRatioMomentumFeature, {"window": 20}, ["adj_close"]),
    ("ret_60d", PriceRatioMomentumFeature, {"window": 60}, ["adj_close"]),
    ("mom_12m_skip_1m", Mom12mSkip1mFeature, {"lookback": 252, "skip": 21}, ["adj_close"]),
    ("vol_realized_20d", RealizedVolatilityFeature, {"window": 20, "return_type": "daily_return", "annualize": False}, ["daily_return"]),
    ("vol_realized_60d", RealizedVolatilityFeature, {"window": 60, "return_type": "daily_return", "annualize": False}, ["daily_return"]),
    ("vol_parkinson_20d", ParkinsonVolatilityFeature, {"window": 20}, ["adj_high", "adj_low"]),
    ("downside_deviation_20d", DownsideDeviationFeature, {"window": 20}, ["daily_return"]),
    ("amihud_illiq_20d", AmihudIlliquidityFeature, {"window": 20, "scale": 1e6}, ["daily_return", "close", "volume"]),
    ("volume_ratio_5_20", VolumeRatioFeature, {"fast_window": 5, "slow_window": 20}, ["adj_volume"]),
    ("log_dollar_volume_20d", LogDollarVolumeFeature, {"window": 20}, ["close", "volume"]),
    ("ret_intraday", IntradayReturnFeature, {}, ["adj_close", "adj_open"]),
    ("ret_overnight", OvernightReturnFeature, {}, ["adj_close", "adj_open"]),
    ("rsi_14d", RSIFeature, {"window": 14}, ["adj_close"]),
    ("bollinger_pct_b_20d", BollingerPctBFeature, {"window": 20, "k": 2.0}, ["adj_close"]),
]

DEFAULT_TEST_DATES = ["2005-06-15", "2015-06-15", "2022-06-15"]
DEFAULT_TEST_SIDS = ["AAPL R735QTJ8XC9X", "MSFT R735QTJ8XC9X", "XON R735QTJ8XC9X"]


def run_extended_causal_tests(
    test_dates=None,
    test_sids=None,
    seed=42,
    output_csv=None,
    verbose=True,
):
    rng = np.random.default_rng(seed)
    dates_to_test = test_dates or DEFAULT_TEST_DATES
    sids_to_test = test_sids or DEFAULT_TEST_SIDS
    out_path = Path(output_csv) if output_csv else ROOT_DIR / "docs" / "reports" / "feature_eda" / "extended_causal_test_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if verbose:
        print("=" * 80)
        print("BẮT ĐẦU KIỂM ĐỊNH NHÂN QUẢ MỞ RỘNG (EXTENDED CAUSAL TESTS)")
        print(f"Tham số: seed={seed}, dates={dates_to_test}, sids={sids_to_test}")
        print("=" * 80)

    # 1. Load warmup masks and slice to test SIDs for speed
    bar_q_full = load_bar_quality_mask(dev_only=True, include_warmup=True)[sids_to_test]
    mem_mask_full = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)[sids_to_test]

    # Cache inputs sliced to target SIDs
    input_cache = {}
    needed_inputs = set()
    for _, _, _, inps in ALL_FEATURE_SPECS:
        needed_inputs.update(inps)

    for inp in needed_inputs:
        input_cache[inp] = load_matrix(inp, dev_only=True, include_warmup=True)[sids_to_test]

    results = []
    total_evals = len(ALL_FEATURE_SPECS) * len(dates_to_test) * len(sids_to_test)
    passed_cnt = 0
    t_start = time.time()

    for feat_name, feat_cls, feat_kwargs, inps in ALL_FEATURE_SPECS:
        feat_inst = feat_cls(**feat_kwargs)
        
        # Prepare clean baseline data
        data_baseline = {k: input_cache[k] for k in inps}
        df_orig = feat_inst.compute(data=data_baseline, bar_quality_mask=bar_q_full, membership_mask=mem_mask_full)

        for t_str in dates_to_test:
            t_dt = pd.Timestamp(t_str)
            if t_dt not in df_orig.index:
                raise ValueError(f"Test date {t_str} not found in matrix dates index!")

            # --- Test A: Future Perturbation for this date T ---
            future_mask = input_cache[inps[0]].index > t_dt
            data_corrupt = {}
            for k in inps:
                df_c = input_cache[k].copy()
                noise = rng.uniform(1.5, 5.0, size=(future_mask.sum(), df_c.shape[1]))
                df_c.loc[future_mask] = df_c.loc[future_mask].values * noise
                data_corrupt[k] = df_c

            df_corrupt_res = feat_inst.compute(data=data_corrupt, bar_quality_mask=bar_q_full, membership_mask=mem_mask_full)

            # --- Test B: Future Truncation for this date T ---
            trunc_idx = input_cache[inps[0]].index <= t_dt
            data_trunc = {k: input_cache[k].loc[trunc_idx].copy() for k in inps}
            bar_q_trunc = bar_q_full.loc[trunc_idx]
            mem_trunc = mem_mask_full.loc[trunc_idx]

            df_trunc_res = feat_inst.compute(data=data_trunc, bar_quality_mask=bar_q_trunc, membership_mask=mem_trunc)

            # Evaluate each SID
            for sid in sids_to_test:
                val_orig = float(df_orig.loc[t_dt, sid])

                # CRITICAL CAUSAL AUDIT: Assert baseline is FINITE (not NaN)
                if not np.isfinite(val_orig):
                    raise AssertionError(
                        f"Causality audit setup error: baseline value for {feat_name} at ({t_str}, {sid}) "
                        f"is {val_orig}. Test coordinate must be finite to prevent trivial pass!"
                    )

                val_corrupt = float(df_corrupt_res.loc[t_dt, sid])
                val_trunc = float(df_trunc_res.loc[t_dt, sid])

                diff_perturb = abs(val_corrupt - val_orig)
                diff_trunc = abs(val_trunc - val_orig)
                passed = (diff_perturb <= 1e-11) and (diff_trunc <= 1e-11) and np.isfinite(val_corrupt) and np.isfinite(val_trunc)

                if not passed:
                    raise AssertionError(
                        f"Point-In-Time causality violation detected in {feat_name} at ({t_str}, {sid})! "
                        f"Orig={val_orig}, Corrupt={val_corrupt} (diff={diff_perturb}), Trunc={val_trunc} (diff={diff_trunc})"
                    )

                passed_cnt += 1
                results.append({
                    "feature": feat_name,
                    "test_date": t_str,
                    "sid": sid,
                    "val_orig": round(val_orig, 6),
                    "val_corrupt": round(val_corrupt, 6),
                    "val_trunc": round(val_trunc, 6),
                    "diff_perturbation": float(diff_perturb),
                    "diff_truncation": float(diff_trunc),
                    "passed": bool(passed),
                })

    df_out = pd.DataFrame(results)
    df_out.to_csv(out_path, index=False)

    elapsed = time.time() - t_start
    if verbose:
        print(f"\nKết quả: {passed_cnt}/{total_evals} bài kiểm tra PASSED (100.0%) trong {elapsed:.2f}s!")
        print(f"Đã lưu chi tiết vào: {out_path}")
        print("Tất cả các ô kiểm tra đều xác nhận giá trị HỮU HẠN (không bị NaN che giấu sai số).")

    return df_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reproducible PIT causality tests for feature store.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for future perturbation.")
    parser.add_argument("--output", type=str, default=None, help="Custom output CSV path.")
    args = parser.parse_args()

    run_extended_causal_tests(seed=args.seed, output_csv=args.output, verbose=True)
