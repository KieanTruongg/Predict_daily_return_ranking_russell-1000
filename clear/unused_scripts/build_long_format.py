"""
Quick script: Stack wide feature parquets → long-format feature_store_long.parquet
(Chỉ chạy step 6 sau khi wide matrices đã được save)
"""
import os, sys, time
import numpy as np
import pandas as pd
import warnings; warnings.filterwarnings("ignore")

sys.stdout.reconfigure(encoding="utf-8")

FEATURES_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "data", "processed", "features"
)

ALL_FEATURES = [
    "ret_1d","ret_2d","ret_5d","ret_10d","ret_20d","ret_60d","ret_252d",
    "close_to_sma_20","close_to_sma_50","close_to_sma_200","macd_hist_norm",
    "rsi_14","bb_pct_b","bb_bandwidth","hl_spread","close_to_high",
    "vol_ratio_5_20","vol_zscore_20","close_to_vwap_5","amihud_20d",
    "realized_vol_5d","realized_vol_20d","realized_vol_60d",
    "ret_1d_rank","ret_5d_rank","ret_20d_rank","rsi_14_rank",
    "realized_vol_20d_rank","amihud_20d_rank",
    "target_forward_return","target_return_rank",
]

print("Loading wide matrices and stacking to long format...")
t0 = time.time()

long_dfs = []
for i, fname in enumerate(ALL_FEATURES):
    fpath = os.path.join(FEATURES_DIR, f"{fname}.parquet")
    if not os.path.exists(fpath):
        print(f"  SKIP (not found): {fname}")
        continue
    df = pd.read_parquet(fpath)
    df.index = pd.to_datetime(df.index)
    # stack — pandas 3.x compatible
    s = df.stack(future_stack=True)
    s.name = fname
    long_dfs.append(s)
    print(f"  [{i+1:02d}/{len(ALL_FEATURES)}] {fname} stacked — {len(s):,} rows")

print("\nConcatenating...")
long_df = pd.concat(long_dfs, axis=1)
long_df.index.names = ["date", "ticker"]
long_df = long_df.reset_index()

# Drop rows where ALL features are NaN (keep rows with at least 1 value)
feature_cols = [c for c in long_df.columns if c not in ("date", "ticker")]
has_data = long_df[feature_cols].notna().any(axis=1)
long_df  = long_df[has_data].reset_index(drop=True)

out_path = os.path.join(FEATURES_DIR, "feature_store_long.parquet")
long_df.to_parquet(out_path, compression="snappy", index=False)
size_mb = os.path.getsize(out_path) / 1e6

print(f"\n✅ Saved: feature_store_long.parquet")
print(f"   Rows    : {long_df.shape[0]:,}")
print(f"   Cols    : {long_df.shape[1]}")
print(f"   Size    : {size_mb:.1f} MB")
print(f"   NaN rate: {long_df[feature_cols].isna().mean().mean()*100:.1f}%")
print(f"   Time    : {time.time()-t0:.1f}s")
