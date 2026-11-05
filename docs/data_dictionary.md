> **Đặc tả triển khai features/target hiện hành:** [features v1](specifications/features_v1.md), [target/timing v1](specifications/target_and_timing_v1.md). Các ví dụ API trong từ điển minh họa khả năng thư viện, không thay thế hợp đồng v1; momentum v1 dùng adjusted close, không tự chuyển sang total return.

# TỪ ĐIỂN DỮ LIỆU DỰ ÁN (PROJECT DATA DICTIONARY)
## Russell 1000 Daily Return Rankings Prediction Engine

> **Phiên bản tài liệu**: 2.1 — tra cứu dữ liệu và giới hạn  
> **Cập nhật lần cuối**: 2026-11-04  
> **Vai trò**: Tài liệu tra cứu dự án; không phải chứng nhận dữ liệu của bên thứ ba  
> **Tình trạng kiểm toán**: Có kiểm tra nội bộ theo phạm vi báo cáo; chưa xác minh độc lập toàn bộ nguồn  
> **Phân vùng dữ liệu**: 
> - **Khởi tạo đặc trưng (Feature Warm-up)**: 1998-01-02 đến 2000-06-30 (630 phiên NYSE)
> - **Tập phát triển (Development Set)**: 2000-07-01 đến 2023-12-29 (5,911 phiên NYSE — Dùng cho EDA, Feature Engineering & Huấn luyện)
> - **Tập triển khai ngoài mẫu (Out-of-Sample - OOS)**: 2024-01-02 đến 2026-10-30 (711 phiên NYSE — **ĐÓNG BĂNG NGHIÊM NGẶT**)

```
========================================================================================
                              NGUYÊN TẮC ĐÓNG BĂNG DỮ LIỆU OOS
               TUYỆT ĐỐI KHÔNG DÙNG DỮ LIỆU GIAI ĐOẠN 2024–2026 TRONG BẤT KỲ 
             HOẠT ĐỘNG KHÁM PHÁ (EDA), CHỌN LỌC ĐẶC TRƯNG, HAY HUẤN LUYỆN NÀO!
             MỌI THỐNG KÊ, TỪ ĐIỂN VÀ MOMENTS PHÂN PHỐI CHỈ TÍNH TRÊN DEVELOPMENT.
========================================================================================
```

---

## MỤC LỤC TỔNG THỂ

1. [Tổng Quan Kiến Trúc Kho Dữ Liệu](#1-tổng-quan-kiến-trúc-kho-dữ-liệu)
2. [Phần 0: Nguồn Dữ Liệu Thô (Raw Data Sources)](#phần-0-nguồn-dữ-liệu-thô-raw-data-sources)
   - [0.1. Danh Sách Thành Viên iShares Russell 1000 Snapshots (PDF & JSON)](#01-danh-sách-thành-viên-ishares-russell-1000-snapshots-pdf--json)
   - [0.2. Nến Thô QuantConnect LEAN OHLCV (10 Tập Tin Nén Batch ZIP)](#02-nến-thô-quantconnect-lean-ohlcv-10-tập-tin-nén-batch-zip)
   - [0.3. Sự Kiện Doanh Nghiệp Thô (Corporate Actions Splits & Dividends)](#03-sự-kiện-doanh-nghiệp-thô-corporate-actions-splits--dividends)
   - [0.4. Bảng Cứu Hộ Ticker Rỗng (Empty Ticker Final Resolution)](#04-bảng-cứu-hộ-ticker-rỗng-empty-ticker-final-resolution)
3. [Phần 1: Kho Dữ Liệu Nến Thô Tier 1 (Tier 1 OHLCV Warehouse)](#phần-1-kho-dữ-liệu-nến-thô-tier-1-tier-1-ohlcv-warehouse)
   - [Bảng Đặc Tả Chi Tiết 9 Cột Tier 1](#bảng-đặc-tả-chi-tiết-9-cột-tier-1)
4. [Phần 2: Kho Dữ Liệu Giá Điều Chỉnh Tier 2 (Tier 2 Adjusted Price Warehouse)](#phần-2-kho-dữ-liệu-giá-điều-chỉnh-tier-2-tier-2-adjusted-price-warehouse)
   - [Đặc Tả Chi Tiết 25 Cột Dữ Liệu](#đặc-tả-chi-tiết-25-cột-dữ-liệu)
5. [Phần 3: Hệ Thống 17 Ma Trận 2D & 3 Lớp PIT Masks (`data/processed/matrices/`)](#phần-3-hệ-thống-17-ma-trận-2d--3-lớp-pit-masks-dataprocessedmatrices)
   - [3.1. Lưới Tọa Độ Không-Thời Gian Chính Quy](#31-lưới-tọa-độ-không-thời-gian-chính-quy)
   - [3.2. Bảng Danh Mục 26 Tệp Ma Trận & Masks](#32-bảng-danh-mục-26-tệp-ma-trận--masks)
   - [3.3. Cơ Chế Phân Cấp 3 Lớp Mặt Nạ Point-In-Time (PIT)](#33-cơ-chế-phân-cấp-3-lớp-mặt-nạ-point-in-time-pit)
   - [3.4. Cơ Chế Purge Ranh Giới Phát Triển & Ngoài Mẫu](#34-cơ-chế-purge-ranh-giới-phát-triển--ngoài-mẫu)
6. [Phần 4: Bảng Hiệu Chỉnh Ngoại Lệ & Pháp Y Dữ Liệu (`market_data_corrections_and_exceptions.csv`)](#phần-4-bảng-hiệu-chỉnh-ngoại-lệ--pháp-y-dữ-liệu-market_data_corrections_and_exceptionscsv)
   - [4.1. Cấu Trúc Schema Bảng Corrections](#41-cấu-trúc-schema-bảng-corrections)
   - [4.2. Hồ Sơ Pháp Y Chi Tiết 13 Sự Kiện (CORR_001 đến CORR_013)](#42-hồ-sơ-pháp-y-chi-tiết-13-sự-kiện-corr_001-đến-corr_013)
   - [4.3. Bảng Đối Chiếu Thống Kê Trước & Sau Hiệu Chỉnh Dữ Liệu](#43-bảng-đối-chiếu-thống-kê-trước--sau-hiệu-chỉnh-dữ-liệu)
7. [Phần 5: Quy Tắc Vận Hành & Khuyến Nghị Sử Dụng Mô Hình (Best Practices)](#phần-5-quy-tắc-vận-hành--khuyến-nghị-sử-dụng-mô-hình-best-practices)

---

## 1. TỔNG QUAN KIẾN TRÚC KHO DỮ LIỆU

Kho được chia raw/canonical/adjusted/matrices để truy nguồn và kiểm tra từng bước. Thiết kế giảm một số rủi ro bias; các giới hạn về ngày snapshot, mapping và quality vẫn cần được ghi nhận.

```
[iShares Russell 1000 Snapshots]      [QuantConnect LEAN Raw Exports]      [Raw Corporate Actions]
(28 Báo cáo PDF 2000-2026)             (10 Batch ZIPs 1998-2026)            (Splits & Cash Divs)
             │                                     │                                 │
             ▼                                     ▼                                 ▼
[data/raw/universe/by_year/]          [Tier 1 OHLCV Warehouse]             [corporate_actions/]
(russell1000_pit_by_year.json)        (13,147,389 dòng x 9 cột)            (splits & divs CSV)
             │                                     │                                 │
             │               ┌─────────────────────┴─────────────────────────────────┘
             │               ▼
             │      [Step 2A & 3B: Identity Audit, Reverse Splits Injection & Continuous Adjustment]
             │      - Khử trùng 796,602 bản ghi trùng lặp từ 256 cặp alias
             │      - Nối mượt 752 mã placeholder ' 2T' vào SID vĩnh viễn (gap <= 10d)
             │      - Tích hợp 5 ca Reverse Splits bị thiếu (CORR_001 - CORR_005)
             │      - Cách ly 4 ca Spin-offs (CORR_006 - CORR_009) & 4 ca Bad Ticks (CORR_010 - CORR_013)
             │      - Tính Cumulative Split Factor float64 không làm tròn (np.searchsorted)
             │               │
             │               ▼
             │      [Tier 2 Adjusted Price Warehouse]
             │      (12,247,081 dòng x 25 cột - 484.2 MB Parquet ZSTD-7)
             │      - Khóa chính (date, canonical_sid) 100% Unique
             │               │
             └───────────────┼────────────────────────────────────────┐
                             ▼                                        ▼
             [Step 4: 2D Matrices Engine]             [Step 4: Segment-Level PIT Mask Engine]
             - 17 Ma trận giá, khối lượng,            - Phân rã 3,711 SIDs thành từng khoảng hiệu lực
               lợi suất & cờ kiểm toán                - Mask 1: Point-In-Time Membership Mask
               (7,252 ngày x 3,711 SIDs)              - Mask 2: Tradability & Liquidity Mask
                             │                        - Mask 3: Supervised Learning Training Label Mask
                             └────────────────────────┬───────────────┘
                                                      ▼
                                       [data/processed/matrices/]
                                       - 26 Tệp Ma Trận & Masks Chuẩn Hóa
                                       - 0 Look-ahead leakage tại ranh giới 2023-12-29
```

---

## PHẦN 0: NGUỒN DỮ LIỆU THÔ (RAW DATA SOURCES)

### 0.1. Universe theo năm

- Nguồn parser: `data/raw/universe/raw_universe/`, gồm 27 file theo năm (PDF/CSV/JSON/XML-XLS), không phải 28 PDF.
- Output JSON năm trong `by_year/`, JSON tổng hợp `russell1000_pit_by_year.json` và CSV tổng hợp/extraction report.
- Nguồn có tài liệu chỉ số và holdings ETF; không tự coi mọi holdings là danh sách chính thức chỉ số.
- Quy ước áp dụng [01/07/Y,30/06/Y+1] là xấp xỉ nghiên cứu, chưa xác minh ngày hiệu lực chính thức mỗi năm. Xem [source inventory](reports/data_pipeline/universe_source_inventory.csv), đặc biệt ngày ứng viên trong nguồn 2026 muộn hơn tháng 7.
- Extraction report hiện ghi source_file/source_type/số ticker/khoảng áp dụng, không có chứng nhận độ chính xác trích xuất 100% hoặc coverage thị trường 99,42%.

### 0.2. Nến Raw trong 10 ZIP

- Input: `data/raw/market_data/russell_market_batch_01_of_10.zip` đến batch 10.
- Mỗi ZIP hiện có 29 CSV: `raw/year=YYYY/batch_XX_of_10.csv`; ba audit: `audit/batch_XX_of_10_status.csv`, `_identity.csv`, `_summary.json`.
- Raw columns: date, original_ticker, qc_ticker, sid, open, high, low, close, volume.
- SID được coi là khóa định danh nguồn; không suy base/độ dài/ý nghĩa ngày từ chuỗi trong tài liệu này. Ticker không phải khóa vĩnh viễn.
- Script 03 hợp nhất status/identity vào thư mục processed; summary giữ trong ZIP phục vụ đối chiếu metadata.

### 0.3. Corporate actions

- CSV nguồn hiện đặt trong `data/processed/constituents_market_data/corporate_actions/`; vị trí này không có nghĩa nội dung đã được pipeline điều chỉnh.
- Splits dùng date, original_ticker, symbol/sid, split_factor, reference_price; dividends dùng dividend_amount theo schema export thực tế.
- Factor giá S: split 2-for-1 dùng 0,5; reverse 1-for-10 dùng 10. CF nhân trực tiếp các S sau ngày t, không nghịch đảo lần nữa.
- Code 06 lọc reference_price>0 (4.788→2.391 bản ghi), thêm 5 overrides, audit 2.396. Đây là quy tắc hiện hành, cần metadata/split_type nguồn nếu muốn xác minh phân loại đầy đủ.
- Xem [báo cáo corporate actions](reports/data_pipeline/step3_corporate_actions_report.md).

### 0.4. Empty ticker resolution

`data/raw/market_data/empty_ticker_final_resolution.csv` là kết quả kiểm tra trước export nếu có. Không tự gọi là bảng sửa lỗi ticker rỗng hoặc phân giải CUSIP đã xác minh. Đối chiếu status trong ZIP và coverage kho cuối; kết quả scan sơ bộ không thay thế audit cuối.

---

## PHẦN 1: KHO DỮ LIỆU NẾN THÔ TIER 1 (TIER 1 OHLCV WAREHOUSE)

### Thông Tin Tổng Quan Tệp Tin
- **Tên tệp**: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet`
- **Kích thước lưu trữ**: 407.9 MB (Nén PyArrow Snappy)
- **Tổng số bản ghi**: 13,147,389 dòng
- **Tổng số trường dữ liệu**: 9 cột
- **Phạm vi thời gian**: 1998-01-02 đến 2026-10-30 (7,252 phiên giao dịch NYSE)
- **Tổng số Ticker duy nhất**: 4,008 Tickers
- **Tổng số SID thô duy nhất**: 4,675 SIDs
- **Đặc điểm chất lượng**: 0 giá trị khuyết thiếu (0 NaN) trên toàn bộ 9 cột.

### Bảng Đặc Tả Chi Tiết 9 Cột Tier 1

#### 1. `date`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `date` |
| **Kiểu dữ liệu** | `timestamp[us]` (PyArrow) / `datetime64[ns]` (Pandas) |
| **Đơn vị tính** | Thời gian (Lịch phiên giao dịch thị trường chứng khoán Mỹ) |
| **Ý nghĩa kinh tế** | Ngày giao dịch chính thức của phiên đóng cửa thị trường theo lịch sở giao dịch chứng khoán New York (NYSE). Mốc thời gian được chuẩn hóa về 00:00:00 UTC của ngày làm việc đó. |
| **Công thức** | Trích xuất trực tiếp từ cột `date` của dữ liệu xuất QuantConnect LEAN Daily Bars. |
| **Ý nghĩa NaN** | Tuyệt đối không chứa NaN (0 dòng NaN). Mỗi dòng dữ liệu bắt buộc phải gắn liền với một phiên giao dịch cụ thể. |
| **Xử lý biên** | Bao gồm các phiên đóng cửa sớm theo thông lệ thị trường (ví dụ phiên sau Lễ Tạ Ơn, phiên đêm Giáng Sinh đóng cửa lúc 13:00 EST). Không bao gồm các ngày thị trường đóng cửa đột xuất (như 11/09/2001 đến 14/09/2001 do khủng bố, 29/10/2012 đến 30/10/2012 do siêu bão Sandy). |

#### 2. `original_ticker`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `original_ticker` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Ký hiệu định danh (Dimensionless / Ticker String) |
| **Ý nghĩa kinh tế** | Mã ký hiệu cổ phiếu nguyên bản (Point-In-Time Ticker) được ghi nhận trong danh mục iShares Russell 1000 tại kỳ tái cơ cấu gần nhất. Đây là mã được các nhà đầu tư và chuyên viên giao dịch sử dụng để đặt lệnh trên bảng điện tử tại thời điểm lịch sử đó. |
| **Công thức** | Kế thừa nguyên vẹn từ tệp JSON bóc tách danh mục `by_year/russell1000_{YYYY}.json`. |
| **Ý nghĩa NaN** | Không có NaN (0 dòng). |
| **Xử lý biên** | Chứa các ký tự đặc biệt đại diện cho các lớp cổ phiếu như dấu chấm (`BRK.B`, `BF.B`), dấu gạch chéo (`JW/A`), hoặc các mã cổ phiếu đã bị đổi tên nhiều lần trong lịch sử (như `AAPL`, `GOOG`, `FB` -> `META`). |

#### 3. `qc_ticker`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `qc_ticker` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Ký hiệu định danh (Dimensionless / QuantConnect Symbol String) |
| **Ý nghĩa kinh tế** | Mã ký hiệu do máy chủ QuantConnect LEAN phân giải tại thời điểm xuất dữ liệu. Thông thường mã này trùng với `original_ticker`, nhưng có thể phản ánh ký hiệu hiện đại hóa của QuantConnect để truy vấn cơ sở dữ liệu nội bộ. |
| **Công thức** | Trích xuất từ trường `qc_ticker` trong batch export của QuantConnect API. |
| **Ý nghĩa NaN** | Không có NaN (0 dòng). |
| **Xử lý biên** | Trường hợp các mã có đuôi lớp cổ phiếu phức tạp, QuantConnect chuẩn hóa thành chuỗi chuẩn không dấu cách hoặc ký tự thay thế. |

#### 4. `sid`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `sid` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Mã định danh cơ sở 36 (12-char Alphanumeric Base-36 SID) |
| **Ý nghĩa kinh tế** | Mã định danh chứng khoán độc nhất của nền tảng QuantConnect LEAN (Security Identifier). Mỗi SID đại diện cho một hợp đồng vốn cổ phần cụ thể, giải quyết triệt để vấn đề Ticker Reuse (một mã ticker được sàn tái sử dụng cho một công ty hoàn toàn mới sau nhiều năm). |
| **Công thức** | Do LEAN Security Cache sinh ra: bao gồm mã Ticker ban đầu kèm chuỗi hash 12 ký tự (ví dụ: `AAPL R735QTJ8XC9X`). |
| **Ý nghĩa NaN** | Không có NaN (0 dòng). |
| **Xử lý biên** | Tồn tại 846 mã mang hậu tố ` 2T` (Transient Identifier) do cơ chế lưu tạm của QuantConnect đối với các thực thể trong giai đoạn chuyển giao hoặc IPO. Các mã ` 2T` này sẽ được thẩm định và xử lý tại Step 2A. |

#### 5. `open`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `open` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá khớp lệnh đầu tiên trong phiên giao dịch chính quy (09:30 EST) của cổ phiếu, chưa qua bất kỳ sự điều chỉnh chia tách hay cổ tức nào (Raw Unadjusted Price). |
| **Công thức** | Mức giá khớp mở cửa thực tế ghi nhận bởi cơ sở dữ liệu hợp nhất các sàn (Consolidated Tape Association - CTA). |
| **Ý nghĩa NaN** | Không chứa NaN (0 dòng). |
| **Xử lý biên** | Phải thỏa mãn điều kiện kinh tế: $open > 0$. Đối với các cổ phiếu giá thấp (Penny stocks trước khi bị loại rổ), giá mở cửa có thể tiệm cận $0.01. Không làm tròn. |

#### 6. `high`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `high` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Mức giá khớp lệnh cao nhất trong phiên giao dịch chính quy (09:30 - 16:00 EST), chưa qua điều chỉnh. |
| **Công thức** | $\max_{t \in \text{session}} (P_t)$ trên dữ liệu tick của sàn. |
| **Ý nghĩa NaN** | Không chứa NaN (0 dòng). |
| **Xử lý biên** | Bắt buộc tuân thủ bất đẳng thức trọng yếu: $high \ge \max(open, close, low)$. Mọi vi phạm bất đẳng thức này đều là lỗi dữ liệu nguồn. |

#### 7. `low`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `low` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Mức giá khớp lệnh thấp nhất trong phiên giao dịch chính quy, chưa qua điều chỉnh. |
| **Công thức** | $\min_{t \in \text{session}} (P_t)$ trên dữ liệu tick của sàn. |
| **Ý nghĩa NaN** | Không chứa NaN (0 dòng). |
| **Xử lý biên** | Bắt buộc tuân thủ bất đẳng thức: $low \le \min(open, close, high)$ và $low > 0$. |

#### 8. `close`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `close` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá khớp lệnh đóng cửa chính thức (Official Closing Cross Price lúc 16:00 EST) trên sàn giao dịch niêm yết chính (Primary Exchange: NYSE hoặc NASDAQ), chưa điều chỉnh. Mức giá này dùng để định giá danh mục của các quỹ đầu tư tại cuối ngày. |
| **Công thức** | Giá khớp lệnh phiên Closing Auction trên NYSE/NASDAQ. |
| **Ý nghĩa NaN** | Không chứa NaN (0 dòng). |
| **Xử lý biên** | Giá đóng cửa thô có thể biến thiên mạnh tại các ngày chia tách lớn hoặc sự kiện chia tách ngược trước khi điều chỉnh. |

#### 9. `volume`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `volume` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Số lượng cổ phiếu (Shares) |
| **Ý nghĩa kinh tế** | Tổng số lượng cổ phần của công ty được mua bán trao tay qua các sàn giao dịch hợp nhất trong khung giờ giao dịch chính quy của ngày. |
| **Công thức** | $\sum \text{shares}_{\text{trade}}$ trong toàn bộ các giao dịch hợp lệ của phiên. |
| **Ý nghĩa NaN** | Không chứa NaN (0 dòng). |
| **Xử lý biên** | $volume \ge 0$. Các phiên có $volume = 0$ biểu thị ngày giao dịch bị ngừng khớp lệnh (Trading Halt), đình chỉ giao dịch tạm thời (Suspension), hoặc cổ phiếu hoàn toàn mất thanh khoản. Các phiên này sẽ bị loại khỏi mẫu huấn luyện tại tầng Tradability Mask. |

---

## PHẦN 2: KHO DỮ LIỆU GIÁ ĐIỀU CHỈNH TIER 2 (TIER 2 ADJUSTED PRICE WAREHOUSE)

### Thông Tin Tổng Quan Tệp Tin
- **Tên tệp**: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet`
- **Kích thước lưu trữ**: 484.2 MB (Nén Zstandard cấp độ 7 — ZSTD Level 7)
- **Tổng số bản ghi**: 12,247,081 dòng
- **Tổng số trường dữ liệu**: Đúng 25 cột (100% tài liệu hóa đầy đủ)
- **Phạm vi thời gian**: 1998-01-02 đến 2026-10-30 (7,252 phiên giao dịch NYSE)
- **Tổng số Canonical SID duy nhất**: Đúng 3,711 SIDs
- **Độ trùng lặp khóa chính `(date, canonical_sid)`**: Đúng 0 dòng trùng (100% Unique Primary Key)
- **Độ chính xác số thực**: Giữ nguyên chuẩn IEEE 754 Float64 (Không làm tròn trước khi tính Return).

### Đặc Tả Chi Tiết 25 Cột Dữ Liệu

#### 1. `date`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `date` |
| **Kiểu dữ liệu** | `timestamp[us]` (PyArrow) / `datetime64[ns]` |
| **Đơn vị tính** | Thời gian (YYYY-MM-DD 00:00:00 UTC) |
| **Ý nghĩa kinh tế** | Ngày định giá chính thức của phiên giao dịch NYSE. Là trục thời gian chuẩn hóa để đồng bộ hóa chéo (Cross-sectional synchronization) giữa 3,711 cổ phiếu. |
| **Công thức** | Kế thừa từ Tier 1 sau khi deduplicate danh tính. |
| **Ý nghĩa NaN** | 0 dòng NaN (100% có ngày hợp lệ). |
| **Xử lý biên** | Trục ngày kéo dài liên tục qua 7,252 phiên giao dịch từ 02/01/1998 đến 30/10/2026. |

#### 2. `canonical_sid`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `canonical_sid` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Mã định danh chứng khoán chính quy (Canonical Security Identifier) |
| **Ý nghĩa kinh tế** | Mã định danh thực thể chứng khoán tối cao đã qua kiểm toán danh tính tại Step 2A. Khắc phục triệt để hiện tượng phân mảnh dữ liệu: loại bỏ 796,602 lượt quan sát dư thừa do trùng alias, nối theo policy (stitch) 752 mã tạm ` 2T` vào SID vĩnh viễn với khoảng cách gián đoạn $\le 10$ ngày, và giữ độc lập 94 mã 2T có khoảng cách thời gian lớn nhằm ngăn chặn hợp nhất nhầm các công ty khác nhau. |
| **Công thức** | Ánh xạ từ `sid` thô qua từ điển `canonical_security_mapping.csv`. |
| **Ý nghĩa NaN** | 0 dòng NaN (100% có mã hợp lệ trong tập 3,711 Canonical SIDs). |
| **Xử lý biên** | Cùng với `date`, tạo thành Khóa chính phức hợp (Composite Primary Key) duy nhất tuyệt đối của toàn bộ kho dữ liệu. |

#### 3. `original_ticker`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `original_ticker` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Chuỗi ký tự mã giao dịch (Ticker String) |
| **Ý nghĩa kinh tế** | Ký hiệu cổ phiếu niêm yết tại thời điểm quan sát. Cho phép đối chiếu lịch sử với báo cáo phân tích, hồ sơ pháp lý SEC Form 8-K/10-K và hệ thống giao dịch thực tế. |
| **Công thức** | Đồng bộ từ báo cáo thành viên rổ Russell 1000. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Phản ánh hiện tượng Ticker Reuse: một mã ticker (ví dụ `MIR`, `INFO`) có thể trỏ về các `canonical_sid` khác nhau tại các giai đoạn lịch sử khác nhau khi các doanh nghiệp lần lượt giải thể và thành lập mới. |

#### 4. `qc_ticker`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `qc_ticker` |
| **Kiểu dữ liệu** | `large_string` / `object` |
| **Đơn vị tính** | Chuỗi ký tự QuantConnect LEAN Symbol |
| **Ý nghĩa kinh tế** | Mã ký hiệu cổ phiếu do QuantConnect LEAN phân giải, dùng để liên kết ngược với các dịch vụ dữ liệu phụ trợ của LEAN (như tin tức, dữ liệu tâm lý thị trường, dữ liệu vi mô). |
| **Công thức** | Trích xuất từ tệp Tier 1. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Giữ nguyên để phục vụ truy vấn ngược (Reverse Lookup). |

#### 5. `open`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `open` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá mở cửa phiên giao dịch thô chưa điều chỉnh. Thống kê thực nghiệm: Min = $0.01, Trung vị (Median) = $32.33, Max = $9,999.00. |
| **Công thức** | Giá khớp phiên mở cửa thô từ CTA tape. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Được dùng kết hợp với `close` để tính toán tỷ suất sinh lời trong phiên (Intraday Return) tại Step 7. |

#### 6. `high`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `high` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá cao nhất phiên thô chưa điều chỉnh. Thống kê thực nghiệm: Min = $0.0148, Trung vị = $32.83, Max = $199,999.99. |
| **Công thức** | Giá khớp cao nhất trong phiên. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Dùng để tính toán biên độ dao động giá trong ngày (High-Low Price Range). |

#### 7. `low`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `low` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá thấp nhất phiên thô chưa điều chỉnh. Thống kê thực nghiệm: Min = $0.01, Trung vị = $31.84, Max = $9,810.00. |
| **Công thức** | Giá khớp thấp nhất trong phiên. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Bắt buộc thỏa mãn $low > 0$. |

#### 8. `close`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `close` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ (USD) |
| **Ý nghĩa kinh tế** | Giá đóng cửa chính thức thô chưa điều chỉnh. Thống kê thực nghiệm: Min = $0.01, Trung vị = $32.33, Max = $9,924.40. |
| **Công thức** | Giá khớp phiên Closing Cross của sàn niêm yết chính. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Dùng để nhân với `cumulative_split_factor` ra giá điều chỉnh chia tách. |

#### 9. `volume`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `volume` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Số lượng cổ phiếu (Shares) |
| **Ý nghĩa kinh tế** | Khối lượng cổ phiếu giao dịch thô trong ngày. Thống kê thực nghiệm: Min = 0.0, Trung vị = 695,984.0, Max = 2,782,162,281.0 cổ phiếu. |
| **Công thức** | Tổng khối lượng khớp lệnh hợp lệ trong phiên chính quy. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Khi $volume = 0$, mã cổ phiếu được xem là mất thanh khoản hoặc bị ngừng giao dịch trong phiên đó. |

#### 10. `cumulative_split_factor`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `cumulative_split_factor` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Hệ số nhân tỷ lệ (Backward Adjustment Multiplier / Dimensionless Ratio) |
| **Ý nghĩa kinh tế** | Hệ số chia tách dồn tích lùi liên tục theo thời gian (Backward Cumulative Split Factor) $CF_{i,t}$. Được thiết kế để quy đổi toàn bộ mức giá trong quá khứ về mặt bằng tương đương với 1 cổ phiếu tại thời điểm hiện tại mà không làm sai lệch quy mô kinh tế của danh mục. Hệ số này được tính toán độc lập với việc ngày xảy ra sự kiện chia tách có nến giao dịch hay không (Continuous Event Calendar qua thuật toán `np.searchsorted`). Tích hợp đầy đủ 5 sự kiện Reverse Splits được bổ sung từ corrections của dự án (CORR_001 đến CORR_005). |
| **Công thức** | Cho chuỗi sự kiện chia tách với hệ số $s_{i,\tau}$ tại ngày chốt quyền $\tau$: $$CF_{i,t} = \prod_{\tau > t} s_{i,\tau}$$ Trong đó, tại phiên giao dịch mới nhất $T$, $CF_{i,T} = 1.0$. Với một sự kiện chia tách tỷ lệ 2:1 diễn ra vào ngày $\tau$, hệ số $s = 0.5$, toàn bộ các phiên $t < \tau$ nhận $CF_{i,t} = CF_{i,\tau} \times 0.5$. Với sự kiện chia tách ngược 1:200 của CHK ngày 15/04/2020, $s = 200.0$, toàn bộ các phiên trước đó nhận $CF = CF \times 200.0$. |
| **Ý nghĩa NaN** | 0 dòng NaN (Mặc định 1.0 cho các mã không có sự kiện chia tách). |
| **Xử lý biên** | Giữ nguyên độ chính xác nguyên bản của kiểu số thực Float64, nghiêm cấm làm tròn thập phân để tránh làm sai lệch phép thử đẳng thức lợi suất toán học. |

#### 11. `adj_open`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_open` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ tương đương hiện tại (Split-Adjusted USD) |
| **Ý nghĩa kinh tế** | Giá mở cửa đã được điều chỉnh theo toàn bộ các đợt chia tách và chia tách ngược trong tương lai. Thống kê thực nghiệm: Min = $0.005, Trung vị = $29.30, Max = $11,155,924.64. |
| **Công thức** | $$adj\_open_{i,t} = open_{i,t} \times cumulative\_split\_factor_{i,t}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Không làm tròn 2 chữ số thập phân; bảo toàn tính liên tục vi phân trong mô hình toán học. |

#### 12. `adj_high`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_high` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ tương đương hiện tại (Split-Adjusted USD) |
| **Ý nghĩa kinh tế** | Giá cao nhất trong ngày đã điều chỉnh chia tách. Thống kê thực nghiệm: Min = $0.0077, Trung vị = $29.75, Max = $11,155,924.64. |
| **Công thức** | $$adj\_high_{i,t} = high_{i,t} \times cumulative\_split\_factor_{i,t}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Đảm bảo $adj\_high \ge \max(adj\_open, adj\_close, adj\_low)$. |

#### 13. `adj_low`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_low` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ tương đương hiện tại (Split-Adjusted USD) |
| **Ý nghĩa kinh tế** | Giá thấp nhất trong ngày đã điều chỉnh chia tách. Thống kê thực nghiệm: Min = $0.0002, Trung vị = $28.84, Max = $2,145,684.25. |
| **Công thức** | $$adj\_low_{i,t} = low_{i,t} \times cumulative\_split\_factor_{i,t}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Đảm bảo $adj\_low \le \min(adj\_open, adj\_close, adj\_high)$ và $adj\_low > 0$. |

#### 14. `adj_close`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_close` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ tương đương hiện tại (Split-Adjusted USD) |
| **Ý nghĩa kinh tế** | Giá đóng cửa chính thức đã điều chỉnh chia tách. Đây là chuỗi giá trị cốt lõi bậc nhất của toàn bộ dự án, được sử dụng để xây dựng toàn bộ các đặc trưng động lượng (Momentum), biến động (Volatility) và tính toán lợi suất chuỗi thời gian. Thống kê thực nghiệm: Min = $0.0077, Trung vị = $29.29, Max = $2,228,210.57. |
| **Công thức** | $$adj\_close_{i,t} = close_{i,t} \times cumulative\_split\_factor_{i,t}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Loại bỏ hiện tượng nhảy vọt ảo (Artificial Price Jump) do chia tách gây ra. Trên các mã đã kiểm toán như Apple (AAPL), Nvidia (NVDA), chuỗi giá trở nên trơn tru liên tục qua các ngày chia tách lớn. |

#### 15. `adj_volume`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_volume` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Số lượng cổ phiếu tương đương hiện tại (Split-Adjusted Shares) |
| **Ý nghĩa kinh tế** | Khối lượng giao dịch đã điều chỉnh chia tách. Nhằm đảm bảo nguyên lý bảo toàn tổng giá trị giao dịch bằng tiền (Dollar Volume Invariance): tổng giá trị luân chuyển của cổ phiếu trong ngày không bị thay đổi bởi phép biến đổi chia tách ($adj\_close \times adj\_volume = close \times volume$). Thống kê thực nghiệm: Min = 0.0, Trung vị = 746,559.71, Max = 8,907,086,482.83 cổ phiếu. |
| **Công thức** | $$adj\_volume_{i,t} = \frac{volume_{i,t}}{cumulative\_split\_factor_{i,t}}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Dùng để tính toán hệ số thanh khoản Amihud Illiquidity và chỉ số Volume Turnover tại Step 7. |

#### 16. `dividend_amount`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `dividend_amount` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ trên mỗi cổ phiếu thô (USD per Raw Share) |
| **Ý nghĩa kinh tế** | Giá trị cổ tức bằng tiền mặt (Ordinary & Special Cash Dividends) được doanh nghiệp phân phối trên mỗi cổ phiếu thô vào ngày giao dịch không hưởng quyền (Ex-Dividend Date). Thống kê thực nghiệm: Min = $0.0, Trung vị = $0.0 (do đại đa số các ngày trong năm không chia cổ tức), Max = $140.25/cổ phiếu. |
| **Công thức** | Ghép nối từ tệp `russell1000_dividends_1998_2026.csv` theo cặp `(canonical_sid, date)`. |
| **Ý nghĩa NaN** | 0 dòng NaN (Mặc định điền 0.0 cho 12,060,935 ngày không có sự kiện cổ tức). |
| **Xử lý biên** | Bao gồm cả các khoản cổ tức đặc biệt quy mô lớn (như đợt chia cổ tức đặc biệt $32.00/cổ phiếu của Microsoft năm 2004). |

#### 17. `adj_dividend`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `adj_dividend` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Đô la Mỹ tương đương hiện tại trên mỗi cổ phiếu (Adjusted USD per Share) |
| **Ý nghĩa kinh tế** | Cổ tức tiền mặt đã được điều chỉnh chia tách về mặt bằng số lượng cổ phiếu hiện tại, phục vụ cho việc tính toán Lợi suất Tổng (Total Return). Thống kê thực nghiệm: Min = $0.0, Trung vị = $0.0, Max = $30,757.55/cổ phiếu. |
| **Công thức** | $$adj\_dividend_{i,t} = dividend\_amount_{i,t} \times cumulative\_split\_factor_{i,t}$$ |
| **Ý nghĩa NaN** | 0 dòng NaN (Điền 0.0 cho các ngày không có cổ tức). |
| **Xử lý biên** | Giữ nguyên float64 không làm tròn để đảm bảo đẳng thức toán học $TotalReturn = DailyReturn + DividendYield$. |

#### 18. `daily_return`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `daily_return` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Tỷ lệ phần trăm biến động giá (Dimensionless Ratio / Decimal Return) |
| **Ý nghĩa kinh tế** | Tỷ suất sinh lời theo giá đóng cửa điều chỉnh chia tách (Split-Adjusted Price Return) giữa phiên hiện tại $t$ và phiên trước đó $t-1$. Phản ánh sự thay đổi giá trị tài sản thuần của nhà đầu tư chỉ xuất phát từ biến động giá trên thị trường. Thống kê thực nghiệm trên tập Development sạch: Quan sát hợp lệ = 5,610,691 phiên-mã; Trung bình (Mean) = +0.0379%/ngày; Trung vị (Median) = +0.0355%/ngày; Biến động ngày (Daily Volatility) = 2.6530% (độ lệch chuẩn gộp stock-day, không phải volatility danh mục); Hệ số bất đối xứng (Skewness) = +0.5634; Hệ số nhọn vượt chuẩn (Excess Kurtosis) = 66.88 (phân phối đuôi dày nhưng hợp lý, giảm các bất thường đã được ghi nhận ở pipeline trước); Tối thiểu = -94.97% (biến cố sụp đổ thật có hồ sơ SEC); Tối đa = +227.87% (quan sát MFA còn cần đối chiếu độc lập mức giá và diễn giải sự kiện). |
| **Công thức** | $$daily\_return_{i,t} = \frac{adj\_close_{i,t} - adj\_close_{i,t-1}}{adj\_close_{i,t-1}}$$ |
| **Ý nghĩa NaN** | NaN xuất hiện theo coverage/quality của phiên bản dữ liệu (chiếm 0.0306%): bao gồm đúng 3,711 phiên giao dịch đầu tiên của mỗi `canonical_sid` (không có phiên liền trước $t-1$ để tính return), cộng với đúng 31 phiên bị cách ly có chủ đích bởi tầng Quality Flags và Spin-offs (CORR_006 đến CORR_013). |
| **Xử lý biên** | Khi một mã cổ phiếu bị cách ly do nến lỗi hoặc chia tách công ty con, giá trị return được ép cưỡng bức thành NaN để bảo vệ thuật toán học máy khỏi bị tối ưu hóa theo các số liệu rác. |

#### 19. `total_return`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `total_return` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Tỷ lệ phần trăm tổng lợi suất (Decimal Total Return Ratio) |
| **Ý nghĩa kinh tế** | Lợi suất ngày cộng phần dividend theo ex-date và cùng đơn vị giá điều chỉnh. Chưa mô phỏng payment date, thuế, tái đầu tư thực tế hoặc mọi phân phối tài sản như spin-off. |
| **Công thức** | $$total\_return_{i,t} = \frac{adj\_close_{i,t} + adj\_dividend_{i,t} - adj\_close_{i,t-1}}{adj\_close_{i,t-1}} = daily\_return_{i,t} + \frac{adj\_dividend_{i,t}}{adj\_close_{i,t-1}}$$ |
| **Ý nghĩa NaN** | Có thể thiếu do phiên đầu, gap hoặc quality flags; đối chiếu artifact tại lần chạy, không áp số đếm của phiên bản cũ. |
| **Xử lý biên** | Đối chiếu đẳng thức số học trong audit theo phạm vi đã ghi; không chứng minh mọi dividend/nguồn giá đã được xác minh độc lập. |

#### 20. `trading_session_gap`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `trading_session_gap` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Số phiên giao dịch sàn NYSE (Trading Sessions) |
| **Ý nghĩa kinh tế** | Số lượng phiên giao dịch chính thức của sàn NYSE trôi qua giữa ngày quan sát hiện tại $t$ và ngày giao dịch có dữ liệu trước đó của mã cổ phiếu. Đây là thước đo vi cấu trúc kiểm toán để phát hiện các mã bị đình chỉ giao dịch kéo dài nhiều ngày hoặc bị thiếu hụt dữ liệu nguồn. Thống kê thực nghiệm: Trung vị = 1.0; Đúng 12,243,116 phiên đạt chuẩn liên tục (Gap = 1 session, chiếm 99.97%); 3,965 phiên có khoảng cách bị ngắt quãng do tạm ngừng giao dịch. |
| **Công thức** | Đo lường theo chỉ số phiên giao dịch NYSE chính thức: $$trading\_session\_gap_{i,t} = idx_{NYSE}(date_{i,t}) - idx_{NYSE}(date_{i,t-1})$$ |
| **Ý nghĩa NaN** | Có đúng 3,711 dòng NaN (phiên giao dịch đầu tiên của mỗi mã). |
| **Xử lý biên** | Các phiên có $trading\_session\_gap > 1$ biểu thị cổ phiếu bị đình chỉ giao dịch nhiều phiên liên tiếp, sẽ bị loại khỏi mặt nạ Tradability Mask do không phản ánh lợi suất 1 ngày thực sự. |

#### 21. `is_consecutive_session`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `is_consecutive_session` |
| **Kiểu dữ liệu** | `bool` (boolean) |
| **Đơn vị tính** | Cờ logic nhị phân (Binary Flag: True / False) |
| **Ý nghĩa kinh tế** | Cờ kiểm toán xác nhận phiên giao dịch hiện tại có nối tiếp ngay lập tức phiên giao dịch trước đó của thị trường hay không. Thống kê thực nghiệm: True = 12,243,116 dòng (99.97%); False = 3,965 dòng (0.03%). |
| **Công thức** | $$is\_consecutive\_session_{i,t} = (trading\_session\_gap_{i,t} == 1.0)$$ |
| **Ý nghĩa NaN** | 0 dòng NaN (Mặc định điền False cho 3,711 phiên đầu tiên và các phiên gián đoạn). |
| **Xử lý biên** | Điều kiện tiên quyết để đưa dữ liệu vào huấn luyện mô hình dự đoán lợi suất 1 ngày. |

#### 22. `calendar_day_gap`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `calendar_day_gap` |
| **Kiểu dữ liệu** | `double` (float64) |
| **Đơn vị tính** | Ngày theo lịch dương (Calendar Days) |
| **Ý nghĩa kinh tế** | Số ngày dương lịch trôi qua giữa hai phiên giao dịch. Cho phép phân biệt giữa các phiên cách nhau qua đêm trong tuần (Gap = 1 ngày), qua kỳ nghỉ cuối tuần thông thường (Gap = 3 ngày: từ thứ Sáu sang thứ Hai), hoặc qua các kỳ nghỉ lễ dài ngày (Gap = 4 ngày). |
| **Công thức** | $$calendar\_day\_gap_{i,t} = (date_{i,t} - date_{i,t-1}).days$$ |
| **Ý nghĩa NaN** | Có đúng 3,711 dòng NaN (phiên đầu tiên). |
| **Xử lý biên** | Hỗ trợ phân tích hiệu ứng ngày trong tuần (Day-of-the-week Effect) và hiệu ứng kỳ nghỉ lễ (Holiday Effect) trong các bài toán định lượng nâng cao. |

#### 23. `is_bad_data_period`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `is_bad_data_period` |
| **Kiểu dữ liệu** | `bool` (boolean) |
| **Đơn vị tính** | Cờ logic chất lượng (Data Quality Quarantine Flag) |
| **Ý nghĩa kinh tế** | Cờ đánh dấu các phiên giao dịch nằm trong khoảng thời gian bị ô nhiễm bởi lỗi chèn nến rác của nhà cung cấp dữ liệu hoặc xung đột mã cổ phiếu ưu đãi thanh khoản thấp (Ticker Collision). Thống kê thực nghiệm: True = đúng 23 dòng; False = 12,247,058 dòng. Bao gồm 4 vụ việc pháp y chấn động: MKL (17 phiên nến $26.10 rác), SABR (1 phiên print $0.50), LOW (6 phiên chạm mã preferred $0.60), CPTH (khoảng halt $1.00 - $3.78). |
| **Công thức** | Kích hoạt tự động dựa trên bảng hồ sơ pháp y `market_data_corrections_and_exceptions.csv` với các lớp `QUALITY_FLAG_BAD_TICK` và `QUALITY_FLAG_COLLISION`. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Khi $is\_bad\_data\_period = True$, hệ thống đồng thời tự động cách ly thêm 1 phiên giao dịch ngay liền sau khoảng lỗi (Recovery Session) để triệt tiêu bước nhảy hồi phục nhân tạo. |

#### 24. `is_spinoff_discontinuity`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `is_spinoff_discontinuity` |
| **Kiểu dữ liệu** | `bool` (boolean) |
| **Đơn vị tính** | Cờ logic chia tách công ty (Corporate Spinoff Quarantine Flag) |
| **Ý nghĩa kinh tế** | Cờ đánh dấu các phiên giao dịch ghi nhận bước sụt giảm giá nghiêm trọng do doanh nghiệp thực hiện tách công ty con (Subsidiary Spin-off Distribution) mà dữ liệu giá đơn lẻ không phản ánh giá trị cổ phiếu công ty con được nhận. Thống kê thực nghiệm: True = đúng 4 dòng; False = 12,247,077 dòng. Bao gồm: KSU (tách Stilwell Financial ngày 13/07/2000), SSP (tách Scripps Networks ngày 01/07/2008), COMS (tách Palm Inc ngày 28/07/2000), PENN (tách quỹ REIT GLPI ngày 04/11/2013). |
| **Công thức** | Kích hoạt tại ngày hiệu lực tách công ty con dựa trên hồ sơ SEC Form 8-K trong bảng `market_data_corrections_and_exceptions.csv`. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Bảo vệ giá trị kinh tế thực: cổ đông không hề bị mất tiền, nhưng giá cổ phiếu công ty mẹ rớt từ 70% đến 96% do tài sản đã được chuyển sang cổ phiếu mới. Cờ này đảm bảo mô hình không hiểu nhầm đây là một vụ phá sản. |

#### 25. `quality_flag`
| Thuộc tính | Giá trị chi tiết |
|:---|:---|
| **Tên cột** | `quality_flag` |
| **Kiểu dữ liệu** | `large_string` / `category` |
| **Đơn vị tính** | Nhãn phân loại chất lượng dữ liệu (Quality Classification Label) |
| **Ý nghĩa kinh tế** | Chuỗi văn bản phân loại trạng thái kiểm toán vi mô của từng bản ghi dữ liệu giá, cung cấp khả năng truy vết và kiểm toán pháp lý nhanh chóng. Thống kê thực nghiệm phân bổ danh mục: <br>• `CLEAN`: 12,247,054 dòng (99.9998%) — Dữ liệu sạch, hoàn toàn tin cậy; <br>• `QUALITY_FLAG_BAD_TICK`: 17 dòng — Nến lỗi do nhà cung cấp dữ liệu chèn sai giá; <br>• `QUALITY_FLAG_COLLISION`: 6 dòng — Xung đột mã với cổ phiếu ưu đãi hoặc chứng quyền; <br>• `SPINOFF_DISCONTINUITY`: 4 dòng — Gián đoạn giá do tách công ty con. |
| **Công thức** | Gán nhãn trực tiếp từ cột `correction_layer` của bảng kiểm toán pháp y. |
| **Ý nghĩa NaN** | 0 dòng NaN. |
| **Xử lý biên** | Là điều kiện lọc nhanh để loại bỏ dữ liệu bất thường trong các pipeline kiểm toán hạ nguồn. |

---

## PHẦN 3: HỆ THỐNG 17 MA TRẬN 2D & 3 LỚP PIT MASKS (`data/processed/matrices/`)

### 3.1. Lưới Tọa Độ Không-Thời Gian Chính Quy
Toàn bộ các ma trận 2D trong thư mục `data/processed/matrices/` đều được cấu trúc trên một lưới tọa độ chính quy đồng nhất:
- **Trục tung (Hàng - Rows / Dates)**: Đúng 7,252 ngày giao dịch NYSE chính thức từ ngày `1998-01-02` đến `2026-10-30` (được lưu tại `matrix_dates_index.parquet`).
- **Trục hoành (Cột - Columns / Constituents)**: Đúng 3,711 Canonical SIDs chính quy (được lưu tại `matrix_columns_sids.parquet`).
- **Tổng số phần tử trên mỗi ma trận**: $7,252 \times 3,711 = 26,912,172$ ô dữ liệu (Cells).
- **Quy ước định dạng tệp**: Lưu dưới định dạng Parquet với thuật toán nén `snappy`. Khi tải qua thư viện PyArrow hoặc Pandas, mỗi ma trận có kích thước `[7252 rows x 3712 columns]` do bao gồm thêm 1 cột chỉ mục `__index_level_0__` hoặc `date`.

### 3.2. Bảng Danh Mục 26 Tệp Ma Trận & Masks

| STT | Tên tệp tin Parquet | Kích thước | Kiểu dữ liệu | Nhóm chức năng | Ý nghĩa giá trị & Công thức | Bước sử dụng trong Pipeline |
|:---:|:---|:---:|:---:|:---:|:---|:---:|
| 1 | `open.parquet` | 7252 x 3712 | `float64` | Giá thô | Giá mở cửa thô $open_{i,t}$ (USD). NaN khi mã không có giao dịch trong phiên. | Step 4, Step 6, Sanity check |
| 2 | `high.parquet` | 7252 x 3712 | `float64` | Giá thô | Giá cao nhất thô $high_{i,t}$ (USD). | Step 4, Step 6, Range check |
| 3 | `low.parquet` | 7252 x 3712 | `float64` | Giá thô | Giá thấp nhất thô $low_{i,t}$ (USD). | Step 4, Step 6, Range check |
| 4 | `close.parquet` | 7252 x 3712 | `float64` | Giá thô | Giá đóng cửa thô chính thức $close_{i,t}$ (USD). | Step 4, Step 6, Corporate Actions Audit |
| 5 | `volume.parquet` | 7252 x 3712 | `float64` | Khối lượng thô | Khối lượng giao dịch thô $volume_{i,t}$ (shares). Điền NaN khi không có nến. | Step 4, Step 6, Dollar Volume Audit |
| 6 | `adj_open.parquet` | 7252 x 3712 | `float64` | Giá điều chỉnh | Giá mở cửa điều chỉnh chia tách: $open \times CF$. Float64 không làm tròn. | Step 6, Step 7 (Intraday Return) |
| 7 | `adj_high.parquet` | 7252 x 3712 | `float64` | Giá điều chỉnh | Giá cao nhất điều chỉnh chia tách: $high \times CF$. | Step 6, Step 7 (52-week High Feature) |
| 8 | `adj_low.parquet` | 7252 x 3712 | `float64` | Giá điều chỉnh | Giá thấp nhất điều chỉnh chia tách: $low \times CF$. | Step 6, Step 7 (Parkinson Volatility) |
| 9 | `adj_close.parquet` | 7252 x 3712 | `float64` | Giá điều chỉnh | Giá đóng cửa điều chỉnh chia tách: $close \times CF$. Chuỗi giá chuẩn mực cao nhất. | Step 6 EDA, Step 7 (Features: ret_1d, ret_5d, ret_20d, ret_60d, ret_252d) |
| 10 | `adj_volume.parquet` | 7252 x 3712 | `float64` | Khối lượng điều chỉnh | Khối lượng cổ phiếu điều chỉnh chia tách: $volume / CF$. Bảo toàn Dollar Volume. | Step 6 EDA, Step 7 (Amihud Illiquidity, Turnover, Volume Ratio) |
| 11 | `cumulative_split_factor.parquet` | 7252 x 3712 | `float64` | Sự kiện | Hệ số chia tách dồn tích lùi liên tục $CF_{i,t}$. Giá trị mặc định 1.0. | Step 4, Step 6, Sanity Identity Test |
| 12 | `adj_dividend.parquet` | 7252 x 3712 | `float64` | Sự kiện | Cổ tức tiền mặt điều chỉnh chia tách. Điền 0.0 cho các phiên không chia cổ tức. | Step 4, Step 6, Total Return Check |
| 13 | `daily_return.parquet` | 7252 x 3712 | `float64` | Lợi suất | Lợi suất giá hàng ngày $(adj\_close_t - adj\_close_{t-1}) / adj\_close_{t-1}$. | Step 6 EDA, Step 7 (Vol Realized, Target Generation) |
| 14 | `total_return.parquet` | 7252 x 3712 | `float64` | Lợi suất | Lợi suất tổng cộng bao gồm cổ tức tái đầu tư. | Step 6 EDA, Step 7 (Alternative Target) |
| 15 | `is_consecutive_session.parquet` | 7252 x 3712 | `bool` | Cờ kiểm toán | True nếu phiên $t$ nối tiếp phiên $t-1$ theo lịch NYSE ($gap = 1$). False nếu gián đoạn. | Step 4, Cấu thành Valid Data Mask |
| 16 | `is_bad_data_period.parquet` | 7252 x 3712 | `bool` | Cờ kiểm toán | True trong khoảng thời gian có nến lỗi/xung đột mã (CORR_010 đến CORR_013). | Step 4, Cấu thành Valid Data Mask |
| 17 | `is_spinoff_discontinuity.parquet` | 7252 x 3712 | `bool` | Cờ kiểm toán | True tại các ngày tách công ty con (CORR_006 đến CORR_009). | Step 4, Cấu thành Valid Data Mask |
| 18 | `membership_mask.parquet` | 7252 x 3712 | `bool` | Mặt nạ PIT Lớp 1 | True nghiêm ngặt trong khoảng hiệu lực thành viên $[start, end]$ của rổ Russell 1000. True cells: 6,333,323. | Step 4, Step 6, Lọc vũ trụ đầu tư |
| 19 | `resolved_membership_mask.parquet` | 7252 x 3712 | `bool` | Mặt nạ PIT Lớp 1 | Phiên bản mở rộng bao gồm mã vĩnh viễn và các phân đoạn nối chuyển tiếp heuristic $\le 10$ ngày. Đồng nhất với `membership_mask.parquet`. | Step 4, Step 6, Phân tích phân đoạn |
| 20 | `strict_membership_mask.parquet` | 7252 x 3712 | `bool` | Mặt nạ PIT Lớp 1 | Phiên bản kiểm toán khắt khe nhất: CHỈ chứa các mã thuộc Cấp 1 (`LEVEL_1_VERIFIED_PERMANENT`), không chứa mã nối heuristic. | Step 4, Đối chiếu độ nhạy vũ trụ |
| 21 | `valid_data_mask.parquet` | 7252 x 3712 | `bool` | Mặt nạ PIT Lớp 2 | Mặt nạ giao dịch & thanh khoản tại ngày $T$. True: 6,311,822 cells (99.66% membership). Thành viên + Giá > 0 + Vol > 0 + Liền kề + Lịch sử $\ge 20$ phiên + Sạch lỗi. | Step 4, Step 6 EDA, Step 7 (Lọc tính toán Features) |
| 22 | `valid_label_mask.parquet` | 7252 x 3712 | `bool` | Mặt nạ PIT Lớp 3 | Mặt nạ nhãn huấn luyện học máy. True: 6,308,873 cells (99.61% membership). Hợp lệ tại $T$ và phiên $T+1$ có giá, vol, return sạch; đã purge ranh giới OOS 2023-12-29. | Step 4, Step 7, Huấn luyện mô hình xếp hạng |
| 23 | `target_next_return.parquet` | 7252 x 3712 | `float64` | Biến mục tiêu | Lợi suất giá ngày mai $r_{i,t+1}$ (shift -1), các ô ngoài `valid_label_mask` bị ép thành NaN. | Step 7 (Tạo nhãn `target_next_rank`), Step 8 Training |
| 24 | `target_next_total_return.parquet` | 7252 x 3712 | `float64` | Biến mục tiêu | Lợi suất tổng ngày mai $total\_r_{i,t+1}$ (shift -1), các ô ngoài `valid_label_mask` là NaN. | Step 7, Step 8 Huấn luyện mục tiêu phụ |
| 25 | `matrix_dates_index.parquet` | 7252 x 1 | `datetime64[us]` | Trục chỉ mục | Danh sách 7,252 ngày giao dịch NYSE chính thức từ 1998-01-02 đến 2026-10-30. Tên cột: `date`. | Step 4-10, Chuẩn hóa chỉ mục hàng |
| 26 | `matrix_columns_sids.parquet` | 3711 x 1 | `string` | Trục chỉ mục | Danh sách 3,711 Canonical SIDs chính quy được sắp xếp theo thứ tự bảng chữ cái. Tên cột: `canonical_sid`. | Step 4-10, Chuẩn hóa chỉ mục cột |

### 3.3. Masks: kho dữ liệu và tính features

- Membership: tập đối tượng đã chọn theo segment mapping tại T; strict/resolved có policy khác nhau. Không tự đồng nhất với toàn bộ source universe chưa phân giải.
- Valid data: membership AND điều kiện close/volume/phiên liên tiếp/20 bars tích lũy/quality. Đây là điều kiện dữ liệu, không chứng nhận khớp lệnh hoặc đủ lookback cho mọi feature.
- Valid label: thêm điều kiện T+1 và purge; có thông tin tương lai, chỉ dành nhãn. `label ⊆ data ⊆ membership` là invariant trong thiết kế masks hiện tại.
- Bar quality: loader tạo từ close dương/có dữ liệu và không bad/spinoff, độc lập membership. Dùng làm sạch input để giữ lịch sử trước ngày gia nhập. Mỗi feature vẫn kiểm tra finite, miền high/low/volume và cửa sổ theo hợp đồng riêng.
- Tính feature trước rồi lọc membership tại output T; không dùng label mask lọc X. RSI có trạng thái seed/reset riêng.

Xem [matrices/masks và ví dụ](reports/data_pipeline/step4_matrices_masks_report.md), [features v1](specifications/features_v1.md).

### 3.4. Cơ Chế Purge Ranh Giới Phát Triển & Ngoài Mẫu
Để tuân thủ tuyệt đối nguyên tắc **Zero Data Snooping**, hệ thống thực hiện cưỡng bức làm sạch (Purging) tại hai mốc ranh giới:
1. **Ranh giới Development / OOS (`2023-12-29`)**:
   - Toàn bộ hàng ngày `2023-12-29` trên `valid_label_mask.parquet` bị cưỡng bức gán giá trị `False` (100% Purged).
   - Tương ứng, toàn bộ hàng ngày `2023-12-29` trên `target_next_return.parquet` và `target_next_total_return.parquet` nhận giá trị `NaN`.
   - **Tác dụng định lượng**: Ngăn chặn hoàn toàn việc mô hình học máy tại phiên cuối cùng của tập phát triển nhìn trộm (Look-ahead Leakage) sang phiên đầu tiên của tập Out-of-Sample (`2024-01-02`).
2. **Phiên Cuối Cùng Của Kho Dữ Liệu (`2026-10-30`)**:
   - Phiên `2026-10-30` không tồn tại phiên giao dịch $T+1$ trong kho dữ liệu, do đó toàn bộ hàng này trên `valid_label_mask` là `False` và target là `NaN`.

---

## PHẦN 4: BẢNG HIỆU CHỈNH NGOẠI LỆ & PHÁP Y DỮ LIỆU (`market_data_corrections_and_exceptions.csv`)

### 4.1. Cấu Trúc Schema Bảng Corrections
Tệp lưu trữ: `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv` gồm đúng 11 cột:
1. `event_id`: Mã định danh sự kiện kiểm toán (`CORR_001` đến `CORR_013`).
2. `source_ticker`: Mã ticker bị ảnh hưởng trong dữ liệu nguồn.
3. `canonical_sid`: Mã Canonical SID tương ứng.
4. `start_date`: Ngày bắt đầu xảy ra sự kiện bất thường (YYYY-MM-DD).
5. `end_date`: Ngày kết thúc ảnh hưởng của sự kiện (YYYY-MM-DD).
6. `correction_layer`: Tầng xử lý trong pipeline kỹ thuật:
   - `CORPORATE_ACTIONS_SPLIT`: Can thiệp vào tầng chia tách trước khi tính toán $CF_{i,t}$.
   - `SPECIAL_CORPORATE_SPINOFF`: Can thiệp vào tầng Quality Flags để cách ly bước nhảy giá tách công ty.
   - `QUALITY_FLAG_BAD_TICK`: Can thiệp vào tầng Quality Flags để cách ly nến lỗi của sàn/nhà cung cấp.
   - `QUALITY_FLAG_COLLISION`: Can thiệp vào tầng Quality Flags để cách ly xung đột mã chứng khoán.
7. `parameter_name`: Tên tham số kỹ thuật được cấu hình (`split_factor`, `quarantine_spinoff_discontinuity`, `quarantine_bad_data_period`, `quarantine_bad_tick`).
8. `parameter_value`: Giá trị tham số đưa vào hệ thống (`200.0`, `10.0`, `7.0`, `3.0`, `5.0`, hoặc `True`).
9. `evidence_source`: Bằng chứng pháp lý đối chiếu độc lập (Hồ sơ SEC Form 8-K, Báo cáo Ủy ban Chứng khoán NYSE/NASDAQ, Băng giá hợp nhất Consolidated Tape).
10. `forensic_explanation`: Bản chất kinh tế và nguyên nhân sâu xa của biến cố ngoại lệ.
11. `action_taken`: Hành động kỹ thuật cụ thể đã thực thi trong mã nguồn pipeline.

---

### 4.2. Corrections và mức bằng chứng

13 dòng trong bảng input chia thành 5 split overrides (CHK, CRC, ADCT, AA, DYN), 4 spin-off bị cách ly (KSU, SSP, COMS, PENN), 4 khoảng nghi dữ liệu lỗi (MKL, SABR, LOW, CPTH). Không phải mọi dòng đều sửa giá hoặc đều có bằng chứng độc lập cùng mức.

`evidence_source` là chuỗi nguồn mà hồ sơ đã ghi, chưa phải chứng minh nhóm đã truy và kiểm tra từng tài liệu. Một số mô tả chưa có URL/accession và chuỗi giá trong forensic ledger bị mất ký tự. Không khẳng định đã đối chiếu Bloomberg/CRSP/NYSE tape khi chưa có artifact truy được. Không suy diễn tên công ty từ ticker CPTH nếu chưa xác minh identity.

Chi tiết công thức, số đếm và chính sách trong [corporate actions](reports/data_pipeline/step3_corporate_actions_report.md); EDA và MFA trong [EDA](reports/data_pipeline/step6_eda_report.md). CSV nguồn giữ nguyên trong lượt sửa tài liệu này.

### 4.3. Kết quả mô tả không phải chứng nhận chất lượng

Moments CSV ghi 5.610.691 stock-days Development, std gộp 2,653%, skew 0,563, excess kurtosis 66,875, min −94,97%, max +227,87%. Những số này mô tả mẫu đã lọc, không chứng minh toàn kho đúng hoặc model sẽ hội tụ/tạo lợi nhuận.

Std gộp nhân sqrt(252) không phải volatility danh mục. Max MFA chưa được lượt này xác minh mức giá/nguyên nhân độc lập. Giảm tails sau corrections không tự xác nhận mọi mapping/event còn lại. Trường p01 trong script 09 tương ứng phân vị 0,01%, không phải 0,1%.

### 4.4. Bảng Ánh Xạ Chứng Khoán & Thành Viên Theo Thời Gian (Mapping Tables)

Nhằm đảm bảo tính minh bạch khoa học, toàn bộ quá trình chuẩn hóa định danh và liên kết thành viên theo niên độ được lưu trữ tại 3 bảng kiểm toán độc lập trong thư mục `docs/Data report/market_data_audit/tables/`:

#### 4.4.1. Bảng Ánh Xạ Định Danh Chính Quy (`canonical_security_mapping.csv`)
- **Đường dẫn**: `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv`
- **Quy mô**: Đúng **4.737 dòng $\times$ 7 cột**, ánh xạ về **3.711 Canonical SID duy nhất**.
- **Ý nghĩa**: Bảng tổng kết quá trình chuẩn hóa định danh chứng khoán, ánh xạ từ cặp `(original_ticker, raw_sid)` sang một `canonical_sid` duy nhất trên toàn bộ 28 năm lịch sử (1998–2026).
- **Cấu trúc cột & Giá trị thực tế**:
  | Tên cột | Kiểu dữ liệu | Ý nghĩa & Giá trị thực tế |
  |:---|:---:|:---|
  | `original_ticker` | string | Mã ticker gốc thu thập từ các báo cáo chỉ số hoặc sàn giao dịch (2.845 ticker phân biệt). |
  | `raw_sid` | string | Định danh thô ban đầu trong kho Lean (4.463 mã thô phân biệt, bao gồm các mã tạm ` 2T` và SID vĩnh viễn). |
  | `canonical_sid` | string | Định danh chính quy duy nhất đại diện cho thực thể chứng khoán (Khóa chính gồm đúng 3.711 mã). |
  | `resolution_type` | string | Phương thức phân giải gồm đúng 5 giá trị enum:<br>• `PERMANENT_CANONICAL` (3.891 dòng): SID vĩnh viễn trực tiếp từ QuantConnect Lean.<br>• `2T_STITCH_SUCCEEDING` (456 dòng): Ghép nối mã tạm ` 2T` vào SID vĩnh viễn ở phía sau với khoảng cách $\le 10$ ngày dương lịch.<br>• `2T_STITCH_PRECEDING` (296 dòng): Ghép nối mã tạm ` 2T` vào SID vĩnh viễn ở phía trước với khoảng cách $\le 10$ ngày dương lịch.<br>• `STANDALONE_2T_DISCONTINUOUS` (81 dòng): Mã tạm ` 2T` gián đoạn $> 10$ ngày dương lịch so với SID vĩnh viễn, được giữ làm thực thể riêng.<br>• `STANDALONE_2T_NO_PERM` (13 dòng): Mã tạm ` 2T` không có SID vĩnh viễn tương ứng trong kho dữ liệu. |
  | `min_date` | string (YYYY-MM-DD) | Ngày đầu tiên xuất hiện dữ liệu giao dịch trong kho giá. |
  | `max_date` | string (YYYY-MM-DD) | Ngày cuối cùng xuất hiện dữ liệu giao dịch trong kho giá. |
  | `trading_days` | int64 | Tổng số phiên giao dịch có dữ liệu thực tế trên sàn. |

*Lưu ý về 752 lượt nối 2T*: Gồm 456 trường hợp nối phía sau (`2T_STITCH_SUCCEEDING`) và 296 trường hợp nối phía trước (`2T_STITCH_PRECEDING`), hoàn toàn áp dụng tiêu chuẩn khoảng cách $\le 10$ ngày dương lịch (`gap_calendar_days <= 10`), không phải phiên giao dịch.

#### 4.4.2. Bảng Phân Bổ Thành Viên Theo Niên Độ Chính Thức (`universe_constituent_temporal_mapping.csv`)
- **Đường dẫn**: `docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv`
- **Quy mô**: Đúng **26.919 dòng $\times$ 9 cột** (do Step 05 xuất độc quyền).
- **Ý nghĩa**: Bảng ánh xạ chính thức làm căn cứ xây dựng ma trận thành viên `membership_mask.parquet`, quy định từng lượt thành viên–niên độ $[01/07/Y, 30/06/Y+1]$ tương ứng với Canonical SID nào.
- **Cấu trúc cột & Giá trị thực tế**:
  | Tên cột | Kiểu dữ liệu | Ý nghĩa & Giá trị thực tế |
  |:---|:---:|:---|
  | `period_year` | int64 | Năm niên độ tái cơ cấu thường niên (27 năm: từ 2000 đến 2026). |
  | `period_start` | string (YYYY-MM-DD) | Ngày bắt đầu hiệu lực của niên độ (thường là 01/07 năm $Y$). |
  | `period_end` | string (YYYY-MM-DD) | Ngày kết thúc hiệu lực của niên độ (30/06 năm $Y+1$). |
  | `source_ticker` | string | Mã ticker được ghi nhận trong snapshot iShares năm đó (2.883 ticker phân biệt). |
  | `assigned_canonical_sid` | string | Canonical SID được gán chính thức cho kỳ thành viên (2.838 mã phân biệt). |
  | `evidence_level` | string | Cấp độ bằng chứng liên kết niên độ gồm đúng 6 giá trị enum:<br>• `LEVEL_1_VERIFIED_PERMANENT`: Ánh xạ vĩnh viễn duy nhất.<br>• `LEVEL_2_VERIFIED_SEQUENTIAL_TRANSITION`: Chuyển tiếp liên tục giữa các phân đoạn SID.<br>• `LEVEL_3_HEURISTIC_2T_STITCH`: Ghép nối theo heuristic mã tạm ` 2T` ($\le 10$ ngày lịch).<br>• `LEVEL_4_AMBIGUOUS_MULTI_SID`: Tồn tại nhiều hơn 1 SID hợp lệ trong cùng khoảng thời gian.<br>• `LEVEL_5_UNRESOLVED_ZERO_BARS`: Có trong mapping nhưng không có nến nào trong niên độ.<br>• `LEVEL_6_UNRESOLVED_NOT_IN_MAPPING`: Ticker không có trong kho ánh xạ. |
  | `verification_status` | string | Trạng thái xác thực niên độ gồm 4 giá trị enum: `VERIFIED`, `ASSUMED_UNVERIFIED`, `AMBIGUOUS`, `UNRESOLVED`. |
  | `validity_overlap_range` | string | Chuỗi mô tả khoảng giao nhau giữa dữ liệu giá và niên độ (ví dụ: `'2000-07-01 đến 2001-06-30'`). |
  | `notes` | string | Ghi chú chi tiết về trạng thái ánh xạ và lịch sử niêm yết. |

#### 4.4.3. Bảng Kiểm Toán Phân Đoạn Nối Heuristic (`temporal_mapping_heuristic_audit.csv`)
- **Đường dẫn**: `docs/Data report/market_data_audit/tables/temporal_mapping_heuristic_audit.csv`
- **Quy mô**: Đúng **26.919 dòng $\times$ 10 cột** (do Step 04b xuất độc quyền).
- **Ý nghĩa**: Bảng kiểm toán phân tích độ nhạy của các trường hợp nối mã dựa trên giả định heuristic (khoảng cách $\le 10$ ngày lịch), phục vụ việc đánh giá tác động loại trừ khi cần kiểm định khắt khe.
- **Cấu trúc cột & Giá trị thực tế**:
  | Tên cột | Kiểu dữ liệu | Ý nghĩa & Giá trị thực tế |
  |:---|:---:|:---|
  | `period_year` | int64 | Năm niên độ tái cơ cấu (2000 đến 2026). |
  | `period_start` | string (YYYY-MM-DD) | Ngày bắt đầu niên độ (01/07 năm $Y$). |
  | `period_end` | string (YYYY-MM-DD) | Ngày kết thúc niên độ (30/06 năm $Y+1$). |
  | `source_ticker` | string | Mã ticker nguồn trong snapshot. |
  | `assigned_canonical_sids` | string | Canonical SID tạm gán tương ứng (lưu ý tên cột có hậu tố số nhiều `_sids`). |
  | `resolution_category` | string | Phân loại phân giải niên độ gồm đúng 5 giá trị enum:<br>• `RESOLVED_CONFIRMED`<br>• `RESOLVED_ASSUMED_2T`<br>• `UNRESOLVED_ZERO_BARS_IN_PERIOD`<br>• `RESOLVED_CONSECUTIVE_TRANSITION`<br>• `UNRESOLVED_NOT_IN_WAREHOUSE` |
  | `verification_status` | string | Trạng thái kiểm toán gồm đúng 4 giá trị enum: `CONFIRMED`, `ASSUMED_UNVERIFIED`, `UNRESOLVED`, `RESOLVED_CONSECUTIVE`. |
  | `bars_in_period` | int64 | Số lượng nến giao dịch thực tế quan sát được trong niên độ. |
  | `active_date_range` | string | Khoảng ngày giao dịch hoạt động thực tế trong niên độ (ví dụ: `'2000-07-03 đến 2001-06-29'`). |
  | `notes` | string | Ghi chú phân tích chi tiết của quá trình kiểm toán. |

---

## PHẦN 5: QUY TẮC VẬN HÀNH & KHUYẾN NGHỊ SỬ DỤNG MÔ HÌNH (BEST PRACTICES)

### 5.1. Phân Vùng Dữ Liệu Nghiêm Ngặt
1. **Giai đoạn khởi tạo (Warm-up Period: 1998-01-02 đến 2000-06-30 — 630 phiên)**:
   - Toàn bộ các ô trên `membership_mask.parquet`, `valid_data_mask.parquet` và `valid_label_mask.parquet` đều nhận giá trị `False`.
   - **Mục đích**: Tích lũy lịch sử trượt (Rolling Lookback Windows) cho các đặc trưng dài hạn (như Momentum 252 ngày, Biến động 60 ngày) đối với các chứng khoán đã niêm yết trước ngày `2000-07-01`. Cần lưu ý rằng cơ chế này giúp bảo tồn lịch sử nhưng không thể bảo đảm 100% đầy đủ cho mọi mã, bởi các cổ phiếu mới phát hành (IPO) hoặc mới niêm yết chưa đủ số phiên lookback vẫn sẽ nhận giá trị `NaN` hợp lệ theo hợp đồng lookback riêng cho từng feature.
2. **Giai đoạn phát triển (Development Period: 2000-07-01 đến 2023-12-29 — 5,911 phiên)**:
   - Dùng cho toàn bộ các hoạt động: Phân tích khám phá dữ liệu (EDA), thiết kế và trích xuất đặc trưng (Feature Engineering), chuẩn hóa dữ liệu, huấn luyện mô hình học máy (Cross-validation) và kiểm thử đối sánh mô hình (Validation).
3. **Giai đoạn ngoài mẫu (Out-of-Sample: 2024-01-02 đến 2026-10-30 — 711 phiên)**:
   - **Nguyên tắc phương pháp luận**: Tuyệt đối không dùng dữ liệu OOS để khám phá dữ liệu, lựa chọn đặc trưng (feature selection), định hình kiến trúc mô hình hay tinh chỉnh siêu tham số (tuning). Điều này không đồng nghĩa với việc dữ liệu chưa từng được quét qua (vì các bước tiền xử lý hạ tầng đã kiểm tra lịch ngày và schema bảng cho toàn dải 1998–2026).
   - **Cơ chế kỹ thuật**: Thư viện nạp ma trận tích hợp kiểm tra tự động kích hoạt ngoại lệ `OOSFreezeViolationError` nếu có truy vấn vượt quá mốc `2023-12-29` mà không có cờ cho phép chuyên biệt.

### 5.2. Biến Mục Tiêu Chính Theo Đặc Tả v1
- **Mục tiêu nghiên cứu chính đã chốt**: `target_next_return.parquet` quy đổi thành phân vị đồng nhất `target_next_rank` $\in [0, 1]$ trên mặt cắt ngang hàng ngày (Cross-sectional Uniform Rank):
  $$target\_next\_rank_{i,t} = \frac{Rank(r_{i,t+1}) - 1}{N_t - 1}$$
- **Tính chất toán học & kinh tế**: Xếp hạng phân vị chuẩn hóa thứ hạng vào khoảng $[0, 1]$ (ties không tạo phân phối đều chính xác) trên từng mặt cắt ngang ngày, giúp ổn định thang đo mục tiêu trước các biến động độ phân tán qua các thời kỳ thị trường khác nhau. Tuy nhiên, phép biến đổi thứ tự này không triệt tiêu rủi ro thị trường (Market Beta) hay rủi ro ngành, bởi nó không phải là phép hồi quy trung hòa nhân tố; tương quan giữa các chứng khoán vẫn bị chi phối bởi các biến động hệ thống chung.

### 5.3. Chính Sách Xử Lý Giá Trị Khuyết Thiếu (NaN Policy) & Bảo Toàn Warm-up
Khi trích xuất các đặc trưng ứng viên tại Step 7 (theo đặc tả v1 đã chốt), quy trình tính toán tuân thủ 3 bước nghiêm ngặt:
1. **Làm sạch đầu vào (Input Data Hygiene)**:
   - Dữ liệu giá/lợi suất đầu vào bắt buộc được làm sạch bằng `bar_quality_mask` (độc lập với membership): mọi ô có $bar\_quality\_mask == \text{False}$ (bad tick, spinoff jump) bị ép thành `NaN`.
   - **Bảo toàn lịch sử warm-up**: Các phiên giao dịch hợp lệ trước ngày cổ phiếu chính thức vào rổ Russell 1000 được giữ nguyên vẹn để phục vụ warm-up, cho phép tính toán đặc trưng ngay tại Ngày 1 gia nhập rổ.
2. **Kiểm tra độ đầy đủ của cửa sổ chất lượng (Quality-Window Completeness)**:
   - Áp cửa sổ theo từng công thức: W return thường cần W+1 giá; Parkinson cần W cặp high/low; RSI cần seed/reset trạng thái. Không áp min_periods=W đồng loạt cho mọi input. Cửa sổ đo đi qua dữ liệu lỗi/thiếu không được bắc cầu ngầm.
3. **Lọc thành viên đầu ra (Output Membership Masking)**:
   - Áp dụng `membership_mask` tại ngày đầu ra $t$. Chứng khoán ngoài rổ tại ngày $t$ nhận giá trị `NaN`.
   - **Cách ly tuyệt đối**: Tuyệt đối không dùng `valid_label_mask` để lọc đầu vào đặc trưng $X_t$.

### 5.4. Quy Chuẩn Kiểm Thử Tự Động & Ghi Chú Runner
- **Lệnh kiểm thử chuẩn thức của dự án**:
  ```powershell
  python -m pytest -q
  ```
  Lệnh này thực thi toàn bộ **32/32 bài test tự động** (thời gian chạy ~3.8 giây), bao gồm:
  - `tests/test_matrix_loader.py` (11 tests): Kiểm tra nạp ma trận 2D, lưới tọa độ $7.252 \times 3.711$, phân vùng Development (5.911 phiên) và cơ chế khóa OOS.
  - `tests/test_pipeline_integrity.py` (10 tests): Biên dịch tĩnh 13 script chính, kiểm tra không ổ đĩa cứng, đối chiếu đường dẫn Bước 03/04, phân lập bảng audit 04b/05.
  - `tests/test_library_fixes.py` (11 tests): Kiểm thử hồi quy các ca biên (tra cứu PIT không fallback, bảo toàn warm-up, cửa sổ rolling qua bar lỗi, công thức uniform rank chuẩn).
- **Ghi chú kỹ thuật về `tests/run_tests.py`**:
  - Script `tests/run_tests.py` sử dụng trình khám phá chuẩn của Python `unittest.TestLoader().discover`.
  - Do quy ước mặc định của `unittest` chỉ tự động quét các lớp kế thừa `unittest.TestCase`, runner này hiện phát hiện và thực thi **21 tests** (từ `test_library_fixes.py` và `test_pipeline_integrity.py`).
  - Để chạy đầy đủ cả 11 bài test dạng hàm trong `test_matrix_loader.py`, lệnh kiểm thử chính thức được khuyến nghị cho toàn bộ nhóm phát triển là `python -m pytest -q`.

### 5.5. Hướng Dẫn Code Mẫu Tính Toán Đặc Trưng (Feature Engineering API)
Mọi phép tính đặc trưng tại Step 7 đều sử dụng lớp cơ sở `FeatureBase` với việc truyền rõ ràng cả `bar_quality_mask` và `membership_mask`:

```python
from src.data.matrix_loader import load_matrix, load_bar_quality_mask, load_layer1_mask
from src.features.base import TotalReturnMomentumFeature, RealizedVolatilityFeature

# 1. Nạp ma trận dữ liệu (kèm Warm-up 630 phiên để có đủ lookback)
total_ret = load_matrix("total_return", dev_only=True, include_warmup=True)
daily_ret = load_matrix("daily_return", dev_only=True, include_warmup=True)

# 2. Nạp Bar Quality Mask (độc lập membership, làm sạch input)
bar_quality = load_bar_quality_mask(dev_only=True, include_warmup=True)

# 3. Nạp Membership Mask (dùng lọc output tại ngày T)
membership = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)

# 4. Tính toán đặc trưng Momentum 20 ngày (minh bạch price_type)
mom_20d = TotalReturnMomentumFeature(window=20, price_type="total_return")
mom_matrix = mom_20d.compute(
    data={"total_return": total_ret},
    bar_quality_mask=bar_quality,
    membership_mask=membership,
)

# 5. Tính toán đặc trưng Realized Volatility 20 ngày (minh bạch return_type)
vol_20d = RealizedVolatilityFeature(window=20, return_type="daily_return")
vol_matrix = vol_20d.compute(
    data={"daily_return": daily_ret},
    bar_quality_mask=bar_quality,
    membership_mask=membership,
)
```

---
*Tài liệu từ điển dữ liệu được biên soạn và cập nhật theo tiêu chuẩn kỹ thuật dữ liệu định lượng cao cấp (Institutional Quant Grade).*
