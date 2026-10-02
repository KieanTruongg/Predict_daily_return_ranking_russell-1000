"""
Deep Audit: Survivorship Bias & Linkage Reconciliation
=======================================================
Bước 1: Bảng linkage Russell PIT ↔ QC OHLCV (audit/reconcile từ M4)
Bước 2: Survivorship Bias Test — so sánh OHLCV coverage giữa Survivor vs Disappeared
Bước 3: Missing breakdown theo thời gian × nhóm (Survivor vs Disappeared)  
Bước 4: Identity Mapping audit — kiểm tra các case còn lại từ Test 7
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"
PARQUET_DIR = "data/processed/by_year"
AUDIT_DIR = "data/processed/audit/by_year"

YEARS = list(range(2000, 2027))

# =============================================================================
# UTILITY: Load all data
# =============================================================================
def load_all_data():
    """Load universe, parquet tickers, and audit data for all years."""
    universe = {}
    parquet_tickers = {}
    audit_data = {}
    
    for yr in YEARS:
        # Universe JSON
        fp = os.path.join(UNIVERSE_DIR, f"russell1000_{yr}.json")
        if os.path.exists(fp):
            with open(fp, 'r', encoding='utf-8') as f:
                universe[yr] = set(json.load(f))
        
        # Parquet tickers
        pq = os.path.join(PARQUET_DIR, f"russell1000_{yr}.parquet")
        if os.path.exists(pq):
            df = pd.read_parquet(pq, columns=['ticker'])
            parquet_tickers[yr] = set(df['ticker'].unique())
        
        # Audit CSV
        aud = os.path.join(AUDIT_DIR, f"audit_{yr}.csv")
        if os.path.exists(aud):
            audit_data[yr] = pd.read_csv(aud)
    
    return universe, parquet_tickers, audit_data


def classify_stocks(universe):
    """Phân loại cổ phiếu thành Survivor (còn tồn tại 2025/2026) vs Disappeared."""
    all_tickers = set().union(*universe.values())
    
    # Stocks hiện diện ở 2025 hoặc 2026 = Survivor
    recent_set = universe.get(2025, set()) | universe.get(2026, set())
    
    survivors = {}
    disappeared = {}
    
    for t in all_tickers:
        active_yrs = sorted([y for y in YEARS if t in universe.get(y, set())])
        info = {
            'first_year': active_yrs[0],
            'last_year': active_yrs[-1],
            'active_years': len(active_yrs)
        }
        if t in recent_set:
            survivors[t] = info
        else:
            disappeared[t] = info
    
    return survivors, disappeared


# =============================================================================
# BƯỚC 1: Linkage Reconciliation Table
# =============================================================================
def step1_linkage_table(universe, parquet_tickers):
    print("=" * 90)
    print("📌 BƯỚC 1: BẢNG LINKAGE RUSSELL PIT ↔ QUANTCONNECT OHLCV")
    print("=" * 90)
    
    rows = []
    for yr in YEARS:
        r_set = universe.get(yr, set())
        p_set = parquet_tickers.get(yr, set())
        match = r_set & p_set
        missing = r_set - p_set
        extra = p_set - r_set
        rate = len(match) / len(r_set) * 100 if r_set else 0
        
        rows.append({
            'Year': yr,
            'Russell': len(r_set),
            'QC_OHLCV': len(p_set),
            'Match': len(match),
            'Missing': len(missing),
            'Extra': len(extra),
            'Match%': f"{rate:.1f}%"
        })
    
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    
    total_r = sum(r['Russell'] for r in rows)
    total_match = sum(r['Match'] for r in rows)
    total_missing = sum(r['Missing'] for r in rows)
    print(f"\n📊 TỔNG: {total_r:,} stock-year | Match: {total_match:,} | Missing: {total_missing:,} | Rate: {total_match/total_r*100:.2f}%")
    print()
    return df


# =============================================================================
# BƯỚC 2: Survivorship Bias Test — Coverage comparison
# =============================================================================
def step2_survivorship_bias(universe, audit_data, survivors, disappeared):
    print("=" * 90)
    print("🔥 BƯỚC 2: SURVIVORSHIP BIAS TEST — SO SÁNH OHLCV COVERAGE")
    print("=" * 90)
    
    # Tạo lookup: ticker → tất cả audit records
    # Cho mỗi stock, kiểm tra tổng stock-year appearances vs có OHLCV
    
    def compute_group_coverage(group_dict, label):
        """Tính coverage cho nhóm stock."""
        total_appearances = 0
        has_ohlcv = 0
        empty_count = 0
        partial_count = 0
        
        per_stock_results = []
        
        for ticker, info in group_dict.items():
            # Tìm tất cả năm ticker xuất hiện trong universe
            active_years = [y for y in YEARS if ticker in universe.get(y, set())]
            
            success_years = 0
            empty_years = 0
            partial_years = 0
            
            for yr in active_years:
                total_appearances += 1
                if yr in audit_data:
                    df_aud = audit_data[yr]
                    row = df_aud[df_aud['russell_ticker'] == ticker]
                    if not row.empty:
                        status = row.iloc[0]['status']
                        if status == 'SUCCESS':
                            has_ohlcv += 1
                            success_years += 1
                        elif status == 'EMPTY':
                            empty_count += 1
                            empty_years += 1
                        else:  # PARTIAL
                            partial_count += 1
                            partial_years += 1
                            has_ohlcv += 1  # PARTIAL vẫn có data
                    else:
                        empty_count += 1
                        empty_years += 1
            
            cov = (success_years + partial_years) / len(active_years) * 100 if active_years else 0
            per_stock_results.append({
                'ticker': ticker,
                'active_years': len(active_years),
                'success': success_years,
                'partial': partial_years,
                'empty': empty_years,
                'coverage_pct': cov
            })
        
        return {
            'label': label,
            'num_stocks': len(group_dict),
            'total_stock_years': total_appearances,
            'has_ohlcv': has_ohlcv,
            'empty': empty_count,
            'partial': partial_count,
            'coverage_pct': has_ohlcv / total_appearances * 100 if total_appearances else 0,
        }, pd.DataFrame(per_stock_results)
    
    surv_stats, df_surv_detail = compute_group_coverage(survivors, "Còn tồn tại (Survivor)")
    disap_stats, df_disap_detail = compute_group_coverage(disappeared, "Đã biến mất (Disappeared)")
    
    print(f"\n{'Nhóm':<30} {'Số stock':>10} {'Stock-years':>13} {'Có OHLCV':>10} {'Empty':>8} {'Coverage':>10}")
    print("-" * 90)
    for s in [surv_stats, disap_stats]:
        print(f"{s['label']:<30} {s['num_stocks']:>10,} {s['total_stock_years']:>13,} {s['has_ohlcv']:>10,} {s['empty']:>8,} {s['coverage_pct']:>9.1f}%")
    
    diff = surv_stats['coverage_pct'] - disap_stats['coverage_pct']
    print(f"\n📊 CHÊNH LỆCH COVERAGE: {diff:+.1f} percentage points")
    
    if abs(diff) < 5:
        print("   → Hai nhóm tương đối gần nhau → bằng chứng TỐT rằng QC không chỉ giữ dữ liệu của survivor")
    elif abs(diff) < 15:
        print("   → Chênh lệch vừa phải → cần phân tích thêm nguyên nhân (historical data limitation?)")
    else:
        print("   → ⚠️ Chênh lệch LỚN → cần điều tra kỹ về survivorship bias risk")
    
    # Per-stock coverage distribution
    print("\n--- Phân bố Coverage per-stock (Disappeared group) ---")
    bins = [0, 25, 50, 75, 90, 100.01]
    labels_b = ['0-25%', '25-50%', '50-75%', '75-90%', '90-100%']
    df_disap_detail['cov_bin'] = pd.cut(df_disap_detail['coverage_pct'], bins=bins, labels=labels_b, right=False)
    dist = df_disap_detail['cov_bin'].value_counts().sort_index()
    for b, cnt in dist.items():
        pct = cnt / len(df_disap_detail) * 100
        bar = "█" * int(pct / 2)
        print(f"   {b:<12} : {cnt:>5} stocks ({pct:5.1f}%) {bar}")
    
    # Stocks biến mất với 0% coverage
    zero_cov = df_disap_detail[df_disap_detail['coverage_pct'] == 0]
    print(f"\n   Stocks biến mất với 0% OHLCV coverage: {len(zero_cov)} stocks")
    if not zero_cov.empty:
        sample = zero_cov.sort_values('active_years', ascending=False).head(10)
        print(f"   Top 10 (theo số năm active):")
        for _, r in sample.iterrows():
            print(f"      {r['ticker']:<8} active {r['active_years']} years, 0 OHLCV records")
    
    print()
    return surv_stats, disap_stats, df_disap_detail


# =============================================================================
# BƯỚC 3: Missing breakdown theo thời gian × nhóm
# =============================================================================
def step3_missing_by_time_group(universe, audit_data, survivors, disappeared):
    print("=" * 90)
    print("📊 BƯỚC 3: MISSING BREAKDOWN THEO THỜI GIAN × NHÓM (SURVIVOR vs DISAPPEARED)")
    print("=" * 90)
    
    rows = []
    for yr in YEARS:
        r_set = universe.get(yr, set())
        surv_in_yr = r_set & set(survivors.keys())
        disap_in_yr = r_set & set(disappeared.keys())
        
        surv_missing = 0
        disap_missing = 0
        
        if yr in audit_data:
            df_aud = audit_data[yr]
            empty_tickers = set(df_aud[df_aud['status'] == 'EMPTY']['russell_ticker'])
            # Also count tickers in universe but NOT in audit at all
            audit_tickers = set(df_aud['russell_ticker'])
            not_in_audit = r_set - audit_tickers
            all_missing = empty_tickers | not_in_audit
            
            surv_missing = len(all_missing & surv_in_yr)
            disap_missing = len(all_missing & disap_in_yr)
        
        total_missing = surv_missing + disap_missing
        rows.append({
            'Year': yr,
            'Russell': len(r_set),
            'Survivor_in_yr': len(surv_in_yr),
            'Disap_in_yr': len(disap_in_yr),
            'Missing_Surv': surv_missing,
            'Missing_Disap': disap_missing,
            'Total_Missing': total_missing,
            'Missing_Disap%': f"{disap_missing/total_missing*100:.0f}%" if total_missing > 0 else "-"
        })
    
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    
    # Summary
    total_miss_surv = sum(r['Missing_Surv'] for r in rows)
    total_miss_disap = sum(r['Missing_Disap'] for r in rows)
    total_miss = total_miss_surv + total_miss_disap
    
    print(f"\n📊 TỔNG MISSING: {total_miss:,}")
    print(f"   • Từ nhóm Survivor:    {total_miss_surv:>5,} ({total_miss_surv/total_miss*100:.1f}%)")
    print(f"   • Từ nhóm Disappeared: {total_miss_disap:>5,} ({total_miss_disap/total_miss*100:.1f}%)")
    
    # Pre-2012 vs Post-2012
    pre2012_miss = sum(r['Total_Missing'] for r in rows if r['Year'] <= 2011)
    post2012_miss = sum(r['Total_Missing'] for r in rows if r['Year'] > 2011)
    print(f"\n   • Missing 2000–2011: {pre2012_miss:,} ({pre2012_miss/total_miss*100:.1f}%)")
    print(f"   • Missing 2012–2026: {post2012_miss:,} ({post2012_miss/total_miss*100:.1f}%)")
    print()
    return df


# =============================================================================
# BƯỚC 4: Identity Mapping Audit
# =============================================================================
def step4_identity_mapping(audit_data):
    print("=" * 90)
    print("🔗 BƯỚC 4: IDENTITY MAPPING AUDIT — TICKER FORMAT & REMAINING CASES")
    print("=" * 90)
    
    # Collect all special ticker cases
    all_special = []
    for yr in YEARS:
        if yr in audit_data:
            df_aud = audit_data[yr]
            special = df_aud[df_aud['russell_ticker'].str.contains(r'[-.]', regex=True, na=False)]
            for _, row in special.iterrows():
                all_special.append({
                    'year': yr,
                    'russell_ticker': row['russell_ticker'],
                    'qc_candidate': row.get('qc_candidate', ''),
                    'qc_symbol': row.get('qc_symbol', ''),
                    'status': row['status'],
                    'trading_days': row.get('trading_days', 0),
                    'reason': row.get('reason', '')
                })
    
    df_special = pd.DataFrame(all_special)
    
    if df_special.empty:
        print("Không tìm thấy ticker đặc biệt.")
        return df_special
    
    # Summary by ticker
    ticker_summary = df_special.groupby('russell_ticker').agg(
        appearances=('year', 'count'),
        success=('status', lambda x: (x == 'SUCCESS').sum()),
        empty=('status', lambda x: (x == 'EMPTY').sum()),
        partial=('status', lambda x: (x == 'PARTIAL').sum())
    ).reset_index()
    ticker_summary['success_rate'] = (ticker_summary['success'] / ticker_summary['appearances'] * 100).round(1)
    
    print("\n--- Tổng hợp Ticker đặc biệt (chứa '-' hoặc '.') ---")
    print(ticker_summary.sort_values('appearances', ascending=False).to_string(index=False))
    
    total = len(df_special)
    success = len(df_special[df_special['status'] == 'SUCCESS'])
    empty = len(df_special[df_special['status'] == 'EMPTY'])
    partial = len(df_special[df_special['status'] == 'PARTIAL'])
    print(f"\n📊 TỔNG: {total} lượt | SUCCESS: {success} ({success/total*100:.1f}%) | EMPTY: {empty} ({empty/total*100:.1f}%) | PARTIAL: {partial}")
    
    # Show FAILED cases in detail
    failed = df_special[df_special['status'] != 'SUCCESS']
    if not failed.empty:
        print(f"\n--- ⚠️ {len(failed)} lượt KHÔNG SUCCESS (cần kiểm tra) ---")
        print(failed[['year', 'russell_ticker', 'qc_candidate', 'status', 'reason']].to_string(index=False))
    
    # Also check famous ticker changes
    print("\n--- Kiểm tra các case đổi Ticker nổi tiếng ---")
    famous_changes = [
        ('FB', 'META', 'Meta Platforms'),
        ('ANTM', 'ELV', 'Elevance Health'),
        ('KFT', 'MDLZ', 'Mondelez'),
        ('LB', 'BBWI', 'Bath & Body Works'),
        ('AAXN', 'AXON', 'Axon Enterprise'),
        ('ACE', 'CB', 'Chubb Limited'),
        ('PCLN', 'BKNG', 'Booking Holdings'),
        ('TWX', 'T', 'AT&T/Time Warner'),
    ]
    
    for old, new, name in famous_changes:
        old_years = []
        new_years = []
        for yr in YEARS:
            if yr in audit_data:
                df_aud = audit_data[yr]
                if old in df_aud['russell_ticker'].values:
                    status = df_aud[df_aud['russell_ticker'] == old].iloc[0]['status']
                    old_years.append((yr, status))
                if new in df_aud['russell_ticker'].values:
                    status = df_aud[df_aud['russell_ticker'] == new].iloc[0]['status']
                    new_years.append((yr, status))
        
        old_range = f"{old_years[0][0]}–{old_years[-1][0]}" if old_years else "N/A"
        new_range = f"{new_years[0][0]}–{new_years[-1][0]}" if new_years else "N/A"
        old_statuses = set(s for _, s in old_years)
        new_statuses = set(s for _, s in new_years)
        
        transition = "✅" if ('SUCCESS' in old_statuses or not old_years) and ('SUCCESS' in new_statuses or not new_years) else "⚠️"
        print(f"   {transition} {name:<25} {old:<6} ({old_range}) → {new:<6} ({new_range})")
    
    print()
    return df_special


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n🔬 DEEP AUDIT: SURVIVORSHIP BIAS & LINKAGE RECONCILIATION")
    print("=" * 90)
    
    print("\n⏳ Loading all data...")
    universe, parquet_tickers, audit_data = load_all_data()
    print(f"   Loaded {len(universe)} years universe, {len(parquet_tickers)} years parquet, {len(audit_data)} years audit\n")
    
    # Classify stocks
    survivors, disappeared = classify_stocks(universe)
    print(f"   📊 Classification: {len(survivors):,} Survivors | {len(disappeared):,} Disappeared\n")
    
    # Run all 4 steps
    step1_linkage_table(universe, parquet_tickers)
    step2_survivorship_bias(universe, audit_data, survivors, disappeared)
    step3_missing_by_time_group(universe, audit_data, survivors, disappeared)
    step4_identity_mapping(audit_data)
    
    print("=" * 90)
    print("✅ DEEP AUDIT HOÀN TẤT")
    print("=" * 90)
