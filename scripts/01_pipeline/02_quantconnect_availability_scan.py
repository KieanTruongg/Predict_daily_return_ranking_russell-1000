# ==============================================================================
# [CLOUD-ONLY] QUANTCONNECT RESEARCH NOTEBOOK: RUSSELL 1000 AVAILABILITY SCAN (2000 - 2026)
# Execution environment: QuantConnect LEAN Cloud Research Notebook (Cloud-Only).
# ==============================================================================
# Script này dùng để kiểm tra tính sẵn sàng (Availability Scan) của 26,919 lượt
# cổ phiếu trong rổ Russell 1000 qua 27 năm (2000 - 2026) trên QuantConnect.
#
# Kết quả thực nghiệm ngày 02/11/2026:
# - Tổng lượt cổ phiếu: 26,919 ticker-years (2,884 mã duy nhất)
# - Khớp dữ liệu (MATCH): 26,656 (99.02%)
# - Không có dữ liệu (EMPTY): 263 (0.98%)
# ==============================================================================

import base64
import zlib
import json
import os
import gc
from datetime import datetime

import pandas as pd
from AlgorithmImports import *

qb = QuantBook()

# 1) Decode danh sách Russell 1000 Point-in-Time 27 năm (2000-2026)
_B64_DATA = (
    "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"
    "760Ex+vURvMgOE7yiojGc0zIDp+W4//9f1k6gfQ="
)
pit_universe = json.loads(zlib.decompress(base64.b64decode(_B64_DATA)).decode("utf-8"))

# 2) Scan settings
FIRST_YEAR = 2000
LAST_YEAR = 2026
YEAR_TO_RUN = None       # None = scan all years; hoặc set e.g. 2000 để chạy 1 năm
BATCH_SIZE = 40          # batch size tối ưu bộ nhớ
OUTPUT_DIR = os.path.join(os.getcwd(), "russell1000_scan")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY = datetime.utcnow().date()


def symbol_key(value):
    """Chuẩn hóa QC Symbol / string index values thành ticker key."""
    if hasattr(value, "Value"):
        return str(value.Value).upper()
    return str(value).upper().split(" ")[0]


def get_symbol_counts(history):
    """Đếm số phiên giao dịch cho từng symbol từ QC MultiIndex DataFrame."""
    if history is None or len(history) == 0:
        return {}

    if not isinstance(history.index, pd.MultiIndex):
        return {symbol_key(history.index.name or ""): len(history)}

    names = list(history.index.names)
    level = names.index("symbol") if "symbol" in names else 0

    counts = {}
    for raw_symbol, count in history.groupby(level=level).size().items():
        counts[symbol_key(raw_symbol)] = int(count)
    return counts


def scan_one_year(year):
    tickers = sorted(set(str(t).upper() for t in pit_universe[str(year)]))
    start = datetime(year, 6, 30)
    end = datetime(year + 1, 6, 30)
    if end.date() > TODAY:
        end = datetime.combine(TODAY, datetime.min.time())

    if end <= start:
        print("Bỏ qua năm {}: không có cửa sổ quét hợp lệ".format(year))
        return pd.DataFrame()

    rows = []
    print("\nNĂM {} | {} tickers | {} -> {}".format(
        year, len(tickers), start.date(), end.date()
    ))

    for offset in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[offset:offset + BATCH_SIZE]
        symbols = []
        symbol_to_ticker = {}

        for ticker in batch:
            try:
                sid = SecurityIdentifier.GenerateEquity(
                    ticker,
                    Market.USA,
                    mappingResolveDate=start
                )
                symbol = Symbol(sid, ticker)
                symbols.append(symbol)
                symbol_to_ticker[symbol_key(symbol)] = ticker
            except Exception as exc:
                rows.append({
                    "year": year, "ticker": ticker, "status": "ERROR",
                    "rows": 0, "reason": "SYMBOL_CREATE: " + str(exc)[:300]
                })

        if not symbols:
            continue

        try:
            history = qb.History(symbols, start, end, Resolution.Daily)
            counts = get_symbol_counts(history)

            for symbol in symbols:
                ticker = symbol_to_ticker[symbol_key(symbol)]
                n = counts.get(symbol_key(symbol), 0)
                rows.append({
                    "year": year,
                    "ticker": ticker,
                    "status": "MATCH" if n > 0 else "EMPTY",
                    "rows": n,
                    "reason": "HAS_ROWS_IN_WINDOW" if n > 0 else "NO_ROWS_IN_WINDOW"
                })

        except Exception as exc:
            error_text = str(exc).replace("\n", " ")[:500]
            for symbol in symbols:
                ticker = symbol_to_ticker[symbol_key(symbol)]
                rows.append({
                    "year": year, "ticker": ticker, "status": "ERROR",
                    "rows": 0, "reason": error_text
                })

        print("  Đã quét {}/{} | batch {}".format(
            min(offset + BATCH_SIZE, len(tickers)), len(tickers),
            offset // BATCH_SIZE + 1
        ))
        del history
        gc.collect()

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["year", "ticker"]).reset_index(drop=True)
    return result


# 3) Tiến hành quét và lưu checkpoint từng năm
if YEAR_TO_RUN is None:
    years = list(range(FIRST_YEAR, LAST_YEAR + 1))
else:
    years = [YEAR_TO_RUN]

all_results = []
for year in years:
    year_result = scan_one_year(year)
    if year_result.empty:
        continue

    checkpoint_path = os.path.join(OUTPUT_DIR, "russell1000_scan_{}.csv".format(year))
    year_result.to_csv(checkpoint_path, index=False)
    all_results.append(year_result)

    print("Đã lưu checkpoint:", checkpoint_path)
    print(year_result["status"].value_counts().to_dict())

if all_results:
    audit = pd.concat(all_results, ignore_index=True)
    audit_path = os.path.join(OUTPUT_DIR, "russell1000_scan_all.csv")
    audit.to_csv(audit_path, index=False)

    summary = (audit.groupby(["year", "status"])["ticker"]
                    .count().unstack(fill_value=0))
    print("\n===== TỔNG KẾT KHẢ DỤNG 27 NĂM =====")
    display(summary)
    print("\nFile tổng kết đã lưu tại:", audit_path)
else:
    print("Không có kết quả scan nào được tạo ra.")
