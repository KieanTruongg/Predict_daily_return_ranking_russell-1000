# ==============================================================================
# [CLOUD-ONLY] QuantConnect Research Notebook — Russell historical market data collector (10 Batches)
# Execution environment: QuantConnect LEAN Cloud Research Notebook (Cloud-Only).
# ==============================================================================
# Paste this entire file into a QuantConnect Research Python notebook cell.
# One run = one of 10 batches (about 287-288 historical ticker strings).
# Outputs a downloadable ZIP of CSV files + audit; convert CSV to Parquet locally.
# Historical symbol reuse, corporate actions and ticker identity need manual audit.

from AlgorithmImports import *
from datetime import datetime
from collections import defaultdict
import pandas as pd
import json, zlib, base64, io, zipfile, time
from IPython.display import HTML, display

BATCH_INDEX = 0   # 0..9, run once for each index
TOTAL_BATCHES_TARGET = 10
START_YEAR = 1998
END_YEAR = 2026
NORMALIZATION = DataNormalizationMode.Raw
# Keep History calls at 20 symbols despite ~289 symbols per export batch.
HISTORY_GROUP_SIZE = 20

# 2,871 valid unique Russell 1000 equity tickers across 27 years (1998-2026)
_B64_DATA = (
    "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"
)

TICKERS = json.loads(zlib.decompress(base64.b64decode(_B64_DATA)).decode('utf-8'))
TOTAL_BATCHES = TOTAL_BATCHES_TARGET
BATCH_SIZE = (len(TICKERS) + TOTAL_BATCHES - 1) // TOTAL_BATCHES
assert 0 <= BATCH_INDEX < TOTAL_BATCHES
batch = TICKERS[BATCH_INDEX*BATCH_SIZE:(BATCH_INDEX+1)*BATCH_SIZE]
print('Universe:', len(TICKERS), 'batch:', BATCH_INDEX+1, '/', TOTAL_BATCHES, 'size:', len(batch))
qb = QuantBook()

# Candidate aliases are hypotheses, not verified corporate-action mappings.
# Potentially ambiguous aliases are deliberately NOT auto-accepted.
FORMAT_ALIASES = {
    'BF-B':['BF.B'], 'BRK-B':['BRK.B'], 'FCE-A':['FCE.A'],
    'HUB-B':['HUB.B'], 'LEN-B':['LEN.B'], 'LGFA':['LGF.A'],
    'LGFB':['LGF.B'], 'CWENA':['CWEN.A'], 'NWS-A':['NWS.A'],
    'BRKB':['BRK.B'], 'BFA':['BF.A'], 'BFB':['BF.B'],
    'HEIA':['HEI.A'], 'LENB':['LEN.B'], 'UHALB':['UHAL.B'],
}
REVIEW_ALIASES = {
    'BRUKER':['BRKR'], 'VIA-B':['VIAB'], 'JW-A':['JW.A'],
    'JWA':['JW.A'], 'FNF':[],
}
# Keep these under review: automatic stitching could attach another company.
BLOCK_AUTOMATIC_ALIAS = {'ENR','PL','BTU','CR','MOS','XTSLA'}
ENABLE_REVIEW_ALIASES = False  # only enable after checking company/SID/time

def candidates(t):
    values = [t]
    values += FORMAT_ALIASES.get(t, [])
    if '-' in t: values.append(t.replace('-', '.'))
    if '.' in t: values.append(t.replace('.', '-'))
    if ENABLE_REVIEW_ALIASES and t not in BLOCK_AUTOMATIC_ALIAS:
        values += REVIEW_ALIASES.get(t, [])
    return list(dict.fromkeys(values))

def resolve_symbol(candidate, dt):
    sid = SecurityIdentifier.GenerateEquity(candidate, Market.USA, mappingResolveDate=dt)
    sym = Symbol(sid, candidate)
    sec = qb.AddSecurity(sym, Resolution.Daily)
    sec.SetDataNormalizationMode(NORMALIZATION)
    return sym

def consume(history, lookup, year, rows_by_year, counts):
    if history is None or history.empty: return
    h = history.reset_index()
    cols = {str(c).lower():c for c in h.columns}
    if 'symbol' not in cols or 'time' not in cols:
        raise ValueError('Unexpected History schema: '+str(list(h.columns)))
    required = ('open','high','low','close','volume')
    if not all(c in cols for c in required):
        raise ValueError('Missing OHLCV columns: '+str(list(h.columns)))
    for symbol_obj, piece in h.groupby(cols['symbol']):
        sid = str(symbol_obj.ID)
        if sid not in lookup: continue
        original, candidate = lookup[sid]
        frame = pd.DataFrame({
            'date':pd.to_datetime(piece[cols['time']]).dt.strftime('%Y-%m-%d'),
            'original_ticker':original,
            'qc_ticker':candidate,
            'sid':sid,
            'open':piece[cols['open']].values,
            'high':piece[cols['high']].values,
            'low':piece[cols['low']].values,
            'close':piece[cols['close']].values,
            'volume':piece[cols['volume']].values,
        })
        rows_by_year[year].append(frame)
        counts[original] += len(frame)

# A mapping date in each calendar year reduces, but does not eliminate,
# ticker reuse risk. A historical ticker must be manually verified against SID.
rows_by_year = defaultdict(list)
audit = []
identities = []
t0 = time.time()
for year in range(START_YEAR, END_YEAR+1):
    start, end = datetime(year, 1, 1), datetime(year+1, 1, 1)
    anchor = datetime(year, 6, 30)
    tasks = []
    candidate_errors = defaultdict(list)
    for original in batch:
        try:
            symbol = resolve_symbol(original, anchor)
            tasks.append((original, original, symbol))
            identities.append(dict(year=year, original_ticker=original, candidate=original,
                                   sid=str(symbol.ID), anchor_date=anchor.date().isoformat(),
                                   mapping_type='ORIGINAL_ATTEMPT'))
        except Exception as exc:
            candidate_errors[original].append('original: '+str(exc)[:200])
    counts = defaultdict(int)
    errors = {}
    for k in range(0, len(tasks), HISTORY_GROUP_SIZE):
        group = tasks[k:k+HISTORY_GROUP_SIZE]
        lookup = {str(s.ID):(o,c) for o,c,s in group}
        try:
            consume(qb.History([s for _,_,s in group],start,end,Resolution.Daily),lookup,year,rows_by_year,counts)
        except Exception as exc:
            print('Year',year,'group',k//HISTORY_GROUP_SIZE,'failed; retrying individually:',str(exc)[:160])
            for original,candidate,symbol in group:
                try:
                    consume(qb.History([symbol],start,end,Resolution.Daily),
                            {str(symbol.ID):(original,candidate)},year,rows_by_year,counts)
                except Exception as e:
                    errors[original] = str(e)[:300]
                    
    # Retry alternate formatting candidates ONLY when the original returned no bars.
    # This is important: AddSecurity success does NOT mean History has data.
    missing = [t for t in batch if counts[t] == 0]
    for original in missing:
        for candidate in candidates(original)[1:]:
            try:
                sym = resolve_symbol(candidate, anchor)
                fallback_history = qb.History([sym], start, end, Resolution.Daily)
                if fallback_history is None or fallback_history.empty:
                    continue
                before = counts[original]
                consume(fallback_history, {str(sym.ID):(original,candidate)},year,rows_by_year,counts)
                if counts[original] > before:
                    identities.append(dict(year=year, original_ticker=original,
                                           candidate=candidate, sid=str(sym.ID),
                                           anchor_date=anchor.date().isoformat(),
                                           mapping_type='FALLBACK_NEEDS_REVIEW'))
                    break
            except Exception as exc:
                candidate_errors[original].append(candidate+': '+str(exc)[:200])

    for original in batch:
        status = 'HAS_BARS' if counts[original] else (
            'HISTORY_ERROR' if original in errors else
            'RESOLVE_OR_FALLBACK_ERROR' if candidate_errors[original] else 'EMPTY'
        )
        audit.append(dict(year=year, original_ticker=original, status=status,
                          bars=counts[original],
                          error=errors.get(original,'')+' | '.join(candidate_errors[original])))
    print(year, 'bars:',sum(counts.values()),'tickers with bars:',sum(v>0 for v in counts.values()),
          'errors:',len(errors))

batch_label = 'batch_%02d_of_%02d' % (BATCH_INDEX+1,TOTAL_BATCHES)
zip_name = 'russell_market_%s.zip' % batch_label
n_rows=0
with zipfile.ZipFile(zip_name,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for year, frames in sorted(rows_by_year.items()):
        if not frames: continue
        df = pd.concat(frames,ignore_index=True)
        # Do not silently merge conflicting data from different SIDs.
        df = df.drop_duplicates(['date','original_ticker','sid']).sort_values(['original_ticker','date'])
        n_rows += len(df)
        z.writestr('raw/year=%d/%s.csv' % (year,batch_label),df.to_csv(index=False))
    z.writestr('audit/%s_status.csv' % batch_label,pd.DataFrame(audit).to_csv(index=False))
    z.writestr('audit/%s_identity.csv' % batch_label,pd.DataFrame(identities).to_csv(index=False))
    z.writestr('audit/%s_summary.json' % batch_label,json.dumps({
        'batch_index':BATCH_INDEX,'total_batches':TOTAL_BATCHES,
        'tickers':len(batch),'rows':n_rows,'start_year':START_YEAR,
        'end_year':END_YEAR,'normalization':'Raw',
        'warning':'SID identity and aliases require independent verification; Raw OHLCV is not split-adjusted'
    },indent=2))
print('Done:',zip_name,'rows:',n_rows,'elapsed minutes:',round((time.time()-t0)/60,1))
# Notebook links can be large. For large ZIPs use QC ObjectStore/cloud storage
# instead of embedding a huge base64 link in the notebook output.
if __import__('os').path.getsize(zip_name) < 25*1024*1024:
    with open(zip_name,'rb') as f:
        encoded = base64.b64encode(f.read()).decode()
    display(HTML('<a download="%s" href="data:application/zip;base64,%s">Download %s</a>'
                 % (zip_name,encoded,zip_name)))
else:
    print('ZIP >25MB: saved in notebook working directory; use QC supported export/storage workflow.')
print('Review audit status and SID identity before accepting this batch.')
