"""
07_build_2d_matrices_and_masks.py
================================================================================
Step 4: Build 2D Matrices and 3-Tier PIT Masks (1998-2026)

Key Implementations & Academic Rigor:
1. Export Segment-Level Mapping (1 SID - 1 validity range per row):
   - universe_constituent_segments_mapping.csv
   - Fully accounts for sequential transitions and overlap conflicts.
   - Gap <= 10d is classified as HEURISTIC_UNVERIFIED (NOT verified!).
   - Ambiguous and unresolved cases are preserved with explicit exclusion policy (is_included_in_mask = False).
2. Point-In-Time Membership Mask (membership_mask.parquet):
   - Built directly from segment validity windows, NOT inferred from price bars.
   - Active strictly during [effective_start_date, effective_end_date].
   - 1998-1999 is 100% False (warm-up lookback).
3. Tradability Mask (valid_data_mask.parquet):
   - Member AND Close > 0 AND Volume > 0 AND consecutive session AND >=20 bars lookback.
4. Training Label Mask (valid_label_mask.parquet):
   - Valid data at T AND clean T+1 bar, purged at 2023-12-29 and 2026-10-30.
5. Future Targets:
   - target_next_return.parquet & target_next_total_return.parquet
================================================================================
"""

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import time
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WAREHOUSE_PATH = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet"
PIT_JSON_PATH = BASE_DIR / "data" / "raw" / "universe" / "russell1000_pit_by_year.json"
MATRICES_DIR = BASE_DIR / "data" / "processed" / "matrices"
AUDIT_TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
CANONICAL_MAP_CSV = AUDIT_TABLES_DIR / "canonical_security_mapping.csv"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    t_start = time.time()
    log("=" * 80)
    log("STEP 4: XÂY DỰNG HỆ THỐNG MA TRẬN 2D VÀ 3 LỚP PIT MASKS THEO SEGMENT MAPPING")
    log("=" * 80)

    MATRICES_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # 1. Establish Canonical Grid (Dates x Canonical SIDs)
    # --------------------------------------------------------------------------
    log("[1/6] Thẩm định lưới tọa độ chính quy (7,252 phiên NYSE x 3,711 Canonical SIDs)...")
    t0 = time.time()
    df_grid = pd.read_parquet(WAREHOUSE_PATH, columns=['date', 'canonical_sid'])
    unique_dates = pd.DatetimeIndex(sorted(df_grid['date'].unique()))
    unique_sids = sorted(df_grid['canonical_sid'].unique())
    n_dates = len(unique_dates)
    n_sids = len(unique_sids)
    del df_grid
    log(f"  -> Lưới tọa độ: {n_dates:,} ngày ({unique_dates[0].strftime('%Y-%m-%d')} đến {unique_dates[-1].strftime('%Y-%m-%d')}) "
        f"x {n_sids:,} canonical_sids ({time.time()-t0:.2f}s)")
    assert n_dates == 7252, f"Expected 7,252 dates, got {n_dates}"
    assert n_sids == 3711, f"Expected 3,711 canonical SIDs, got {n_sids}"

    pd.Series(unique_dates).to_frame(name='date').to_parquet(MATRICES_DIR / "matrix_dates_index.parquet", index=False)
    pd.Series(unique_sids).to_frame(name='canonical_sid').to_parquet(MATRICES_DIR / "matrix_columns_sids.parquet", index=False)

    sid_to_col = {sid: idx for idx, sid in enumerate(unique_sids)}

    # --------------------------------------------------------------------------
    # 2. Build & Export Segment-Level Mapping (1 SID - 1 Validity Range per Row)
    # --------------------------------------------------------------------------
    log("\n[2/6] Xuất bảng Segment-Level Mapping (1 SID - 1 khoảng hiệu lực mỗi dòng)...")
    with open(PIT_JSON_PATH, 'r', encoding='utf-8') as f:
        pit = json.load(f)

    df_map = pd.read_csv(CANONICAL_MAP_CSV, keep_default_na=False)
    df_map['min_date'] = pd.to_datetime(df_map['min_date'])
    df_map['max_date'] = pd.to_datetime(df_map['max_date'])

    map_by_ticker = defaultdict(list)
    for row in df_map.itertuples(index=False):
        map_by_ticker[row.original_ticker].append(row)

    segments = []
    for y_str in sorted(pit.keys()):
        y = int(y_str)
        p_start = pd.Timestamp(f"{y}-07-01")
        p_end = pd.Timestamp(f"{y+1}-06-30") if y < 2026 else pd.Timestamp("2026-10-30")
        tickers = pit[y_str]

        for t in tickers:
            rows = map_by_ticker.get(t, [])
            if not rows:
                segments.append({
                    'snapshot_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'canonical_sid': None,
                    'segment_index': 1,
                    'total_segments': 1,
                    'effective_start_date': None,
                    'effective_end_date': None,
                    'evidence_level': 'LEVEL_6_UNRESOLVED_NOT_IN_MAPPING',
                    'verification_status': 'UNRESOLVED',
                    'is_included_in_mask': False,
                    'exclusion_reason': 'Mã không tồn tại trong kho nến (OTC/non-equity/un-downloaded)',
                    'notes': 'Chính sách loại trừ: Giữ trong đối chiếu nhưng không kích hoạt mask'
                })
                continue

            overlaps = [r for r in rows if r.min_date <= p_end and r.max_date >= p_start]
            if not overlaps:
                segments.append({
                    'snapshot_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'canonical_sid': None,
                    'segment_index': 1,
                    'total_segments': 1,
                    'effective_start_date': None,
                    'effective_end_date': None,
                    'evidence_level': 'LEVEL_5_UNRESOLVED_ZERO_BARS',
                    'verification_status': 'UNRESOLVED',
                    'is_included_in_mask': False,
                    'exclusion_reason': 'Không có nến nào trong khoảng 12 tháng của kỳ này',
                    'notes': 'Chính sách loại trừ: Giữ trong đối chiếu nhưng không kích hoạt mask'
                })
                continue

            unique_canon_sids = list(dict.fromkeys(r.canonical_sid for r in overlaps))

            if len(unique_canon_sids) == 1:
                r0 = overlaps[0]
                eff_start = max(r0.min_date, p_start).strftime('%Y-%m-%d')
                eff_end = min(r0.max_date, p_end).strftime('%Y-%m-%d')
                rtypes = set(r.resolution_type for r in overlaps)

                if any('STITCH' in rt for rt in rtypes):
                    lvl = 'LEVEL_3_HEURISTIC_2T_STITCH'
                    stat = 'HEURISTIC_UNVERIFIED'
                    notes = 'Nối mã placeholder 2T (gap <= 10d). Giả định kỹ thuật.'
                elif any('STANDALONE_2T' in rt for rt in rtypes):
                    lvl = 'LEVEL_3_HEURISTIC_2T_STITCH'
                    stat = 'HEURISTIC_UNVERIFIED'
                    notes = 'Mã 2T độc lập không nối.'
                else:
                    lvl = 'LEVEL_1_VERIFIED_PERMANENT'
                    stat = 'VERIFIED'
                    notes = 'Mã SID vĩnh viễn duy nhất từ QuantConnect LEAN.'

                segments.append({
                    'snapshot_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'canonical_sid': unique_canon_sids[0],
                    'segment_index': 1,
                    'total_segments': 1,
                    'effective_start_date': eff_start,
                    'effective_end_date': eff_end,
                    'evidence_level': lvl,
                    'verification_status': stat,
                    'is_included_in_mask': True,
                    'exclusion_reason': None,
                    'notes': notes
                })
            else:
                sorted_ov = sorted(overlaps, key=lambda x: x.min_date)
                
                # Check actual date conflict between distinct SIDs
                has_date_conflict = False
                for i in range(len(sorted_ov) - 1):
                    if sorted_ov[i].canonical_sid != sorted_ov[i+1].canonical_sid:
                        if sorted_ov[i].max_date >= sorted_ov[i+1].min_date:
                            has_date_conflict = True
                            break

                if has_date_conflict:
                    # Ambiguous overlap conflict -> Excluded from mask
                    for idx, r in enumerate(sorted_ov, 1):
                        eff_start = max(r.min_date, p_start).strftime('%Y-%m-%d')
                        eff_end = min(r.max_date, p_end).strftime('%Y-%m-%d')
                        segments.append({
                            'snapshot_year': y,
                            'period_start': p_start.strftime('%Y-%m-%d'),
                            'period_end': p_end.strftime('%Y-%m-%d'),
                            'source_ticker': t,
                            'canonical_sid': r.canonical_sid,
                            'segment_index': idx,
                            'total_segments': len(sorted_ov),
                            'effective_start_date': eff_start,
                            'effective_end_date': eff_end,
                            'evidence_level': 'LEVEL_4_AMBIGUOUS_MULTI_SID',
                            'verification_status': 'AMBIGUOUS',
                            'is_included_in_mask': False,
                            'exclusion_reason': 'XUNG ĐỘT NGÀY: 2 thực thể cùng giao dịch trên sàn tại cùng thời điểm',
                            'notes': 'Chính sách loại trừ: Loại khỏi mask để bảo vệ universe khỏi bị nhân đôi mã'
                        })
                else:
                    gap_days = (sorted_ov[1].min_date - sorted_ov[0].max_date).days
                    if gap_days <= 10:
                        # Sequential transition (Heuristic, not verified!)
                        lvl = 'LEVEL_2_HEURISTIC_SEQUENTIAL_TRANSITION'
                        stat = 'HEURISTIC_UNVERIFIED'
                        notes = f"Chuyển tiếp tuần tự không trùng ngày (gap={gap_days}d <= 10d). Giả định kỹ thuật theo dõi M&A/rename."
                        inc = True
                        ex_reason = None
                    else:
                        # Discontinuous gap > 10d -> Ambiguous -> Excluded from mask
                        lvl = 'LEVEL_4_AMBIGUOUS_MULTI_SID'
                        stat = 'AMBIGUOUS'
                        notes = f"Gián đoạn thời gian lớn (gap={gap_days}d > 10d). Thiếu bằng chứng continuity."
                        inc = False
                        ex_reason = f"Gián đoạn thời gian {gap_days} ngày (>10d); thiếu hồ sơ CUSIP xác minh"

                    for idx, r in enumerate(sorted_ov, 1):
                        eff_start = max(r.min_date, p_start).strftime('%Y-%m-%d')
                        eff_end = min(r.max_date, p_end).strftime('%Y-%m-%d')
                        segments.append({
                            'snapshot_year': y,
                            'period_start': p_start.strftime('%Y-%m-%d'),
                            'period_end': p_end.strftime('%Y-%m-%d'),
                            'source_ticker': t,
                            'canonical_sid': r.canonical_sid,
                            'segment_index': idx,
                            'total_segments': len(sorted_ov),
                            'effective_start_date': eff_start,
                            'effective_end_date': eff_end,
                            'evidence_level': lvl,
                            'verification_status': stat,
                            'is_included_in_mask': inc,
                            'exclusion_reason': ex_reason,
                            'notes': notes
                        })

    df_segments = pd.DataFrame(segments)
    out_segments_file = AUDIT_TABLES_DIR / "universe_constituent_segments_mapping.csv"
    df_segments.to_csv(out_segments_file, index=False)
    log(f"  -> Đã lưu bảng phân đoạn Segment Mapping: {out_segments_file.name} ({len(df_segments):,} dòng)")
    log(f"  -> Thống kê đưa vào Mask (is_included_in_mask):\n{df_segments['is_included_in_mask'].value_counts().to_string()}")
    log(f"  -> Thống kê Cấp độ bằng chứng:\n{df_segments['evidence_level'].value_counts().to_string()}")

    # --------------------------------------------------------------------------
    # 3. Vectorized Construction of Dual Membership Masks (Strict vs Resolved)
    # --------------------------------------------------------------------------
    log("\n[3/6] Xây dựng hệ thống 2 phiên bản Membership Masks (Strict vs Resolved)...")
    t0 = time.time()
    
    # Version A: Strict Membership (ONLY LEVEL_1_VERIFIED_PERMANENT)
    strict_membership_arr = np.zeros((n_dates, n_sids), dtype=bool)
    strict_segments = df_segments[df_segments['evidence_level'] == 'LEVEL_1_VERIFIED_PERMANENT']
    log(f"  -> Version A (Strict): {len(strict_segments):,} phân đoạn có bằng chứng vĩnh viễn mạnh nhất...")
    for seg in strict_segments.itertuples(index=False):
        sid = seg.canonical_sid
        col_idx = sid_to_col.get(sid)
        if col_idx is None:
            continue
        s_date = pd.Timestamp(seg.effective_start_date)
        e_date = pd.Timestamp(seg.effective_end_date)
        if e_date < pd.Timestamp("2000-07-01"):
            continue
        s_date = max(s_date, pd.Timestamp("2000-07-01"))
        date_mask = (unique_dates >= s_date) & (unique_dates <= e_date)
        strict_membership_arr[date_mask, col_idx] = True

    strict_mask_df = pd.DataFrame(strict_membership_arr, index=unique_dates, columns=unique_sids)
    strict_mask_df.to_parquet(MATRICES_DIR / "strict_membership_mask.parquet", compression='snappy')
    log(f"     -> [Version A] strict_membership_mask: {strict_membership_arr.sum():,} True cells")

    # Version B: Resolved Membership (Selected Universe: Verified + Heuristic Transitions & 2T Stitches)
    resolved_membership_arr = np.zeros((n_dates, n_sids), dtype=bool)
    active_segments = df_segments[df_segments['is_included_in_mask'] == True]
    log(f"  -> Version B (Resolved Heuristic): {len(active_segments):,} phân đoạn hợp lệ được chọn dùng...")
    for seg in active_segments.itertuples(index=False):
        sid = seg.canonical_sid
        col_idx = sid_to_col.get(sid)
        if col_idx is None:
            continue
        s_date = pd.Timestamp(seg.effective_start_date)
        e_date = pd.Timestamp(seg.effective_end_date)
        if e_date < pd.Timestamp("2000-07-01"):
            continue
        s_date = max(s_date, pd.Timestamp("2000-07-01"))
        date_mask = (unique_dates >= s_date) & (unique_dates <= e_date)
        resolved_membership_arr[date_mask, col_idx] = True

    resolved_mask_df = pd.DataFrame(resolved_membership_arr, index=unique_dates, columns=unique_sids)
    resolved_mask_df.to_parquet(MATRICES_DIR / "resolved_membership_mask.parquet", compression='snappy')
    # Save membership_mask.parquet for backward compatibility with downstream pipeline
    resolved_mask_df.to_parquet(MATRICES_DIR / "membership_mask.parquet", compression='snappy')
    membership_arr = resolved_membership_arr
    membership_mask = resolved_mask_df
    total_member_cells = membership_arr.sum()
    log(f"     -> [Version B] resolved_membership_mask: {total_member_cells:,} True cells ({time.time()-t0:.2f}s)")

    # --------------------------------------------------------------------------
    # 4. Load Pivot Matrices (Re-pivoted fresh from Tier 2 Warehouse)
    # --------------------------------------------------------------------------
    log("\n[4/6] Tái tạo toàn bộ các ma trận 2D từ kho Tier 2 Adjusted...")
    fields = [
        'open', 'high', 'low', 'close', 'volume',
        'adj_open', 'adj_high', 'adj_low', 'adj_close', 'adj_volume',
        'cumulative_split_factor', 'adj_dividend',
        'daily_return', 'total_return', 'is_consecutive_session',
        'is_bad_data_period', 'is_spinoff_discontinuity'
    ]

    matrices = {}
    for fld in fields:
        out_file = MATRICES_DIR / f"{fld}.parquet"
        t0 = time.time()
        df_col = pd.read_parquet(WAREHOUSE_PATH, columns=['date', 'canonical_sid', fld])
        mat = df_col.pivot(index='date', columns='canonical_sid', values=fld)
        mat = mat.reindex(index=unique_dates, columns=unique_sids)
        if fld in ['is_consecutive_session', 'is_bad_data_period', 'is_spinoff_discontinuity']:
            mat = mat.fillna(False).astype(bool)
        elif fld == 'adj_dividend':
            mat = mat.fillna(0.0).astype(np.float64)
        else:
            mat = mat.astype(np.float64)
        
        mat.to_parquet(out_file, compression='snappy')
        matrices[fld] = mat
        log(f"  -> Ma trận {fld}.parquet đã tái tạo ({time.time()-t0:.2f}s)")
        del df_col, mat

    # --------------------------------------------------------------------------
    # 5. Build Valid Data Mask, Valid Label Mask & Future Targets
    # --------------------------------------------------------------------------
    log("\n[5/6] Tái tạo valid_data_mask, valid_label_mask và target_next_return...")
    t0 = time.time()

    adj_close = matrices['adj_close']
    adj_volume = matrices['adj_volume']
    is_consec = matrices['is_consecutive_session']
    daily_ret = matrices['daily_return']
    total_ret = matrices['total_return']
    is_bad = matrices['is_bad_data_period'].values
    is_spinoff = matrices['is_spinoff_discontinuity'].values

    # --- Mask 2: valid_data_mask ---
    # a. Member at date T
    c_member = membership_arr
    # b. Valid positive close at T
    c_price = (adj_close.notna().values) & (adj_close.values > 0)
    # c. Positive volume at T
    c_vol = (adj_volume.notna().values) & (adj_volume.values > 0)
    # d. Consecutive session at T
    c_consec = is_consec.values
    # e. Lookback warmup history >= 20 bars
    has_bar = (adj_close.notna().values) & (adj_volume.values > 0)
    cum_bars = np.cumsum(has_bar, axis=0)
    c_history = cum_bars >= 20
    # f. Quality flag / Spinoff quarantine
    c_clean = (~is_bad) & (~is_spinoff)

    valid_data_arr = c_member & c_price & c_vol & c_consec & c_history & c_clean
    valid_data_mask = pd.DataFrame(valid_data_arr, index=unique_dates, columns=unique_sids)
    valid_data_mask.to_parquet(MATRICES_DIR / "valid_data_mask.parquet", compression='snappy')
    log(f"  -> [Mask 2] valid_data_mask: {valid_data_arr.sum():,} True cells ({time.time()-t0:.2f}s)")

    # --- Mask 3: valid_label_mask ---
    t0 = time.time()
    next_price_valid = np.zeros_like(valid_data_arr)
    next_price_valid[:-1, :] = (adj_close.values[1:, :] > 0) & np.isfinite(adj_close.values[1:, :])

    next_vol_valid = np.zeros_like(valid_data_arr)
    next_vol_valid[:-1, :] = (adj_volume.values[1:, :] > 0) & np.isfinite(adj_volume.values[1:, :])

    next_consec = np.zeros_like(valid_data_arr)
    next_consec[:-1, :] = is_consec.values[1:, :]

    next_return_valid = np.zeros_like(valid_data_arr)
    next_return_valid[:-1, :] = np.isfinite(daily_ret.values[1:, :])

    purge_dates = [unique_dates[-1], pd.Timestamp("2023-12-29")]
    purge_mask_1d = np.isin(unique_dates, purge_dates)
    not_purged = (~purge_mask_1d)[:, None]

    valid_label_arr = (
        valid_data_arr &
        next_price_valid &
        next_vol_valid &
        next_consec &
        next_return_valid &
        not_purged
    )
    valid_label_mask = pd.DataFrame(valid_label_arr, index=unique_dates, columns=unique_sids)
    valid_label_mask.to_parquet(MATRICES_DIR / "valid_label_mask.parquet", compression='snappy')
    log(f"  -> [Mask 3] valid_label_mask: {valid_label_arr.sum():,} True cells ({time.time()-t0:.2f}s)")

    # --- Target Matrices ---
    t0 = time.time()
    next_daily_ret = daily_ret.shift(-1).values.copy()
    next_daily_ret[~valid_label_arr] = np.nan
    target_next_return = pd.DataFrame(next_daily_ret, index=unique_dates, columns=unique_sids)
    target_next_return.to_parquet(MATRICES_DIR / "target_next_return.parquet", compression='snappy')

    next_tot_ret = total_ret.shift(-1).values.copy()
    next_tot_ret[~valid_label_arr] = np.nan
    target_next_total_return = pd.DataFrame(next_tot_ret, index=unique_dates, columns=unique_sids)
    target_next_total_return.to_parquet(MATRICES_DIR / "target_next_total_return.parquet", compression='snappy')
    log(f"  -> Target matrices saved ({time.time()-t0:.2f}s)")

    # --------------------------------------------------------------------------
    # 6. Audit Summary by Reconstitution Period
    # --------------------------------------------------------------------------
    log("\n[6/6] Tính toán bảng thống kê độ phủ ma trận & mask theo kỳ tái cơ cấu...")
    summary_rows = []

    warmup_dates = unique_dates[unique_dates < pd.Timestamp("2000-07-01")]
    summary_rows.append({
        'period': '1998-01-02 đến 2000-06-30 (Feature Warm-up — 630 phiên)',
        'period_start': unique_dates[0].strftime('%Y-%m-%d'),
        'period_end': warmup_dates[-1].strftime('%Y-%m-%d'),
        'trading_days': len(warmup_dates),
        'official_tickers': 0,
        'theoretical_stock_days': 0,
        'actual_valid_data_stock_days': 0,
        'avg_resolved_membership_count': 0.0,
        'avg_valid_data_count': 0.0,
        'avg_valid_label_count': 0.0,
        'coverage_vs_resolved_membership_pct': 0.0,
        'coverage_vs_official_snapshot_pct': 0.0,
        'note': 'Lịch sử khởi tạo feature; không thuộc universe PIT'
    })

    for y in sorted([int(k) for k in pit.keys()]):
        p_start = pd.Timestamp(f"{y}-07-01")
        p_end = pd.Timestamp(f"{y+1}-06-30") if y < 2026 else unique_dates[-1]
        p_dates = unique_dates[(unique_dates >= p_start) & (unique_dates <= p_end)]
        if len(p_dates) == 0:
            continue

        n_days = len(p_dates)
        n_official = len(pit[str(y)])
        theo_stock_days = n_days * n_official

        m_sub = membership_mask.loc[p_dates].values
        d_sub = valid_data_mask.loc[p_dates].values
        l_sub = valid_label_mask.loc[p_dates].values

        mean_m = float(m_sub.sum(axis=1).mean())
        mean_d = float(d_sub.sum(axis=1).mean())
        mean_l = float(l_sub.sum(axis=1).mean())
        actual_valid_days = int(d_sub.sum())

        ratio_d_m = round(mean_d / mean_m * 100.0, 2) if mean_m > 0 else 0.0
        ratio_d_theo = round(actual_valid_days / theo_stock_days * 100.0, 2) if theo_stock_days > 0 else 0.0

        summary_rows.append({
            'period': f"{y} Reconstitution",
            'period_start': p_dates[0].strftime('%Y-%m-%d'),
            'period_end': p_dates[-1].strftime('%Y-%m-%d'),
            'trading_days': n_days,
            'official_tickers': n_official,
            'theoretical_stock_days': theo_stock_days,
            'actual_valid_data_stock_days': actual_valid_days,
            'avg_resolved_membership_count': round(mean_m, 1),
            'avg_valid_data_count': round(mean_d, 1),
            'avg_valid_label_count': round(mean_l, 1),
            'coverage_vs_resolved_membership_pct': ratio_d_m,
            'coverage_vs_official_snapshot_pct': ratio_d_theo,
            'note': 'Chính thức có mặt trong rổ Russell 1000'
        })

    df_summary = pd.DataFrame(summary_rows)
    audit_file = AUDIT_TABLES_DIR / "matrix_and_mask_coverage_by_period.csv"
    df_summary.to_csv(audit_file, index=False)
    log(f"\nBảng tổng hợp độ phủ ma trận theo kỳ (Mẫu):\n{df_summary.iloc[[0,1,2,3,-3,-2,-1]].to_string(index=False)}")
    log(f"\n-> Đã xuất: {audit_file.name}")

    log("\n" + "=" * 80)
    log(f"BƯỚC 4 HOÀN THÀNH XUẤT SẮC TRONG {time.time()-t_start:.2f} GIÂY!")
    log("=" * 80)

if __name__ == '__main__':
    main()
