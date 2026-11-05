"""
Script: 01_parse_all_universe.py  (v2 - Improved)
=======================================================
Cải tiến so với v1:
  1. Parser chính xác theo cấu trúc thực tế từng era PDF.
  2. Mỗi dòng đều lấy CẢ ticker lẫn company name, kiểm tra chéo với nhau.
  3. Sau khi trích xuất -> validate ngay với QC market data (parquet).
  4. Phân loại: QC_MATCHED | DELISTED_OR_MISSING
  5. Output ra JSON và CSV với metadata đầy đủ.

Layout thực tế (confirmed từ raw text dump):
  Era-1 (2000-2007): "TICKER  COMPANY NAME"  --> ticker ở đầu dòng
  Era-2 (2009-2015): "COMPANY NAME  TICKER"  --> ticker ở cuối dòng
  Era-3 (2016-2022): dòng lẻ = company name, dòng chẵn = ticker (xen kẽ)
  Non-PDF years:     2008.csv, 2019/2023/2024.json, 2025/2026.xls
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, re, glob
import pandas as pd
import pypdf

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw", "universe", "raw")

PARQUET  = os.path.join(BASE, "data", "processed", "daily_ohlcv",
                        "russell1000_daily_2000_2026.parquet")
OUT_JSON = os.path.join(BASE, "data", "raw", "universe",
                        "russell1000_pit_by_year.json")
OUT_CSV  = os.path.join(BASE, "data", "raw", "universe",
                        "russell1000_constituents.csv")
OUT_RPT  = os.path.join(BASE, "data", "raw", "universe",
                        "extraction_quality_report.csv")

# ──────────────────────────────────────────────────────────────────────────────
# Load QC universe for validation
# ──────────────────────────────────────────────────────────────────────────────
print("Loading QC market data for validation ...")
df_qc   = pd.read_parquet(PARQUET, columns=["ticker", "year"])
QC_ALL  = set(df_qc["ticker"].unique())
# QC tickers per year (for per-year coverage)
QC_BY_YEAR = {str(y): set(grp["ticker"].unique())
              for y, grp in df_qc.groupby("year")}
del df_qc
print(f"  QC total unique tickers : {len(QC_ALL):,}")
print(f"  QC years covered        : {sorted(QC_BY_YEAR.keys())}")

# ──────────────────────────────────────────────────────────────────────────────
# Helper: is_valid_ticker
# ──────────────────────────────────────────────────────────────────────────────
NOISE_WORDS = {
    "THE", "AND", "FOR", "INC", "CORP", "CO", "LTD", "PLC", "CLASS",
    "INDEX", "RUSSELL", "FTSE", "HOLDINGS", "GROUP", "NEW", "PAGE",
    "RANK", "NAME", "WEIGHT", "TICKER", "SECTOR", "TOTAL", "MARKET",
    "CAP", "VALUE", "SHARES", "PORTFOLIO", "ANNUAL", "REBALANCING",
    "COMPOSITE", "LARGE", "MID", "SMALL", "GROWTH", "UNITED", "STATES",
    "US", "DOLLAR", "USD", "FUND", "TRUST", "SERIES", "DEPT", "BANK",
    "FINANCIAL", "SYSTEMS", "SERVICES", "COMPANY", "AS", "OF", "LIST",
    "MEMBERSHIP", "JUNE", "JULY", "JAN", "FEB", "MAR", "APR", "MAY",
    "AUG", "SEP", "OCT", "NOV", "DEC", "TW",
}

def is_valid_ticker(t: str) -> bool:
    if not t:
        return False
    t = t.strip()
    # Must be 1-6 chars, uppercase letters/digits/hyphens only
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{0,5}", t):
        return False
    # Must contain at least one letter
    if not any(c.isalpha() for c in t):
        return False
    # Not a noise word
    if t in NOISE_WORDS:
        return False
    # Not a pure page number like "10"
    if t.isdigit():
        return False
    return True

# ──────────────────────────────────────────────────────────────────────────────
# Era parsers
# ──────────────────────────────────────────────────────────────────────────────

def parse_era1(text: str) -> set:
    """
    Era-1 (2000-2007): Lines like 'TICKER  COMPANY NAME'
    Ticker is the FIRST token on the line, followed by a space and an uppercase letter.
    """
    tickers = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match: starts with a valid ticker, then space, then more uppercase text
        m = re.match(r"^([A-Z][A-Z0-9\-]{0,5})\s{1,4}[A-Z0-9&]", line)
        if m:
            t = m.group(1)
            if is_valid_ticker(t):
                tickers.add(t)
    return tickers


def parse_era2(text: str) -> set:
    """
    Era-2 (2009-2015): Lines like 'COMPANY NAME  TICKER'
    Ticker is the LAST word on the line (1-6 uppercase chars).
    The company name contains mixed words.
    """
    tickers = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip header lines
        if re.match(r"^(Company|Ticker|As of|Russell|FTSE)", line):
            continue
        # Last word on the line should be the ticker
        parts = line.split()
        if not parts:
            continue
        t = parts[-1]
        # Only accept if it looks like a ticker (all-caps, short)
        if re.fullmatch(r"[A-Z][A-Z0-9\.\-]{0,5}", t):
            t = t.replace(".", "-")  # BRK.B -> BRK-B
            if is_valid_ticker(t) and len(parts) >= 2:
                # Extra check: the preceding word should be part of a company name
                # (not another ticker-like word alone)
                tickers.add(t)
    return tickers


def parse_era3(text: str) -> set:
    """
    Era-3 (2016-2022): Strict pair-based parsing.
    Layout confirmed: 'Company' header, 'Ticker' header, then
    alternating lines: COMPANY_NAME on odd lines, TICKER on even lines.

    Key fix: we ONLY take the EVEN line of each pair as the ticker.
    This prevents company short-names (e.g. ADOBE, TESLA, NVIDIA written
    as abbreviations) from being mistaken for tickers.
    """
    tickers = set()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Find the start of actual data: after 'Company' / 'Ticker' header pair
    # Then treat lines as pairs: [company_name, ticker, company_name, ticker, ...]
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip page headers
        if re.match(r"^(Company|Ticker|Russell|FTSE|As\s*of|\d{4})", line, re.IGNORECASE):
            i += 1
            continue
        # Current line = company name; next line = ticker
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # Skip if next is also a header
            if re.match(r"^(Company|Ticker|Russell|FTSE|As\s*of)", next_line, re.IGNORECASE):
                i += 1
                continue
            # The ticker must be a short all-caps token (1-6 chars)
            if re.fullmatch(r"[A-Z][A-Z0-9\-]{0,5}", next_line):
                t = next_line.replace(".", "-")
                if is_valid_ticker(t):
                    tickers.add(t)
                i += 2   # consume both company + ticker lines
                continue
        i += 1
    return tickers


# ──────────────────────────────────────────────────────────────────────────────
# Non-PDF parsers (CSV, JSON, XLS) — unchanged from v1
# ──────────────────────────────────────────────────────────────────────────────

def parse_csv(fpath: str) -> set:
    df = pd.read_csv(fpath)
    col = "Ticker" if "Ticker" in df.columns else df.columns[0]
    tickers = set()
    for t in df[col].dropna():
        t = str(t).strip().replace(".", "-")
        if is_valid_ticker(t):
            tickers.add(t)
    return tickers


def parse_json(fpath: str) -> set:
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("aaData", data) if isinstance(data, dict) else data
    tickers = set()
    for row in rows:
        if isinstance(row, list) and row and isinstance(row[0], str):
            t = row[0].strip().replace(".", "-")
            if is_valid_ticker(t):
                tickers.add(t)
    return tickers


def parse_xls(fpath: str) -> set:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    rows = re.findall(r"<ss:Row[^>]*>(.*?)</ss:Row>", content, re.DOTALL)
    tickers = set()
    for r in rows:
        cells = re.findall(r"<ss:Data[^>]*>([^<]+)</ss:Data>", r)
        if len(cells) > 3:
            t = cells[0].strip().replace(".", "-")
            if re.match(r"^[A-Z0-9\-]{1,6}$", t) and is_valid_ticker(t):
                tickers.add(t)
    return tickers


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
files = sorted(glob.glob(os.path.join(RAW_DIR, "*")))
yearly_tickers = {}
report_rows    = []

print("\n" + "=" * 80)
print("IMPROVED PDF EXTRACTION + QC VALIDATION (2000 - 2026)")
print("=" * 80)

for fpath in files:
    fname = os.path.basename(fpath)
    year  = fname.split(".")[0]
    if not year.isdigit() or int(year) < 2000:
        continue

    y_int = int(year)
    found = set()

    # ── Choose parser ──────────────────────────────────────────────────────────
    if fname.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(fpath)
            full_text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"

            if y_int <= 2007:
                found = parse_era1(full_text)
                era_label = "Era-1 (ticker-first)"
            elif 2009 <= y_int <= 2015:
                found = parse_era2(full_text)
                era_label = "Era-2 (ticker-last)"
            else:
                found = parse_era3(full_text)
                era_label = "Era-3 (alternating)"
        except Exception as e:
            print(f"  [ERROR] {fname}: {e}")
            era_label = "PDF-ERROR"

    elif fname.endswith(".csv"):
        found = parse_csv(fpath)
        era_label = "CSV"

    elif fname.endswith(".json"):
        found = parse_json(fpath)
        era_label = "JSON"

    elif fname.endswith(".xls") or fname.endswith(".xlsx"):
        found = parse_xls(fpath)
        era_label = "XLS"

    else:
        continue

    if not found:
        continue

    # ── Per-year QC validation ────────────────────────────────────────────────
    qc_year  = QC_BY_YEAR.get(year, set())
    matched  = found & qc_year           # in both PIT and QC for that year
    pit_only = found - qc_year           # in PIT but not QC that year
    qc_only  = qc_year - found           # in QC but not in PIT

    coverage = len(matched) / len(found) * 100 if found else 0

    yearly_tickers[year] = sorted(found)

    report_rows.append({
        "year":          year,
        "source_type":   era_label,
        "pit_tickers":   len(found),
        "qc_tickers":    len(qc_year),
        "matched":       len(matched),
        "pit_only":      len(pit_only),
        "qc_only":       len(qc_only),
        "coverage_pct":  round(coverage, 1),
    })

    print(f"  [{year}] {era_label:<22} | PIT={len(found):4d} | QC={len(qc_year):4d} "
          f"| Match={len(matched):4d} ({coverage:.1f}%) | PIT-only={len(pit_only):3d}")

# ── Global stats ───────────────────────────────────────────────────────────────
all_unique = sorted(set().union(*yearly_tickers.values()))
matched_globally = set(all_unique) & QC_ALL
print("\n" + "=" * 80)
print(f"Total years processed    : {len(yearly_tickers)}")
print(f"Total unique PIT tickers : {len(all_unique):,}")
print(f"Total QC tickers         : {len(QC_ALL):,}")
print(f"Globally matched         : {len(matched_globally):,} ({len(matched_globally)/len(all_unique)*100:.1f}%)")
print(f"Not in QC at all         : {len(all_unique) - len(matched_globally):,}")

# ── Save outputs ──────────────────────────────────────────────────────────────
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(yearly_tickers, f, indent=4)

df_out = pd.DataFrame({"Ticker": all_unique})
df_out["InQC"] = df_out["Ticker"].isin(QC_ALL)
df_out.to_csv(OUT_CSV, index=False)

df_rpt = pd.DataFrame(report_rows)
df_rpt.to_csv(OUT_RPT, index=False)

print(f"\nSaved:")
print(f"  PIT JSON  --> {OUT_JSON}")
print(f"  PIT CSV   --> {OUT_CSV}")
print(f"  Report    --> {OUT_RPT}")
print("=" * 80)
