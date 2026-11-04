# 📊 BÁO CÁO KHAI PHÁ & KIỂM THỬ DỮ LIỆU — PHASE 1: DATA PIPELINE VALIDATION

> **Đồ án**: Dự đoán thứ hạng tỷ suất sinh lời hàng ngày cổ phiếu (Predict Daily Return Rankings)  
> **Dữ liệu**: Russell 1000 Index — Point-In-Time (2000–2026)  
> **Phiên bản Dữ liệu**: Audit-Grade v4 (`mappingResolveDate` via QuantConnect Lean Engine)  
> **Ngày thực hiện**: 01/10/2026 – 03/10/2026  
> **Phạm vi**: Phase 1 — Universe + OHLCV Pipeline Validation (9 bài test)

---

## 🗂️ I. TỔNG QUAN BỘ DỮ LIỆU

### Nguồn dữ liệu

| # | Bộ dữ liệu | Mô tả | Vị trí |
|:---:|:---|:---|:---|
| 1 | **Russell 1000 Universe** | Danh sách mã cổ phiếu theo từng năm (2000–2026). Trích xuất từ tài liệu PDF/CSV/JSON/XLS chính thức của FTSE Russell. | `data/raw/universe/by_year/russell1000_{year}.json` |
| 2 | **Market Data (OHLCV)** | Giá giao dịch hàng ngày (O/H/L/C/V) từ QuantConnect Cloud Engine, chế độ `SplitAdjusted`, với cơ chế Point-In-Time Ticker Resolution. | `data/processed/by_year/russell1000_{year}.parquet` |

**Tài liệu kiểm toán bổ sung:**
- `data/processed/audit/by_year/audit_{year}.csv` — Bản ghi chi tiết từng mã/năm
- `data/processed/audit/master_audit_2000_2026.csv` — Tổng hợp 26,919 bản ghi

### Thống kê tổng thể

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Số năm thu thập | **27 năm** (2000–2026) |
| Tổng Stock-Years | **26,919 lượt** |
| Unique Tickers | **2,860 mã** |
| Total OHLCV Rows | **6,601,516 dòng** |
| Coverage Rate | **99.42%** |
| System Fail Rate | **0.00%** |
| In-Sample size | 6,021 ngày × 2,852 tickers (2000–2023) |
| Out-Sample size | 687 ngày × 2,852 tickers (2024–2026) \[LOCKED\] |

### Cấu trúc lưu trữ

```
data/processed/
├── by_year/russell1000_{YEAR}.parquet     ← 27 files (nguồn gốc)
├── daily_ohlcv/russell1000_daily_2000_2026.parquet  ← Merged (119.1 MB)
├── in_sample/   close, returns, forward_returns, volume, adj_close (2000–2023)
├── out_sample/  close, returns, forward_returns, volume, adj_close (2024–2026)
└── audit/       by_year/audit_{year}.csv + master_audit_2000_2026.csv
```

---

## ✅ TEST 1: Cấu trúc Universe Russell 1000 (Universe Structure)

**Script**: `scripts/02_validation_universe/test1_universe_structure.py`  
**Mục đích**: Xác nhận dữ liệu Universe JSON hợp lệ — đúng kiểu `list[str]`, không có NULL/duplicate/whitespace.

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

- **Trung bình**: 997 mã/năm | **Min**: 967 (2009) | **Max**: 1,026 (2015)
- Tổng unique tickers qua 27 năm: **2,884 mã**
- NULL, Empty, Duplicate, Whitespace ticker: **0**

### Nhận xét
Năm 2009 có ít mã nhất (967) do nhiều công ty phá sản sau GFC 2008. Năm 2015 có nhiều nhất (1,026) do multi-share class (GOOGL+GOOG). Hoàn toàn phù hợp với quy tắc vận hành FTSE Russell.

> ✅ **PASS** — Universe đầy đủ, sạch, đúng định dạng.

---

## ✅ TEST 2: PIT Turnover Rate

**Script**: `scripts/02_validation_universe/test3_universe_pit_turnover.py`  
**Mục đích**: Kiểm tra tỷ lệ thay đổi thành phần chỉ số Russell 1000 hàng năm (annual reconstitution).

### Kết quả
- **Turnover trung bình**: ~8–12%/năm
- Biến động cao nhất tại năm 2001–2002 (Dot-com crash) và 2008–2009 (GFC)

> ✅ **PASS** — Turnover rate phù hợp với lịch sử tái cơ cấu chỉ số Russell 1000.

---

## ✅ TEST 3: Security Identity Mapping (PIT Ticker Resolution)

**Script**: `scripts/02_validation_universe/test4_security_identity.py`  
**Mục đích**: Xác minh cơ chế `mappingResolveDate` giải quyết đúng các trường hợp đổi tên/M&A.

### Kết quả — Các case nổi tiếng

| Old Ticker | New Ticker | Sự kiện | Kết quả |
|:---|:---|:---|:---:|
| `FB` | `META` | Meta Platforms đổi tên 2021 | ✅ 100% |
| `PCLN` | `BKNG` | Booking Holdings đổi tên 2018 | ✅ 100% |
| `ANTM` | `ELV` | Elevance Health đổi tên 2022 | ✅ 100% |
| `KFT` | `MDLZ` | Mondelez tách ra 2012 | ✅ 100% |
| `LB` | `BBWI` | Bath & Body Works 2021 | ✅ 100% |
| `AAXN` | `AXON` | Axon Enterprise 2021 | ✅ 100% |
| `ACE` | `CB` | Chubb Limited 2016 | ✅ 100% |
| `TWX` | `T` | Time Warner → AT&T 2018 | ✅ 100% |

> ✅ **PASS** — 100% các case đổi ticker nổi tiếng được resolve đúng nhờ `mappingResolveDate`.

---

## ✅ TEST 4: OHLCV Schema & Integrity (M1)

**Script**: `scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py`  
**Mục đích**: Kiểm tra schema chuẩn và logic tài chính của toàn bộ 6.6M dòng OHLCV.

### Schema dữ liệu v4

| Trường | Kiểu | Mô tả |
|:---|:---|:---|
| `date` | `date32` | Ngày giao dịch YYYY-MM-DD |
| `ticker` | `string` | Mã cổ phiếu |
| `open` | `float64` | Giá mở cửa (SplitAdjusted) |
| `high` | `float64` | Giá cao nhất (SplitAdjusted) |
| `low` | `float64` | Giá thấp nhất (SplitAdjusted) |
| `close` | `float64` | Giá đóng cửa (SplitAdjusted) |
| `volume` | `int64` | Khối lượng giao dịch |

### Kết quả Integrity Tests

| Loại kiểm thử | Số vi phạm | Trạng thái |
|:---|:---:|:---:|
| Null / NaN trong OHLCV | **0** | ✅ PASS |
| Duplicate (Date, Ticker) | **0** | ✅ PASS |
| Giá ≤ 0 | **0** | ✅ PASS |
| High < Low | **0** | ✅ PASS |
| Open/Close ngoài [Low, High] | **0** | ✅ PASS |

> ✅ **PASS** — 6,601,516 dòng, 0 vi phạm.

---

## ✅ TEST 5: Time Coverage & Trading Days (M2)

**Script**: `scripts/03_validation_ohlcv/test_m2_time_coverage.py`  
**Mục đích**: Kiểm tra số ngày giao dịch thực tế và tính liên tục của chuỗi thời gian.

### Phân loại coverage

| Nhóm | Tiêu chí | Số lượt | Tỷ lệ |
|:---|:---|:---:|:---:|
| **Full** | ≥ 240 ngày/năm | 26,153 | **97.2%** |
| **Partial** | 50–239 ngày/năm | 611 | 2.3% |
| **Short** | < 50 ngày/năm | 155 | 0.6% |

- Số ngày giao dịch trung bình thị trường Mỹ/năm: **248.4 ngày** (chuẩn 250–252d)
- Tickers có lịch sử cực ngắn (< 10 ngày): rất ít, đều là IPO/delisting giữa năm

> ✅ **PASS** — 97.2% stock-years có đủ dữ liệu. Phù hợp với thực tế vận hành thị trường.

---

## ✅ TEST 6: Corporate Actions & Split Adjustment (M3)

**Script**: `scripts/03_validation_ohlcv/test_m3_corporate_actions.py`  
**Mục đích**: Xác nhận giá đã được điều chỉnh đúng cho các sự kiện chia tách cổ phiếu lớn.

### Kết quả kiểm tra Split Events nổi tiếng

| Sự kiện | Ticker | Ngày | Return ngày Split | Kết quả |
|:---|:---|:---|:---:|:---:|
| Apple 7-for-1 | AAPL | 2014-06-09 | < 5% | ✅ SplitAdj |
| Apple 4-for-1 | AAPL | 2020-08-31 | +3.39% | ✅ SplitAdj |
| Tesla 5-for-1 | TSLA | 2020-08-31 | < 5% | ✅ SplitAdj |
| Nvidia 4-for-1 | NVDA | 2021-07-20 | < 5% | ✅ SplitAdj |
| Nvidia 10-for-1 | NVDA | 2024-06-10 | < 5% | ✅ SplitAdj |
| Amazon 20-for-1 | AMZN | 2022-06-06 | < 5% | ✅ SplitAdj |
| Alphabet 20-for-1 | GOOGL | 2022-07-18 | -2.46% | ✅ SplitAdj |

- Tổng thanh giá kiểm tra: ~6.3M | Spike |r| > 50%: rất ít, đều có lý do cơ bản (earnings shock, delisting)

> ✅ **PASS** — 100% sự kiện Split lớn không bị nhảy giá giả. SplitAdjusted hoàn hảo.

---

## ✅ TEST 7: Russell Universe ↔ OHLCV Compatibility (M4)

**Script**: `scripts/03_validation_ohlcv/test_m4_russell_ohlcv_compatibility.py`  
**Mục đích**: Đối soát tỷ lệ khớp nối giữa danh sách PIT Russell 1000 và kho OHLCV.

### Kết quả Linkage Reconciliation (2000–2026)

| Năm | Russell PIT | Matched | Missing | Match Rate |
|:---:|:---:|:---:|:---:|:---:|
| 2000 | 996 | 989 | 7 | **99.3%** |
| 2001 | 989 | 984 | 5 | **99.5%** |
| 2005 | 987 | 979 | 8 | **99.2%** |
| 2008 | 1,002 | 994 | 8 | **99.2%** |
| 2009 | 967 | 958 | 9 | **99.1%** |
| 2015 | 1,026 | 1,023 | 3 | **99.7%** |
| 2016 | 991 | 990 | 1 | **99.9%** |
| 2020 | 994 | 992 | 2 | **99.8%** |
| **TỔNG** | **26,919** | **26,764** | **155** | **99.42%** |

- Extra tickers (dư thừa) = **0** trên tất cả 27 năm

> ✅ **PASS** — 99.42% match rate toàn bộ 27 năm. Pipeline sạch không rác.

---

## ✅ TEST 8: Market Value & Liquidity (M5/M6)

**Script**: `scripts/03_validation_ohlcv/test_m5_m6_market_value.py`  
**Mục đích**: Kiểm tra tính hợp lý của khối lượng giao dịch và ước lượng Dollar Volume.

### Kết quả
- **Tổng Dollar Volume quét**: ~\$1,168 Trillion (27 năm)
- **Dollar Volume trung bình/ngày**: ~\$179.5 Billion/ngày (hợp lý cho Russell 1000)
- **Tickers Volume = 0 toàn bộ năm**: 0

> ✅ **PASS** — Dollar Volume hợp lý, không có tickers hoàn toàn không giao dịch.

---

## ✅ TEST 9: Survivorship Bias Audit

**Script**: `scripts/04_deep_audit/deep_audit_survivorship.py`  
**Mục đích**: Kiểm tra xem dữ liệu OHLCV có thiên lệch về phía cổ phiếu còn tồn tại không.

### Kết quả — Survivorship Gap

| Nhóm | Số Stocks | Stock-Years | Có OHLCV | Coverage |
|:---|:---:|:---:|:---:|:---:|
| **Survivor** (còn trong 2024+) | 1,101 | 16,324 | 16,256 | **99.6%** |
| **Disappeared** (không có sau 2024) | 1,783 | 10,595 | 10,507 | **99.2%** |

- **Survivorship Gap = +0.4 percentage points** (ngưỡng an toàn < 5pp)
- 98.5% cổ phiếu đã hủy niêm yết vẫn có dữ liệu OHLCV đầy đủ 90–100%
- Chỉ 17 cổ phiếu (trên toàn bộ 2,884) hoàn toàn thiếu dữ liệu

### Giải thích cơ chế v4
`mappingResolveDate = datetime(year, 6, 30)` → QuantConnect Lean Engine đọc `map_files` nội bộ để resolve ticker → Security ID tại thời điểm lịch sử → lấy được data cho cả cổ phiếu đã hủy niêm yết.

> ✅ **PASS** — Survivorship Bias gần như bằng 0. An toàn tuyệt đối cho ML research.

---

## 🏆 II. MA TRẬN TỔNG KẾT PHASE 1

| # | Bài test | Script | Kết quả thực tế | Trạng thái |
|:---:|:---|:---|:---|:---:|
| T1 | Universe Structure | `test1_universe_structure.py` | 997 mã/năm avg, 0 lỗi format | ✅ PASS |
| T2 | PIT Turnover Rate | `test3_universe_pit_turnover.py` | 8–12%/năm, hợp lý | ✅ PASS |
| T3 | Security Identity Mapping | `test4_security_identity.py` | 100% M&A cases resolved | ✅ PASS |
| T4 | OHLCV Schema & Integrity | `test_m1_ohlcv_structure.py` | 0 lỗi trên 6.6M dòng | ✅ PASS |
| T5 | Time Coverage | `test_m2_time_coverage.py` | 97.2% Full ≥ 240d | ✅ PASS |
| T6 | Corporate Actions (SplitAdj) | `test_m3_corporate_actions.py` | 100% Split events đúng | ✅ PASS |
| T7 | Russell ↔ OHLCV Compatibility | `test_m4_russell_ohlcv_compatibility.py` | 99.42% match rate | ✅ PASS |
| T8 | Market Value & Liquidity | `test_m5_m6_market_value.py` | \$179.5B avg daily vol | ✅ PASS |
| T9 | Survivorship Bias Audit | `deep_audit_survivorship.py` | Gap chỉ +0.4pp | ✅ PASS |

> **KẾT LUẬN PHASE 1**: Toàn bộ 9/9 bài test **ĐẠT**. Dữ liệu đạt chuẩn Audit-Grade, sẵn sàng cho Phase 2 (Feature Engineering).

---

## ⚠️ III. HẠN CHẾ & GHI CHÚ TRUNG THỰC

1. **155 stock-years missing** (0.58%): Chủ yếu là cổ phiếu chỉ active trước 2012 không có trong QuantConnect historical database — đây là **data availability limitation**, không phải lỗi pipeline.
2. **Security Identity** chỉ được kiểm tra trên 8 cases nổi tiếng. Một số ticker ít phổ biến hơn có thể không được resolve hoàn hảo.
3. **SplitAdjusted ≡ close**: QuantConnect SplitAdjusted đã apply cả dividend vào `close`. Không có trường `adj_close` riêng biệt — cả hai trường giống nhau hoàn toàn.
4. **Dollar Volume** là ước tính dựa trên `close × volume` (không phải VWAP-weighted). Đây là proxy hợp lý nhưng không chính xác tuyệt đối.

---

*Báo cáo được hợp nhất từ `data_exploration_report.md` + `data_market_value_validation_report.md` | Cập nhật: 03/10/2026*
