"""
Script: scripts/07_alpha_eval/eval_benchmark_alpha.py
Purpose: T5 — Đánh giá Alpha Benchmark Reversal 5D + IC của tất cả features

Nội dung:
  1. Load close matrix + forward_returns từ in_sample
  2. Tính Reversal 5D alpha theo công thức thầy
  3. Tính daily Rank IC series → summary (Mean IC, ICIR, Positive IC %)
  4. Phân tích IC theo từng năm (Regime analysis)
  5. Tính IC nhanh cho tất cả 31 features trong feature store
  6. Lưu kết quả ra CSV + PNG
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore")

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.metrics.information import compute_daily_ic_series, calculate_ic_summary

IN_SAMPLE_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "in_sample")
FEATURES_DIR  = os.path.join(PROJECT_ROOT, "data", "processed", "features")
OUT_DIR       = os.path.join(PROJECT_ROOT, "docs", "Data report", "eda_figures")
os.makedirs(OUT_DIR, exist_ok=True)

SEP = "=" * 80

def section(title): print(f"\n{SEP}\n  {title}\n{SEP}")

# ─────────────────────────────────────────────────────────────────────────────
def load_matrix(base_dir, name):
    df = pd.read_parquet(os.path.join(base_dir, f"{name}.parquet"))
    df.index = pd.to_datetime(df.index)
    return df

def cs_winsorize(df, lo=0.01, hi=0.99):
    q_lo = df.quantile(lo, axis=1)
    q_hi = df.quantile(hi, axis=1)
    return df.clip(lower=q_lo, upper=q_hi, axis=0)

def cs_demean(df):
    return df.sub(df.mean(axis=1), axis=0)

def cs_rank(df):
    return df.rank(axis=1, pct=True, na_option="keep")

# ─────────────────────────────────────────────────────────────────────────────
def compute_ic_vectorized(signal_matrix: pd.DataFrame,
                          fwd_matrix: pd.DataFrame,
                          method: str = "spearman") -> pd.Series:
    """
    Vectorized Rank IC: tính corr cross-sectional cho mỗi ngày.
    Nhanh hơn row-by-row loop ~20x nhờ dùng cs_rank trước rồi pearson corr.
    """
    if method == "spearman":
        sig_r = cs_rank(signal_matrix)
        fwd_r = cs_rank(fwd_matrix)
    else:
        sig_r = signal_matrix
        fwd_r = fwd_matrix

    # Pearson corr row-wise (đã rank → equivalent to spearman)
    # Tính manually: corr = cov(x,y) / (std_x * std_y)
    sig_dm = sig_r.sub(sig_r.mean(axis=1), axis=0)
    fwd_dm = fwd_r.sub(fwd_r.mean(axis=1), axis=0)

    n_valid = (~signal_matrix.isna() & ~fwd_matrix.isna()).sum(axis=1)
    cov     = (sig_dm * fwd_dm).sum(axis=1, skipna=True) / n_valid.clip(lower=1)
    std_sig = sig_r.std(axis=1, skipna=True)
    std_fwd = fwd_r.std(axis=1, skipna=True)

    ic = cov / (std_sig * std_fwd).replace(0, np.nan)
    ic = ic.where(n_valid >= 10)   # min 10 tickers per day
    return ic

def ic_summary_str(ic: pd.Series, label: str) -> dict:
    c = ic.dropna()
    if len(c) < 2:
        return {}
    mean_ic = c.mean()
    std_ic  = c.std()
    icir    = mean_ic / std_ic if std_ic > 1e-8 else 0.0
    pos_pct = (c > 0).mean() * 100
    t_stat, p_val = stats.ttest_1samp(c, 0)
    return {
        "feature": label,
        "mean_ic": round(mean_ic, 5),
        "ic_std":  round(std_ic, 5),
        "icir":    round(icir, 4),
        "positive_ic_pct": round(pos_pct, 1),
        "t_stat":  round(t_stat, 3),
        "p_value": round(p_val, 6),
        "n_days":  len(c),
    }

# ─────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print(SEP)
    print("  T5: ALPHA BENCHMARK EVALUATION — Reversal 5D + All Features IC")
    print(SEP)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    section("1. LOADING DATA")
    print("  Loading close matrix...")
    close = load_matrix(IN_SAMPLE_DIR, "close")
    print(f"  ✓ close: {close.shape}")

    print("  Loading forward_returns matrix...")
    fwd = load_matrix(IN_SAMPLE_DIR, "forward_returns")
    print(f"  ✓ forward_returns: {fwd.shape}")

    # Filter chỉ giữ in-sample tickers (bỏ OOS)
    nan_pct = close.isna().mean()
    keep    = nan_pct[nan_pct < 0.95].index
    close   = close[keep]
    fwd     = fwd[keep]
    print(f"  ✓ Sau filter OOS: {close.shape[1]} tickers")

    # ── 2. Reversal 5D Alpha ──────────────────────────────────────────────────
    section("2. REVERSAL 5D ALPHA — CÔNG THỨC THẦY")
    print("""
  Công thức:
    α_i = (P_{t-5} - P_{t-1}) / 5
    α_i = α_i - mean(α_i)   [CS demeaned → dollar-neutral]
  """)

    p_t5  = close.shift(5)   # P_{t-5}
    p_t1  = close.shift(1)   # P_{t-1}
    raw   = (p_t5 - p_t1) / 5.0
    alpha = cs_demean(raw)    # dollar-neutral

    print("  Tính Rank IC series (vectorized)...")
    ic_rev5 = compute_ic_vectorized(alpha, fwd, method="spearman")

    summ = ic_summary_str(ic_rev5, "Reversal_5D")
    print(f"\n  {'Chỉ tiêu':<30} {'Giá trị':>15}")
    print(f"  {'-'*47}")
    print(f"  {'Mean Rank IC':<30} {summ['mean_ic']:>15.5f}")
    print(f"  {'IC Std':<30} {summ['ic_std']:>15.5f}")
    print(f"  {'ICIR':<30} {summ['icir']:>15.4f}")
    print(f"  {'Positive IC %':<30} {summ['positive_ic_pct']:>14.1f}%")
    print(f"  {'t-statistic':<30} {summ['t_stat']:>15.3f}")
    print(f"  {'p-value':<30} {summ['p_value']:>15.6f}")
    print(f"  {'N days evaluated':<30} {summ['n_days']:>15,}")

    print(f"\n  ── Nhận xét ──")
    mic = summ['mean_ic']
    if abs(mic) < 0.01:
        print(f"  Mean IC = {mic:.5f} → Rất thấp (< 0.01). Reversal 5D không mạnh trên toàn bộ 24 năm.")
    elif abs(mic) < 0.03:
        print(f"  Mean IC = {mic:.5f} → Thấp nhưng có (0.01–0.03). Cần kết hợp với features khác.")
    else:
        print(f"  Mean IC = {mic:.5f} → Khá tốt cho single-factor alpha.")
    print(f"  Positive IC % = {summ['positive_ic_pct']:.1f}% → {'Tốt (>50%)' if summ['positive_ic_pct']>50 else 'Yếu (<50%)'}")

    # ── 3. IC theo năm ────────────────────────────────────────────────────────
    section("3. RANK IC THEO TỪNG NĂM — REGIME ANALYSIS")
    ic_df = ic_rev5.to_frame("ic")
    ic_df["year"] = ic_df.index.year
    annual_ic = ic_df.groupby("year")["ic"].agg(
        mean_ic="mean", ic_std="std",
        pos_pct=lambda x: (x > 0).mean() * 100,
        n_days="count"
    ).reset_index()

    print(f"\n  {'Năm':<6} {'Mean IC':>10} {'IC Std':>10} {'Pos IC%':>10} {'Nhận xét'}")
    print(f"  {'-'*55}")
    for _, r in annual_ic.iterrows():
        flag = ""
        if r["mean_ic"] > 0.02:  flag = "🟢 STRONG"
        elif r["mean_ic"] > 0.005: flag = "🟡 WEAK"
        elif r["mean_ic"] > -0.005: flag = "⚪ NEUTRAL"
        else:                      flag = "🔴 NEGATIVE"
        print(f"  {int(r['year']):<6} {r['mean_ic']:>+10.5f} {r['ic_std']:>10.5f} {r['pos_pct']:>9.1f}% {flag}")

    # ── 4. IC tất cả features ─────────────────────────────────────────────────
    section("4. RANK IC — TẤT CẢ 31 FEATURES")
    print("  Tính IC cho từng feature trong feature store...")

    FEATURES_TO_EVAL = [
        "ret_1d", "ret_2d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ret_252d",
        "close_to_sma_20", "close_to_sma_50", "close_to_sma_200", "macd_hist_norm",
        "rsi_14", "bb_pct_b", "bb_bandwidth", "hl_spread", "close_to_high",
        "vol_ratio_5_20", "vol_zscore_20", "close_to_vwap_5", "amihud_20d",
        "realized_vol_5d", "realized_vol_20d", "realized_vol_60d",
    ]

    all_ic_results = []
    ic_series_dict = {"Reversal_5D": ic_rev5}

    for fname in FEATURES_TO_EVAL:
        fpath = os.path.join(FEATURES_DIR, f"{fname}.parquet")
        if not os.path.exists(fpath):
            print(f"  SKIP (not found): {fname}")
            continue
        feat = pd.read_parquet(fpath)
        feat.index = pd.to_datetime(feat.index)
        feat = feat[[c for c in feat.columns if c in fwd.columns]]
        common_idx = feat.index.intersection(fwd.index)
        feat = feat.loc[common_idx]
        fwd_aligned = fwd.loc[common_idx]
        ic = compute_ic_vectorized(feat, fwd_aligned, method="spearman")
        ic_series_dict[fname] = ic
        s = ic_summary_str(ic, fname)
        all_ic_results.append(s)
        print(f"  {fname:<30} Mean IC={s['mean_ic']:>+8.5f}  ICIR={s['icir']:>+7.4f}  Pos%={s['positive_ic_pct']:>5.1f}%")

    all_ic_results.insert(0, summ)  # reversal_5d first

    # Print ranked table
    ic_df_all = pd.DataFrame(all_ic_results).sort_values("mean_ic", ascending=False)
    print(f"\n  ── RANKING FEATURES BY MEAN IC (High → Low) ──")
    print(f"\n  {'Feature':<30} {'Mean IC':>10} {'ICIR':>8} {'Pos IC%':>9} {'t-stat':>8} {'p-value':>10}")
    print(f"  {'-'*79}")
    for _, r in ic_df_all.iterrows():
        sig = "***" if r["p_value"] < 0.001 else ("**" if r["p_value"] < 0.01 else ("*" if r["p_value"] < 0.05 else ""))
        print(f"  {r['feature']:<30} {r['mean_ic']:>+10.5f} {r['icir']:>+8.4f} {r['positive_ic_pct']:>8.1f}% {r['t_stat']:>+8.3f} {r['p_value']:>10.6f} {sig}")

    # ── 5. Plots ──────────────────────────────────────────────────────────────
    section("5. XUẤT BIỂU ĐỒ")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Alpha Benchmark Evaluation: Reversal 5D & Feature IC Analysis\n"
                 "Russell 1000 In-Sample (2000–2023)", fontsize=13, fontweight="bold")

    # Plot 1: IC time series (Reversal 5D)
    ax = axes[0, 0]
    ic_roll = ic_rev5.rolling(63).mean()   # 3-month rolling
    ax.fill_between(ic_rev5.index, ic_rev5.values, alpha=0.25, color="#2196F3", label="Daily IC")
    ax.plot(ic_roll.index, ic_roll.values, color="#0D47A1", lw=2, label="63-day rolling avg")
    ax.axhline(0, color="black", lw=1)
    ax.axhline(ic_rev5.mean(), color="red", ls="--", lw=1.5,
               label=f"Mean IC = {ic_rev5.mean():.4f}")
    ax.set_title(f"Reversal 5D — Daily Rank IC Series\nMean={ic_rev5.mean():.4f}, ICIR={summ['icir']:.3f}")
    ax.set_xlabel("Date"); ax.set_ylabel("Rank IC")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(4))

    # Plot 2: Annual IC bar chart (Reversal 5D)
    ax = axes[0, 1]
    colors = ["#4CAF50" if v > 0 else "#F44336" for v in annual_ic["mean_ic"]]
    ax.bar(annual_ic["year"], annual_ic["mean_ic"], color=colors, width=0.7, alpha=0.85)
    ax.axhline(0, color="black", lw=1)
    ax.axhline(ic_rev5.mean(), color="red", ls="--", lw=1.5,
               label=f"Overall Mean IC = {ic_rev5.mean():.4f}")
    ax.set_title("Reversal 5D — Annual Mean Rank IC\n🟢 Positive / 🔴 Negative")
    ax.set_xlabel("Year"); ax.set_ylabel("Mean IC")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=45)

    # Plot 3: IC distribution histogram (Reversal 5D)
    ax = axes[1, 0]
    c = ic_rev5.dropna()
    ax.hist(c, bins=80, color="#2196F3", alpha=0.75, density=True)
    x = np.linspace(c.min(), c.max(), 300)
    ax.plot(x, stats.norm.pdf(x, c.mean(), c.std()), "r-", lw=2, label="Normal fit")
    ax.axvline(0, color="black", lw=1)
    ax.axvline(c.mean(), color="red", ls="--", lw=2, label=f"Mean={c.mean():.4f}")
    ax.set_title(f"Reversal 5D — IC Distribution\nSkew={stats.skew(c):.3f}, Kurt={stats.kurtosis(c):.2f}")
    ax.set_xlabel("Rank IC"); ax.set_ylabel("Density")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Plot 4: Feature IC comparison bar chart
    ax = axes[1, 1]
    top_df = ic_df_all.head(20)
    bar_colors = ["#4CAF50" if v > 0 else "#F44336" for v in top_df["mean_ic"]]
    y_pos = range(len(top_df))
    ax.barh(list(y_pos), top_df["mean_ic"].values, color=bar_colors, alpha=0.85)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(top_df["feature"].values, fontsize=8)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Mean Rank IC")
    ax.set_title("Feature Mean IC Ranking (Top 20)\n🟢 Positive / 🔴 Negative")
    ax.grid(alpha=0.3, axis="x")

    plt.tight_layout()
    out_png = os.path.join(OUT_DIR, "t5_alpha_benchmark_ic.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Biểu đồ: {out_png}")

    # ── 6. Save results ───────────────────────────────────────────────────────
    section("6. LƯU KẾT QUẢ")
    ic_df_all.to_csv(os.path.join(OUT_DIR, "t5_feature_ic_ranking.csv"), index=False)
    annual_ic.to_csv(os.path.join(OUT_DIR, "t5_reversal5d_annual_ic.csv"), index=False)
    ic_rev5.to_frame("rank_ic").to_csv(os.path.join(OUT_DIR, "t5_reversal5d_daily_ic.csv"))
    print(f"  ✓ t5_feature_ic_ranking.csv")
    print(f"  ✓ t5_reversal5d_annual_ic.csv")
    print(f"  ✓ t5_reversal5d_daily_ic.csv")

    print(f"\n{SEP}")
    print(f"  ✅ HOÀN TẤT T5 — Total time: {time.time()-t0:.1f}s")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
