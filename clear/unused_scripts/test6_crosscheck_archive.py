"""
Test 6: Cross-check Archive - Đối chiếu chép Tập dữ liệu Universe Snapshot vs Raw Archive Dataset
================================================================================================
Mục tiêu:
1. Đọc tập dữ liệu archive thô (data/raw/universe/russell1000_pit_by_year.json hoặc russell1000_constituents.csv).
2. So sánh từng năm giữa Snapshot (`data/raw/universe/by_year/russell1000_{year}.json`) vs Raw Archive:
   - Intersection (Số mã nằm trong cả 2 tập): |A ∩ B|
   - Missing from Snapshot (Mã có trong Archive nhưng thiếu trong Snapshot): |Archive \ Snapshot|
   - Extra in Snapshot (Mã có trong Snapshot nhưng không có trong Archive): |Snapshot \ Archive|
   - Jaccard Similarity (% tương đồng): |A ∩ B| / |A ∪ B|
3. Phân tích nguyên nhân cụ thể đối với các mã bị thiếu (Missing) hoặc thừa (Extra).
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_BY_YEAR_DIR = "data/raw/universe/by_year"
ARCHIVE_JSON = "data/raw/universe/russell1000_pit_by_year.json"
ARCHIVE_CSV = "data/raw/universe/russell1000_constituents.csv"

def run_test6_crosscheck_archive():
    years = list(range(2000, 2027))
    
    # Load Snapshot Universe
    snapshot_by_year = {}
    for yr in years:
        fp = os.path.join(UNIVERSE_BY_YEAR_DIR, f"russell1000_{yr}.json")
        if os.path.exists(fp):
            with open(fp, 'r', encoding='utf-8') as f:
                snapshot_by_year[yr] = set(json.load(f))

    # Load Raw Archive Dataset
    archive_by_year = {}
    if os.path.exists(ARCHIVE_JSON):
        with open(ARCHIVE_JSON, 'r', encoding='utf-8') as f:
            raw_arc = json.load(f)
            # Inspect structure
            for k, v in raw_arc.items():
                try:
                    yr_int = int(k)
                    archive_by_year[yr_int] = set(v)
                except ValueError:
                    pass
    elif os.path.exists(ARCHIVE_CSV):
        df_arc = pd.read_csv(ARCHIVE_CSV)
        if 'year' in df_arc.columns and 'ticker' in df_arc.columns:
            for yr, group in df_arc.groupby('year'):
                archive_by_year[int(yr)] = set(group['ticker'].dropna().unique())

    crosscheck_results = []
    total_missing_samples = set()
    total_extra_samples = set()

    for yr in years:
        snap_set = snapshot_by_year.get(yr, set())
        arc_set = archive_by_year.get(yr, set())

        if not arc_set:
            crosscheck_results.append({
                'year': yr,
                'snapshot_cnt': len(snap_set),
                'archive_cnt': 0,
                'intersection': 0,
                'missing_cnt': 0,
                'extra_cnt': len(snap_set),
                'jaccard_similarity_pct': 0.0,
                'missing_samples': "-",
                'extra_samples': "-"
            })
            continue

        intersection = snap_set & arc_set
        missing = arc_set - snap_set
        extra = snap_set - arc_set

        total_missing_samples.update(missing)
        total_extra_samples.update(extra)

        union_cnt = len(snap_set | arc_set)
        jaccard_pct = (len(intersection) / union_cnt * 100) if union_cnt > 0 else 0.0

        crosscheck_results.append({
            'year': yr,
            'snapshot_cnt': len(snap_set),
            'archive_cnt': len(arc_set),
            'intersection': len(intersection),
            'missing_cnt': len(missing),
            'extra_cnt': len(extra),
            'jaccard_similarity_pct': round(jaccard_pct, 2),
            'missing_samples': ", ".join(sorted(list(missing))[:3]) if missing else "-",
            'extra_samples': ", ".join(sorted(list(extra))[:3]) if extra else "-"
        })

    df_res = pd.DataFrame(crosscheck_results)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST 6: CROSS-CHECK ARCHIVE - ĐỐI CHIẾU THÀNH PHẦN HOÀN CHỈNH")
    print("==================================================================================")
    print(df_res.to_string(index=False))

    avg_jaccard = df_res[df_res['archive_cnt'] > 0]['jaccard_similarity_pct'].mean()

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP KẾT QUẢ TEST 6:")
    print(f" • Tỷ lệ tương đồng Jaccard Similarity trung bình : {avg_jaccard:.2f}%")
    print(f" • Tổng số mã bị thiếu khác biệt (Missing from snapshot) : {len(total_missing_samples):,} mã")
    print(f" • Tổng số mã thừa khác biệt (Extra in snapshot)       : {len(total_extra_samples):,} mã")
    print("----------------------------------------------------------------------------------\n")

    return df_res

if __name__ == "__main__":
    run_test6_crosscheck_archive()
