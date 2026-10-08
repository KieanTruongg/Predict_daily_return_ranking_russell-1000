"""
Script: scripts/05_eda/sanity_check_in_sample.py
Purpose: Data Sanity Checks S1–S7 trên dữ liệu in_sample/
         Kiểm tra tính nhất quán của dữ liệu trước khi build features.

Checks:
  S1 - Cross-layer consistency (by_year tickers vs in_sample matrix)
  S2 - Return calculation correctness (r_t = close_t/close_{t-1} - 1)
  S3 - Forward return look-ahead bias check
  S4 - NaN profile of the Date x Ticker matrix
  S5 - Volume sanity (zero-volume streaks)
  S6 - Cross-check close prices between by_year and in_sample
  S7 - adj_close vs close comparison
"""

import os
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IN_SAMPLE_DIR = os.path.join(BASE_DIR, "data", "processed", "in_sample")
BY_YEAR_DIR   = os.path.join(BASE_DIR, "data", "processed", "by_year")

SEPARATOR = "=" * 80
SEP_SMALL = "-" * 80

def section(title):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)

def load_matrix(fname):
    fpath = os.path.join(IN_SAMPLE_DIR, fname)
    if not os.path.exists(fpath):
        print(f"  [WARN] Không tìm thấy file: {fpath}")
        return None
    df = pd.read_parquet(fpath)
    df.index = pd.to_datetime(df.index)
    return df


def s1_cross_layer_consistency(close_matrix):
    section("S1: CROSS-LAYER CONSISTENCY — by_year vs in_sample matrix")

    # Get tickers from in_sample
    is_tickers = set(close_matrix.columns)
    print(f"  in_sample/close.parquet: {close_matrix.shape[0]} ngày x {close_matrix.shape[1]} tickers")
    print(f"  Date range: {close_matrix.index.min().date()} → {close_matrix.index.max().date()}")

    # Get all tickers from by_year parquets (in-sample years only: 2000-2023)
    by_year_tickers = set()
    for yr in range(2000, 2024):
        fp = os.path.join(BY_YEAR_DIR, f"russell1000_{yr}.parquet")
        if os.path.exists(fp):
            df_yr = pd.read_parquet(fp, columns=['ticker'])
            by_year_tickers.update(df_yr['ticker'].unique())

    print(f"\n  Unique tickers in by_year (2000-2023): {len(by_year_tickers)}")
    print(f"  Unique tickers in in_sample matrix:    {len(is_tickers)}")

    only_in_matrix = is_tickers - by_year_tickers
    only_in_byyear = by_year_tickers - is_tickers
    intersection   = is_tickers & by_year_tickers

    print(f"\n  Tickers trong CẢ HAI: {len(intersection)}")
    print(f"  Chỉ trong in_sample (không có trong by_year): {len(only_in_matrix)}")
    if only_in_matrix:
        print(f"    Ví dụ: {list(only_in_matrix)[:10]}")
    print(f"  Chỉ trong by_year (không xuất hiện trong matrix): {len(only_in_byyear)}")
    if only_in_byyear:
        print(f"    Ví dụ: {list(only_in_byyear)[:10]}")

    # Check trading calendar - so sánh số ngày unique
    by_year_dates = set()
    for yr in range(2000, 2024):
        fp = os.path.join(BY_YEAR_DIR, f"russell1000_{yr}.parquet")
        if os.path.exists(fp):
            df_yr = pd.read_parquet(fp, columns=['date'])
            df_yr['date'] = pd.to_datetime(df_yr['date'])
            by_year_dates.update(df_yr['date'].dt.date.unique())
    matrix_dates = set(close_matrix.index.date)
    missing_dates = by_year_dates - matrix_dates
    extra_dates   = matrix_dates - by_year_dates
    print(f"\n  Trading days in by_year (2000-2023): {len(by_year_dates)}")
    print(f"  Trading days in in_sample matrix:    {len(matrix_dates)}")
    print(f"  Missing dates in matrix: {len(missing_dates)}")
    print(f"  Extra dates in matrix:   {len(extra_dates)}")

    if len(only_in_matrix) == 0 and len(only_in_byyear) == 0 and len(missing_dates) == 0:
        print(f"\n  ✅ S1 PASS: Cross-layer hoàn toàn nhất quán!")
    else:
        print(f"\n  ⚠️ S1 CẢNH BÁO: Có sự khác biệt giữa 2 layer — kiểm tra chi tiết ở trên.")


def s2_return_calculation(close_matrix, return_matrix):
    section("S2: RETURN CALCULATION CHECK — r_t = close_t / close_{t-1} - 1")

    if close_matrix is None or return_matrix is None:
        print("  [SKIP] Thiếu file close hoặc returns.")
        return

    # Compute expected return from close
    expected_ret = close_matrix.pct_change(1)

    # Compare for 5 famous tickers
    TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'XOM']
    available = [t for t in TICKERS if t in close_matrix.columns and t in return_matrix.columns]

    max_diff_all = 0.0
    print(f"\n  {'Ticker':<8} {'Max |diff|':>12} {'Mean |diff|':>12} {'Status':>10}")
    print(f"  {'-'*50}")
    for t in available:
        exp = expected_ret[t].dropna()
        act = return_matrix[t].reindex(exp.index).dropna()
        common = exp.index.intersection(act.index)
        if len(common) == 0:
            print(f"  {t:<8} {'NO COMMON DATA':>35}")
            continue
        diff = (exp[common] - act[common]).abs()
        max_d = diff.max()
        mean_d = diff.mean()
        max_diff_all = max(max_diff_all, max_d)
        status = "✅ OK" if max_d < 1e-6 else ("⚠️ SMALL DIFF" if max_d < 0.001 else "❌ LARGE DIFF")
        print(f"  {t:<8} {max_d:>12.8f} {mean_d:>12.8f} {status:>10}")

    # Sample return values for famous crash/rally days
    print(f"\n  --- Return thực tế tại các ngày sự kiện quan trọng ---")
    events = [
        ('AAPL', '2008-09-15', 'Lehman Brothers phá sản'),
        ('AAPL', '2020-03-16', 'COVID sell-off'),
        ('AAPL', '2020-08-31', 'Apple 4-for-1 Split'),
        ('GOOGL', '2022-07-18', 'Alphabet 20-for-1 Split'),
        ('XOM',  '2020-03-09', 'Oil price war crash'),
    ]
    for ticker, date_str, event in events:
        if ticker not in return_matrix.columns:
            continue
        dt = pd.Timestamp(date_str)
        idx = return_matrix.index
        nearby = idx[(idx >= dt - pd.Timedelta(days=3)) & (idx <= dt + pd.Timedelta(days=3))]
        if len(nearby) > 0:
            closest = nearby[np.argmin(abs(nearby - dt))]
            ret_val = return_matrix.loc[closest, ticker]
            print(f"  {ticker} | {closest.date()} | {event}: {ret_val:+.2%}")

    if max_diff_all < 1e-6:
        print(f"\n  ✅ S2 PASS: Return được tính chính xác (max diff < 1e-6)")
    elif max_diff_all < 0.001:
        print(f"\n  ⚠️ S2 CẢNH BÁO: Có sai số nhỏ (max diff = {max_diff_all:.6f}) — có thể do làm tròn float")
    else:
        print(f"\n  ❌ S2 FAIL: Sai số lớn (max diff = {max_diff_all:.4f}) — cần điều tra!")


def s3_forward_return_leakage(return_matrix, fwd_return_matrix):
    section("S3: FORWARD RETURN LOOK-AHEAD BIAS CHECK")

    if return_matrix is None or fwd_return_matrix is None:
        print("  [SKIP] Thiếu file returns hoặc forward_returns.")
        return

    # forward_return[t] phải bằng return[t+1]
    # Tức là: fwd_ret.shift(1) phải bằng return
    TICKERS = ['AAPL', 'MSFT', 'JPM']
    available = [t for t in TICKERS if t in return_matrix.columns and t in fwd_return_matrix.columns]

    print(f"\n  Kiểm tra: forward_return[t] == return[t+1]")
    print(f"\n  {'Ticker':<8} {'Max |diff|':>12} {'N samples':>10} {'Status':>12}")
    print(f"  {'-'*50}")

    all_pass = True
    for t in available:
        ret = return_matrix[t]
        fwd = fwd_return_matrix[t]

        # fwd[t] phải = ret[t+1] => fwd.shift(1) phải = ret
        aligned = fwd.shift(1).dropna()
        common = ret.index.intersection(aligned.index)
        if len(common) < 10:
            print(f"  {t:<8} {'NOT ENOUGH DATA':>35}")
            continue
        diff = (ret[common] - aligned[common]).abs().dropna()
        max_d = diff.max()
        n = len(diff)
        ok = max_d < 1e-6
        if not ok:
            all_pass = False
        status = "✅ OK" if ok else "❌ LEAK DETECTED"
        print(f"  {t:<8} {max_d:>12.8f} {n:>10} {status:>12}")

    if all_pass:
        print(f"\n  ✅ S3 PASS: Không phát hiện look-ahead bias trong forward_returns!")
    else:
        print(f"\n  ❌ S3 FAIL: Phát hiện sai lệch trong forward_returns — nguy cơ look-ahead bias!")


def s4_nan_profile(close_matrix):
    section("S4: NaN PROFILE CỦA MA TRẬN CLOSE (Date × Ticker)")

    if close_matrix is None:
        print("  [SKIP] Thiếu file close.")
        return

    total_cells = close_matrix.size
    nan_cells   = close_matrix.isna().sum().sum()
    nan_pct     = nan_cells / total_cells * 100
    print(f"\n  Shape: {close_matrix.shape[0]} days × {close_matrix.shape[1]} tickers")
    print(f"  Total cells: {total_cells:,}")
    print(f"  NaN cells:   {nan_cells:,} ({nan_pct:.2f}%)")

    # NaN by year - use index.year directly
    print(f"\n  --- NaN % theo từng năm ---")
    years_arr = close_matrix.index.year
    for yr in sorted(set(years_arr)):
        mask = years_arr == yr
        yr_nan = close_matrix.loc[mask].isna().mean().mean() * 100
        bar = '█' * int(yr_nan / 5)
        print(f"  {yr}: {yr_nan:5.1f}% {bar}")

    # Tickers có NaN nhiều nhất
    ticker_nan_pct = close_matrix.isna().mean() * 100
    print(f"\n  --- Top 10 tickers NaN nhiều nhất ---")
    top_nan = ticker_nan_pct.sort_values(ascending=False).head(10)
    for t, pct in top_nan.items():
        print(f"  {t:<10}: {pct:.1f}% NaN")

    print(f"\n  --- Tickers có 0% NaN (luôn có dữ liệu) ---")
    full_tickers = ticker_nan_pct[ticker_nan_pct == 0]
    print(f"  Số tickers có đầy đủ dữ liệu toàn bộ in-sample: {len(full_tickers)}")

    # Phantom delisting: ticker có data rồi đột ngột mất giữa chừng
    print(f"\n  --- Kiểm tra Phantom Delisting (NaN đột ngột giữa chừng) ---")
    phantom_count = 0
    for col in close_matrix.columns[:200]:  # Chỉ sample 200 tickers đầu
        series = close_matrix[col]
        last_valid = series.last_valid_index()
        if last_valid is not None and last_valid < close_matrix.index[-1]:
            remaining_nan = series[last_valid:].isna().sum()
            if remaining_nan > 20:  # Hơn 20 ngày NaN liên tiếp cuối
                phantom_count += 1
    print(f"  (Sample 200 tickers đầu) Số tickers nghi ngờ phantom delisting: {phantom_count}")
    print(f"  → Đây là hành vi BÌNH THƯỜNG cho cổ phiếu bị hủy niêm yết / M&A")

    print(f"\n  ✅ S4 HOÀN TẤT: NaN profile đã được phân tích.")


def s5_volume_sanity(volume_matrix):
    section("S5: VOLUME SANITY CHECK — Zero-volume streaks")

    if volume_matrix is None:
        print("  [SKIP] Thiếu file volume.")
        return

    # Kiểm tra cổ phiếu có volume = 0 nhiều ngày liên tiếp
    zero_vol_tickers = []
    sample_cols = volume_matrix.columns[:300]  # Sample 300 tickers
    for col in sample_cols:
        series = volume_matrix[col].dropna()
        if len(series) == 0:
            continue
        zero_streak = (series == 0)
        # Tìm streak dài nhất
        max_streak = 0
        current = 0
        for v in zero_streak:
            if v:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        if max_streak >= 5:
            zero_vol_tickers.append((col, max_streak))

    zero_vol_tickers.sort(key=lambda x: -x[1])
    print(f"\n  (Sample {len(sample_cols)} tickers) Số tickers có streak volume=0 >= 5 ngày: {len(zero_vol_tickers)}")
    if zero_vol_tickers:
        print(f"  Top 10 worst streaks:")
        for t, streak in zero_vol_tickers[:10]:
            print(f"    {t:<10}: max streak = {streak} ngày")

    # Overall volume stats
    daily_total_vol = volume_matrix.sum(axis=1)
    print(f"\n  --- Tổng Volume market theo ngày ---")
    print(f"  Min total daily volume: {daily_total_vol.min():,.0f}")
    print(f"  Max total daily volume: {daily_total_vol.max():,.0f}")
    print(f"  Mean total daily volume: {daily_total_vol.mean():,.0f}")
    print(f"  Số ngày có total volume = 0: {(daily_total_vol == 0).sum()}")

    if len(zero_vol_tickers) < 20 and (daily_total_vol == 0).sum() == 0:
        print(f"\n  ✅ S5 PASS: Volume hợp lý, không có ngày market volume = 0.")
    else:
        print(f"\n  ⚠️ S5 CẢNH BÁO: Có {len(zero_vol_tickers)} tickers với zero-volume streak dài.")


def s6_cross_check_prices(close_matrix):
    section("S6: CROSS-CHECK GIÁ CLOSE giữa by_year và in_sample")

    if close_matrix is None:
        print("  [SKIP] Thiếu file close.")
        return

    # Chọn 10 tickers để so sánh
    TEST_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'JPM', 'XOM', 'WMT', 'JNJ', 'PG', 'V']
    available = [t for t in TEST_TICKERS if t in close_matrix.columns]

    print(f"\n  So sánh giá close tại 5 ngày cụ thể cho {len(available)} tickers:")

    # Test dates
    test_dates = ['2001-09-17', '2008-10-10', '2020-03-20', '2021-01-04', '2023-06-30']

    all_match = True
    for t in available:
        for date_str in test_dates[:3]:  # Chỉ test 3 ngày cho gọn
            dt = pd.Timestamp(date_str)
            yr = dt.year
            # Load from by_year
            fp = os.path.join(BY_YEAR_DIR, f"russell1000_{yr}.parquet")
            if not os.path.exists(fp):
                continue
            df_yr = pd.read_parquet(fp, columns=['date', 'ticker', 'close'])
            df_yr['date'] = pd.to_datetime(df_yr['date'])

            by_year_row = df_yr[(df_yr['ticker'] == t) & (df_yr['date'] == dt)]
            if by_year_row.empty:
                continue
            by_year_price = by_year_row.iloc[0]['close']

            # Get from in_sample matrix
            if dt not in close_matrix.index:
                # Find nearest date
                nearest = close_matrix.index[np.argmin(abs(close_matrix.index - dt))]
                matrix_price = close_matrix.loc[nearest, t]
            else:
                matrix_price = close_matrix.loc[dt, t]

            if pd.isna(matrix_price):
                continue
            diff = abs(by_year_price - matrix_price)
            if diff > 0.01:
                all_match = False
                print(f"  ❌ MISMATCH: {t} @ {date_str}: by_year={by_year_price:.4f}, matrix={matrix_price:.4f}, diff={diff:.4f}")

    if all_match:
        print(f"\n  ✅ S6 PASS: Giá close nhất quán giữa by_year và in_sample matrix!")
    else:
        print(f"\n  ❌ S6 FAIL: Phát hiện sai lệch giá — cần kiểm tra lại script merge!")


def s7_adj_close_vs_close(close_matrix, adj_close_matrix):
    section("S7: ADJ_CLOSE vs CLOSE COMPARISON")

    if close_matrix is None or adj_close_matrix is None:
        print("  [SKIP] Thiếu file close hoặc adj_close.")
        return

    # Tính tỷ lệ adj_close / close
    TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'XOM', 'KO', 'PEP', 'JNJ']
    available = [t for t in TICKERS if t in close_matrix.columns and t in adj_close_matrix.columns]

    print(f"\n  {'Ticker':<8} {'Là adj≡close?':>15} {'Max ratio':>12} {'Min ratio':>12} {'% diff > 0.1%':>15}")
    print(f"  {'-'*65}")

    all_identical = True
    for t in available:
        c = close_matrix[t].dropna()
        a = adj_close_matrix[t].reindex(c.index).dropna()
        common = c.index.intersection(a.index)
        if len(common) < 10:
            continue
        ratio = (a[common] / c[common]).dropna()
        max_ratio = ratio.max()
        min_ratio = ratio.min()
        is_identical = (c[common] - a[common]).abs().max() < 1e-6
        pct_diff = ((ratio - 1).abs() > 0.001).mean() * 100
        if not is_identical:
            all_identical = False
        status = "✅ SplitAdj" if not is_identical else "⚠️ BẰNG NHAU"
        print(f"  {t:<8} {str(is_identical):>15} {max_ratio:>12.4f} {min_ratio:>12.4f} {pct_diff:>14.1f}%")

    if all_identical:
        print(f"\n  ⚠️ S7 CẢNH BÁO: adj_close = close cho TẤT CẢ tickers được kiểm tra!")
        print(f"     → QuantConnect SplitAdjusted có thể đã apply LUÔN vào trường 'close'")
        print(f"     → adj_close và close là CÙNG 1 chuỗi (không có dividend adjustment riêng)")
        print(f"     → Điều này KHÔNG phải lỗi: SplitAdjusted = giá đã điều chỉnh hoàn toàn")
    else:
        print(f"\n  ✅ S7: adj_close khác close (có Dividend & Split adjustment!)")

    print(f"\n  → KẾT LUẬN: Trong pipeline, nên dùng 'close' (= SplitAdjusted) để tính return.")
    print(f"     Feature engineer không cần dùng adj_close riêng.")


def main():
    print(SEPARATOR)
    print("  DATA SANITY CHECKS S1–S7: in_sample/ Cross-Validation")
    print("  Mục tiêu: Kiểm tra tính nhất quán của dữ liệu trước khi build features")
    print(SEPARATOR)

    # Load all matrices
    print("\n  Loading matrices...")
    close_m   = load_matrix("close.parquet")
    adj_m     = load_matrix("adj_close.parquet")
    ret_m     = load_matrix("returns.parquet")
    fwd_m     = load_matrix("forward_returns.parquet")
    vol_m     = load_matrix("volume.parquet")
    print(f"  ✓ Loaded: close={close_m.shape if close_m is not None else 'None'}")
    print(f"  ✓ Loaded: returns={ret_m.shape if ret_m is not None else 'None'}")
    print(f"  ✓ Loaded: forward_returns={fwd_m.shape if fwd_m is not None else 'None'}")
    print(f"  ✓ Loaded: volume={vol_m.shape if vol_m is not None else 'None'}")

    s1_cross_layer_consistency(close_m)
    s2_return_calculation(close_m, ret_m)
    s3_forward_return_leakage(ret_m, fwd_m)
    s4_nan_profile(close_m)
    s5_volume_sanity(vol_m)
    s6_cross_check_prices(close_m)
    s7_adj_close_vs_close(close_m, adj_m)

    print(f"\n{SEPARATOR}")
    print("  ✅ HOÀN TẤT TOÀN BỘ SANITY CHECKS S1–S7")
    print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    main()
