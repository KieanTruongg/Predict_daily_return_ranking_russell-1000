"""
Script: scripts/07_features/pilot_features_v1.py
Purpose: Pilot kiểm tra feature store v1 trên dữ liệu thật Development (mục 7 features_v1.md).

Kiểm tra:
  1. Coverage theo feature và theo năm (mẫu số = ô membership tại T trong Development).
  2. Ô ngoài membership phải NaN; miền giá trị (RSI ∈ [0,100], volatility ≥ 0, …).
  3. Đồng nhất (1 + ret_1d) = (1 + ret_overnight)(1 + ret_intraday).
  4. Split: ret_1d tại ngày split không có bước nhảy giả như giá thô.
  5. Warm-up: mã mới vào rổ có đủ lịch sử sạch → ret_60d tính được ngay ngày đầu.
  6. Liên tục: return sạch nhưng is_consecutive_session = False (phải bằng 0).
  7. Đối chiếu số học ngẫu nhiên: tính lại từng ô bằng vòng lặp scalar độc lập với src/features/v1.py.
  8. Phân phối (percentiles) mỗi feature.

Output: outputs/reports/feature_pilot_v1/<run_id>/{summary.json, coverage_summary.csv,
        coverage_by_year.csv, numerical_checks.csv, distribution_summary.csv}
"""
import json
import math
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.masks import load_layer1_mask
from src.data.matrix_loader import load_bar_quality_mask, load_matrix
from src.models.feature_sets import FEATURES_V1
from src.utils.config import load_config

FEAT_DIR = PROJECT_ROOT / "data" / "processed" / "features"
N_SAMPLES = 40
TOL = 1e-4   # feature lưu float32 → sai số tương đối ~1e-7; dùng tolerance tương đối 1e-4


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def load_feature(name, index, columns):
    f = pd.read_parquet(FEAT_DIR / f"{name}.parquet")
    f.index = pd.to_datetime(f.index)
    assert f.index.equals(index) and f.columns.equals(columns), f"{name}: lệch trục với matrices"
    return f.to_numpy(dtype=np.float64)


# ----------------------------------------------------------------- tham chiếu scalar độc lập

def _ok(x):
    return x is not None and math.isfinite(x) and x > 0


def ref_value(name, t, c, A):
    """Tính lại feature tại (t, c) bằng vòng lặp thuần Python trên ma trận đã làm sạch."""
    P, O, H, L, C, V, AV = (A[k][:, c] for k in ("adj_close", "adj_open", "adj_high", "adj_low",
                                                 "close", "volume", "adj_volume"))
    def price(i):
        return P[i] if i >= 0 and _ok(P[i]) else None

    def rets(n):                         # n return kết thúc tại t
        out = []
        for i in range(t - n + 1, t + 1):
            a, b = price(i - 1), price(i)
            if a is None or b is None:
                return None
            out.append(b / a - 1)
        return out

    if name in ("ret_1d", "ret_5d", "ret_20d", "ret_60d"):
        w = int(name[4:-1])
        if any(price(i) is None for i in range(t - w, t + 1)):
            return math.nan
        return price(t) / price(t - w) - 1
    if name == "mom_12m_skip_1m":
        if any(price(i) is None for i in range(t - 252, t - 20)):
            return math.nan
        return price(t - 21) / price(t - 252) - 1
    if name in ("vol_realized_20d", "vol_realized_60d"):
        r = rets(int(name.split("_")[2][:-1]))
        if r is None:
            return math.nan
        m = sum(r) / len(r)
        return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
    if name == "downside_deviation_20d":
        r = rets(20)
        return math.nan if r is None else math.sqrt(sum(min(x, 0) ** 2 for x in r) / 20)
    if name == "vol_parkinson_20d":
        s = 0.0
        for i in range(t - 19, t + 1):
            if i < 0 or not (_ok(H[i]) and _ok(L[i])) or H[i] < L[i]:
                return math.nan
            s += math.log(H[i] / L[i]) ** 2
        return math.sqrt(s / 20 / (4 * math.log(2)))
    if name in ("amihud_illiq_20d", "log_dollar_volume_20d"):
        dv = []
        for i in range(t - 19, t + 1):
            if i < 0 or not (_ok(C[i]) and _ok(V[i])):
                return math.nan
            dv.append(C[i] * V[i])
        if name == "log_dollar_volume_20d":
            return math.log1p(sum(dv) / 20)
        r = rets(20)
        return math.nan if r is None else 1e6 * sum(abs(x) / d for x, d in zip(r, dv)) / 20
    if name == "volume_ratio_5_20":
        v = [AV[i] if i >= 0 and _ok(AV[i]) else None for i in range(t - 19, t + 1)]
        if any(x is None for x in v):
            return math.nan
        return (sum(v[-5:]) / 5) / (sum(v) / 20)
    if name == "ret_intraday":
        return P[t] / O[t] - 1 if _ok(P[t]) and _ok(O[t]) else math.nan
    if name == "ret_overnight":
        return O[t] / P[t - 1] - 1 if t > 0 and _ok(O[t]) and _ok(P[t - 1]) else math.nan
    if name == "bollinger_pct_b_20d":
        w = [price(i) for i in range(t - 19, t + 1)]
        if any(x is None for x in w):
            return math.nan
        m = sum(w) / 20
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
        return math.nan if sd <= 1e-10 * m / 4 else (w[-1] - (m - 2 * sd)) / (4 * sd)
    if name == "rsi_14d":
        run, gl, ag, al = 0, [], None, None
        for i in range(1, t + 1):
            a, b = price(i - 1), price(i)
            if a is None or b is None:
                run, gl, ag, al = 0, [], None, None
                continue
            g, l = max(b - a, 0.0), max(a - b, 0.0)
            run += 1
            if run <= 14:
                gl.append((g, l))
                if run == 14:
                    ag, al = sum(x for x, _ in gl) / 14, sum(y for _, y in gl) / 14
            else:
                ag, al = (13 * ag + g) / 14, (13 * al + l) / 14
        if run < 14:
            return math.nan
        if ag == 0 and al == 0:
            return 50.0
        if al == 0:
            return 100.0
        return 100 - 100 / (1 + ag / al)
    raise KeyError(name)


def main():
    t0 = time.time()
    cfg = load_config()
    kw = dict(dev_only=True, include_warmup=True, config=cfg)
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{git_commit()}"
    out_dir = PROJECT_ROOT / "outputs" / "reports" / "feature_pilot_v1" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((FEAT_DIR / "manifest_v1.json").read_text(encoding="utf-8"))
    strict = "strict" in manifest.get("membership_mask", "")

    member_df = load_layer1_mask(strict=strict, **kw)
    idx, cols = member_df.index, member_df.columns
    member = member_df.to_numpy().astype(bool)
    dev = np.asarray(idx >= cfg.dev_start_date)
    years = idx.year.to_numpy()
    summary = {"run_id": run_id, "features_manifest_commit": manifest.get("git_commit"),
               "membership_mask": manifest.get("membership_mask"), "checks": {}}

    # ---- 1-2. coverage, ngoài membership, miền giá trị, phân phối
    cov_rows, year_rows, dist_rows = [], [], []
    domain = {"rsi_14d": (0, 100), "vol_realized_20d": (0, None), "vol_realized_60d": (0, None),
              "vol_parkinson_20d": (0, None), "downside_deviation_20d": (0, None),
              "amihud_illiq_20d": (0, None), "volume_ratio_5_20": (0, None), "log_dollar_volume_20d": (0, None)}
    md = member & dev[:, None]
    for name in FEATURES_V1:
        x = load_feature(name, idx, cols)
        fin = np.isfinite(x)
        lo, hi = domain.get(name, (None, None))
        vals = x[md & fin]
        cov_rows.append({
            "feature": name, "dev_member_cells": int(md.sum()), "dev_valid": int((md & fin).sum()),
            "coverage": (md & fin).sum() / md.sum(), "non_nan_outside_membership": int((fin & ~member).sum()),
            "inf_cells": int(np.isinf(x).sum()),
            "below_domain": int((vals < lo).sum()) if lo is not None else 0,
            "above_domain": int((vals > hi).sum()) if hi is not None else 0,
        })
        for y in np.unique(years[dev]):
            r = md & (years[:, None] == y)
            year_rows.append({"feature": name, "year": int(y), "coverage": (r & fin).sum() / max(r.sum(), 1)})
        q = np.percentile(vals, [0.1, 1, 5, 25, 50, 75, 95, 99, 99.9])
        dist_rows.append({"feature": name, "mean": vals.mean(), "std": vals.std(),
                          **{f"p{p}": v for p, v in zip([0.1, 1, 5, 25, 50, 75, 95, 99, 99.9], q)}})
        del x, fin, vals
    cov = pd.DataFrame(cov_rows)
    cov.to_csv(out_dir / "coverage_summary.csv", index=False)
    pd.DataFrame(year_rows).pivot(index="year", columns="feature", values="coverage").to_csv(out_dir / "coverage_by_year.csv")
    pd.DataFrame(dist_rows).to_csv(out_dir / "distribution_summary.csv", index=False)
    print(cov[["feature", "coverage", "non_nan_outside_membership", "inf_cells", "below_domain", "above_domain"]]
          .to_string(index=False, formatters={"coverage": "{:.2%}".format}))
    summary["checks"]["outside_membership_non_nan"] = int(cov["non_nan_outside_membership"].sum())
    summary["checks"]["domain_violations"] = int(cov["below_domain"].sum() + cov["above_domain"].sum())
    summary["checks"]["inf_cells"] = int(cov["inf_cells"].sum())

    # ---- 3. đồng nhất ret_1d = overnight ∘ intraday
    r1, on, intra = (load_feature(n, idx, cols) for n in ("ret_1d", "ret_overnight", "ret_intraday"))
    ok = np.isfinite(r1) & np.isfinite(on) & np.isfinite(intra)
    err = np.abs((1 + r1[ok]) - (1 + on[ok]) * (1 + intra[ok]))
    summary["checks"]["identity_ret1d"] = {"cells": int(ok.sum()), "max_abs_err": float(err.max()),
                                           "cells_err_gt_1e-5": int((err > 1e-5).sum())}
    print(f"\n[3] identity ret_1d: {ok.sum():,} ô, max |err| = {err.max():.2e}")
    del on, intra, ok, err

    # ---- 4. split
    csf = load_matrix("cumulative_split_factor", **kw).to_numpy()
    close = load_matrix("close", **kw).to_numpy()
    split_day = np.zeros_like(member)
    split_day[1:] = np.isfinite(csf[1:]) & np.isfinite(csf[:-1]) & (np.abs(csf[1:] / csf[:-1] - 1) > 1e-9)
    raw_r = np.full_like(close, np.nan); raw_r[1:] = close[1:] / close[:-1] - 1
    s = split_day & np.isfinite(r1)
    summary["checks"]["split_days"] = {
        "cells_with_ret_1d": int(s.sum()),
        "median_abs_ret_1d": float(np.median(np.abs(r1[s]))) if s.any() else None,
        "median_abs_raw_return": float(np.nanmedian(np.abs(raw_r[s]))) if s.any() else None,
        "ret_1d_abs_gt_30pct": int((np.abs(r1[s]) > 0.3).sum()),
        "raw_abs_gt_30pct": int((np.abs(raw_r[s]) > 0.3).sum()),
    }
    print(f"[4] split days: {summary['checks']['split_days']}")

    # 4b. hệ số split đổi nhưng giá thô không nhảy tương ứng → bước nhảy giả trong giá điều chỉnh
    label = load_matrix("valid_label_mask", **kw).fillna(False).to_numpy().astype(bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        expected_raw = np.zeros_like(raw_r); expected_raw[1:] = np.log(csf[:-1] / csf[1:])
        mismatch = np.abs(np.log1p(raw_r) - expected_raw)
    sus = split_day & dev[:, None] & np.isfinite(r1) & (np.abs(np.log1p(r1)) > np.log(1.3)) & (mismatch > np.log(1.3))
    prev_label = np.zeros_like(label); prev_label[1:] = label[:-1]
    sus_rows = [{"date": idx[t].date(), "canonical_sid": cols[c], "adj_ret_1d": r1[t, c], "raw_return": raw_r[t, c],
                 "split_factor_prev": csf[t - 1, c], "split_factor": csf[t, c],
                 "label_at_prev_day_contaminated": bool(prev_label[t, c])} for t, c in np.argwhere(sus)]
    pd.DataFrame(sus_rows).to_csv(out_dir / "suspicious_split_adjustments.csv", index=False)
    summary["checks"]["suspicious_split_adjustments"] = {
        "cells": len(sus_rows), "contaminated_labels": int(sum(r["label_at_prev_day_contaminated"] for r in sus_rows))}
    print(f"[4b] split nghi vấn: {summary['checks']['suspicious_split_adjustments']}")
    del csf, close, raw_r, split_day, s, label, prev_label, sus, mismatch, expected_raw

    # 4c. open/high/low lệch close cùng phiên > 3 lần (giá trị giả kiểu 0.01 / 999.99)
    q0 = load_bar_quality_mask(**kw).to_numpy()
    ohlc = {k: load_matrix(k, **kw).to_numpy() for k in ("adj_open", "adj_high", "adj_low", "adj_close")}
    with np.errstate(divide="ignore", invalid="ignore"):
        far = {k: q0 & dev[:, None] & (np.abs(np.log(ohlc[k] / ohlc["adj_close"])) > np.log(3))
               for k in ("adj_open", "adj_high", "adj_low")}
    any_far = far["adj_open"] | far["adj_high"] | far["adj_low"]
    pd.DataFrame([{"date": idx[t].date(), "canonical_sid": cols[c],
                   **{k[4:]: ohlc[k][t, c] for k in ohlc}} for t, c in np.argwhere(any_far)]
                 ).to_csv(out_dir / "ohlc_outlier_bars.csv", index=False)
    summary["checks"]["ohlc_outlier_bars"] = {"bars": int(any_far.sum()),
                                              **{k[4:]: int(v.sum()) for k, v in far.items()}}
    print(f"[4c] bar có open/high/low lệch close > 3x: {summary['checks']['ohlc_outlier_bars']}")
    del q0, ohlc, far, any_far

    # ---- 5. warm-up khi vào rổ
    quality = load_bar_quality_mask(**kw).to_numpy()
    r60 = load_feature("ret_60d", idx, cols)
    entry = np.zeros_like(member); entry[1:] = member[1:] & ~member[:-1]
    entry &= dev[:, None] & (np.asarray(idx > pd.Timestamp(cfg.dev_start_date) + pd.Timedelta(days=5))[:, None])
    clean61 = pd.DataFrame(quality.astype(np.float32)).rolling(61, min_periods=61).sum().to_numpy() == 61
    e = entry & clean61
    summary["checks"]["entry_day_warmup"] = {"entries_with_61_clean_bars": int(e.sum()),
                                             "ret_60d_valid_on_entry": int((e & np.isfinite(r60)).sum())}
    print(f"[5] entry warm-up: {summary['checks']['entry_day_warmup']}")
    del r60, entry, clean61, e

    # ---- 6. liên tục
    consec = load_matrix("is_consecutive_session", **kw).fillna(False).to_numpy().astype(bool)
    summary["checks"]["finite_ret_1d_but_not_consecutive"] = int((np.isfinite(r1) & ~consec).sum())
    print(f"[6] ret_1d hữu hạn nhưng is_consecutive_session=False: {summary['checks']['finite_ret_1d_but_not_consecutive']}")
    del consec, r1

    # ---- 7. đối chiếu số học ngẫu nhiên
    A = {}
    for k in ("adj_close", "adj_open", "adj_high", "adj_low", "close", "volume", "adj_volume"):
        A[k] = load_matrix(k, **kw).to_numpy().astype(np.float64)
        A[k][~quality] = np.nan
    rng = np.random.default_rng(20261105)
    rows = []
    for name in FEATURES_V1:
        x = load_feature(name, idx, cols)
        cand_valid = np.argwhere(md & np.isfinite(x))
        cand_nan = np.argwhere(md & ~np.isfinite(x))
        picks = [("valid", p) for p in cand_valid[rng.choice(len(cand_valid), N_SAMPLES, replace=False)]]
        if len(cand_nan):
            picks += [("nan", p) for p in cand_nan[rng.choice(len(cand_nan), min(10, len(cand_nan)), replace=False)]]
        for kind, (t, c) in picks:
            exp = ref_value(name, int(t), int(c), A)
            act = float(x[t, c])
            both_nan = math.isnan(exp) and math.isnan(act)
            abs_err = 0.0 if both_nan else abs(exp - act)
            passed = both_nan or (not math.isnan(exp) and abs_err <= TOL * max(1.0, abs(exp)))
            rows.append({"run_id": run_id, "feature": name, "date": idx[t].date(), "canonical_sid": cols[c],
                         "case_id": kind, "expected": exp, "actual": act, "absolute_error": abs_err,
                         "tolerance": TOL * max(1.0, abs(exp)) if not math.isnan(exp) else 0.0,
                         "status": "pass" if passed else "fail"})
        del x
    checks = pd.DataFrame(rows)
    checks.to_csv(out_dir / "numerical_checks.csv", index=False)
    by_feat = checks.groupby("feature")["status"].apply(lambda s: (s == "pass").mean())
    summary["checks"]["numerical"] = {"cells": len(checks), "fails": int((checks["status"] == "fail").sum())}
    print(f"\n[7] numerical checks: {len(checks)} ô, fail = {summary['checks']['numerical']['fails']}")
    if summary["checks"]["numerical"]["fails"]:
        print(checks[checks["status"] == "fail"].head(20).to_string(index=False))
    print(by_feat[by_feat < 1].to_string() if (by_feat < 1).any() else "    mọi feature pass 100%")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n✓ Pilot xong → {out_dir} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
