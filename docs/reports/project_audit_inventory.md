# BÁO CÁO KIỂM KÊ VÀ THẨM ĐỊNH TOÀN DIỆN DỰ ÁN (PROJECT AUDIT & INVENTORY REPORT)

> **Dự án**: Russell 1000 Daily Return Ranking Prediction Engine  
> **Milestone**: M0 — R0 (Scan toàn bộ project & Lập danh sách phân loại file cần xử lý)  
> **Ngày thực hiện**: 2026-11-04 16:27:13  
> **Thực hiện bởi**: Subagent `explorer_m0` (Project Inventory Explorer)  
> **Integrity Mode**: Development (Đóng băng tuyệt đối dữ liệu OOS 2024–2026)  

---

## MỤC LỤC
1. [Tóm Tắt Điều Hành & Xác Định Đường Dẫn Dự Án](#1-tóm-tắt-điều-hành--xác-định-đường-dẫn-dự-án)
2. [Chuẩn Số Liệu Hiện Tại (Ground Truth Baseline)](#2-chuẩn-số-liệu-hiện-tại-ground-truth-baseline)
3. [Kiểm Kê Thư Mục `scripts/` (42 Files)](#3-kiểm-kê-thư-mục-scripts-42-files)
4. [Kiểm Kê Thư Mục `docs/` (82 Files)](#4-kiểm-kê-thư-mục-docs-82-files)
5. [Kiểm Kê Thư Mục `data/processed/` (65 Files)](#5-kiểm-kê-thư-mục-dataprocessed-65-files)
6. [Kế Hoạch Lưu Trữ Cho Milestone M1 (Archiving Execution Plan)](#6-kế-hoạch-lưu-trữ-cho-milestone-m1-archiving-execution-plan)

---

## 1. TÓM TẮT ĐIỀU HÀNH & XÁC ĐỊNH ĐƯỜNG DẪN DỰ ÁN

### 1.1. Phát Hiện Quan Trọng Về Đường Dẫn Dự Án
Trong quá trình khảo sát thực địa tại hệ thống máy chủ Windows, nhóm kiểm kê đã xác định rõ hai không gian làm việc:
- **Thư mục chứa mã nguồn và dữ liệu thực tế của dự án**:
  `D:\A_Learning\HK1_2026-2027\CO3101 - Đồ án tổng hợp - ttnt\Predict_daily_return_rankings`
  *(Chứa toàn bộ mã nguồn pipeline mới, dữ liệu kho 484 MB, 17 ma trận 2D, các báo cáo audit chuẩn mực và các script cũ)*.
- **Thư mục môi trường IDE Antigravity / Teamwork workspace**:
  `D:\Learning\HK1_2026-2027\CO3101 - Đồ án tổng hợp - ttnt\Predict_daily_return_rankings`
  *(Nơi lưu trữ metadata của các agent `.agents/teamwork/`)*.

**Quyết định thực thi**: Báo cáo kiểm kê này quét trực tiếp 100% tệp tin trên cây thư mục thực tế tại `D:\A_Learning\...` và được lưu đồng thời tại cả hai thư mục `docs/reports/project_audit_inventory.md` để đảm bảo tính sẵn sàng tối đa cho toàn bộ các subagent tiếp theo.

### 1.2. Tổng Hợp Thống Kê Kiểm Kê

| Thư mục khảo sát | Tổng số file | Hoạt động (ACTIVE / CURRENT) | Lỗi thời (STALE / WRONG / OLD) | Tham chiếu (REFERENCE / REDUNDANT) |
|:---|:---:|:---:|:---:|:---:|
| `scripts/` | **42** | 13 | 29 | 0 |
| `docs/` | **82** | 48 | 29 | 5 (4 tham chiếu + 1 trùng lặp) |
| `data/processed/` | **65** | 63 | 0 | 2 (trùng lặp tại `market_data/`) |
| **TỔNG CỘNG** | **189** | **124** | **58** | **7** |

---

## 2. CHUẨN SỐ LIỆU HIỆN TẠI (GROUND TRUTH BASELINE)

Tất cả các tài liệu, báo cáo, biểu đồ và mã nguồn trong dự án sau đợt tái cấu trúc **phải thống nhất 100%** với các số liệu chuẩn mực (Ground Truth) đã được kiểm chứng bằng thực nghiệm khoa học tại Step 3, Step 4 và Step 6 (trích xuất trực tiếp từ `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv` và `market_data_corrections_and_exceptions.csv`):

| Chỉ số định lượng | Giá trị Ground Truth chuẩn (Step 6) | Giá trị sai trong Pipeline v1 cũ (Phase 2) | Nguyên nhân & Bản chất khác biệt |
|:---|:---:|:---:|:---|
| **Khoảng thời gian phát triển (Dev Window)** | **2000-07-01 đến 2023-12-29** | 2000-01-01 đến 2023-12-31 | Chuẩn hóa theo chu kỳ Reconstitution hàng năm [YYYY-07-01 đến (YYYY+1)-06-30]. Giai đoạn 1998-1999 dùng làm warm-up |
| **Số ngày giao dịch (Trading Days)** | **7,252 ngày** (Toàn bộ 1998–2026) | 6,021 ngày (chỉ tính in-sample) | Bao phủ toàn bộ lịch giao dịch NYSE/NASDAQ từ 1998 đến 2026 |
| **Tổng số quan sát hợp lệ (Valid Stock-Days)** | **5,610,691 lượt** | 5,920,516 lượt | Pipeline cũ tính cả các ngày có giá nhưng không nằm trong rổ PIT hoặc bị lỗi dữ liệu/phi giao dịch |
| **Số lượng mã cổ phiếu chuẩn hóa (Canonical SIDs)** | **3,711 SIDs** | 2,852 / 2,884 raw tickers | Giải quyết triệt để vấn đề Ticker Reuse (1 ticker nhiều công ty qua các thời kỳ) và gộp 2T placeholder |
| **Độ biến động hàng ngày (Daily Volatility)** | **2.65%** (0.026530) | 2.83% | Pipeline cũ bị kéo bởi các gai giá lỗi và chia tách ngược chưa được điều chỉnh |
| **Độ lệch phân phối (Skewness)** | **+0.563** (0.56343) | +41.08 | Skewness dương nhẹ đặc trưng của cổ phiếu vốn hóa lớn, loại bỏ hoàn toàn méo mó do lỗi chia tách ngược |
| **Độ nhọn phân phối (Excess Kurtosis)** | **66.88** (66.875) | **16,433** (thậm chí 3.4M trước lọc) | Đã hạ từ mức bất thường xuống 66.88 sau khi chuẩn hóa 13 ca pháp y CORR_001–CORR_013 |
| **Tỷ suất sinh lời tối đa (Max Return)** | **+227.87%** (2.2787) | **+1,364.52%** (thậm chí +12,371%) | Các ca tăng ảo hàng chục lần (như CHK +19,900%, CRC +900%) là do chia tách ngược chưa tính factor |
| **Tỷ suất sinh lời tối thiểu (Min Return)** | **-94.97%** (-0.9497) | -96.66% | Phản ánh chính xác các cú sập thị trường thực tế (WorldCom, Enron, v.v.) |
| **Bảng hiệu chỉnh pháp y (Corrections Table)** | **CORR_001 đến CORR_013** (13 ca) | Không có | 4 ca Reverse Split (CHK, CRC, ADCT, AA), 5 ca Spinoff/Discontinuity, 4 ca Bad Ticks/Collisions |

---

## 3. KIỂM KÊ THƯ MỤC `scripts/` (42 FILES)

Toàn bộ 42 file mã nguồn Python trong `scripts/` đã được duyệt xét từng dòng đầu (header & imports) và phân loại theo bảng dưới đây:

| STT | Đường dẫn file | Kích thước | Ngày cập nhật | Phân loại | Bằng chứng kiểm tra & Lý do | Đề xuất hành động |
|:---:|:---|:---:|:---:|:---:|:---|:---|
| 1 | `scripts/01_pipeline/01_parse_all_universe.py` | 14,228 B | 2026-10-01 10:40:43 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 2 | `scripts/01_pipeline/02_quantconnect_availability_scan.py` | 28,747 B | 2026-11-02 19:29:56 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 3 | `scripts/01_pipeline/02_quantconnect_export_10_batches.py` | 19,799 B | 2026-11-02 21:39:16 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 4 | `scripts/01_pipeline/02b_test_empty_ticker_candidates.py` | 20,901 B | 2026-11-02 19:46:20 | **STALE** | Script notebook test phục hồi ticker rỗng trên QuantConnect; đã hoàn tất mục đích nghiên cứu; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 5 | `scripts/01_pipeline/02c_test_targeted_recovery_v2.py` | 4,957 B | 2026-11-02 20:01:55 | **STALE** | Script notebook test phục hồi ticker rỗng trên QuantConnect; đã hoàn tất mục đích nghiên cứu; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 6 | `scripts/01_pipeline/03_process_10_batches_to_parquet.py` | 4,851 B | 2026-11-02 22:17:32 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 7 | `scripts/01_pipeline/04_audit_identity_and_build_canonical_mapping.py` | 12,776 B | 2026-11-03 00:53:06 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 8 | `scripts/01_pipeline/04b_generate_comprehensive_step3_audits.py` | 17,881 B | 2026-11-03 10:14:02 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 9 | `scripts/01_pipeline/05_build_cross_sectional.py` | 2,915 B | 2026-10-02 16:24:40 | **STALE_OLD_PIPELINE** | Script v1 cũ (02/10/2026) import từ src.data và ghi dữ liệu ra in_sample/out_sample legacy; đã bị thay thế hoàn toàn bởi script 07 | Move vào scripts/archive/ |
| 10 | `scripts/01_pipeline/05_quantconnect_export_corporate_actions.py` | 18,224 B | 2026-11-03 08:46:29 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 11 | `scripts/01_pipeline/05_rigorous_pit_membership_reconstruction.py` | 15,620 B | 2026-11-03 10:32:32 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 12 | `scripts/01_pipeline/06_process_corporate_actions_and_adjusted_prices.py` | 27,764 B | 2026-11-03 13:56:59 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 13 | `scripts/01_pipeline/07_build_2d_matrices_and_masks.py` | 24,849 B | 2026-11-03 14:00:14 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 14 | `scripts/01_pipeline/08_validate_matrices_and_sanity_checks.py` | 15,987 B | 2026-11-03 09:31:46 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 15 | `scripts/01_pipeline/09_run_development_eda.py` | 17,308 B | 2026-11-03 09:32:20 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 16 | `scripts/01_pipeline/10_investigate_extreme_returns.py` | 19,813 B | 2026-11-03 14:08:26 | **ACTIVE** | Thuộc pipeline sản xuất chính thức 01-10 (hoặc công cụ thu thập QC / audit generator tương ứng) | Giữ nguyên hoạt động (Keep Active) |
| 17 | `scripts/01_pipeline/11_apply_forensic_corrections_and_rerun_eda.py` | 15,054 B | 2026-11-03 11:11:44 | **STALE** | Script can thiệp ma trận trung gian; các hiệu chỉnh đã được tích hợp trực tiếp vào script 06, 07, 09, 10; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 18 | `scripts/01_pipeline/plot_universe_coverage_stacked.py` | 3,574 B | 2026-11-01 21:32:39 | **STALE** | Script vẽ biểu đồ stacked coverage độc lập (01/11/2026), biểu đồ đã được tích hợp trong báo cáo audit | Move vào scripts/archive/ |
| 19 | `scripts/02_validation_universe/test1_universe_structure.py` | 5,130 B | 2026-10-01 15:47:01 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 20 | `scripts/02_validation_universe/test3_universe_pit_turnover.py` | 6,572 B | 2026-10-01 15:50:28 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 21 | `scripts/02_validation_universe/test4_security_identity.py` | 5,150 B | 2026-10-01 16:03:02 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 22 | `scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py` | 4,332 B | 2026-10-01 16:56:29 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 23 | `scripts/03_validation_ohlcv/test_m2_time_coverage.py` | 4,535 B | 2026-10-01 17:03:27 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 24 | `scripts/03_validation_ohlcv/test_m3_corporate_actions.py` | 5,760 B | 2026-10-01 17:06:14 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 25 | `scripts/03_validation_ohlcv/test_m4_russell_ohlcv_compatibility.py` | 3,875 B | 2026-10-01 17:06:57 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 26 | `scripts/03_validation_ohlcv/test_m5_m6_market_value.py` | 3,717 B | 2026-10-01 17:07:57 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 27 | `scripts/04_deep_audit/deep_audit_survivorship.py` | 16,880 B | 2026-10-01 17:24:21 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 28 | `scripts/05_eda/__init__.py` | 0 B | 2026-10-03 15:22:46 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 29 | `scripts/05_eda/eda_01_return_distribution.py` | 17,677 B | 2026-10-03 15:36:56 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 30 | `scripts/05_eda/eda_02_nan_universe_dynamics.py` | 13,896 B | 2026-10-03 15:48:57 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 31 | `scripts/05_eda/sanity_check_in_sample.py` | 17,882 B | 2026-10-03 15:10:08 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 32 | `scripts/06_features/__init__.py` | 0 B | 2026-10-03 15:22:46 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 33 | `scripts/06_features/analyze_feature_correlation.py` | 6,761 B | 2026-10-26 14:09:58 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 34 | `scripts/06_features/build_feature_store.py` | 10,166 B | 2026-11-01 00:57:46 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 35 | `scripts/07_alpha_eval/__init__.py` | 0 B | 2026-10-03 15:22:46 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 36 | `scripts/07_alpha_eval/eval_benchmark_alpha.py` | 15,128 B | 2026-11-01 00:57:46 | **STALE_OLD_PIPELINE** | Thư mục kiểm thử/EDA/feature thuộc cấu trúc pipeline v1 (tháng 10/2026), hoàn toàn không được import bởi pipeline mới | Move vào scripts/archive/ |
| 37 | `scripts/08_train_quick_test.py` | 5,889 B | 2026-11-01 01:24:39 | **STALE** | Script prototype huấn luyện/backtest nhanh trên dữ liệu feature cũ trước khi xây dựng ma trận 2D chuẩn; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 38 | `scripts/09_inspect_predictions.py` | 5,036 B | 2026-11-01 01:27:46 | **STALE** | Script prototype huấn luyện/backtest nhanh trên dữ liệu feature cũ trước khi xây dựng ma trận 2D chuẩn; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 39 | `scripts/10_backtest_top10.py` | 5,859 B | 2026-11-01 01:30:25 | **STALE** | Script prototype huấn luyện/backtest nhanh trên dữ liệu feature cũ trước khi xây dựng ma trận 2D chuẩn; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 40 | `scripts/audit_step1_warehouse_and_pit_coverage.py` | 9,220 B | 2026-11-03 00:27:43 | **STALE** | Script tiện ích giai đoạn đầu khi gom batch QC; đã được thay thế bởi scripts 03, 04, 04b trong 01_pipeline; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 41 | `scripts/build_audit_reports.py` | 13,856 B | 2026-11-02 23:14:34 | **STALE** | Script tiện ích giai đoạn đầu khi gom batch QC; đã được thay thế bởi scripts 03, 04, 04b trong 01_pipeline; nằm trong danh sách chỉ định archive của R1 | Move vào scripts/archive/ |
| 42 | `scripts/build_comprehensive_project_report.py` | 43,145 B | 2026-11-03 14:09:25 | **ACTIVE_UTILITY** | Script biên dịch HTML project report (docs/Data report/project_report.html); cần sử dụng để cập nhật đồng bộ HTML ở Milestone M4/R8 | Giữ tạm thời để cập nhật R8, sau đó chuyển scripts/archive/ hoặc giữ làm build tool |

### 3.1. Phân Tích & Xác Nhận Bằng Chứng Mã Nguồn Cũ Trong `scripts/`
1. **Các script prototype ngoài thư mục gốc (`scripts/08_`, `09_`, `10_`)**:
   - `08_train_quick_test.py`: Header ghi rõ *'QUICK TEST BASELINE MODEL — LIGHTGBM ON RUSSELL 1000 PIT'*, sử dụng dữ liệu cũ `feature_store_long.parquet` và tách train window 2018-2022. Đây là thử nghiệm trước khi xây dựng hệ thống 17 ma trận 2D.
   - `09_inspect_predictions.py`: Script soi kết quả dự báo của mô hình test 08.
   - `10_backtest_top10.py`: Script mô phỏng danh mục Top 10 năm 2023 trên kết quả của mô hình test 08.
   - **Kết luận**: Cả 3 file đều là prototype tạm thời, cần move vào `scripts/archive/`.

2. **Các script kiểm thử Phase 1 & Phase 2 cũ (`02_validation_universe/`, `03_validation_ohlcv/`, `04_deep_audit/`, `05_eda/`, `06_features/`, `07_alpha_eval/`)**:
   - Toàn bộ 18 script trong các thư mục này được viết từ 01/10/2026 đến 03/10/2026, dựa trên cấu trúc module `src.data` cũ và bộ dữ liệu `in_sample/` chưa khử nhiễu.
   - Ví dụ, `05_eda/eda_01_return_distribution.py` đọc từ `data/processed/in_sample/returns.parquet` và tính ra Kurtosis 16,433 và Max return +1,364.52%.
   - Kiểm tra chéo: Không có bất kỳ script nào trong `scripts/01_pipeline/` import hay phụ thuộc vào các thư mục này.
   - **Kết luận**: Đủ điều kiện chuyển toàn bộ các thư mục này vào `scripts/archive/`.

3. **Các file cần archive bên trong `scripts/01_pipeline/`**:
   - `05_build_cross_sectional.py`: Tạo ngày 02/10/2026, chứa logic chia in_sample/out_sample cũ, xung đột trực tiếp với script `07_build_2d_matrices_and_masks.py`.
   - `11_apply_forensic_corrections_and_rerun_eda.py`: Là script trung gian vá dữ liệu; logic của nó đã được chuyển hóa vào pipeline chính thức ở script 06 và 07.
   - `02b_test_empty_ticker_candidates.py` và `02c_test_targeted_recovery_v2.py`: Script thử nghiệm trên QuantConnect, đã hoàn thành nhiệm vụ.
   - `plot_universe_coverage_stacked.py`: Script vẽ đồ thị độc lập.

---

## 4. KIỂM KÊ THƯ MỤC `docs/` (82 FILES)

Toàn bộ 82 file tài liệu trong `docs/` đã được kiểm tra nội dung và số liệu định lượng:

| STT | Đường dẫn file | Định dạng | Kích thước | Ngày cập nhật | Phân loại | Bằng chứng & Số liệu đối chiếu | Đề xuất hành động |
|:---:|:---|:---:|:---:|:---:|:---:|:---|:---|
| 1 | `docs/Data report/institutional_pipeline_report.html` | `.html` | 144,649 B | 2026-11-03 14:09:32 | **CURRENT_REDUNDANT** | Bản sao nhị phân giống hệt (duplicate 100%) của project_report.html (cùng kích thước 144,649 B); gây dư thừa | Move vào docs/archive/ (hoặc xóa trùng lặp) |
| 2 | `docs/Data report/market_data_audit/figures/eda_cross_sectional_dispersion_history.png` | `.png` | 434,359 B | 2026-11-03 14:06:46 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 3 | `docs/Data report/market_data_audit/figures/eda_daily_return_distribution_qq.png` | `.png` | 231,084 B | 2026-11-03 14:06:38 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 4 | `docs/Data report/market_data_audit/figures/eda_liquidity_vs_volatility_deciles.png` | `.png` | 136,131 B | 2026-11-03 14:06:50 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 5 | `docs/Data report/market_data_audit/figures/eda_universe_turnover_and_active_count.png` | `.png` | 147,829 B | 2026-11-03 14:06:33 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 6 | `docs/Data report/market_data_audit/market_data_audit_report.md` | `.md` | 7,465 B | 2026-11-03 00:37:54 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 7 | `docs/Data report/market_data_audit/step2_identity_and_corporate_actions_report.md` | `.md` | 16,001 B | 2026-11-03 00:56:56 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 8 | `docs/Data report/market_data_audit/tables/2t_stitching_conflict_audit.csv` | `.csv` | 62,748,669 B | 2026-11-03 13:57:17 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 9 | `docs/Data report/market_data_audit/tables/ambiguous_multi_sid_audit.csv` | `.csv` | 34,101 B | 2026-11-03 10:32:38 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 10 | `docs/Data report/market_data_audit/tables/annual_trading_days_distribution.csv` | `.csv` | 1,689 B | 2026-11-02 23:14:41 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 11 | `docs/Data report/market_data_audit/tables/batch_execution_summary.csv` | `.csv` | 928 B | 2026-11-02 23:14:41 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 12 | `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | `.csv` | 401,931 B | 2026-11-03 00:53:18 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 13 | `docs/Data report/market_data_audit/tables/canonical_sid_reconciliation_audit.csv` | `.csv` | 710,266 B | 2026-11-03 10:14:09 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 14 | `docs/Data report/market_data_audit/tables/corporate_actions_match_summary.csv` | `.csv` | 130 B | 2026-11-03 13:57:35 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 15 | `docs/Data report/market_data_audit/tables/coverage_ticker_period_vs_daily_stock_days.csv` | `.csv` | 1,939 B | 2026-11-03 10:32:48 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 16 | `docs/Data report/market_data_audit/tables/daily_pit_coverage_by_period.csv` | `.csv` | 2,426 B | 2026-11-03 00:28:13 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 17 | `docs/Data report/market_data_audit/tables/dividend_identity_mathematical_audit.csv` | `.csv` | 1,088 B | 2026-11-03 13:58:36 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 18 | `docs/Data report/market_data_audit/tables/dividends_matched_unmatched_audit.csv` | `.csv` | 6,024,154 B | 2026-11-03 13:57:35 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 19 | `docs/Data report/market_data_audit/tables/eda_cross_sectional_dispersion.csv` | `.csv` | 2,181 B | 2026-11-03 14:06:45 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 20 | `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv` | `.csv` | 706 B | 2026-11-03 14:06:35 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 21 | `docs/Data report/market_data_audit/tables/eda_liquidity_deciles.csv` | `.csv` | 559 B | 2026-11-03 14:06:49 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 22 | `docs/Data report/market_data_audit/tables/eda_universe_dynamics_by_year.csv` | `.csv` | 1,104 B | 2026-11-03 14:06:32 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 23 | `docs/Data report/market_data_audit/tables/extreme_returns_forensic_investigation.csv` | `.csv` | 17,101 B | 2026-11-03 14:08:34 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 24 | `docs/Data report/market_data_audit/tables/fallback_mapping_audit.csv` | `.csv` | 14,420 B | 2026-11-02 23:14:42 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 25 | `docs/Data report/market_data_audit/tables/june_july_boundary_transition_audit.csv` | `.csv` | 2,835 B | 2026-11-03 10:14:20 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 26 | `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv` | `.csv` | 6,661 B | 2026-11-03 13:54:03 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 27 | `docs/Data report/market_data_audit/tables/matrix_and_mask_coverage_by_period.csv` | `.csv` | 4,304 B | 2026-11-03 14:05:31 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 28 | `docs/Data report/market_data_audit/tables/matrix_reconciliation_audit.csv` | `.csv` | 314 B | 2026-11-03 14:05:56 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 29 | `docs/Data report/market_data_audit/tables/matrix_sanity_check_summary.csv` | `.csv` | 840 B | 2026-11-03 14:05:58 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 30 | `docs/Data report/market_data_audit/tables/matrix_split_boundary_audit.csv` | `.csv` | 1,424 B | 2026-11-03 14:05:58 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 31 | `docs/Data report/market_data_audit/tables/period_reconciliation_summary.csv` | `.csv` | 1,164 B | 2026-11-03 10:14:13 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 32 | `docs/Data report/market_data_audit/tables/pit_constituent_coverage_by_year.csv` | `.csv` | 725 B | 2026-11-02 23:14:43 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 33 | `docs/Data report/market_data_audit/tables/shared_sid_alias_audit.csv` | `.csv` | 17,333 B | 2026-11-03 00:40:05 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 34 | `docs/Data report/market_data_audit/tables/split_adjustment_sanity_audit.csv` | `.csv` | 1,763 B | 2026-11-03 08:53:45 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 35 | `docs/Data report/market_data_audit/tables/split_formula_mathematical_audit.csv` | `.csv` | 3,310 B | 2026-11-03 13:58:36 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 36 | `docs/Data report/market_data_audit/tables/splits_matched_unmatched_audit.csv` | `.csv` | 159,844 B | 2026-11-03 13:57:28 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 37 | `docs/Data report/market_data_audit/tables/ticker_changes_audit.csv` | `.csv` | 47,498 B | 2026-11-03 10:14:13 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 38 | `docs/Data report/market_data_audit/tables/ticker_identity_transitions.csv` | `.csv` | 93,516 B | 2026-11-02 23:14:42 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 39 | `docs/Data report/market_data_audit/tables/ticker_reuse_audit.csv` | `.csv` | 200,248 B | 2026-11-03 00:53:18 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 40 | `docs/Data report/market_data_audit/tables/ticker_reuse_temporal_audit.csv` | `.csv` | 229,046 B | 2026-11-03 10:14:15 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 41 | `docs/Data report/market_data_audit/tables/ticker_to_canonical_sid_reuse_breakdown.csv` | `.csv` | 308,037 B | 2026-11-03 10:32:59 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 42 | `docs/Data report/market_data_audit/tables/top_50_negative_returns_audit.csv` | `.csv` | 6,531 B | 2026-11-03 14:08:34 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 43 | `docs/Data report/market_data_audit/tables/top_50_positive_returns_audit.csv` | `.csv` | 6,379 B | 2026-11-03 14:08:34 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 44 | `docs/Data report/market_data_audit/tables/transient_2t_resolution_audit.csv` | `.csv` | 81,181 B | 2026-11-03 00:53:17 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 45 | `docs/Data report/market_data_audit/tables/universe_constituent_segments_mapping.csv` | `.csv` | 4,774,340 B | 2026-11-03 14:00:23 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 46 | `docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv` | `.csv` | 4,588,694 B | 2026-11-03 10:32:38 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 47 | `docs/Data report/market_data_audit/tables/warehouse_sanity_check.csv` | `.csv` | 535 B | 2026-11-03 00:27:58 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 48 | `docs/Data report/market_data_audit/tables/zero_bar_constituents_by_period.csv` | `.csv` | 32,297 B | 2026-11-03 00:28:13 | **CURRENT** | Báo cáo, biểu đồ và bảng audit chuẩn mực của pipeline mới (Step 2 - Step 6) sinh ngày 03/11/2026 | Giữ nguyên hoạt động (Keep Active) |
| 49 | `docs/Data report/phase1/figures/step1_universe_count_by_year.png` | `.png` | 99,363 B | 2026-10-01 15:20:55 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 50 | `docs/Data report/phase1/figures/step2_market_data_coverage.png` | `.png` | 387,975 B | 2026-10-02 16:26:12 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 51 | `docs/Data report/phase1/figures/test3_universe_turnover.png` | `.png` | 318,004 B | 2026-10-03 16:12:41 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 52 | `docs/Data report/phase1/figures/universe_constituents_coverage.png` | `.png` | 172,644 B | 2026-11-01 21:32:24 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 53 | `docs/Data report/phase1/phase1_data_validation_report.md` | `.md` | 12,747 B | 2026-10-03 15:32:46 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 54 | `docs/Data report/phase1/test_results_report.md` | `.md` | 15,895 B | 2026-10-03 16:15:29 | **STALE_OLD_PIPELINE** | Tài liệu báo cáo markdown và biểu đồ kiểm thử Phase 1 cũ (tháng 10/2026); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase1/ vào docs/archive/ |
| 55 | `docs/Data report/phase1_report.html` | `.html` | 73,548 B | 2026-11-02 19:17:36 | **STALE_OLD_PIPELINE** | Báo cáo HTML thuộc pipeline cũ (Phase 1 / Phase 2 cũ); số liệu không khớp chuẩn hiện tại; nằm trong danh sách chỉ định archive của R1 | Move vào docs/archive/ |
| 56 | `docs/Data report/phase2/eda_01_return_distribution_report.md` | `.md` | 7,904 B | 2026-10-03 15:45:18 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 57 | `docs/Data report/phase2/eda_02_nan_universe_report.md` | `.md` | 6,157 B | 2026-10-03 16:01:31 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 58 | `docs/Data report/phase2/figures/eda_01_annual_dispersion.csv` | `.csv` | 1,169 B | 2026-10-03 15:44:02 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 59 | `docs/Data report/phase2/figures/eda_01_return_distribution.png` | `.png` | 268,629 B | 2026-10-03 15:44:01 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 60 | `docs/Data report/phase2/figures/eda_01_return_stats.csv` | `.csv` | 443 B | 2026-10-03 15:44:02 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 61 | `docs/Data report/phase2/figures/eda_02_nan_universe_dynamics.png` | `.png` | 229,825 B | 2026-10-03 16:00:41 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 62 | `docs/Data report/phase2/figures/eda_02_ticker_lifespan.csv` | `.csv` | 81,882 B | 2026-10-03 16:00:42 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 63 | `docs/Data report/phase2/figures/eda_02_universe_dynamics.csv` | `.csv` | 609 B | 2026-10-03 16:00:42 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 64 | `docs/Data report/phase2/figures/feature_correlation_heatmap.png` | `.png` | 335,557 B | 2026-11-01 01:14:41 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 65 | `docs/Data report/phase2/figures/feature_correlation_matrix.csv` | `.csv` | 4,498 B | 2026-11-01 01:14:37 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 66 | `docs/Data report/phase2/figures/feature_high_correlation_pairs.csv` | `.csv` | 1,597 B | 2026-11-01 01:14:37 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 67 | `docs/Data report/phase2/figures/t5_alpha_benchmark_ic.png` | `.png` | 330,876 B | 2026-11-01 01:12:36 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 68 | `docs/Data report/phase2/figures/t5_feature_ic_ranking.csv` | `.csv` | 1,544 B | 2026-11-01 01:12:37 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 69 | `docs/Data report/phase2/figures/t5_reversal5d_annual_ic.csv` | `.csv` | 1,667 B | 2026-11-01 01:12:37 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 70 | `docs/Data report/phase2/figures/t5_reversal5d_daily_ic.csv` | `.csv` | 247,715 B | 2026-11-01 01:12:37 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 71 | `docs/Data report/phase2/phase2_eda_feature_summary.md` | `.md` | 13,496 B | 2026-10-03 19:54:53 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 72 | `docs/Data report/phase2/sanity_check_report.md` | `.md` | 13,260 B | 2026-10-03 15:19:38 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 73 | `docs/Data report/phase2/t4_feature_store_report.md` | `.md` | 7,411 B | 2026-10-03 16:32:01 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 74 | `docs/Data report/phase2/t5_alpha_benchmark_report.md` | `.md` | 8,997 B | 2026-10-03 19:52:10 | **STALE_WRONG_NUMBERS** | Báo cáo markdown, bảng CSV và biểu đồ Phase 2 cũ; chứa số liệu sai nghiêm trọng (Kurtosis 16,433, max return +1,364%, observations 5,920,516); nằm trong danh sách chỉ định archive của R1 | Move toàn bộ thư mục docs/Data report/phase2/ vào docs/archive/ |
| 75 | `docs/Data report/phase2_report.html` | `.html` | 79,652 B | 2026-11-01 01:15:22 | **STALE_WRONG_NUMBERS** | Báo cáo HTML thuộc pipeline cũ (Phase 1 / Phase 2 cũ); số liệu không khớp chuẩn hiện tại; nằm trong danh sách chỉ định archive của R1 (chứa Kurtosis sai 16,433, max return sai +1,364%, số quan sát sai 5,920,516) | Move vào docs/archive/ |
| 76 | `docs/Data report/project_report.html` | `.html` | 144,649 B | 2026-11-03 14:09:32 | **CURRENT** | Báo cáo tổng hợp HTML cập nhật ngày 03/11/2026; chứa số liệu chuẩn (Kurtosis 66.88, 5.6M stock-days, CORR_001-013); sẽ được đồng bộ bổ sung ở R8 | Giữ nguyên hoạt động (Cập nhật ở R8) |
| 77 | `docs/Data report/russell1000_universe_preprocessing.html` | `.html` | 108,610 B | 2026-11-02 19:17:36 | **STALE_OLD_PIPELINE** | Báo cáo HTML thuộc pipeline cũ (Phase 1 / Phase 2 cũ); số liệu không khớp chuẩn hiện tại; nằm trong danh sách chỉ định archive của R1 | Move vào docs/archive/ |
| 78 | `docs/Data report/russell1000_universe_preprocessing_v2.html` | `.html` | 86,043 B | 2026-11-02 21:40:14 | **STALE_OLD_PIPELINE** | Báo cáo HTML thuộc pipeline cũ (Phase 1 / Phase 2 cũ); số liệu không khớp chuẩn hiện tại; nằm trong danh sách chỉ định archive của R1 | Move vào docs/archive/ |
| 79 | `docs/Teacher Resource/Research_Directions.pdf` | `.pdf` | 195,698 B | 2026-09-13 16:43:32 | **KEEP_AS_REFERENCE** | Tài liệu hướng dẫn, đề bài của giảng viên và tài liệu tham khảo nghiên cứu định lượng | Giữ nguyên tham chiếu (Keep as Reference) |
| 80 | `docs/Teacher Resource/Rusell.md` | `.md` | 7,433 B | 2026-09-23 19:05:25 | **KEEP_AS_REFERENCE** | Tài liệu hướng dẫn, đề bài của giảng viên và tài liệu tham khảo nghiên cứu định lượng | Giữ nguyên tham chiếu (Keep as Reference) |
| 81 | `docs/Teacher Resource/quant overview.pdf` | `.pdf` | 77,299,182 B | 2026-11-03 20:57:59 | **KEEP_AS_REFERENCE** | Tài liệu hướng dẫn, đề bài của giảng viên và tài liệu tham khảo nghiên cứu định lượng | Giữ nguyên tham chiếu (Keep as Reference) |
| 82 | `docs/refer_report.pdf` | `.pdf` | 2,176,787 B | 2026-09-28 19:37:02 | **KEEP_AS_REFERENCE** | Tài liệu hướng dẫn, đề bài của giảng viên và tài liệu tham khảo nghiên cứu định lượng | Giữ nguyên tham chiếu (Keep as Reference) |

### 4.1. Phân Tích Chuyên Sâu Sai Lệch Số Liệu Trong `docs/`
1. **Thư mục `docs/Data report/phase2/` (19 files)**:
   - Toàn bộ 19 file (gồm 6 file markdown, 7 bảng CSV và 6 đồ thị PNG) được tạo vào ngày 03/10/2026 dựa trên dữ liệu chưa xử lý chia tách ngược.
   - Báo cáo `eda_01_return_distribution_report.md` công bố số liệu: Excess Kurtosis = **16,433**, Skewness = **+41.08**, Max return = **+1,364.52%**, Số quan sát = **5,920,516**.
   - Trong khi đó, số liệu chuẩn hiện tại (Step 6) là: Excess Kurtosis = **66.88**, Skewness = **+0.563**, Max return = **+227.87%**, Số quan sát = **5,610,691**.
   - Báo cáo `t5_alpha_benchmark_report.md` và `t4_feature_store_report.md` đánh giá các feature trên tập dữ liệu cũ.
   - **Hành động**: Chuyển toàn bộ thư mục `docs/Data report/phase2/` vào `docs/archive/phase2/`.

2. **Các báo cáo HTML cũ tại `docs/Data report/`**:
   - `phase1_report.html` (73.5 KB) và `phase2_report.html` (79.7 KB): Báo cáo HTML tĩnh của pipeline cũ, chứa số liệu sai lệch.
   - `russell1000_universe_preprocessing.html` (108.6 KB) và `_v2.html` (86.0 KB): Báo cáo tiền xử lý vũ trụ sơ khởi.
   - `institutional_pipeline_report.html` (144.6 KB): Giống hệt 100% từng byte với `project_report.html` (cùng SHA/kích thước), gây dư thừa.
   - **Hành động**: Chuyển 4 file HTML cũ và bản duplicate vào `docs/archive/`.

3. **Kho Báo Cáo Chuẩn Mực Hiện Tại (`docs/Data report/market_data_audit/`)**:
   - Gồm 2 báo cáo Markdown hoàn chỉnh (`market_data_audit_report.md`, `step2_identity_and_corporate_actions_report.md`).
   - Gồm 4 đồ thị phân giải cao phân tích phân phối return, Q-Q plot, biến động dispersion và luân chuyển universe.
   - Gồm **41 bảng CSV audit chi tiết** (100% khớp chuẩn Ground Truth: 3,711 SIDs, 13 corrections, 34 forensic cases, ma trận sanity checks, split factor audits).
   - **Hành động**: Giữ nguyên toàn bộ làm tài sản cốt lõi của dự án.

---

## 5. KIỂM KÊ THƯ MỤC `data/processed/` (65 FILES)

Thư mục `data/processed/` chứa kho dữ liệu phục vụ nghiên cứu và huấn luyện mô hình ML. Kết quả kiểm kê như sau:

| STT | Đường dẫn file | Kích thước | Kích thước ma trận (Shape) | Các cột tiêu biểu | Phân loại | Đề xuất hành động |
|:---:|:---|:---:|:---:|:---|:---:|:---|
| 1 | `data/processed/constituents_market_data/audit/master_batch_identity.csv` | 4.64 MB | `[83,848, 6]` | year, original_ticker, candidate | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 2 | `data/processed/constituents_market_data/audit/master_batch_status.csv` | 1.80 MB | `[83,636, 5]` | year, original_ticker, status | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 3 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_1998.parquet` | 3.89 MB | `[467,141, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 4 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_1999.parquet` | 4.20 MB | `[484,119, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 5 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2000.parquet` | 4.63 MB | `[502,426, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 6 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2001.parquet` | 4.77 MB | `[488,151, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 7 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2002.parquet` | 4.89 MB | `[487,077, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 8 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2003.parquet` | 5.47 MB | `[480,190, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 9 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2004.parquet` | 5.59 MB | `[482,480, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 10 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2005.parquet` | 5.66 MB | `[483,885, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 11 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2006.parquet` | 5.63 MB | `[477,095, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 12 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2007.parquet` | 5.93 MB | `[471,199, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 13 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2008.parquet` | 6.13 MB | `[467,807, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 14 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2009.parquet` | 5.89 MB | `[453,400, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 15 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2010.parquet` | 5.93 MB | `[451,099, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 16 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2011.parquet` | 6.00 MB | `[448,171, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 17 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2012.parquet` | 5.96 MB | `[443,438, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 18 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2013.parquet` | 6.11 MB | `[446,567, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 19 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2014.parquet` | 6.27 MB | `[453,692, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 20 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2015.parquet` | 6.36 MB | `[456,480, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 21 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2016.parquet` | 6.26 MB | `[449,211, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 22 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2017.parquet` | 6.22 MB | `[440,195, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 23 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2018.parquet` | 6.25 MB | `[435,764, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 24 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2019.parquet` | 6.34 MB | `[434,352, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 25 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2020.parquet` | 6.93 MB | `[433,180, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 26 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2021.parquet` | 7.18 MB | `[440,952, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 27 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2022.parquet` | 7.16 MB | `[442,177, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 28 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2023.parquet` | 7.07 MB | `[432,062, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 29 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2024.parquet` | 7.17 MB | `[429,340, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 30 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2025.parquet` | 7.14 MB | `[419,549, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 31 | `data/processed/constituents_market_data/by_year/constituents_ohlcv_2026.parquet` | 6.11 MB | `[346,190, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 32 | `data/processed/constituents_market_data/corporate_actions/russell1000_corporate_actions_1998_2026.zip` | 0.75 MB | `N/A` | None | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 33 | `data/processed/constituents_market_data/corporate_actions/russell1000_dividends_1998_2026.csv` | 4.35 MB | `[96,773, 6]` | date, original_ticker, symbol | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 34 | `data/processed/constituents_market_data/corporate_actions/russell1000_splits_1998_2026.csv` | 0.23 MB | `[4,788, 6]` | date, original_ticker, symbol | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 35 | `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` | 198.12 MB | `[13,147,389, 9]` | date, original_ticker, qc_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 36 | `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | 484.32 MB | `[12,247,081, 25]` | date, canonical_sid, original_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 37 | `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet` | 155.76 MB | `[12,247,081, 9]` | date, canonical_sid, original_ticker | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 38 | `data/processed/market_data/master_batch_identity.csv` | 4.64 MB | `[83,848, 6]` | year, original_ticker, candidate | **REDUNDANT_DUPLICATE** | Move vào data/archive/ hoặc dọn dẹp để chuẩn hóa đường dẫn |
| 39 | `data/processed/market_data/master_batch_status.csv` | 1.80 MB | `[83,636, 5]` | year, original_ticker, status | **REDUNDANT_DUPLICATE** | Move vào data/archive/ hoặc dọn dẹp để chuẩn hóa đường dẫn |
| 40 | `data/processed/matrices/adj_close.parquet` | 54.59 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 41 | `data/processed/matrices/adj_dividend.parquet` | 2.81 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 42 | `data/processed/matrices/adj_high.parquet` | 55.20 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 43 | `data/processed/matrices/adj_low.parquet` | 54.93 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 44 | `data/processed/matrices/adj_open.parquet` | 53.30 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 45 | `data/processed/matrices/adj_volume.parquet` | 80.45 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 46 | `data/processed/matrices/close.parquet` | 49.59 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 47 | `data/processed/matrices/cumulative_split_factor.parquet` | 2.36 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 48 | `data/processed/matrices/daily_return.parquet` | 108.95 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 49 | `data/processed/matrices/high.parquet` | 50.38 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 50 | `data/processed/matrices/is_bad_data_period.parquet` | 2.08 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 51 | `data/processed/matrices/is_consecutive_session.parquet` | 2.10 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 52 | `data/processed/matrices/is_spinoff_discontinuity.parquet` | 2.08 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 53 | `data/processed/matrices/low.parquet` | 50.12 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 54 | `data/processed/matrices/matrix_columns_sids.parquet` | 0.04 MB | `[3,711, 1]` | canonical_sid | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 55 | `data/processed/matrices/matrix_dates_index.parquet` | 0.06 MB | `[7,252, 1]` | date | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 56 | `data/processed/matrices/membership_mask.parquet` | 2.10 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 57 | `data/processed/matrices/open.parquet` | 48.51 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 58 | `data/processed/matrices/resolved_membership_mask.parquet` | 2.10 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 59 | `data/processed/matrices/strict_membership_mask.parquet` | 2.10 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 60 | `data/processed/matrices/target_next_return.parquet` | 58.90 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 61 | `data/processed/matrices/target_next_total_return.parquet` | 58.90 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 62 | `data/processed/matrices/total_return.parquet` | 108.96 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 63 | `data/processed/matrices/valid_data_mask.parquet` | 2.10 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 64 | `data/processed/matrices/valid_label_mask.parquet` | 2.11 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |
| 65 | `data/processed/matrices/volume.parquet` | 77.17 MB | `[7,252, 3,712]` | A R735QTJ8XC9X, A RPTMYV3VC57P, AA R735QTJ8XC9X | **CURRENT** | Giữ nguyên hoạt động (Keep Active) |

### 5.1. Đánh Giá Kiến Trúc Dữ Liệu Hiện Tại
1. **Tier 1 & Tier 2 Market Data Warehouses**:
   - `russell1000_constituents_daily_ohlcv_1998_2026.parquet` (198.12 MB): 13,147,389 dòng x 9 cột. Chứa toàn bộ dữ liệu OHLCV thô trích xuất từ QuantConnect.
   - `russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet` (155.76 MB): 12,247,081 dòng x 9 cột. Đã khử trùng hoàn toàn danh tính, mapping về 3,711 canonical SIDs, khóa chính `(date, canonical_sid)` đạt tính duy nhất 100% (0 duplicate).
   - `russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` (484.32 MB): 12,247,081 dòng x 25 cột. Kho dữ liệu cao cấp nhất, tích hợp hệ số chia tách tích lũy liên tục (cumulative split factor), giá điều chỉnh ngược (adj_open, adj_high, adj_low, adj_close), cash dividends, và các quality flags (`is_bad_data_period`, `is_spinoff_discontinuity`, `is_consecutive_session`).

2. **Hệ Thống 17 Ma Trận 2D & 3-Tier PIT Masks (`data/processed/matrices/`)**:
   - Toàn bộ 26 file parquet trong thư mục này đều có kích thước thống nhất: **7,252 ngày giao dịch (1998–2026) x 3,712 cột** (Cột 0 là `date` index + 3,711 SIDs).
   - Gồm 17 ma trận giá trị (OHLCV thô và điều chỉnh, daily_return, total_return, target_next_return, v.v.).
   - Gồm hệ thống mặt nạ 3 lớp chuẩn Point-in-Time: `membership_mask`, `valid_data_mask`, `valid_label_mask` đảm bảo tuyệt đối không rò rỉ dữ liệu (No Look-Ahead, Zero Data Snooping).

3. **Phát Hiện File Trùng Lặp Cần Chuẩn Hóa**:
   - Thư mục `data/processed/market_data/` chứa 2 file `master_batch_identity.csv` (4.64 MB) và `master_batch_status.csv` (1.80 MB).
   - Hai file này **hoàn toàn trùng khớp từng byte (100% duplicate)** với 2 file cùng tên trong `data/processed/constituents_market_data/audit/`.
   - **Hành động**: Chuẩn hóa đường dẫn trong script 03 để trỏ về `constituents_market_data/audit/` và lưu trữ/dọn dẹp thư mục dư thừa `market_data/`.

---

## 6. KẾ HOẠCH LƯU TRỮ CHO MILESTONE M1 (ARCHIVING EXECUTION PLAN)

Dựa trên kết quả rà soát chi tiết ở R0, đề xuất thực thi lưu trữ cho Milestone M1 tuân thủ nghiêm ngặt nguyên tắc **KHÔNG XÓA VĨNH VIỄN BẤT KỲ FILE NÀO**, chỉ di chuyển có hệ thống vào thư mục archive tương ứng:

### 6.1. Danh Sách Tệp Cần Chuyển Vào `scripts/archive/` (Tổng cộng 29 files)

1. **Chuyển từ thư mục gốc `scripts/` (5 files)**:
   - `scripts/08_train_quick_test.py`
   - `scripts/09_inspect_predictions.py`
   - `scripts/10_backtest_top10.py`
   - `scripts/audit_step1_warehouse_and_pit_coverage.py`
   - `scripts/build_audit_reports.py`

2. **Chuyển từ `scripts/01_pipeline/` (5 files)**:
   - `scripts/01_pipeline/02b_test_empty_ticker_candidates.py`
   - `scripts/01_pipeline/02c_test_targeted_recovery_v2.py`
   - `scripts/01_pipeline/05_build_cross_sectional.py`
   - `scripts/01_pipeline/11_apply_forensic_corrections_and_rerun_eda.py`
   - `scripts/01_pipeline/plot_universe_coverage_stacked.py`

3. **Chuyển nguyên thư mục các gói cũ vào `scripts/archive/` (19 files)**:
   - `scripts/02_validation_universe/` (3 files: `test1_universe_structure.py`, `test3_universe_pit_turnover.py`, `test4_security_identity.py`)
   - `scripts/03_validation_ohlcv/` (5 files: `test_m1_ohlcv_structure.py`, `test_m2_time_coverage.py`, `test_m3_corporate_actions.py`, `test_m4_russell_ohlcv_compatibility.py`, `test_m5_m6_market_value.py`)
   - `scripts/04_deep_audit/` (1 file: `deep_audit_survivorship.py`)
   - `scripts/05_eda/` (4 files: `__init__.py`, `eda_01_return_distribution.py`, `eda_02_nan_universe_dynamics.py`, `sanity_check_in_sample.py`)
   - `scripts/06_features/` (3 files: `__init__.py`, `analyze_feature_correlation.py`, `build_feature_store.py`)
   - `scripts/07_alpha_eval/` (2 files: `__init__.py`, `eval_benchmark_alpha.py`)
   - *(Riêng `scripts/build_comprehensive_project_report.py`: Giữ lại tại `scripts/` tạm thời để phục vụ R8 biên dịch HTML report, sau đó archive hoặc đổi tên thành build script chính thức)*.

### 6.2. Danh Sách Tệp Cần Chuyển Vào `docs/archive/` (Tổng cộng 30 files)

1. **Chuyển các file HTML đơn lẻ từ `docs/Data report/` (5 files)**:
   - `docs/Data report/institutional_pipeline_report.html` (Bản sao trùng lặp)
   - `docs/Data report/phase1_report.html` (Báo cáo HTML Phase 1 cũ)
   - `docs/Data report/phase2_report.html` (Báo cáo HTML Phase 2 cũ, số liệu sai)
   - `docs/Data report/russell1000_universe_preprocessing.html` (Bản v1 cũ)
   - `docs/Data report/russell1000_universe_preprocessing_v2.html` (Bản v2 cũ)

2. **Chuyển nguyên thư mục `docs/Data report/phase1/` vào `docs/archive/phase1/` (6 files)**:
   - `phase1_data_validation_report.md`
   - `test_results_report.md`
   - `figures/step1_universe_count_by_year.png`
   - `figures/step2_market_data_coverage.png`
   - `figures/test3_universe_turnover.png`
   - `figures/universe_constituents_coverage.png`

3. **Chuyển nguyên thư mục `docs/Data report/phase2/` vào `docs/archive/phase2/` (19 files)**:
   - 6 file Markdown báo cáo (`eda_01_return_distribution_report.md`, `eda_02_nan_universe_report.md`, `phase2_eda_feature_summary.md`, `sanity_check_report.md`, `t4_feature_store_report.md`, `t5_alpha_benchmark_report.md`).
   - 7 file bảng CSV (`eda_01_annual_dispersion.csv`, `eda_01_return_stats.csv`, `eda_02_ticker_lifespan.csv`, `eda_02_universe_dynamics.csv`, `feature_correlation_matrix.csv`, `feature_high_correlation_pairs.csv`, `t5_feature_ic_ranking.csv`, `t5_reversal5d_annual_ic.csv`, `t5_reversal5d_daily_ic.csv`).
   - 6 file biểu đồ PNG (`eda_01_return_distribution.png`, `eda_02_nan_universe_dynamics.png`, `feature_correlation_heatmap.png`, `t5_alpha_benchmark_ic.png`).

### 6.3. Quy Chuẩn Tạo README.md Trong Thư Mục Archive
Sau khi Milestone M1 di chuyển các file trên, agent M1 sẽ tạo hai file tài liệu điều hướng:
1. `scripts/archive/README.md`: Bảng kê tên từng file, mục đích ban đầu, lý do lưu trữ và script thay thế trong `scripts/01_pipeline/`.
2. `docs/archive/README.md`: Bảng kê tên từng file/thư mục báo cáo, giai đoạn tạo ra (Phase 1 / Phase 2 cũ), nguyên nhân lỗi thời (sai số liệu Kurtosis/Return/SIDs hoặc thay đổi kiến trúc pipeline).

---
**Báo cáo kết thúc kiểm kê — Đã sẵn sàng chuyển giao cho Milestone M1 (Archiving).**