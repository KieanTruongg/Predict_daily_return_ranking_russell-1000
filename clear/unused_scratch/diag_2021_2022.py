"""
Diagnostic: check 2021 & 2022 PDF raw text + investigate PIT-only anomaly
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, re
import pypdf

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw", "universe", "raw")
PARQUET = os.path.join(BASE, "data", "processed", "daily_ohlcv",
                       "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe",
                        "russell1000_pit_by_year.json")

import pandas as pd
df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
QC_BY_YEAR = {str(y): set(grp["ticker"].unique())
              for y, grp in df_qc.groupby("year")}
QC_ALL = set(df_qc["ticker"].unique())

with open(PIT_JSON, "r") as f:
    pit = json.load(f)

# ── Show PIT-only for 2021 and 2022 ──────────────────────────────────────────
for year in ["2021", "2022"]:
    pit_set = set(pit.get(year, []))
    qc_set  = QC_BY_YEAR.get(year, set())
    pit_only = sorted(pit_set - qc_set)
    print(f"\n[{year}] PIT={len(pit_set)} | QC={len(qc_set)} | PIT-only ({len(pit_only)}):")
    for t in pit_only:
        in_qc_any = "IN_QC_OTHER_YEAR" if t in QC_ALL else "NOT_IN_QC_AT_ALL"
        print(f"  {t:8s}  {in_qc_any}")

# ── Also inspect first 2 pages of 2021.pdf and 2022.pdf raw text ─────────────
for fname in ["2021.pdf", "2022.pdf"]:
    fpath = os.path.join(RAW_DIR, fname)
    print(f"\n{'='*70}")
    print(f"RAW TEXT SAMPLE: {fname}")
    print(f"{'='*70}")
    reader = pypdf.PdfReader(fpath)
    print(f"Total pages: {len(reader.pages)}")
    for i, page in enumerate(reader.pages[:2]):
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        print(f"\n  [Page {i+1}] {len(lines)} lines:")
        for j, line in enumerate(lines[:50]):
            print(f"    {j+1:3d}: {repr(line)}")
        if len(lines) > 50:
            print(f"    ... ({len(lines)-50} more)")
