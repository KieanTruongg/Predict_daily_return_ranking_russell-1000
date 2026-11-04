# Lưu Trữ Mã Nguồn Cũ (Scripts Archive Repository)

> **Dự án**: Russell 1000 Daily Return Ranking Prediction Engine  
> **Milestone**: M1 (Section R1 — Archive Toàn Diện)  
> **Ngày thực hiện**: 2026-11-04  
> **Quy chuẩn**: Bảo toàn nguyên vẹn 100% mã nguồn lịch sử (Zero Deletion Policy), chuyển giao toàn bộ script prototype, test suite cũ và pipeline v1 vào không gian lưu trữ chuyên biệt.

---

## 1. Tổng Quan Kiến Trúc Lưu Trữ

Trong quá trình tái cấu trúc toàn diện pipeline sản xuất (Production Pipeline Overhaul), toàn bộ mã nguồn xử lý dữ liệu và mô hình hóa đã được chuyển đổi từ kiến trúc bảng dọc (Tall/Long Table format) sang **hệ thống 17 Ma trận 2D chuẩn hóa** (`data/processed/matrices/`) kết hợp với **hệ thống Mặt nạ 3 lớp Point-in-Time (PIT)** (`membership_mask`, `valid_data_mask`, `valid_label_mask`).

Các mã nguồn được chuyển vào thư mục này gồm:
1. **Script prototype & backtest nhanh ngoài thư mục gốc (`scripts/`)**: Các script thử nghiệm mô hình LightGBM trên feature store cũ trước khi có ma trận 2D.
2. **Script kiểm thử & vá lỗi trung gian trong (`scripts/01_pipeline/`)**: Các script phục hồi ticker trên QuantConnect, script xây dựng cross-sectional cũ và script can thiệp pháp y trung gian đã được hợp nhất vào pipeline chuẩn.
3. **Các gói kiểm thử & EDA thuộc Pipeline v1 cũ (`02_validation_universe/` đến `07_alpha_eval/`)**: Bộ mã nguồn xây dựng từ tháng 10/2026, vận hành trên dữ liệu chưa xử lý chia tách ngược (Reverse Split), dẫn đến số liệu méo mó nghiêm trọng.

---

## 2. Bảng Kê Chi Tiết 29 Tệp Mã Nguồn Đã Lưu Trữ & Script Thay Thế

| STT | Tên Tệp / Thư Mục | Nguồn Gốc Ban Đầu | Mục Đích Ban Đầu | Lý Do Lưu Trữ (Archiving Rationale) | Script Thay Thế Trong `scripts/01_pipeline/` |
|:---:|:---|:---|:---|:---|:---|
| 1 | `08_train_quick_test.py` | `scripts/` | Huấn luyện thử nghiệm mô hình LightGBM baseline trên universe Russell 1000 PIT | Sử dụng định dạng `feature_store_long.parquet` cũ; chia tập train 2018–2022 không tuân thủ phân vùng chuẩn (Dev 2000–2023, OOS 2024–2026); chưa khai thác 17 ma trận 2D | Roadmap Step 8/9: Huấn luyện mô hình chuẩn trên ma trận 2D |
| 2 | `09_inspect_predictions.py` | `scripts/` | Soi và phân tích phân phối dự báo của mô hình prototype 08 | Phụ thuộc hoàn toàn vào output của script prototype 08 và cấu trúc feature cũ | Roadmap Step 9: Module đánh giá dự báo và ranking chuẩn |
| 3 | `10_backtest_top10.py` | `scripts/` | Mô phỏng backtest chiến lược Top 10 cổ phiếu năm 2023 | Thử nghiệm sơ bộ trên kết quả LightGBM cũ; chưa tích hợp mô hình chi phí giao dịch, trượt giá và bộ lọc mặt nạ 3 lớp PIT | Roadmap Step 10: Backtest engine chính thức dựa trên `strict_membership_mask` |
| 4 | `audit_step1_warehouse_and_pit_coverage.py` | `scripts/` | Tiện ích kiểm tra sơ bộ kho dữ liệu và độ bao phủ PIT sau khi tải batch QC | Đã được tái cấu trúc thành các module chuẩn trong pipeline chính thức; không còn được gọi trực tiếp | `03_process_10_batches_to_parquet.py`, `04_audit_identity_and_build_canonical_mapping.py` |
| 5 | `build_audit_reports.py` | `scripts/` | Tổng hợp và xuất các bảng báo cáo kiểm toán sơ khởi | Tạo báo cáo tạm thời cho đợt batch QC đầu tiên; đã được thay thế bởi hệ thống 41 bảng CSV kiểm toán chuyên sâu | `04b_generate_comprehensive_step3_audits.py`, `08_validate_matrices_and_sanity_checks.py` |
| 6 | `02b_test_empty_ticker_candidates.py` | `scripts/01_pipeline/` | Rà soát tìm ứng viên thay thế cho các ticker trả về rỗng trên QuantConnect | Script nghiên cứu thăm dò (exploratory research). Logic phục hồi đã được đúc kết thành công vào quy trình mapping chính thức | `04_audit_identity_and_build_canonical_mapping.py` |
| 7 | `02c_test_targeted_recovery_v2.py` | `scripts/01_pipeline/` | Thử nghiệm phục hồi chuyên sâu đợt 2 cho các mã ticker dị biệt | Nghiên cứu đã hoàn thành. 13 ca dị biệt đã được chuẩn hóa thành bảng `market_data_corrections_and_exceptions.csv` | `06_process_corporate_actions_and_adjusted_prices.py` |
| 8 | `05_build_cross_sectional.py` | `scripts/01_pipeline/` | Xây dựng bảng cross-sectional và phân chia in-sample / out-sample | Thuộc kiến trúc pipeline v1 (tạo ngày 02/10/2026), import từ `src.data` cũ, ghi dữ liệu ra thư mục legacy, xung đột với kiến trúc ma trận 2D | `07_build_2d_matrices_and_masks.py` |
| 9 | `11_apply_forensic_corrections_and_rerun_eda.py` | `scripts/01_pipeline/` | Vá dữ liệu 13 ca CORR_001–CORR_013 vào ma trận và tính lại EDA | Script can thiệp trung gian tạm thời. Toàn bộ logic vá dữ liệu đã được tích hợp trực tiếp upstream vào script 06, 07, 09 và 10 | `06_process_corporate_actions_and_adjusted_prices.py`, `07_build_2d_matrices_and_masks.py`, `09_run_development_eda.py` |
| 10 | `plot_universe_coverage_stacked.py` | `scripts/01_pipeline/` | Vẽ biểu đồ diện tích chồng (stacked area) về độ bao phủ vũ trụ | Script vẽ biểu đồ độc lập giai đoạn đầu; biểu đồ chuẩn đã được tích hợp vào báo cáo audit và HTML report | `09_run_development_eda.py`, `scripts/build_comprehensive_project_report.py` |
| 11 | `build_comprehensive_project_report.py` *(Bản sao)* | `scripts/` | Biên dịch toàn bộ dữ liệu audit thành báo cáo HTML tự chứa | Bản sao lưu trữ để đối chiếu phiên bản. Bản hoạt động chính (ACTIVE) vẫn được duy trì tại `scripts/build_comprehensive_project_report.py` để phục vụ R8 | `scripts/build_comprehensive_project_report.py` (Active tool) |
| 12 | `02_validation_universe/` *(Thư mục gồm 3 files)* | `scripts/` | Kiểm thử tính toàn vẹn cấu trúc universe và luân chuyển PIT Phase 1 | Dựa trên danh sách ticker thô chưa chuẩn hóa canonical SID, không phản ánh chính xác 3,711 SIDs duy nhất | `04_audit_identity_and_build_canonical_mapping.py`, `05_rigorous_pit_membership_reconstruction.py` |
| 13 | `03_validation_ohlcv/` *(Thư mục gồm 5 files)* | `scripts/` | Kiểm thử dữ liệu giá OHLCV, tính liên tục thời gian và tương thích Russell | Thuộc bộ test suite Phase 1 cũ; chưa xử lý dồn tích split factor liên tục và các ca chia tách ngược dị biệt | `06_process_corporate_actions_and_adjusted_prices.py`, `08_validate_matrices_and_sanity_checks.py` |
| 14 | `04_deep_audit/` *(Thư mục gồm 1 file)* | `scripts/` | Thẩm định chuyên sâu sai lệch sống sót (Survivorship Bias) | Nghiên cứu sơ khởi; vấn đề sai lệch sống sót hiện được xử lý triệt để thông qua 3 lớp mask PIT trên 7,252 ngày giao dịch | `05_rigorous_pit_membership_reconstruction.py`, `07_build_2d_matrices_and_masks.py` |
| 15 | `05_eda/` *(Thư mục gồm 4 files)* | `scripts/` | Phân tích phân phối tỷ suất sinh lời, động thái NaN và kiểm tra in-sample Phase 2 | Tính toán trên dữ liệu chưa hiệu chỉnh chia tách ngược, cho ra số liệu méo mó nghiêm trọng (Kurtosis 16,433, Max Return +1,364.52%) | `09_run_development_eda.py`, `10_investigate_extreme_returns.py` |
| 16 | `06_features/` *(Thư mục gồm 3 files)* | `scripts/` | Tính toán và lưu trữ các feature kỹ thuật dưới dạng bảng dài (Long format) | Kiến trúc bảng dài gây thắt nút cổ chai bộ nhớ và không tối ưu hóa tính toán cross-sectional; tính trên giá chưa khử nhiễu | Bản thiết kế specs 16 features ma trận 2D trong `docs/reports/step7_feature_engineering_plan.md` |
| 17 | `07_alpha_eval/` *(Thư mục gồm 2 files)* | `scripts/` | Đánh giá hệ số thông tin (Information Coefficient - IC) của các alpha benchmark | Đánh giá trên tập feature cũ và target chưa chuẩn hóa cross-sectional ranking; số liệu IC bị nhiễu bởi các gai giá lỗi | Module Alpha Evaluation chuẩn dựa trên `target_next_rank` (Uniform [0, 1]) |

---

## 3. Danh Sách Tệp Bên Trong Các Gói Cũ (Sub-Directory Breakdown)

### 3.1. `scripts/archive/02_validation_universe/` (3 files)
- `test1_universe_structure.py`: Kiểm thử cấu trúc bảng universe iShares thô.
- `test3_universe_pit_turnover.py`: Đo lường tỷ lệ luân chuyển danh mục hàng năm theo ticker thô.
- `test4_security_identity.py`: Kiểm tra định danh chứng khoán giai đoạn đầu.

### 3.2. `scripts/archive/03_validation_ohlcv/` (5 files)
- `test_m1_ohlcv_structure.py`: Kiểm tra schema cột của dữ liệu nến ngày.
- `test_m2_time_coverage.py`: Đánh giá độ phủ thời gian từ năm 2000.
- `test_m3_corporate_actions.py`: Kiểm tra các sự kiện cổ tức và chia tách thô.
- `test_m4_russell_ohlcv_compatibility.py`: Đánh giá độ khớp giữa danh sách thành viên và dữ liệu giá.
- `test_m5_m6_market_value.py`: Kiểm tra giá trị giao dịch và vốn hóa ước tính.

### 3.3. `scripts/archive/04_deep_audit/` (1 file)
- `deep_audit_survivorship.py`: Phân tích tác động của các công ty phá sản, hủy niêm yết.

### 3.4. `scripts/archive/05_eda/` (4 files)
- `__init__.py`: Package initialization.
- `eda_01_return_distribution.py`: Sinh số liệu phân phối cũ (Kurtosis = 16,433, Skew = +41.08).
- `eda_02_nan_universe_dynamics.py`: Phân tích tỷ lệ khuyết dữ liệu và tuổi thọ mã.
- `sanity_check_in_sample.py`: Kiểm tra bất thường giá trên tập in-sample cũ.

### 3.5. `scripts/archive/06_features/` (3 files)
- `__init__.py`: Package initialization.
- `analyze_feature_correlation.py`: Tính ma trận tương quan giữa các feature cũ.
- `build_feature_store.py`: Xây dựng `feature_store_long.parquet` (bảng dọc cũ).

### 3.6. `scripts/archive/07_alpha_eval/` (2 files)
- `__init__.py`: Package initialization.
- `eval_benchmark_alpha.py`: Đánh giá IC chuỗi thời gian của các tín hiệu momentum/reversal cũ.

---

## 4. Hướng Dẫn Kỹ Thuật

- **Tính bất biến**: Tuyệt đối không chỉnh sửa mã nguồn bên trong `scripts/archive/` để giữ tính toàn vẹn lịch sử phục vụ kiểm toán khoa học.
- **Thực thi pipeline hiện tại**: Tất cả quy trình sản xuất được khởi chạy duy nhất từ `scripts/01_pipeline/01_*.py` đến `10_*.py`.
