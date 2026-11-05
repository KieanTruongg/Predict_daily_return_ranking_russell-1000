"""
Script: scratch/check_qc_vs_v2.py
Purpose: Analyze whether v1 parser extracted a SUPERSET of v2, or if v2 found NEW valid tickers
         that were NOT included in the old QuantConnect download.
"""
import os, json
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(BASE, "data", "processed", "daily_ohlcv", "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")

df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
qc_all = set(df_qc["ticker"].unique())

with open(PIT_JSON, "r") as f:
    pit_v2 = json.load(f)

pit_v2_all = set().union(*[set(v) for v in pit_v2.values()])

print("=== CHECKING V2 TICKERS VS QC DOWNLOADED DATA ===")
print(f"Total Unique Tickers in QC Parquet: {len(qc_all)}")
print(f"Total Unique Tickers in V2 PIT JSON: {len(pit_v2_all)}")

matched = pit_v2_all & qc_all
v2_not_in_qc = pit_v2_all - qc_all
qc_not_in_v2 = qc_all - pit_v2_all

print(f"Matched (v2 in QC) : {len(matched)}")
print(f"In v2 PIT, but NOT in QC Parquet : {len(v2_not_in_qc)}")
print(f"In QC Parquet, but NOT in v2 PIT : {len(qc_not_in_v2)}")

print("\nSample tickers in v2 PIT but NOT in QC Parquet:")
print(sorted(list(v2_not_in_qc))[:30])

print("\nSample tickers in QC Parquet but NOT in v2 PIT:")
print(sorted(list(qc_not_in_v2))[:30])
