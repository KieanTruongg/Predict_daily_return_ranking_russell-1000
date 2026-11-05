"""
Script: inspect_pdf_raw_text.py
Purpose: Dump raw extracted text from sample pages of each PDF era
         to understand the EXACT layout — needed to design a correct parser.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import pypdf

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "raw", "universe", "raw")

# Pick one representative PDF from each era
SAMPLES = {
    "Era-1 (2000-2007)": ["2000.pdf", "2003.pdf", "2007.pdf"],
    "Era-2 (2009-2015)": ["2009.pdf", "2010.pdf", "2013.pdf"],
    "Era-3 (2016-2022)": ["2016.pdf", "2020.pdf", "2022.pdf"],
}

PAGES_TO_SHOW = 2   # how many pages to dump per file
LINES_PER_PAGE = 40 # max lines to print per page

for era, fnames in SAMPLES.items():
    print("\n" + "=" * 80)
    print(f"ERA: {era}")
    print("=" * 80)
    for fname in fnames:
        fpath = os.path.join(RAW_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [SKIP] {fname} not found")
            continue
        print(f"\n{'─'*60}")
        print(f"FILE: {fname}")
        print(f"{'─'*60}")
        try:
            reader = pypdf.PdfReader(fpath)
            n_pages = len(reader.pages)
            print(f"Total pages: {n_pages}")
            # Show first non-trivial pages (skip cover/TOC if too short)
            shown = 0
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if len(lines) < 5:
                    continue
                print(f"\n  [Page {i+1}] ({len(lines)} lines):")
                for j, line in enumerate(lines[:LINES_PER_PAGE]):
                    print(f"    {j+1:3d}: {repr(line)}")
                if len(lines) > LINES_PER_PAGE:
                    print(f"    ... ({len(lines) - LINES_PER_PAGE} more lines)")
                shown += 1
                if shown >= PAGES_TO_SHOW:
                    break
        except Exception as e:
            print(f"  ERROR: {e}")
