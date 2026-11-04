# Lưu Trữ Tài Liệu & Báo Cáo Cũ (Docs Archive Repository)

> **Dự án**: Russell 1000 Daily Return Ranking Prediction Engine  
> **Milestone**: M1 (Section R1 — Archive Toàn Diện)  
> **Ngày thực hiện**: 2026-11-04  
> **Quy chuẩn**: Bảo toàn 100% dữ liệu lịch sử (Zero Deletion Policy), cô lập toàn bộ báo cáo HTML, Markdown, biểu đồ PNG và bảng CSV chứa số liệu lỗi thời hoặc cấu trúc pipeline v1 cũ.

---

## 1. Lý Do Lưu Trữ & Bảng Đối Chiếu Số Liệu Chuẩn (Ground Truth Baseline)

Trong quá trình phát triển dự án, dữ liệu giá và tỷ suất sinh lời ở giai đoạn đầu (Pipeline v1 / Phase 2 cũ tháng 10/2026) **chưa được điều chỉnh đầy đủ các sự kiện doanh nghiệp (Corporate Actions)**, đặc biệt là các ca **chia tách ngược cực đoan (Reverse Splits)** và **tách công ty con (Spinoffs)**. Điều này dẫn đến sự xuất hiện của các gai giá giả tạo hàng chục lần (như Chesapeake Energy tăng ảo +19,900%, California Resources tăng ảo +900%), gây méo mó nghiêm trọng các mô-men thống kê.

Sau khi pipeline được xây dựng lại từ đầu (Step 1 đến Step 6), toàn bộ dữ liệu đã được chuẩn hóa với **13 ca hiệu chỉnh pháp y CORR_001 đến CORR_013** và định danh **3,711 Canonical SIDs**.

Bảng dưới đây đối chiếu sự khác biệt bản chất giữa số liệu chuẩn mực hiện tại (Ground Truth) và số liệu trong các tài liệu lưu trữ tại thư mục này:

| Chỉ số định lượng | Ground Truth Chuẩn Mực Hiện Tại (Step 6) | Số Liệu Sai Lệch Trong Tài Liệu Archive (Phase 2 cũ) | Bản Chất & Nguyên Nhân Sai Lệch |
|:---|:---:|:---:|:---|
| **Độ nhọn phân phối (Excess Kurtosis)** | **66.88** (66.875) | **16,433** (thậm chí 3,400,000 trước lọc) | Pipeline cũ chưa xử lý chia tách ngược và bad ticks, tạo đuôi phân phối dày giả tạo cực đoan |
| **Tỷ suất sinh lời tối đa (Max Daily Return)** | **+227.87%** (2.2787) | **+1,364.52%** (thậm chí +12,371%) | Các ca nhảy vọt giá do chia tách cổ phiếu 1:200 hoặc 1:10 chưa tính hệ số chia tách dồn tích |
| **Độ lệch phân phối (Skewness)** | **+0.563** (0.56343) | **+41.08** | Bị kéo lệch bởi các outlier dương khổng lồ do lỗi chia tách |
| **Tổng số quan sát hợp lệ (Valid Stock-Days)** | **5,610,691 lượt** | **5,920,516 lượt** | Pipeline cũ tính cả các ngày mã đã bị hủy niêm yết hoặc ngoài rổ PIT tại thời điểm t |
| **Số lượng cổ phiếu chuẩn hóa (Security SIDs)** | **3,711 Canonical SIDs** | 2,852 / 2,884 raw tickers | Pipeline cũ dùng mã ticker thô, bị trùng lặp khi 1 ticker được gán cho nhiều công ty khác nhau |
| **Độ biến động hàng ngày (Daily Volatility)** | **2.65%** (0.026530) | 2.83% | Phản ánh chính xác biến động thị trường sau khi loại bỏ gai giá nhân tạo |
| **Bảng hiệu chỉnh pháp y (Corrections Table)** | **CORR_001 đến CORR_013** (13 ca) | Không có | Gồm 4 ca Reverse Split, 5 ca Spinoff, 4 ca Ticker Collision/Bad ticks |

---

## 2. Bảng Kê Chi Tiết 30 Tệp / Thư Mục Tài Liệu Đã Lưu Trữ

| STT | Tên Tệp / Thư Mục | Định Dạng | Pipeline Phase Tạo Ra | Lý Do Lỗi Thời & Cần Lưu Trữ | Vị Trí Báo Cáo Thay Thế Chuẩn Mực Hiện Tại |
|:---:|:---|:---:|:---|:---|:---|
| 1 | `phase1_report.html` | HTML (73.5 KB) | Phase 1 (02/11/2026) | Báo cáo kiểm định dữ liệu thô ban đầu; dựa trên ticker thô chưa giải quyết canonical SID; không có 17 ma trận 2D | `docs/Data report/project_report.html` |
| 2 | `phase2_report.html` | HTML (79.7 KB) | Phase 2 (01/11/2026) | Chứa toàn bộ số liệu sai lệch nghiêm trọng: Kurtosis = 16,433, Max return = +1,364.52%, số quan sát = 5,920,516 | `docs/Data report/project_report.html` (Được đồng bộ ở Milestone M4/R8) |
| 3 | `russell1000_universe_preprocessing.html` | HTML (108.6 KB) | Phase 1 Early (02/11/2026) | Phiên bản HTML tiền xử lý sơ khai; chưa có thuật toán giải quyết 2T transient placeholder và ticker reuse | `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` |
| 4 | `russell1000_universe_preprocessing_v2.html` | HTML (86.0 KB) | Phase 1 Intermediate (02/11/2026) | Báo cáo tiền xử lý v2; đã bị thay thế hoàn toàn bởi kho dữ liệu hợp nhất 484 MB và các báo cáo audit chuẩn | `docs/Data report/market_data_audit/step2_identity_and_corporate_actions_report.md` |
| 5 | `institutional_pipeline_report.html` | HTML (144.6 KB) | Phase 2 Final (03/11/2026) | Bản sao trùng lặp 100% từng byte với `docs/Data report/project_report.html` (cùng kích thước 144,649 B); lưu trữ để chống dư thừa | `docs/Data report/project_report.html` |
| 6 | `phase1/` *(Thư mục gồm 6 files)* | MD & PNG | Phase 1 (10/2026) | Bộ báo cáo kiểm định và đồ thị universe thô cũ; chưa có khái niệm Point-in-Time 3 lớp mask và 3,711 SIDs | Thư mục `docs/Data report/market_data_audit/` |
| 7 | `phase2/` *(Thư mục gồm 19 files)* | MD, CSV & PNG | Phase 2 (10/2026) | Báo cáo phân tích EDA, ma trận tương quan và kiểm thử alpha factor cũ; toàn bộ tính toán trên dữ liệu dính lỗi chia tách | Thư mục `docs/Data report/market_data_audit/` (41 tables & 4 figures) |

---

## 3. Danh Sách Tệp Chi Tiết Trong Các Thư Mục Báo Cáo Cũ

### 3.1. Thư mục `docs/archive/phase1/` (6 files)
- `phase1_data_validation_report.md`: Báo cáo thẩm định dữ liệu ban đầu.
- `test_results_report.md`: Tổng hợp kết quả chạy kiểm thử test1 đến test4 cũ.
- `figures/step1_universe_count_by_year.png`: Đồ thị đếm số lượng mã thô theo năm.
- `figures/step2_market_data_coverage.png`: Biểu đồ độ phủ dữ liệu giá thô.
- `figures/test3_universe_turnover.png`: Biểu đồ luân chuyển vũ trụ theo ticker cũ.
- `figures/universe_constituents_coverage.png`: Biểu đồ diện tích bao phủ thành viên universe.

### 3.2. Thư mục `docs/archive/phase2/` (19 files)
#### Báo cáo Markdown (6 files):
- `eda_01_return_distribution_report.md`: Công bố sai Kurtosis = 16,433 và Max return = +1,364.52%.
- `eda_02_nan_universe_report.md`: Báo cáo động thái khuyết dữ liệu trên cấu trúc bảng dọc cũ.
- `phase2_eda_feature_summary.md`: Tóm tắt đặc trưng dữ liệu Phase 2 cũ.
- `sanity_check_report.md`: Báo cáo kiểm tra bất thường in-sample cũ.
- `t4_feature_store_report.md`: Báo cáo xây dựng kho feature store dạng tall table.
- `t5_alpha_benchmark_report.md`: Báo cáo đo lường IC của các alpha benchmark cũ.

#### Bảng dữ liệu thống kê CSV (9 files):
- `figures/eda_01_annual_dispersion.csv`: Độ phân tán hàng năm cũ.
- `figures/eda_01_return_stats.csv`: Bảng thống kê mô-men phân phối cũ (sai Kurtosis, Skew).
- `figures/eda_02_ticker_lifespan.csv`: Tuổi thọ ticker tính trên mã thô.
- `figures/eda_02_universe_dynamics.csv`: Động thái thêm/bớt mã cũ.
- `figures/feature_correlation_matrix.csv`: Ma trận tương quan giữa các feature cũ.
- `figures/feature_high_correlation_pairs.csv`: Danh sách các cặp feature đa cộng tuyến cũ.
- `figures/t5_feature_ic_ranking.csv`: Bảng xếp hạng IC của feature cũ.
- `figures/t5_reversal5d_annual_ic.csv`: IC hàng năm của tín hiệu reversal 5 ngày cũ.
- `figures/t5_reversal5d_daily_ic.csv`: IC hàng ngày của tín hiệu reversal 5 ngày cũ.

#### Biểu đồ phân tích PNG (4 files):
- `figures/eda_01_return_distribution.png`: Biểu đồ histogram phân phối tỷ suất sinh lời cũ với gai lỗi.
- `figures/eda_02_nan_universe_dynamics.png`: Đồ thị biến động tỷ lệ dữ liệu thiếu.
- `figures/feature_correlation_heatmap.png`: Bản đồ nhiệt tương quan giữa các feature cũ.
- `figures/t5_alpha_benchmark_ic.png`: Biểu đồ phân phối IC của benchmark alpha cũ.

---

## 4. Cảnh Báo Cho Các Subagent & Nhà Nghiên Cứu

1. **Tuyệt đối không trích dẫn số liệu từ thư mục này**: Bất kỳ tài liệu, slide thuyết trình hay báo cáo học thuật nào trích dẫn các con số `Kurtosis 16,433`, `Max return +1,364%` hay `5,920,516 stock-days` đều bị coi là **sai lệch khoa học nghiêm trọng**.
2. **Nguồn tham chiếu duy nhất**: Mọi phân tích định lượng chỉ được phép lấy từ:
   - `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv`
   - `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv`
   - `docs/Data report/project_report.html` (bản chuẩn)
   - `data/processed/matrices/` (17 ma trận 2D chuẩn hóa)
