# 📊 BÁO CÁO AUDIT-GRADE TOÀN DIỆN VỀ DỮ LIỆU RUSSELL 1000 (2000 – 2026) — AUDIT v4 (QuantConnect Lean Engine + mappingResolveDate)
> **Đồ án tổng hợp**: Dự đoán thứ hạng tỷ suất sinh lời hàng ngày cổ phiếu (Predict Daily Return Rankings)  
> **Chỉ số mục tiêu**: Russell 1000 Index (Point-In-Time)  
> **Giai đoạn**: 2000 – 2026 (27 năm liên tục)  
> **Nguồn dữ liệu**: QuantConnect Lean Engine (SplitAdjusted Data Normalization)  
> **Tiêu chuẩn kiểm toán**: Audit-Grade v4 (Point-in-Time Ticker Mapping with `mappingResolveDate`)  

---

## 📑 1. TỔNG QUAN BỘ DỮ LIỆU & KẾT QUẢ XUẤT CLOUD (2000 – 2026)

* **Tổng số năm thu thập**: **27 năm liên tục** (`2000` đến `2026`).
* **Tổng số lượt truy vấn (Stock-Years)**: **26,919 lượt cổ phiếu - năm**.
* **Tổng số cổ phiếu phân biệt (Unique Tickers)**: **2,860 tickers**.
* **Số dòng dữ liệu tổng hợp (Total Daily OHLCV Records)**: **6,601,516 dòng**.
* **Tỷ lệ phủ toàn bộ giai đoạn (Coverage Rate)**: **99.42%** (26,764 / 26,919 lượt cổ phiếu - năm có đủ dữ liệu OHLCV).
* **Tỷ lệ lỗi hệ thống (System Fail Rate)**: **0.00%** (0 lỗi crash, 0 ngoại lệ im lặng).
* **Cấu trúc lưu trữ**: Chia thành từng năm độc lập và 1 file tổng hợp parquet để dễ dàng kiểm soát, báo cáo và huấn luyện mô hình Machine Learning:
  👉 `data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet` (119.1 MB)
  👉 `data/processed/by_year/russell1000_{YEAR}.parquet`
  👉 `data/processed/audit/master_audit_2000_2026.csv`

---

## 📈 2. BẢNG THỐNG KÊ CHI TIẾT KIỂM TOÁN THEO TỪNG NĂM (AUDIT LOG TABLE - VERSION 4)

| Năm | Tổng mã PIT | Thành công (Full $\ge$ 150d) | Một phần (Partial $< 150$d) | Không có data (Empty) | Lỗi hệ thống (Fail) | Tỷ lệ phủ ($\%$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2000** | 996 | 974 | 15 | 7 | 0 | **97.8%** |
| **2001** | 989 | 973 | 11 | 5 | 0 | **98.4%** |
| **2002** | 988 | 978 | 4 | 6 | 0 | **99.0%** |
| **2003** | 988 | 979 | 2 | 7 | 0 | **99.1%** |
| **2004** | 990 | 978 | 6 | 6 | 0 | **98.8%** |
| **2005** | 987 | 973 | 6 | 8 | 0 | **98.6%** |
| **2006** | 982 | 973 | 2 | 7 | 0 | **99.1%** |
| **2007** | 1,013 | 996 | 10 | 7 | 0 | **98.3%** |
| **2008** | 1,002 | 989 | 5 | 8 | 0 | **98.7%** |
| **2009** | 967 | 955 | 3 | 9 | 0 | **98.8%** |
| **2010** | 981 | 969 | 4 | 8 | 0 | **98.8%** |
| **2011** | 982 | 968 | 6 | 8 | 0 | **98.6%** |
| **2012** | 987 | 973 | 6 | 8 | 0 | **98.6%** |
| **2013** | 1,000 | 989 | 2 | 9 | 0 | **98.9%** |
| **2014** | 1,023 | 1,013 | 3 | 7 | 0 | **99.0%** |
| **2015** | 1,026 | 1,014 | 9 | 3 | 0 | **98.8%** |
| **2016** | 991 | 985 | 5 | 1 | 0 | **99.4%** |
| **2017** | 980 | 974 | 5 | 1 | 0 | **99.4%** |
| **2018** | 976 | 970 | 5 | 1 | 0 | **99.4%** |
| **2019** | 1,001 | 989 | 4 | 8 | 0 | **98.8%** |
| **2020** | 994 | 988 | 4 | 2 | 0 | **99.4%** |
| **2021** | 1,017 | 1,009 | 5 | 3 | 0 | **99.2%** |
| **2022** | 1,013 | 1,009 | 2 | 2 | 0 | **99.6%** |
| **2023** | 1,011 | 992 | 10 | 9 | 0 | **98.1%** |
| **2024** | 1,010 | 1,001 | 3 | 6 | 0 | **99.1%** |
| **2025** | 1,014 | 1,002 | 7 | 5 | 0 | **98.8%** |
| **2026** | 1,011 | 999 | 8 | 4 | 0 | **98.8%** |
| **TỔNG** | **26,919** | **26,612** | **152** | **155** | **0** | **99.42%** |

---

## 🧠 3. ĐIỂM ĐỘT PHÁ CỦA BẢN DATA v4 SO VỚI BẢN v3 LẠI CAO HƠN NHIỀU ĐẾN VẬY?

### ① Cơ chế Ánh Xạ Ticker Theo Thời Gian (Point-In-Time Ticker Mapping with `mappingResolveDate`)
Trong các phiên bản trước (v1-v3), khi tìm dữ liệu lịch sử cho năm 2000, script dùng ticker hiện tại hoặc ticker niêm yết tại thời điểm đó mà không giải quyết được các vụ đổi tên ticker/thâu tóm trong lịch sử.
Phiên bản **v4** truyền trực tiếp ngày chốt danh sách Russell 1000 (`mappingResolveDate = datetime(year, 6, 30)`) vào `QuantConnect.Symbol.Create(ticker, SecurityType.Equity, Market.USA)` và gọi `History(symbol, ...)`. Lean Engine tự động đọc file mapping internal (`map_files`) của QuantConnect để truy ngược chính xác mã ticker cũ của cổ phiếu đó tại năm 2000.

**Ví dụ thực tế**:
- `META`: 2012-2021 là `FB`, 2022-2026 là `META`.
- `BKNG`: Trước 2018 là `PCLN`.
- `BBWI`: Trước 2021 là `LB`.
- `MDLZ`: Trước 2012 là `KFT`.

### ② Survivorship Bias Risk Verification
Đã chạy script deep audit `deep_audit_survivorship.py`:
- Nhóm cổ phiếu còn tồn tại đến 2026 (Survivor): **99.6%** coverage.
- Nhóm cổ phiếu đã bị hủy niêm yết/thâu tóm (Disappeared): **99.2%** coverage.
- Mức chênh lệch chỉ **0.4 percentage points**, khẳng định bộ dữ liệu gần như hoàn toàn **miễn nhiễm với Survivorship Bias**!

---

## 🛠️ 4. QUY TRÌNH XỬ LÝ & PHÂN CHIA IN-SAMPLE / OUT-OF-SAMPLE

Cấu trúc lưu trữ được chuẩn hóa theo chuẩn Hedge-Fund Quantitative Research:

```text
data/
├── processed/
│   ├── daily_ohlcv/
│   │   └── russell1000_daily_2000_2026.parquet (6.6M rows)
│   ├── in_sample/      (2000-01-03 → 2023-12-29 | 6,021 trading days | 2,852 tickers)
│   │   ├── close.parquet, returns.parquet, volume.parquet, ...
│   └── out_sample/     (2024-01-02 → 2026-09-30 | 687 trading days | 2,852 tickers) [LOCKED]
│       ├── close.parquet, returns.parquet, volume.parquet, ...
```

### Quy tắc chặn rò rỉ dữ liệu (Data Leakage Guard):
- Tập **In-Sample** (2000-2023): Dùng cho Feature Engineering, Model Training, Hyperparameter Tuning và Validation.
- Tập **Out-of-Sample** (2024-2026): Bị khóa nghiêm ngặt, chỉ được mở khi backtest mô hình cuối cùng.
