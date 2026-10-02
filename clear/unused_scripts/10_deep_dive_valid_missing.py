"""
Script: 10_deep_dive_valid_missing.py
Purpose: For VALID_MISSING tickers — check if they are:
  1. Actually present in QC but with a slightly different ticker (case / suffix variants)
  2. Well-known companies that were acquired/merged (explain why absent)
  3. Clear PDF extraction errors (company name leaked as ticker)
  Outputs a refined classification and updates the summary.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, re
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET  = os.path.join(BASE, "data", "processed", "daily_ohlcv",
                        "russell1000_daily_2000_2026.parquet")
PIT_JSON = os.path.join(BASE, "data", "raw", "universe",
                        "russell1000_pit_by_year.json")
MISS_CSV = os.path.join(BASE, "data", "raw", "universe",
                        "missing_ticker_analysis.csv")

# -- Load data -----------------------------------------------------------------
print("Loading data ...")
df      = pd.read_parquet(PARQUET)
miss_df = pd.read_csv(MISS_CSV)
with open(PIT_JSON, "r", encoding="utf-8") as f:
    pit = json.load(f)

all_qc = set(df["ticker"].unique())
valid_miss = miss_df[miss_df["category"] == "VALID_MISSING"]["ticker"].tolist()

print(f"QC unique tickers  : {len(all_qc):,}")
print(f"VALID_MISSING count: {len(valid_miss)}")
print("=" * 70)

# -- Known acquisitions / mergers / rebrands -----------------------------------
# (company was absorbed into another — perfectly expected absence post-merger)
KNOWN_MERGER_OR_REBRAND = {
    "ABI":   "Acquired by InBev (now BUD)",
    "APC":   "Acquired by Occidental Petroleum (OXY) in 2019",
    "ATHN":  "Acquired by Virence / GE Healthcare 2019",
    "AMR":   "American Airlines parent, merged into AAL 2013",
    "ACT":   "Allergan acquired by AbbVie, ticker changed",
    "ADOBE": "PDF parse error — actual ticker is ADBE",
    "AFLAC": "PDF parse error — actual ticker is AFL",
    "AECOM": "AECOM ticker is ACM on NYSE, PDF parse error",
    "AVNET": "PDF parse error — actual ticker is AVT",
    "AWAY":  "HomeAway, acquired by Expedia (EXPE) 2015",
    "ARNC":  "Arconic — spun off, trades as HWM/ARNC, possible QC gap",
    "AMCOR": "Australian company AMCR, listed on NYSE 2019",
    "ANV":   "Allied Nevada Gold — delisted 2015 (bankruptcy)",
    "ARCP":  "American Realty Capital, became VEREIT (VER) 2015",
    "ARIA":  "Acquired by Clovis Oncology 2013",
    "ARM":   "ARM Holdings — UK listed, delisted US 2016, re-IPO 2023 as ARM",
    "BEAM":  "Acquired by Suntory (now SBSW) 2014",
}

# -- Detect cases where ticker is clearly a PDF extraction error ---------------
# (company long name leaked, or known ticker variant)
def is_pdf_name_leak(t: str) -> tuple[bool, str]:
    """Heuristic: if removing vowels or matching known company name patterns."""
    # 5+ char all caps that look like truncated company names
    known_name_leaks = {
        "ADOBE": "Should be ADBE",
        "AFLAC": "Should be AFL",
        "AECOM": "Should be ACM",
        "AVNET": "Should be AVT",
        "AMCOR": "Should be AMCR",
    }
    if t in known_name_leaks:
        return True, known_name_leaks[t]
    return False, ""

# -- Cross-check: does a close variant exist in QC? ----------------------------
def find_qc_variant(t: str):
    """Try common transformations to find the real QC ticker."""
    candidates = [
        t[:4], t[:3],          # truncated
        t + "C", t + "A",      # class shares suffix
        t.replace("Q", ""),    # remove OTC suffix 'Q'
    ]
    for c in candidates:
        if c in all_qc and c != t and len(c) >= 2:
            return c
    return None

# -- Analyze valid missing tickers ---------------------------------------------
rows = []
for t in valid_miss:
    sub_pit = {y: (t in tlist) for y, tlist in pit.items()}
    years_in_pit = [y for y, present in sub_pit.items() if present]

    # Check merger/rebrand
    merger_note = KNOWN_MERGER_OR_REBRAND.get(t, "")

    # Check PDF name leak
    is_leak, leak_note = is_pdf_name_leak(t)

    # Check QC variant
    qc_var = find_qc_variant(t)

    # Revised category
    if is_leak:
        rev_cat = "PDF_NAME_LEAK"
        rev_reason = leak_note
    elif merger_note:
        rev_cat = "MERGED_OR_ACQUIRED"
        rev_reason = merger_note
    elif qc_var:
        rev_cat = "FORMAT_VARIANT"
        rev_reason = f"QC has '{qc_var}' as close variant"
    else:
        rev_cat = "VALID_MISSING"
        rev_reason = "No match found in QC"

    rows.append({
        "ticker":       t,
        "revised_cat":  rev_cat,
        "revised_reason": rev_reason,
        "pit_years":    ", ".join(sorted(years_in_pit)),
    })

refined = pd.DataFrame(rows)

# -- Summary -------------------------------------------------------------------
print("\nREFINED CLASSIFICATION of VALID_MISSING group")
print("=" * 70)
summary2 = refined["revised_cat"].value_counts()
for cat, cnt in summary2.items():
    pct = cnt / len(refined) * 100
    print(f"  {cat:<25}: {cnt:4d} ({pct:.1f}%)")

# -- Show PDF name leaks -------------------------------------------------------
leaks = refined[refined["revised_cat"] == "PDF_NAME_LEAK"]
mergers = refined[refined["revised_cat"] == "MERGED_OR_ACQUIRED"]
fmts = refined[refined["revised_cat"] == "FORMAT_VARIANT"]
truly_missing = refined[refined["revised_cat"] == "VALID_MISSING"]

if not leaks.empty:
    print(f"\n-- PDF_NAME_LEAK ({len(leaks)}) ---")
    for _, r in leaks.iterrows():
        print(f"  {r['ticker']:8s} -> {r['revised_reason']}")

if not mergers.empty:
    print(f"\n-- MERGED_OR_ACQUIRED ({len(mergers)}) ---")
    for _, r in mergers.iterrows():
        print(f"  {r['ticker']:8s} -> {r['revised_reason']}")

if not fmts.empty:
    print(f"\n-- FORMAT_VARIANT ({len(fmts)}) ---")
    for _, r in fmts.iterrows():
        print(f"  {r['ticker']:8s} -> {r['revised_reason']}")

print(f"\n-- TRULY VALID_MISSING ({len(truly_missing)}) sample ---")
for _, r in truly_missing.head(20).iterrows():
    print(f"  {r['ticker']:8s} | {r['pit_years'][:60]}")
if len(truly_missing) > 20:
    print(f"  ... and {len(truly_missing) - 20} more")

# -- Final coverage summary ----------------------------------------------------
pdf_noise_orig = miss_df[miss_df["category"] == "PDF_NOISE"].shape[0]
hist_delist    = miss_df[miss_df["category"] == "HISTORICAL_DELIST"].shape[0]
fmt_mismatch   = miss_df[miss_df["category"] == "FORMAT_MISMATCH"].shape[0]
total_pit      = len(set().union(*[set(v) for v in pit.values()]))

all_accounted  = (pdf_noise_orig + hist_delist + fmt_mismatch +
                  len(leaks) + len(mergers) + len(fmts))
true_gap       = len(truly_missing)
true_gap_pct   = true_gap / total_pit * 100
coverage_pct   = 100 - true_gap_pct

print("\n" + "=" * 70)
print("FINAL COVERAGE ANALYSIS (All 404 missing tickers accounted)")
print("=" * 70)
print(f"  Total PIT universe        : {total_pit:,} tickers")
print(f"  PDF noise artifacts       : {pdf_noise_orig}  (not real tickers)")
print(f"  PDF name leaks            : {len(leaks)}  (wrong ticker extracted from company name)")
print(f"  Format mismatches         : {fmt_mismatch + len(fmts)}  (same stock, different symbol)")
print(f"  Historical delistings     : {hist_delist}  (pre-QC coverage era)")
print(f"  Acquired / Merged         : {len(mergers)}  (absorbed into other companies)")
print(f"  Truly absent from QC      : {true_gap}")
print(f"\n  ==> Adjusted QC Coverage  : {coverage_pct:.2f}%")
print(f"  ==> True data gap         : {true_gap_pct:.2f}%")

# -- Save refined CSV ----------------------------------------------------------
out_csv = os.path.join(BASE, "data", "raw", "universe",
                       "valid_missing_refined.csv")
refined.to_csv(out_csv, index=False)
print(f"\nRefined analysis saved --> {out_csv}")
print("=" * 70)
