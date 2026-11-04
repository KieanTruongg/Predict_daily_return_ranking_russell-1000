"""
Script: scripts/05_eda/eda_02_nan_universe_dynamics.py
Purpose: EDA Task 2+3 — NaN Pattern & Universe Dynamics

Nội dung:
  1. NaN profile chi tiết theo từng ticker (phân loại: full / partial / out-sample-only)
  2. Universe dynamics: số tickers active mỗi năm, entry/exit rate
  3. Ticker lifespan distribution (cổ phiếu tồn tại bao nhiêu năm trong Russell 1000)
  4. Đề xuất ngưỡng lọc cho Feature Store
  5. Lưu kết quả ra CSV và PNG
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IN_SAMPLE    = os.path.join(BASE_DIR, "data", "processed", "in_sample")
UNIVERSE_DIR = os.path.join(BASE_DIR, "data", "raw", "universe", "by_year")
OUT_DIR      = os.path.join(BASE_DIR, "docs", "Data report", "eda_figures")
os.makedirs(OUT_DIR, exist_ok=True)

SEP = "=" * 80
IN_SAMPLE_YEARS  = list(range(2000, 2024))
ALL_YEARS        = list(range(2000, 2027))

# ─────────────────────────────────────────────────────────────────────────────
def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def load_close():
    fpath = os.path.join(IN_SAMPLE, "close.parquet")
    df = pd.read_parquet(fpath)
    df.index = pd.to_datetime(df.index)
    return df

def load_universe():
    universe = {}
    for yr in ALL_YEARS:
        fp = os.path.join(UNIVERSE_DIR, f"russell1000_{yr}.json")
        if os.path.exists(fp):
            with open(fp, "r") as f:
                universe[yr] = set(json.load(f))
    return universe

# ─────────────────────────────────────────────────────────────────────────────
def eda_1_nan_profile(close_m):
    section("1. NaN PROFILE CHI TIẾT THEO TỪNG TICKER")

    ticker_nan_pct    = close_m.isna().mean() * 100
    ticker_valid_days = close_m.notna().sum()
    total_days        = len(close_m)

    # Phân loại tickers
    full_tickers    = ticker_nan_pct[ticker_nan_pct == 0]
    partial_tickers = ticker_nan_pct[(ticker_nan_pct > 0) & (ticker_nan_pct < 95)]
    oos_tickers     = ticker_nan_pct[ticker_nan_pct >= 95]  # chủ yếu là out-sample-only

    print(f"\n  Tổng tickers trong matrix: {len(ticker_nan_pct):,}")
    print(f"\n  {'Nhóm':<40} {'Số tickers':>12} {'Tỷ lệ':>8}")
    print(f"  {'-'*62}")
    print(f"  {'Full (0% NaN — có data toàn bộ 24 năm)':<40} {len(full_tickers):>12,} {len(full_tickers)/len(ticker_nan_pct)*100:>7.1f}%")
    print(f"  {'Partial (0–95% NaN — IPO/delisting giữa chừng)':<40} {len(partial_tickers):>12,} {len(partial_tickers)/len(ticker_nan_pct)*100:>7.1f}%")
    print(f"  {'Out-sample only (≥95% NaN — chỉ xuất hiện 2024+)':<40} {len(oos_tickers):>12,} {len(oos_tickers)/len(ticker_nan_pct)*100:>7.1f}%")

    # Phân bố số ngày valid
    bins = [0, 50, 252, 1260, 3024, 6021]
    labels = ["<50d", "50–251d (< 1yr)", "252–1259d (1–5yr)", "1260–3023d (5–12yr)", "≥3024d (12–24yr)"]
    print(f"\n  {'Khoảng ngày valid':<30} {'Số tickers':>12} {'Tỷ lệ':>8}")
    print(f"  {'-'*52}")
    for i, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
        cnt = ((ticker_valid_days >= lo) & (ticker_valid_days < hi)).sum()
        print(f"  {labels[i]:<30} {cnt:>12,} {cnt/len(ticker_valid_days)*100:>7.1f}%")

    # Ngưỡng lọc đề xuất
    min_days_threshold = 252  # 1 năm
    usable = (ticker_valid_days >= min_days_threshold).sum()
    print(f"\n  ── Ngưỡng lọc đề xuất cho Feature Store ──")
    print(f"  Tickers có ≥ {min_days_threshold} ngày valid (≥1 năm data): {usable:,} / {len(ticker_valid_days):,} ({usable/len(ticker_valid_days)*100:.1f}%)")
    print(f"  Tickers bị loại (< {min_days_threshold} ngày): {len(ticker_valid_days)-usable:,} ({(len(ticker_valid_days)-usable)/len(ticker_valid_days)*100:.1f}%)")

    return ticker_nan_pct, ticker_valid_days

# ─────────────────────────────────────────────────────────────────────────────
def eda_2_universe_dynamics(universe):
    section("2. UNIVERSE DYNAMICS — THÀNH PHẦN CHỈ SỐ THEO NĂM")

    rows = []
    prev_set = set()
    for yr in ALL_YEARS:
        curr = universe.get(yr, set())
        entries = len(curr - prev_set) if prev_set else 0
        exits   = len(prev_set - curr) if prev_set else 0
        turnover = (entries + exits) / (2 * len(prev_set)) * 100 if prev_set else 0
        rows.append({
            "year": yr, "n_tickers": len(curr),
            "entries": entries, "exits": exits,
            "turnover_pct": round(turnover, 1)
        })
        prev_set = curr

    df = pd.DataFrame(rows)
    print(f"\n  {'Năm':<6} {'N tickers':>10} {'Vào (Entry)':>12} {'Ra (Exit)':>10} {'Turnover %':>12}")
    print(f"  {'-'*52}")
    for _, r in df.iterrows():
        flag = " ⚡" if r["turnover_pct"] > 15 else ""
        print(f"  {int(r['year']):<6} {int(r['n_tickers']):>10,} {int(r['entries']):>12,} {int(r['exits']):>10,} {r['turnover_pct']:>11.1f}%{flag}")

    avg_entry   = df[df["year"] > 2000]["entries"].mean()
    avg_exit    = df[df["year"] > 2000]["exits"].mean()
    avg_turnover = df[df["year"] > 2000]["turnover_pct"].mean()
    print(f"\n  Trung bình (2001–2026): Entry={avg_entry:.0f}/năm | Exit={avg_exit:.0f}/năm | Turnover={avg_turnover:.1f}%/năm")
    print(f"\n  ── Nhận xét ──")
    print(f"  Năm có turnover cao nhất thường là hậu khủng hoảng (2001, 2002, 2009)")
    print(f"  Turnover ~10%/năm = ~100 cổ phiếu thay đổi mỗi năm — phù hợp lịch sử Russell 1000")

    return df

# ─────────────────────────────────────────────────────────────────────────────
def eda_3_ticker_lifespan(universe):
    section("3. TICKER LIFESPAN — CỔ PHIẾU TỒN TẠI BAO NHIÊU NĂM")

    all_tickers = set().union(*universe.values())
    lifespan = {}
    for t in all_tickers:
        years_active = [yr for yr in ALL_YEARS if t in universe.get(yr, set())]
        lifespan[t] = {
            "n_years": len(years_active),
            "first_year": min(years_active),
            "last_year": max(years_active),
            "in_insample": any(yr in IN_SAMPLE_YEARS for yr in years_active),
            "in_outsample": any(yr >= 2024 for yr in years_active),
        }

    df_life = pd.DataFrame(lifespan).T.reset_index().rename(columns={"index": "ticker"})
    df_life["n_years"] = df_life["n_years"].astype(int)

    print(f"\n  Tổng unique tickers trong Russell 1000 (2000–2026): {len(df_life):,}")
    print(f"\n  {'Số năm active':<20} {'Số tickers':>12} {'Tỷ lệ':>8}")
    print(f"  {'-'*42}")
    for bucket, label in [(1, "1 năm (one-hit)"), (range(2,4), "2–3 năm"),
                          (range(4,6), "4–5 năm"), (range(6,11), "6–10 năm"),
                          (range(11,21), "11–20 năm"), (range(21,28), "21–27 năm (blue chip)")]:
        if isinstance(bucket, int):
            cnt = (df_life["n_years"] == bucket).sum()
        else:
            cnt = df_life["n_years"].isin(bucket).sum()
        print(f"  {label:<20} {cnt:>12,} {cnt/len(df_life)*100:>7.1f}%")

    long_lived = df_life[df_life["n_years"] >= 20].sort_values("n_years", ascending=False)
    print(f"\n  ── Top 15 tickers tồn tại lâu nhất trong Russell 1000 ──")
    for _, r in long_lived.head(15).iterrows():
        print(f"  {r['ticker']:<8}: {int(r['n_years'])} năm ({int(r['first_year'])}–{int(r['last_year'])})")

    return df_life

# ─────────────────────────────────────────────────────────────────────────────
def eda_4_plot_all(ticker_valid_days, df_universe, df_life):
    section("4. XUẤT BIỂU ĐỒ")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("EDA: NaN Profile & Universe Dynamics\n"
                 "Russell 1000 In-Sample (2000–2023)", fontsize=14, fontweight="bold")

    # ── Plot 1: Valid-days distribution (histogram) ───────────────────────────
    ax = axes[0, 0]
    valid_days_arr = ticker_valid_days.values
    ax.hist(valid_days_arr[valid_days_arr > 0], bins=60, color="#2196F3", alpha=0.8, edgecolor="white")
    ax.axvline(252, color="orange", ls="--", lw=2, label="252d threshold (1 yr)")
    ax.axvline(1260, color="green", ls="--", lw=2, label="1260d threshold (5 yr)")
    ax.set_xlabel("Number of Valid (non-NaN) Days")
    ax.set_ylabel("Count of Tickers")
    ax.set_title("Distribution of Valid Days per Ticker\n(tickers with >0 valid days)")
    ax.legend()
    ax.grid(alpha=0.3)

    # ── Plot 2: Universe size & turnover over time ────────────────────────────
    ax = axes[0, 1]
    ax2 = ax.twinx()
    ax.bar(df_universe["year"], df_universe["n_tickers"], color="#90CAF9", alpha=0.7, label="N Tickers")
    ax2.plot(df_universe["year"][1:], df_universe["turnover_pct"][1:],
             "r-o", ms=4, lw=1.5, label="Turnover %")
    ax.set_xlabel("Year")
    ax.set_ylabel("N Tickers in Russell 1000", color="#1565C0")
    ax2.set_ylabel("Annual Turnover (%)", color="red")
    ax.set_title("Universe Size & Annual Turnover (2000–2026)")
    ax.set_ylim(900, 1100)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
    ax.grid(alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    # ── Plot 3: Ticker lifespan histogram ─────────────────────────────────────
    ax = axes[1, 0]
    ax.hist(df_life["n_years"], bins=27, range=(1, 28), color="#4CAF50", alpha=0.8, edgecolor="white")
    ax.set_xlabel("Years Active in Russell 1000 (2000–2026)")
    ax.set_ylabel("Count of Tickers")
    ax.set_title("Ticker Lifespan Distribution\n(How many years each stock was in Russell 1000)")
    ax.grid(alpha=0.3, axis="y")

    # ── Plot 4: Entry/Exit bar chart ──────────────────────────────────────────
    ax = axes[1, 1]
    df_sub = df_universe[df_universe["year"] > 2000]
    x = df_sub["year"].values
    ax.bar(x - 0.2, df_sub["entries"].values, width=0.4, color="#4CAF50", alpha=0.8, label="Entry (new tickers)")
    ax.bar(x + 0.2, df_sub["exits"].values,   width=0.4, color="#F44336", alpha=0.8, label="Exit (removed tickers)")
    ax.axhline(df_sub["entries"].mean(), color="green", ls="--", lw=1.5,
               label=f"Avg entry={df_sub['entries'].mean():.0f}")
    ax.axhline(df_sub["exits"].mean(), color="red", ls="--", lw=1.5,
               label=f"Avg exit={df_sub['exits'].mean():.0f}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Count")
    ax.set_title("Annual Index Reconstitution\n(Entries vs Exits)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "eda_02_nan_universe_dynamics.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  ✓ Biểu đồ đã lưu: {out_path}")

# ─────────────────────────────────────────────────────────────────────────────
def eda_5_save_results(df_universe, df_life):
    section("5. LƯU KẾT QUẢ")

    df_universe.to_csv(os.path.join(OUT_DIR, "eda_02_universe_dynamics.csv"), index=False)
    print(f"  ✓ Universe dynamics: {os.path.join(OUT_DIR, 'eda_02_universe_dynamics.csv')}")

    df_life.to_csv(os.path.join(OUT_DIR, "eda_02_ticker_lifespan.csv"), index=False)
    print(f"  ✓ Ticker lifespan:   {os.path.join(OUT_DIR, 'eda_02_ticker_lifespan.csv')}")

# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(SEP)
    print("  EDA Task 2: NaN Pattern & Universe Dynamics")
    print("  Dữ liệu: in_sample/close.parquet + raw/universe/by_year/*.json")
    print(SEP)

    print("\n  Đang load dữ liệu...")
    close_m  = load_close()
    universe = load_universe()
    print(f"  ✓ Close matrix: {close_m.shape}")
    print(f"  ✓ Universe loaded: {len(universe)} năm")

    ticker_nan_pct, ticker_valid_days = eda_1_nan_profile(close_m)
    df_universe                        = eda_2_universe_dynamics(universe)
    df_life                            = eda_3_ticker_lifespan(universe)
    eda_4_plot_all(ticker_valid_days, df_universe, df_life)
    eda_5_save_results(df_universe, df_life)

    print(f"\n{SEP}")
    print("  ✅ HOÀN TẤT EDA TASK 2: NaN PATTERN & UNIVERSE DYNAMICS")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
