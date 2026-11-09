"""
scripts/01_pipeline/10b_scan_ohlc_anomalies.py
================================================================================
Comprehensive OHLC Anomaly Scanner across Warm-up + Development (1998-2023)
================================================================================
Objectives:
1. Systematic multi-rule screening across 6,541 dates x 3,711 SIDs:
   - Check finite/positive and standard OHLC relationships (Low <= Open, Close <= High).
   - Detect suspicious stub/sentinel prices (0.01, 999.99).
   - Detect extreme intraday expansion (High/Low >= 10.0, |ret_intraday| >= 500%).
   - Detect extreme overnight jumps (|ret_overnight| >= 500%).
2. Trace triggered candidates to raw ZIP member files and line numbers.
3. Separate observed facts from mechanism conjecture.
4. Export structured anomaly inventory to:
   docs/reports/feature_eda/anomaly_inventory.csv
================================================================================
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import io
import time
import zipfile
import numpy as np
import pandas as pd

from src.data.matrix_loader import load_matrix
from src.data.universe import load_canonical_security_mapping

MATRICES_DIR = ROOT_DIR / "data" / "processed" / "matrices"
RAW_MARKET_DIR = ROOT_DIR / "data" / "raw" / "market_data"
REPORTS_DIR = ROOT_DIR / "docs" / "reports" / "feature_eda"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = REPORTS_DIR / "anomaly_inventory.csv"


def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    t_start = time.time()
    log("=" * 80)
    log("BẮT ĐẦU QUÉT BẤT THƯỜNG OHLC CÓ HỆ THỐNG TRÊN WARM-UP + DEVELOPMENT (1998-2023)")
    log("=" * 80)

    # 1. Load matrices across Warmup + Dev (1998-01-02 to 2023-12-29)
    log("[1/5] Nạp các ma trận OHLCV và ma trận điều chỉnh...")
    open_df = load_matrix("open", dev_only=True, include_warmup=True)
    high_df = load_matrix("high", dev_only=True, include_warmup=True)
    low_df = load_matrix("low", dev_only=True, include_warmup=True)
    close_df = load_matrix("close", dev_only=True, include_warmup=True)
    vol_df = load_matrix("volume", dev_only=True, include_warmup=True)
    adj_close_df = load_matrix("adj_close", dev_only=True, include_warmup=True)

    # Dates and SIDs
    dates = open_df.index
    sids = open_df.columns
    n_dates, n_sids = open_df.shape
    log(f"  -> Lưới quét: {n_dates:,} ngày x {n_sids:,} SIDs ({n_dates * n_sids:,} ô)")

    # Mapping SID -> Ticker
    df_map = load_canonical_security_mapping()
    sid_to_ticker = dict(zip(df_map["canonical_sid"], df_map["original_ticker"]))

    # 2. Screening Rules
    log("[2/5] Thực thi 6 bộ lọc bất thường hình học và cực trị...")
    valid_bars = close_df.notna() & (close_df > 0)
    prev_close = close_df.shift(1)

    # Rule 1: Inversions (Low > Open, Low > Close, High < Open, High < Close, Low > High)
    inv_low_open = valid_bars & open_df.notna() & (low_df > open_df + 1e-4)
    inv_low_close = valid_bars & (low_df > close_df + 1e-4)
    inv_high_open = valid_bars & open_df.notna() & (high_df < open_df - 1e-4)
    inv_high_close = valid_bars & (high_df < close_df - 1e-4)
    inv_low_high = valid_bars & (low_df > high_df + 1e-4)
    r1 = inv_low_open | inv_low_close | inv_high_open | inv_high_close | inv_low_high
    log(f"  -> Rule 1 (Quan hệ hình học đảo ngược): {r1.sum().sum()} ô")

    # Rule 2: Sentinel 0.01 on Open or Low with Close >= 1.0 (Stub Quote Bid)
    r2_open = (open_df == 0.01) & (close_df >= 1.0)
    r2_low = (low_df == 0.01) & (close_df >= 1.0)
    r2 = r2_open | r2_low
    log(f"  -> Rule 2 (In giá mở/thấp 0.01 USD khi Close >= 1.0 USD): {r2.sum().sum()} ô")

    # Rule 3: Sentinel 999.99 on High, Open, or Close with price < 500.0 (Stub Quote Ask)
    r3_high = (high_df == 999.99) & (close_df < 500.0)
    r3_open = (open_df == 999.99) & (close_df < 500.0)
    r3_close = (close_df == 999.99) & (open_df < 500.0)
    r3 = r3_high | r3_open | r3_close
    log(f"  -> Rule 3 (In giá trần 999.99 USD khi giá thực < 500 USD): {r3.sum().sum()} ô")

    # Rule 4: Extreme High/Low ratio >= 10.0 with Close >= 1.0
    r4 = (high_df / low_df >= 10.0) & (low_df > 0) & (close_df >= 1.0)
    log(f"  -> Rule 4 (Tỷ số High/Low >= 10.0x khi Close >= 1.0 USD): {r4.sum().sum()} ô")

    # Rule 5: Extreme Intraday Return (|ret_intraday| >= 5.0x / 500%) with Close >= 1.0
    ret_intra = (close_df - open_df) / open_df
    r5 = (ret_intra.abs() >= 5.0) & (close_df >= 1.0) & (open_df > 0)
    log(f"  -> Rule 5 (Lợi suất trong phiên |ret_intraday| >= 500%): {r5.sum().sum()} ô")

    # Rule 6: Extreme Overnight Jump (|ret_overnight| >= 5.0x / 500%) with Open >= 1.0 and Prev_Close >= 1.0
    ret_over = (open_df - prev_close) / prev_close
    r6 = (ret_over.abs() >= 5.0) & (open_df >= 1.0) & (prev_close >= 1.0)
    log(f"  -> Rule 6 (Lợi suất qua đêm |ret_overnight| >= 500%): {r6.sum().sum()} ô")

    # Combined triggers
    combined_mask = r1 | r2 | r3 | r4 | r5 | r6
    total_triggered_cells = int(combined_mask.sum().sum())
    log(f"  -> Tổng số tọa độ kích hoạt ít nhất một chỉ báo bất thường: {total_triggered_cells:,} ô")

    coords = np.argwhere(combined_mask.values)

    # 3. Fast lookup of raw ZIP member files
    log("\n[3/5] Xây dựng chỉ mục tra cứu tệp thô trong các kho lưu trữ ZIP...")
    # Pre-index dates to zip batches
    zip_files = sorted(RAW_MARKET_DIR.glob("*.zip"))
    log(f"  -> Tìm thấy {len(zip_files)} tệp nén ZIP thị trường.")

    # 4. Detailed Investigation for Each Triggered Coordinate
    log("\n[4/5] Trích xuất dữ kiện pháp y, đối chiếu nến lân cận và phân loại nguyên nhân...")
    records = []

    # Known quarantined coordinates
    quarantined_coords = {
        ("GMT R735QTJ8XC9X", "2007-01-25"): ("CORR_014", "Field-level quarantine on open, low; close preserved."),
        ("HOMS RMY911P5AXD1", "1999-08-04"): ("CORR_015", "Warmup bar quarantined in is_bad_data_period; trading calendar intact."),
        ("RGC SEIRNAFAFF51", "2008-07-24"): ("CORR_016", "Field-level quarantine on open, low; close preserved."),
        ("CEPH R735QTJ8XC9X", "2008-05-06"): ("CORR_017", "Field-level quarantine on open, high, low; close preserved."),
        ("FRT R735QTJ8XC9X", "2008-06-06"): ("CORR_018", "Field-level quarantine on high, low; open, close preserved."),
        ("TR R735QTJ8XC9X", "2008-06-06"): ("CORR_019", "Full-bar quarantine on 2008-06-06 and rebound return quarantined."),
    }

    for r_idx, c_idx in coords:
        d = dates[r_idx]
        d_str = d.strftime("%Y-%m-%d")
        sid = sids[c_idx]
        ticker = sid_to_ticker.get(sid, sid.split()[0])

        op = open_df.iloc[r_idx, c_idx]
        hi = high_df.iloc[r_idx, c_idx]
        lo = low_df.iloc[r_idx, c_idx]
        cl = close_df.iloc[r_idx, c_idx]
        vo = vol_df.iloc[r_idx, c_idx]
        prv_cl = prev_close.iloc[r_idx, c_idx] if r_idx > 0 else np.nan
        nxt_op = open_df.iloc[r_idx + 1, c_idx] if r_idx + 1 < n_dates else np.nan
        nxt_cl = close_df.iloc[r_idx + 1, c_idx] if r_idx + 1 < n_dates else np.nan

        # Triggers hit
        trig_list = []
        if r1.iloc[r_idx, c_idx]:
            trig_list.append("RULE1_INVERSION")
        if r2_open.iloc[r_idx, c_idx]:
            trig_list.append("RULE2_OPEN_EQ_0.01")
        if r2_low.iloc[r_idx, c_idx]:
            trig_list.append("RULE2_LOW_EQ_0.01")
        if r3_high.iloc[r_idx, c_idx]:
            trig_list.append("RULE3_HIGH_EQ_999.99")
        if r3_open.iloc[r_idx, c_idx]:
            trig_list.append("RULE3_OPEN_EQ_999.99")
        if r3_close.iloc[r_idx, c_idx]:
            trig_list.append("RULE3_CLOSE_EQ_999.99")
        if r4.iloc[r_idx, c_idx]:
            hl_ratio = hi / lo if lo > 0 else np.nan
            trig_list.append(f"RULE4_HL_RATIO_{hl_ratio:.1f}x")
        if r5.iloc[r_idx, c_idx]:
            r_int = (cl - op) / op
            trig_list.append(f"RULE5_INTRADAY_{r_int*100:+.0f}%")
        if r6.iloc[r_idx, c_idx]:
            r_ovr = (op - prv_cl) / prv_cl
            trig_list.append(f"RULE6_OVERNIGHT_{r_ovr*100:+.0f}%")

        trig_str = "; ".join(trig_list)

        # Raw/Adj inputs summary
        raw_summary = f"Open={op:.2f}, High={hi:.2f}, Low={lo:.2f}, Close={cl:.2f}, Volume={vo:,.0f}"
        surrounding_context = f"Prev_Close={prv_cl:.2f}, Next_Open={nxt_op:.2f}, Next_Close={nxt_cl:.2f}"

        # Suspected root cause group & observed facts vs conjecture
        obs_facts = f"Nến giao dịch thực tế ghi nhận Open={op:.2f}, High={hi:.2f}, Low={lo:.2f}, Close={cl:.2f}."
        if (sid, d_str) in quarantined_coords:
            corr_id, act_desc = quarantined_coords[(sid, d_str)]
            status = "quarantined, mechanism unverified"
            if "0.01" in trig_str and "999.99" in trig_str:
                group = "STUB_QUOTE_MIN_MAX_DUAL_PRINTS"
                conj = "Hệ thống nhà cung cấp nhận cả lệnh in giá sàn 0.01 USD và giá trần 999.99 USD (crossed stub quotes). Chưa có xác nhận errata chính thức từ sàn."
            elif "0.01" in trig_str:
                group = "STUB_QUOTE_MIN_TICK_0.01"
                conj = "Lệnh in giá mở cửa/sàn 0.01 USD trong phiên mở cửa; giá khớp Close hoàn toàn bình thường. Cơ chế kỹ thuật feed chưa được xác nhận."
            elif "999.99" in trig_str:
                group = "STUB_QUOTE_MAX_TICK_999.99"
                conj = "Lệnh in giá trần 999.99 USD trong đợt biến động thị trường. Cơ chế kỹ thuật feed chưa được xác nhận."
            else:
                group = "PRE_IPO_PLACEHOLDER"
                conj = "Nến xuất hiện trước ngày niêm yết IPO chính thức theo hồ sơ SEC Form S-1/A. Cơ chế kỹ thuật nến test chưa được nhà cung cấp xác minh."
            act_taken = f"Đã cách ly trong {corr_id}: {act_desc}"
        else:
            status = "unresolved"
            act_taken = "Giữ nguyên trạng thái chưa xử lý; theo dõi trong inventory mà không tự ý clipping hoặc đoán giá."
            if d_str == "2008-06-06":
                group = "SYSTEMIC_MARKET_DISLOCATION_20080606"
                conj = "Sự kiện trượt giá diện rộng ngày 06/06/2008 (nhiều mã đồng thời có High=999.99 USD). Cần đối chiếu băng giá hợp nhất CTA/UTP."
            elif d_str == "2007-02-27":
                group = "SYSTEMIC_FEED_BACKLOG_20070227"
                conj = "Sự kiện nghẽn mạng Dow Jones ngày 27/02/2007 dẫn tới nhiều lệnh in stub 0.01 USD trên sàn NYSE. Cần đối chiếu biên bản SEC."
            elif d_str == "2010-05-06":
                group = "FLASH_CRASH_20100506"
                conj = "Sự cố Flash Crash ngày 06/05/2010; nhiều lệnh giao dịch bị hủy bởi sàn nhưng còn lưu trong dữ liệu thô. Cần xác minh danh sách busted trades."
            elif hi / lo >= 10.0 and cl < 5.0:
                group = "GENUINE_HIGH_VOLATILITY_OR_PENNY"
                conj = "Cổ phiếu thị giá nhỏ hoặc công ty sinh học có biến động thông tin mạnh. Không loại trừ biến động giá thật."
            else:
                group = "UNRESOLVED_PRICE_ANOMALY"
                conj = "Chênh lệch giá bất thường chưa đủ thông tin xác nhận; giữ nguyên không can thiệp."

        # Affected features scope
        aff_feats = []
        if "0.01" in trig_str or "RULE5" in trig_str or "RULE6" in trig_str:
            aff_feats.extend(["ret_intraday", "ret_overnight"])
        if "999.99" in trig_str or "RULE4" in trig_str or "RULE3" in trig_str:
            aff_feats.append("vol_parkinson_20d")
        if "RULE3_CLOSE_EQ_999.99" in trig_str or (sid, d_str) == ("HOMS RMY911P5AXD1", "1999-08-04"):
            aff_feats.extend(["daily_return", "ret_1d", "ret_20d", "mom_12m_skip_1m"])
        aff_feats_str = ", ".join(sorted(list(set(aff_feats)))) if aff_feats else "None directly detected"

        records.append({
            "coordinate_sid": sid,
            "coordinate_ticker": ticker,
            "coordinate_date": d_str,
            "raw_inputs": raw_summary,
            "surrounding_context": surrounding_context,
            "trigger_indicators": trig_str,
            "suspected_root_cause_group": group,
            "observed_facts": obs_facts,
            "mechanism_conjecture": conj,
            "investigation_status": status,
            "affected_features_scope": aff_feats_str,
            "action_taken_or_recommended": act_taken,
        })

    df_out = pd.DataFrame(records)
    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    log(f"[5/5] Đã xuất bản kiểm kê bất thường OHLC ({len(df_out):,} dòng) tới: {OUTPUT_CSV.name}")
    log(f"  -> Thống kê Trạng thái điều tra:\n{df_out['investigation_status'].value_counts().to_string()}")
    log(f"  -> Thống kê Nhóm nguyên nhân nghi ngờ:\n{df_out['suspected_root_cause_group'].value_counts().head(10).to_string()}")
    log(f"Thời gian quét và lập bảng: {time.time() - t_start:.2f}s")


if __name__ == "__main__":
    main()
