"""
Script: scratch/audit_2000_tickers_quality.py
Purpose: Audit all 996 extracted tickers for year 2000 against raw lines to ensure 100% correctness.
"""
import os, json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pypdf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_2000 = os.path.join(BASE, "data", "raw", "universe", "raw", "2000.pdf")

reader = pypdf.PdfReader(PDF_2000)
raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")
with open(PIT_JSON, "r") as f:
    pit = json.load(f)

extracted_2000 = pit["2000"]

print(f"Total extracted tickers in 2000: {len(extracted_2000)}")

# Check for suspicious tickers (length > 5, numbers, etc.)
suspicious = [t for t in extracted_2000 if len(t) > 5 or not t.replace("-", "").replace(".", "").isalnum()]
print(f"Suspicious tickers: {suspicious}")

# Check lines starting with number or weird chars
weird_lines = []
for l in lines:
    if l.startswith("Russell") or l.startswith("Ticker") or l.startswith("*") or l.startswith("Page"):
        continue
    # check first token
    parts = l.split(maxsplit=1)
    if parts:
        token = parts[0]
        if not token.isupper() and not token.replace("-","").isalnum():
            weird_lines.append(l)

print(f"\nWeird raw lines count: {len(weird_lines)}")
for wl in weird_lines[:20]:
    print(f"  {wl}")
