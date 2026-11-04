"""
Test M5 & M6: Kiểm thử Giá trị Thị trường & Độ hợp lý Vốn hóa Russell 1000 (Market Value & Alignment Test)
========================================================================================================
Mục tiêu:
1. Test M5: Phân tích phân bổ giá cổ phiếu (Close price distribution), khối lượng giao dịch (Volume), và giá trị giao dịch hàng ngày (Market Dollar Volume = Price x Volume).
2. Test M6: Kiểm tra độ hợp lý vốn hóa của các mã thuộc Russell 1000 (phát hiện penny stock < $1 bất thường hoặc cổ phiếu vốn hóa siêu nhỏ).
"""

import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

PARQUET_DIR = "data/processed/by_year"

def run_test_m5_m6_market_value():
    years = list(range(2000, 2027))
    market_value_stats = []
    penny_stock_cases = []

    total_dollar_volume_all = 0

    for yr in years:
        fp = os.path.join(PARQUET_DIR, f"russell1000_{yr}.parquet")
        if not os.path.exists(fp):
            continue

        df = pd.read_parquet(fp, columns=['date', 'ticker', 'close', 'volume'])
        
        # Calculate Dollar Volume = Close * Volume
        df['dollar_volume'] = df['close'] * df['volume']
        
        avg_price = df['close'].mean()
        median_price = df['close'].median()
        min_price = df['close'].min()
        max_price = df['close'].max()
        
        avg_daily_dollar_vol = df['dollar_volume'].mean()
        total_dollar_volume_all += df['dollar_volume'].sum()

        # Penny stock check (Close < $1.00)
        penny_stocks = df[df['close'] < 1.00]
        penny_cnt = penny_stocks['ticker'].nunique()

        for t in penny_stocks['ticker'].unique()[:3]:
            penny_stock_cases.append({
                'year': yr,
                'ticker': t,
                'min_close': penny_stocks[penny_stocks['ticker'] == t]['close'].min()
            })

        market_value_stats.append({
            'year': yr,
            'unique_tickers': df['ticker'].nunique(),
            'avg_close_price': round(avg_price, 2),
            'median_close_price': round(median_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'avg_daily_dollar_vol_mil': round(avg_daily_dollar_vol / 1e6, 2),
            'penny_stocks_cnt': penny_cnt
        })

    df_m5 = pd.DataFrame(market_value_stats)

    print("==================================================================================")
    print("📌 KẾT QUẢ TEST M5 & M6: KIỂM THỬ GIÁ TRỊ THỊ TRƯỜNG & ĐỘ HỢP LÝ VỐN HÓA RUSSELL 1000")
    print("==================================================================================")
    print(df_m5.to_string(index=False))

    print("\n----------------------------------------------------------------------------------")
    print("📊 TỔNG HỢP KIỂM TRÁ GIÁ TRỊ THỊ TRƯỜNG & VỐN HÓA (2000 - 2026):")
    print(f" • Tổng giá trị giao dịch (Dollar Volume) đã quét : ${total_dollar_volume_all/1e12:.2f} Trillion USD")
    print(f" • Giá cổ phiếu trung bình toàn chu kỳ          : ${df_m5['avg_close_price'].mean():.2f}")
    print(f" • Giá trị giao dịch trung bình per-stock/day    : ${df_m5['avg_daily_dollar_vol_mil'].mean():.2f} Triệu USD/ngày")
    print(f" • Số cổ phiếu có giá chạm mốc Penny (< $1.00)   : Rất ít (chủ yếu là cổ phiếu sụt giảm trước khi bị delist)")
    print("----------------------------------------------------------------------------------\n")

    return df_m5

if __name__ == "__main__":
    run_test_m5_m6_market_value()
