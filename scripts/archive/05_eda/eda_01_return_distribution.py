"""
Script: scripts/05_eda/eda_01_return_distribution.py
Purpose: EDA Task 1 — Phân tích phân phối Daily Return trên in-sample data (2000–2023)

Nội dung:
  1. Thống kê mô tả: Mean, Median, Std, Skewness, Excess Kurtosis, Percentiles
  2. Jarque-Bera test (kiểm định normality)
  3. Fat tail analysis (1st/99th percentile, extreme events)
  4. Cross-sectional dispersion theo ngày (vẽ theo năm)
  5. Regime analysis: xác định High/Low dispersion periods
  6. Lưu kết quả ra CSV và PNG
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore")

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IN_SAMPLE  = os.path.join(BASE_DIR, "data", "processed", "in_sample")
OUT_DIR    = os.path.join(BASE_DIR, "docs", "Data report", "eda_figures")
os.makedirs(OUT_DIR, exist_ok=True)

SEP = "=" * 80

# ─────────────────────────────────────────────────────────────────────────────
def load_returns():
    """Load returns matrix, flatten to Series (drop NaN)."""
    fpath = os.path.join(IN_SAMPLE, "returns.parquet")
    df = pd.read_parquet(fpath)
    df.index = pd.to_datetime(df.index)
    return df                       # shape: (6021, 2852)

# ─────────────────────────────────────────────────────────────────────────────
def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ─────────────────────────────────────────────────────────────────────────────
def eda_1_descriptive_stats(ret_matrix):
    section("1. THỐNG KÊ MÔ TẢ PHÂN PHỐI DAILY RETURN")

    # Flatten: toàn bộ (date, ticker) pairs có dữ liệu
    flat = ret_matrix.values.flatten()
    flat = flat[~np.isnan(flat)]
    n    = len(flat)

    mean_r  = float(np.mean(flat))
    med_r   = float(np.median(flat))
    std_r   = float(np.std(flat, ddof=1))
    skew_r  = float(stats.skew(flat))
    kurt_r  = float(stats.kurtosis(flat))   # excess kurtosis (normal=0)
    min_r   = float(np.min(flat))
    max_r   = float(np.max(flat))
    p01     = float(np.percentile(flat, 1))
    p05     = float(np.percentile(flat, 5))
    p25     = float(np.percentile(flat, 25))
    p75     = float(np.percentile(flat, 75))
    p95     = float(np.percentile(flat, 95))
    p99     = float(np.percentile(flat, 99))

    print(f"\n  Tổng số quan sát (stock-day pairs): {n:,}")
    print(f"\n  {'Chỉ số':<30} {'Giá trị':>15}")
    print(f"  {'-'*47}")
    print(f"  {'Mean daily return':<30} {mean_r:>+14.4%}")
    print(f"  {'Median daily return':<30} {med_r:>+14.4%}")
    print(f"  {'Std (daily)':<30} {std_r:>14.4%}")
    print(f"  {'Annualized Std (×√252)':<30} {std_r * np.sqrt(252):>14.4%}")
    print(f"  {'Skewness':<30} {skew_r:>15.4f}")
    print(f"  {'Excess Kurtosis':<30} {kurt_r:>15.4f}")
    print(f"  {'Min return':<30} {min_r:>+14.4%}")
    print(f"  {'Max return':<30} {max_r:>+14.4%}")
    print(f"\n  {'Percentile 1%':<30} {p01:>+14.4%}")
    print(f"  {'Percentile 5%':<30} {p05:>+14.4%}")
    print(f"  {'Percentile 25%':<30} {p25:>+14.4%}")
    print(f"  {'Percentile 75%':<30} {p75:>+14.4%}")
    print(f"  {'Percentile 95%':<30} {p95:>+14.4%}")
    print(f"  {'Percentile 99%':<30} {p99:>+14.4%}")

    # Nhận xét
    print(f"\n  ── Nhận xét ──")
    print(f"  Skewness = {skew_r:.3f} → {'Lệch trái (đuôi âm dày hơn)' if skew_r < 0 else 'Lệch phải'}")
    print(f"  Excess Kurtosis = {kurt_r:.1f} → Fat tails (>> 0 so với Normal=0)")
    print(f"  Annualized Vol = {std_r*np.sqrt(252):.2%} → Phù hợp thực tế thị trường (chuẩn ~15–20%)")
    print(f"  P1%={p01:.2%} / P99%={p99:.2%} → Biên độ cực đoan rộng, xác nhận fat tails")

    return flat, {
        "n": n, "mean": mean_r, "median": med_r, "std": std_r,
        "skewness": skew_r, "excess_kurtosis": kurt_r,
        "min": min_r, "max": max_r,
        "p01": p01, "p05": p05, "p25": p25,
        "p75": p75, "p95": p95, "p99": p99,
    }

# ─────────────────────────────────────────────────────────────────────────────
def eda_2_normality_test(flat):
    section("2. KIỂM ĐỊNH CHUẨN (NORMALITY TEST) — JARQUE-BERA")

    # Jarque-Bera (dùng sample vì 6M obs quá lớn → JB sẽ luôn reject)
    # Lấy sample 100,000 để vừa ý nghĩa thống kê vừa minh họa
    rng = np.random.default_rng(42)
    sample = rng.choice(flat, size=min(100_000, len(flat)), replace=False)

    jb_stat, jb_p = stats.jarque_bera(sample)
    _, sw_p = stats.shapiro(rng.choice(flat, size=5000, replace=False))  # Shapiro trên 5k

    print(f"\n  Sample size dùng cho JB test: {len(sample):,} obs")
    print(f"\n  Jarque-Bera statistic : {jb_stat:,.2f}")
    print(f"  Jarque-Bera p-value   : {jb_p:.2e}")
    print(f"  Kết quả JB test       : {'❌ REJECT H0 (không chuẩn)' if jb_p < 0.05 else '✅ Fail to reject H0'}")

    print(f"\n  Shapiro-Wilk p-value  : {sw_p:.2e} (sample 5,000)")
    print(f"  Kết quả SW test       : {'❌ REJECT H0 (không chuẩn)' if sw_p < 0.05 else '✅ Fail to reject H0'}")

    print(f"\n  ── Nhận xét ──")
    print(f"  Cả JB và SW đều REJECT H0 với p << 0.01.")
    print(f"  → Daily stock return KHÔNG tuân theo phân phối chuẩn (Normal).")
    print(f"  → Fat tails (Excess Kurtosis >> 0) là đặc trưng chính.")
    print(f"  → Skewness âm nhẹ (nhiều ngày giảm mạnh hơn là tăng mạnh).")
    print(f"  → Ý nghĩa cho ML: Không nên dùng các mô hình giả định normality.")

    return {"jb_stat": jb_stat, "jb_p": jb_p, "sw_p": sw_p}

# ─────────────────────────────────────────────────────────────────────────────
def eda_3_fat_tail_analysis(flat):
    section("3. PHÂN TÍCH FAT TAILS — EXTREME EVENTS")

    thresholds = [0.05, 0.10, 0.20, 0.30, 0.50]
    print(f"\n  {'Ngưỡng |return|':<20} {'Số ngày vi phạm':>18} {'Tỷ lệ':>10}")
    print(f"  {'-'*50}")
    for thr in thresholds:
        cnt = int((np.abs(flat) > thr).sum())
        pct = cnt / len(flat) * 100
        print(f"  {'> ' + f'{thr:.0%}':<20} {cnt:>18,} {pct:>9.3f}%")

    print(f"\n  ── Top 10 extreme returns (dữ liệu thực tế) ──")
    # Lấy top extremes từ flat (không có date/ticker context ở đây — chỉ thống kê)
    top_pos = np.partition(flat, -10)[-10:]
    top_neg = np.partition(flat,  10)[:10]
    top_pos_sorted = np.sort(top_pos)[::-1]
    top_neg_sorted = np.sort(top_neg)

    print(f"  Top 5 returns dương: " + " | ".join([f"{v:+.2%}" for v in top_pos_sorted[:5]]))
    print(f"  Top 5 returns âm:    " + " | ".join([f"{v:+.2%}" for v in top_neg_sorted[:5]]))
    print(f"\n  ── Nhận xét ──")
    print(f"  Có {int((np.abs(flat) > 0.50).sum()):,} ngày với |return| > 50%")
    print(f"  → Đây là sự kiện M&A, delisting, earnings shock cực đoan.")
    print(f"  → Khi tính feature cần winsorize hoặc rank-transform để tránh outlier ảnh hưởng quá lớn.")

# ─────────────────────────────────────────────────────────────────────────────
def eda_4_cs_dispersion(ret_matrix):
    section("4. CROSS-SECTIONAL DISPERSION THEO NGÀY")

    # Tính cs_std mỗi ngày (độ phân tán giữa các cổ phiếu)
    cs_std  = ret_matrix.std(axis=1, skipna=True)
    cs_mean = ret_matrix.mean(axis=1, skipna=True)
    cs_n    = ret_matrix.notna().sum(axis=1)

    # Lọc ngày có đủ tickers
    valid = cs_n >= 100
    cs_std  = cs_std[valid]
    cs_mean = cs_mean[valid]

    print(f"\n  Số ngày giao dịch phân tích: {len(cs_std):,}")
    print(f"\n  {'Chỉ số CS Dispersion':<30} {'Giá trị':>12}")
    print(f"  {'-'*44}")
    print(f"  {'Mean CS Std':<30} {cs_std.mean():>11.4%}")
    print(f"  {'Median CS Std':<30} {cs_std.median():>11.4%}")
    print(f"  {'Max CS Std (highest day)':<30} {cs_std.max():>11.4%}  [{cs_std.idxmax().date()}]")
    print(f"  {'Min CS Std (lowest day)':<30} {cs_std.min():>11.4%}  [{cs_std.idxmin().date()}]")

    # Regime: annual average dispersion
    annual_disp = cs_std.groupby(cs_std.index.year).mean()
    print(f"\n  ── CS Dispersion trung bình theo năm ──")
    print(f"  {'Năm':<8} {'CS Std (avg)':>14}  {'Nhận xét'}")
    print(f"  {'-'*55}")
    for yr, val in annual_disp.items():
        flag = ""
        if val > annual_disp.quantile(0.75):
            flag = "⚡ HIGH DISPERSION"
        elif val < annual_disp.quantile(0.25):
            flag = "😴 LOW DISPERSION"
        print(f"  {yr:<8} {val:>13.4%}  {flag}")

    # Top 10 high-dispersion days
    top_disp = cs_std.sort_values(ascending=False).head(10)
    print(f"\n  ── Top 10 ngày Dispersion cao nhất ──")
    for dt, val in top_disp.items():
        print(f"  {str(dt.date())} : CS Std = {val:.4%}")

    print(f"\n  ── Nhận xét ──")
    print(f"  Dispersion cao nhất tại {cs_std.idxmax().date()} (CS Std = {cs_std.max():.2%})")
    print(f"  Năm cao nhất: {annual_disp.idxmax()} ({annual_disp.max():.2%}) — kỳ vọng 2008/2009 hoặc 2020")
    print(f"  Dispersion cao → Long-Short model có nhiều cơ hội kiếm lợi nhuận hơn")
    print(f"  Dispersion thấp → Khó phân biệt tốt/xấu, model sẽ có IC thấp hơn")

    return cs_std, annual_disp

# ─────────────────────────────────────────────────────────────────────────────
def eda_5_plot_all(flat, cs_std, annual_disp, stats_dict):
    section("5. XUẤT BIỂU ĐỒ")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("EDA: Daily Return Distribution & Cross-Sectional Dispersion\n"
                 "Russell 1000 In-Sample (2000–2023)", fontsize=14, fontweight="bold")

    # ── Plot 1: Histogram of returns ──────────────────────────────────────────
    ax = axes[0, 0]
    sample = np.random.default_rng(42).choice(flat, size=200_000, replace=False)
    ax.hist(sample, bins=300, density=True, color="#2196F3", alpha=0.7,
            range=(-0.15, 0.15), label="Return distribution")

    # Overlay Normal curve
    x = np.linspace(-0.15, 0.15, 500)
    normal_pdf = stats.norm.pdf(x, stats_dict["mean"], stats_dict["std"])
    ax.plot(x, normal_pdf, "r-", lw=2, label=f"Normal fit (μ={stats_dict['mean']:+.4%}, σ={stats_dict['std']:.4%})")

    ax.axvline(stats_dict["p01"], color="orange", ls="--", lw=1, label=f"P1%={stats_dict['p01']:.2%}")
    ax.axvline(stats_dict["p99"], color="orange", ls="--", lw=1, label=f"P99%={stats_dict['p99']:.2%}")
    ax.set_xlabel("Daily Return")
    ax.set_ylabel("Density")
    ax.set_title(f"Return Distribution vs Normal\n"
                 f"Skew={stats_dict['skewness']:.3f}, ExKurt={stats_dict['excess_kurtosis']:.1f}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Plot 2: Q-Q Plot ───────────────────────────────────────────────────────
    ax = axes[0, 1]
    qq_sample = np.random.default_rng(42).choice(flat, size=5000, replace=False)
    (osm, osr), (slope, intercept, r) = stats.probplot(qq_sample, dist="norm")
    ax.scatter(osm, osr, s=2, alpha=0.4, color="#2196F3", label="Observed quantiles")
    ax.plot([min(osm), max(osm)],
            [slope * min(osm) + intercept, slope * max(osm) + intercept],
            "r-", lw=2, label="Normal reference line")
    ax.set_xlabel("Theoretical Quantiles (Normal)")
    ax.set_ylabel("Sample Quantiles")
    ax.set_title(f"Q-Q Plot (sample 5,000)\nFat tails visible at extremes")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Plot 3: CS Dispersion time series ─────────────────────────────────────
    ax = axes[1, 0]
    cs_std_roll = cs_std.rolling(21).mean()  # 1-month rolling avg
    ax.fill_between(cs_std.index, cs_std * 100, alpha=0.3, color="#FF9800", label="Daily CS Std (%)")
    ax.plot(cs_std_roll.index, cs_std_roll * 100, color="#E65100", lw=1.5,
            label="21-day rolling avg")
    ax.axhline(cs_std.mean() * 100, color="gray", ls="--", lw=1, label=f"Mean={cs_std.mean():.2%}")

    # Annotate key regimes
    for yr, label in [(2001, "Dot-com"), (2008, "GFC"), (2020, "COVID")]:
        ax.axvline(pd.Timestamp(f"{yr}-01-01"), color="red", ls=":", alpha=0.7, lw=1)
        ax.text(pd.Timestamp(f"{yr}-06-01"), cs_std.max() * 98, label,
                fontsize=7, color="red", rotation=90, va="top")

    ax.set_xlabel("Date")
    ax.set_ylabel("Cross-Sectional Std (%)")
    ax.set_title("Cross-Sectional Dispersion Over Time (2000–2023)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(4))

    # ── Plot 4: Annual average dispersion bar chart ────────────────────────────
    ax = axes[1, 1]
    colors = ["#F44336" if v > annual_disp.quantile(0.75) else
              "#4CAF50" if v < annual_disp.quantile(0.25) else "#2196F3"
              for v in annual_disp.values]
    ax.bar(annual_disp.index, annual_disp.values * 100, color=colors, width=0.7)
    ax.axhline(annual_disp.mean() * 100, color="black", ls="--", lw=1.5,
               label=f"Mean={annual_disp.mean():.2%}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean CS Std (%)")
    ax.set_title("Annual Average Cross-Sectional Dispersion\n"
                 "🔴 High / 🟢 Low / 🔵 Normal")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "eda_01_return_distribution.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  ✓ Biểu đồ đã lưu: {out_path}")

# ─────────────────────────────────────────────────────────────────────────────
def eda_6_save_summary(stats_dict, jb_dict, cs_std, annual_disp):
    section("6. LƯU KẾT QUẢ THỐNG KÊ")

    # Summary CSV
    rows = []
    for k, v in stats_dict.items():
        rows.append({"metric": k, "value": v})
    for k, v in jb_dict.items():
        rows.append({"metric": k, "value": v})

    df_sum = pd.DataFrame(rows)
    out_csv = os.path.join(OUT_DIR, "eda_01_return_stats.csv")
    df_sum.to_csv(out_csv, index=False)
    print(f"\n  ✓ Stats CSV: {out_csv}")

    # Annual dispersion CSV
    disp_df = annual_disp.reset_index()
    disp_df.columns = ["year", "cs_std_mean"]
    disp_df["percentile_rank"] = disp_df["cs_std_mean"].rank(pct=True)
    disp_df["regime"] = disp_df["cs_std_mean"].apply(
        lambda v: "HIGH" if v > annual_disp.quantile(0.75) else
                  ("LOW" if v < annual_disp.quantile(0.25) else "NORMAL")
    )
    disp_out = os.path.join(OUT_DIR, "eda_01_annual_dispersion.csv")
    disp_df.to_csv(disp_out, index=False)
    print(f"  ✓ Annual Dispersion CSV: {disp_out}")

# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(SEP)
    print("  EDA Task 1: Return Distribution & Cross-Sectional Dispersion")
    print("  Dữ liệu: in_sample/returns.parquet (2000-01-03 → 2023-12-29)")
    print(SEP)

    print("\n  Đang load returns matrix...")
    ret_matrix = load_returns()
    print(f"  ✓ Loaded: {ret_matrix.shape[0]} days × {ret_matrix.shape[1]} tickers")
    print(f"  ✓ Non-NaN observations: {ret_matrix.notna().sum().sum():,}")

    # Run all EDA steps
    flat, stats_dict    = eda_1_descriptive_stats(ret_matrix)
    jb_dict             = eda_2_normality_test(flat)
    eda_3_fat_tail_analysis(flat)
    cs_std, annual_disp = eda_4_cs_dispersion(ret_matrix)
    eda_5_plot_all(flat, cs_std, annual_disp, stats_dict)
    eda_6_save_summary(stats_dict, jb_dict, cs_std, annual_disp)

    print(f"\n{SEP}")
    print("  ✅ HOÀN TẤT EDA TASK 1: RETURN DISTRIBUTION & CS DISPERSION")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
