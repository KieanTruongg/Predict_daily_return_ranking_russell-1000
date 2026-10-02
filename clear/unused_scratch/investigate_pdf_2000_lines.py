"""
Script: scratch/investigate_pdf_2000_lines.py
Purpose: Inspect the raw text lines of 2000 PDF to see if there are extraction errors,
         split lines, or missing company names vs tickers.
"""
import os, json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pypdf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_2000 = os.path.join(BASE, "clear", "refer_project", "raw_pdf", "russell1000_2000.pdf")
if not os.path.exists(PDF_2000):
    # Search for PDF in data/raw/universe or clear
    for root, dirs, files in os.walk(BASE):
        for f in files:
            if "2000" in f and f.endswith(".pdf") and not f.startswith("._") and "__MACOSX" not in root:
                PDF_2000 = os.path.join(root, f)
                break

print(f"Reading PDF: {PDF_2000}")
reader = pypdf.PdfReader(PDF_2000)
raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

print(f"Total lines extracted: {len(lines)}")
print("\nSample lines (first 40):")
for l in lines[:40]:
    print(f"  {l}")

PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")
with open(PIT_JSON, "r") as f:
    pit = json.load(f)

pit_2000 = pit["2000"]
PARQUET = os.path.join(BASE, "data", "processed", "daily_ohlcv", "russell1000_daily_2000_2026.parquet")
import pandas as pd
df_qc = pd.read_parquet(PARQUET, columns=["ticker", "year"])
qc_2000 = set(df_qc[df_qc["year"] == 2000]["ticker"].unique())

failed_2000 = set(pit_2000) - qc_2000

print(f"\n--- Searching raw PDF lines for failed tickers in 2000 ---")
sample_failed = sorted(list(failed_2000))[:30]
for t in sample_failed:
    matching_lines = [l for l in lines if l.startswith(t + " ") or l.startswith(t + "\t")]
    if matching_lines:
        print(f"Ticker [{t}]: {matching_lines[0]}")
    else:
        # try find anywhere in line
        any_match = [l for l in lines if re.search(r'\b' + re.escape(t) + r'\b', l)]
        print(f"Ticker [{t}] (anywhere): {any_match[:2]}")
