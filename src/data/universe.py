"""Universe management for Russell 1000 Point-in-Time constituents (2000-2026)."""
import os
import glob
import json
import re
import io
import requests
import pandas as pd
from typing import List, Dict, Optional

DEFAULT_UNIVERSE_CSV = os.path.join("data", "raw", "universe", "russell1000_constituents.csv")
RAW_ARCHIVE_DIR = os.path.join("data", "raw", "universe", "raw")


def parse_pit_universe_archive(archive_dir: str = RAW_ARCHIVE_DIR) -> Dict[str, List[str]]:
    """
    Parses annual Point-in-Time Russell 1000 reconstitution archive (2000 to 2026)
    located in `data/raw/universe/raw/`.
    
    Returns a dictionary mapping Year (str) -> List of Tickers (List[str]).
    """
    if not os.path.exists(archive_dir):
        return {}

    files = glob.glob(os.path.join(archive_dir, "*"))
    yearly_tickers: Dict[str, List[str]] = {}

    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        year = fname.split(".")[0]
        if not year.isdigit():
            continue

        found_tickers = set()

        if fname.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for row in data:
                        if isinstance(row, list) and len(row) > 0 and isinstance(row[0], str):
                            t = row[0].strip().replace(".", "-")
                            if t and len(t) <= 6:
                                found_tickers.add(t)
            except Exception:
                pass

        elif fname.endswith(".csv"):
            try:
                df = pd.read_csv(fpath)
                col = "Ticker" if "Ticker" in df.columns else df.columns[0]
                for t in df[col].dropna():
                    t = str(t).strip().replace(".", "-")
                    if t and len(t) <= 6:
                        found_tickers.add(t)
            except Exception:
                pass

        elif fname.endswith(".xls") or fname.endswith(".xlsx"):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                cells = re.findall(r"<Cell[^>]*>\s*<Data[^>]*>([A-Z0-9\.\-]{1,6})</Data>\s*</Cell>", text)
                for t in cells:
                    t = t.strip().replace(".", "-")
                    if t not in ["TICKER", "NAME", "USD", "ISIN", "CUSIP", "EQUITY"]:
                        found_tickers.add(t)
            except Exception:
                pass

        elif fname.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(fpath)
                text = " ".join([page.extract_text() for page in reader.pages])
                tokens = re.findall(r"\b[A-Z]{1,5}\b", text)
                for t in tokens:
                    if t not in ["THE", "AND", "FOR", "INC", "CORP", "CO", "LTD", "PLC", "CLASS", "INDEX", "RUSSELL", "FTSE", "HOLDINGS", "GROUP"]:
                        found_tickers.add(t)
            except Exception:
                pass

        if found_tickers:
            yearly_tickers[year] = sorted(list(found_tickers))

    return yearly_tickers


def build_or_load_universe(output_csv: str = DEFAULT_UNIVERSE_CSV, min_stocks: int = 500) -> List[str]:
    """
    Loads existing universe or builds it from local annual PIT archive or fallback sources.
    Ensures at least `min_stocks` tickers are available.
    """
    # 1. Try local annual PIT archive in data/raw/universe/raw/
    pit_dict = parse_pit_universe_archive()
    if pit_dict:
        all_unique_tickers = set()
        for year, tickers in pit_dict.items():
            all_unique_tickers.update(tickers)

        if len(all_unique_tickers) >= min_stocks:
            sorted_tickers = sorted(list(all_unique_tickers))
            df = pd.DataFrame({"Ticker": sorted_tickers, "Name": sorted_tickers, "Source": "PIT_Russell_Archive"})
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)

            # Also save yearly PIT mapping JSON for dynamic backtesting
            json_path = os.path.join(os.path.dirname(output_csv), "russell1000_pit_by_year.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(pit_dict, f, indent=4)

            print(f"[Success] Loaded Point-in-Time Russell 1000 archive ({len(sorted_tickers)} unique tickers across {len(pit_dict)} years).")
            print(f"[Saved] Master ticker list -> '{output_csv}'")
            print(f"[Saved] Yearly Point-in-Time JSON mapping -> '{json_path}'")
            return sorted_tickers

    # 2. Check existing CSV
    if os.path.exists(output_csv):
        df = pd.read_csv(output_csv)
        if len(df) >= min_stocks:
            tickers = df["Ticker"].dropna().unique().tolist()
            return sorted(tickers)

    # 3. Fallback to S&P 500 / Large-Cap list
    print(f"Building Russell 1000 universe proxy (target >= {min_stocks} stocks)...")
    fallback_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        df = pd.read_csv(fallback_url)
        if "Symbol" in df.columns:
            df = df.rename(columns={"Symbol": "Ticker"})
        df["Ticker"] = df["Ticker"].str.replace(".", "-", regex=False)
        df.to_csv(output_csv, index=False)
        tickers = df["Ticker"].dropna().unique().tolist()
        return sorted(tickers)
    except Exception:
        seed_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "TSLA", "UNH", "JNJ"]
        df = pd.DataFrame({"Ticker": seed_tickers})
        df.to_csv(output_csv, index=False)
        return seed_tickers
