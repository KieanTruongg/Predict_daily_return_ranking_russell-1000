"""
Script: scripts/01_pipeline/generate_qc_export_script.py
Purpose: Regenerate scripts/01_pipeline/02_quantconnect_export_by_year.py using the proven QuantConnect Cloud AddEquity API:
  1. Detailed error logging & failure reasons
  2. Multi-directional ticker candidate mapping (. ↔ - ↔ / ↔ empty)
  3. qb.AddEquity(cand, Resolution.Daily) with SetDataNormalizationMode(SplitAdjusted)
  4. Structured Audit Trail output (audit_russell1000_{year}.csv included in ZIP)
  5. Trading Days sufficiency check (Full >= 150 days vs Partial < 150 days vs Empty)
  6. Explicit DataNormalizationMode.SplitAdjusted
"""
import os, json, sys, io, zlib, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIT_JSON = os.path.join(BASE, "data", "raw", "universe", "russell1000_pit_by_year.json")
OUT_PY   = os.path.join(BASE, "scripts", "01_pipeline", "02_quantconnect_export_by_year.py")

with open(PIT_JSON, "r", encoding="utf-8") as f:
    pit = json.load(f)

# Sort keys and ticker lists
pit_sorted = {k: sorted(list(set(v))) for k, v in sorted(pit.items(), key=lambda x: int(x[0]))}
raw_bytes = json.dumps(pit_sorted).encode('utf-8')
b64_compressed = base64.b64encode(zlib.compress(raw_bytes)).decode('ascii')

code = f'''# ==============================================================================
# QUANTCONNECT RESEARCH NOTEBOOK SCRIPT: EXPORT BY YEAR (2000 - 2026) (PROVEN WORKING)
# Incorporating 6 Major Improvements:
#   1. Detailed Failure Reason Logging (No silent exception swallowing)
#   2. Multi-Directional Ticker Mapping (. ↔ - ↔ /)
#   3. qb.AddEquity() with Symbol Resolution
#   4. Structured Audit Trail CSV (audit_russell1000_{{year}}.csv)
#   5. Data Sufficiency Verification (Full >= 150 days vs Partial < 150 days)
#   6. Explicit DataNormalizationMode (SplitAdjusted for Return Ranking)
# ==============================================================================
import base64
import zlib
import json
import zipfile
import os
import gc
from datetime import datetime
from IPython.display import HTML, display
from AlgorithmImports import *

qb = QuantBook()

# 1. Danh sách Universe Russell 1000 (Zlib Compressed)
_B64_DATA = "{b64_compressed}"
pit_universe = json.loads(zlib.decompress(base64.b64decode(_B64_DATA)).decode('utf-8'))

def get_zip_download_html(zip_filename, year, success_cnt, partial_cnt, empty_cnt, fail_cnt, size_mb):
    with open(zip_filename, "rb") as f:
        bytes_data = f.read()
    b64 = base64.b64encode(bytes_data).decode()
    return f"""
    <div style="margin: 10px 0; padding: 15px; border: 2px solid #2e7d32; background-color: #e8f5e9; border-radius: 8px;">
        <h3 style="color: #2e7d32; margin-top: 0;">✅ Tải file dữ liệu năm {{year}} (Kèm Audit Log CSV)</h3>
        <p>
           <b>Thành công (Full >= 150d):</b> {{success_cnt}} | 
           <b>Một phần (< 150d):</b> {{partial_cnt}} | 
           <b>Không có data:</b> {{empty_cnt}} | 
           <b>Lỗi:</b> {{fail_cnt}}<br/>
           <b>Dung lượng file ZIP:</b> {{size_mb:.2f}} MB
        </p>
        <a download="{{zip_filename}}" href="data:application/zip;base64,{{b64}}" 
           style="background-color: #2e7d32; color: white; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">
           ⬇️ TẢI FILE ZIP NĂM {{year}} (DATA + AUDIT REPORT)
        </a>
    </div>
    """

print("🚀 BẮT ĐẦU TIẾN TRÌNH XUẤT DỮ LIỆU AUDIT-GRADE RUSSELL 1000 (2000 - 2026)...")

for year_str, tickers in pit_universe.items():
    year = int(year_str)
    start_date = datetime(year, 1, 1)
    end_date = datetime(2026, 10, 1) if year == 2026 else datetime(year, 12, 31)

    zip_filename = f"russell1000_{{year}}.zip"
    print(f"\\n==================================================================")
    print(f"⏳ ĐANG XỬ LÝ NĂM {{year}} (Tổng số mã PIT: {{len(tickers)}})...")
    
    zip_file = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
    
    audit_rows = ["russell_ticker,qc_candidate,qc_symbol,status,reason,trading_days,min_date,max_date"]
    
    success_cnt = 0
    partial_cnt = 0
    empty_cnt = 0
    fail_cnt = 0

    for idx, ticker in enumerate(tickers, 1):
        # 2. Multi-directional candidate list
        candidates = [ticker]
        if "-" in ticker:
            candidates.append(ticker.replace("-", "."))
            candidates.append(ticker.replace("-", ""))
        elif "." in ticker:
            candidates.append(ticker.replace(".", "-"))
            candidates.append(ticker.replace(".", ""))
        if "/" in ticker:
            candidates.append(ticker.replace("/", "."))
            candidates.append(ticker.replace("/", "-"))

        matched_symbol = None
        matched_cand = None
        df_matched = None
        last_error = ""

        # 3. Security Identity resolution & history query via AddEquity
        for cand in dict.fromkeys(candidates):
            try:
                equity = qb.AddEquity(cand, Resolution.Daily)
                equity.SetDataNormalizationMode(DataNormalizationMode.SplitAdjusted)
                symbol = equity.Symbol
                
                df_temp = qb.History(symbol, start_date, end_date, Resolution.Daily)
                if not df_temp.empty:
                    df_matched = df_temp
                    matched_symbol = str(symbol.Value)
                    matched_cand = cand
                    break
                else:
                    last_error = "EMPTY_HISTORY"
            except Exception as e:
                last_error = f"ADD_EQUITY_ERROR: {{str(e).replace(',', ';')}}"

        # 4 & 5. Audit Logging & Sufficiency Verification
        if df_matched is not None and not df_matched.empty:
            if hasattr(df_matched.index, 'nlevels') and df_matched.index.nlevels > 1:
                df_matched = df_matched.droplevel(0)

            trading_days = len(df_matched)
            min_d = str(df_matched.index.min().date()) if not df_matched.empty else ""
            max_d = str(df_matched.index.max().date()) if not df_matched.empty else ""
            
            if trading_days >= 150:
                status = "SUCCESS"
                reason = "FULL_STOCK_YEAR"
                success_cnt += 1
            else:
                status = "PARTIAL"
                reason = f"PARTIAL_STOCK_YEAR ({{trading_days}}d)"
                partial_cnt += 1

            csv_name = f"{{ticker}}_{{year}}.csv"
            zip_file.writestr(csv_name, df_matched.to_csv())
            
            audit_rows.append(f"{{ticker}},{{matched_cand}},{{matched_symbol}},{{status}},{{reason}},{{trading_days}},{{min_d}},{{max_d}}")
        else:
            if last_error == "EMPTY_HISTORY":
                status = "EMPTY"
                reason = "QC_DATABASE_NO_RECORDS"
                empty_cnt += 1
            else:
                status = "FAILED"
                reason = last_error if last_error else "UNKNOWN_ERROR"
                fail_cnt += 1

            audit_rows.append(f"{{ticker}},NONE,NONE,{{status}},{{reason}},0,,")

        if idx % 200 == 0 or idx == len(tickers):
            print(f"   ► [{{idx}}/{{len(tickers)}}] Full: {{success_cnt}} | Partial: {{partial_cnt}} | Empty: {{empty_cnt}} | Fail: {{fail_cnt}}")

    # Save audit report into ZIP
    audit_csv_content = "\\n".join(audit_rows)
    zip_file.writestr(f"audit_russell1000_{{year}}.csv", audit_csv_content)
    zip_file.close()

    if os.path.exists(zip_filename) and os.path.getsize(zip_filename) > 0:
        file_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
        print(f"✅ NĂM {{year}}: Full={{success_cnt}} | Partial={{partial_cnt}} | Empty={{empty_cnt}} | Fail={{fail_cnt}} | ZIP: {{file_size_mb:.2f}}MB")
        display(HTML(get_zip_download_html(zip_filename, year, success_cnt, partial_cnt, empty_cnt, fail_cnt, file_size_mb)))
        try:
            os.remove(zip_filename)
        except Exception:
            pass
    else:
        print(f"⚠️ Năm {{year}} không xuất được dữ liệu.")

    gc.collect()

print("\\n==================================================================")
print("✨ HOÀN TẤT BÁO CÁO AUDIT-GRADE! CÁC FILE ZIP ĐÃ BAO GỒM CẢ FILE AUDIT CSV CHO TỪNG NĂM.")
'''

with open(OUT_PY, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Successfully generated PROVEN WORKING QuantConnect script ({len(code)} chars) at: {OUT_PY}")
