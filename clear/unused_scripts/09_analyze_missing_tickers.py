"""
Script: 09_analyze_missing_tickers.py
Purpose: Deep-dive analysis of tickers present in the PIT Russell 1000 Universe
         but NOT found in the QuantConnect market data.
         Classifies each missing ticker into one of 5 categories:
           A) FORMAT_MISMATCH    - same stock, different symbol format (e.g. BRK-A vs BRKA)
           B) PDF_NOISE          - non-ticker string leaked from PDF parsing
           C) OTC_OR_FOREIGN     - genuine stock but traded OTC or on foreign exchange
           D) HISTORICAL_DELIST  - delisted before QC data coverage window
           E) VALID_MISSING      - legitimate ticker absent from QC (unexplained gap)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import re
import pandas as pd

# -- Paths ---------------------------------------------------------------------
PARQUET = (r"d:\Learning\HK1_2026-2027\CO3101 - Do an tong hop - ttnt"
           r"\Predict_daily_return_rankings"
           r"\data\processed\daily_ohlcv\russell1000_daily_2000_2026.parquet")
PARQUET = r"d:\Learning\HK1_2026-2027\CO3101 - \u0110\u1ed3 \u00e1n t\u1ed5ng h\u1ee3p - ttnt\Predict_daily_return_rankings\data\processed\daily_ohlcv\russell1000_daily_2000_2026.parquet"
PIT_JSON = r"d:\Learning\HK1_2026-2027\CO3101 - \u0110\u1ed3 \u00e1n t\u1ed5ng h\u1ee3p - ttnt\Predict_daily_return_rankings\data\raw\universe\russell1000_pit_by_year.json"

import os
PARQUET  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "processed", "daily_ohlcv",
                        "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "raw", "universe",
                        "russell1000_pit_by_year.json")

# -- Load data -----------------------------------------------------------------
print("Loading data ...")
df = pd.read_parquet(PARQUET)
with open(PIT_JSON, "r", encoding="utf-8") as f:
    pit = json.load(f)

all_pit = set().union(*pit.values())
all_qc  = set(df["ticker"].unique())

missing = sorted(all_pit - all_qc)
print(f"\nPIT universe   : {len(all_pit):,} unique tickers")
print(f"QC market data : {len(all_qc):,} unique tickers")
print(f"Missing tickers: {len(missing)}")
print("=" * 70)

# -- Classification rules ------------------------------------------------------
PDF_NOISE_PATTERNS = [
    r"^\d+$",                          # pure numbers: "10", "50"
    r"^[A-Z]{1}$",                     # single letter page markers
    r"^(II|III|IV|VI|VII|VIII|IX|XI|XII)$",  # roman numerals
    r"^[^A-Z]+$",                      # no alphabetic chars at all
]

KNOWN_OTC_OR_FOREIGN = {
    "WAMUQ", "LEHVQ", "WFMI", "BVPS", "FWLT",
    "CWMFA", "KMART", "AIMCO", "SGRP",
}

KNOWN_EARLY_DELIST = {
    "ENRNQ", "WCOMP", "ADELQ", "GNWT", "CONSRC", "KMRTQ",
}


def classify(ticker: str):
    """Returns (category_code, reason_string)."""

    # 1. Format variant — dash removed (BRK-A -> BRKA)
    no_dash = ticker.replace("-", "")
    if no_dash in all_qc and no_dash != ticker:
        return "FORMAT_MISMATCH", f"QC has '{no_dash}' (dash removed)"

    # 2. Format variant — dot (BRK.A)
    dot_var = ticker.replace("-", ".")
    if dot_var in all_qc and dot_var != ticker:
        return "FORMAT_MISMATCH", f"QC has '{dot_var}' (dot variant)"

    # 3. PDF noise patterns
    for pat in PDF_NOISE_PATTERNS:
        if re.fullmatch(pat, ticker):
            return "PDF_NOISE", f"Matches noise pattern '{pat}'"

    # 4. Single character — almost certainly PDF noise
    if len(ticker) == 1:
        return "PDF_NOISE", "Single character — PDF artifact"

    # 5. Known OTC / foreign
    if ticker in KNOWN_OTC_OR_FOREIGN:
        return "OTC_OR_FOREIGN", "Known OTC / foreign-listed security"

    # 6. Known early delist
    if ticker in KNOWN_EARLY_DELIST:
        return "HISTORICAL_DELIST", "Known early-delisted company pre-QC coverage"

    # 7. Heuristic: appears only in very early years (2000-2002) — likely pre-QC delist
    years_in_pit = [int(y) for y, tlist in pit.items() if ticker in tlist]
    if years_in_pit and max(years_in_pit) <= 2002:
        return "HISTORICAL_DELIST", f"Only in PIT years {min(years_in_pit)}-{max(years_in_pit)}, pre-QC era"

    # 8. Default — looks like a real ticker, genuinely missing from QC
    return "VALID_MISSING", "Ticker looks valid but absent from QC dataset"


# -- Run classification --------------------------------------------------------
rows = []
for t in missing:
    cat, reason = classify(t)
    years_in_pit = [y for y, tlist in pit.items() if t in tlist]
    rows.append({
        "ticker":      t,
        "category":    cat,
        "reason":      reason,
        "pit_years":   ", ".join(sorted(years_in_pit)),
        "n_pit_years": len(years_in_pit),
    })

results = pd.DataFrame(rows)

# -- Summary table -------------------------------------------------------------
print("\nCLASSIFICATION SUMMARY")
print("=" * 70)
summary = results["category"].value_counts()
for cat, cnt in summary.items():
    pct = cnt / len(results) * 100
    print(f"  {cat:<22}: {cnt:4d} tickers ({pct:.1f}%)")
print(f"\n  TOTAL MISSING          : {len(results):4d} tickers (100%)")

# -- Detail per category -------------------------------------------------------
for cat in ["FORMAT_MISMATCH", "PDF_NOISE", "OTC_OR_FOREIGN",
            "HISTORICAL_DELIST", "VALID_MISSING"]:
    sub = results[results["category"] == cat]
    if sub.empty:
        continue
    print(f"\n-- {cat} ({len(sub)} tickers) " + "-" * 35)
    for _, row in sub.head(40).iterrows():
        yrs = row["pit_years"] if len(row["pit_years"]) < 50 else row["pit_years"][:47] + "..."
        print(f"  {row['ticker']:8s} | {row['reason']:<47s} | years: {yrs}")
    if len(sub) > 40:
        print(f"  ... and {len(sub) - 40} more")

# -- Coverage impact -----------------------------------------------------------
valid_missing    = results[results["category"] == "VALID_MISSING"]
pdf_noise        = results[results["category"] == "PDF_NOISE"]
fmt_mismatch     = results[results["category"] == "FORMAT_MISMATCH"]
hist_delist      = results[results["category"] == "HISTORICAL_DELIST"]
otc_foreign      = results[results["category"] == "OTC_OR_FOREIGN"]

print("\n" + "=" * 70)
print("COVERAGE IMPACT ANALYSIS")
print("=" * 70)
print(f"  Total missing            : {len(missing)}")
print(f"  - PDF noise artifacts    : {len(pdf_noise)}  (not real tickers)")
print(f"  - Format mismatches      : {len(fmt_mismatch)}  (same stock, diff symbol)")
print(f"  - Historical delistings  : {len(hist_delist)}  (pre-QC era, expected)")
print(f"  - OTC / Foreign          : {len(otc_foreign)}  (out-of-scope exchange)")
print(f"  - Genuinely absent (QC gap): {len(valid_missing)}")

true_missing_pct = len(valid_missing) / len(all_pit) * 100
print(f"\n  True QC gap (VALID_MISSING) as % of PIT : {true_missing_pct:.2f}%")
print(f"  Adjusted QC Coverage Rate               : {100 - true_missing_pct:.2f}%")

# -- Save detailed CSV ---------------------------------------------------------
out_csv = os.path.join(os.path.dirname(PIT_JSON), "missing_ticker_analysis.csv")
results.to_csv(out_csv, index=False)
print(f"\nDetailed analysis saved --> {out_csv}")
print("=" * 70)
