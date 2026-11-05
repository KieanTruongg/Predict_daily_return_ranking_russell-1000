"""
Script: scripts/06_features/build_feature_store.py
Purpose: Build Feature Store từ in_sample matrices → lưu ra parquet

Pipeline:
  1. Load 5 matrices từ data/processed/in_sample/ (close, high, low, volume, forward_returns)
  2. Filter OOS tickers (≥95% NaN trong in-sample period)
  3. Gọi FeatureEngineer.build_feature_matrix() — vectorized trên toàn ma trận
  4. Lưu feature store theo 2 format:
     a. Wide matrix per feature: data/processed/features/{feature_name}.parquet
     b. Long-format stacked:     data/processed/features/feature_store_long.parquet
  5. In summary statistics

Thời gian dự kiến: ~5–10 phút (6,021 × 2,553 tickers, vectorized)
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.features.feature_engineer import FeatureEngineer
from src.data.pit_universe import build_pit_mask, mask_coverage_report

IN_SAMPLE_DIR  = os.path.join(PROJECT_ROOT, "data", "processed", "in_sample")
BY_YEAR_DIR    = os.path.join(PROJECT_ROOT, "data", "raw", "universe", "by_year")
FEATURES_DIR   = os.path.join(PROJECT_ROOT, "data", "processed", "features")
os.makedirs(FEATURES_DIR, exist_ok=True)

SEP = "=" * 80

# ─────────────────────────────────────────────────────────────────────────────
def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def load_matrix(name: str) -> pd.DataFrame:
    path = os.path.join(IN_SAMPLE_DIR, f"{name}.parquet")
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df

# ─────────────────────────────────────────────────────────────────────────────
def filter_oos_tickers(close: pd.DataFrame, threshold: float = 0.95) -> list[str]:
    """
    Trả về list tickers có ≥ threshold NaN trong in-sample → loại ra.
    Đây là out-sample tickers (chỉ xuất hiện 2024+).
    """
    nan_pct = close.isna().mean()
    oos = nan_pct[nan_pct >= threshold].index.tolist()
    return oos

# ─────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    print(SEP)
    print("  BUILD FEATURE STORE — in_sample → data/processed/features/")
    print("  Dữ liệu: 2000-01-03 → 2023-12-29 (6,021 ngày)")
    print(SEP)

    # ── 1. Load matrices ──────────────────────────────────────────────────────
    section("1. LOADING IN-SAMPLE MATRICES")
    matrices = {}
    for name in ["close", "high", "low", "volume", "forward_returns"]:
        print(f"  Loading {name}...", end="", flush=True)
        t = time.time()
        matrices[name] = load_matrix(name)
        print(f" ✓ {matrices[name].shape}  ({time.time()-t:.1f}s)")

    close           = matrices["close"]
    high            = matrices["high"]
    low             = matrices["low"]
    volume          = matrices["volume"]
    forward_returns = matrices["forward_returns"]

    # ── 2. Filter OOS tickers ─────────────────────────────────────────────────
    section("2. FILTERING OUT-OF-SAMPLE TICKERS")
    oos_tickers = filter_oos_tickers(close, threshold=0.95)
    print(f"  Tổng tickers trong matrix: {len(close.columns):,}")
    print(f"  OOS tickers (≥95% NaN):    {len(oos_tickers):,} → loại bỏ")

    keep_tickers = [t for t in close.columns if t not in set(oos_tickers)]
    print(f"  Tickers giữ lại:           {len(keep_tickers):,}")

    close           = close[keep_tickers]
    high            = high[keep_tickers]
    low             = low[keep_tickers]
    volume          = volume[keep_tickers]
    forward_returns = forward_returns[keep_tickers]

    print(f"\n  Matrix shape sau filter: {close.shape[0]:,} days × {close.shape[1]:,} tickers")

    # ── 2b. PIT universe mask (list năm Y hiệu lực sau reconstitution cuối tháng 6) ─
    section("2b. BUILDING PIT UNIVERSE MASK")
    universe_mask = build_pit_mask(close.index, close.columns, by_year_dir=BY_YEAR_DIR)
    print(f"  Members/ngày (trung bình): {universe_mask.sum(axis=1).mean():,.1f}")
    print("  Coverage giá theo nửa năm (H1 thấp hơn H2 → thiếu giá của mã bị loại ở recon):")
    print(mask_coverage_report(universe_mask, close).to_string())

    # ── 3. Build features ─────────────────────────────────────────────────────
    section("3. COMPUTING FEATURES (VECTORIZED)")
    print("  Khởi tạo FeatureEngineer (winsorize=1%, min_valid_days=252)...")

    fe = FeatureEngineer(
        forward_lookahead=1,
        winsorize_pct=0.01,
        min_valid_days=252,
    )

    print("  Đang tính features... (có thể mất vài phút)")
    t_feat = time.time()
    feature_dict = fe.build_feature_matrix(
        close=close,
        high=high,
        low=low,
        volume=volume,
        forward_returns=forward_returns,
        universe_mask=universe_mask,
    )
    elapsed = time.time() - t_feat
    print(f"  ✓ Hoàn tất tính features trong {elapsed:.1f}s")
    print(f"  Số features: {len(feature_dict)}")

    # ── 4. Summary statistics per feature ────────────────────────────────────
    section("4. FEATURE SUMMARY STATISTICS")
    print(f"\n  {'Feature':<30} {'Non-NaN%':>10} {'Mean':>12} {'Std':>12} {'P1%':>10} {'P99%':>10}")
    print(f"  {'-'*78}")
    for fname, fmat in feature_dict.items():
        flat = fmat.values.flatten()
        flat = flat[~np.isnan(flat)]
        if len(flat) == 0:
            print(f"  {fname:<30} {'ALL NaN':>10}")
            continue
        non_nan_pct = len(flat) / (fmat.shape[0] * fmat.shape[1]) * 100
        mean_v = np.mean(flat)
        std_v  = np.std(flat)
        p01    = np.percentile(flat, 1)
        p99    = np.percentile(flat, 99)
        print(f"  {fname:<30} {non_nan_pct:>9.1f}% {mean_v:>12.4f} {std_v:>12.4f} {p01:>10.4f} {p99:>10.4f}")

    # ── 5. Save wide matrices (per feature) ──────────────────────────────────
    section("5. SAVING WIDE FEATURE MATRICES")
    print(f"  Output dir: {FEATURES_DIR}")
    saved_wide = []
    for fname, fmat in feature_dict.items():
        out_path = os.path.join(FEATURES_DIR, f"{fname}.parquet")
        fmat.to_parquet(out_path, compression="snappy")
        size_mb = os.path.getsize(out_path) / 1e6
        print(f"  ✓ {fname:<35} → {size_mb:.1f} MB")
        saved_wide.append(fname)

    # ── 6. Save long-format stacked (for ML training) ────────────────────────
    section("6. SAVING LONG-FORMAT FEATURE STORE")
    print("  Stacking features to long format (date, ticker, feature1, feature2, ...)...")
    t_stack = time.time()

    # Stack: chọn features cần thiết cho ML (bỏ raw SMA, chỉ giữ ratio)
    ML_FEATURES = [f for f in feature_dict.keys() if not f.startswith("bb_upper") and not f.startswith("bb_lower")]

    long_dfs = []
    for fname in ML_FEATURES:
        s = feature_dict[fname].stack(future_stack=True)
        s.name = fname
        long_dfs.append(s)

    long_df = pd.concat(long_dfs, axis=1)
    long_df.index.names = ["date", "ticker"]
    long_df = long_df.reset_index()

    # Chỉ giữ rows có ít nhất 1 feature không NaN
    feature_cols = [c for c in long_df.columns if c not in ("date", "ticker")]
    has_data = long_df[feature_cols].notna().any(axis=1)
    long_df  = long_df[has_data].reset_index(drop=True)

    long_out = os.path.join(FEATURES_DIR, "feature_store_long.parquet")
    long_df.to_parquet(long_out, compression="snappy", index=False)
    size_mb = os.path.getsize(long_out) / 1e6
    elapsed_stack = time.time() - t_stack
    print(f"  ✓ Long-format: {long_df.shape[0]:,} rows × {long_df.shape[1]} cols")
    print(f"  ✓ Saved: feature_store_long.parquet ({size_mb:.1f} MB) in {elapsed_stack:.1f}s")

    # ── 7. Final summary ──────────────────────────────────────────────────────
    section("7. BUILD SUMMARY")
    total_elapsed = time.time() - t0
    print(f"\n  {'Chỉ tiêu':<40} {'Giá trị':>20}")
    print(f"  {'-'*62}")
    print(f"  {'Tickers được build':<40} {len(keep_tickers):>20,}")
    print(f"  {'Tickers loại (OOS)':<40} {len(oos_tickers):>20,}")
    print(f"  {'Trading days':<40} {close.shape[0]:>20,}")
    print(f"  {'Features computed':<40} {len(feature_dict):>20,}")
    print(f"  {'Long-format rows':<40} {long_df.shape[0]:>20,}")
    print(f"  {'Long-format cols':<40} {long_df.shape[1]:>20,}")
    print(f"  {'NaN rate (long format)':<40} {long_df[feature_cols].isna().mean().mean()*100:>19.1f}%")
    print(f"  {'Total build time':<40} {total_elapsed:>19.1f}s")
    print(f"\n  Output: {FEATURES_DIR}")
    print(f"\n{SEP}")
    print("  ✅ FEATURE STORE BUILD HOÀN TẤT!")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
