"""
Script: scripts/08_train/run_walk_forward.py
Purpose: Phase 3 — Walk-Forward CV cho baseline models trên kho ma trận 2D (chỉ Development).

Pipeline:
  1. Nạp ma trận Warm-up + Development qua src.data (OOS bị khoá bởi matrix_loader):
     adj_close, bar_quality_mask, valid_data_mask (tập dự đoán tại T),
     valid_label_mask, target_next_return.
  2. Nạp các feature v1 đã có tại data/processed/features/<tên>.parquet (thiếu thì bỏ qua)
     + tín hiệu baseline reversal_5d tính trực tiếp từ adj_close.
  3. build_panel: rank feature theo ngày trong valid_data_mask − 0.5, nhãn target_next_rank.
  4. make_folds: train 5 năm rolling → val 1 năm (2010…2023), embargo 5 phiên.
  5. run_walk_forward cho từng model → lưu predictions + bảng metrics.

Ví dụ:
  python scripts/08_train/run_walk_forward.py
  python scripts/08_train/run_walk_forward.py --models factor:reversal_5d ridge --expanding

Output:
  data/processed/predictions/{model}.parquet       (date, canonical_sid, fold, score, target_next_return)
  outputs/reports/walk_forward/wf_summary.csv       (1 dòng / model, toàn bộ kỳ val)
  outputs/reports/walk_forward/wf_folds_{model}.csv (metrics từng fold)
  outputs/reports/walk_forward/wf_ic_by_year.csv    (Mean IC theo năm × model)
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.masks import load_layer2_mask, load_layer3_mask
from src.data.matrix_loader import load_bar_quality_mask, load_matrix
from src.models.baselines import get_model_factory
from src.models.feature_sets import FEATURES_V1, available_features, load_feature_matrices, reversal_5d
from src.models.panel import build_panel
from src.models.walk_forward import make_folds, run_walk_forward
from src.utils.config import load_config

PRED_DIR = PROJECT_ROOT / "data" / "processed" / "predictions"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports" / "walk_forward"
BASELINE_SIGNALS = ["reversal_5d"]
LEARNED = {"ridge", "ic_sign_ew"}

SEP = "=" * 80
DEFAULT_MODELS = ["factor:reversal_5d", "ic_sign_ew", "ridge"]


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def load_panel(cfg):
    kw = dict(dev_only=True, include_warmup=True, config=cfg)
    adj_close = load_matrix("adj_close", **kw)
    bar_quality = load_bar_quality_mask(**kw)
    universe = load_layer2_mask(**kw)
    label = load_layer3_mask(**kw)
    target = load_matrix("target_next_return", **kw)
    print(f"  ✓ Ma trận: {adj_close.shape[0]:,} phiên × {adj_close.shape[1]:,} SID | "
          f"{adj_close.index[0].date()} → {adj_close.index[-1].date()}")

    names = available_features(FEATURES_V1)
    missing = [n for n in FEATURES_V1 if n not in names]
    print(f"  ✓ Feature v1 có sẵn: {len(names)}/{len(FEATURES_V1)} {names}")
    if missing:
        print(f"  ⚠️ Chưa có trong data/processed/features: {missing}")
    feats = load_feature_matrices(names, adj_close.index, adj_close.columns)
    feats["reversal_5d"] = reversal_5d(adj_close, bar_quality)
    del adj_close, bar_quality

    panel, _ = build_panel(feats, target, label, universe, start=cfg.dev_start_date)
    print(f"  ✓ Panel: {len(panel):,} dòng (date, SID) có nhãn hợp lệ | "
          f"{panel['date'].nunique():,} ngày | TB {len(panel) / max(panel['date'].nunique(), 1):.0f} mã/ngày")
    return panel, names


def main():
    ap = argparse.ArgumentParser(description="Walk-forward CV cho baseline models (Development)")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                    help="ic_sign_ew | ridge | factor:[-]<cột> (mặc định: %(default)s)")
    ap.add_argument("--first-val-year", type=int, default=2010)
    ap.add_argument("--last-val-year", type=int, default=2023)
    ap.add_argument("--train-years", type=int, default=5)
    ap.add_argument("--expanding", action="store_true", help="train từ đầu Development thay vì rolling")
    ap.add_argument("--embargo-days", type=int, default=5)
    args = ap.parse_args()
    t0 = time.time()
    cfg = load_config()

    section("1. LOAD MATRICES + BUILD PANEL")
    panel, features = load_panel(cfg)

    section("2. WALK-FORWARD FOLDS")
    folds = make_folds(panel["date"], args.first_val_year, args.last_val_year,
                       args.train_years, args.expanding, args.embargo_days)
    for f in folds:
        print(f"  {f}")

    section("3. TRAIN / PREDICT")
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summaries, yearly = [], {}
    for name in args.models:
        if name in LEARNED and not features:
            print(f"  ⚠️ Bỏ qua {name}: chưa có feature v1 nào trong data/processed/features")
            continue
        res = run_walk_forward(panel, get_model_factory(name), features, folds, model_name=name)
        safe = name.replace(":", "_")
        res.predictions.to_parquet(PRED_DIR / f"{safe}.parquet", index=False)
        res.fold_metrics.to_csv(REPORT_DIR / f"wf_folds_{safe}.csv", index=False)
        summaries.append(res.overall("target_next_return"))
        yearly[name] = res.ic_by_year()["mean_ic"]

    if not summaries:
        sys.exit("❌ Không có model nào chạy được.")

    section("4. SUMMARY (toàn bộ các kỳ validation)")
    summary = pd.DataFrame(summaries).set_index("model")
    summary.to_csv(REPORT_DIR / "wf_summary.csv")
    print(summary[["mean_ic", "ic_std", "icir", "ic_tstat", "positive_ic_ratio",
                   "spread_mean_daily", "spread_ann_sharpe", "days_evaluated"]].round(5).to_string())

    ic_year = pd.DataFrame(yearly)
    ic_year.to_csv(REPORT_DIR / "wf_ic_by_year.csv")
    print("\n  Mean Rank IC theo năm:")
    print(ic_year.round(5).to_string())
    print("\n  ⚠️ spread = top−bottom decile của lợi suất close→close, CHƯA trừ phí và chưa phải "
          "P&L thực thi (xem target_and_timing_v1.md mục 7).")
    print(f"\n  Output: {PRED_DIR}\n          {REPORT_DIR}\n  Thời gian: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
