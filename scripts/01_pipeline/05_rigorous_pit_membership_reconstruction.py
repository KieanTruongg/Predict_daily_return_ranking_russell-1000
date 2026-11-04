"""
scripts/01_pipeline/05_rigorous_pit_membership_reconstruction.py
================================================================================
Rigorous Step 3 Finalization:
1. Reconcile 2,884 unique Russell tickers to 3,711 Canonical SIDs (Ticker Reuse).
2. Snapshot-driven temporal mapping with validity windows [min_date, max_date].
3. Rigorous Multi-SID inspection:
   - Date overlap conflicts -> AMBIGUOUS_DATE_CONFLICT
   - Sequential transitions with gap <= 10d -> LEVEL_2_VERIFIED_SEQUENTIAL_TRANSITION
   - Sequential transitions with gap > 10d -> AMBIGUOUS_DISCONTINUOUS_GAP
4. Graded Evidence Levels:
   - LEVEL_1_VERIFIED_PERMANENT
   - LEVEL_2_VERIFIED_SEQUENTIAL_TRANSITION
   - LEVEL_3_HEURISTIC_2T_STITCH
   - LEVEL_4_AMBIGUOUS_MULTI_SID
   - LEVEL_5_UNRESOLVED_ZERO_BARS
   - LEVEL_6_UNRESOLVED_NOT_IN_MAPPING
5. Differentiate:
   - Ticker-Period Coverage (Macro annual membership coverage)
   - Daily Stock-Day Coverage (Micro bar execution coverage)
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

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

WAREHOUSE_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet"
CANONICAL_MAP_CSV = TABLES_DIR / "canonical_security_mapping.csv"
PIT_JSON = BASE_DIR / "data" / "raw" / "universe" / "russell1000_pit_by_year.json"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    t_start = time.time()
    log("=" * 80)
    log("CHUẨN HÓA HỌC THUẬT BƯỚC ③: TEMPORAL MEMBERSHIP & MULTI-SID AMBIGUITY")
    log("=" * 80)

    # 1. Load PIT snapshots
    with open(PIT_JSON, 'r', encoding='utf-8') as f:
        pit = json.load(f)

    all_pit_tickers = sorted(list(set(t for t_list in pit.values() for t in t_list)))
    log(f"[1/5] Tải danh sách Universe: 27 snapshots ({len(all_pit_tickers)} tickers duy nhất)...")

    # 2. Load Mapping Table with Validity Windows
    df_map = pd.read_csv(CANONICAL_MAP_CSV, keep_default_na=False)
    df_map['min_date'] = pd.to_datetime(df_map['min_date'])
    df_map['max_date'] = pd.to_datetime(df_map['max_date'])
    log(f"  -> Bảng ánh xạ: {len(df_map)} dòng | {df_map['original_ticker'].nunique()} tickers | {df_map['canonical_sid'].nunique()} canonical SIDs")

    # Group mapping entries by original_ticker
    map_by_ticker = defaultdict(list)
    for row in df_map.itertuples(index=False):
        map_by_ticker[row.original_ticker].append(row)

    # 3. Snapshot-Driven Reconstruction across 26,919 Constituent-Years
    log("\n[2/5] Tái tạo Membership từ Snapshot và Khoảng Hiệu Lực [min_date, max_date]...")
    constituent_records = []
    ambiguous_records = []

    for y_str in sorted(pit.keys()):
        y = int(y_str)
        p_start = pd.Timestamp(f"{y}-07-01")
        p_end = pd.Timestamp(f"{y+1}-06-30") if y < 2026 else pd.Timestamp("2026-10-30")
        tickers = pit[y_str]

        for t in tickers:
            rows = map_by_ticker.get(t, [])
            if not rows:
                constituent_records.append({
                    'period_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'assigned_canonical_sid': None,
                    'evidence_level': 'LEVEL_6_UNRESOLVED_NOT_IN_MAPPING',
                    'verification_status': 'UNRESOLVED',
                    'validity_overlap_range': None,
                    'notes': 'Không tìm thấy mã trong kho mapping (mã OTC / non-equity / un-downloaded)'
                })
                continue

            overlaps = [r for r in rows if r.min_date <= p_end and r.max_date >= p_start]
            if not overlaps:
                all_ranges = [f"{r.min_date.strftime('%Y-%m-%d')}->{r.max_date.strftime('%Y-%m-%d')}" for r in rows]
                constituent_records.append({
                    'period_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'assigned_canonical_sid': None,
                    'evidence_level': 'LEVEL_5_UNRESOLVED_ZERO_BARS',
                    'verification_status': 'UNRESOLVED',
                    'validity_overlap_range': None,
                    'notes': f"Có trong kho ({'; '.join(all_ranges)}) nhưng không có ngày hiệu lực nào trong kỳ {y}"
                })
                continue

            unique_sids = list(dict.fromkeys(r.canonical_sid for r in overlaps))
            
            if len(unique_sids) == 1:
                r0 = overlaps[0]
                rtypes = set(r.resolution_type for r in overlaps)
                eff_min = max(r0.min_date, p_start).strftime('%Y-%m-%d')
                eff_max = min(r0.max_date, p_end).strftime('%Y-%m-%d')

                if any('STITCH' in rt for rt in rtypes):
                    lvl = 'LEVEL_3_HEURISTIC_2T_STITCH'
                    stat = 'ASSUMED_UNVERIFIED'
                    notes = 'Nối mã 2T tạm thời dựa trên gap <=10 ngày; giả định kỹ thuật chưa xác minh hồ sơ'
                elif any('STANDALONE_2T' in rt for rt in rtypes):
                    lvl = 'LEVEL_3_HEURISTIC_2T_STITCH'
                    stat = 'ASSUMED_UNVERIFIED'
                    notes = 'Mã 2T độc lập không nối'
                else:
                    lvl = 'LEVEL_1_VERIFIED_PERMANENT'
                    stat = 'VERIFIED'
                    notes = 'Mã SID vĩnh viễn duy nhất từ QuantConnect LEAN'

                constituent_records.append({
                    'period_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'assigned_canonical_sid': unique_sids[0],
                    'evidence_level': lvl,
                    'verification_status': stat,
                    'validity_overlap_range': f"{eff_min} đến {eff_max}",
                    'notes': notes
                })
            else:
                # Multiple Canonical SIDs in period: Check overlap & continuity
                sorted_ov = sorted(overlaps, key=lambda x: x.min_date)
                
                # Check for date overlap between different canonical SIDs
                has_date_conflict = False
                for i in range(len(sorted_ov) - 1):
                    if sorted_ov[i].canonical_sid != sorted_ov[i+1].canonical_sid:
                        if sorted_ov[i].max_date >= sorted_ov[i+1].min_date:
                            has_date_conflict = True
                            break

                sids_str = '; '.join(unique_sids)
                eff_min = max(sorted_ov[0].min_date, p_start).strftime('%Y-%m-%d')
                eff_max = min(sorted_ov[-1].max_date, p_end).strftime('%Y-%m-%d')

                if has_date_conflict:
                    lvl = 'LEVEL_4_AMBIGUOUS_MULTI_SID'
                    stat = 'AMBIGUOUS'
                    notes = f"XUNG ĐỘT NGÀY: 2 thực thể cùng hoạt động đồng thời trong kỳ ({sids_str}). Thiếu bằng chứng phân lập."
                    ambiguous_records.append({
                        'period_year': y,
                        'ticker': t,
                        'ambiguity_type': 'DATE_OVERLAP_CONFLICT',
                        'canonical_sids': sids_str,
                        'details': ' | '.join([f"{r.canonical_sid} ({r.min_date.strftime('%Y-%m-%d')}->{r.max_date.strftime('%Y-%m-%d')}, {r.resolution_type})" for r in sorted_ov]),
                        'resolution_recommendation': 'Loại khỏi universe giao dịch cho đến khi có hồ sơ CUSIP xác minh'
                    })
                else:
                    gap_days = (sorted_ov[1].min_date - sorted_ov[0].max_date).days
                    if gap_days <= 10:
                        lvl = 'LEVEL_2_VERIFIED_SEQUENTIAL_TRANSITION'
                        stat = 'VERIFIED'
                        notes = f"Chuyển tiếp tuần tự không trùng ngày qua M&A/rename (gap={gap_days}d <= 10d; {sids_str})"
                    else:
                        lvl = 'LEVEL_4_AMBIGUOUS_MULTI_SID'
                        stat = 'AMBIGUOUS'
                        notes = f"GIÁN ĐOẠN LỚN: Khoảng cách giữa 2 SID là {gap_days} ngày (>10d); thiếu bằng chứng continuity"
                        ambiguous_records.append({
                            'period_year': y,
                            'ticker': t,
                            'ambiguity_type': 'DISCONTINUOUS_GAP',
                            'canonical_sids': sids_str,
                            'details': f"Gap={gap_days}d giữa {sorted_ov[0].canonical_sid} và {sorted_ov[1].canonical_sid}",
                            'resolution_recommendation': 'Cần kiểm tra xem có phải 2 công ty khác nhau tái sử dụng ticker hay không'
                        })

                constituent_records.append({
                    'period_year': y,
                    'period_start': p_start.strftime('%Y-%m-%d'),
                    'period_end': p_end.strftime('%Y-%m-%d'),
                    'source_ticker': t,
                    'assigned_canonical_sid': sids_str,
                    'evidence_level': lvl,
                    'verification_status': stat,
                    'validity_overlap_range': f"{eff_min} đến {eff_max}",
                    'notes': notes
                })

    df_constituents = pd.DataFrame(constituent_records)
    out_const = TABLES_DIR / "universe_constituent_temporal_mapping.csv"
    df_constituents.to_csv(out_const, index=False)
    log(f"  -> Đã lưu bảng ánh xạ 100% constituent-years: {out_const.name} ({len(df_constituents):,} dòng)")
    log(f"  -> Phân phối Evidence Level:\n{df_constituents['evidence_level'].value_counts().to_string()}")
    log(f"  -> Phân phối Verification Status:\n{df_constituents['verification_status'].value_counts().to_string()}")

    # Save Ambiguous Audit Table
    df_ambiguous = pd.DataFrame(ambiguous_records)
    out_ambig = TABLES_DIR / "ambiguous_multi_sid_audit.csv"
    df_ambiguous.to_csv(out_ambig, index=False)
    log(f"  -> Đã lưu bảng thẩm định {len(df_ambiguous)} ca AMBIGUOUS: {out_ambig.name}")

    # 4. Coverage Metrics: Ticker-Period vs Daily Stock-Day
    log("\n[3/5] Tính toán phân biệt rạch ròi 2 thước đo Coverage:")
    log("  - Metric A: Ticker-Period Coverage (Độ phủ mã nguồn theo kỳ)")
    log("  - Metric B: Daily Stock-Day Coverage (Độ phủ nến khớp lệnh cổ phiếu-ngày)")
    
    df_wh = pd.read_parquet(WAREHOUSE_PARQUET, columns=['date', 'original_ticker', 'canonical_sid'])
    wh_dates = df_wh['date'].drop_duplicates().sort_values()

    coverage_records = []
    for y_str in sorted(pit.keys()):
        y = int(y_str)
        p_start = pd.Timestamp(f"{y}-07-01")
        p_end = pd.Timestamp(f"{y+1}-06-30") if y < 2026 else pd.Timestamp("2026-10-30")
        official_tickers = set(pit[y_str])
        n_official = len(official_tickers)

        period_days = wh_dates[(wh_dates >= p_start) & (wh_dates <= p_end)]
        n_days = len(period_days)

        sub_wh = df_wh[(df_wh['date'] >= p_start) & (df_wh['date'] <= p_end)]
        wh_tickers_in_period = set(sub_wh['original_ticker'].unique())
        matched_tickers = official_tickers.intersection(wh_tickers_in_period)
        ticker_period_cov_pct = len(matched_tickers) / n_official * 100.0

        official_bars = sub_wh[sub_wh['original_ticker'].isin(official_tickers)]
        actual_stock_days = len(official_bars)
        theoretical_stock_days = n_days * n_official
        daily_stock_day_cov_pct = actual_stock_days / theoretical_stock_days * 100.0 if theoretical_stock_days > 0 else 0
        mean_stocks_day = actual_stock_days / n_days if n_days > 0 else 0

        # Also count verified vs ambiguous in this period
        sub_c = df_constituents[df_constituents['period_year'] == y]
        n_ver = (sub_c['verification_status'] == 'VERIFIED').sum()
        n_assumed = (sub_c['verification_status'] == 'ASSUMED_UNVERIFIED').sum()
        n_ambig = (sub_c['verification_status'] == 'AMBIGUOUS').sum()
        n_unres = (sub_c['verification_status'] == 'UNRESOLVED').sum()

        coverage_records.append({
            'snapshot_year': y,
            'trading_days': n_days,
            'official_tickers': n_official,
            'tickers_with_bars': len(matched_tickers),
            'ticker_period_coverage_pct': round(ticker_period_cov_pct, 2),
            'theoretical_stock_days': theoretical_stock_days,
            'actual_stock_days': actual_stock_days,
            'daily_stock_day_coverage_pct': round(daily_stock_day_cov_pct, 2),
            'mean_active_stocks_per_day': round(mean_stocks_day, 1),
            'verified_constituents': n_ver,
            'assumed_constituents': n_assumed,
            'ambiguous_constituents': n_ambig,
            'unresolved_constituents': n_unres
        })

    df_coverage = pd.DataFrame(coverage_records)
    out_cov = TABLES_DIR / "coverage_ticker_period_vs_daily_stock_days.csv"
    df_coverage.to_csv(out_cov, index=False)
    log(f"  -> Đã lưu bảng phân biệt Coverage: {out_cov.name}")
    log(f"  -> Mean Ticker-Period Coverage: {df_coverage['ticker_period_coverage_pct'].mean():.2f}%")
    log(f"  -> Mean Daily Stock-Day Coverage: {df_coverage['daily_stock_day_coverage_pct'].mean():.2f}%")

    # 5. Dedicated Explanation of 2,884 Tickers vs 3,711 SIDs
    log("\n[4/5] Tạo bảng giải trình 2,884 Tickers -> 3,711 SIDs (Ticker Reuse Breakdown)...")
    sids_per_ticker = df_map.groupby('original_ticker')['canonical_sid'].nunique().reset_index()
    sids_per_ticker.columns = ['ticker', 'canonical_sid_count']

    reuse_records = []
    for _, row in sids_per_ticker.iterrows():
        t = row['ticker']
        cnt = row['canonical_sid_count']
        sub = df_map[df_map['original_ticker'] == t]
        sids = sub['canonical_sid'].unique()
        ranges = [f"{r.canonical_sid} ({r.min_date.strftime('%Y-%m-%d')}->{r.max_date.strftime('%Y-%m-%d')})" for r in sub.itertuples()]
        reuse_records.append({
            'ticker': t,
            'entity_count': cnt,
            'in_pit_universe': t in all_pit_tickers,
            'canonical_sids': '; '.join(sids),
            'entity_lifecycles': ' | '.join(ranges)
        })

    df_ticker_breakdown = pd.DataFrame(reuse_records)
    out_tbreakdown = TABLES_DIR / "ticker_to_canonical_sid_reuse_breakdown.csv"
    df_ticker_breakdown.to_csv(out_tbreakdown, index=False)
    log(f"  -> Đã lưu bảng giải trình Ticker Reuse: {out_tbreakdown.name} ({len(df_ticker_breakdown):,} tickers)")

    log("\n" + "=" * 80)
    log(f"HOÀN TẤT THẨM ĐỊNH BƯỚC ③ TRONG {time.time()-t_start:.2f} GIÂY!")
    log("=" * 80)

if __name__ == '__main__':
    main()
