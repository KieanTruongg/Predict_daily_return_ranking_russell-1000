"""
Script: scratch/analyze_failed_tickers_2000.py
Purpose: Analyze the tickers in 2000-2004 that were NOT matched in QuantConnect.
         Check if ticker format issues (dots, slashes, hyphens, spaces, suffixes) are causing failures.
"""
import os, json
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(BASE, "data", "processed", "daily_ohlcv", "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")

df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
qc_2000 = set(df_qc[df_qc["year"] == 2000]["ticker"].unique())

with open(PIT_JSON, "r") as f:
    pit = json.load(f)

pit_2000 = set(pit["2000"])
failed_2000 = pit_2000 - qc_2000

print(f"Total PIT tickers in 2000: {len(pit_2000)}")
print(f"Matched in QC 2000     : {len(pit_2000 & qc_2000)}")
print(f"Failed in QC 2000      : {len(failed_2000)}")

print("\n--- Failed Tickers in 2000 (Sample 50) ---")
print(sorted(list(failed_2000))[:50])

# Categorize failed tickers by format features
has_dot = [t for t in failed_2000 if "." in t]
has_dash = [t for t in failed_2000 if "-" in t]
has_slash = [t for t in failed_2000 if "/" in t]
has_num = [t for t in failed_2000 if any(c.isdigit() for c in t)]
four_or_five_letters = [t for t in failed_2000 if len(t) >= 4 and t.isalpha()]
three_letters = [t for t in failed_2000 if len(t) <= 3 and t.isalpha()]

print(f"\nBreakdown of 258 Failed Tickers in 2000:")
print(f"  Has Dot '.'      : {len(has_dot)} -> {has_dot}")
print(f"  Has Dash '-'     : {len(has_dash)} -> {has_dash}")
print(f"  Has Slash '/'    : {len(has_slash)} -> {has_slash}")
print(f"  Has Digits (0-9) : {len(has_num)} -> {has_num[:20]}")
print(f"  Pure letters <= 3: {len(three_letters)}")
print(f"  Pure letters >= 4: {len(four_or_five_letters)}")
