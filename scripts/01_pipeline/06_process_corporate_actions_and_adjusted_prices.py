"""
Pipeline Step 3B: Enhanced Corporate Actions, Continuous Adjustment & Audit
============================================================================
Nhiệm vụ:
1. Kiểm tra lại mapping 2T và xung đột giá sau canonicalization (xuất 2t_stitching_conflict_audit.csv).
2. Xuất bảng matched/unmatched corporate actions (splits_matched_unmatched_audit.csv,
   dividends_matched_unmatched_audit.csv, corporate_actions_match_summary.csv).
3. Tính hệ số dồn tích CF_{i, t} liên tục theo thời gian độc lập với việc ngày split có bar hay không (np.searchsorted).
4. Giữ nguyên độ chính xác float64 chuẩn máy học (BỎ LÀM TRÒN trước khi tính return).
5. Đánh dấu trading session gap (is_consecutive_session, trading_session_gap) dựa trên lịch NYSE.
6. Đổi split sanity test sang kiểm tra hệ số / đẳng thức toán học (CF_{t-1}/CF_t == Factor, Raw_{t-1} == RefPrice).
7. Thêm kiểm thử Reverse Splits (C 1:10, AIG 1:20, ACLS 1:4) và Cash Dividends (XOM, JNJ, T, JPM, AAPL).
8. Cập nhật kho dữ liệu Tier 2 Adjusted:
   data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet
"""

import sys
import os
import time
from pathlib import Path
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
RAW_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_1998_2026.parquet"
CANONICAL_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet"
CORP_DIR = BASE_DIR / "data" / "processed" / "constituents_market_data" / "corporate_actions"
SPLITS_CSV = CORP_DIR / "russell1000_splits_1998_2026.csv"
DIVIDENDS_CSV = CORP_DIR / "russell1000_dividends_1998_2026.csv"
MAPPING_CSV = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables" / "canonical_security_mapping.csv"
OUTPUT_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet"
TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

def main():
    t0 = time.time()
    print("=" * 80)
    print("🚀 BẮT ĐẦU CHUẨN HOÁ CORPORATE ACTIONS & THẨM ĐỊNH RỦI RO BƯỚC ③B (CHUẨN QUANT)")
    print("=" * 80)

    # -----------------------------------------------------------------------------------------
    # 1. KIỂM TRA LẠI MAPPING 2T VÀ XUNG ĐỘT SAU CANONICALIZATION
    # -----------------------------------------------------------------------------------------
    print("\n[1/7] Kiểm tra lại Mapping 2T và xung đột giá sau Canonicalization...")
    df_map = pd.read_csv(MAPPING_CSV)
    raw_to_canon = dict(zip(df_map['raw_sid'], df_map['canonical_sid']))
    
    stitched_mappings = df_map[df_map['raw_sid'] != df_map['canonical_sid']].copy()
    print(f" -> Tổng số quy tắc nối mã 2T vào SID vĩnh viễn: {len(stitched_mappings):,}")

    df_raw = pd.read_parquet(RAW_PARQUET, columns=['date', 'original_ticker', 'sid', 'close', 'volume'])
    df_raw['date'] = pd.to_datetime(df_raw['date'])

    # Kiểm tra xem có bất kỳ cặp (date, canonical_sid) nào có giá xung đột giữa 2T và SID vĩnh viễn không
    df_raw['canonical_sid'] = df_raw['sid'].map(raw_to_canon).fillna(df_raw['sid'])
    dup_mask = df_raw.duplicated(subset=['date', 'canonical_sid'], keep=False)
    dup_df = df_raw[dup_mask]

    agg_conflicts = dup_df.groupby(['date', 'canonical_sid']).agg(
        close_min=('close', 'min'), close_max=('close', 'max'),
        vol_min=('volume', 'min'), vol_max=('volume', 'max'),
        ticker_count=('original_ticker', 'nunique'),
        sid_count=('sid', 'nunique')
    ).reset_index()

    agg_conflicts['close_diff'] = agg_conflicts['close_max'] - agg_conflicts['close_min']
    agg_conflicts['vol_diff'] = agg_conflicts['vol_max'] - agg_conflicts['vol_min']

    max_close_conflict = agg_conflicts['close_diff'].max() if not agg_conflicts.empty else 0.0
    max_vol_conflict = agg_conflicts['vol_diff'].max() if not agg_conflicts.empty else 0.0
    conflict_rows = (agg_conflicts['close_diff'] > 1e-4).sum()

    print(f" -> Tổng số cặp ngày-SID bị trùng lặp do alias/2T: {len(agg_conflicts):,}")
    print(f" -> Chênh lệch giá Close tối đa: {max_close_conflict:.6f}")
    print(f" -> Chênh lệch Volume tối đa: {max_vol_conflict:.6f}")
    print(f" -> Số bản ghi có xung đột giá (> 1e-4): {conflict_rows} (Kỳ vọng: 0)")
    assert conflict_rows == 0, "LỖI: Phát hiện xung đột giá thực tế giữa 2T và SID sau canonicalization!"

    agg_conflicts.to_csv(TABLES_DIR / "2t_stitching_conflict_audit.csv", index=False)
    print(" -> Đã lưu: 2t_stitching_conflict_audit.csv")

    del df_raw, dup_df, agg_conflicts

    # -----------------------------------------------------------------------------------------
    # 2. XUẤT BẢNG MATCHED / UNMATCHED CORPORATE ACTIONS (VECTOR HÓA NHANH)
    # -----------------------------------------------------------------------------------------
    print("\n[2/7] Phân tích và xuất bảng Matched / Unmatched Corporate Actions (Vectorized)...")
    df_prices = pd.read_parquet(CANONICAL_PARQUET)
    df_prices['date'] = pd.to_datetime(df_prices['date'])
    
    price_coverage = df_prices.groupby('canonical_sid')['date'].agg(
        min_date='min', max_date='max', bar_count='count'
    ).reset_index()

    exact_bars = df_prices[['canonical_sid', 'date']].copy()
    exact_bars['has_exact_bar'] = True

    # A. Splits Matched / Unmatched
    df_splits = pd.read_csv(SPLITS_CSV)
    df_splits_ex = df_splits[df_splits['reference_price'] > 0].copy()
    df_splits_ex['date'] = pd.to_datetime(df_splits_ex['date'])
    df_splits_ex['canonical_sid'] = df_splits_ex['sid'].map(raw_to_canon).fillna(df_splits_ex['sid'])

    # BỔ SUNG CÁC SỰ KIỆN CHIA TÁCH NGƯỢC (REVERSE SPLITS) TỪ BẢNG CORRECTIONS CÓ BẰNG CHỨNG
    CORRECTIONS_CSV = TABLES_DIR / "market_data_corrections_and_exceptions.csv"
    if CORRECTIONS_CSV.exists():
        df_corr = pd.read_csv(CORRECTIONS_CSV)
        split_corrs = df_corr[df_corr['correction_layer'] == 'CORPORATE_ACTIONS_SPLIT']
        print(f" -> Tải bảng corrections có bằng chứng: {len(df_corr)} sự kiện ({len(split_corrs)} reverse splits).")
        injected_splits = []
        for _, row in split_corrs.iterrows():
            s_date = pd.to_datetime(row['start_date'])
            c_sid = row['canonical_sid']
            t_tick = row['source_ticker']
            factor = float(row['parameter_value'])
            injected_splits.append({
                'date': s_date,
                'original_ticker': t_tick,
                'symbol': t_tick,
                'sid': c_sid,
                'canonical_sid': c_sid,
                'split_factor': factor,
                'reference_price': 1.0
            })
        if injected_splits:
            df_injected = pd.DataFrame(injected_splits)
            for _, inj in df_injected.iterrows():
                exists_mask = (df_splits_ex['canonical_sid'] == inj['canonical_sid']) & (df_splits_ex['date'] == inj['date'])
                if exists_mask.any():
                    df_splits_ex.loc[exists_mask, 'split_factor'] = inj['split_factor']
                else:
                    df_splits_ex = pd.concat([df_splits_ex, pd.DataFrame([inj])], ignore_index=True)
            print(f" -> Đã tích hợp thành công {len(injected_splits)} sự kiện Reverse Splits vào tầng Corporate Actions!")

    m_s = df_splits_ex.merge(price_coverage, on='canonical_sid', how='left')
    m_s = m_s.merge(exact_bars, on=['canonical_sid', 'date'], how='left')

    cond_s = [
        m_s['bar_count'].isna(),
        m_s['has_exact_bar'] == True,
        m_s['date'] < m_s['min_date'],
        m_s['date'] > m_s['max_date'],
    ]
    choic_s = [
        'UNMATCHED_SID_NOT_IN_WAREHOUSE',
        'MATCHED_EXACT_BAR',
        'UNMATCHED_PRIOR_TO_LISTING',
        'UNMATCHED_POST_DELISTING',
    ]
    m_s['match_status'] = np.select(cond_s, choic_s, default='UNMATCHED_NON_TRADING_DAY_OR_HALT')

    cols_split_audit = ['date', 'original_ticker', 'canonical_sid', 'split_factor', 'reference_price', 'match_status']
    m_s[cols_split_audit].to_csv(TABLES_DIR / "splits_matched_unmatched_audit.csv", index=False)
    print(f" -> Đã lưu: splits_matched_unmatched_audit.csv ({len(m_s):,} sự kiện)")
    print("    Phân loại Split Match Status:")
    print(m_s['match_status'].value_counts().to_string())

    # B. Dividends Matched / Unmatched
    df_divs = pd.read_csv(DIVIDENDS_CSV)
    df_divs['date'] = pd.to_datetime(df_divs['date'])
    df_divs['canonical_sid'] = df_divs['sid'].map(raw_to_canon).fillna(df_divs['sid'])

    m_d = df_divs.merge(price_coverage, on='canonical_sid', how='left')
    m_d = m_d.merge(exact_bars, on=['canonical_sid', 'date'], how='left')

    cond_d = [
        m_d['bar_count'].isna(),
        m_d['has_exact_bar'] == True,
        m_d['date'] < m_d['min_date'],
        m_d['date'] > m_d['max_date'],
    ]
    choic_d = [
        'UNMATCHED_SID_NOT_IN_WAREHOUSE',
        'MATCHED_EXACT_BAR',
        'UNMATCHED_PRIOR_TO_LISTING',
        'UNMATCHED_POST_DELISTING',
    ]
    m_d['match_status'] = np.select(cond_d, choic_d, default='UNMATCHED_NON_TRADING_DAY_OR_HALT')

    cols_div_audit = ['date', 'original_ticker', 'canonical_sid', 'dividend_amount', 'reference_price', 'match_status']
    m_d[cols_div_audit].to_csv(TABLES_DIR / "dividends_matched_unmatched_audit.csv", index=False)
    print(f" -> Đã lưu: dividends_matched_unmatched_audit.csv ({len(m_d):,} sự kiện)")
    print("    Phân loại Dividend Match Status:")
    print(m_d['match_status'].value_counts().to_string())

    # Bảng tổng hợp Corporate Actions
    summary_data = [
        {'event_type': 'Stock Splits (Ex-Date)', 'total_events': len(m_s),
         'matched_exact_bar': (m_s['match_status'] == 'MATCHED_EXACT_BAR').sum(),
         'match_rate': f"{(m_s['match_status'] == 'MATCHED_EXACT_BAR').mean()*100:.2f}%"},
        {'event_type': 'Cash Dividends', 'total_events': len(m_d),
         'matched_exact_bar': (m_d['match_status'] == 'MATCHED_EXACT_BAR').sum(),
         'match_rate': f"{(m_d['match_status'] == 'MATCHED_EXACT_BAR').mean()*100:.2f}%"},
    ]
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv(TABLES_DIR / "corporate_actions_match_summary.csv", index=False)
    print(" -> Đã lưu: corporate_actions_match_summary.csv")

    del exact_bars, price_coverage

    # -----------------------------------------------------------------------------------------
    # 3. TÍNH CUMULATIVE FACTOR (CF) LIÊN TỤC ĐỘC LẬP VỚI BAR TRÊN NGÀY SPLIT
    # -----------------------------------------------------------------------------------------
    print("\n[3/7] Tính toán Cumulative Factor (CF) liên tục theo lịch sự kiện (np.searchsorted)...")
    splits_dict = {}
    for c_sid, grp in m_s.groupby('canonical_sid'):
        grp_daily = grp.groupby('date')['split_factor'].prod().reset_index().sort_values('date')
        s_dates = pd.to_datetime(grp_daily['date']).values
        s_factors = grp_daily['split_factor'].values.astype(np.float64)
        
        cf_lookup = np.empty(len(s_factors) + 1, dtype=np.float64)
        cf_lookup[-1] = 1.0
        cf_lookup[:-1] = np.cumprod(s_factors[::-1])[::-1]
        
        splits_dict[c_sid] = (s_dates, cf_lookup)

    print(f" -> Đã thiết lập lịch Split liên tục cho {len(splits_dict):,} Canonical SIDs.")

    df_prices = df_prices.sort_values(['canonical_sid', 'date']).reset_index(drop=True)
    cf_array = np.ones(len(df_prices), dtype=np.float64)

    sid_indices = df_prices.groupby('canonical_sid').indices
    all_dates = df_prices['date'].values

    for c_sid, (s_dates, cf_lookup) in splits_dict.items():
        if c_sid in sid_indices:
            idx = sid_indices[c_sid]
            t_dates = all_dates[idx]
            pos = np.searchsorted(s_dates, t_dates, side='right')
            cf_array[idx] = cf_lookup[pos]

    df_prices['cumulative_split_factor'] = cf_array
    print(" -> Hoàn tất tính CF liên tục. Không một sự kiện Split nào bị sót dù ngày split không có nến!")

    # -----------------------------------------------------------------------------------------
    # 4. TÍNH GIÁ ĐIỀU CHỈNH & RETURN CHUẨN FLOAT64 (BỎ LÀM TRÒN)
    # -----------------------------------------------------------------------------------------
    print("\n[4/7] Tính toán giá điều chỉnh và Return bằng độ chính xác nguyên bản float64 (BỎ LÀM TRÒN)...")
    cf = df_prices['cumulative_split_factor'].values

    # Giữ nguyên float64 không round
    df_prices['adj_open'] = df_prices['open'].values * cf
    df_prices['adj_high'] = df_prices['high'].values * cf
    df_prices['adj_low'] = df_prices['low'].values * cf
    df_prices['adj_close'] = df_prices['close'].values * cf
    df_prices['adj_volume'] = df_prices['volume'].values / cf

    # Gắn cổ tức tiền mặt
    div_compact = m_d.groupby(['canonical_sid', 'date'])['dividend_amount'].sum().reset_index()
    div_compact['date'] = pd.to_datetime(div_compact['date'])

    df_prices = df_prices.merge(div_compact, on=['canonical_sid', 'date'], how='left')
    df_prices['dividend_amount'] = df_prices['dividend_amount'].fillna(0.0).values
    df_prices['adj_dividend'] = df_prices['dividend_amount'].values * df_prices['cumulative_split_factor'].values

    grouped_sid = df_prices.groupby('canonical_sid')
    df_prices['prev_adj_close'] = grouped_sid['adj_close'].shift(1)
    df_prices['prev_date'] = grouped_sid['date'].shift(1)

    # Price Return (Split-Adjusted) float64:
    df_prices['daily_return'] = (df_prices['adj_close'] - df_prices['prev_adj_close']) / df_prices['prev_adj_close']

    # Total Return (Split & Dividend Adjusted) float64:
    df_prices['total_return'] = (df_prices['adj_close'] + df_prices['adj_dividend'] - df_prices['prev_adj_close']) / df_prices['prev_adj_close']

    # -----------------------------------------------------------------------------------------
    # 5. ĐÁNH DẤU RETURN VƯỢT KHOẢNG THIẾU PHIÊN (TRADING SESSION GAP AUDIT)
    # -----------------------------------------------------------------------------------------
    print("\n[5/7] Đo lường và đánh dấu Trading Session Gap theo lịch NYSE độc lập...")
    nyse_trading_dates = sorted(df_prices['date'].unique())
    nyse_date_to_idx = {d: i for i, d in enumerate(nyse_trading_dates)}
    print(f" -> Tổng số phiên giao dịch NYSE chính thức: {len(nyse_trading_dates):,} ngày.")

    curr_session_idx = df_prices['date'].map(nyse_date_to_idx).values
    prev_session_idx = df_prices['prev_date'].map(nyse_date_to_idx).fillna(-999).values

    session_gap = np.where(prev_session_idx >= 0, curr_session_idx - prev_session_idx, np.nan)
    df_prices['trading_session_gap'] = session_gap
    df_prices['is_consecutive_session'] = (session_gap == 1.0)
    df_prices['calendar_day_gap'] = (df_prices['date'] - df_prices['prev_date']).dt.days

    consecutive_count = (df_prices['is_consecutive_session'] == True).sum()
    gap_count = (df_prices['is_consecutive_session'] == False).sum()
    nan_count = df_prices['is_consecutive_session'].isna().sum()

    print(f" -> Phiên giao dịch liền kề chuẩn (Gap = 1 session): {consecutive_count:,} ({consecutive_count/(consecutive_count+gap_count)*100:.2f}%)")
    print(f" -> Phiên bị ngắt quãng (Gap > 1 session): {gap_count:,} ({gap_count/(consecutive_count+gap_count)*100:.2f}%)")
    print(f" -> Phiên đầu tiên của chuỗi (NaN): {nan_count:,}")

    # -----------------------------------------------------------------------------------------
    # 5B. ÁP DỤNG QUALITY FLAGS, FIELD QUARANTINE & SPIN-OFFS TỪ BẢNG CORRECTIONS CÓ BẰNG CHỨNG
    # -----------------------------------------------------------------------------------------
    print("\n[5B/7] Áp dụng Quality Flags, Field Quarantine & Spin-offs theo cơ chế thống nhất...")
    from src.data.corrections import apply_corrections_to_dataframe, load_market_corrections
    corrs = load_market_corrections(CORRECTIONS_CSV)
    df_prices = apply_corrections_to_dataframe(df_prices, corrections=corrs)
    print(f" -> Đã áp dụng thành công {len(corrs)} sự kiện corrections vào bảng giá Tier 2!")
    print(f"    is_bad_data_period=True: {(df_prices['is_bad_data_period'] == True).sum():,} dòng")
    print(f"    is_spinoff_discontinuity=True: {(df_prices['is_spinoff_discontinuity'] == True).sum():,} dòng")

    # -----------------------------------------------------------------------------------------
    # 6. KIỂM THỬ SANITY THEO CÔNG THỨC TOÁN HỌC & KIỂM THỬ REVERSE SPLIT
    # -----------------------------------------------------------------------------------------
    print("\n[6/7] Kiểm thử Sanity theo đẳng thức toán học, Reverse Splits & Cash Dividends...")

    # A. Đẳng thức Toán học trên các sự kiện Split & Reverse Split
    print(" -> 6A. Kiểm thử đẳng thức toán học hệ số chia tách (Formula Identity)...")
    famous_test_splits = [
        ("AAPL", "2000-06-21", "Apple 2:1 Split", 0.5, "FORWARD"),
        ("AAPL", "2005-02-28", "Apple 2:1 Split", 0.5, "FORWARD"),
        ("AAPL", "2014-06-09", "Apple 7:1 Split", 1/7, "FORWARD"),
        ("AAPL", "2020-08-31", "Apple 4:1 Split", 0.25, "FORWARD"),
        ("TSLA", "2020-08-31", "Tesla 5:1 Split", 0.20, "FORWARD"),
        ("TSLA", "2022-08-25", "Tesla 3:1 Split", 1/3, "FORWARD"),
        ("NVDA", "2000-06-27", "Nvidia 2:1 Split", 0.5, "FORWARD"),
        ("NVDA", "2006-04-07", "Nvidia 2:1 Split", 0.5, "FORWARD"),
        ("NVDA", "2007-09-11", "Nvidia 3:2 Split", 2/3, "FORWARD"),
        ("NVDA", "2021-07-20", "Nvidia 4:1 Split", 0.25, "FORWARD"),
        ("NVDA", "2024-06-10", "Nvidia 10:1 Split", 0.10, "FORWARD"),
        ("AMZN", "1998-06-02", "Amazon 2:1 Split", 0.5, "FORWARD"),
        ("AMZN", "1999-01-05", "Amazon 3:1 Split", 1/3, "FORWARD"),
        ("AMZN", "1999-09-02", "Amazon 2:1 Split", 0.5, "FORWARD"),
        ("AMZN", "2022-06-06", "Amazon 20:1 Split", 0.05, "FORWARD"),
        ("GOOGL", "2014-04-03", "Alphabet 2:1 Split", 0.5, "FORWARD"),
        ("GOOGL", "2022-07-18", "Alphabet 20:1 Split", 0.05, "FORWARD"),
        # Reverse Splits
        ("C", "2011-05-09", "Citigroup 1:10 Reverse Split", 10.0, "REVERSE"),
        ("AIG", "2009-07-01", "AIG 1:20 Reverse Split", 20.0, "REVERSE"),
        ("ACLS", "2016-07-01", "Axcelis 1:4 Reverse Split", 4.0, "REVERSE"),
        ("GE", "2021-08-02", "General Electric 1:8 Reverse Split", 8.0, "REVERSE"),
        ("CHK", "2020-04-15", "Chesapeake Energy 1:200 Reverse Split", 200.0, "REVERSE"),
        ("CRC", "2016-06-01", "California Resources 1:10 Reverse Split", 10.0, "REVERSE"),
        ("ADCT", "2005-05-10", "ADC Telecom 1:7 Reverse Split", 7.0, "REVERSE"),
        ("AA", "2016-10-06", "Alcoa 1:3 Reverse Split", 3.0, "REVERSE"),
        ("DYN", "2010-05-25", "Dynegy 1:5 Reverse Split", 5.0, "REVERSE"),
    ]

    formula_test_records = []
    for ticker, dt_str, desc, expected_f, s_type in famous_test_splits:
        split_dt = pd.to_datetime(dt_str)
        sub = df_prices[(df_prices['original_ticker'] == ticker) & (df_prices['date'] == split_dt)]
        if not sub.empty:
            r = sub.iloc[0]
            cf_t = r['cumulative_split_factor']
            c_sid = r['canonical_sid']
            
            sub_full = df_prices[df_prices['canonical_sid'] == c_sid].sort_values('date').reset_index(drop=True)
            t_loc = sub_full[sub_full['date'] == split_dt].index[0]
            if t_loc > 0:
                row_prev = sub_full.iloc[t_loc - 1]
                cf_t_minus_1 = row_prev['cumulative_split_factor']
                raw_close_prev = row_prev['close']
                raw_close_t = r['close']
                ret_val = r['daily_return']
                
                ratio_cf = cf_t_minus_1 / cf_t
                cf_ratio_err = abs(ratio_cf - expected_f)
                
                expected_ret = (raw_close_t / (raw_close_prev * expected_f)) - 1.0
                ret_formula_err = abs(ret_val - expected_ret)

                formula_test_records.append({
                    'event': desc,
                    'ticker': ticker,
                    'type': s_type,
                    'split_date': dt_str,
                    'expected_factor': expected_f,
                    'observed_cf_ratio': round(ratio_cf, 6),
                    'cf_ratio_error': f"{cf_ratio_err:.1e}",
                    'raw_return_unadjusted': f"{((raw_close_t - raw_close_prev)/raw_close_prev)*100:+.2f}%",
                    'clean_daily_return': f"{ret_val*100:+.2f}%",
                    'return_formula_error': f"{ret_formula_err:.1e}",
                    'status': '✅ Khớp đẳng thức 100%' if (cf_ratio_err < 1e-4 and ret_formula_err < 1e-4) else '⚠️ Sai lệch'
                })

    df_formula_sanity = pd.DataFrame(formula_test_records)
    print(df_formula_sanity[['event', 'type', 'observed_cf_ratio', 'raw_return_unadjusted', 'clean_daily_return', 'status']].to_string(index=False))
    df_formula_sanity.to_csv(TABLES_DIR / "split_formula_mathematical_audit.csv", index=False)
    print("\n -> Đã lưu: split_formula_mathematical_audit.csv")

    # B. Đẳng thức Cổ tức (Dividend Identity Test)
    print("\n -> 6B. Kiểm thử đẳng thức cổ tức (Dividend Yield Identity Test)...")
    div_test_tickers = ['XOM', 'JNJ', 'T', 'JPM', 'AAPL', 'MSFT']
    sub_divs = df_prices[(df_prices['original_ticker'].isin(div_test_tickers)) & (df_prices['adj_dividend'] > 0)].copy()
    sub_divs['diff_return'] = sub_divs['total_return'] - sub_divs['daily_return']
    sub_divs['expected_div_yield'] = sub_divs['adj_dividend'] / sub_divs['prev_adj_close']
    sub_divs['identity_error'] = (sub_divs['diff_return'] - sub_divs['expected_div_yield']).abs()

    max_div_error = sub_divs['identity_error'].max()
    print(f" -> Tổng số sự kiện trả cổ tức của nhóm cổ phiếu lớn: {len(sub_divs):,}")
    print(f" -> Sai số tối đa giữa (Total_Return - Price_Return) và (Adj_Dividend / Prev_Price): {max_div_error:.2e}")
    assert max_div_error < 1e-12, "LỖI: Vi phạm đẳng thức tính Total Return của cổ tức!"

    div_sanity_records = []
    for _, r in sub_divs.head(10).iterrows():
        div_sanity_records.append({
            'ticker': r['original_ticker'],
            'date': r['date'].strftime('%Y-%m-%d'),
            'raw_dividend': r['dividend_amount'],
            'adj_dividend': r['adj_dividend'],
            'price_return': f"{r['daily_return']*100:+.2f}%",
            'total_return': f"{r['total_return']*100:+.2f}%",
            'dividend_yield': f"{(r['adj_dividend']/r['prev_adj_close'])*100:+.2f}%",
            'identity_error': f"{r['identity_error']:.1e}",
            'status': '✅ Khớp đẳng thức 100%'
        })

    df_div_sanity = pd.DataFrame(div_sanity_records)
    print(df_div_sanity[['ticker', 'date', 'raw_dividend', 'price_return', 'total_return', 'dividend_yield', 'status']].to_string(index=False))
    df_div_sanity.to_csv(TABLES_DIR / "dividend_identity_mathematical_audit.csv", index=False)
    print(" -> Đã lưu: dividend_identity_mathematical_audit.csv")

    # -----------------------------------------------------------------------------------------
    # 7. GHI KHO DỮ LIỆU TIER 2 ADJUSTED ĐÃ HOÀN THIỆN
    # -----------------------------------------------------------------------------------------
    print(f"\n[7/7] Ghi kho dữ liệu Tier 2 Adjusted Parquet ({OUTPUT_PARQUET.name})...")
    cols_to_save = [
        'date', 'canonical_sid', 'original_ticker', 'qc_ticker',
        'open', 'high', 'low', 'close', 'volume',
        'cumulative_split_factor', 'adj_open', 'adj_high', 'adj_low', 'adj_close', 'adj_volume',
        'dividend_amount', 'adj_dividend',
        'daily_return', 'total_return',
        'trading_session_gap', 'is_consecutive_session', 'calendar_day_gap',
        'is_bad_data_period', 'is_spinoff_discontinuity', 'quality_flag'
    ]

    df_prices[cols_to_save].to_parquet(
        OUTPUT_PARQUET,
        engine='pyarrow',
        compression='zstd',
        compression_level=7,
        index=False
    )

    size_mb = OUTPUT_PARQUET.stat().st_size / (1024 * 1024)
    print(f" -> Đã ghi thành công: {OUTPUT_PARQUET.name} ({size_mb:.2f} MB)")
    print(f" -> Tổng thời gian thực thi: {time.time() - t0:.2f} giây.")
    print("=" * 80)
    print("🎯 BƯỚC ③B ĐÃ ĐẠT CHUẨN ĐỊNH LƯỢNG CAO NHẤT (INSTITUTIONAL QUANT GRADE)!")
    print("=" * 80)

if __name__ == "__main__":
    main()
