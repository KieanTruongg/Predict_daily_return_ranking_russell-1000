# 🔄 Data Pipeline Directed Acyclic Graph (DAG) & Execution Specification

> **Dự án**: Russell 1000 Daily Return Ranking Prediction Engine  
> **Tài liệu**: Đặc tả Kiến trúc Pipeline DAG, Phân định Thực thi Cloud/Local, và Quyền sở hữu Bảng Thẩm định  
> **Cập nhật**: Tháng 11/2026  
> **Trạng thái**: Hoạt động chính thức (Authoritative Standard)

---

## 1. 📌 TỔNG QUAN HỆ THỐNG & PHÂN VÙNG DỮ LIỆU

Pipeline xử lý dữ liệu của dự án được thiết kế theo kiến trúc kho dữ liệu định lượng đa tầng (Multi-tier Quantitative Warehouse), chuyển hóa từ các tài liệu snapshot thường niên thô và nến giá thị trường cấp tick/phút thành hệ thống lưới tọa độ ma trận 2D ($7,252 \text{ ngày giao dịch NYSE} \times 3,711 \text{ Canonical SIDs}$) phục vụ trực tiếp cho mô hình Machine Learning Supervised Ranking.

### 1.1. Phân Vùng Lịch Sử 3 Giai Đoạn (7,252 Phiên Giao Dịch NYSE)

Toàn bộ chuỗi thời gian từ **1998-01-02 đến 2026-10-30** bao gồm **7,252 ngày giao dịch chính thức của sàn NYSE**, được phân hoạch nghiêm ngặt:

| Giai Đoạn | Khoảng Thời Gian | Số Phiên NYSE | Mục Đích Định Lượng & Ranh Giới Kỹ Thuật |
|:---|:---:|:---:|:---|
| **Warm-up Window** | 1998-01-02 đến 2000-06-30 | **630 phiên** | Cung cấp lịch sử nến giá và lợi suất tối thiểu 2 năm để khởi tạo các chỉ báo kỹ thuật, rolling features dài hạn (SMA252, Realized Volatility 252d, Momentum 1y). Giai đoạn này **không tham gia tính loss hay huấn luyện mô hình**. |
| **Development Window** | 2000-07-01 đến 2023-12-29 | **5,911 phiên** | Phục vụ khám phá dữ liệu (EDA), trích xuất đặc trưng (Feature Engineering), thẩm định pháp y dữ liệu, cross-validation theo chu kỳ tái cơ cấu thường niên, và huấn luyện mô hình. |
| **Out-of-Sample (OOS)** | 2024-01-02 đến 2026-10-30 | **711 phiên** | **ĐÓNG BĂNG NGHIÊM NGẶT (STRICTLY FROZEN & ISOLATED)**. Dành riêng cho kiểm định mù cuối cùng (Final Blind Test). Tuyệt đối không thăm dò hay nạp trong quá trình thiết kế và huấn luyện. |
| **Tổng Cộng Toàn Kỳ** | **1998-01-02 đến 2026-10-30** | **7,252 phiên** | $630 + 5,911 + 711 = 7,252$ phiên giao dịch. |

> **Cơ chế Purge Ranh Giới (Boundary Purge)**: Nhãn mục tiêu tương lai $T+1$ (`target_next_return` và `target_next_total_return`) tại phiên giao dịch cuối cùng của tập Development (**2023-12-29**) bị cưỡng bức gán giá trị `NaN` trong ma trận 2D, đảm bảo ngăn ngừa rò rỉ thông tin sang phiên đầu tiên của tập OOS (**2024-01-02**).

---

## 2. 🗂️ PHÂN ĐỊNH MÔI TRƯỜNG THỰC THI: CLOUD-ONLY VS. LOCAL CLI

Hệ thống mã nguồn pipeline bao gồm 13 tập lệnh thực thi, được phân tách rành mạch theo hạ tầng môi trường:

### 2.1. Tập Lệnh Chạy Trên Đám Mây (Cloud-Only Scripts — QuantConnect LEAN Cloud)

Các tập lệnh này phụ thuộc vào API độc quyền của **QuantConnect LEAN Research Cloud Engine** (`AlgorithmImports`, `QuantConnect.Data.Market`, LEAN Factor Files). Chúng không thể chạy độc lập trên máy trạm cục bộ nếu không có tài khoản QuantConnect và đăng ký thuê bao dữ liệu chứng khoán Mỹ US Equity:

| Tên Script | Hạ Tầng | Đầu Vào | Đầu Ra | Mô Tả Chức Năng |
|:---|:---:|:---|:---|:---|
| `02_quantconnect_availability_scan.py` | QC Cloud | Ticker universe nạp dạng Base64 qua LEAN Research Notebook | Nhật ký log quét độ sẵn sàng | Khảo sát 2,884 mã định danh trên cơ sở dữ liệu QuantConnect LEAN, thống kê tỷ lệ sẵn sàng của dữ liệu nến thô. |
| `02_quantconnect_export_10_batches.py` | QC Cloud | Ticker universe chia 10 batch (`BATCH_INDEX = 0..9`), chế độ nến `Raw` | 10 tệp nén `russell_market_batch_{XX}_of_10.zip` | Trích xuất toàn bộ dữ liệu nến thô từng phút/ngày từ 1998–2026 cho 2,871 tickers hợp lệ, đóng gói thành 10 ZIP files. |
| `05_quantconnect_export_corporate_actions.py` | QC Cloud | Ticker universe, LEAN Factor Files API | `russell1000_corporate_actions_1998_2026.zip` | Trích xuất toàn bộ dữ liệu chia tách (Splits) và cổ tức tiền mặt (Dividends) từ hệ thống Factor Files của QuantConnect. |

### 2.2. Tập Lệnh Chạy Cục Bộ (Local CLI Scripts — Python Môi Trường Trạm)

Các tập lệnh này chạy 100% độc lập trên máy trạm hoặc máy chủ nội bộ thông qua môi trường ảo Python tiêu chuẩn (`pandas`, `numpy`, `scipy`, `pyarrow`, `pypdf`, `matplotlib`):

| Tên Script | Thứ Tự DAG | Đầu Vào Chính | Đầu Ra Chính |
|:---|:---:|:---|:---|
| `01_parse_all_universe.py` | **1** | `data/raw/universe/raw_universe/*` | `data/raw/universe/russell1000_pit_by_year.json`, `russell1000_constituents.csv` |
| `03_process_10_batches_to_parquet.py` | **3** | 10 tệp ZIP tại `data/raw/market_data/` | `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` |
| `04_audit_identity_and_build_canonical_mapping.py` | **4** | Master Raw Parquet (từ Step 03) | `..._daily_ohlcv_canonical_1998_2026.parquet`, `canonical_security_mapping.csv` |
| `06_process_corporate_actions_and_adjusted_prices.py` | **6** | Canonical Parquet, Splits, Divs, 13 Hiệu chỉnh | `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` (Tier 2 Warehouse) |
| `04b_generate_comprehensive_step3_audits.py` | **7a** *(Hậu 06)* | Tier 2 Adjusted Warehouse Parquet, PIT JSON | `docs/Data report/market_data_audit/tables/temporal_mapping_heuristic_audit.csv` |
| `05_rigorous_pit_membership_reconstruction.py` | **7b** *(Hậu 06)* | Tier 2 Adjusted Warehouse Parquet, PIT JSON | `docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv` |
| `07_build_2d_matrices_and_masks.py` | **8** | Tier 2 Adjusted Warehouse Parquet, Temporal Mapping CSV | 26 tệp 2D Parquet tại `data/processed/matrices/` |
| `08_validate_matrices_and_sanity_checks.py` | **9** | 2D Matrices, Tier 2 Adjusted Warehouse | Báo cáo kiểm định Sanity Check 50,000 ô ngẫu nhiên |
| `09_run_development_eda.py` | **10** | 2D Matrices (lọc tập Development 2000–2023) | Biểu đồ EDA PNG 300 DPI và bảng CSV Moments thống kê |
| `10_investigate_extreme_returns.py` | **11** | 2D Matrices, Bảng hiệu chỉnh CORR_001..CORR_013 | Bảng kiểm toán Top 50 +/- return cực đoan |
| `build_comprehensive_project_report.py` | **12** | Toàn bộ bảng kiểm toán CSV và biểu đồ PNG | `docs/Data report/institutional_pipeline_report.html` |

---

## 3. 📊 ĐỒ THỊ PHỤ THUỘC (DIRECTED ACYCLIC GRAPH — DAG)

Sơ đồ dưới đây thể hiện chính xác luồng dữ liệu và quan hệ phụ thuộc nhân quả giữa các tập lệnh:

```text
                                  +---------------------------------------+
                                  |     data/raw/universe/raw_universe/    |
                                  |     (27 Snapshot files 2000-2026)     |
                                  +---------------------------------------+
                                                      │
                                                      ▼ [Local CLI]
                                      [ 01_parse_all_universe.py ]
                                                      │
                                                      ├───────────────────────────────────┐
                                                      ▼                                   ▼
                                      russell1000_pit_by_year.json           russell1000_constituents.csv
                                                      │
                                                      ▼ [QC Cloud]
                                   [ 02_quantconnect_export_10_batches.py ]
                                                      │
                                                      ▼ (Download 10 ZIPs to data/raw/market_data/)
                                   [ 03_process_10_batches_to_parquet.py ] [Local CLI]
                                                      │
                                                      ▼
                       data/processed/constituents_market_data/
                       russell1000_constituents_daily_ohlcv_1998_2026.parquet (Master Raw Warehouse)
                                                      │
                                                      ▼ [Local CLI]
                                [ 04_audit_identity_and_build_canonical_mapping.py ]
                                                      │
                        ┌─────────────────────────────┴─────────────────────────────┐
                        ▼                                                           ▼
         canonical_security_mapping.csv                   russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet
                        │                                                           │
                        │        +--------------------------------------------------+
                        │        │
                        │        │  [QC Cloud]
                        │        ├────────────────► [ 05_quantconnect_export_corporate_actions.py ]
                        │        │                                    │
                        │        │                                    ▼ (Extract splits.csv, dividends.csv)
                        │        │                  data/processed/constituents_market_data/corporate_actions/
                        │        │                                    │
                        │        ▼                                    ▼
                        │   +-----------------------------------------------------------+
                        └──►| 06_process_corporate_actions_and_adjusted_prices.py       | [Local CLI]
                            | (Injects 13 corrections, backward split CF, total return) |
                            +-----------------------------------------------------------+
                                                      │
                                                      ▼
                       data/processed/constituents_market_data/
                       russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet (Tier 2 Adjusted Warehouse)
                                                      │
                        ┌─────────────────────────────┴─────────────────────────────┐
                        │                                                           │
                        ▼ [Local CLI]                                               ▼ [Local CLI]
  [ 04b_generate_comprehensive_step3_audits.py ]             [ 05_rigorous_pit_membership_reconstruction.py ]
  (Thẩm định heuristic & đối soát Bước 3)                    (Tái thiết lập Point-In-Time 6 cấp độ bằng chứng)
                        │                                                           │
                        ▼                                                           ▼
    docs/Data report/market_data_audit/tables/                  docs/Data report/market_data_audit/tables/
    temporal_mapping_heuristic_audit.csv                        universe_constituent_temporal_mapping.csv
                        │                                                           │
                        └─────────────────────────────┬─────────────────────────────┘
                                                      │
                                                      ▼ [Local CLI]
                                     [ 07_build_2d_matrices_and_masks.py ]
                                     (7,252 dates x 3,711 SIDs, 3 masks, Purge 2023-12-29)
                                                      │
                                                      ▼
                                       data/processed/matrices/ (26 Parquet files)
                                                      │
                        ┌─────────────────────────────┼─────────────────────────────┐
                        ▼                             ▼                             ▼
        [ 08_validate_matrices...py ]     [ 09_run_development_eda.py ]     [ 10_investigate_extreme...py ]
        (Sanity check 50,000 ô)           (Moments, Dispersion, Deciles)    (Top 50 returns & SEC 8-K)
                        │                             │                             │
                        └─────────────────────────────┼─────────────────────────────┘
                                                      │
                                                      ▼ [Local CLI]
                                   [ build_comprehensive_project_report.py ]
                                                      │
                                                      ▼
                           docs/Data report/institutional_pipeline_report.html
```

---

## 4. 🔍 BẢN CHẤT QUAN HỆ PHỤ THUỘC GIỮA BƯỚC 04b, 05 VÀ 06

Một điểm cốt lõi trong pipeline cần được làm sáng tỏ là sự khác biệt giữa **tiền tố đánh số tập lệnh** và **thứ tự thực thi thực tế**:

### 4.1. Tại sao Bước 04b và Bước 05 (Rigorous) lại phụ thuộc vào Bước 06?

Mặc dù mang tên bắt đầu bằng `04b` và `05`, hai script:
- `04b_generate_comprehensive_step3_audits.py`
- `05_rigorous_pit_membership_reconstruction.py`

**ĐỀU TIÊU THỤ (CONSUME)** kho dữ liệu giá điều chỉnh Tier 2:
```text
data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet
```

Tệp Parquet này **chỉ được tạo ra sau khi Script 06 kết thúc thành công**. 

Lý do về mặt nghiệp vụ định lượng:
1. **Kiểm tra độ phủ thực tế (Active Trading Coverage)**: Để xác định một mã cổ phiếu thành viên Russell 1000 có thực sự giao dịch trong chu kỳ thường niên $[01/07/Y \text{ đến } 30/06/Y+1]$ hay không, hệ thống phải đối soát chéo từng ngày giao dịch thực tế đối với dữ liệu giá đã được khử trùng, gán nhãn Canonical SIDs, và điều chỉnh đầy đủ corporate actions từ Bước 06.
2. **Xác minh 6 cấp độ bằng chứng (6 Evidence Levels)**: Script 05 đối chiếu các trường hợp thay đổi mã (ticker change), sáp nhập (M&A), hoặc giao dịch dưới dạng placeholder `' 2T'` trên chuỗi dữ liệu giá liên tục của Bước 06 để phân loại chính xác mức độ tin cậy của quyền thành viên Point-In-Time.
3. **Thứ tự thực thi chuẩn**:
   $$\mathbf{01} \longrightarrow \mathbf{02} \longrightarrow \mathbf{03} \longrightarrow \mathbf{04} \longrightarrow \mathbf{05\ (QC\ Export)} \longrightarrow \mathbf{06} \longrightarrow \mathbf{(04b\ \&\ 05\ Rigorous)} \longrightarrow \mathbf{07} \longrightarrow \mathbf{08} \longrightarrow \mathbf{09} \longrightarrow \mathbf{10}$$

---

## 5. 🛡️ PHÂN ĐỊNH QUYỀN SỞ HỮU BẢNG AUDIT ĐẦU RA (SCHEMA SEPARATION)

Trước đây, cả Script `04b` và Script `05_rigorous` đều ghi ra tệp có cùng tên `universe_constituent_temporal_mapping.csv`, dẫn đến việc ghi đè cấu trúc schema khác nhau tùy theo script nào chạy sau. Hệ thống hiện đã phân định rõ ràng quyền sở hữu đơn nhất (Single Producer Ownership):

### 5.1. Bảng Do Bước 04b Độc Quyền Ghi Nhận
- **Đường dẫn**: `docs/Data report/market_data_audit/tables/temporal_mapping_heuristic_audit.csv`
- **Mục đích**: Bảng đối soát heuristic cho Bước 3, ghi nhận số lượng nến giá trong kỳ, khoảng ngày hiệu lực thực tế và phân loại phương án giải quyết (resolution category).
- **Cấu trúc Schema (10 cột)**:
  ```text
  [period_year, period_start, period_end, source_ticker, assigned_canonical_sids, 
   resolution_category, verification_status, bars_in_period, active_date_range, notes]
  ```

### 5.2. Bảng Do Bước 05 Độc Quyền Ghi Nhận (Bảng Chính Thức)
- **Đường dẫn**: `docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv`
- **Mục đích**: Bảng ánh xạ thời gian Point-In-Time chính thức cấp tổ chức, phân loại theo 6 cấp độ bằng chứng pháp y (`CONFIRMED_DIRECT`, `CONFIRMED_2T_STITCH`, `CONFIRMED_TICKER_CHANGE`, `FALLBACK_PARTIAL_BARS`, `UNRESOLVED_ZERO_BARS`, `DELISTED_EARLY`). Bảng này là đầu vào trực tiếp cho Bước 07 để xây dựng mặt nạ `membership_mask.parquet`.
- **Cấu trúc Schema (9 cột)**:
  ```text
  [period_year, period_start, period_end, source_ticker, assigned_canonical_sids, 
   evidence_level, verification_status, validity_overlap_range, notes]
  ```

> **Nguyên tắc bất biến**: Mỗi bảng CSV chỉ do đúng một script chịu trách nhiệm sản sinh. Tuyệt đối không có sự xung đột hay ghi đè schema chéo giữa `04b` và `05`.

---

## 6. 📂 QUY ƯỚC ĐƯỜNG DẪN DỮ LIỆU CHUẨN TRÊN HỆ THỐNG TỆP

Mọi tập lệnh và tài liệu trong kho lưu trữ tuân thủ tuyệt đối cấu trúc thư mục sau:

```text
Predict_daily_return_rankings/
├── configs/
│   └── base_config.yaml                        # Cấu hình chuẩn trỏ tới Tier 2 Warehouse & 2D Matrices
│
├── data/
│   ├── raw/
│   │   ├── universe/
│   │   │   ├── raw_universe/                   # 27 tệp snapshot thô (PDF, XLS, CSV, JSON) 2000-2026
│   │   │   ├── russell1000_pit_by_year.json    # JSON từ điển chuẩn hóa 27 năm PIT constituents
│   │   │   ├── russell1000_constituents.csv    # Danh mục tổng hợp 2,884 mã định danh
│   │   │   └── extraction_quality_report.csv   # Đánh giá chất lượng trích xuất tài liệu
│   │   │
│   │   └── market_data/                        # 10 tệp ZIP nến thô tải từ QuantConnect Cloud
│   │       ├── russell_market_batch_01_of_10.zip ... batch_10_of_10.zip
│   │       ├── master_batch_status.csv
│   │       └── master_batch_identity.csv
│   │
│   └── processed/
│       ├── constituents_market_data/           # Kho dữ liệu nến thành viên hợp nhất & điều chỉnh
│       │   ├── by_year/                        # Parquet nến thô phân vùng theo từng năm (1998–2026)
│       │   ├── russell1000_constituents_daily_ohlcv_1998_2026.parquet # Master Raw (Step 03 -> Step 04)
│       │   ├── russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet # Canonical SIDs
│       │   ├── corporate_actions/              # splits.csv và dividends.csv trích xuất từ QC
│       │   └── russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet  # Tier 2 Adjusted Warehouse
│       │
│       └── matrices/                           # 26 ma trận 2D Parquet (7,252 ngày x 3,711 SIDs)
│           ├── matrix_dates_index.parquet      # Trục hàng: 7,252 ngày giao dịch NYSE
│           ├── matrix_columns_sids.parquet     # Trục cột: 3,711 Canonical SIDs
│           ├── close.parquet ... volume.parquet# Giá và khối lượng thô
│           ├── adj_close.parquet ...           # Giá và khối lượng điều chỉnh dồn tích
│           ├── adj_dividend.parquet            # Cổ tức tiền mặt điều chỉnh
│           ├── cumulative_split_factor.parquet # Hệ số chia tách tích lũy CF
│           ├── daily_return.parquet            # Lợi suất đóng cửa ngày float64
│           ├── total_return.parquet            # Tổng tỷ suất sinh lời gồm cổ tức
│           ├── membership_mask.parquet         # Layer 1: PIT Universe Mask
│           ├── valid_data_mask.parquet         # Layer 2: Giao dịch hợp lệ (không halt, không bad tick)
│           ├── valid_label_mask.parquet        # Layer 3: Hợp lệ để tính nhãn T+1 (đã purge 2023-12-29)
│           ├── target_next_return.parquet      # Biến mục tiêu ngày mai T+1
│           └── target_next_total_return.parquet# Biến mục tiêu tổng lợi suất ngày mai T+1
│
├── docs/
│   ├── pipeline_dag.md                         # Tài liệu này (Đặc tả DAG & phân định script)
│   └── Data report/
│       ├── institutional_pipeline_report.html  # Báo cáo kết quả tổng hợp HTML
│       └── market_data_audit/tables/           # Bảng kiểm toán định lượng
│           ├── temporal_mapping_heuristic_audit.csv      # Bảng audit Bước 04b
│           ├── universe_constituent_temporal_mapping.csv # Bảng chính thức Bước 05
│           └── ... (39 bảng kiểm toán chuyên sâu khác)
│
└── scripts/
    └── 01_pipeline/                            # 13 Scripts hoạt động chính thức
```

---

## 7. 🔬 PHƯƠNG PHÁP LUẬN ĐỊNH LƯỢNG & CÁC GIỚI HẠN THỰC NGHIỆM

Để đảm bảo tính trung thực học thuật và quy chuẩn nghiên cứu định lượng cấp tổ chức, các phương pháp luận trong pipeline được định nghĩa song hành cùng các giới hạn thực nghiệm khách quan:

### 7.1. Giảm Thiểu Thiên Lệch Sống Sót (Survivorship Bias Mitigation)
- **Phương pháp**: Sử dụng 27 danh sách snapshot thường niên chính thức từ nguồn tài liệu gốc của FTSE Russell / iShares, áp dụng quy ước hiệu lực niên độ $[01/07 \text{ năm } Y \text{ đến } 30/06 \text{ năm } Y+1]$. Hệ thống giữ lại toàn bộ các công ty đã phá sản, bị hủy niêm yết, hoặc bị thâu tóm trong lịch sử (Enron, WorldCom, Lehman Brothers, Bear Stearns...).
- **Giới hạn thực nghiệm còn lại**: 
  1. *Tái cơ cấu nội năm (Intra-year reconstitution lag)*: Quy ước niên độ cố định không phản ánh các lần thêm/bớt đột xuất phát sinh giữa chu kỳ do FTSE Russell thực hiện (ví dụ: các đợt IPO lớn được đưa vào rổ chỉ số giữa năm).
  2. *Hạn chế thị trường OTC*: Đối với các cổ phiếu bị hủy niêm yết khỏi sàn chính (NYSE/NASDAQ) và chuyển sang giao dịch trên sàn phi tập trung (Pink Sheets/OTC), nguồn cấp dữ liệu chuẩn của QuantConnect không duy trì đầy đủ nến thanh khoản giai đoạn OTC, dẫn đến một số mã kết thúc chuỗi giá sớm hơn ngày kết thúc niên độ chỉ số.

### 7.2. Ngăn Ngừa Rò Rỉ Thông Tin Tương Lai (Look-Ahead Bias Prevention)
- **Phương pháp**:
  - Tách bạch cửa sổ khởi tạo 2 năm Warm-up (1998–2000, 630 phiên) để các hàm rolling window không bị thiếu dữ liệu ban đầu.
  - Phân vùng phát triển (Development: 2000–2023, 5,911 phiên) và ngoài mẫu (OOS: 2024–2026, 711 phiên).
  - Triệt tiêu nhãn tương lai tại phiên ranh giới: Gán `NaN` vào hàng ngày `2023-12-29` của các ma trận nhãn `target_next_*`, ngăn chặn tuyệt đối việc mô hình tại ngày cuối tập Development học trước tỷ suất sinh lời của ngày đầu tập OOS.
- **Giới hạn thực nghiệm còn lại**: Việc chia tách và điều chỉnh giá sử dụng hệ số chia tách dồn tích lùi ($CF_t = \prod_{s > t} S_s$). Trong ứng dụng backtest danh mục thực tế (Live Trading), việc tính giá điều chỉnh cần tuân thủ chế độ Point-In-Time Factor (chỉ biết factor khi sự kiện đã xảy ra). Ma trận 2D hiện tại cung cấp cả giá thô nguyên bản (`close`, `open`...) và giá điều chỉnh dồn tích (`adj_close`...) để người dùng lựa chọn chế độ mô phỏng phù hợp.

### 7.3. Điều Chỉnh Sự Kiện Doanh Nghiệp & Tái Đầu Tư Cổ Tức (Corporate Actions)
- **Phương pháp**:
  - Áp dụng thuật toán tìm kiếm lùi (`np.searchsorted`) trên hệ số chia tách để bảo toàn tính đơn điệu của hệ số điều chỉnh.
  - Tích hợp bảng hiệu chỉnh pháp y 13 ca dị biệt (CORR_001–CORR_013) nhằm giải quyết các trường hợp chia tách ngược kỷ lục (1:200 ở `CHK`, 1:10 ở `CRC`) và các ca tách công ty con đặc thù (Spinoffs).
  - Tính tổng tỷ suất sinh lời ngày bao gồm cổ tức tiền mặt: $R_{total, t} = \frac{P_t + D_t}{P_{t-1}} - 1$.
- **Giới hạn thực nghiệm còn lại**: Công thức tổng tỷ suất sinh lời giả định việc tái đầu tư cổ tức tiền mặt diễn ra tức thì tại giá đóng cửa của ngày giao dịch không hưởng quyền mà không chịu thuế thu nhập doanh nghiệp (tax drag) hoặc chi phí giao dịch trượt giá (slippage/friction).
