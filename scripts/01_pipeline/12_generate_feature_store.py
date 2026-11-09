# -*- coding: utf-8 -*-
"""
scripts/01_pipeline/12_generate_feature_store.py
=================================================
Generates the complete 16-feature Tier 3 Feature Store for the Development
period (2000-07-01 to 2023-12-29, 5,911 sessions x 3,711 Canonical SIDs).

Key Architecture Principles:
1. Strict OOS Freeze: Reads only historical Warm-up (1998-2000) and Development (2000-2023).
   Zero access to Out-of-Sample (2024-2026).
2. Clean Historical Warm-up: Uses bar_quality_mask to sanitize input series prior to
   rolling operations, independent of index membership.
3. Strict Output Membership: Uses strict_membership_mask applied strictly at date T
   on the output matrix. Non-member coordinates are assigned NaN.
4. Memory Efficient Pipeline: Processes feature-by-feature sequentially to ensure
   peak RAM usage stays comfortably under 1.0 GB.
5. Verifiable Storage: Stores matrices in Parquet format with float64 precision
   and generates a comprehensive feature_store_manifest.json.

Outputs:
- data/processed/features/<feature_name>.parquet (16 files)
- data/processed/features/feature_store_manifest.json
"""

import sys
import os
import gc
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import subprocess

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
    load_field_quality_mask,
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

FEATURES_DIR = ROOT_DIR / "data" / "processed" / "features"
FEATURES_DIR.mkdir(parents=True, exist_ok=True)

DEV_START_DATE = "2000-07-01"
DEV_END_DATE = "2023-12-29"

# Feature specification catalog
FEATURE_SPECS = [
    # 1. Momentum Group
    {
        "name": "ret_1d",
        "class": PriceRatioMomentumFeature,
        "kwargs": {"window": 1},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 3.2",
        "description": "1-day rolling price ratio return from adj_close",
    },
    {
        "name": "ret_5d",
        "class": PriceRatioMomentumFeature,
        "kwargs": {"window": 5},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 3.2",
        "description": "5-day rolling price ratio return from adj_close",
    },
    {
        "name": "ret_20d",
        "class": PriceRatioMomentumFeature,
        "kwargs": {"window": 20},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 3.2",
        "description": "20-day rolling price ratio return from adj_close",
    },
    {
        "name": "ret_60d",
        "class": PriceRatioMomentumFeature,
        "kwargs": {"window": 60},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 3.2",
        "description": "60-day rolling price ratio return from adj_close",
    },
    {
        "name": "mom_12m_skip_1m",
        "class": Mom12mSkip1mFeature,
        "kwargs": {"lookback": 252, "skip": 21},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 3.3",
        "description": "12-month momentum (lookback=252d) skipping recent 21d (requires 232 clean prices)",
    },
    # 2. Volatility Group
    {
        "name": "vol_realized_20d",
        "class": RealizedVolatilityFeature,
        "kwargs": {"window": 20, "return_type": "daily_return", "annualize": False},
        "inputs": ["daily_return"],
        "spec_ref": "docs/specifications/features_v1.md Section 4.1",
        "description": "20-day daily realized volatility (std ddof=1, daily unit)",
    },
    {
        "name": "vol_realized_60d",
        "class": RealizedVolatilityFeature,
        "kwargs": {"window": 60, "return_type": "daily_return", "annualize": False},
        "inputs": ["daily_return"],
        "spec_ref": "docs/specifications/features_v1.md Section 4.1",
        "description": "60-day daily realized volatility (std ddof=1, daily unit)",
    },
    {
        "name": "vol_parkinson_20d",
        "class": ParkinsonVolatilityFeature,
        "kwargs": {"window": 20},
        "inputs": ["adj_high", "adj_low"],
        "spec_ref": "docs/specifications/features_v1.md Section 4.2",
        "description": "20-day Parkinson extreme-value volatility from High/Low",
    },
    {
        "name": "downside_deviation_20d",
        "class": DownsideDeviationFeature,
        "kwargs": {"window": 20},
        "inputs": ["daily_return"],
        "spec_ref": "docs/specifications/features_v1.md Section 4.3",
        "description": "20-day downside deviation at threshold 0 (full denominator 20, daily unit)",
    },
    # 3. Liquidity and Volume Group
    {
        "name": "amihud_illiq_20d",
        "class": AmihudIlliquidityFeature,
        "kwargs": {"window": 20, "scale": 1e6},
        "inputs": ["daily_return", "close", "volume"],
        "spec_ref": "docs/specifications/features_v1.md Section 5.2",
        "description": "20-day Amihud illiquidity ratio (1e6 * mean_20(|r| / DV))",
    },
    {
        "name": "volume_ratio_5_20",
        "class": VolumeRatioFeature,
        "kwargs": {"fast_window": 5, "slow_window": 20},
        "inputs": ["adj_volume"],
        "spec_ref": "docs/specifications/features_v1.md Section 5.3",
        "description": "5-day over 20-day split-adjusted volume ratio (mean_5 / mean_20)",
    },
    {
        "name": "log_dollar_volume_20d",
        "class": LogDollarVolumeFeature,
        "kwargs": {"window": 20},
        "inputs": ["close", "volume"],
        "spec_ref": "docs/specifications/features_v1.md Section 5.4",
        "description": "20-day log dollar volume (log1p(mean_20(raw_close * raw_volume)))",
    },
    # 4. Intraday and Technical Group
    {
        "name": "ret_intraday",
        "class": IntradayReturnFeature,
        "kwargs": {},
        "inputs": ["adj_close", "adj_open"],
        "spec_ref": "docs/specifications/features_v1.md Section 6.1",
        "description": "Intraday price return (adj_close / adj_open - 1)",
    },
    {
        "name": "ret_overnight",
        "class": OvernightReturnFeature,
        "kwargs": {},
        "inputs": ["adj_close", "adj_open"],
        "spec_ref": "docs/specifications/features_v1.md Section 6.2",
        "description": "Overnight price return (adj_open[T] / adj_close[T-1] - 1)",
    },
    {
        "name": "rsi_14d",
        "class": RSIFeature,
        "kwargs": {"window": 14},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 6.3",
        "description": "14-day Wilder smoothed RSI with state reset on invalid bars",
    },
    {
        "name": "bollinger_pct_b_20d",
        "class": BollingerPctBFeature,
        "kwargs": {"window": 20, "k": 2.0},
        "inputs": ["adj_close"],
        "spec_ref": "docs/specifications/features_v1.md Section 6.4",
        "description": "20-day Bollinger Bands %B (ddof=0 for sigma, unclipped)",
    },
]


def compute_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 hash of a file."""
    import hashlib
    hasher = hashlib.sha256()
    p = Path(filepath)
    if not p.exists():
        return "FILE_NOT_FOUND"
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_git_provenance() -> dict:
    """Retrieves complete Git provenance: commit, branch, working tree dirty status."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        commit = "UNKNOWN"

    try:
        dirty_output = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        is_dirty = len(dirty_output) > 0
        dirty_list = dirty_output.splitlines() if is_dirty else []
    except Exception:
        dirty_list = []
        is_dirty = None

    return {
        "commit": commit,
        "working_tree_dirty": is_dirty,
        "dirty_files_count": len(dirty_list),
        "dirty_files": dirty_list,
    }


def generate_feature_store(features_filter: list = None):
    print("=" * 80)
    print("BẮT ĐẦU SINH TIER 3 FEATURE STORE TRÊN TẬP DEVELOPMENT (2000-07-01 ĐẾN 2023-12-29)")
    print("=" * 80)
    start_total_time = time.time()

    git_prov = get_git_provenance()
    commit_hash = git_prov['commit']
    print(f"Phiên bản Git commit hiện hành: {commit_hash}")

    # 1. Load masks across Warm-up + Development (1998-01-02 to 2023-12-29)
    print("\n1. Nạp mặt nạ kiểm soát chất lượng và rổ Russell 1000...")
    t0 = time.time()
    bar_quality_full = load_bar_quality_mask(dev_only=True, include_warmup=True)
    strict_mem_full = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
    print(f"   -> Đã nạp bar_quality_mask và strict_membership_mask trong {time.time() - t0:.2f}s. Kích thước: {bar_quality_full.shape}")

    # Cache for reusable matrices to avoid repeated disk reads
    matrix_cache = {}

    def get_matrix(name: str) -> pd.DataFrame:
        if name not in matrix_cache:
            t_load = time.time()
            matrix_cache[name] = load_matrix(name, dev_only=True, include_warmup=True)
            print(f"      [Cache] Nạp ma trận '{name}' ({matrix_cache[name].shape}) trong {time.time() - t_load:.2f}s")
        return matrix_cache[name]

    field_mask_cache = {}
    def get_field_quality_mask(field_name: str) -> pd.DataFrame:
        if field_name not in field_mask_cache:
            field_mask_cache[field_name] = load_field_quality_mask(field_name, dev_only=True, include_warmup=True)
        return field_mask_cache[field_name]

    manifest_path = FEATURES_DIR / "feature_store_manifest.json"
    manifest_features = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                old_manifest = json.load(f)
                manifest_features = old_manifest.get("features", {})
        except Exception:
            manifest_features = {}

    specs_to_run = [
        s for s in FEATURE_SPECS
        if (features_filter is None or s["name"] in features_filter)
    ]

    print(f"\n2. Bắt đầu tính toán tuần tự 16 features...")
    for idx, spec in enumerate(specs_to_run, start=1):
        feat_name = spec["name"]
        feat_cls = spec["class"]
        feat_kwargs = spec["kwargs"]
        required_inputs = spec["inputs"]

        print(f"\n[{idx:02d}/16] Đang xử lý: {feat_name}...")
        t_feat_start = time.time()

        # Prepare input data dictionary
        data_inputs = {inp_name: get_matrix(inp_name) for inp_name in required_inputs}

        # Instantiate feature object
        feature_instance = feat_cls(**feat_kwargs)

        # Prepare field quality masks for required inputs
        feat_field_masks = {inp_name: get_field_quality_mask(inp_name) for inp_name in required_inputs}

        # Compute across Warm-up + Dev with clean input warm-up and output membership mask
        computed_full = feature_instance.compute(
            data=data_inputs,
            bar_quality_mask=bar_quality_full,
            membership_mask=strict_mem_full,
            field_quality_masks=feat_field_masks,
        )

        # Slice strictly to Development period (2000-07-01 to 2023-12-29)
        dev_slice = computed_full.loc[DEV_START_DATE:DEV_END_DATE]

        # Verify output matrix dimensions
        n_sessions, n_sids = dev_slice.shape
        if n_sessions != 5911 or n_sids != 3711:
            raise ValueError(f"Feature {feat_name} có kích thước bất thường: {dev_slice.shape} (kỳ vọng 5911 x 3711)")

        # Verify no Inf values
        inf_count = int(np.isinf(dev_slice.values).sum())
        if inf_count > 0:
            raise ValueError(f"Feature {feat_name} chứa {inf_count} giá trị vô hạn (Inf)! Vi phạm hợp đồng!")

        # Verify all coordinates outside membership are NaN
        dev_mem = strict_mem_full.loc[DEV_START_DATE:DEV_END_DATE]
        outside_non_nan = int(dev_slice.values[~dev_mem.values & dev_slice.notna().values].size)
        if outside_non_nan > 0:
            raise ValueError(f"Feature {feat_name} có {outside_non_nan} giá trị khác NaN ngoài membership!")

        # Save to Parquet
        output_file = FEATURES_DIR / f"{feat_name}.parquet"
        dev_slice.to_parquet(output_file, engine="pyarrow", compression="snappy")
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        valid_cells = int(dev_slice.notna().sum().sum())
        total_cells = dev_slice.size
        mem_cells = int(dev_mem.sum().sum())
        cov_pct = (valid_cells / mem_cells) * 100.0 if mem_cells > 0 else 0.0

        t_elapsed = time.time() - t_feat_start
        print(f"      -> Hoàn tất trong {t_elapsed:.2f}s | File: {output_file.name} ({file_size_mb:.2f} MB)")
        print(f"      -> Độ phủ: Valid={valid_cells:,}/{mem_cells:,} ô ({cov_pct:.2f}% membership)")

        feat_sha256 = compute_sha256(output_file)
        manifest_features[feat_name] = {
            "name": feat_name,
            "class_name": feat_cls.__name__,
            "spec_reference": spec["spec_ref"],
            "description": spec["description"],
            "inputs_required": required_inputs,
            "date_range": {
                "start": DEV_START_DATE,
                "end": DEV_END_DATE,
                "sessions": n_sessions,
            },
            "shape": [n_sessions, n_sids],
            "dtype": str(dev_slice.dtypes.iloc[0]),
            "mask_policy": {
                "input_hygiene": "bar_quality_mask (independent from membership)",
                "output_filter": "strict_membership_mask at date T",
            },
            "metrics": {
                "total_cells": total_cells,
                "membership_cells": mem_cells,
                "valid_cells": valid_cells,
                "nan_cells": total_cells - valid_cells,
                "coverage_pct_of_membership": round(cov_pct, 4),
            },
            "file": {
                "relative_path": f"data/processed/features/{feat_name}.parquet",
                "sha256": feat_sha256,
                "size_bytes": output_file.stat().st_size,
                "size_mb": round(file_size_mb, 2),
                "compression": "snappy",
            },
        }

        # Clear local computed matrix and run GC to keep RAM footprint low
        del computed_full
        del dev_slice
        gc.collect()

    # Clear cached matrices
    matrix_cache.clear()
    gc.collect()

    # Build and save manifest with comprehensive provenance
    git_prov = get_git_provenance()
    manifest_data = {
        "manifest_version": "1.4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "CANDIDATE",
        "provenance": {
            "git_commit": git_prov["commit"],
            "working_tree_dirty": git_prov["working_tree_dirty"],
            "dirty_files_count": git_prov["dirty_files_count"],
            "generation_script": "scripts/01_pipeline/12_generate_feature_store.py",
            "generation_script_sha256": compute_sha256(Path(__file__).resolve()),
            "specs_sha256": {
                "features_v1.md": compute_sha256(ROOT_DIR / "docs" / "specifications" / "features_v1.md"),
                "target_and_timing_v1.md": compute_sha256(ROOT_DIR / "docs" / "specifications" / "target_and_timing_v1.md"),
            },
            "code_sha256": {
                "src/features/base.py": compute_sha256(ROOT_DIR / "src" / "features" / "base.py"),
                "src/data/matrix_loader.py": compute_sha256(ROOT_DIR / "src" / "data" / "matrix_loader.py"),
            },
            "input_matrices_sha256": {
                name: compute_sha256(ROOT_DIR / "data" / "processed" / "matrices" / f"{name}.parquet")
                for name in [
                    "adj_close", "open", "adj_open", "low", "adj_low", "high", "adj_high",
                    "close", "volume", "adj_volume", "daily_return",
                    "is_bad_data_period", "is_spinoff_discontinuity", "strict_membership_mask"
                ]
            },
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
        },
        "parameters": {
            "dev_start_date": DEV_START_DATE,
            "dev_end_date": DEV_END_DATE,
            "warmup_applied": "1998-01-02 to 2000-06-30",
            "oos_frozen_prohibited": "2024-01-02 to 2026-10-30 (Strictly Zero Access)",
            "universe": "Point-in-Time Russell 1000 (3,711 Canonical SIDs)",
            "precision": "float64",
        },
        "feature_count": len(manifest_features),
        "features": manifest_features,
    }

    manifest_path = FEATURES_DIR / "feature_store_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"HOÀN TẤT SINH FEATURE STORE CHO {len(specs_to_run)} FEATURES THÀNH CÔNG!")
    print(f"Tổng thời gian: {time.time() - start_total_time:.2f}s")
    print(f"Đã lưu manifest vào: {manifest_path.relative_to(ROOT_DIR)}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Tier 3 Feature Store for Development")
    parser.add_argument("--features", nargs="*", default=None, help="Optional list of feature names to compute")
    args = parser.parse_args()
    generate_feature_store(features_filter=args.features)
