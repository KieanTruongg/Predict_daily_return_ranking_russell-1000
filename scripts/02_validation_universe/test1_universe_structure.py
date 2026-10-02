"""
Test 1: Kiểm thử Cấu trúc, Ticker Rác & Duplicate trong Russell 1000 Universe
=============================================================================
Mục tiêu:
1. Schema & Data type: Đảm bảo dữ liệu JSON từng năm là danh sách chuỗi list[str].
2. Null / Empty / Whitespace: Phát hiện ticker bị null, rỗng (""), chỉ có khoảng trắng ("  "), hoặc bị dính space thừa (" AAPL ").
3. Duplicate Ticker: Kiểm tra xem trong cùng 1 năm có ticker nào bị lặp lại 2 lần trở lên không.
4. Ticker Format & Invalid Characters: Thống kê định dạng ticker đặc biệt (chứa dấu chấm '.', gạch ngang '-', gạch chéo '/').
"""

import json
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE_DIR = "data/raw/universe/by_year"

def run_test1_universe_structure():
    years = list(range(2000, 2027))
    results = []

    total_null_count = 0
    total_empty_count = 0
    total_whitespace_count = 0
    total_duplicate_count = 0
    special_format_counts = {'dot': 0, 'dash': 0, 'slash': 0, 'lowercase': 0}

    for year in years:
        filepath = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
        if not os.path.exists(filepath):
            print(f"[WARN] Không tìm thấy file: {filepath}")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 1. Type check
        is_list = isinstance(raw_data, list)
        total_items = len(raw_data) if is_list else 0

        # 2. Null / Empty / Whitespace / Trim checks
        null_cnt = 0
        empty_cnt = 0
        space_cnt = 0
        trimmed_cnt = 0
        
        valid_tickers = []
        
        for item in raw_data:
            if item is None:
                null_cnt += 1
            elif not isinstance(item, str):
                null_cnt += 1
            else:
                s = item.strip()
                if len(s) == 0:
                    empty_cnt += 1
                else:
                    if item != s:
                        space_cnt += 1
                    valid_tickers.append(s)

        # 3. Duplicate check
        unique_tickers = set()
        duplicate_list = []
        for t in valid_tickers:
            if t in unique_tickers:
                duplicate_list.append(t)
            else:
                unique_tickers.add(t)
        
        dup_cnt = len(duplicate_list)

        # 4. Format inspection
        dot_cnt = sum(1 for t in valid_tickers if '.' in t)
        dash_cnt = sum(1 for t in valid_tickers if '-' in t)
        slash_cnt = sum(1 for t in valid_tickers if '/' in t)
        lower_cnt = sum(1 for t in valid_tickers if any(c.islower() for c in t))

        total_null_count += null_cnt
        total_empty_count += empty_cnt
        total_whitespace_count += space_cnt
        total_duplicate_count += dup_cnt
        special_format_counts['dot'] += dot_cnt
        special_format_counts['dash'] += dash_cnt
        special_format_counts['slash'] += slash_cnt
        special_format_counts['lowercase'] += lower_cnt

        results.append({
            'year': year,
            'total_items': total_items,
            'valid_unique': len(unique_tickers),
            'null_cnt': null_cnt,
            'empty_cnt': empty_cnt,
            'space_cnt': space_cnt,
            'duplicates': dup_cnt,
            'dup_samples': ", ".join(duplicate_list[:3]) if duplicate_list else "-",
            'dot_format': dot_cnt,
            'dash_format': dash_cnt
        })

    df_res = pd.DataFrame(results)

    print("================================================================================")
    print("📌 KẾT QUẢ TEST 1: KIỂM THỬ CẤU TRÚC, TRÙNG LẶP & NULL CỦA RUSSELL 1000 UNIVERSE")
    print("================================================================================")
    print(df_res.to_string(index=False))

    print("\n--------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP TOÀN BỘ 27 NĂM (2000 - 2026):")
    print(f" • Tổng số lượt ticker quét: {df_res['total_items'].sum():,} lượt")
    print(f" • Số ticker NULL / Invalid type: {total_null_count}")
    print(f" • Số ticker EMPTY ('')        : {total_empty_count}")
    print(f" • Số ticker dính space thừa   : {total_whitespace_count}")
    print(f" • Số ticker DUPLICATE (Trùng) : {total_duplicate_count}")
    print(f" • Định dạng dính dấu chấm '.' : {special_format_counts['dot']} lượt (Ví dụ: BRK.A)")
    print(f" • Định dạng dính dấu gạch '-' : {special_format_counts['dash']} lượt (Ví dụ: BRK-A)")
    print(f" • Định dạng dính dấu gạch '/' : {special_format_counts['slash']} lượt")
    print(f" • Chữ cái viết thường (lower) : {special_format_counts['lowercase']} lượt")
    print("--------------------------------------------------------------------------------\n")

    return df_res

if __name__ == "__main__":
    run_test1_universe_structure()
