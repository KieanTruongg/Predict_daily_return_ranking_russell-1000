# ====================================================================================
# [CLOUD-ONLY] QuantConnect Research Notebook — Export Stock Splits & Cash Dividends (1998-2026)
# Execution environment: QuantConnect LEAN Cloud Research Notebook (Cloud-Only).
# ====================================================================================
# Huong dan su dung:
# 1. Mo mot Research Notebook tren QuantConnect.
# 2. Dan toan bo noi dung file nay vao mot Cell duy nhat va bam RUN (Shift + Enter).
# 3. Thoi gian chay: ~45 - 60 giay.
# 4. Khi chay xong, bam nut HTML 'Download russell1000_corporate_actions_1998_2026.zip'
#    de tai file ve may va luu vao thu muc:
#    data/processed/constituents_market_data/corporate_actions/
# ====================================================================================

from AlgorithmImports import *
import pandas as pd
import json, zlib, base64, io, zipfile, time
from datetime import datetime
from IPython.display import HTML, display

print("=" * 80)
print("XUAT DU LIEU CORPORATE ACTIONS (SPLITS & DIVIDENDS) 1998-2026")
print("=" * 80)

qb = QuantBook()

_B64_DATA = (
    "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"
)


TICKERS = json.loads(zlib.decompress(base64.b64decode(_B64_DATA)).decode('utf-8'))
print(f"[1/4] Da giai nen danh muc: {len(TICKERS):,} tickers.")

FORMAT_ALIASES = {
    'BF-B':['BF.B'], 'BRK-B':['BRK.B'], 'FCE-A':['FCE.A'],
    'HUB-B':['HUB.B'], 'LEN-B':['LEN.B'], 'LGFA':['LGF.A'],
    'LGFB':['LGF.B'], 'CWENA':['CWEN.A'], 'NWS-A':['NWS.A'],
    'BRKB':['BRK.B'], 'BFA':['BF.A'], 'BFB':['BF.B'],
    'HEIA':['HEI.A'], 'LENB':['LEN.B'], 'UHALB':['UHAL.B'],
}

def get_candidates(t):
    vals = [t]
    vals += FORMAT_ALIASES.get(t, [])
    if '-' in t: vals.append(t.replace('-', '.'))
    if '.' in t: vals.append(t.replace('.', '-'))
    return list(dict.fromkeys(vals))

print("[2/4] Dang dang ky Symbols vao QuantBook Engine...")
symbols = []
symbol_to_ticker = {}

for ticker in TICKERS:
    registered = False
    for cand in get_candidates(ticker):
        try:
            sec = qb.AddEquity(cand, Resolution.Daily)
            sym = sec.Symbol
            if sym not in symbol_to_ticker:
                symbols.append(sym)
                symbol_to_ticker[sym] = ticker
            registered = True
            break
        except Exception:
            continue
    if not registered:
        # Fallback to direct LEAN SecurityIdentifier for delisted historical symbols
        try:
            sid = SecurityIdentifier.GenerateEquity(ticker, Market.USA)
            sym = Symbol(sid, ticker)
            sec = qb.AddSecurity(sym, Resolution.Daily)
            if sym not in symbol_to_ticker:
                symbols.append(sym)
                symbol_to_ticker[sym] = ticker
        except Exception:
            pass

print(f" -> Dang ky thanh cong: {len(symbols):,} symbols ({len(symbols)/len(TICKERS)*100:.1f}%).")

start_date = datetime(1998, 1, 1)
end_date = datetime(2026, 11, 1)
CHUNK_SIZE = 100

all_splits = []
all_dividends = []

def extract_items(slice_dict):
    try:
        return list(slice_dict.items())
    except Exception:
        try:
            return [(k, slice_dict[k]) for k in slice_dict.Keys]
        except Exception:
            return [(kvp.Key, kvp.Value) for kvp in slice_dict]

def parse_splits_enumerable(enumerable):
    if enumerable is None: return
    for slice_obj in enumerable:
        items = extract_items(slice_obj)
        for sym_obj, sp in items:
            dt = sp.Time if hasattr(sp, 'Time') else sp.EndTime
            t_str = pd.to_datetime(str(dt)).strftime('%Y-%m-%d')
            orig_t = symbol_to_ticker.get(sym_obj, str(sym_obj.Value))
            factor = float(sp.SplitFactor) if hasattr(sp, 'SplitFactor') else float(sp.Value)
            ref_p = float(sp.ReferencePrice) if hasattr(sp, 'ReferencePrice') else (float(sp.Price) if hasattr(sp, 'Price') else np.nan)
            all_splits.append({
                'date': t_str,
                'original_ticker': orig_t,
                'symbol': str(sym_obj.Value),
                'sid': str(sym_obj.ID),
                'split_factor': factor,
                'reference_price': ref_p
            })

def parse_dividends_enumerable(enumerable):
    if enumerable is None: return
    for slice_obj in enumerable:
        items = extract_items(slice_obj)
        for sym_obj, div in items:
            dt = div.Time if hasattr(div, 'Time') else div.EndTime
            t_str = pd.to_datetime(str(dt)).strftime('%Y-%m-%d')
            orig_t = symbol_to_ticker.get(sym_obj, str(sym_obj.Value))
            dist = float(div.Distribution) if hasattr(div, 'Distribution') else float(div.Value)
            ref_p = float(div.ReferencePrice) if hasattr(div, 'ReferencePrice') else (float(div.Price) if hasattr(div, 'Price') else np.nan)
            all_dividends.append({
                'date': t_str,
                'original_ticker': orig_t,
                'symbol': str(sym_obj.Value),
                'sid': str(sym_obj.ID),
                'dividend_amount': dist,
                'reference_price': ref_p
            })

print("[3/4] Dang truy van Splits & Dividends tu LEAN Factor Database...")
t0 = time.time()

for i in range(0, len(symbols), CHUNK_SIZE):
    chunk = symbols[i:i+CHUNK_SIZE]
    
    # 1. Splits
    try:
        sp_enum = qb.History[Split](chunk, start_date, end_date)
        parse_splits_enumerable(sp_enum)
    except Exception as e:
        for s in chunk:
            try:
                parse_splits_enumerable(qb.History[Split]([s], start_date, end_date))
            except Exception:
                pass

    # 2. Dividends
    try:
        div_enum = qb.History[Dividend](chunk, start_date, end_date)
        parse_dividends_enumerable(div_enum)
    except Exception as e:
        for s in chunk:
            try:
                parse_dividends_enumerable(qb.History[Dividend]([s], start_date, end_date))
            except Exception:
                pass

    if (i // CHUNK_SIZE + 1) % 5 == 0 or (i + CHUNK_SIZE >= len(symbols)):
        print(f"  -> Tien do: {min(i+CHUNK_SIZE, len(symbols))}/{len(symbols)} symbols ({time.time()-t0:.1f}s) | Splits: {len(all_splits):,} | Dividends: {len(all_dividends):,}")

    if (i // CHUNK_SIZE + 1) % 5 == 0 or (i + CHUNK_SIZE >= len(symbols)):
        print(f"  -> Tien do: {min(i+CHUNK_SIZE, len(symbols))}/{len(symbols)} symbols ({time.time()-t0:.1f}s) | Splits: {len(all_splits):,} | Dividends: {len(all_dividends):,}")

df_splits_res = pd.DataFrame(all_splits)
df_divs_res = pd.DataFrame(all_dividends)

print(f"\n[4/4] Dong goi ZIP va tao lien ket tai xuong...")
print(f" -> Tong so su kien Splits trich xuat   : {len(df_splits_res):,} ban ghi")
print(f" -> Tong so su kien Dividends trich xuat: {len(df_divs_res):,} ban ghi")

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('russell1000_splits_1998_2026.csv', df_splits_res.to_csv(index=False).encode('utf-8'))
    zf.writestr('russell1000_dividends_1998_2026.csv', df_divs_res.to_csv(index=False).encode('utf-8'))

zip_bytes = zip_buffer.getvalue()
zip_size_kb = len(zip_bytes) / 1024
b64_zip = base64.b64encode(zip_bytes).decode('utf-8')

html_link = f'''
<div style="padding: 16px; background-color: #e6f4ea; border: 2px solid #34a853; border-radius: 8px; margin: 16px 0;">
    <h3 style="color: #137333; margin-top: 0;">Xuất dữ liệu Corporate Actions hoàn tất!</h3>
    <p>File chứa <b>{len(df_splits_res):,} Splits</b> và <b>{len(df_divs_res):,} Dividends</b> ({zip_size_kb:.1f} KB).</p>
    <a download="russell1000_corporate_actions_1998_2026.zip" 
       href="data:application/zip;base64,{b64_zip}" 
       style="display: inline-block; padding: 10px 20px; background-color: #1a73e8; color: white; text-decoration: none; font-weight: bold; border-radius: 4px;">
       DOWNLOAD russell1000_corporate_actions_1998_2026.zip
    </a>
</div>
'''
display(HTML(html_link))
print("Hoan tat! Bam nut o tren de tai file ZIP.")
