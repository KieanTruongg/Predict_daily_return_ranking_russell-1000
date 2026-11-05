"""
Script: scratch/analyze_qc_match_trend.py
Purpose: Analyze match percentage year by year (2000 to 2026) to see if failures are due to delisted/renamed companies over time.
"""
import os, json
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(BASE, "data", "processed", "daily_ohlcv", "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")

df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
qc_by_year = {str(y): set(grp["ticker"].unique()) for y, grp in df_qc.groupby("year")}
qc_all = set(df_qc["ticker"].unique())

with open(PIT_JSON, "r") as f:
    pit = json.load(f)

print("Year | PIT Count | QC Match | Match % | Fail Count | Fail In QC Other Year | Fail Never In QC")
print("-" * 80)

for year in range(2000, 2027):
    y_str = str(year)
    pit_set = set(pit.get(y_str, []))
    qc_set  = qc_by_year.get(y_str, set())
    matched = pit_set & qc_set
    failed  = pit_set - qc_set
    
    in_other_year = sum(1 for t in failed if t in qc_all)
    never_in_qc   = len(failed) - in_other_year
    
    pct = len(matched) / len(pit_set) * 100 if pit_set else 0
    print(f"{year:<4} | {len(pit_set):<9} | {len(matched):<8} | {pct:>6.1f}% | {len(failed):<10} | {in_other_year:<20} | {never_in_qc:<16}")
