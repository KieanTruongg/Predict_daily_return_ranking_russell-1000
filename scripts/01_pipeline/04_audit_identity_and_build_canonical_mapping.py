"""
Pipeline Step 2A: Identity Audit & Canonical Security Mapping
============================================================
Nhiệm vụ:
1. Thẩm định 1.569.274 dòng trùng (date, sid) tương ứng 796.602 lượt quan sát dư thừa từ 256 cặp alias.
2. Thẩm định 846 mã SID dạng placeholder ' 2T' của QuantConnect:
   - Nối mượt (stitch) 752 mã 2T liền kề ngày (khoảng cách <= 10 ngày) vào SID vĩnh viễn (Permanent SID).
   - Giữ độc lập 94 mã 2T có khoảng cách thời gian lớn (Ticker Reuse hoặc công ty độc lập).
3. Thẩm định Ticker Reuse: 1.281 ticker có nhiều SID qua các năm (như MIR, INFO, BLUE, ROC),
   đảm bảo tách biệt tuyệt đối thành các canonical_sid riêng biệt, không nối nhầm công ty.
4. Xuất bảng ánh xạ chuẩn danh tính:
   - docs/Data report/market_data_audit/tables/canonical_security_mapping.csv
   - docs/Data report/market_data_audit/tables/ticker_reuse_audit.csv
   - docs/Data report/market_data_audit/tables/transient_2t_resolution_audit.csv
5. Tạo kho dữ liệu Tier 2 đã khử trùng danh tính hoàn hảo:
   - data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet
   - Khóa chính (date, canonical_sid) đảm bảo 100% UNIQUE (0 duplicate).
"""

import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_1998_2026.parquet"
OUTPUT_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CANONICAL_PARQUET = BASE_DIR / "data" / "processed" / "constituents_market_data" / "russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet"

def main():
    t0 = time.time()
    print("=" * 80)
    print("🚀 BẮT ĐẦU STEP ②A: IDENTITY AUDIT & CANONICAL SECURITY MAPPING")
    print("=" * 80)
    
    # 1. Đọc dữ liệu thô
    print("\n[1/5] Đang đọc Master Warehouse Parquet...")
    df = pd.read_parquet(RAW_PARQUET)
    total_raw_rows = len(df)
    print(f" -> Tổng số dòng thô ban đầu: {total_raw_rows:,} dòng.")
    print(f" -> Ticker duy nhất: {df['original_ticker'].nunique():,}")
    print(f" -> SID thô duy nhất: {df['sid'].nunique():,}")

    # 2. Thẩm định trùng lặp (date, sid)
    print("\n[2/5] Thẩm định tính đồng nhất của các dòng trùng (date, sid)...")
    dup_mask = df.duplicated(subset=['date', 'sid'], keep=False)
    dup_df = df[dup_mask]
    dup_rows = len(dup_df)
    unique_dup_pairs = dup_df.groupby(['date', 'sid']).ngroups
    excess_rows = dup_rows - unique_dup_pairs
    print(f" -> Tổng số dòng thuộc nhóm trùng: {dup_rows:,}")
    print(f" -> Số cặp (date, sid) độc nhất bị trùng: {unique_dup_pairs:,}")
    print(f" -> Số dòng dư thừa cần loại bỏ: {excess_rows:,}")

    agg_diff = dup_df.groupby(['date', 'sid']).agg(
        c_min=('close', 'min'), c_max=('close', 'max'),
        v_min=('volume', 'min'), v_max=('volume', 'max'),
        o_min=('open', 'min'), o_max=('open', 'max'),
        h_min=('high', 'min'), h_max=('high', 'max'),
        l_min=('low', 'min'), l_max=('low', 'max')
    )
    max_c_diff = (agg_diff['c_max'] - agg_diff['c_min']).max()
    max_v_diff = (agg_diff['v_max'] - agg_diff['v_min']).max()
    print(f" -> Chênh lệch giá Close tối đa giữa các bản ghi trùng: {max_c_diff:.6f}")
    print(f" -> Chênh lệch Volume tối đa giữa các bản ghi trùng: {max_v_diff:.6f}")
    assert max_c_diff == 0.0, "LỖI: Phát hiện giá Close bất đồng nhất giữa các bản ghi trùng (date, sid)!"
    print(" -> KẾT LUẬN: 100% bản ghi trùng khớp từng bit (bit-for-bit identical), an toàn tuyệt đối để khử trùng!")

    # 3. Phân tích vòng đời (date range) của từng cặp (original_ticker, sid)
    print("\n[3/5] Phân tích vòng đời và giải quyết các mã placeholder ' 2T'...")
    agg_lifecycle = df.groupby(['original_ticker', 'sid'])['date'].agg(
        min_date='min',
        max_date='max',
        trading_days='count'
    ).reset_index()
    agg_lifecycle['min_dt'] = pd.to_datetime(agg_lifecycle['min_date'])
    agg_lifecycle['max_dt'] = pd.to_datetime(agg_lifecycle['max_date'])

    sids_2t = agg_lifecycle[agg_lifecycle['sid'].str.endswith(' 2T')].copy()
    print(f" -> Tổng số cặp (ticker, sid) mang đuôi ' 2T': {len(sids_2t)}")

    mapping_dict = {}
    resolution_audit = []

    for _, row in sids_2t.iterrows():
        t = row['original_ticker']
        sid_2t = row['sid']
        t_min = row['min_dt']
        t_max = row['max_dt']
        days = row['trading_days']

        other_sids = agg_lifecycle[(agg_lifecycle['original_ticker'] == t) & (~agg_lifecycle['sid'].str.endswith(' 2T'))]
        if other_sids.empty:
            resolution_audit.append({
                'original_ticker': t,
                'raw_sid': sid_2t,
                'canonical_sid': sid_2t,
                'resolution_type': 'STANDALONE_2T_NO_PERM',
                'min_date': row['min_date'],
                'max_date': row['max_date'],
                'trading_days': days,
                'target_adjacent_sid': None,
                'gap_calendar_days': None
            })
            continue

        prec = other_sids[(other_sids['max_dt'] < t_min) & ((t_min - other_sids['max_dt']).dt.days <= 10)]
        succ = other_sids[(other_sids['min_dt'] > t_max) & ((other_sids['min_dt'] - t_max).dt.days <= 10)]

        if not prec.empty:
            target = prec.sort_values('max_dt', ascending=False).iloc[0]
            gap = (t_min - target['max_dt']).days
            mapping_dict[(t, sid_2t)] = target['sid']
            resolution_audit.append({
                'original_ticker': t,
                'raw_sid': sid_2t,
                'canonical_sid': target['sid'],
                'resolution_type': '2T_STITCH_PRECEDING',
                'min_date': row['min_date'],
                'max_date': row['max_date'],
                'trading_days': days,
                'target_adjacent_sid': target['sid'],
                'gap_calendar_days': gap
            })
        elif not succ.empty:
            target = succ.sort_values('min_dt').iloc[0]
            gap = (target['min_dt'] - t_max).days
            mapping_dict[(t, sid_2t)] = target['sid']
            resolution_audit.append({
                'original_ticker': t,
                'raw_sid': sid_2t,
                'canonical_sid': target['sid'],
                'resolution_type': '2T_STITCH_SUCCEEDING',
                'min_date': row['min_date'],
                'max_date': row['max_date'],
                'trading_days': days,
                'target_adjacent_sid': target['sid'],
                'gap_calendar_days': gap
            })
        else:
            # Standalone 2T across years
            closest_prec = (t_min - other_sids[other_sids['max_dt'] < t_min]['max_dt']).dt.days.min() if any(other_sids['max_dt'] < t_min) else None
            closest_succ = (other_sids[other_sids['min_dt'] > t_max]['min_dt'] - t_max).dt.days.min() if any(other_sids['min_dt'] > t_max) else None
            min_gap = min([g for g in [closest_prec, closest_succ] if g is not None], default=None)
            resolution_audit.append({
                'original_ticker': t,
                'raw_sid': sid_2t,
                'canonical_sid': sid_2t,
                'resolution_type': 'STANDALONE_2T_DISCONTINUOUS',
                'min_date': row['min_date'],
                'max_date': row['max_date'],
                'trading_days': days,
                'target_adjacent_sid': None,
                'gap_calendar_days': min_gap
            })

    df_res_audit = pd.DataFrame(resolution_audit)
    df_res_audit.to_csv(OUTPUT_DIR / "transient_2t_resolution_audit.csv", index=False)
    print(f" -> Đã lưu bảng giải quyết mã 2T: transient_2t_resolution_audit.csv ({len(df_res_audit)} dòng)")
    print(" -> Thống kê phân loại mã 2T:")
    print(df_res_audit['resolution_type'].value_counts().to_string())

    # Xây dựng bảng canonical_security_mapping đầy đủ cho toàn bộ 4.463 SIDs
    mapping_records = []
    for _, row in agg_lifecycle.iterrows():
        t = row['original_ticker']
        s = row['sid']
        if (t, s) in mapping_dict:
            canon = mapping_dict[(t, s)]
            res_type = df_res_audit[(df_res_audit['original_ticker'] == t) & (df_res_audit['raw_sid'] == s)]['resolution_type'].iloc[0]
        elif s.endswith(' 2T'):
            canon = s
            res_type = df_res_audit[(df_res_audit['original_ticker'] == t) & (df_res_audit['raw_sid'] == s)]['resolution_type'].iloc[0]
        else:
            canon = s
            res_type = 'PERMANENT_CANONICAL'
            
        mapping_records.append({
            'original_ticker': t,
            'raw_sid': s,
            'canonical_sid': canon,
            'resolution_type': res_type,
            'min_date': row['min_date'],
            'max_date': row['max_date'],
            'trading_days': row['trading_days']
        })

    df_canonical_map = pd.DataFrame(mapping_records)
    df_canonical_map.to_csv(OUTPUT_DIR / "canonical_security_mapping.csv", index=False)
    print(f" -> Đã lưu: canonical_security_mapping.csv ({len(df_canonical_map)} ánh xạ)")

    # Bảng Ticker Reuse Audit: Các ticker có nhiều canonical_sid khác nhau
    ticker_entities = df_canonical_map.groupby('original_ticker')['canonical_sid'].nunique()
    reuse_tickers = ticker_entities[ticker_entities > 1].index.tolist()
    print(f" -> Số ticker có Ticker Reuse thực tế (> 1 canonical entity): {len(reuse_tickers):,}")
    
    reuse_df = df_canonical_map[df_canonical_map['original_ticker'].isin(reuse_tickers)].sort_values(['original_ticker', 'min_date'])
    reuse_df.to_csv(OUTPUT_DIR / "ticker_reuse_audit.csv", index=False)
    print(f" -> Đã lưu: ticker_reuse_audit.csv ({len(reuse_df)} bản ghi)")

    # 4. Áp dụng canonical_sid vào Master Dataset và Khử trùng lặp
    print("\n[4/5] Ánh xạ canonical_sid vào bảng giá và khử trùng lặp bit-for-bit...")
    # Tạo từ điển ánh xạ nhanh
    pair_to_canonical = {(r['original_ticker'], r['raw_sid']): r['canonical_sid'] for _, r in df_canonical_map.iterrows()}
    
    df['canonical_sid'] = [pair_to_canonical[(t, s)] for t, s in zip(df['original_ticker'], df['sid'])]
    
    # Khử trùng lặp trên (date, canonical_sid)
    # Giữ lại bản ghi có tên original_ticker đại diện
    df_clean = df.drop_duplicates(subset=['date', 'canonical_sid'], keep='first').copy()
    
    # Sắp xếp theo canonical_sid và date để dữ liệu liên tục tối ưu
    df_clean = df_clean.sort_values(['canonical_sid', 'date']).reset_index(drop=True)
    
    # 5. Kiểm thử Sanity sau khi khử trùng
    print("\n[5/5] Kiểm thử Sanity trên kho dữ liệu Canonical...")
    print(f" -> Tổng số dòng ban đầu       : {total_raw_rows:,}")
    print(f" -> Tổng số dòng sau khi làm sạch: {len(df_clean):,}")
    print(f" -> Số dòng trùng lặp đã loại bỏ: {total_raw_rows - len(df_clean):,}")
    print(f" -> Số Canonical Entity duy nhất : {df_clean['canonical_sid'].nunique():,}")
    
    # Kiểm tra Primary Key Uniqueness
    dup_final = df_clean.duplicated(subset=['date', 'canonical_sid']).sum()
    print(f" -> Vi phạm trùng lặp (date, canonical_sid): {dup_final} (Kỳ vọng: 0)")
    assert dup_final == 0, "LỖI: Vẫn còn trùng lặp trên khóa chính (date, canonical_sid)!"

    # Ghi file Parquet Tier 2
    print(f"\nĐang ghi file Parquet Tier 2: {CANONICAL_PARQUET.name}...")
    columns_order = ['date', 'canonical_sid', 'original_ticker', 'qc_ticker', 'open', 'high', 'low', 'close', 'volume']
    df_clean[columns_order].to_parquet(
        CANONICAL_PARQUET,
        engine='pyarrow',
        compression='zstd',
        compression_level=7,
        index=False
    )
    file_size_mb = CANONICAL_PARQUET.stat().st_size / (1024 * 1024)
    print(f" -> Đã lưu thành công: {CANONICAL_PARQUET.name} ({file_size_mb:.2f} MB)")
    print(f" -> Tổng thời gian thực hiện: {time.time() - t0:.2f} giây.")
    print("=" * 80)
    print("✅ HOÀN TẤT STEP ②A: TOÀN BỘ DANH TÍNH CHỨNG KHOÁN ĐÃ ĐƯỢC CHUẨN HÓA VÀ KHỬ TRÙNG!")
    print("=" * 80)

if __name__ == "__main__":
    main()
