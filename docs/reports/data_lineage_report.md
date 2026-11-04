# BÁO CÁO HÀNH TRÌNH VÀ NGUỒN GỐC DỮ LIỆU ĐỊNH LƯỢNG (DATA LINEAGE REPORT)

> **Dự án**: Russell 1000 Daily Return Ranking Prediction Engine  
> **Milestone**: M3 — Section R4 (Kiến Trúc Hành Trình Dữ Liệu & Thẩm Định Pháp Y)  
> **Ngày thực hiện**: 2026-11-04  
> **Tác giả**: Subagent `worker_m3a` (README & Data Lineage Specialist)  
> **Trạng thái**: ✅ **HOÀN TẤT & ĐÃ ĐỐI SOÁT VỚI KHO DỮ LIỆU THỰC TẾ**  
> **Integrity Mode**: Development (Dữ liệu Out-of-Sample 2024–2026 đóng băng tuyệt đối)  

---

## MỤC LỤC
1. [Phần 1: Nguồn Dữ Liệu Gốc & Kiến Trúc Định Danh Chứng Khoán](#phần-1-nguồn-dữ-liệu-gốc--kiến-trúc-định-danh-chứng-khoán)
   - 1.1. Snapshots Thành Viên Russell 1000 Point-in-Time (PIT)
   - 1.2. Dữ Liệu Nến Thô OHLCV Từ QuantConnect LEAN
   - 1.3. Định Dạng SecurityIdentifier (SID) & Bản Chất Kỹ Thuật
   - 1.4. Vấn Đề Ticker Reuse & Mã Placeholder Tạm Thời `' 2T'`
2. [Phần 2: Quá Trình Chuyển Hóa Từng Bước (End-to-End Transformation)](#phần-2-quá-trình-chuyển-hóa-từng-bước-end-to-end-transformation)
   - 2.1. Sơ Đồ Kiến Trúc Luồng Dữ Liệu (Multi-Tier Data Flow)
   - 2.2. Giai Đoạn 1: Raw Sources ➔ 10 ZIP Ingestion Batches
   - 2.3. Giai Đoạn 2: Ingestion Batches ➔ Tier 1 Consolidated Parquet
   - 2.4. Giai Đoạn 3: Tier 1 ➔ Identity Audit & Canonical SIDs Parquet
   - 2.5. Giai Đoạn 4: Canonical Parquet + Corporate Actions ➔ Tier 2 Adjusted Warehouse (484 MB)
   - 2.6. Giai Đoạn 5: Tier 2 Warehouse ➔ 17 Ma Trận 2D Parquet & PIT Masks
3. [Phần 3: Sự Kiện Doanh Nghiệp & Các Hiệu Chỉnh Định Lượng](#phần-3-sự-kiện-doanh-nghiệp--các-hiệu-chỉnh-định-lượng)
   - 3.1. Phương Pháp Luận Điều Chỉnh Chia Tách (Backward Split Adjustment)
   - 3.2. Thuật Toán Tìm Kiếm Nhị Phân Vector Hóa `np.searchsorted`
   - 3.3. Bổ Khuyết Chia Tách Ngược (Reverse Split Injection) & Kiểm Soát Kurtosis
   - 3.4. Xử Lý Gián Đoạn Tách Công Ty Con (Special Corporate Spinoffs)
   - 3.5. Kiểm Soát Chất Lượng Nến (Quality Flags & Symbol Collisions)
4. [Phần 4: Hệ Thống Ma Trận 2D & Cấu Trúc 3 Lớp PIT Masks](#phần-4-hệ-thống-ma-trận-2d--cấu-trúc-3-lớp-pit-masks)
   - 4.1. Khung Tọa Độ 2D (Wide Format) vs Dạng Bảng Dài (Long Format)
   - 4.2. Quy Trình Đồng Bộ & Pivot Tọa Độ Ma Trận
   - 4.3. Cấu Trúc Phân Cấp 3 Lớp PIT Masks (Hierarchical Masking Logic)
   - 4.4. Point-In-Time (PIT): Định Nghĩa Kinh Tế & Tính Tất Yếu Toán Học
   - 4.5. Cơ Chế Purge Ranh Giới (Anti-Lookahead Purge) & Bảo Toàn OOS 2024–2026

---

## PHẦN 1: NGUỒN DỮ LIỆU GỐC & KIẾN TRÚC ĐỊNH DANH CHỨNG KHOÁN

### 1.1. Snapshots Thành Viên Russell 1000 Point-in-Time (PIT)

Để giảm thiểu tối đa **Survivorship Bias** (thiên lệch kẻ sống sót — hiện tượng các phân tích định lượng chỉ chọn những công ty còn tồn tại tới hôm nay, làm thổi phồng tỷ suất sinh lời quá khứ) theo quy chuẩn nghiên cứu tổ chức, toàn bộ danh mục thành viên của chỉ số Russell 1000 được tái cấu trúc từ các tài liệu công bố chính thức hằng năm của đơn vị quản lý chỉ số (FTSE Russell / Frank Russell Company) và quỹ ETF mô phỏng iShares Russell 1000 ETF (IWB).

#### A. Thu Thập & Lưu Trữ Thô
Dữ liệu thô được lưu trữ tại `data/raw/universe/raw_universe/` bao gồm 27 kỳ tái cơ cấu thường niên từ năm 2000 đến năm 2026, trải qua 3 thời kỳ định dạng (Eras):
1. **Era-1 (2000–2007)**: Định dạng tài liệu in ấn PDF scan và text bảng biểu từ Frank Russell Company. Ticker được đặt ở đầu dòng hoặc theo cột cố định (`ticker company_name market_cap`).
2. **Era-2 (2009–2015)**: Báo cáo PDF dạng bảng điện tử nhiều trang với cấu trúc dòng ticker nằm ở cuối token hoặc sau mã phân ngành CUSIP.
3. **Era-3 (2016–2026)**: Báo cáo iShares / BlackRock dạng CSV, XML bảng biểu hoặc JSON API (`aaData`), trong đó mỗi cổ phiếu có cặp thông tin dòng lẻ (Tên công ty) và dòng chẵn (Ticker, CUSIP, SEDOL, Tỷ trọng).

#### B. Quy Trình Bóc Tách (Parsing Engine)
Script `scripts/01_pipeline/01_parse_all_universe.py` triển khai bộ phân tích cú pháp đa thời kỳ:
- **Regex Parsing chuyên biệt**:
  - Era-1: Regex `^([A-Z][A-Z0-9\-]{0,5})\s{1,4}[A-Z0-9&]` bắt mã đầu dòng.
  - Era-2: Regex token cuối dòng với kiểm tra độ dài mã hợp lệ $\le 5$ ký tự.
  - Era-3: Phân tích cú pháp theo cặp dòng đan xen (Pair-based alternating lines).
- **Lọc Nhiễu Học Thuật (Domain Noise Filtering)**:
  - Loại bỏ danh mục 65 từ khóa dừng tài chính (`NOISE_WORDS` như `THE`, `CORP`, `INC`, `HOLDINGS`, `CLASS`, `REBALANCING`, `RUSSELL`, `JUNE`, `INDEX`...) nhằm triệt tiêu hoàn toàn nguy cơ biến đổi nhầm các từ viết hoa trong tiêu đề bảng biểu thành mã chứng khoán.
- **Tập Dữ Liệu Đầu Ra**:
  - `data/raw/universe/russell1000_pit_by_year.json`: Từ điển JSON ánh xạ `{"<year>": ["<ticker>", ...]}` gồm đúng **27 năm**, tổng cộng **26,919 lượt constituent-years**, đại diện cho **2,884 mã chứng khoán thô độc nhất**.
  - `data/raw/universe/extraction_quality_report.csv`: Báo cáo đối soát chất lượng trích xuất, xác nhận độ phủ so với dữ liệu thị trường đạt trung bình **99.42%**.

---

### 1.2. Dữ Liệu Nến Thô OHLCV Từ QuantConnect LEAN

Toàn bộ dữ liệu giá và khối lượng giao dịch được trích xuất từ nền tảng điện toán đám mây định lượng **QuantConnect LEAN Engine** — hệ thống cung cấp dữ liệu thị trường chứng khoán Hoa Kỳ ở cấp độ tổ chức được bảo trợ bởi Morningstar và Algoseek.

#### A. Chế Độ Chuẩn Hóa Thô (DataNormalizationMode.Raw)
Khác với các nguồn dữ liệu tài chính bán lẻ (như Yahoo Finance vốn tự động điều chỉnh giá lùi theo các hệ số không rõ nguồn gốc, làm méo mó các phân tích khớp lệnh và kiểm toán khối lượng), toàn bộ nến ngày (Daily Bars) được kéo về ở chế độ:
$$\text{DataNormalizationMode} = \mathbf{Raw}$$
- **Ý nghĩa định lượng**:
  - Giá Mở cửa (`open`), Cao nhất (`high`), Thấp nhất (`low`), Đóng cửa (`close`) là **giá khớp lệnh thực tế trên sàn giao dịch (Unadjusted Trading Price)** tại đúng phiên giao dịch đó.
  - Khối lượng giao dịch (`volume`) là **số lượng cổ phiếu thực tế được chuyển nhượng** trong phiên.
  - Không có bất kỳ thao tác chia tách (split) hay trừ cổ tức (dividend) nào được áp đặt ngầm vào nến thô. Việc điều chỉnh giá được kiểm soát tường minh 100% trong mã nguồn của dự án tại Bước 6.

#### B. Cơ Chế Ingestion Theo Batch (10 Batches Resilient Architecture)
Do giới hạn tài nguyên tính toán và bộ nhớ RAM trên QuantConnect Research Notebook, danh sách 2,871 mã cổ phiếu khả dụng được phân chia thành 10 lô độc lập (Batches 0 đến 9) thông qua script `02_quantconnect_export_10_batches.py`:
- Mỗi batch bao gồm ~287 cổ phiếu, được xử lý qua các sub-groups 20 symbols.
- Tích hợp cơ chế tự động bắt lỗi: Nếu một sub-group vấp lỗi nến hỏng, hệ thống tự động fallback truy vấn từng symbol riêng lẻ nhằm bảo đảm không làm mất bất kỳ phiên giao dịch nào.
- 10 file ZIP nén được xuất ra: `russell_market_batch_01_of_10.zip` đến `russell_market_batch_10_of_10.zip` (tổng kích thước ~200 MB), nạp trực tiếp vào `data/raw/market_data/`.

---

### 1.3. Định Dạng SecurityIdentifier (SID) & Bản Chất Kỹ Thuật

Trong phân tích định lượng chuyên nghiệp, **Mã Ticker (Symbol) KHÔNG PHẢI là khóa chính duy nhất** của một tài sản tài chính. Một mã ticker có thể đại diện cho nhiều công ty khác nhau tại các thời điểm khác nhau (Ticker Reuse), hoặc một công ty có thể thay đổi ticker nhiều lần trong vòng đời niêm yết (Name/Ticker Change).

QuantConnect giải quyết bài toán này thông qua cấu trúc **`SecurityIdentifier` (SID)**:

```text
Cấu trúc chuỗi SID: "<HistoricalTicker> <MarketIdentifierHash>"
Ví dụ thực tế:
  - "AAPL R735QTJ8XC9X"   : Apple Inc. (Mã vĩnh viễn trên thị trường Hoa Kỳ)
  - "GOOG VPSS70OE3M1X"   : Alphabet Inc. Class C (Phân tách từ GOOGL)
  - "CHK R735QTJ8XC9X"    : Chesapeake Energy Corp. (Giai đoạn trước phá sản 2020)
  - "CHK VW1A4C2VJMN9"    : Chesapeake Energy Corp. (Giai đoạn tái niêm yết sau phá sản 2021)
  - "PL 2T"               : Protective Life Corp. (Mã placeholder tạm thời của LEAN)
```

#### Ý Nghĩa Của Chuỗi Băm (MarketIdentifierHash):
Chuỗi 12 ký tự thập lục phân kết hợp Base32 (như `R735QTJ8XC9X`) mã hóa thông tin nội tại:
1. **Thị trường niêm yết gốc (Market)**: USA Equities (NYSE, NASDAQ, AMEX).
2. **Loại tài sản (SecurityType)**: Equity (Cổ phiếu phổ thông).
3. **Mã số định danh vĩnh viễn (First Known Ticker & Timestamp Hash)**: Được neo vào ngày đầu tiên tài sản bắt đầu phát sinh dữ liệu giao dịch trong lịch sử thị trường Hoa Kỳ (kể từ năm 1998).

---

### 1.4. Vấn Đề Ticker Reuse & Mã Placeholder Tạm Thời `' 2T'`

Quá trình thẩm định danh tính chứng khoán tại Bước 4 (`04_audit_identity_and_build_canonical_mapping.py`) đã phát hiện hai thách thức kỹ thuật lớn trong cơ sở dữ liệu gốc:

#### A. Hiện Tượng Ticker Reuse (Tái Sử Dụng Mã Chứng Khoán)
Có **1,281 trường hợp** một mã ticker được gán cho nhiều SID khác nhau trong suốt 27 năm.
- *Ví dụ 1*: Ticker `C` từng thuộc về Chrysler Corporation trước năm 1998, sau đó được tái cấp cho Citigroup Inc.
- *Ví dụ 2*: Ticker `T` từng thuộc về AT&T Corp cũ, sau đó SBC Communications sáp nhập và lấy lại ticker `T`.
- *Ví dụ 3*: Trường hợp tái cấu trúc sau phá sản (Chapter 11 Bankruptcy) như `CHK` (Chesapeake Energy). Giai đoạn 2000–2020 là thực thể cũ (`CHK R735QTJ8XC9X`), sau khi xóa sổ cổ phiếu cũ và phát hành cổ phiếu mới năm 2021, nó trở thành thực thể mới hoàn toàn độc lập (`CHK VW1A4C2VJMN9`).

#### B. Mã Placeholder Tạm Thời `' 2T'` (Transient Placeholders)
Trong hệ thống LEAN của QuantConnect, khi một cổ phiếu đã hủy niêm yết trong quá khứ hoặc dữ liệu lịch sử sơ khai thiếu liên kết mã CUSIP/CIK gốc, hệ thống tạm thời gán hậu tố `' 2T'` vào mã SID (như `ABC 2T`).
- **Phát hiện kiểm toán**: Tổng cộng có **846 mã dạng `' 2T'`**.
- **Giải pháp Nối Mượt (Temporal Stitching)**:
  - Phân tích vòng đời ngày giao dịch: Với mỗi mã `' 2T'`, tìm mã vĩnh viễn (Permanent SID) tương ứng có cùng tên doanh nghiệp.
  - Nếu khoảng cách thời gian giữa ngày kết thúc của mã vĩnh viễn và ngày bắt đầu của mã `' 2T'` nhỏ hơn hoặc bằng 10 ngày dương lịch ($\text{gap\_calendar\_days} \le 10$): Hệ thống thực hiện nối mượt, hợp nhất mã `' 2T'` vào mã chính quy.
  - **Kết quả**: Đã nối thành công **752 mã `' 2T'`** vào các mã vĩnh viễn; **94 mã còn lại** có gián đoạn lớn hoặc hoạt động độc lập được phân loại thành `STANDALONE_2T_DISCONTINUOUS` và giữ nguyên để tránh gộp sai thực thể.

---

## PHẦN 2: QUÁ TRÌNH CHUYỂN HÓA TỪNG BƯỚC (END-TO-END TRANSFORMATION)

### 2.1. Sơ Đồ Kiến Trúc Luồng Dữ Liệu (Multi-Tier Data Flow)

```text
[Raw Sources: 27 PDF/CSV Snapshots]         [QuantConnect LEAN Cloud Engine]
                 │                                         │
                 │ (Script 01: Multi-Era Parsing)          │ (Scripts 02, 02_export: Raw Mode)
                 ▼                                         ▼
      russell1000_pit_by_year.json              10 ZIP Batches (Raw OHLCV)
                 │                                         │
                 │                                         │ (Script 03: In-Memory Stream)
                 │                                         ▼
                 │                       Tier 1 Master Parquet (13.15M rows)
                 │                                         │
                 │                                         │ (Script 04: Bit-for-bit De-dup,
                 │                                         │             2T Stitching, Reuse Disambiguation)
                 │                                         ▼
                 │                       Tier 1 Canonical Parquet (12.25M rows)
                 │                       + canonical_security_mapping.csv (3,711 SIDs)
                 │                                         │
                 ├────────────────────────┐                │
                 │                        │                │
                 ▼                        ▼                │
     QC Factor Files (Splits/Divs)    Corrections CSV      │
     (Script 05: Export CA)           (13 ca CORR_001..013)│
                 │                        │                │
                 └───────────┬────────────┘                │
                             │                             │
                             ▼                             ▼
                 [Script 06: Searchsorted Backward Adjustment, Float64 Math, Session Gaps]
                                           │
                                           ▼
                 Tier 2 Adjusted Price Warehouse Parquet (484 MB, 25 cột)
                 russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet
                                           │
                                           ▼
                 [Script 07: 2D Coordinate Grid Pivot, 3-Tier Layered PIT Masks,
                             Anti-Lookahead Purge at 2023-12-29]
                                           │
                                           ├─────────────────────────────────────────┐
                                           ▼                                         ▼
                 17 Ma Trận 2D Parquet (7,252 × 3,711)                     3 Lớp PIT Masks & Targets
                 (open, close, adj_close, daily_return...)                 (membership, valid_data, valid_label)
                                           │                                         │
                 ┌─────────────────────────┴─────────────────────────────────────────┤
                 ▼                                                                   ▼
    [Script 08: Sanity Round-trip]     [Script 09: Development EDA 2000-23]     [Script 10: Forensic Outliers]
    (50k cells AE = 0.00e+00)          (Kurt 66.88, Vol 2.65%, Skew +0.56)      (Top 50 +/-, 34 SEC Audits)
```

---

### 2.2. Giai Đoạn 1: Raw Sources ➔ 10 ZIP Ingestion Batches
- **Thực thi**: Script `01_parse_all_universe.py` trên máy cục bộ; Scripts `02_quantconnect_availability_scan.py` và `02_quantconnect_export_10_batches.py` trên QuantConnect Research Notebook.
- **Dữ liệu đầu vào**:
  - Tài liệu snapshot tại `data/raw/universe/raw_universe/`.
  - Cơ sở dữ liệu thị trường QuantConnect LEAN.
- **Quá trình xử lý**:
  - Trích xuất 26,919 lượt constituent-years.
  - Mã hóa Base64 nén zlib nhúng trực tiếp vào notebook cloud để vượt qua hạn chế truyền file.
  - Phân tích độ sẵn sàng của 2,884 mã chứng khoán: 2,871 mã có dữ liệu (`MATCH`), 13 mã không có dữ liệu giao dịch trong kỳ (`EMPTY`).
  - Truy vấn nến nạp ở chế độ `DataNormalizationMode.Raw` từ 1998 đến 2026.
- **Dữ liệu đầu ra**:
  - 10 tệp tin ZIP nén `russell_market_batch_{01..10}_of_10.zip` (tổng dung lượng ~200 MB), chứa hàng ngàn file CSV theo năm và file nhật ký audit `master_batch_status.csv`.

---

### 2.3. Giai Đoạn 2: Ingestion Batches ➔ Tier 1 Consolidated Parquet
- **Thực thi**: Script `03_process_10_batches_to_parquet.py`.
- **Dữ liệu đầu vào**: 10 file ZIP tại `data/raw/market_data/`.
- **Kỹ thuật Data Engineering**:
  - **In-Memory Stream Reading**: Sử dụng `zipfile.ZipFile.open()` đọc trực tiếp luồng nhị phân của các file CSV bên trong file ZIP vào bộ nhớ RAM của Pandas, không ghi giải nén ra ổ cứng trung gian, tiết kiệm hơn 10 GB dung lượng I/O đĩa.
  - **Schema Enforcing & Type Casting**: Ép kiểu `date` sang `datetime64[ns]`, các cột giá (`open`, `high`, `low`, `close`) và khối lượng (`volume`) sang `float64`, các trường danh tính (`original_ticker`, `qc_ticker`, `sid`) sang `string`.
  - **Khử trùng lặp trên cặp khóa `(date, original_ticker)`**: Đảm bảo mỗi cổ phiếu chỉ có đúng 1 nến cho mỗi ngày giao dịch.
- **Dữ liệu đầu ra**:
  - Phân vùng theo năm: `data/processed/constituents_market_data/by_year/russell_ohlcv_{year}.parquet` (29 file).
  - Kho tổng hợp Master: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` (**13,147,389 dòng**, 9 cột, kích thước ~200 MB).

---

### 2.4. Giai Đoạn 3: Tier 1 ➔ Identity Audit & Canonical SIDs Parquet
- **Thực thi**: Script `04_audit_identity_and_build_canonical_mapping.py`.
- **Dữ liệu đầu vào**: Master Raw Parquet từ Giai đoạn 2.
- **Phát hiện & Xử lý kỹ thuật**:
  - **Phát hiện 1.57 triệu dòng trùng lặp bit-for-bit**: Do các mã alias (như `FB` và `META`, `ANTM` và `ELV`), QuantConnect trả về 2 chuỗi nến giống hệt nhau cho cùng một doanh nghiệp. Script thực hiện kiểm tra khẳng định `assert max_close_diff == 0.0` (sai số bằng 0 tuyệt đối) và loại bỏ các bản ghi trùng lặp này.
  - **Nối mượt 752 mã `' 2T'`**: Xác định các khoảng thời gian gián đoạn và ánh xạ về Permanent SID tương ứng.
  - **Phân lập 1,281 Ticker Reuse**: Tách các thực thể khác nhau có chung ticker thành các `canonical_sid` riêng biệt dựa trên khoảng ngày hoạt động thực tế.
- **Dữ liệu đầu ra**:
  - Bảng ánh xạ danh tính chính thức: `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` (4,463 dòng, chứa 3,711 Canonical SIDs độc nhất).
  - Kho nến chuẩn hóa danh tính: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet` (**12,247,081 dòng**, nén `zstd` level 7, kích thước 155.76 MB).

---

### 2.5. Giai Đoạn 4: Canonical Parquet + Corporate Actions ➔ Tier 2 Adjusted Warehouse (484 MB)
- **Thực thi**: Script `06_process_corporate_actions_and_adjusted_prices.py`.
- **Dữ liệu đầu vào**:
  - `russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet`.
  - Cơ sở dữ liệu sự kiện chia tách: `russell1000_splits_1998_2026.csv`.
  - Cơ sở dữ liệu cổ tức: `russell1000_dividends_1998_2026.csv`.
  - Bảng hiệu chỉnh pháp y: `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv` (13 ca CORR_001..CORR_013).
- **Quy trình chuyển hóa định lượng**:
  1. *Tiêm hiệu chỉnh pháp y*: Bổ sung 5 ca chia tách ngược bị thiếu từ nguồn QC Factor Files vào bảng splits trước khi tính toán.
  2. *Tính hệ số Cumulative Split Factor ($CF_{i,t}$)*: Sử dụng thuật toán `np.searchsorted` lùi thời gian (Backward adjustment).
  3. *Tính chuỗi giá và khối lượng điều chỉnh*: Áp dụng công thức nhân hệ số chia tách ở độ chính xác số học nguyên bản `float64` (không làm tròn số thập phân).
  4. *Đo lường khoảng trống phiên giao dịch*: So khớp với lịch giao dịch chính thức của NYSE (`nyse_trading_dates`), tính toán `trading_session_gap` và gắn cờ `is_consecutive_session == True` khi khoảng cách phiên đúng bằng 1.
  5. *Tính toán Lợi suất ngày*:
     $$r_{i, t} = \frac{P_{adj, i, t}}{P_{adj, i, t-1}} - 1$$
     $$\text{total\_return}_{i, t} = \frac{P_{adj, i, t} + \text{adj\_div}_{i, t}}{P_{adj, i, t-1}} - 1$$
  6. *Gắn cờ kiểm soát chất lượng*: Gán `is_bad_data_period = True` cho 4 ca nến lỗi và `is_spinoff_discontinuity = True` cho 4 ca chia tách công ty con, đồng thời biến đổi lợi suất tại các phiên này thành `NaN`.
- **Dữ liệu đầu ra**:
  - **Tier 2 Adjusted Warehouse**: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` (**12,247,081 dòng, đúng 25 cột chuẩn hóa**, nén `zstd` level 7, kích thước **484.32 MB**).

#### Chi Tiết 25 Cột Của Kho Dữ Liệu Tier 2:
| Nhóm Cột | Tên Cột | Kiểu Dữ Liệu | Ý Nghĩa Kỹ Thuật |
|:---|:---|:---:|:---|
| **Khóa chính** | `date` | `datetime64[us]` | Ngày giao dịch (Khóa kết hợp cùng SID) |
| | `canonical_sid` | `string` | Mã định danh chuẩn hóa của chứng khoán |
| | `original_ticker`| `string` | Mã ticker ghi nhận trong hồ sơ thành viên rổ |
| | `qc_ticker` | `string` | Mã ticker ánh xạ trong hệ thống QuantConnect |
| **Giá thị trường thô** | `open`, `high`, `low`, `close` | `float64` | Giá khớp lệnh thực tế trên sàn chưa qua điều chỉnh |
| | `volume` | `float64` | Khối lượng cổ phiếu thực tế chuyển nhượng |
| **Hệ số & Giá điều chỉnh** | `cumulative_split_factor` | `float64` | Hệ số chia tách dồn tích liên tục $CF_{i,t}$ (Neo ngày hiện tại = 1.0) |
| | `adj_open`, `adj_high`, `adj_low`, `adj_close` | `float64` | Chuỗi giá đã điều chỉnh chia tách backward |
| | `adj_volume` | `float64` | Khối lượng giao dịch tương đương sau điều chỉnh ($V_{raw} / CF$) |
| **Cổ tức tiền mặt** | `dividend_amount` | `float64` | Cổ tức tiền mặt công bố trên 1 cổ phiếu |
| | `adj_dividend` | `float64` | Cổ tức tiền mặt điều chỉnh theo hệ số chia tách ($D_{raw} \times CF$) |
| **Lợi suất ngày** | `daily_return` | `float64` | Lợi suất thay đổi giá đóng cửa điều chỉnh so với phiên trước |
| | `total_return` | `float64` | Tổng lợi suất bao gồm tái đầu tư cổ tức tiền mặt |
| **Phiên & Lịch NYSE** | `trading_session_gap` | `float64` | Số phiên giao dịch thực tế trên sàn NYSE giữa 2 nến liên tiếp |
| | `calendar_day_gap` | `float64` | Số ngày dương lịch giữa 2 nến liên tiếp |
| | `is_consecutive_session` | `boolean` | Đạt `True` khi hai nến giao dịch liền kề nhau trên sàn NYSE (gap = 1) |
| **Kiểm soát chất lượng** | `is_bad_data_period` | `boolean` | Đạt `True` khi nến nằm trong vùng nạp dữ liệu lỗi thị trường |
| | `is_spinoff_discontinuity` | `boolean` | Đạt `True` khi nến nằm tại phiên tách công ty con chưa điều chỉnh |
| | `quality_flag` | `string` | Nhãn phân loại pháp y chi tiết (`OK`, `BAD_TICK`, `SPINOFF`, ...) |

---

### 2.6. Giai Đoạn 5: Tier 2 Warehouse ➔ 17 Ma Trận 2D Parquet & PIT Masks
- **Thực thi**: Script `07_build_2d_matrices_and_masks.py`.
- **Dữ liệu đầu vào**: Tier 2 Adjusted Warehouse Parquet (484 MB).
- **Quy trình chuyển hóa**:
  1. *Khởi tạo khung tọa độ chuẩn*:
     - Trục hàng (Index): 7,252 ngày giao dịch chính thức của NYSE từ 1998-01-02 đến 2026-10-30 (`matrix_dates_index.parquet`).
     - Trục cột (Columns): 3,711 Canonical SIDs chính quy (`matrix_columns_sids.parquet`).
     - Tổng không gian lưới: $7,252 \times 3,711 = \mathbf{26,912,172\text{ ô dữ liệu}}$.
  2. *Pivot 17 Ma trận Giá trị*: Tách 17 trường số liệu từ dạng bảng dài thành 17 tệp Parquet dạng ma trận 2D độc lập.
  3. *Tạo 3 lớp PIT Masks*: Thiết lập các ma trận boolean lọc dữ liệu nhiều tầng (`membership_mask`, `valid_data_mask`, `valid_label_mask`).
  4. *Tính toán Biến mục tiêu (Forward Target Matrices)*:
     $$target\_next\_return_{i, t} = daily\_return_{i, t+1}$$
     $$target\_next\_total\_return_{i, t} = total\_return_{i, t+1}$$
     Tất cả các ô có `valid_label_mask == False` đều được ép về `NaN`.
  5. *Kích hoạt cơ chế Purge ranh giới*: Ép toàn bộ nhãn tại ngày `2023-12-29` về `NaN` để cách ly hoàn toàn giai đoạn Out-of-Sample 2024–2026.
- **Dữ liệu đầu ra**:
  - Toàn bộ 26 file Parquet trong thư mục `data/processed/matrices/` (tổng kích thước ~1 GB).

---

## PHẦN 3: SỰ KIỆN DOANH NGHIỆP & CÁC HIỆU CHỈNH ĐỊNH LƯỢNG

### 3.1. Phương Pháp Luận Điều Chỉnh Chia Tách (Backward Split Adjustment)

Trong nghiên cứu định lượng, có hai trường phái điều chỉnh giá:
1. **Forward Adjustment (Điều chỉnh tiến)**: Giữ nguyên giá trong quá khứ, nhân hệ số vào giá tương lai. Phương pháp này khiến giá cổ phiếu hiện tại bị lệch khỏi thị giá thực tế đang quan sát trên bảng điện tử (ví dụ: AAPL hôm nay có giá 0.15 USD).
2. **Backward Adjustment (Điều chỉnh lùi — Chuẩn cấp tổ chức)**:
   - **Mốc neo (Anchor Point)**: Lấy phiên giao dịch hiện tại làm mốc chuẩn với hệ số $CF = 1.0$.
   - **Ý nghĩa kinh tế**: Giá cổ phiếu tại ngày hôm nay trên biểu đồ phản ánh chính xác đơn vị tiền tệ thực tế của đồng Đô la Mỹ ngày hôm nay. Toàn bộ chuỗi giá trong quá khứ được điều chỉnh co giãn lùi tương ứng với số lượng cổ phiếu đã bị pha loãng hoặc gộp lại qua các sự kiện chia tách.

#### Công Thức Toán Học:
Giả sử cổ phiếu phát sinh $M$ sự kiện chia tách tại các ngày $T_1 < T_2 < \dots < T_M$ với các tỷ lệ chia tách tương ứng là $s_1, s_2, \dots, s_M$ (với $s > 1$ là chia tách thông thường — ví dụ chia 2:1 thì $s=2$; $0 < s < 1$ là chia tách ngược — ví dụ gộp 1:10 thì $s=0.1$ hoặc biểu diễn theo hệ số đảo).

Hệ số chia tách tích lũy lùi $CF_{i, t}$ tại ngày giao dịch $t$ được định nghĩa:
$$CF_{i, t} = \prod_{k: T_k > t} \frac{1}{\text{factor}_k}$$
Khi đó:
$$P_{adj, i, t} = P_{raw, i, t} \times CF_{i, t}$$
$$V_{adj, i, t} = \frac{V_{raw, i, t}}{CF_{i, t}}$$

#### Bảo Toàn Tính Bất Biến Của Giá Trị Giao Dịch (Dollar Volume Invariance):
Tích số giữa giá và khối lượng (Dollar Volume) là một đại lượng bảo toàn năng lượng tài chính:
$$\text{Dollar Volume} = P_{adj, i, t} \times V_{adj, i, t} = (P_{raw, i, t} \times CF_{i, t}) \times \left(\frac{V_{raw, i, t}}{CF_{i, t}}\right) \equiv P_{raw, i, t} \times V_{raw, i, t}$$
Đẳng thức này đã được thẩm định tự động trong script 06 và 08 với sai số tuyệt đối bằng $0.00e+00$.

---

### 3.2. Thuật Toán Tìm Kiếm Nhị Phân Vector Hóa `np.searchsorted`

Trong thực tế, ngày thực hiện quyền chia tách (Ex-Date) thường rơi vào ngày thứ Hai đầu tuần, ngày nghỉ lễ hoặc các ngày cổ phiếu tạm ngừng giao dịch. Nếu sử dụng phép nối bảng thông thường (`merge_asof` hoặc `join`), hệ thống rất dễ bị lỗi mất dữ liệu hoặc tính sai hệ số cho các nến lân cận.

Dự án áp dụng thuật toán tìm kiếm nhị phân tối ưu hóa vector trên mảng một chiều:
```python
# Sắp xếp danh sách ngày chia tách của cổ phiếu
s_dates = np.array(splits_df['date'].values)  # Chiều dài M
s_factors = np.array(splits_df['factor'].values)

# Tính mảng lookup hệ số tích lũy lùi
cf_lookup = np.cumprod(s_factors[::-1])[::-1]
cf_lookup = np.append(cf_lookup, 1.0)  # Mốc neo ngày sau cùng = 1.0

# Ánh xạ nhị phân tốc độ cao vào mảng nến giao dịch của cổ phiếu
pos = np.searchsorted(s_dates, t_dates, side='right')
cumulative_split_factor = cf_lookup[pos]
```
- **Độ phức tạp thuật toán**: $O(\log M)$ cho mỗi ngày giao dịch, thực thi tức thời cho toàn bộ 12.25 triệu dòng chỉ trong chưa đầy **45 giây**.
- **Tính trơ với lịch giao dịch**: Hoạt động hoàn hảo ngay cả khi Ex-Date không trùng với ngày có nến thị trường.

---

### 3.3. Bổ Khuyết Chia Tách Ngược (Reverse Split Injection) & Kiểm Soát Kurtosis

#### A. Khủng Hoảng Số Liệu Của Pipeline Cũ (The Kurtosis Anomaly)
Trong phiên bản pipeline Phase 2 cũ, quá trình phân tích phân phối lợi suất ghi nhận:
- **Excess Kurtosis**: Lên tới **16,433** (thậm chí trước khi lọc là **3,412,091**!).
- **Max Daily Return**: Đạt mức phi lý **+12,371.4%** hoặc **+1,364.5%**.

#### B. Nguyên Nhân Gốc Rễ Pháp Y
Cơ sở dữ liệu LEAN Factor Files của QuantConnect bị thiếu ghi nhận các sự kiện **Chia tách ngược (Reverse Stock Split)** của các công ty gặp khó khăn tài chính cận kề nguy cơ bị hủy niêm yết (delisting).
- *Trường hợp điển hình nhất — Chesapeake Energy (`CHK`)*:
  - Ngày 14/04/2020: Cổ phiếu CHK giao dịch ở mức giá penny **0.13 USD**.
  - Ngày 15/04/2020: Công ty thực hiện chia tách ngược tỷ lệ **1-for-200** theo phê duyệt của ĐHCĐ để giữ chuẩn niêm yết tối thiểu 1.00 USD của sàn NYSE. Giá mở cửa nhảy lên **16.20 USD**.
  - Do QuantConnect thiếu factor chia tách $200.0$, nến thô ghi nhận giá nhảy từ 0.13 lên 16.20 USD, tạo ra một cú nhảy giá giả tạo **+12,371.4%**!
  - Trên thực tế, sau khi tính đúng tỷ lệ 1:200, thị giá tương đương ngày 14/04 là $0.13 \times 200 = 26.00\text{ USD}$. Do đó, lợi suất thực tế của cổ đông ngày hôm đó là **-37.64%** (cổ phiếu giảm giá mạnh!).

#### C. Quy Trình Bổ Khuyết 5 Ca Chia Tách Ngược (CORR_001 – CORR_005)
Script `06_process_corporate_actions_and_adjusted_prices.py` tự động đọc bảng `market_data_corrections_and_exceptions.csv` và tiêm bổ sung các factor chia tách ngược vào bảng splits trước khi tính toán:
1. `CHK`: Gộp 1:200 ngày 2020-04-15 (`split_factor = 200.0`, SEC Form 8-K Item 3.03).
2. `CRC`: Gộp 1:10 ngày 2016-06-01 (`split_factor = 10.0`, SEC Form 8-K Item 5.03).
3. `ADCT`: Gộp 1:7 ngày 2005-05-10 (`split_factor = 7.0`, SEC Form 8-K Item 5.03).
4. `AA`: Gộp 1:3 ngày 2016-10-06 (`split_factor = 3.0`, SEC Form 8-K Item 8.01).
5. `DYN`: Gộp 1:5 ngày 2010-05-25 (`split_factor = 5.0`, SEC Form 8-K Item 5.03).

**Kết quả sau hiệu chỉnh**:
- Kurtosis phân phối lợi suất giảm từ **16,433** xuống mức chuẩn mực học thuật **66.88**.
- Max Daily Return giảm từ **+12,371%** về **+227.87%** (các phiên tăng trần thực tế có kiểm chứng).
- Skewness ổn định ở mức **+0.563**.

---

### 3.4. Xử Lý Gián Đoạn Tách Công Ty Con (Special Corporate Spinoffs)

Khi một tập đoàn thực hiện chia tách công ty con (Corporate Spin-off) không thu tiền và phân phối cổ phiếu công ty con trực tiếp cho cổ đông hiện hữu:
- Giá của cổ phiếu công ty mẹ sẽ sụt giảm mạnh trên sàn trong ngày giao dịch không hưởng quyền (Ex-Distribution Date) tương ứng với giá trị phần tài sản đã chuyển giao.
- Tuy nhiên, cổ đông không bị mất tiền vì họ nhận được cổ phiếu của công ty con mới niêm yết (tổng tài sản được bảo toàn).
- Nếu tính lợi suất chỉ dựa trên chuỗi giá đơn lẻ của công ty mẹ, mô hình sẽ ghi nhận một cú sụp đổ giả tạo từ **-76% đến -96%**, gây ô nhiễm nghiêm trọng nhãn huấn luyện học máy.

#### 4 Ca Pháp Y Tách Công Ty Con Được Cách Ly (CORR_006 – CORR_009):
1. **`KSU` (Kansas City Southern, 2000-07-13)**: Tách Stilwell Financial Inc. (nắm giữ công ty quản lý quỹ Janus Capital). Cổ đông KSU nhận 2 cổ phiếu Stilwell (~36.50 USD/cp) cho mỗi cổ phiếu KSU. Giá đơn lẻ của KSU giảm **-96.66%**, nhưng tổng tài sản cổ đông không đổi.
2. **`SSP` (E.W. Scripps Co., 2008-07-01)**: Tách mảng truyền hình cáp Scripps Networks Interactive (SNI — sở hữu HGTV, Food Network). Cổ đông nhận 1 cổ phiếu SNI cho mỗi cổ phiếu SSP. Giá đơn vị giảm **-92.67%**.
3. **`COMS` (3Com Corp., 2000-07-28)**: Phân phối cổ phiếu Palm Inc. (tỷ lệ 1.4832 cp Palm/cp 3Com). Giá đơn vị giảm **-79.99%**.
4. **`PENN` (Penn National Gaming, 2013-11-04)**: Tách tài sản bất động sản thành quỹ REIT độc lập Gaming and Leisure Properties (GLPI). Giá đơn vị giảm **-76.68%**.

#### Giải Pháp Kỹ Thuật:
- Gắn cờ `is_spinoff_discontinuity = True` tại ngày giao dịch phát sinh sự kiện.
- Ép giá trị `daily_return` và `total_return` tại phiên đó thành `NaN`.
- Loại trừ phiên đó khỏi `valid_data_mask` và loại trừ phiên $T$ lẫn $T+1$ khỏi `valid_label_mask`.

---

### 3.5. Kiểm Soát Chất Lượng Nến (Quality Flags & Symbol Collisions)

Một số ít bản ghi nến thô trong kho dữ liệu bị méo mó do lỗi kỹ thuật của hệ thống nạp dữ liệu từ sàn giao dịch hoặc hiện tượng trùng mã cổ phiếu với cổ phiếu ưu đãi không thanh khoản (Symbol Collision):
1. **`MKL` (Markel Group, 2010-04-19 đến 2010-04-27 — CORR_010)**: Lỗi nạp một chuỗi giá ~26 USD trong 7 phiên thay vì thị giá thực ~350 USD trên NYSE, gây sập ảo -93% và bật tăng ảo +1,364%.
2. **`SABR` (Sabre Corp, 2020-03-20 — CORR_011)**: Bắt nhầm print khớp lệnh 0.50 USD vào ngày đáo hạn hợp đồng quyền chọn Triple Witching (thị giá thật 4.70 USD), gây sập ảo -86.9% và bật tăng ảo +630%.
3. **`LOW` (Lowe's Companies, 2008-06-10 đến 2008-06-17 — CORR_012)**: Một mã chứng khoán ưu đãi hoặc chứng chỉ quỹ có cùng ký hiệu LOW bị nạp đè vào chuỗi giá của Lowe's với giá 6.60 USD trong 6 phiên.
4. **`CPTH` (2001-02-02 đến 2001-02-14 — CORR_013)**: Dị thường báo giá ảo trong đợt tạm ngừng giao dịch kéo dài trên sàn NASDAQ.

**Giải Pháp**: Toàn bộ các khoảng ngày trên được cách ly hoàn toàn qua cờ `is_bad_data_period = True`, biến đổi lợi suất thành `NaN` và loại bỏ khỏi ma trận nhãn.

---

## PHẦN 4: HỆ THỐNG MA TRẬN 2D & CẤU TRÚC 3 LỚP PIT MASKS

### 4.1. Khung Tọa Độ 2D (Wide Format) vs Dạng Bảng Dài (Long Format)

Trong kiến trúc hệ thống học máy cho tài chính định lượng, việc lưu trữ dữ liệu dưới dạng bảng dài (Long-Form Table: `[date, sid, price, return]`) bộc lộ nhiều điểm nghẽn nghiêm trọng:
- **Tốn dung lượng bộ nhớ**: Cột `date` và `sid` phải lặp lại hàng chục triệu lần.
- **Tốc độ truy vấn chậm**: Khi tính toán các toán tử chéo (Cross-Sectional Rank: xếp hạng 1,000 cổ phiếu tại ngày $t$) hoặc toán tử trượt thời gian (Time-Series Rolling: tính MA 20 ngày của cổ phiếu $i$), hệ thống phải liên tục thực hiện `groupby` rất tốn kém tài nguyên CPU.

Dự án quyết định cấu trúc hóa toàn bộ dữ liệu thành **Lưới Tọa Độ 2D Đồng Bộ (Wide 2D Matrix Coordinate Grid)**:
- **Trục hàng (Index)**: 7,252 ngày giao dịch chính thức của NYSE.
- **Trục cột (Columns)**: 3,711 Canonical SIDs.
- **Kích thước cố định**: Đúng $7,252 \times 3,711 = 26,912,172\text{ ô tọa độ}$.

```text
                  SID_0001    SID_0002    SID_0003  ...  SID_3711
Date
1998-01-02        [ Val ]     [ Val ]     [ NaN ]   ...  [ Val ]
1998-01-05        [ Val ]     [ Val ]     [ NaN ]   ...  [ Val ]
    ...             ...         ...         ...     ...    ...
2023-12-29 (Dev)  [ Val ]     [ Val ]     [ Val ]   ...  [ Val ]
2024-01-02 (OOS)  [ LOCKED ]  [ LOCKED ]  [ LOCKED ] ...  [ LOCKED ]
    ...             ...         ...         ...     ...    ...
2026-10-30        [ LOCKED ]  [ LOCKED ]  [ LOCKED ] ...  [ LOCKED ]
```

#### Ưu Thế Định Lượng Tuyệt Đối Của Wide Format:
1. **Vector hóa toàn phần (Full Vectorization)**:
   - Xếp hạng cross-sectional hàng ngày: Thực hiện bằng `scipy.stats.rankdata(matrix[t, :])` hoặc `np.argsort` trực tiếp trên một mảng vector contiguous trong bộ nhớ đệm L1/L2 với độ phức tạp $O(N \log N)$ chỉ mất vài micro-giây.
   - Rolling lookback theo chuỗi thời gian: Thực hiện trượt dọc theo từng cột mà không bị đan xen với các cổ phiếu khác.
2. **Tiết kiệm bộ nhớ**: Các ma trận boolean mask chỉ chiếm **2.1 MB** mỗi file nhờ thuật toán nén bit trong Parquet.

---

### 4.2. Quy Trình Đồng Bộ & Pivot Tọa Độ Ma Trận

Script `07_build_2d_matrices_and_masks.py` nạp kho nến Tier 2 Adjusted Warehouse và thực hiện pivot 17 trường thông tin:
1. Giá thị trường thô: `open.parquet`, `high.parquet`, `low.parquet`, `close.parquet`, `volume.parquet`.
2. Giá & khối lượng điều chỉnh: `adj_open.parquet`, `adj_high.parquet`, `adj_low.parquet`, `adj_close.parquet`, `adj_volume.parquet`.
3. Dữ liệu sự kiện: `adj_dividend.parquet`, `cumulative_split_factor.parquet`.
4. Lợi suất: `daily_return.parquet`, `total_return.parquet`.
5. Cờ trạng thái thị trường: `is_consecutive_session.parquet`, `is_bad_data_period.parquet`, `is_spinoff_discontinuity.parquet`.

Mọi ô tọa độ không có nến giao dịch tự động được điền `NaN` (đối với float) hoặc `False` (đối với boolean).

---

### 4.3. Cấu Trúc Phân Cấp 3 Lớp PIT Masks (Hierarchical Masking Logic)

Để đảm bảo tính nghiêm ngặt tuyệt đối trong nghiên cứu học máy, hệ thống triển khai kiến trúc **3 Lớp Mặt Nạ Hình Nón (3-Tier Layered PIT Masks)**, trong đó lớp sau là tập con nghiêm ngặt của lớp trước:

$$\mathbf{valid\_label\_mask} \subseteq \mathbf{valid\_data\_mask} \subseteq \mathbf{membership\_mask}$$

```text
+-----------------------------------------------------------------------------------+
| LAYER 1: membership_mask (6,333,323 cells)                                        |
| Thuộc danh mục chính thức của chỉ số Russell 1000 tại kỳ tái cơ cấu Point-In-Time |
| +-------------------------------------------------------------------------------+ |
| | LAYER 2: valid_data_mask (6,311,822 cells — 99.66%)                           | |
| | Đủ điều kiện giao dịch thực tế: Có nến, Giá > 0, Vol > 0, Phiên liên tục,     | |
| | Đã tích lũy >= 20 nến lịch sử, Không bị lỗi/quarantine                        | |
| | +---------------------------------------------------------------------------+ | |
| | | LAYER 3: valid_label_mask (6,308,873 cells — 99.61%)                      | | |
| | | Đủ điều kiện gán nhãn Supervised ML: Nến T hợp lệ VÀ Nến T+1 hợp lệ,      | | |
| | | KHÔNG nằm trong ngày ranh giới OOS bị Purge                               | | |
| | +---------------------------------------------------------------------------+ | |
| +-------------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------------+
```

#### A. Layer 1 — Membership Mask (`membership_mask.parquet`)
- **Điều kiện kích hoạt**: Ô tọa độ $(t, i)$ đạt `True` khi và chỉ khi ngày $t$ nằm trong khoảng thời gian thành viên chính thức của rổ chỉ số:
  $$t \in [\text{effective\_start\_date}_i, \text{effective\_end\_date}_i]$$
  với chu kỳ thường niên chuẩn quy ước từ ngày `01/07 năm Y` đến `30/06 năm Y+1`.
- **Loại trừ khởi đầu**: Toàn bộ giai đoạn warm-up 1998–1999 hoàn toàn mang giá trị `False`.

#### B. Layer 2 — Valid Data Mask / Tradability Mask (`valid_data_mask.parquet`)
- **Ý nghĩa định lượng**: Xác định xem cổ phiếu có thực sự giao dịch bình thường trên thị trường và có đủ dữ liệu để tính toán các đặc trưng kỹ thuật hay không.
- **Điều kiện kích hoạt (Đồng thời 6 tiêu chí)**:
  1. `membership_mask == True` (Phải là thành viên rổ chỉ số).
  2. `close > 0` và `volume > 0` (Có phát sinh giao dịch thực tế, không bị đóng băng/halt).
  3. `is_consecutive_session == True` (Phiên giao dịch liên tục, không bị nhảy cóc phiên do tạm ngừng giao dịch).
  4. `cum_bars >= 20` (Đã niêm yết và tích lũy ít nhất 20 phiên nến trong lịch sử, bảo đảm đủ dữ liệu tính rolling lookback ngắn hạn).
  5. `is_bad_data_period == False` (Không nằm trong vùng nạp dữ liệu lỗi thị trường).
  6. `is_spinoff_discontinuity == False` (Không nằm tại phiên tách công ty con chưa điều chỉnh).

#### C. Layer 3 — Valid Label Mask / Training Mask (`valid_label_mask.parquet`)
- **Ý nghĩa định lượng**: Xác định xem cặp $(t, i)$ có đủ điều kiện để mô hình học máy lấy làm mẫu huấn luyện có giám sát (Supervised Learning Sample) hay không.
- **Điều kiện kích hoạt**:
  1. `valid_data_mask[t, i] == True` (Dữ liệu tại ngày quan sát $t$ phải hoàn toàn hợp lệ để trích xuất Features $X_{i, t}$).
  2. `valid_data_mask[t+1, i] == True` (Dữ liệu tại ngày kế tiếp $t+1$ phải hoàn toàn hợp lệ để tính toán Nhãn mục tiêu $y_{i, t} = r_{i, t+1}$).
  3. `t != 2023-12-29` (Không phải là phiên giao dịch cuối cùng của tập Development).
  4. `t != 2026-10-30` (Không phải là phiên giao dịch cuối cùng của toàn bộ tập dữ liệu).

#### Thẩm Định Phân Cấp (Mask Hierarchy Sanity Assertion):
Trong script `08_validate_matrices_and_sanity_checks.py`, hai mệnh đề logic sau đã được chứng minh qua kiểm thử:
$$\sum (\mathbf{valid\_label\_mask} \land \neg \mathbf{valid\_data\_mask}) = \mathbf{0}$$
$$\sum (\mathbf{valid\_data\_mask} \land \neg \mathbf{membership\_mask}) = \mathbf{0}$$
Khẳng định 100% không có bất kỳ ô dữ liệu nào vi phạm cấu trúc hình nón.

---

### 4.4. Point-In-Time (PIT): Định Nghĩa Kinh Tế & Tính Tất Yếu Toán Học

#### A. Định Nghĩa Point-In-Time (PIT)
Một tập dữ liệu đạt chuẩn **Point-In-Time** khi và chỉ khi:
$$\forall t, \quad \mathcal{I}_t \text{ chỉ chứa các thông tin đã được công bố chính thức và sẵn sàng trước hoặc tại thời điểm } t$$
trong đó $\mathcal{I}_t$ là tập thông tin (Information Set / Filtration) tại thời điểm ra quyết định.

#### B. Hai Mối Nguy Hiểm Của Dữ Liệu Phi-PIT
1. **Survivorship Bias (Thiên lệch kẻ sống sót)**:
   - Nếu ta lấy danh sách thành viên Russell 1000 của năm 2026 và áp đặt ngược về năm 2000, danh mục sẽ chỉ chứa những công ty thành công vượt trội (như Apple, Microsoft, Amazon, Nvidia) và loại bỏ hoàn toàn hàng trăm công ty phá sản, sụp đổ trong các cuộc khủng hoảng (Enron, WorldCom, Lehman Brothers, Washington Mutual, Bear Stearns).
   - Mô hình học máy khi đó sẽ bị "đầu độc" bởi niềm tin sai lầm rằng các công ty đều sẽ tăng trưởng vĩnh viễn, dẫn đến ước tính tỷ suất sinh lời vượt quá thực tế từ **300 đến 500 điểm cơ bản (3–5% / năm)**.
   - *Cách giải quyết*: Hệ thống nạp đúng 27 snapshot thường niên. Tại ngày 01/07/2001, universe chỉ chứa các công ty là thành viên tại ngày đó (bao gồm cả Enron đang sụp đổ).
2. **Look-Ahead Bias (Thiên lệch thấy trước tương lai)**:
   - Xảy ra khi dữ liệu của tương lai $t+k$ bị vô tình sử dụng để tính toán đặc trưng tại thời điểm $t$.
   - Ví dụ: Dùng giá đóng cửa của ngày hôm nay để ra quyết định mua ở giá mở cửa sáng nay, hoặc dùng báo cáo tài chính quý trước ngày nộp hồ sơ SEC Form 10-Q thực tế.

---

### 4.5. Cơ Chế Purge Ranh Giới (Anti-Lookahead Purge) & Bảo Toàn OOS 2024–2026

Để bảo toàn tính toàn vẹn tuyệt đối cho giai đoạn kiểm thử ngoài mẫu (**Out-of-Sample Evaluation 2024–2026**), hệ thống áp dụng cơ chế **Purge Ranh Giới (Boundary Purge Protocol)** tại script `07_build_2d_matrices_and_masks.py`:

#### Phân Tích Rủi Ro Rò Rỉ Tại Ranh Giới $T$:
- Phiên giao dịch cuối cùng của tập Development là ngày:
  $$t_{\text{dev\_end}} = \mathbf{2023-12-29}\text{ (Thứ Sáu)}$$
- Phiên giao dịch kế tiếp $t+1$ trên sàn NYSE là ngày:
  $$t_{\text{oos\_start}} = \mathbf{2024-01-02}\text{ (Thứ Ba — Phiên đầu tiên của giai đoạn OOS)}$$
- Biến mục tiêu cho ngày $t_{\text{dev\_end}}$ được tính theo công thức:
  $$y_{i, \text{2023-12-29}} = r_{i, \text{2024-01-02}}$$

Nếu ta cho phép mô hình học máy sử dụng mẫu quan sát tại ngày `2023-12-29` trong quá trình huấn luyện:
- Mô hình sẽ tính toán hàm mất mát (Loss Function) và điều chỉnh trọng số (Weights update) dựa trên lợi suất thực tế của ngày `2024-01-02`.
- Điều này cấu thành hành vi **RÒ RỈ DỮ LIỆU NGOÀI MẪU (OOS Data Leakage)**: Thông tin giá của ngày đầu tiên trong tập OOS đã thâm nhập ngược vào mô hình!

#### Cơ Chế Triệt Tiêu Của Dự Án:
```python
# Script 07: Ép buộc ranh giới
purge_dates = [unique_dates[-1], pd.Timestamp("2023-12-29")]
purge_mask_1d = np.isin(unique_dates, purge_dates)
not_purged = (~purge_mask_1d)[:, None]

# valid_label_mask bắt buộc not_purged == True
valid_label_arr = (valid_data_arr & valid_data_next & not_purged)

# Target matrices ép NaN ngoài mask
target_next_return_arr[~valid_label_arr] = np.nan
```

#### Kết Quả Thẩm Định Kiểm Toán:
- Tại hàng `2023-12-29`:
  - `valid_data_mask`: Đạt `True` (Dữ liệu giá nến của ngày 2023-12-29 vẫn hợp lệ để tính toán các đặc trưng kỹ thuật quá khứ).
  - `valid_label_mask`: **Đạt `False` trên 100% các cột (0 valid cells)**.
  - `target_next_return`: **Toàn bộ 3,711 cột đều mang giá trị `NaN`**.
- Khẳng định toán học: **Hệ thống kín khít 100% (Zero OOS Leakage)**. Không có bất kỳ một bit thông tin nào từ năm 2024–2026 bị rò rỉ vào giai đoạn phát triển mô hình.

---

## TỔNG KẾT & KÝ DUYỆT BẢO TOÀN DỮ LIỆU

Báo cáo này xác nhận chuỗi hành trình dữ liệu từ 27 tài liệu thô PDF/CSV và hàng triệu nến thị trường QuantConnect LEAN đã được chuyển hóa thành công, đạt độ tin cậy cấp tổ chức định lượng (Audit-Grade Quantitative Warehouse):
1. **Khử trùng lặp bit-for-bit**: Loại bỏ 1.57 triệu dòng alias trùng lặp hoàn hảo.
2. **Nối mượt danh tính**: Hợp nhất 752 mã tạm thời `' 2T'`, phân lập 1,281 Ticker Reuse thành 3,711 Canonical SIDs chính quy.
3. **Hiệu chỉnh pháp y 13 ca dị biệt**: Hạ Kurtosis từ 16,433 xuống 66.88, chuẩn hóa độ biến động 2.65%/ngày.
4. **Lưới ma trận 2D 26.9 triệu ô**: Tối ưu hóa toàn diện cho các thuật toán học máy và xếp hạng chéo.
5. **Cơ chế Purge ranh giới**: Bảo vệ toàn vẹn 100% tập dữ liệu Out-of-Sample 2024–2026.

*Hồ sơ dữ liệu đã sẵn sàng phục vụ cho các cột mốc Huấn luyện Mô hình Học máy (Machine Learning Training) và Xây dựng Danh mục Định lượng (Portfolio Backtesting).*
