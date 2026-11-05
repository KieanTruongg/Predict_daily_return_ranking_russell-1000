# 📊 BÁO CÁO TỔNG HỢP: EDA & FEATURE ENGINEERING
## Dự án: Predict Daily Return Rankings — Russell 1000 PIT (2000–2026)

> **Giai đoạn**: Phase 2 — EDA & Feature Engineering (hoàn tất)  
> **Ngày**: 03/10/2026  
> **Phạm vi**: Chỉ trên **in-sample data (2000–2023)** — out-sample bị khóa đến backtest cuối  
> **Tài liệu chi tiết**: Xem các báo cáo riêng trong `docs/Data report/`

---

## 🗺️ MỤC LỤC

1. [Tổng quan Phase 2](#tong-quan)
2. [EDA T1: Phân phối Return & CS Dispersion](#eda-t1)
3. [EDA T2: NaN Pattern & Universe Dynamics](#eda-t2)
4. [Sanity Checks S1–S7](#sanity)
5. [Feature Store (T4)](#feature-store)
6. [Alpha Benchmark IC (T5)](#alpha-ic)
7. [Kết luận & Khuyến nghị cho Phase 3](#conclusion)

---

## I. TỔNG QUAN PHASE 2 {#tong-quan}

### Dữ liệu sử dụng
| Dataset | Shape | Period | Source |
|:---|:---:|:---:|:---|
| `in_sample/close.parquet` | 6,021 × 2,852 | 2000–2023 | QuantConnect SplitAdjusted |
| `in_sample/returns.parquet` | 6,021 × 2,852 | 2000–2023 | Derived: close.pct_change() |
| `in_sample/forward_returns.parquet` | 6,021 × 2,852 | 2000–2023 | Derived: returns.shift(-1) |
| `in_sample/volume.parquet` | 6,021 × 2,852 | 2000–2023 | QuantConnect |
| `raw/universe/by_year/*.json` | 27 files | 2000–2026 | FTSE Russell PIT |

### Các task đã hoàn tất

| Task | Script | Trạng thái | Output |
|:---:|:---|:---:|:---|
| S1–S7 | `sanity_check_in_sample.py` | ✅ Done | `sanity_check_report.md` |
| T8 | Tái cấu trúc thư mục | ✅ Done | Scripts reorganized |
| EDA T1 | `eda_01_return_distribution.py` | ✅ Done | `eda_01_return_distribution_report.md` |
| EDA T2 | `eda_02_nan_universe_dynamics.py` | ✅ Done | `eda_02_nan_universe_report.md` |
| T6 | Test results report | ✅ Done | `test_results_report.md` |
| T4 | `build_feature_store.py` | ✅ Done | `data/processed/features/` (1.1 GB) |
| T5 | `eval_benchmark_alpha.py` | ✅ Done | `t5_alpha_benchmark_report.md` |

---

## II. EDA T1: PHÂN PHỐI DAILY RETURN & CROSS-SECTIONAL DISPERSION {#eda-t1}

> 📄 Chi tiết: [`eda_01_return_distribution_report.md`](eda_01_return_distribution_report.md)

### Thống kê mô tả (5,920,516 quan sát)

| Chỉ số | Giá trị | Nhận xét |
|:---|:---:|:---|
| Mean daily return | +0.0484% | Dương nhỏ — thị trường cổ phần long-run |
| Median daily return | +0.0327% | Thấp hơn mean → outlier dương kéo lên |
| Std (daily) | 2.83% | |
| Annualized Std | **44.98%** | Cao hơn 15–20% chuẩn vì gồm cả mid-cap biến động |
| Skewness | **+41.08** | Lệch phải mạnh do outlier M&A/takeover |
| Excess Kurtosis | **16,433** | Cực kỳ fat tails — outlier chưa lọc |
| P1% / P99% | -7.30% / +7.69% | Biên độ cực đoan rộng |

> ⚠️ **Sau winsorize P1%/P99%**: Skewness và Kurtosis sẽ về mức bình thường hơn nhiều (~3–10). Con số raw trên phản ánh outlier M&A/delisting chưa lọc.

### Normality Tests
- **Jarque-Bera** (n=100,000): stat = 6,294,733 | p ≈ 0 → ❌ REJECT H0
- **Shapiro-Wilk** (n=5,000): p = 5.05e-66 → ❌ REJECT H0

> **Kết luận**: Daily return **không tuân theo phân phối chuẩn**. Cần rank-based ML approach.

### Fat Tail Analysis

| Ngưỡng | Số vi phạm | Tỷ lệ |
|:---:|:---:|:---:|
| \|return\| > 5% | 304,250 | 5.14% |
| \|return\| > 10% | 56,220 | 0.95% |
| \|return\| > 50% | 306 | 0.005% |

### Cross-Sectional Dispersion (Market Regime)

| Regime | Giai đoạn | CS Std TB | Ý nghĩa cho model |
|:---:|:---:|:---:|:---|
| ⚡ HIGH | 2000–2002, 2008–2009, 2020 | 2.6–4.4% | Model dễ phân biệt tốt/xấu, IC cao hơn |
| ⚪ NORMAL | 2003–2007, 2010–2012, 2021–2023 | 1.7–2.0% | Baseline performance |
| 😴 LOW | 2005–2006, 2013–2014, 2017–2018 | 1.5–1.7% | Model khó phân biệt, IC thấp hơn |

**Mean CS Std = 2.11%/ngày** — ngày đặc biệt nhất: 2010-04-28 (43.79%, nghi có outlier cổ phiếu đơn lẻ).

---

## III. EDA T2: NaN PATTERN & UNIVERSE DYNAMICS {#eda-t2}

> 📄 Chi tiết: [`eda_02_nan_universe_report.md`](eda_02_nan_universe_report.md)

### NaN Profile (in_sample matrix: 6,021 × 2,852)

| Nhóm tickers | Số | Tỷ lệ | Xử lý |
|:---|:---:|:---:|:---|
| **Full** (0% NaN, 24 năm liên tục) | 240 | 8.4% | Dùng ngay |
| **Partial** (0–95% NaN) | 2,023 | 70.9% | Dùng với min_period filter |
| **OOS only** (≥95% NaN, chỉ 2024+) | **589** | 20.7% | **Loại bỏ** trước feature build |

**Phân bố ngày valid per ticker**: 37.2% tickers có 1–5 năm data, 17.6% có ≥ 12 năm.

### Universe Dynamics (2000–2026)

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Unique tickers Russell 1000 | 2,884 |
| Average Annual Entry | 88.3/năm |
| Average Annual Exit | 87.7/năm |
| **Turnover trung bình** | **8.84%/năm** |
| Tickers tồn tại 27 năm liên tục | 223 (MSFT, XOM, SO...) |
| Tickers chỉ active 1 năm | 486 (16.9%) |
| "Flicker" tickers (vào rồi ra lại) | 361 |

**Năm turnover cao nhất**: 2001 (21.01%) — Dot-com bust  
**Năm turnover thấp nhất**: 2024 (4.90%)

### Ngưỡng lọc cho Feature Store
- **≥ 252 ngày non-NaN trong lookback** → giữ lại 2,553/2,852 tickers (89.5%)
- **Walk-Forward CV** nên dùng annual rebalancing phù hợp turnover 8.84%/năm

---

## IV. SANITY CHECKS S1–S7 {#sanity}

> 📄 Chi tiết: [`sanity_check_report.md`](sanity_check_report.md)

| Check | Kết quả | Hành động |
|:---|:---:|:---|
| S1: Cross-layer consistency | ⚠️ 155 OOS tickers trong matrix | Lọc khi build feature ✅ |
| S2: Return calculation | ✅ Max diff = 0.000000 | Không cần sửa |
| S3: Forward return look-ahead | ✅ EXACT match fwd[t] = ret[t+1] | Target variable sạch |
| S4: NaN profile | ✅ 65.5% NaN, phân bổ đều | Bình thường |
| S5: Volume = 0 streaks | ⚠️ AWH (67d), ARD (60d) | Gán NaN cho Amihud/VWAP ✅ |
| S6: Price cross-check | ✅ by_year ↔ matrix khớp 100% | Pipeline đúng |
| S7: adj_close vs close | ⚠️ adj_close ≡ close (SplitAdj) | Chỉ dùng `close` ✅ |

**Tổng: 4 PASS, 3 WARNING** — Tất cả warning đã được xử lý trong Feature Store.

---

## V. FEATURE STORE (T4) {#feature-store}

> 📄 Chi tiết: [`t4_feature_store_report.md`](t4_feature_store_report.md)

### Pipeline Build
```
in_sample/ (6,021 × 2,852)
  → Filter OOS 589 tickers
  → (6,021 × 2,263)
  → Winsorize P1%/P99% cross-sectional
  → FeatureEngineer.build_feature_matrix() [vectorized, 77s]
  → 31 features
  → feature_store_long.parquet [5,820,358 rows × 33 cols]
```

### 31 Features đã build

| Nhóm | Features |
|:---|:---|
| Momentum/Reversal (7) | `ret_1d, ret_2d, ret_5d, ret_10d, ret_20d, ret_60d, ret_252d` |
| Moving Averages (4) | `close_to_sma_20/50/200, macd_hist_norm` |
| Technical (5) | `rsi_14, bb_pct_b, bb_bandwidth, hl_spread, close_to_high` |
| Volume (4) | `vol_ratio_5_20, vol_zscore_20, close_to_vwap_5, amihud_20d` |
| Volatility (3) | `realized_vol_5d/20d/60d` |
| CS Rank (6) | `ret_1d/5d/20d_rank, rsi_14_rank, vol_20d_rank, amihud_rank` |
| Target (2) | `target_forward_return, target_return_rank` |

### Thống kê Feature Store

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Tickers giữ lại | 2,263 |
| Trading days | 6,021 |
| Long-format rows | **5,820,358** |
| NaN rate (long-format) | **10.8%** |
| File size | 1,103 MB |
| Build time | 77.4 giây |

---

## VI. ALPHA BENCHMARK IC EVALUATION (T5) {#alpha-ic}

> 📄 Chi tiết: [`t5_alpha_benchmark_report.md`](t5_alpha_benchmark_report.md)

### Reversal 5D (Công thức thầy)

| Chỉ tiêu | Giá trị |
|:---|:---:|
| **Mean Rank IC** | **+0.00736** |
| ICIR | 0.055 |
| Positive IC % | 51.5% |
| p-value | 0.000020 (***) |

> **Nhận xét**: IC thấp (< 0.01) nhưng **có ý nghĩa thống kê**. Phù hợp literature (Jegadeesh 1990: IC ~0.01–0.04). Hoạt động tốt nhất trong High Volatility regimes (2001, 2008, 2020), yếu trong bull market (2017–2018).

### Full Feature IC Ranking

```
close_to_high          IC = +0.019 *** (STRONGEST — intraday reversal)
ret_252d               IC = +0.010 *** (12M momentum)
Reversal_5D            IC = +0.007 *** (teacher's formula)
vol_zscore_20          IC = +0.007 *** (volume anomaly)
close_to_sma_200       IC = +0.005 *
vol_ratio_5_20         IC = +0.003 ***
─────────────────────── IC ≈ 0 ──────────────────────
amihud_20d             IC = -0.000   (p=0.95, NOT significant)
ret_60d                IC = -0.001   (p=0.67, NOT significant)
─────────────────────── Negative IC ─────────────────
close_to_sma_20        IC = -0.009 ***
realized_vol_*         IC = -0.009 to -0.010 ***
ret_5d                 IC = -0.011 ***
ret_2d                 IC = -0.012 ***
close_to_vwap_5        IC = -0.014 ***
ret_1d                 IC = -0.014 *** (STRONGEST NEGATIVE — use reversed sign)
```

### Phát hiện quan trọng

1. **`close_to_high` là feature mạnh nhất** (IC = +0.019, ICIR = 0.169): Stocks đóng cửa gần đáy ngày → tăng ngày mai. Intraday reversal effect (Heston et al. 2010).

2. **`ret_1d` có IC âm mạnh nhất** (IC = -0.014): Đảo dấu `ret_1d` = short-term reversal signal. **Phải dùng `-ret_1d` làm feature** khi đưa vào ML model.

3. **Tất cả `realized_vol_*` có IC âm**: High volatility → return thấp hơn ngày mai. Không dùng raw vol làm dự báo dương.

4. **`amihud_20d` không có predictive power** (p = 0.95): Drop feature này khỏi ML model.

---

## VII. KẾT LUẬN & KHUYẾN NGHỊ CHO PHASE 3 {#conclusion}

### A. Kết luận về chất lượng dữ liệu

> ✅ **Dữ liệu đạt chuẩn Audit-Grade** để sử dụng cho ML model:
> - 99.42% coverage, 0 OHLCV violations, pipeline sạch
> - No look-ahead bias (S3 PASS exact)
> - Survivorship Bias gap chỉ +0.4pp (negligible)
> - Feature store: 5.8M rows, NaN rate 10.8%, sẵn sàng cho training

### B. Kết luận về Feature Engineering

| Quyết định | Chi tiết |
|:---|:---|
| **Winsorize** | P1%/P99% cross-sectional — bắt buộc (đã áp dụng) |
| **OOS filter** | Loại 589 tickers 2024+ — đã áp dụng |
| **volume=0** | → NaN cho Amihud/VWAP — đã áp dụng |
| **adj_close** | Không cần — `close` đã SplitAdjusted đủ |
| **Rank transform** | CS rank features đã có — ưu tiên dùng cho tree models |

### C. Feature Selection cho ML Model (Phase 3)

**Ưu tiên cao** (IC *** và > 0.005):
- `close_to_high` (+0.019) — keep as-is
- `vol_zscore_20` (+0.007) — keep as-is
- `vol_ratio_5_20` (+0.003) — keep as-is
- `ret_252d` (+0.010) — keep as-is
- `-ret_1d` (đảo dấu, IC equivalent = +0.014)
- `-ret_2d` (đảo dấu, IC equivalent = +0.012)
- `-ret_5d` (đảo dấu, IC equivalent = +0.011)
- `-close_to_vwap_5` (đảo dấu, IC equivalent = +0.014)

**Giữ lại nhưng ưu tiên thấp**: `rsi_14`, `bb_pct_b`, `close_to_sma_200`, `macd_hist_norm`

**Bỏ khỏi ML model**: `amihud_20d` (p = 0.95)

### D. Walk-Forward Cross-Validation Design

Dựa trên Regime Analysis (T1 + T5):

```
Recommended Walk-Forward Splits:
  Training window : 5 năm (rolling)
  Validation      : 1 năm
  Periods:
    [2000–2004] → test 2005
    [2001–2005] → test 2006
    ...
    [2018–2022] → test 2023

Lý do: Turnover 8.84%/năm → universe thay đổi đáng kể sau 5 năm
       Regime shifts cần detect bằng rolling window, không phải expanding
```

### E. Hạn chế cần ghi nhận (TRUNG THỰC)

1. **Tất cả single-feature IC đều < 0.02**: Đây là thực tế của large-cap US equity. ML model cần kết hợp nhiều features và capture nonlinearity để vượt IC đơn lẻ.

2. **IC không ổn định theo thời gian** (ICIR < 0.2 cho hầu hết features): Walk-Forward CV cần thiết, không nên dùng static train/test.

3. **Không có alternative data**: Chỉ có price/volume — bỏ lỡ earnings revision, analyst sentiment, short interest... là các features quan trọng trong industry.

4. **Feature store 1.1 GB**: Cần memory management khi train trên Kaggle (30GB RAM limit).

5. **Regime dependency**: `Reversal_5D` và nhiều features khác hoạt động rất khác giữa bull/bear markets. Model cần regime-conditional approach hoặc ít nhất là regime feature.

---

## 📁 TÀI LIỆU LIÊN QUAN

| File | Nội dung |
|:---|:---|
| [`phase1_data_validation_report.md`](phase1_data_validation_report.md) | 9 bài test Phase 1 |
| [`test_results_report.md`](test_results_report.md) | 16 bài test chi tiết (T1–T9, S1–S7) |
| [`sanity_check_report.md`](sanity_check_report.md) | S1–S7 in_sample checks |
| [`eda_01_return_distribution_report.md`](eda_01_return_distribution_report.md) | EDA T1 |
| [`eda_02_nan_universe_report.md`](eda_02_nan_universe_report.md) | EDA T2 |
| [`t4_feature_store_report.md`](t4_feature_store_report.md) | Feature Store build |
| [`t5_alpha_benchmark_report.md`](t5_alpha_benchmark_report.md) | Alpha Benchmark IC |
| [`eda_figures/`](eda_figures/) | Biểu đồ + CSV outputs |

---

*Báo cáo tổng hợp Phase 2 — EDA & Feature Engineering | Predict Daily Return Rankings | 03/10/2026*
