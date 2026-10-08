# 📈 Predict Daily Return Rankings — Russell 1000 PIT

> **Dự án Nghiên cứu Định lượng — CO3101 HCMUT**  
> **Mục tiêu**: Dự đoán xếp hạng lợi nhuận ngày T+1 (Cross-Sectional Daily Return Ranking) cho các cổ phiếu Russell 1000 bằng Machine Learning  
> **Dữ liệu**: Russell 1000 Point-In-Time (2000–2026, 27 năm, 6.6M rows, 2,860 tickers)  
> **Trạng thái**: ✅ Phase 1 + Phase 2 Hoàn tất | 🔄 Phase 3 ML Training — Tiếp theo

---

## 📌 Tổng quan bài toán

Thay vì dự báo giá hay lợi nhuận tuyệt đối, bài toán đặt ra là: **"Trong ngày giao dịch T+1, cổ phiếu nào sẽ outperform / underperform so với phần còn lại của Russell 1000?"**

- **Input**: OHLCV lịch sử → 31 features (momentum, technical, volume, volatility)
- **Target**: `target_return_rank` — percentile rank cross-sectional của forward return ngày T+1
- **Model**: LightGBM LambdaMART (ranking objective) — Walk-Forward CV
- **Universe**: Russell 1000 Point-In-Time (không survivorship bias)
- **Training**: Kaggle T4 GPU | **Data**: QuantConnect Cloud

---

## 🗺️ Tiến độ dự án

| Phase | Nội dung | Trạng thái |
|:---:|:---|:---:|
| **Phase 1** | Data Pipeline & Validation (9 tests) | ✅ Hoàn tất |
| **Phase 2** | EDA, Sanity Checks, Feature Store, Alpha IC | ✅ Hoàn tất |
| **Phase 3** | ML Model Training (LightGBM Walk-Forward CV) | 🔄 Tiếp theo |
| Phase 4 | Backtest & Portfolio Construction | ⏳ Chưa bắt đầu |
| Phase 5 | Final OOS Evaluation (2024–2026) | 🔒 LOCKED |

---

## 🏗️ Cấu trúc thư mục

```text
Predict_daily_return_rankings/
├── configs/             # Cấu hình hệ thống (base_config.yaml)
├── data/
│   ├── raw/             # Universe PIT JSONs theo năm & QC raw ZIPs
│   └── processed/       # Matrices in_sample/ (6,021×2,852), out_sample/ (LOCKED), features/ (5.8M rows)
├── docs/Data report/    # Báo cáo HTML trực quan (project, phase1, phase2) & báo cáo chi tiết
├── scripts/
│   ├── 01_pipeline/            # Tải dữ liệu, trích xuất & tạo ma trận chéo (cross-sectional)
│   ├── 02_validation_universe/ # Kiểm thử tính toàn vẹn Universe PIT (T1–T3)
│   ├── 03_validation_ohlcv/    # Kiểm thử dữ liệu OHLCV, Corporate Actions (M1–M5)
│   ├── 04_deep_audit/          # Kiểm toán Survivorship Bias chuyên sâu (T9)
│   ├── 05_eda/                 # Sanity Checks (S1–S7) & Phân tích phân phối lợi nhuận
│   ├── 06_features/            # Xây dựng 31-Feature Store (vectorized, 77.4s)
│   └── 07_alpha_eval/          # Đánh giá Rank IC cho Alpha Benchmark & Features
├── src/
│   ├── alphas/          # Toán tử định lượng (cs_rank, cs_demean...) & Reversal 5D
│   ├── features/        # FeatureEngineer v4 (vectorized matrix ops, winsorize)
│   ├── metrics/         # Thước đo hiệu năng (Rank IC, ICIR, Sharpe...)
│   └── data/            # Module legacy (v3 schema - giữ tham khảo)
├── tests/               # Unit tests cho operators & metrics
└── clear/               # Lưu trữ scripts/tài liệu cũ (không xóa hẳn)
```

---

## 📊 Kết quả Phase 1 — Data Pipeline & Validation

**9 tests**, tất cả trên 6,601,516 rows OHLCV:

| Test | Script | Kết quả | Status |
|:---|:---|:---|:---:|
| T1 Universe Structure | `test1_universe_structure.py` | 0 NULL/Dup/Empty / 26,919 tickers | ✅ PASS |
| T2 PIT Turnover | `test3_universe_pit_turnover.py` | 8.84%/năm avg, 223 blue-chip liên tục | ✅ PASS |
| T3 Security Identity | `test4_security_identity.py` | 198 mismatch (0.74%) — có giải thích | ⚠️ WARN |
| M1 OHLCV Integrity | `test_m1_ohlcv_structure.py` | **0 violations / 6,601,516 rows** | ✅ PASS |
| M2 Time Coverage | `test_m2_time_coverage.py` | 93.8% ≥ 240d, 248.4d/năm avg | ✅ PASS |
| M3 Corporate Actions | `test_m3_corporate_actions.py` | 7/7 split events đúng (AAPL, TSLA, NVDA...) | ✅ PASS |
| M4 Russell↔OHLCV | `test_m4_russell_ohlcv_compatibility.py` | **99.42% match**, 155 EMPTY, 0 extra | ✅ PASS |
| M5/M6 Market Value | `test_m5_m6_market_value.py` | \$1,168T total, \$179.5M/stock/day | ✅ PASS |
| T9 Survivorship Bias | `deep_audit_survivorship.py` | Gap **+0.4pp** (Survivor 99.6% vs Disappeared 99.2%) | ✅ PASS |

> **Kết luận Phase 1**: Data đạt chuẩn **Audit-Grade**. 8/9 PASS, 1 WARNING (non-blocking), 0 FAIL.

---

## 📈 Kết quả Phase 2 — EDA & Feature Engineering

### Sanity Checks (S1–S7) — `scripts/05_eda/sanity_check_in_sample.py`

| Check | Kết quả | Quyết định |
|:---|:---|:---|
| S1 Cross-layer | 155 OOS tickers trong matrix | Filter ≥95% NaN → 589 tickers bị loại |
| S2 Return calc | Max diff = **0.000000** (5 tickers) | Không cần sửa |
| S3 Look-ahead bias | `fwd_return[t] = return[t+1]` exact | Target sạch ✅ |
| S4 NaN profile | **65.5% NaN**, phân bổ đều 64–66%/năm | Bình thường — expected |
| S5 Volume = 0 | AWH: 67d, ARD: 60d zero-vol streak | `volume.replace(0, NaN)` trong Feature Store |
| S6 Price cross-check | 10 tickers × 3 ngày — khớp **100%** | Pipeline merge đúng ✅ |
| S7 adj_close vs close | `adj_close ≡ close` (SplitAdj mode) | Chỉ dùng `close`, bỏ `adj_close` |

### Feature Store (T4) — `scripts/06_features/build_feature_store.py`

| Chỉ tiêu | Giá trị |
|:---|:---|
| Tickers sau filter | 2,263 (−589 OOS) |
| Long-format rows | **5,820,358** |
| Features | **31** (momentum, technical, volume, volatility, CS rank, target) |
| NaN rate | 10.8% |
| Build time | 77.4 giây (vectorized matrix ops) |
| File size | 1,103 MB (`feature_store_long.parquet`) |
| Target mean | 0.5005 (≈0.5 — unbiased ✅) |
| Winsorize | P1%/P99% = −7.30% / +7.69% cross-sectional per day |

### Alpha IC Benchmark (T5) — `scripts/07_alpha_eval/eval_benchmark_alpha.py`

Top features theo Rank IC (Spearman, cross-sectional daily):

| Feature | Mean IC | ICIR | p-value |
|:---|:---:|:---:|:---:|
| `close_to_high` | **+0.01887** | +0.169 | <0.001 *** |
| `ret_252d` | +0.00994 | +0.048 | <0.001 *** |
| `Reversal_5D` (baseline thầy) | +0.00736 | +0.055 | 0.000020 *** |
| `vol_zscore_20` | +0.00701 | +0.108 | <0.001 *** |
| `ret_1d` | **−0.01444** | −0.093 | <0.001 *** |
| `amihud_20d` | −0.00010 | −0.001 | 0.948 — bỏ |

> **Lưu ý**: `ret_1d`, `ret_2d`, `ret_5d` có IC âm → **phải đảo dấu** khi dùng làm feature.  
> `amihud_20d` không có predictive power trên large-cap (p=0.948) → **bỏ khỏi ML model**.

---

## 📄 Báo cáo

| File | Nội dung |
|:---|:---|
| [`docs/Data report/project_report.html`](docs/Data%20report/project_report.html) | Overview tổng hợp Phase 1+2 (offline HTML) |
| [`docs/Data report/phase1_report.html`](docs/Data%20report/phase1_report.html) | Chi tiết Phase 1 — 9 tests (mục đích, code, kết quả, kết luận) |
| [`docs/Data report/phase2_report.html`](docs/Data%20report/phase2_report.html) | Chi tiết Phase 2 — S1–S7, EDA, Feature Store, Alpha IC |

---

## ⚡ Quick Start

### 1. Cài đặt
```bash
pip install -r requirements.txt
```

### 2. Chạy Pipeline (nếu cần rebuild)
```bash
# Merge 27 parquets → consolidated
python scripts/01_pipeline/04_merge_all_years.py

# Build in_sample / out_sample matrices
python scripts/01_pipeline/05_build_cross_sectional.py
```

### 3. Data Validation
```bash
# Phase 1 tests
python scripts/02_validation_universe/test1_universe_structure.py
python scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py
python scripts/04_deep_audit/deep_audit_survivorship.py

# Phase 2 sanity + EDA
python scripts/05_eda/sanity_check_in_sample.py
python scripts/05_eda/eda_01_return_distribution.py
python scripts/05_eda/eda_02_nan_universe_dynamics.py
```

### 4. Build Feature Store
```bash
python scripts/06_features/build_feature_store.py
# Output: data/processed/features/ (~2.6 GB, 77.4 giây)
```

### 5. Evaluate Alpha IC
```bash
python scripts/07_alpha_eval/eval_benchmark_alpha.py
# Output: docs/Data report/phase2/figures/t5_alpha_benchmark_ic.png
```

---

## 🔑 Key Facts

| Fact | Giá trị |
|:---|:---|
| Data source | QuantConnect Cloud (SplitAdjusted mode, không chạy local) |
| Training platform | Kaggle T4 GPU |
| adj_close vs close | `adj_close ≡ close` — QC bakes dividends into close |
| In-sample period | 2000-01-03 → 2023-12-29 (6,021 trading days) |
| Out-sample (LOCKED) | 2024-01-02 → 2026-09-30 (687 trading days) |
| OOS filter | Tickers với ≥95% NaN in-sample → loại (589 tickers) |
| Winsorize | P1%/P99% = −7.30% / +7.69% cross-sectional |
| Min valid days | ≥252 ngày non-NaN trong lookback window |

---

## 🗓️ Roadmap Phase 3

| Bước | Nội dung |
|:---:|:---|
| P3.1 | Feature prep: negate `ret_1d/2d/5d`, drop `amihud_20d` |
| P3.2 | Walk-Forward CV: 5yr train / 1yr val, 2005→2023 |
| P3.3 | LightGBM LambdaMART baseline |
| P3.4 | Hyperparameter tuning (Optuna) |
| P3.5 | Evaluate: Mean IC, NDCG@50/100 trên validation folds |
| P3.6 | Final backtest trên out_sample 🔒 |

---

*CO3101 — Đồ án tổng hợp — TTNT · HCMUT · 10/2026*
