# 📊 BÁO CÁO AUDIT-GRADE TOÀN DIỆN VỀ DỮ LIỆU RUSSELL 1000 (2000 – 2026)
> **Đồ án tổng hợp**: Dự đoán thứ hạng tỷ suất sinh lời hàng ngày cổ phiếu (Predict Daily Return Rankings)  
> **Chỉ số mục tiêu**: Russell 1000 Index (Point-In-Time)  
> **Giai đoạn**: 2000 – 2026 (27 năm liên tục)  
> **Nguồn dữ liệu**: QuantConnect Lean Engine (SplitAdjusted Data Normalization)  
> **Tiêu chuẩn kiểm toán**: Audit-Grade v3 (Phân loại Full / Partial / Empty / Fail)  

---

## 📑 1. TỔNG QUAN BỘ DỮ LIỆU & KẾT QUẢ XUẤT CLOUD (2000 – 2026)

* **Tổng số năm thu thập**: **27 năm liên tục** (`2000` đến `2026`).
* **Tổng số lượt truy vấn (Stock-Years)**: **26,975 lượt cổ phiếu - năm**.
* **Tỷ lệ lỗi hệ thống (System Fail Rate)**: **0.00%** (0 lỗi crash, 0 ngoại lệ im lặng).
* **Cấu trúc lưu trữ**: Chia thành từng năm độc lập để dễ dàng kiểm soát, báo cáo và huấn luyện mô hình Machine Learning:
  👉 `data/processed/by_year/russell1000_{YEAR}.parquet`
  👉 `data/processed/audit/master_audit_2000_2026.csv`

---

## 📈 2. BẢNG THỐNG KÊ CHI TIẾT KIỂM TOÁN THEO TỪNG NĂM (AUDIT LOG TABLE)

| Năm | Tổng mã PIT | Thành công (Full $\ge$ 150d) | Một phần (Partial $< 150$d) | Không có data (Empty) | Lỗi hệ thống (Fail) | Tỷ lệ phủ ($\%$) | Dung lượng ZIP |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2000** | 996 | 727 | 11 | 258 | 0 | **74.1%** | 2.73 MB |
| **2001** | 989 | 739 | 8 | 242 | 0 | **75.5%** | 2.84 MB |
| **2002** | 988 | 767 | 8 | 213 | 0 | **78.4%** | 3.05 MB |
| **2003** | 988 | 789 | 2 | 197 | 0 | **80.1%** | 3.13 MB |
| **2004** | 990 | 792 | 4 | 194 | 0 | **80.4%** | 3.14 MB |
| **2005** | 987 | 802 | 6 | 179 | 0 | **81.9%** | 3.19 MB |
| **2006** | 982 | 825 | 2 | 155 | 0 | **84.2%** | 3.26 MB |
| **2007** | 1,013 | 862 | 5 | 146 | 0 | **85.6%** | 3.51 MB |
| **2008** | 1,002 | 862 | 2 | 138 | 0 | **85.7%** | 3.77 MB |
| **2009** | 967 | 846 | 3 | 118 | 0 | **87.3%** | 3.63 MB |
| **2010** | 981 | 867 | 2 | 112 | 0 | **88.0%** | 3.65 MB |
| **2011** | 982 | 878 | 3 | 101 | 0 | **89.1%** | 3.74 MB |
| **2012** | 987 | 888 | 7 | 92 | 0 | **90.2%** | 3.68 MB |
| **2013** | 1,000 | 911 | 2 | 87 | 0 | **90.9%** | 3.82 MB |
| **2014** | 1,023 | 943 | 2 | 78 | 0 | **92.0%** | 3.99 MB |
| **2015** | 1,026 | 949 | 9 | 68 | 0 | **92.8%** | 4.06 MB |
| **2016** | 991 | 935 | 5 | 51 | 0 | **94.9%** | 4.00 MB |
| **2017** | 980 | 932 | 6 | 42 | 0 | **95.7%** | 3.94 MB |
| **2018** | 976 | 941 | 5 | 30 | 0 | **96.9%** | 4.07 MB |
| **2019** | 1,001 | 974 | 3 | 24 | 0 | **97.6%** | 4.22 MB |
| **2020** | 994 | 981 | 3 | 10 | 0 | **99.0%** | 4.48 MB |
| **2021** | 1,017 | 1,004 | 5 | 8 | 0 | **99.2%** | 4.51 MB |
| **2022** | 1,013 | 1,008 | 1 | 4 | 0 | **99.6%** | 4.53 MB |
| **2023** | 1,011 | 991 | 13 | 7 | 0 | **99.3%** | 4.38 MB |
| **2024** | 1,010 | 1,000 | 3 | 7 | 0 | **99.3%** | 4.42 MB |
| **2025** | 1,014 | 1,004 | 5 | 5 | 0 | **99.5%** | 4.44 MB |
| **2026** | 1,011 | 999 | 8 | 4 | 0 | **99.6%** | 3.38 MB |
| **TỔNG** | **26,975** | **24,129** | **140** | **2,706** | **0** | **89.5% (Trung bình)** | **97.55 MB** |

---

## 🧠 3. GIẢI TRÌNH KIỂM TOÁN CHI TIẾT (AUDIT RATIONALE)

### ① Nhóm `Full` ($\ge 150$ ngày giao dịch)
* Đây là nhóm các cổ phiếu có chuỗi thời gian đầy đủ trong năm, đảm bảo tính liên tục để tính toán chỉ báo kỹ thuật, Alpha, Tỷ suất sinh lời (Return) và Xếp hạng (Rank).
* Đạt số lượng tối đa ở giai đoạn 2016–2026 (932 đến 1,008 mã/năm).

### ② Nhóm `Partial` ($< 150$ ngày giao dịch)
* Chiếm số lượng rất nhỏ ($\approx 0.5\%$).
* Nguyên nhân: Do doanh nghiệp **mới IPO giữa năm** (chưa đủ 150 ngày) hoặc **bị thâu tóm / hủy niêm yết giữa năm**.
* Tất cả đều được ghi nhận số ngày giao dịch thực tế vào file audit log.

### ③ Nhóm `Empty` (Không có dữ liệu trong kho QuantConnect)
* Chiếm chủ yếu ở giai đoạn 2000–2005 (do các công ty đã phá sản / giải thể / sáp nhập từ bong bóng Dot-com từ hơn 20–25 năm trước như `AOL`, `Bestfoods`, `Burr-Brown`, `Adelphia`, `Excite@Home`).
* Nguyên nhân: Cơ sở dữ liệu thương mại của QuantConnect chỉ duy trì lịch sử dữ liệu giá đối với các doanh nghiệp còn hoạt động sau đợt chuẩn hóa 2003–2005.

### ④ Chuẩn hóa dữ liệu (`SplitAdjusted`)
* Toàn bộ chuỗi giá được đăng ký dưới chế độ `DataNormalizationMode.SplitAdjusted`.
* Điều này đảm bảo triệt tiêu hiện tượng sụt giảm giá ảo do tách/gộp cổ phiếu (Stock Splits), giúp mô hình ML dự đoán thứ hạng tỷ suất sinh lời chính xác tuyệt đối.

---

## 🛠️ 4. QUY TRÌNH XỬ LÝ & PHÂN CHIA NĂM KHI XUẤT DATA (YEARLY DATA ARCHITECTURE)

Thay vì gộp toàn bộ 27 năm vào một file Parquet duy nhất quá lớn, hệ thống chuyển sang lưu trữ theo cấu trúc từng năm độc lập:

```text
data/
├── raw/
│   └── quantconnect/
│       ├── russell1000_2000.zip
│       ├── russell1000_2001.zip
│       └── ... (tới 2026)
├── processed/
│   ├── by_year/
│   │   ├── russell1000_2000.parquet
│   │   ├── russell1000_2001.parquet
│   │   └── ... (tới 2026)
│   └── audit/
│       └── master_audit_2000_2026.csv
```

### Ưu điểm vượt trội:
1. **Dễ dàng kiểm soát**: Dễ dàng load từng năm để chạy backtest, kiểm tra hoặc vẽ biểu đồ EDA.
2. **Tối ưu cho Training Model ML**: Cho phép dễ dàng chia cửa sổ cuộn (Rolling Window) hoặc Walk-Forward Cross-Validation (ví dụ: Train trên các file 2015-2020, Valid 2021-2022, Test 2023-2026).
3. **Minh bạch khi Báo cáo Đồ án**: Có sẵn file `master_audit_2000_2026.csv` để giải trình chi tiết từng mã cổ phiếu với thầy cô.
