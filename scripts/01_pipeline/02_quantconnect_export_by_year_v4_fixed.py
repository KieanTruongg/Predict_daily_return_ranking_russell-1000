# ==============================================================================
# QUANTCONNECT RESEARCH NOTEBOOK SCRIPT: EXPORT BY YEAR (2000 - 2026) v4
# POINT-IN-TIME SECURITY IDENTITY RESOLUTION
# Incorporating 6 Major Improvements:
#   1. Detailed Failure Reason Logging (No silent exception swallowing)
#   2. Multi-Directional Ticker Mapping (. ↔ - ↔ /)
#   3. Security Identity & QC Symbol Resolution
#   4. Structured Audit Trail CSV (audit_russell1000_{year}.csv)
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
_B64_DATA = "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"
pit_universe = json.loads(zlib.decompress(base64.b64decode(_B64_DATA)).decode('utf-8'))

def get_zip_download_html(zip_filename, year, success_cnt, partial_cnt, empty_cnt, fail_cnt, size_mb):
    with open(zip_filename, "rb") as f:
        bytes_data = f.read()
    b64 = base64.b64encode(bytes_data).decode()
    return f"""
    <div style="margin: 10px 0; padding: 15px; border: 2px solid #2e7d32; background-color: #e8f5e9; border-radius: 8px;">
        <h3 style="color: #2e7d32; margin-top: 0;">✅ Tải file dữ liệu năm {year} (Kèm Audit Log CSV)</h3>
        <p>
           <b>Thành công (Full >= 150d):</b> {success_cnt} | 
           <b>Một phần (< 150d):</b> {partial_cnt} | 
           <b>Không có data:</b> {empty_cnt} | 
           <b>Lỗi:</b> {fail_cnt}<br/>
           <b>Dung lượng file ZIP:</b> {size_mb:.2f} MB
        </p>
        <a download="{zip_filename}" href="data:application/zip;base64,{b64}" 
           style="background-color: #2e7d32; color: white; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">
           ⬇️ TẢI FILE ZIP NĂM {year} (DATA + AUDIT REPORT)
        </a>
    </div>
    """

print("🚀 BẮT ĐẦU TIẾN TRÌNH XUẤT DỮ LIỆU AUDIT-GRADE RUSSELL 1000 (2000 - 2026)...")

for year_str, tickers in pit_universe.items():
    year = int(year_str)
    start_date = datetime(year, 1, 1)
    end_date = datetime(2026, 10, 1) if year == 2026 else datetime(year, 12, 31)

    # Annual convention for resolving the historical security identity.
    # Replace with the exact Russell effective date if your source provides one.
    mapping_date = datetime(year, 6, 30)
    
    zip_filename = f"russell1000_{year}.zip"
    print(f"\n==================================================================")
    print(f"⏳ ĐANG XỬ LÝ NĂM {year} (Tổng số mã PIT: {len(tickers)})...")
    
    zip_file = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
    
    audit_rows = ["russell_ticker,qc_candidate,qc_symbol,mapping_date,status,reason,trading_days,min_date,max_date"]
    
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

        # 3. Point-in-Time Security Identity resolution & history query
        #
        # DO NOT use AddEquity(cand) here. AddEquity can resolve a ticker to
        # the current/default security identity, causing old history to look
        # EMPTY even when the historical data exists.
        for cand in dict.fromkeys(candidates):
            try:
                sid = SecurityIdentifier.GenerateEquity(
                    cand,
                    Market.USA,
                    mappingResolveDate=mapping_date
                )
                symbol = Symbol(sid, cand)

                # Register the exact point-in-time Symbol as a daily security.
                security = qb.AddSecurity(symbol, Resolution.Daily)
                security.SetDataNormalizationMode(DataNormalizationMode.SplitAdjusted)

                df_temp = qb.History(
                    symbol,
                    start_date,
                    end_date,
                    Resolution.Daily
                )

                if not df_temp.empty:
                    df_matched = df_temp
                    matched_symbol = str(symbol.Value)
                    matched_cand = cand
                    break
                else:
                    last_error = "EMPTY_HISTORY"

            except Exception as e:
                last_error = f"SECURITY_ID_ERROR: {str(e).replace(',', ';')}"

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
                reason = f"PARTIAL_STOCK_YEAR ({trading_days}d)"
                partial_cnt += 1

            csv_name = f"{ticker}_{year}.csv"
            zip_file.writestr(csv_name, df_matched.to_csv())
            
            audit_rows.append(f"{ticker},{matched_cand},{matched_symbol},{mapping_date.date()},{status},{reason},{trading_days},{min_d},{max_d}")
        else:
            if last_error == "EMPTY_HISTORY":
                status = "EMPTY"
                reason = "EMPTY_HISTORY_FOR_PIT_SECURITY_ID"
                empty_cnt += 1
            else:
                status = "FAILED"
                reason = last_error if last_error else "UNKNOWN_ERROR"
                fail_cnt += 1

            audit_rows.append(f"{ticker},NONE,NONE,{mapping_date.date()},{status},{reason},0,,")

        if idx % 200 == 0 or idx == len(tickers):
            print(f"   ► [{idx}/{len(tickers)}] Full: {success_cnt} | Partial: {partial_cnt} | Empty: {empty_cnt} | Fail: {fail_cnt}")

    # Save audit report into ZIP
    audit_csv_content = "\n".join(audit_rows)
    zip_file.writestr(f"audit_russell1000_{year}.csv", audit_csv_content)
    zip_file.close()

    if os.path.exists(zip_filename) and os.path.getsize(zip_filename) > 0:
        file_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
        print(f"✅ NĂM {year}: Full={success_cnt} | Partial={partial_cnt} | Empty={empty_cnt} | Fail={fail_cnt} | ZIP: {file_size_mb:.2f}MB")
        display(HTML(get_zip_download_html(zip_filename, year, success_cnt, partial_cnt, empty_cnt, fail_cnt, file_size_mb)))
        try:
            os.remove(zip_filename)
        except Exception:
            pass
    else:
        print(f"⚠️ Năm {year} không xuất được dữ liệu.")

    gc.collect()

print("\n==================================================================")
print("✨ HOÀN TẤT BÁO CÁO AUDIT-GRADE! CÁC FILE ZIP ĐÃ BAO GỒM CẢ FILE AUDIT CSV CHO TỪNG NĂM.")
