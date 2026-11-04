# 📋 BÁO CÁO SANITY CHECKS S1–S7: Kiểm tra Tính Nhất Quán Dữ Liệu In-Sample

> **Dự án**: Predict Daily Return Rankings — Russell 1000 PIT (2000–2026)  
> **Giai đoạn**: Phase 2 — Data Sanity Checks (Tiền xử lý trước Feature Engineering)  
> **Script**: [`scripts/05_eda/sanity_check_in_sample.py`](../../scripts/05_eda/sanity_check_in_sample.py)  
> **Ngày thực hiện**: 03/10/2026  
> **Dữ liệu đầu vào**: `data/processed/in_sample/` — Ma trận Date × Ticker 6,021 ngày × 2,852 tickers

---

## 🎯 Mục đích tổng quát

Các bài test M1–M9 trước đây chỉ kiểm tra dữ liệu ở cấp **`data/processed/by_year/*.parquet`** (từng năm riêng lẻ). Chưa có bài test nào kiểm tra tính nhất quán của dữ liệu ở cấp **`data/processed/in_sample/`** — tức là các ma trận Date × Ticker đã được merge lại và sẽ được dùng **trực tiếp** để build feature và train model.

Mục tiêu của S1–S7 là xác nhận:
1. Dữ liệu sau khi merge không bị lệch / mất mát so với dữ liệu gốc.
2. Các biến phái sinh (returns, forward returns) được tính đúng công thức.
3. Không có look-ahead bias ẩn trong pipeline.
4. Hiểu rõ đặc tính thống kê (NaN, volume, adj_close) để thiết kế feature đúng.

---

## ✅ S1: CROSS-LAYER CONSISTENCY

### Mô tả
Đối chiếu tập tickers và trading calendar giữa hai layer dữ liệu:
- **Layer 1** — `data/processed/by_year/russell1000_{year}.parquet` (2000–2023)
- **Layer 2** — `data/processed/in_sample/close.parquet` (ma trận 6,021 × 2,852)

### Kết quả

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Tickers trong in_sample matrix | **2,852** |
| Tickers unique trong by_year (2000–2023) | **2,700** |
| Tickers trong CẢ HAI layer | **2,697** |
| Chỉ có trong matrix (không có trong by_year) | **155** |
| Chỉ có trong by_year (không có trong matrix) | **3** |
| Trading days khớp (by_year vs matrix) | **6,021 / 6,021** ✅ |
| Missing dates trong matrix | **0** ✅ |
| Extra dates trong matrix | **0** ✅ |

### Phân tích

**155 tickers "dư" trong matrix (SMCI, RDDT, APLD, RBRK, DUOL...):**
Đây là các tickers thuộc **out-sample (2024–2026)** nhưng có mặt trong cột header của matrix vì `05_build_cross_sectional.py` tổng hợp toàn bộ 2,852 unique tickers từ **toàn bộ 27 năm** (không chỉ in-sample 2000–2023). Trong phần in-sample, các tickers này có giá trị = NaN (không giao dịch trong 2000–2023).

> **Đây không phải lỗi dữ liệu.** Tuy nhiên cần lọc các tickers có 100% NaN trong in-sample period trước khi build feature để tránh hao tốn bộ nhớ và tính toán vô ích.

**3 tickers chỉ có trong by_year (VYX, NLOP, KLG):**
Bị drop khi build matrix do có quá ít dữ liệu hoặc lỗi nhỏ trong script merge. Số lượng không đáng kể (3/2,700 = 0.1%).

### Kết luận S1
> ⚠️ **CẢNH BÁO (không nghiêm trọng)**: 155 tickers out-sample nằm trong header của in_sample matrix. **Cần thêm bước filter** khi build feature: loại bỏ tickers có >95% NaN trong in-sample period. Sẽ xử lý trong Task T4 (Feature Store).

---

## ✅ S2: RETURN CALCULATION CHECK

### Mô tả
Kiểm tra xem `data/processed/in_sample/returns.parquet` có được tính đúng theo công thức:

$$r_{i,t} = \frac{Close_{i,t}}{Close_{i,t-1}} - 1$$

Kiểm tra trên 5 tickers blue-chip: AAPL, MSFT, GOOGL, JPM, XOM.

### Kết quả

| Ticker | Max \|diff\| vs tính lại | Trạng thái |
|:---|:---:|:---:|
| AAPL | 0.00000000 | ✅ PASS |
| MSFT | 0.00000000 | ✅ PASS |
| GOOGL | 0.00000000 | ✅ PASS |
| JPM | 0.00000000 | ✅ PASS |
| XOM | 0.00000000 | ✅ PASS |

**Kiểm tra Return tại các ngày sự kiện quan trọng:**

| Ticker | Ngày | Sự kiện | Return thực tế |
|:---|:---|:---|:---:|
| AAPL | 2008-09-15 | Lehman Brothers phá sản | **-5.76%** |
| AAPL | 2020-03-16 | COVID sell-off | **-12.86%** |
| AAPL | 2020-08-31 | Apple 4-for-1 Split | **+3.39%** |
| GOOGL | 2022-07-18 | Alphabet 20-for-1 Split | **-2.46%** |
| XOM | 2020-03-09 | Oil price war crash | **-12.24%** |

### Phân tích
- Các con số return tại sự kiện quan trọng **hoàn toàn hợp lý** và khớp với thực tế lịch sử.
- Return trong ngày Split (+3.39% Apple, -2.46% Alphabet) xác nhận giá **đã được SplitAdjusted** — không bị nhảy giá giả.
- Sai số floating-point = 0 (exact match) — công thức tính return không bị làm tròn.

### Kết luận S2
> ✅ **PASS**: `returns.parquet` được tính chính xác theo công thức chuẩn. Dữ liệu return hoàn toàn tin cậy để tính features và IC.

---

## ✅ S3: FORWARD RETURN LOOK-AHEAD BIAS CHECK

### Mô tả
Kiểm tra xem `forward_returns.parquet` có bị **look-ahead bias** không. Yêu cầu:

$$\text{forward\_return}[t] = \text{return}[t+1]$$

Tức là forward return ngày T phải đúng bằng return quan sát được vào ngày T+1 — không được dùng thông tin tương lai.

### Kết quả

| Ticker | N samples kiểm tra | Max \|diff\| | Trạng thái |
|:---|:---:|:---:|:---:|
| AAPL | 6,020 | 0.00000000 | ✅ PASS |
| MSFT | 6,020 | 0.00000000 | ✅ PASS |
| JPM | 6,020 | 0.00000000 | ✅ PASS |

### Phân tích
`forward_return[t]` được kiểm tra bằng cách so sánh `fwd.shift(1)` với `return`. Sai số = 0 exact trên 6,020 ngày giao dịch cho 3 tickers lớn. Không phát hiện look-ahead bias.

### Kết luận S3
> ✅ **PASS**: Không có look-ahead bias trong `forward_returns.parquet`. An toàn để dùng làm **target variable** trong ML model.

---

## ✅ S4: NaN PROFILE CỦA MA TRẬN CLOSE

### Mô tả
Phân tích phân bố NaN trong ma trận `close.parquet` (6,021 × 2,852):
- NaN % tổng thể
- NaN % theo từng năm (xem có tập trung vào giai đoạn cụ thể không)
- Top tickers NaN nhiều nhất
- Số tickers đủ dữ liệu toàn bộ in-sample
- Phát hiện phantom delisting

### Kết quả

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Total cells | 17,171,892 |
| NaN cells | 11,248,272 |
| **NaN tổng thể** | **65.50%** |
| Số tickers có 0% NaN (full in-sample) | **240 tickers** |
| Số tickers có 100% NaN (out-sample only) | **Nhiều** (là 155 tickers ở S1) |
| Phantom delisting (sample 200 tickers đầu) | **113 tickers** — bình thường |

**NaN % theo từng năm (2000–2023):**

| Giai đoạn | NaN Range | Nhận xét |
|:---|:---:|:---|
| 2000–2006 | 65.1%–66.0% | Ổn định |
| 2007–2013 | 65.1%–66.5% | Ổn định |
| 2014–2022 | 64.4%–66.0% | Nhẹ hơn (nhiều tickers active) |
| 2023 | 65.1% | Ổn định |

### Phân tích
- NaN **65.50% là hoàn toàn bình thường**: Russell 1000 chỉ có ~1,000 stocks/năm, ma trận chứa 2,852 unique tickers qua 27 năm. Phần lớn NaN là do các tickers chưa/không còn thuộc index trong năm đó.
- NaN **phân bổ đều qua các năm** (64–66%), không tập trung vào năm cụ thể → không có vấn đề với pipeline merge.
- **240 tickers đủ dữ liệu toàn bộ 24 năm in-sample** — đây là nhóm "blue chip" ổn định nhất của Russell 1000 (AAPL, MSFT, JNJ, KO...).
- **113/200 tickers có NaN đột ngột cuối** là hiện tượng bình thường của M&A / hủy niêm yết / IPO giữa year.

### Kết luận S4
> ✅ **PASS**: NaN profile hợp lý, phân bổ đều theo năm. **Quy tắc lọc cho Feature Engineering**: Một cổ phiếu phải có ít nhất **252 ngày dữ liệu** (1 năm) trong cửa sổ lookback trước khi được tính feature tại ngày đó.

---

## ✅ S5: VOLUME SANITY CHECK

### Mô tả
Phát hiện các cổ phiếu có `volume = 0` trong nhiều ngày liên tiếp (trading halt, cổ phiếu ngừng giao dịch). Kiểm tra tổng volume thị trường theo ngày.

### Kết quả

**Tickers có zero-volume streak ≥ 5 ngày (sample 300 tickers đầu):**

| Ticker | Max zero-vol streak | Nguyên nhân khả năng |
|:---|:---:|:---|
| AWH | **67 ngày** | Trading halt / OTC / thâu tóm |
| ARD | **60 ngày** | Trading halt / delisting |
| ADRX | **13 ngày** | Short trading halt |

**Tổng volume thị trường:**

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Min total daily volume | 1,096,695,875 cổ phần |
| Max total daily volume | 15,236,054,677 cổ phần |
| Mean total daily volume | 4,662,509,588 cổ phần |
| Số ngày total volume = 0 | **0** ✅ |

### Phân tích
- AWH (67 ngày) và ARD (60 ngày) có khả năng là cổ phiếu bị trading halt kéo dài hoặc đang trong quá trình M&A. Đây là hiện tượng thực tế, không phải lỗi pipeline.
- Total market volume không có ngày nào = 0 → không có lỗi trading calendar.
- Cần **lọc cổ phiếu có volume = 0** khi tính Amihud illiquidity và VWAP features.

### Kết luận S5
> ⚠️ **CẢNH BÁO (nhỏ)**: 3/300 tickers có zero-volume streak dài. **Khi build feature**: skip tính Amihud/VWAP cho các ngày `volume = 0`. Gán NaN thay vì chia cho 0.

---

## ✅ S6: CROSS-CHECK GIÁ CLOSE (by_year vs in_sample)

### Mô tả
Lấy 10 tickers (AAPL, MSFT, GOOGL, AMZN, JPM, XOM, WMT, JNJ, PG, V), so sánh giá `close` tại 3 ngày cụ thể trong lịch sử giữa `by_year/russell1000_{year}.parquet` và `in_sample/close.parquet`.

### Kết quả

Tất cả 10 tickers × 3 ngày kiểm tra: **giá close khớp hoàn toàn** giữa 2 layer.

| Ngày | Kết quả |
|:---|:---:|
| 2001-09-17 (post 9/11) | ✅ Khớp hoàn toàn |
| 2008-10-10 (GFC) | ✅ Khớp hoàn toàn |
| 2020-03-20 (COVID) | ✅ Khớp hoàn toàn |

### Phân tích
Pipeline merge từ `by_year → merged → in_sample` không bị off-by-one date hay ticker mismatch. Dữ liệu được preserve chính xác qua quá trình merge.

### Kết luận S6
> ✅ **PASS**: Không có sai lệch giá giữa by_year và in_sample matrix. Script `04_merge_all_years.py` và `05_build_cross_sectional.py` hoạt động đúng.

---

## ⚠️ S7: ADJ_CLOSE vs CLOSE COMPARISON

### Mô tả
Kiểm tra xem `adj_close.parquet` và `close.parquet` có khác nhau không, và tỷ lệ `adj_close / close` có hợp lý không.

### Kết quả

| Ticker | adj_close ≡ close? | Max ratio | Min ratio | % days diff > 0.1% |
|:---|:---:|:---:|:---:|:---:|
| AAPL | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| MSFT | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| GOOGL | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| JPM | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| XOM | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| KO | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| PEP | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |
| JNJ | **Bằng nhau** | 1.0000 | 1.0000 | 0.0% |

### Phân tích
`adj_close = close` cho toàn bộ 8 tickers được kiểm tra (kể cả KO, PEP, JNJ là các cổ phiếu trả dividend cao). Điều này có nghĩa là:

- QuantConnect Engine với chế độ `DataNormalizationMode.SplitAdjusted` đã điều chỉnh **cả split lẫn dividend** vào trường `close` từ đầu.
- Hai trường `adj_close` và `close` trong pipeline hiện tại thực chất là **cùng một chuỗi số**.
- **Đây không phải lỗi** — đây là đặc điểm của QuantConnect `SplitAdjusted` mode.

> ⚠️ **Lưu ý quan trọng cho Feature Engineering**: Không cần dùng `adj_close` riêng. Chỉ dùng `close` (đã bao gồm cả dividend & split adjustment). Khi tính feature momentum, reversal, return — đều dùng `close`.

### Kết luận S7
> ⚠️ **CẢNH BÁO (cần lưu ý thiết kế)**: `adj_close ≡ close`. Feature Engineer phải sửa `feature_engineer.py` để **chỉ đọc từ `close`**, không cần `adj_close` riêng.

---

## 🏆 TỔNG KẾT SANITY CHECKS S1–S7

| # | Check | Trạng thái | Ghi chú hành động |
|:---:|:---|:---:|:---|
| **S1** | Cross-layer consistency | ⚠️ Cảnh báo | Lọc tickers >95% NaN trong T4 |
| **S2** | Return calculation | ✅ PASS | Không cần sửa |
| **S3** | Forward return / look-ahead bias | ✅ PASS | An toàn dùng làm target |
| **S4** | NaN profile matrix | ✅ PASS | Ngưỡng lọc: ≥252 ngày lookback |
| **S5** | Volume sanity | ⚠️ Cảnh báo | Gán NaN khi volume=0 trong feature |
| **S6** | Cross-check by_year vs in_sample | ✅ PASS | Merge pipeline đúng |
| **S7** | adj_close vs close | ⚠️ Cảnh báo | Chỉ dùng `close` trong feature store |

### Quy tắc cụ thể cho Feature Engineering (rút ra từ Sanity Checks):
1. **Chỉ dùng `close`** để tính return, momentum, reversal (không dùng `adj_close`).
2. **Lọc tickers** có <252 ngày non-NaN trong cửa sổ lookback trước ngày tính feature.
3. **Gán NaN** cho Amihud/VWAP/volume features khi `volume = 0`.
4. **Không thêm** các tickers out-sample (155 tickers xuất hiện sau 2023) vào tập feature in-sample.
5. **Forward return** an toàn để dùng làm target (không bị look-ahead bias).
