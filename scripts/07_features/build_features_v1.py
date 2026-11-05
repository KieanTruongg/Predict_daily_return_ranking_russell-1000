"""
Script: scripts/07_features/build_features_v1.py
Purpose: Sinh feature store v1 (16 features, docs/specifications/features_v1.md) dạng ma trận 2D.

Phạm vi: Warm-up + Development (1998-01-02 → 2023-12-29). OOS KHÔNG được nạp; khi tới Phase 5
mới chạy lại với quyền OOS. Mọi feature chỉ nhìn về quá khứ nên các hàng Development không
cần dữ liệu OOS.

Input  : data/processed/matrices/*.parquet (qua src.data, đã chặn OOS)
Output : data/processed/features/<feature>.parquet  (float32, ngày × canonical_sid, cùng trục matrices)
         data/processed/features/manifest_v1.json    (commit, phạm vi ngày, mask, coverage)

Ví dụ:
  python scripts/07_features/build_features_v1.py
  python scripts/07_features/build_features_v1.py --features ret_1d rsi_14d
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.masks import load_layer1_mask
from src.data.matrix_loader import load_bar_quality_mask, load_matrix
from src.features.v1 import features_v1
from src.utils.config import load_config

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "features"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser(description="Build feature store v1 (Warm-up + Development)")
    ap.add_argument("--features", nargs="+", help="chỉ build các feature này (mặc định: cả 16)")
    ap.add_argument("--membership", choices=["resolved", "strict"], default="resolved",
                    help="mask membership áp tại ngày đầu ra T (mặc định resolved = cùng gốc với valid_data_mask)")
    args = ap.parse_args()
    t0 = time.time()
    cfg = load_config()
    kw = dict(dev_only=True, include_warmup=True, config=cfg)

    feats = features_v1()
    if args.features:
        unknown = set(args.features) - {f.name for f in feats}
        if unknown:
            sys.exit(f"❌ Feature không có trong v1: {sorted(unknown)}")
        feats = [f for f in feats if f.name in args.features]
    # nhóm theo input để mỗi ma trận chỉ nạp một lần
    feats.sort(key=lambda f: f.inputs)

    quality = load_bar_quality_mask(**kw)
    member = load_layer1_mask(strict=args.membership == "strict", **kw)
    dev_rows = member.index >= cfg.dev_start_date
    member_cells = int(member.to_numpy()[dev_rows].sum())
    print(f"✓ Trục: {member.shape[0]:,} phiên × {member.shape[1]:,} SID | "
          f"{member.index[0].date()} → {member.index[-1].date()} | membership={args.membership}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache, stats = {}, {}
    for f in feats:
        t1 = time.time()
        for name in list(cache):
            if name not in f.inputs:
                del cache[name]
        for name in f.inputs:
            if name not in cache:
                cache[name] = load_matrix(name, **kw)
        out = f.compute({k: cache[k] for k in f.inputs}, bar_quality_mask=quality, membership_mask=member)
        out = out.astype(np.float32)
        out.to_parquet(OUT_DIR / f"{f.name}.parquet", compression="snappy")

        vals = out.to_numpy()[dev_rows]
        valid = int(np.isfinite(vals).sum())
        stats[f.name] = {"inputs": list(f.inputs), "window": f.window, "dev_valid_cells": valid,
                         "dev_member_cells": member_cells, "dev_coverage": round(valid / member_cells, 6)}
        print(f"  {f.name:24s} coverage Dev {valid / member_cells:6.2%} ({time.time() - t1:5.1f}s)")
        del out, vals

    manifest_path = OUT_DIR / "manifest_v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest.update({
        "spec": "docs/specifications/features_v1.md",
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "date_range": [str(member.index[0].date()), str(member.index[-1].date())],
        "oos_included": False,
        "membership_mask": "strict_membership_mask" if args.membership == "strict" else "membership_mask (resolved)",
        "input_hygiene": "bar_quality_mask (adj_close > 0, not bad data, not spin-off)",
        "dtype": "float32",
    })
    manifest.setdefault("features", {}).update(stats)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ {len(feats)} feature → {OUT_DIR} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
