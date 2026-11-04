# QuantConnect Research Notebook — 84 EMPTY Tickers Recovery & Verification
# Run this entire script in a QuantConnect Research Notebook.
# It automatically tests all candidate aliases for the 84 EMPTY tickers (263 ticker-years)
# and outputs an empirical recovery report with a downloadable CSV button.

import io
import json
import base64
from datetime import datetime
import pandas as pd
from IPython.display import display, HTML
from AlgorithmImports import *

qb = QuantBook()

# Master candidate dictionary for all 84 tickers
EMPTY_CANDIDATES = {
  "CR": {
    "years": [
      2000,
      2001,
      2002,
      2003,
      2004,
      2006,
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015,
      2016,
      2017,
      2018,
      2019,
      2020,
      2021
    ],
    "candidates": [
      "CR",
      "CXT",
      "CR 1",
      "CR 2"
    ],
    "category": "CORPORATE_SPLIT_MAPPING"
  },
  "ENR": {
    "years": [
      2000,
      2001,
      2002,
      2003,
      2004,
      2005,
      2006,
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "ENR",
      "EPC"
    ],
    "category": "TICKER_REUSE_SPINOFF"
  },
  "AVX": {
    "years": [
      2000,
      2001,
      2002,
      2003,
      2004,
      2005,
      2006,
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014
    ],
    "candidates": [
      "AVX",
      "AVX 1"
    ],
    "category": "PRE_MA_MAPPING_GAP"
  },
  "PL": {
    "years": [
      2000,
      2001,
      2002,
      2003,
      2004,
      2005,
      2006,
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014
    ],
    "candidates": [
      "PL",
      "PL 1"
    ],
    "category": "TICKER_RECYCLED"
  },
  "BTU": {
    "years": [
      2001,
      2002,
      2003,
      2004,
      2005,
      2006,
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014
    ],
    "candidates": [
      "BTU",
      "BTUUQ",
      "BTU 1"
    ],
    "category": "BANKRUPTCY_RELUSTING"
  },
  "AWH": {
    "years": [
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015,
      2016,
      2017
    ],
    "candidates": [
      "AWH",
      "AWH 1"
    ],
    "category": "ACQUIRED_MAPPING_GAP"
  },
  "BF-B": {
    "years": [
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "BF-B",
      "BF.B",
      "BF/B",
      "BFB"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "FCE-A": {
    "years": [
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "FCE-A",
      "FCE.A",
      "FCE/A",
      "FCEA"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "FNF": {
    "years": [
      2007,
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014
    ],
    "candidates": [
      "FNF",
      "FNFG"
    ],
    "category": "TRACKING_STOCK_MAPPING"
  },
  "HUB-B": {
    "years": [
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "HUB-B",
      "HUB.B",
      "HUB/B",
      "HUBB"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "JW-A": {
    "years": [
      2008,
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "JW-A",
      "JW.A",
      "JW/A",
      "JWA"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "WCN": {
    "years": [
      2009,
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "WCN"
    ],
    "category": "RENAME_CROSS_BORDER"
  },
  "BRK-B": {
    "years": [
      2010,
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "BRK-B",
      "BRK.B",
      "BRK/B",
      "BRKB"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "MOS": {
    "years": [
      2005,
      2006,
      2007,
      2008,
      2009,
      2010
    ],
    "candidates": [
      "MOS",
      "IMX"
    ],
    "category": "MERGER_FORMATION"
  },
  "AAN": {
    "years": [
      2011,
      2012,
      2013,
      2014,
      2015
    ],
    "candidates": [
      "AAN",
      "PRG"
    ],
    "category": "SPINOFF_RENAME"
  },
  "VIA": {
    "years": [
      2015,
      2016,
      2017,
      2018,
      2019
    ],
    "candidates": [
      "VIA",
      "VIAB",
      "VIA.B",
      "VIA-B",
      "PARA"
    ],
    "category": "MA_RENAME_DUAL_CLASS"
  },
  "XTSLA": {
    "years": [
      2019,
      2023,
      2024,
      2025,
      2026
    ],
    "candidates": [
      "XTSLA",
      "TSLA"
    ],
    "category": "SYNTHETIC_PREFIX"
  },
  "BFA": {
    "years": [
      2019,
      2023,
      2024,
      2025
    ],
    "candidates": [
      "BFA",
      "BF.A",
      "BF-A",
      "BF/A"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "BFB": {
    "years": [
      2019,
      2023,
      2024,
      2025
    ],
    "candidates": [
      "BFB",
      "BF.B",
      "BF-B",
      "BF/B"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "BRKB": {
    "years": [
      2019,
      2023,
      2024,
      2025
    ],
    "candidates": [
      "BRKB",
      "BRK.B",
      "BRK-B",
      "BRK/B"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "HEIA": {
    "years": [
      2019,
      2023,
      2024,
      2025
    ],
    "candidates": [
      "HEIA",
      "HEI.A",
      "HEI-A",
      "HEI/A"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "LENB": {
    "years": [
      2019,
      2023,
      2024,
      2025
    ],
    "candidates": [
      "LENB",
      "LEN.B",
      "LEN-B",
      "LEN/B"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "VIA-B": {
    "years": [
      2008,
      2009,
      2010,
      2011
    ],
    "candidates": [
      "VIA-B",
      "VIA.B",
      "VIA/B",
      "VIAB"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "CWENA": {
    "years": [
      2023,
      2024,
      2025
    ],
    "candidates": [
      "CWENA",
      "CWEN.A",
      "CWEN-A",
      "CWEN/A"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "UBFUT": {
    "years": [
      2019,
      2023,
      2026
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "UHALB": {
    "years": [
      2023,
      2024,
      2025
    ],
    "candidates": [
      "UHALB",
      "UHAL.B",
      "UHAL-B",
      "UHAL/B"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "YB": {
    "years": [
      2020,
      2021,
      2022
    ],
    "candidates": [
      "YB"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "ARD": {
    "years": [
      2023,
      2024
    ],
    "candidates": [
      "ARD"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "BRUKER": {
    "years": [
      2021,
      2022
    ],
    "candidates": [
      "BRUKER",
      "BRKR"
    ],
    "category": "RAW_NAME_TYPO"
  },
  "HR": {
    "years": [
      2003,
      2005
    ],
    "candidates": [
      "HR"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "SGAFT": {
    "years": [
      2024,
      2025
    ],
    "candidates": [
      "SGAFT"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "ADLAC": {
    "years": [
      2000
    ],
    "candidates": [
      "ADLAC"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "ALEX": {
    "years": [
      2012
    ],
    "candidates": [
      "ALEX"
    ],
    "category": "HOLDING_CO_RESTRUCTURE"
  },
  "ANTM": {
    "years": [
      2022
    ],
    "candidates": [
      "ANTM",
      "ELV"
    ],
    "category": "REBRAND_RENAME"
  },
  "BEC": {
    "years": [
      2011
    ],
    "candidates": [
      "BEC"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "BF-A": {
    "years": [
      2015
    ],
    "candidates": [
      "BF-A",
      "BF.A",
      "BF/A",
      "BFA"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "COC": {
    "years": [
      2000
    ],
    "candidates": [
      "COC"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "COR": {
    "years": [
      2023
    ],
    "candidates": [
      "COR"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "CST": {
    "years": [
      2017
    ],
    "candidates": [
      "CST"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "EG": {
    "years": [
      2023
    ],
    "candidates": [
      "EG",
      "RE"
    ],
    "category": "HOLDING_CO_RESTRUCTURE"
  },
  "ESU4": {
    "years": [
      2024
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "ESU5": {
    "years": [
      2025
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "ESU9": {
    "years": [
      2019
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "ESZ3": {
    "years": [
      2023
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "ESZ6": {
    "years": [
      2026
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "ETFCD": {
    "years": [
      2010
    ],
    "candidates": [],
    "category": "NON_EQUITY_CASH"
  },
  "FAU4": {
    "years": [
      2024
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "FAU5": {
    "years": [
      2025
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "FAU9": {
    "years": [
      2019
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "FAZ3": {
    "years": [
      2023
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "FAZ6": {
    "years": [
      2026
    ],
    "candidates": [],
    "category": "NON_EQUITY_FUTURE"
  },
  "GCI": {
    "years": [
      2015
    ],
    "candidates": [
      "GCI",
      "TGNA"
    ],
    "category": "HOLDING_CO_RESTRUCTURE"
  },
  "HHH": {
    "years": [
      2023
    ],
    "candidates": [
      "HHH",
      "HHC"
    ],
    "category": "HOLDING_CO_RESTRUCTURE"
  },
  "HOLX": {
    "years": [
      2026
    ],
    "candidates": [
      "HOLX"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "HUB": {
    "years": [
      2000
    ],
    "candidates": [
      "HUB"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "IDT": {
    "years": [
      2004
    ],
    "candidates": [
      "IDT"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "JWA": {
    "years": [
      2019
    ],
    "candidates": [
      "JWA",
      "JW.A",
      "JW-A",
      "JW/A"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "KLG": {
    "years": [
      2023
    ],
    "candidates": [
      "KLG"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "LEAF": {
    "years": [
      2015
    ],
    "candidates": [
      "LEAF"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "LEN-B": {
    "years": [
      2015
    ],
    "candidates": [
      "LEN-B",
      "LEN.B",
      "LEN/B",
      "LENB"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "LGFA": {
    "years": [
      2019
    ],
    "candidates": [
      "LGFA",
      "LGF.A",
      "LGF-A",
      "LGF/A"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "LGFB": {
    "years": [
      2019
    ],
    "candidates": [
      "LGFB",
      "LGF.B",
      "LGF-B",
      "LGF/B"
    ],
    "category": "SHARE_CLASS_CONCAT"
  },
  "LMG": {
    "years": [
      2000
    ],
    "candidates": [
      "LMG"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "MBGL": {
    "years": [
      2026
    ],
    "candidates": [
      "MBGL"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "MEL": {
    "years": [
      2007
    ],
    "candidates": [
      "MEL"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "MNK": {
    "years": [
      2013
    ],
    "candidates": [
      "MNK"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "NATL": {
    "years": [
      2023
    ],
    "candidates": [
      "NATL"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "NLOP": {
    "years": [
      2023
    ],
    "candidates": [
      "NLOP"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "NWS-A": {
    "years": [
      2008
    ],
    "candidates": [
      "NWS-A",
      "NWS.A",
      "NWS/A",
      "NWSA"
    ],
    "category": "SHARE_CLASS_HYPHEN"
  },
  "PHIN": {
    "years": [
      2023
    ],
    "candidates": [
      "PHIN"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "RGS": {
    "years": [
      2002
    ],
    "candidates": [
      "RGS"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "RTN": {
    "years": [
      2000
    ],
    "candidates": [
      "RTN",
      "RTX"
    ],
    "category": "MAJOR_MERGER"
  },
  "SKYF": {
    "years": [
      2007
    ],
    "candidates": [
      "SKYF"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "SLE": {
    "years": [
      2012
    ],
    "candidates": [
      "SLE"
    ],
    "category": "SPINOFF_DISSOLUTION"
  },
  "TEG": {
    "years": [
      2015
    ],
    "candidates": [
      "TEG"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "TKO": {
    "years": [
      2023
    ],
    "candidates": [
      "TKO"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "UAG": {
    "years": [
      2007
    ],
    "candidates": [
      "UAG",
      "PAG"
    ],
    "category": "HOLDING_CO_RESTRUCTURE"
  },
  "UDI": {
    "years": [
      2005
    ],
    "candidates": [
      "UDI"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "VLTO": {
    "years": [
      2023
    ],
    "candidates": [
      "VLTO"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "VMRK": {
    "years": [
      2026
    ],
    "candidates": [
      "VMRK"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "VSTS": {
    "years": [
      2023
    ],
    "candidates": [
      "VSTS"
    ],
    "category": "RECENT_SPINOFF_2023"
  },
  "WRC": {
    "years": [
      2004
    ],
    "candidates": [
      "WRC"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "WSC": {
    "years": [
      2011
    ],
    "candidates": [
      "WSC"
    ],
    "category": "HISTORICAL_DELISTED_OR_MAPPING"
  },
  "ZMH": {
    "years": [
      2015
    ],
    "candidates": [
      "ZMH",
      "ZBH"
    ],
    "category": "MERGER_RENAME"
  }
}

print(f"=== Starting Candidate Test Scan for {len(EMPTY_CANDIDATES)} tickers across 263 ticker-years ===")

results = []

# Map of year to test date ranges (June Rebalance to June Rebalance of next year)
# Using standard Russell 1000 reconstitution window (June 30 Year to June 30 Year+1)
def get_year_window(year):
    start = datetime(year, 6, 20)
    end = datetime(year + 1, 7, 5)
    return start, end

total_tested = 0
recovered_count = 0

for ticker, info in EMPTY_CANDIDATES.items():
    years = info['years']
    cands = info['candidates']
    cat = info['category']
    
    # If category is non-equity futures/cash, mark as NON_EQUITY_EXCLUDE directly
    if 'NON_EQUITY' in cat or not cands:
        for y in years:
            results.append({
                'russell_ticker': ticker,
                'year': y,
                'category': cat,
                'tested_candidate': 'NONE',
                'status': 'NON_EQUITY_EXCLUDE',
                'trading_days': 0,
                'min_date': 'N/A',
                'max_date': 'N/A',
                'notes': 'Non-equity instrument (Futures/Cash collateral) - excluded from common stock universe'
            })
        continue

    for y in years:
        total_tested += 1
        start_dt, end_dt = get_year_window(y)
        
        best_candidate = None
        best_rows = 0
        best_min = 'N/A'
        best_max = 'N/A'
        
        # Test each candidate
        for cand in cands:
            try:
                sec = qb.AddEquity(cand, Resolution.Daily)
                sym = sec.Symbol
                hist = qb.History(sym, start_dt, end_dt, Resolution.Daily)
                
                if hist is not None and len(hist) > 0:
                    # History may be MultiIndex (symbol, time) or single index (time)
                    if isinstance(hist.index, pd.MultiIndex):
                        times = hist.index.get_level_values(-1)
                    else:
                        times = hist.index
                    
                    n_days = len(times)
                    if n_days > best_rows:
                        best_rows = n_days
                        best_candidate = cand
                        best_min = str(times.min().date())
                        best_max = str(times.max().date())
            except Exception as e:
                pass
        
        if best_rows > 0:
            status = 'RECOVERED'
            recovered_count += 1
            notes = f"Recovered using alias '{best_candidate}' ({best_rows} bars)"
        else:
            if 'RECENT_SPINOFF' in cat:
                status = 'PRE_IPO'
                notes = 'Pre-IPO period for recent spin-off'
            elif 'DELISTED' in cat or 'MA' in cat or 'ACQUIRED' in cat:
                status = 'DELISTED_OR_MAPPING_GAP'
                notes = 'No active/historical mapping found in QC cloud database'
            else:
                status = 'UNRESOLVED'
                notes = 'No candidate returned historical bars'
                
        results.append({
            'russell_ticker': ticker,
            'year': y,
            'category': cat,
            'tested_candidate': best_candidate if best_candidate else cands[0],
            'status': status,
            'trading_days': best_rows,
            'min_date': best_min,
            'max_date': best_max,
            'notes': notes
        })

res_df = pd.DataFrame(results)

print("\n" + "="*80)
print("=== VERIFICATION SUMMARY ===")
print("="*80)
print(f"Total EMPTY ticker-years evaluated: {len(res_df)}")
print(f"Status distribution:")
print(res_df['status'].value_counts())
print("-" * 80)

# Calculate mathematically honest coverage
raw_total = 26919
raw_matched = 26656
raw_empty = 263
raw_coverage = (raw_matched / raw_total) * 100

recov_cnt = (res_df['status'] == 'RECOVERED').sum()
non_eq_cnt = (res_df['status'] == 'NON_EQUITY_EXCLUDE').sum()
valid_universe = raw_total - non_eq_cnt
effective_matched = raw_matched + recov_cnt
adj_coverage = (effective_matched / valid_universe) * 100

print(f"Raw Coverage:      {raw_matched:,} / {raw_total:,} = {raw_coverage:.2f}%")
print(f"Recovered Aliases: +{recov_cnt} ticker-years")
print(f"Non-Equity Excl:   -{non_eq_cnt} instruments")
print(f"Effective Matched: {effective_matched:,} / {valid_universe:,}")
print(f"Adjusted Coverage: {adj_coverage:.2f}%")
print("="*80)

# Convert to CSV and create download button
csv_buf = io.StringIO()
res_df.to_csv(csv_buf, index=False)
csv_bytes = csv_buf.getvalue().encode('utf-8')
b64_csv = base64.b64encode(csv_bytes).decode('ascii')

html_btn = f'''
<div style="margin: 20px 0; padding: 15px; background: #eef7ee; border: 1px solid #99cc99; border-radius: 8px;">
    <h3 style="margin: 0 0 10px 0; color: #1e561e;">Download Candidate Test Results</h3>
    <a download="empty_ticker_test_results.csv" href="data:text/csv;base64,{b64_csv}"
       style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
       📥 Download empty_ticker_test_results.csv ({len(res_df)} rows)
    </a>
</div>
'''
display(HTML(html_btn))
