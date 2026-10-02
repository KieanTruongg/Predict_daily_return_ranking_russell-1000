# 📈 Predict Daily Return Rankings (US Equity - Russell 1000 PIT)

> **Hệ thống Nghiên cứu Định lượng & Machine Learning Alpha Strategy**  
> **Dữ liệu**: Russell 1000 Point-In-Time Index (2000–2026, 27 Năm liên tục)  
> **Mục tiêu**: Dự đoán thứ hạng tỷ suất sinh lời hàng ngày cổ phiếu (Cross-Sectional Daily Return Rankings) & Xây dựng Danh mục Long-Short Dollar-Neutral.  
> **Phiên bản Dữ liệu**: Audit-Grade v4 (Point-In-Time Security Identity Resolution via `mappingResolveDate` — 99.42% Coverage)

---

## 📌 Tổng Quan Dự Án

Dự án phát triển một hệ thống định lượng (Quantitative Trading Framework) hoàn chỉnh theo chuẩn các Quỹ đầu tư định lượng (Hedge Funds / WorldQuant IQC), bao gồm 8 Phases xử lý toàn diện:

1. **Phase 1: Point-In-Time Data Pipeline**: Trích xuất dữ liệu gốc PDF/CSV của FTSE Russell, tải dữ liệu OHLCV từ QuantConnect Lean Engine (`SplitAdjusted` với cơ chế mappingResolveDate), và kiểm toán tính toàn vẹn 27 năm (2000–2026, 6.6M dòng, 2,860 tickers, 99.42% match rate).
2. **Phase 2: Alpha & Feature Store**: Tính toán 50+ đặc trưng kỹ thuật, biến động, khối lượng và các chỉ báo định lượng (Cross-Sectional Alphas, Reversal 5D, Momentum, Volatility).
3. **Phase 3: Machine Learning & Ranking Models**: Huấn luyện các mô hình học máy chuyên biệt bài toán xếp hạng (XGBoost, LambdaMART, PyTorch LSTM).
4. **Phase 4: Meta-Alpha Ensemble**: Tổng hợp tín hiệu đa mô hình (Equal-weight, Stacking, Inverse-Variance Ensemble).
5. **Phase 5: Position Engine & Backtester**: Chuẩn hóa danh mục Long-Short Dollar-Neutral ($\sum w = 0, \sum |w| = 1$), chạy Backtest Vectorized đo lường Sharpe Ratio, Rank IC, Drawdown & PnL trên 2 tập phân chia nghiêm ngặt **In-Sample (<2024)** và **Out-of-Sample (>=2024)**.
6. **Phase 6: Production REST API**: Cung cấp dịch vụ FastAPI dự đoán thứ hạng và chạy backtest thời gian thực.
7. **Phase 7: Interactive Dashboard**: Giao diện Web tương tác Streamlit trực quan hóa hiệu năng chiến lược và đồ thị PnL.
8. **Phase 8: Monitoring & Drift Detection**: Giám sát biến động dữ liệu (Data Drift) và suy giảm hiệu năng mô hình (Concept Drift).

---

## 🏗️ Cấu Trúc Thư Mục Dự Án (Complete Directory Architecture)

```text
Predict_daily_return_rankings/
├── configs/                            # Cấu hình dự án & Tham số hệ thống
│   └── base_config.yaml                # Cấu hình Universe, thời gian cutoff 2024-01-01, phí giao dịch
├── dashboard/                          # Web Application tương tác (Phase 7)
│   └── app.py                          # Ứng dụng Streamlit hiển thị Dashboard PnL, Rank IC, Alpha Performance
├── data/                               # Quản lý Dữ liệu Định lượng (Phân cấp chi tiết)
│   ├── raw/
│   │   ├── universe/                   # Dữ liệu Universe gốc (PDF/CSV & JSON Point-In-Time từng năm)
│   │   │   ├── by_year/                # russell1000_2000.json ... russell1000_2026.json (27 năm)
│   │   │   ├── raw/                    # Tài liệu thô 2000.pdf ... 2026.xls
│   │   │   ├── extraction_quality_report.csv
│   │   │   ├── missing_ticker_analysis.csv
│   │   │   ├── russell1000_constituents.csv
│   │   │   └── russell1000_pit_by_year.json
│   │   └── market_data/                # Raw ZIP archives giá OHLCV tải từ QuantConnect (2000–2026)
│   └── processed/
│       ├── by_year/                    # File Parquet SplitAdjusted OHLCV độc lập từng năm
│       ├── audit/                      # Bản ghi kiểm toán CSV master và chi tiết theo năm
│       │   ├── master_audit_2000_2026.csv
│       │   └── by_year/                # audit_2000.csv ... audit_2026.csv
│       ├── daily_ohlcv/                # Parquet tổng hợp dữ liệu giao dịch toàn bộ 27 năm (6.6M rows)
│       │   └── russell1000_daily_2000_2026.parquet
│       ├── in_sample/                  # Cửa sổ huấn luyện & validation (2000–2023 | 6,021 trading days)
│       │   ├── close.parquet, returns.parquet, volume.parquet, ...
│       └── out_sample/                 # Cửa sổ khóa dành cho Backtest (2024–2026 | 687 trading days) [LOCKED]
│           ├── close.parquet, returns.parquet, volume.parquet, ...
├── docs/                               # Tài liệu & Báo cáo Nghiên cứu Kiểm định Khoa học
│   ├── Data report/
│   │   ├── data_exploration_report.html # Báo cáo kiểm thử thẩm định dữ liệu trực quan (HTML)
│   │   ├── data_exploration_report.md   # Báo cáo kiểm thử định dạng Markdown
│   │   ├── data_market_value_validation_report.md # Báo cáo kiểm toán thanh khoản & vốn hóa
│   │   └── *.png                       # Biểu đồ minh họa (Universe size, Coverage, Turnover)
│   ├── Teacher Resource/               # Đề bài & Tài liệu tham khảo từ Giảng viên
│   │   ├── Research_Directions.pdf
│   │   └── Rusell.md
│   ├── project_roadmap.html            # Lộ trình nghiên cứu dự án
│   └── workflow.html                   # Sơ đồ quy trình kiến trúc 8 Phases
├── notebooks/                          # Jupyter Notebooks thực nghiệm nghiên cứu
│   └── 01_research_walkthrough.ipynb
├── outputs/                            # Kết quả xuất ra từ hệ thống
│   ├── figures/                        # Đồ thị PnL, biểu đồ kiểm định dữ liệu
│   ├── logs/                           # Nhật ký hệ thống
│   └── reports/                        # Báo cáo hiệu năng backtest
├── scripts/                            # Thư viện Scripts thực thi (Tổ chức theo 4 module)
│   ├── 01_pipeline/                    # Trích xuất dữ liệu, export QC cloud & Parquet conversion
│   │   ├── 01_parse_all_universe.py
│   │   ├── 02_quantconnect_export_by_year_v4_fixed.py
│   │   ├── 03_process_qc_zips_by_year.py
│   │   ├── 04_merge_all_years.py       # Gộp 27 năm by_year thành 1 file parquet tổng hợp
│   │   └── 05_build_cross_sectional.py # Tạo Date x Ticker matrices & phân chia In/Out-of-Sample
│   ├── 02_validation_universe/         # Bộ kiểm thử Russell 1000 Universe PIT (Test 1 - Test 8)
│   │   ├── step1_check_universe.py
│   │   ├── test1_universe_structure.py
│   │   ├── test3_universe_pit_turnover.py
│   │   ├── test4_security_identity.py
│   │   ├── test5_historical_survivorship.py
│   │   ├── test6_crosscheck_archive.py
│   │   ├── test7_ticker_format_mapping.py
│   │   └── test8_final_audit_mismatches.py
│   ├── 03_validation_ohlcv/            # Bộ kiểm thử Market Data OHLCV (Test M1 - Test M6)
│   │   ├── step2_check_market_data.py
│   │   ├── test_m1_ohlcv_structure.py
│   │   ├── test_m2_time_coverage.py
│   │   ├── test_m3_corporate_actions.py
│   │   ├── test_m4_russell_ohlcv_compatibility.py
│   │   └── test_m5_m6_market_value.py
│   └── 04_deep_audit/                  # Kiểm thử chuyên sâu Survivorship Bias & Identity Mapping
│       ├── deep_audit_survivorship.py
│       └── deep_audit_phase2.py
├── src/                                # Mã nguồn chính dự án (Core Python Modules)
│   ├── alphas/                         # Thư viện Alpha factors & Toán tử định lượng
│   │   ├── base.py                     # Base class cho Alpha Factors
│   │   ├── operators.py                # Toán tử Cross-Sectional (Rank, Z-score, Neutralize, Decay)
│   │   ├── alpha_library.py            # Thư viện tập hợp các công thức Alpha
│   │   └── reversal_5d.py              # Alpha mẫu: 5-Day Mean Reversal
│   ├── api/                            # Production REST API Service (FastAPI)
│   │   └── main.py                     # Endpoints (/health, /predict, /backtest, /metrics)
│   ├── backtest/                       # Động cơ Backtest Cross-Sectional Vectorized
│   │   └── engine.py                   # Tính toán PnL, Turnover, Phí giao dịch & Sụt giảm tài sản (Drawdown)
│   ├── data/                           # Module Xử lý & Phân chia Dữ liệu (Cập nhật v4)
│   │   ├── loader.py                   # Data loader đọc trực tiếp từ Parquet v4 (load_full_panel, load_by_year_range, etc.)
│   │   ├── preprocessor.py             # Pivot ra Date x Ticker matrices, Winsorize, Z-score, summary()
│   │   ├── split.py                    # Phân chia in_sample/out_sample với rào chắn chống Data Leakage
│   │   └── universe.py                 # Lọc danh mục cổ phiếu thuộc chỉ số tại từng thời điểm
│   ├── db/                             # Cơ sở dữ liệu lưu trữ vết dự đoán & Backtest
│   │   └── models.py                   # SQLAlchemy ORM schemas
│   ├── ensemble/                       # Kết hợp đa mô hình Meta-Alpha Ensemble
│   │   └── meta_ensemble.py            # Equal-Weight, Inverse-Variance & Stacking Regressor
│   ├── features/                       # Engine Tạo Đặc trưng (Feature Store)
│   │   └── feature_engineer.py         # Trích xuất 50+ kỹ thuật, biến động, khối lượng & tương quan
│   ├── metrics/                        # Đo lường Hiệu năng Định lượng
│   │   ├── information.py              # Rank Information Coefficient (Rank IC, IC IR)
│   │   └── performance.py              # Sharpe Ratio, Sortino, Max Drawdown, Win Rate, Annual Return
│   ├── models/                         # Mô hình Học máy Chuyên bài toán Ranking
│   │   ├── base_model.py               # Base interface cho ML models
│   │   ├── xgboost_model.py            # Mô hình XGBoost Ranker / Regressor
│   │   ├── lambdamart_model.py         # Mô hình LightGBM LambdaMART Listwise Ranking
│   │   └── lstm_model.py               # PyTorch Deep Learning Sequence Model (LSTM)
│   ├── monitoring/                     # Giám sát Trôi lệch Dữ liệu & Mô hình
│   │   └── drift_detector.py           # Data Drift (PSI / KS-test) & Model Performance Drift
│   └── portfolio/                      # Động cơ Tối ưu hóa & Quản lý Vị thế
│       ├── neutralizer.py              # Chuẩn hóa Long-Short Dollar-Neutral ($\sum w = 0, \sum |w| = 1.0$)
│       └── combiner.py                 # Kết hợp vị thế và áp hạn mức rủi ro (Risk Limits)
├── tests/                              # Bộ kiểm thử tự động Unit Tests (PyTest)
│   ├── run_tests.py                    # Test runner tổng hợp
│   ├── test_metrics.py                 # Kiểm thử tính đúng đắn công thức Sharpe/Rank IC
│   ├── test_neutralization.py          # Kiểm thử ràng buộc Dollar-Neutral
│   └── test_operators.py               # Kiểm thử toán tử định lượng (Rank, Z-score)
├── requirements.txt                    # Danh sách thư viện phụ thuộc Python
└── README.md                           # Tài liệu tổng quan & hướng dẫn dự án
```

---

## 🧪 Bộ Kiểm Thử Chất Lượng Dữ Liệu (Data Validation Suite - Version 4)

Báo cáo chi tiết kết quả thẩm định dữ liệu được ghi nhận minh bạch tại:
- 📄 **Báo cáo HTML Trực quan**: [`docs/Data report/data_exploration_report.html`](file:///docs/Data%20report/data_exploration_report.html)
- 📝 **Báo cáo Markdown**: [`docs/Data report/data_exploration_report.md`](file:///docs/Data%20report/data_exploration_report.md)
- 📊 **Báo cáo Thẩm định Vốn hóa & Mapping**: [`docs/Data report/data_market_value_validation_report.md`](file:///docs/Data%20report/data_market_value_validation_report.md)

### Tóm tắt Kết quả Thực nghiệm v4:

| Nhóm bài test | Thư mục Script | Số bài test | Kết quả nổi bật | Trạng thái |
|:---|:---|:---:|:---|:---:|
| **Phần I: Universe PIT** | `scripts/02_validation_universe/` | 8 bài test | Khớp 100% Archive gốc, 0 Duplicate, 0 Null. Dynamic Turnover trung bình **8.84%/năm**. | ✅ **PASS** |
| **Phần II: Market Data OHLCV** | `scripts/03_validation_ohlcv/` | 6 bài test | **6,601,516 dòng** SplitAdjusted OHLCV. Match rate đồng nhất **99.1%–99.9%** trên toàn bộ 27 năm. 0 Lỗi Null/Price bounds. | ✅ **PASS** |
| **Deep Audit** | `scripts/04_deep_audit/` | 4 bước | Overall match rate **99.42%** (26,764 / 26,919 stock-years). Survivorship Gap chỉ **+0.4pp** (Gần như triệt tiêu hoàn toàn rủi ro Thiên vị sống sót). | ✅ **PASS** |

---

## ⚡ Hướng Dẫn Thực Thi (Quick Start)

### 1. Cài Đặt Môi Trường
```bash
# Cài đặt toàn bộ các thư viện phụ thuộc
pip install -r requirements.txt
```

### 2. Kiểm Thử Unit Tests (Toán Học & Logic Chiến Lược)
```bash
# Chạy bộ test tự động kiểm tra hàm Neutralizer, Rank IC và Operators
python tests/run_tests.py
```

### 3. Pipeline Xử Lý & Chuẩn Bị Dữ Liệu v4
```bash
# 1. Merge 27 file by_year parquet thành file tổng hợp
python scripts/01_pipeline/04_merge_all_years.py

# 2. Pivot tạo Date x Ticker matrices & phân chia In-Sample (<2024) / Out-of-Sample (>=2024)
python scripts/01_pipeline/05_build_cross_sectional.py
```

### 4. Kiểm Định Chất Lượng Dữ Liệu (Data Validation Suite)
```bash
# 1. Kiểm tra Universe PIT
python scripts/02_validation_universe/step1_check_universe.py
python scripts/02_validation_universe/test1_universe_structure.py

# 2. Kiểm tra Market Data OHLCV & Tương thích
python scripts/03_validation_ohlcv/step2_check_market_data.py
python scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py
python scripts/03_validation_ohlcv/test_m4_russell_ohlcv_compatibility.py
python scripts/03_validation_ohlcv/test_m5_m6_market_value.py

# 3. Chạy Deep Audit Survivorship Bias
python scripts/04_deep_audit/deep_audit_survivorship.py
```

### 5. Khởi Chạy Production REST API (Phase 6)
```bash
uvicorn src.api.main:app --reload
```
- Tài liệu API tương tác Swagger UI: `http://127.0.0.1:8000/docs`

### 6. Khởi Chạy Web Dashboard Trực Quan (Phase 7)
```bash
streamlit run dashboard/app.py
```
- Giao diện Dashboard tự động mở tại: `http://localhost:8501`

---

## 🏆 Khuyến Nghị Dữ Liệu Cho Machine Learning

1. **Toàn bộ Giai đoạn Huấn luyện & Kiểm thử (2000 – 2026)**:
   - Nhờ bản nâng cấp `v4`, **toàn bộ 27 năm (2000–2026) đều đạt độ phủ 97.8% đến 99.9%** (trung bình **99.42%**).
   - Survivorship Gap siêu nhỏ (**+0.4pp**), loại bỏ rủi ro thiên vị sống sót.
   - Chuỗi thời gian 27 năm bao quát trọn vẹn cả 2 chu kỳ khủng hoảng lớn (Bong bóng Dot-com 2000–2002 và Khủng hoảng tài chính toàn cầu GFC 2008), mang lại sức mạnh vượt trội cho mô hình Machine Learning Alpha.
