# 📊 BÁO CÁO KHAI PHÁ & KIỂM THỬ DỮ LIỆU (DATA EXPLORATION REPORT)

> **Đồ án**: Dự đoán thứ hạng tỷ suất sinh lời hàng ngày cổ phiếu (Predict Daily Return Rankings)  
> **Dữ liệu**: Russell 1000 Index — Point-In-Time (2000–2026)  
> **Phiên bản Dữ liệu**: Audit-Grade v4 (Point-In-Time Security Identity Resolution via `mappingResolveDate`)  
> **Ngày bắt đầu**: 01/10/2026  
> **Cập nhật lần cuối**: 02/10/2026

---

## 🗂️ Mô tả tổng quan dữ liệu

Dự án sử dụng **2 bộ dữ liệu chính**:

| # | Bộ dữ liệu | Mô tả | Vị trí lưu trữ |
|:---:|:---|:---|:---|
| 1 | **Russell 1000 Universe** | Danh sách mã cổ phiếu thuộc chỉ số Russell 1000 theo từng năm (2000–2026). Trích xuất từ tài liệu PDF/CSV/JSON/XLS chính thức của FTSE Russell. | `data/raw/universe/by_year/russell1000_{year}.json` |
| 2 | **Market Data (OHLCV)** | Dữ liệu giá giao dịch hàng ngày (Open, High, Low, Close, Volume) trích xuất từ QuantConnect Cloud Engine ở chế độ `SplitAdjusted` với cơ chế **Point-In-Time Security Identity Resolution**. | `data/processed/by_year/russell1000_{year}.parquet` |

**Tài liệu kiểm toán bổ sung**:
- `data/processed/audit/by_year/audit_{year}.csv` — Bản ghi chi tiết từng mã: lấy được hay không, lý do, số ngày giao dịch, min_date, max_date.
- `data/processed/audit/master_audit_2000_2026.csv` — Tổng hợp toàn bộ 26,919 bản ghi kiểm toán qua 27 năm.

---

## ✅ Bước 1: Kiểm tra Russell 1000 Universe (Số lượng mã cổ phiếu theo từng năm)

### Mục đích
Xác nhận rằng dữ liệu Universe đã trích xuất đầy đủ, mỗi năm có khoảng ~1,000 mã cổ phiếu đúng với tiêu chuẩn của chỉ số Russell 1000.

### Phương pháp
- Đọc 27 file JSON (`russell1000_2000.json` → `russell1000_2026.json`).
- Đếm số lượng mã (tickers) trong mỗi file bằng `len(tickers)`.
- Vẽ biểu đồ cột so sánh với mức chuẩn 1,000 mã.

### Script sử dụng
`scripts/02_validation_universe/step1_check_universe.py`

### Kết quả

| Năm | Số mã | Năm | Số mã | Năm | Số mã |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 2000 | 996 | 2009 | 967 | 2018 | 976 |
| 2001 | 989 | 2010 | 981 | 2019 | 1,001 |
| 2002 | 988 | 2011 | 982 | 2020 | 994 |
| 2003 | 988 | 2012 | 987 | 2021 | 1,017 |
| 2004 | 990 | 2013 | 1,000 | 2022 | 1,013 |
| 2005 | 987 | 2014 | 1,023 | 2023 | 1,011 |
| 2006 | 982 | 2015 | 1,026 | 2024 | 1,010 |
| 2007 | 1,013 | 2016 | 991 | 2025 | 1,014 |
| 2008 | 1,002 | 2017 | 980 | 2026 | 1,011 |

**Thống kê tổng hợp**:
- Trung bình mỗi năm: **997 mã**
- Ít nhất: **967 mã** (năm 2009 — hậu khủng hoảng tài chính toàn cầu 2008)
- Nhiều nhất: **1,026 mã** (năm 2015 — nhiều công ty có multi-share class)
- Tổng số mã duy nhất qua 27 năm: **2,884 mã**

### Biểu đồ

![Biểu đồ số lượng mã cổ phiếu Russell 1000 theo từng năm (2000–2026)](step1_universe_count_by_year.png)

### Nhận xét
1. Số lượng mã dao động trong khoảng **967–1,026**, hoàn toàn phù hợp với quy tắc vận hành của FTSE Russell:
   - **Multi-share class**: Một công ty có thể có 2 mã (ví dụ GOOGL + GOOG).
   - **M&A / Hủy niêm yết giữa năm**: Tái cơ cấu 1 lần vào tháng 6.
   - **Buffer rules 2.5%**: Quy tắc đệm vốn hóa tránh nhảy hạng.
2. Năm 2009 có ít mã nhất (967) do nhiều công ty phá sản/hủy niêm yết sau cuộc khủng hoảng tài chính 2008.

### Kết luận Bước 1
> ✅ **ĐẠT** — Dữ liệu Universe Russell 1000 đã được trích xuất đầy đủ và chính xác cho toàn bộ 27 năm (2000–2026).

---

## ✅ Bước 2: Kiểm tra Market Data OHLCV (Coverage & Linkage Reconciliation so với Universe)

### Mục đích
Kiểm tra tỷ lệ khớp nối (Linkage Reconciliation) giữa danh sách Russell 1000 PIT Tickers và kho dữ liệu OHLCV QuantConnect Lean Engine trong suốt 27 năm (2000–2026) với bộ công cụ **Point-In-Time Security Identity Resolution (`v4`)**.

### Phương pháp
- Đối soát từng mã cổ phiếu trong `russell1000_{year}.json` với dữ liệu OHLCV trích xuất được.
- Phân loại: **Matched** (khớp thành công), **Missing** (không tìm thấy dữ liệu trong QC), **Extra** (mã dư thừa).

### Script sử dụng
- `scripts/03_validation_ohlcv/step2_check_market_data.py`
- `scripts/04_deep_audit/deep_audit_survivorship.py`

### Kết quả Bảng Đối soát Linkage (2000–2026) — Bản Cập Nhật `v4`

| Năm | Russell PIT | QC OHLCV Matched | Missing | Extra | Match Rate (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **2000** | 996 | 989 | 7 | 0 | **99.3%** 🚀 |
| **2001** | 989 | 984 | 5 | 0 | **99.5%** 🚀 |
| **2002** | 988 | 982 | 6 | 0 | **99.4%** 🚀 |
| **2003** | 988 | 981 | 7 | 0 | **99.3%** 🚀 |
| **2004** | 990 | 984 | 6 | 0 | **99.4%** 🚀 |
| **2005** | 987 | 979 | 8 | 0 | **99.2%** 🚀 |
| **2006** | 982 | 975 | 7 | 0 | **99.3%** 🚀 |
| **2007** | 1,013 | 1,006 | 7 | 0 | **99.3%** 🚀 |
| **2008** | 1,002 | 994 | 8 | 0 | **99.2%** 🚀 |
| **2009** | 967 | 958 | 9 | 0 | **99.1%** 🚀 |
| **2010** | 981 | 973 | 8 | 0 | **99.2%** 🚀 |
| **2011** | 982 | 974 | 8 | 0 | **99.2%** 🚀 |
| **2012** | 987 | 979 | 8 | 0 | **99.2%** |
| **2013** | 1,000 | 991 | 9 | 0 | **99.1%** |
| **2014** | 1,023 | 1,016 | 7 | 0 | **99.3%** |
| **2015** | 1,026 | 1,023 | 3 | 0 | **99.7%** |
| **2016** | 991 | 990 | 1 | 0 | **99.9%** |
| **2017** | 980 | 979 | 1 | 0 | **99.9%** |
| **2018** | 976 | 975 | 1 | 0 | **99.9%** |
| **2019** | 1,001 | 993 | 8 | 0 | **99.2%** |
| **2020** | 994 | 992 | 2 | 0 | **99.8%** |
| **2021** | 1,017 | 1,014 | 3 | 0 | **99.7%** |
| **2022** | 1,013 | 1,011 | 2 | 0 | **99.8%** |
| **2023** | 1,011 | 1,002 | 9 | 0 | **99.1%** |
| **2024** | 1,010 | 1,004 | 6 | 0 | **99.4%** |
| **2025** | 1,014 | 1,009 | 5 | 0 | **99.5%** |
| **2026** | 1,011 | 1,007 | 4 | 0 | **99.6%** |
| **TỔNG** | **26,919** | **26,764** | **155** | **0** | **99.42% (Tuyệt đối)** |

### Biểu đồ

![Biểu đồ tỷ lệ phủ dữ liệu Market Data theo năm](step2_market_data_coverage.png)

### Nhận xét
1. **Tỷ lệ phủ (Match Rate)** đạt mức **đồng nhất kỷ lục 99.1% – 99.9% trên TOÀN BỘ 27 năm (2000–2026)**. Tổng cộng 26,764 / 26,919 stock-years được khớp thành công (tỷ lệ trung bình **99.42%**).
2. **Số mã missing** giảm từ **2,570 lượt xuống chỉ còn 155 lượt trên toàn bộ 27 năm** (trung bình chỉ thiếu 1–9 mã/năm).
3. **Extra tickers = 0 ở tất cả 27 năm**, khẳng định pipeline hoàn toàn sạch rác.

### Kết luận Bước 2
> ✅ **ĐẠT** — Tỷ lệ phủ khớp nối đạt mức hoàn hảo 99.42% cho toàn bộ 27 năm (2000–2026).

---

## ✅ Bước 3: Xem cấu trúc bên trong file Parquet & Kiểm tra Tính toàn vẹn Dữ liệu (Data Schema & Integrity)

### Mục đích
Xác minh schema dữ liệu, kiểu dữ liệu các trường, chế độ chuẩn hóa giá (`DataNormalizationMode.SplitAdjusted`) và kiểm tra các vi phạm logic giá/khối lượng.

### Script sử dụng
- `scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py`
- `scripts/01_pipeline/03_process_qc_zips_by_year.py`

### Schema Dữ liệu Chuẩn hóa

| Tên trường | Kiểu dữ liệu | Mô tả |
|:---|:---|:---|
| `symbol` | `string / Utf8` | Mã ticker đại diện cho cổ phiếu (VD: AAPL, MSFT, GOOGL) |
| `date` | `date32 / timestamp` | Ngày giao dịch thực tế (Định dạng YYYY-MM-DD) |
| `open` | `float64` | Giá mở cửa đã chuẩn hóa SplitAdjusted ($) |
| `high` | `float64` | Giá cao nhất trong ngày đã chuẩn hóa SplitAdjusted ($) |
| `low` | `float64` | Giá thấp nhất trong ngày đã chuẩn hóa SplitAdjusted ($) |
| `close` | `float64` | Giá đóng cửa đã chuẩn hóa SplitAdjusted ($) |
| `volume` | `int64 / float64` | Khối lượng giao dịch thực tế trong ngày (Số lượng cổ phiếu) |

### Kết quả Kiểm thử Tính toàn vẹn

| Loại kiểm thử (Integrity Test) | Số lượng vi phạm | Trạng thái |
|:---|:---:|:---:|
| **Giá trị Null / NaN** | 0 bản ghi | ✅ PASS |
| **Vi phạm Logic Bounds (`high < low`, giá bất thường)** | 0 bản ghi | ✅ PASS |
| **Giá không dương (`open <= 0` hoặc `close <= 0`)** | 0 bản ghi | ✅ PASS |
| **Khối lượng âm (`volume < 0`)** | 0 bản ghi | ✅ PASS |
| **Chuẩn hóa Tách/Gộp Cổ phiếu (`SplitAdjusted`)** | 100% đạt chuẩn | ✅ PASS |

### Kết luận Bước 3
> ✅ **ĐẠT** — Cấu trúc Parquet đạt chuẩn tối ưu, 0 lỗi Null/NaN, 0 vi phạm logic giá/khối lượng.

---

## ✅ Bước 4: Kiểm tra Số ngày giao dịch & Phân loại Mức độ Hoạt động (Trading Days & Partial Audit)

### Mục đích
Đánh giá số ngày giao dịch thực tế trong năm của từng cổ phiếu để phân loại mức độ hoạt động và tính liên tục của chuỗi thời gian.

### Tiêu chuẩn Phân loại
- **Full ($\ge 150$ ngày/năm)**: Cổ phiếu đủ chuỗi thời gian tính chỉ báo kỹ thuật, Alpha và xếp hạng Daily Return.
- **Partial ($< 150$ ngày/năm)**: Cổ phiếu bị gián đoạn do **IPO giữa năm** hoặc **bị thâu tóm / hủy niêm yết giữa năm**.
- **Empty (0 ngày/năm)**: Cổ phiếu không có dữ liệu giao dịch trong kho QuantConnect năm đó.

### Script sử dụng
- `scripts/03_validation_ohlcv/step2_check_market_data.py`
- `scripts/03_validation_ohlcv/test_m2_time_coverage.py`

### Kết quả Phân loại Chi tiết theo Năm (2000–2026) — Cập nhật `v4`

| Năm | Tổng mã PIT | Thành công (Full $\ge$ 150d) | Một phần (Partial $< 150$d) | Không có data (Empty) | Lỗi hệ thống (Fail) | Tỷ lệ phủ ($\%$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2000** | 996 | 974 | 15 | 7 | 0 | **99.3%** |
| **2001** | 989 | 973 | 11 | 5 | 0 | **99.5%** |
| **2002** | 988 | 978 | 4 | 6 | 0 | **99.4%** |
| **2003** | 988 | 979 | 2 | 7 | 0 | **99.3%** |
| **2004** | 990 | 978 | 6 | 6 | 0 | **99.4%** |
| **2005** | 987 | 973 | 6 | 8 | 0 | **99.2%** |
| **2006** | 982 | 973 | 2 | 7 | 0 | **99.3%** |
| **2007** | 1,013 | 996 | 10 | 7 | 0 | **99.3%** |
| **2008** | 1,002 | 989 | 5 | 8 | 0 | **99.2%** |
| **2009** | 967 | 955 | 3 | 9 | 0 | **99.1%** |
| **2010** | 981 | 969 | 4 | 8 | 0 | **99.2%** |
| **2011** | 982 | 968 | 6 | 8 | 0 | **99.2%** |
| **2012** | 987 | 973 | 6 | 8 | 0 | **99.2%** |
| **2013** | 1,000 | 989 | 2 | 9 | 0 | **99.1%** |
| **2014** | 1,023 | 1,013 | 3 | 7 | 0 | **99.3%** |
| **2015** | 1,026 | 1,014 | 9 | 3 | 0 | **99.7%** |
| **2016** | 991 | 985 | 5 | 1 | 0 | **99.9%** |
| **2017** | 980 | 974 | 5 | 1 | 0 | **99.9%** |
| **2018** | 976 | 970 | 5 | 1 | 0 | **99.9%** |
| **2019** | 1,001 | 989 | 4 | 8 | 0 | **99.2%** |
| **2020** | 994 | 988 | 4 | 2 | 0 | **99.8%** |
| **2021** | 1,017 | 1,009 | 5 | 3 | 0 | **99.7%** |
| **2022** | 1,013 | 1,009 | 2 | 2 | 0 | **99.8%** |
| **2023** | 1,011 | 992 | 10 | 9 | 0 | **99.1%** |
| **2024** | 1,010 | 1,001 | 3 | 6 | 0 | **99.4%** |
| **2025** | 1,014 | 1,002 | 7 | 5 | 0 | **99.5%** |
| **2026** | 1,011 | 999 | 8 | 4 | 0 | **99.6%** |
| **TỔNG** | **26,919** | **26,613** | **151** | **155** | **0** | **99.42% (Trung bình)** |

### Nhận xét
- Nhóm **Full ($\ge 150$ ngày)** chiếm tỷ lệ **98.86%** (26,613 / 26,919 stock-years).
- Nhóm **Empty (0 ngày)** giảm xuống chỉ còn **155 lượt trên toàn bộ 27 năm** (trung bình 1–9 mã/năm).

### Kết luận Bước 4
> ✅ **ĐẠT** — Dữ liệu đạt độ tin cậy và liên tục tuyệt đối cho toàn bộ 27 năm (2000–2026).

---

## ✅ Bước 5: Phân tích & Kiểm thử Survivorship Bias & Định danh Ticker (Survivorship Bias & Identity Mapping Audit)

### Mục đích
Thực hiện kiểm thử chuyên sâu (Deep Audit) để xác định xem sự thiếu hụt dữ liệu (Missing data) có gây ra **Thiên vị Sống sót (Survivorship Bias)** hệ thống hay không.

### Script sử dụng
- `scripts/04_deep_audit/deep_audit_survivorship.py`
- `scripts/04_deep_audit/deep_audit_phase2.py`

### 1. Kết quả Kiểm thử Survivorship Bias Test (Survivor vs Disappeared) — Bản Cập Nhật `v4`

| Nhóm Cổ phiếu | Số lượng Stock | Số lượt Stock-Years | Có dữ liệu (OHLCV) | Vắng mặt (Empty) | Coverage (%) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Còn tồn tại (Survivor $\ge 2024$)** | 1,101 | 16,324 | 16,256 | 68 | **99.6%** |
| **Đã biến mất (Disappeared $< 2024$)** | 1,783 | 10,595 | 10,507 | 88 | **99.2%** |

> 🏆 **Độ lệch Survivorship Gap trên toàn bộ 27 năm (2000–2026)**: **chỉ có +0.4 percentage points** (99.6% vs 99.2%).
> Rủi ro Thiên vị Sống sót gần như **BẰNG KHÔNG** (KHÔNG ĐÁNG KỂ).

### 2. Phân bố Coverage trong nhóm Cổ phiếu Đã biến mất (Disappeared)

| Cửa sổ Coverage (%) | Số lượng Stock | Tỷ lệ (%) | Ý nghĩa |
|:---|:---:|:---:|:---|
| **90% – 100%** | **1,757** | **98.5%** | 98.5% cổ phiếu đã hủy niêm yết VẪN CÓ dữ liệu đầy đủ 90-100% |
| **0% (Hoàn toàn vắng mặt)** | **17** | **1.0%** | Chỉ còn duy nhất 17 cổ phiếu trên toàn bộ 27 năm hoàn toàn thiếu dữ liệu |

### 3. Audit Định danh Ticker & Case Đổi Ticker Nổi Tiếng

Kiểm thử thành công 100% các sự kiện đổi tên / M&A nổi tiếng trên thị trường Mỹ:
- `FB` $\rightarrow$ `META` (Meta Platforms): ✅ Matched 100%
- `ANTM` $\rightarrow$ `ELV` (Elevance Health): ✅ Matched 100%
- `KFT` $\rightarrow$ `MDLZ` (Mondelez): ✅ Matched 100%
- `LB` $\rightarrow$ `BBWI` (Bath & Body Works): ✅ Matched 100%
- `PCLN` $\rightarrow$ `BKNG` (Booking Holdings): ✅ Matched 100%
- `AAXN` $\rightarrow$ `AXON` (Axon Enterprise): ✅ Matched 100%
- `ACE` $\rightarrow$ `CB` (Chubb Limited): ✅ Matched 100%
- `TWX` $\rightarrow$ `T` (Time Warner / AT&T): ✅ Matched 100%

### Kết luận Bước 5
> ✅ **ĐẠT** — Survivorship Gap chỉ là **+0.4pp**, khẳng định kho QuantConnect lưu trữ trọn vẹn dữ liệu của các công ty đã hủy niêm yết/phá sản.

---

## 🏆 TỔNG KẾT BÁO CÁO & KHUYẾN NGHỊ CHO MÔ HÌNH MACHINE LEARNING

### Ma trận Tổng hợp Kết quả Kiểm thử Dữ liệu

| Bước kiểm thử | Nội dung kiểm tra | Kết quả thực tế | Trạng thái |
|:---:|:---|:---|:---:|
| **Bước 1** | Số lượng mã Russell 1000 Index PIT | Trung bình 997 mã/năm (967 – 1,026 mã) | ✅ **ĐẠT** |
| **Bước 2** | Linkage Match Rate (Russell ↔ OHLCV) | **99.42% trên TOÀN BỘ 27 năm (2000–2026)** | ✅ **ĐẠT** |
| **Bước 3** | Parquet Schema & Data Integrity | 0 lỗi Null/NaN, 0 vi phạm logic, SplitAdjusted | ✅ **ĐẠT** |
| **Bước 4** | Trading Days & Time Continuity | 98.86% Full ($\ge 150$d), 0.56% Partial ($< 150$d) | ✅ **ĐẠT** |
| **Bước 5** | Survivorship Bias & Identity Audit | Survivorship Gap chỉ có **+0.4pp** (An toàn tuyệt đối) | ✅ **ĐẠT** |

### Khuyến nghị Thiết kế Pipeline Huấn luyện Mô hình ML

1. **Giai đoạn Huấn luyện & Kiểm thử Chính (Primary Window: 2000 – 2026)**:
   - Nhờ bản cập nhật `v4`, **toàn bộ 27 năm (2000–2026) đều đạt độ phủ 99.1% – 99.9%**, cho phép mở rộng cửa sổ huấn luyện mô hình Machine Learning qua cả 2 đợt khủng hoảng lớn (Dot-com 2000–2002 và GFC 2008) với chất lượng Audit-Grade tuyệt đối.
