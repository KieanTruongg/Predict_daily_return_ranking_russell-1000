"""
Script: 11_final_coverage_report.py
Purpose: After improved extraction, generate a clean final coverage report
         comparing PIT universe vs QC data, with detailed breakdown.
         Outputs both to console and updates the data_validation_report.md.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json
import pandas as pd

BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET  = os.path.join(BASE, "data", "processed", "daily_ohlcv",
                        "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe",
                        "russell1000_pit_by_year.json")
RPT_CSV  = os.path.join(BASE, "data", "raw", "universe",
                        "extraction_quality_report.csv")

print("Loading data ...")
df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
QC_BY_YEAR = {str(y): set(grp["ticker"].unique())
              for y, grp in df_qc.groupby("year")}
QC_ALL = set(df_qc["ticker"].unique())

with open(PIT_JSON, "r") as f:
    pit = json.load(f)

rpt = pd.read_csv(RPT_CSV)

print("\n" + "=" * 90)
print("FINAL EXTRACTION QUALITY REPORT (v2 parser with QC validation)")
print("=" * 90)
print(f"{'Year':<6} {'Type':<25} {'PIT':>5} {'QC':>5} {'Match':>6} {'Match%':>7} {'PIT-only':>9} {'QC-only':>8}")
print("-" * 90)

total_pit_only_valid = 0
for _, row in rpt.iterrows():
    year = str(int(row["year"]))
    pit_set   = set(pit.get(year, []))
    qc_set    = QC_BY_YEAR.get(year, set())
    matched   = pit_set & qc_set
    pit_only  = pit_set - qc_set
    # Of PIT-only, how many are in QC in OTHER years? (valid delistings)
    pit_only_in_qc_other = sum(1 for t in pit_only if t in QC_ALL)
    pit_only_not_in_qc   = len(pit_only) - pit_only_in_qc_other
    total_pit_only_valid += pit_only_not_in_qc

    print(f"  {year:<4} {row['source_type']:<25} {row['pit_tickers']:>5} {row['qc_tickers']:>5} "
          f"{row['matched']:>6} {row['coverage_pct']:>6.1f}%"
          f"  {len(pit_only):>5} ({pit_only_not_in_qc} truly absent)")

print("-" * 90)
all_pit     = set().union(*[set(v) for v in pit.values()])
all_matched = all_pit & QC_ALL
avg_cov     = rpt["coverage_pct"].mean()
print(f"\nSUMMARY:")
print(f"  Total unique PIT tickers          : {len(all_pit):,}")
print(f"  Total unique QC tickers           : {len(QC_ALL):,}")
print(f"  Globally matched (PIT in QC)      : {len(all_matched):,} ({len(all_matched)/len(all_pit)*100:.1f}%)")
print(f"  Not in QC at all                  : {len(all_pit)-len(all_matched):,} ({(len(all_pit)-len(all_matched))/len(all_pit)*100:.1f}%)")
print(f"  Avg per-year match rate           : {avg_cov:.1f}%")
print(f"  Best year (highest coverage)      : {rpt.loc[rpt['coverage_pct'].idxmax(), 'year']:.0f} ({rpt['coverage_pct'].max():.1f}%)")
print(f"  Worst year (lowest coverage)      : {rpt.loc[rpt['coverage_pct'].idxmin(), 'year']:.0f} ({rpt['coverage_pct'].min():.1f}%)")

# -- Per-year PIT-only breakdown for key years --------------------------------
print("\n-- Investigating PIT-only tickers (not in QC that year) --")
for year in ["2021", "2022", "2016", "2017", "2018"]:
    pit_set  = set(pit.get(year, []))
    qc_set   = QC_BY_YEAR.get(year, set())
    pit_only = sorted(pit_set - qc_set)
    not_in_any = [t for t in pit_only if t not in QC_ALL]
    in_other   = [t for t in pit_only if t in QC_ALL]
    print(f"  [{year}] PIT-only={len(pit_only):3d} | "
          f"truly absent from QC: {len(not_in_any):3d} | "
          f"delisted/other year: {len(in_other):3d}")
    if not_in_any:
        print(f"         Sample truly absent: {not_in_any[:10]}")
