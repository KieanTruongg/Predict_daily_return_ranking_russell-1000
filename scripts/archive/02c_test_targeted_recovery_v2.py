# QuantConnect Research Notebook — Vòng 2: Targeted Recovery & PIT Date Resolution
# Paste and run this script in QuantConnect Research Notebook to test:
# 1. New Candidates: WLY (for JW-A/JWA), NWSA/FOXA (for NWS-A), EPC (for ENR), BTUUQ (for BTU)
# 2. Point-in-Time Resolution via qb.SetStartDate() for PL, AVX, CR, ENR, BTU

import io
import json
import base64
from datetime import datetime
import pandas as pd
from IPython.display import display, HTML
from AlgorithmImports import *

qb = QuantBook()

# Targeted test specifications
TARGET_TESTS = [
    # 1. Share Class New Candidates
    {"ticker": "JW-A", "years": [2013, 2014, 2015], "candidates": ["WLY", "JW.A", "JWA"], "use_pit_date": False},
    {"ticker": "JWA",  "years": [2019],             "candidates": ["WLY", "JW.A", "JWA"], "use_pit_date": False},
    {"ticker": "NWS-A","years": [2008],             "candidates": ["NWSA", "FOXA", "NWS.A", "NWS"], "use_pit_date": False},
    
    # 2. Restructured / Ticker Reuse with Point-in-Time Date Resolution
    {"ticker": "PL",   "years": list(range(2000, 2015)), "candidates": ["PL"], "use_pit_date": True},
    {"ticker": "ENR",  "years": list(range(2000, 2014)), "candidates": ["ENR", "EPC"], "use_pit_date": True},
    {"ticker": "BTU",  "years": [2001, 2002, 2003, 2004, 2005, 2006, 2008, 2009, 2010, 2011, 2012, 2013, 2014], "candidates": ["BTU", "BTUUQ"], "use_pit_date": True},
    {"ticker": "CR",   "years": list(range(2001, 2021)), "candidates": ["CR"], "use_pit_date": True},
    {"ticker": "AVX",  "years": list(range(2000, 2015)), "candidates": ["AVX"], "use_pit_date": True},
    {"ticker": "MOS",  "years": [2009],                   "candidates": ["MOS", "IMX"], "use_pit_date": True},
]

print("=== Starting Vòng 2 Targeted Recovery Scan ===")

results_v2 = []

for spec in TARGET_TESTS:
    ticker = spec["ticker"]
    years = spec["years"]
    cands = spec["candidates"]
    use_pit = spec["use_pit_date"]
    
    for y in years:
        start_dt = datetime(y, 6, 20)
        end_dt = datetime(y + 1, 7, 5)
        
        # If testing PIT date resolution, anchor QuantBook clock to historical date
        if use_pit:
            try:
                qb.SetStartDate(start_dt)
            except:
                pass
        
        best_cand = None
        best_rows = 0
        best_min = "N/A"
        best_max = "N/A"
        
        for cand in cands:
            try:
                sec = qb.AddEquity(cand, Resolution.Daily)
                sym = sec.Symbol
                hist = qb.History(sym, start_dt, end_dt, Resolution.Daily)
                if hist is not None and len(hist) > 0:
                    times = hist.index.get_level_values(-1) if isinstance(hist.index, pd.MultiIndex) else hist.index
                    n_days = len(times)
                    if n_days > best_rows:
                        best_rows = n_days
                        best_cand = cand
                        best_min = str(times.min().date())
                        best_max = str(times.max().date())
            except:
                pass
                
        if best_rows > 0:
            if best_rows >= 240:
                status = "FULL_RECOVERED"
            else:
                status = "PARTIAL_RECOVERED"
            notes = f"Recovered using {best_cand} ({best_rows} bars)"
        else:
            status = "UNRESOLVED_GAP"
            notes = f"Tested {cands} (PIT={use_pit}) - no historical bars returned"
            best_cand = cands[0]
            
        results_v2.append({
            "ticker": ticker,
            "year": y,
            "best_candidate": best_cand,
            "status": status,
            "trading_days": best_rows,
            "min_date": best_min,
            "max_date": best_max,
            "notes": notes
        })

df_v2 = pd.DataFrame(results_v2)
print("\n=== VÒNG 2 SUMMARY ===")
print(df_v2['status'].value_counts())
print("\nSample Successful Recoveries:")
succ = df_v2[df_v2['trading_days'] > 0]
if len(succ) > 0:
    print(succ[['ticker', 'year', 'best_candidate', 'trading_days', 'status']].to_string())
else:
    print("No additional bars returned with current candidates/resolver.")

# Export downloadable CSV
csv_buf = io.StringIO()
df_v2.to_csv(csv_buf, index=False)
b64_csv = base64.b64encode(csv_buf.getvalue().encode('utf-8')).decode('ascii')

html_btn = f'''
<div style="margin: 20px 0; padding: 15px; background: #eef2ff; border: 1px solid #818cf8; border-radius: 8px;">
    <h3 style="margin: 0 0 10px 0; color: #3730a3;">Download Targeted Recovery Results (Vòng 2)</h3>
    <a download="empty_ticker_v2_targeted_results.csv" href="data:text/csv;base64,{b64_csv}"
       style="display: inline-block; padding: 10px 20px; background: #4f46e5; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
       📥 Download empty_ticker_v2_targeted_results.csv ({len(df_v2)} rows)
    </a>
</div>
'''
display(HTML(html_btn))
