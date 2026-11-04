# 📊 BÁO CÁO EDA TASK 1: PHÂN PHỐI DAILY RETURN & CROSS-SECTIONAL DISPERSION

> **Dự án**: Predict Daily Return Rankings — Russell 1000 PIT (2000–2026)  
> **Giai đoạn**: Phase 2 — EDA Task 1  
> **Script**: [`scripts/05_eda/eda_01_return_distribution.py`](../../scripts/05_eda/eda_01_return_distribution.py)  
> **Ngày thực hiện**: 03/10/2026  
> **Dữ liệu**: `data/processed/in_sample/returns.parquet` — 6,021 ngày × 2,852 tickers (2000–2023)  
> **Biểu đồ**: [`docs/Data report/eda_figures/eda_01_return_distribution.png`](eda_figures/eda_01_return_distribution.png)

---

## 🎯 Mục đích

Phân tích đặc tính thống kê thực tế của daily return trên toàn bộ in-sample data (5,920,516 quan sát). Mục đích chính:
1. Xác định phân phối của return (có chuẩn không? fat tails như thế nào?)
2. Đánh giá Cross-Sectional Dispersion theo thời gian — nền tảng để hiểu "cơ hội" của mô hình ranking
3. Phát hiện các outlier/vấn đề cần xử lý trước khi tính features
4. Xác định các Market Regime (High/Low dispersion) — cần thiết cho Walk-Forward CV

---

## 📐 I. THỐNG KÊ MÔ TẢ

**Tổng số quan sát (non-NaN stock-day pairs): 5,920,516**

| Chỉ số | Giá trị | Ghi chú |
|:---|:---:|:---|
| Mean daily return | **+0.0484%** | Dương nhỏ — expected cho thị trường cổ phần dài hạn |
| Median daily return | **+0.0327%** | Thấp hơn mean → bị kéo bởi outlier dương |
| Std (daily) | **2.83%** | |
| Annualized Std (×√252) | **44.98%** | Cao hơn chuẩn 15–20% vì tính cross-section bao gồm mid/small-cap biến động lớn |
| Skewness | **+41.08** | Lệch phải mạnh |
| Excess Kurtosis | **16,433** | Cực kỳ fat tails |
| Min return | **-96.66%** | Delisting / phá sản |
| Max return | **+1,364.52%** | M&A premium / short squeeze cực đoan |
| Percentile 1% | -7.30% | |
| Percentile 99% | +7.69% | |

### Nhận xét trung thực

> ⚠️ **Skewness = +41.08 (lệch PHẢI, không phải âm)**: Khác với kỳ vọng ban đầu. Nguyên nhân: có các outlier tăng cực mạnh (+630% đến +1,364%) do M&A với giá premium cao, short squeeze, hoặc reverse stock split — các sự kiện này kéo toàn bộ distribution lệch phải rất mạnh.

> ⚠️ **Excess Kurtosis = 16,433**: Không phải "fat tails thông thường" của thị trường cổ phần (~10–50), mà là kurtosis cực đoan do outlier chưa được lọc. Sau khi winsorize, kurtosis sẽ giảm đáng kể.

> ✅ **Median = +0.033%/ngày** (~8.4%/năm) hợp lý cho Russell 1000 historical performance.

---

## 📊 II. KIỂM ĐỊNH CHUẨN (NORMALITY TESTS)

| Test | Statistic | p-value | Kết quả |
|:---|:---:|:---:|:---:|
| Jarque-Bera (n=100,000) | 6,294,733.82 | 0.00e+00 | ❌ REJECT H0 |
| Shapiro-Wilk (n=5,000) | — | 5.05e-66 | ❌ REJECT H0 |

**Kết luận**: Daily stock return **KHÔNG tuân theo phân phối chuẩn** (Normal) với mọi mức ý nghĩa thống kê. Cả Jarque-Bera lẫn Shapiro-Wilk đều bác bỏ H0 với p ≈ 0.

**Ý nghĩa cho Feature Engineering & ML**:
- Không dùng các mô hình giả định normality (Linear Regression thuần, OLS, ...)
- Nên dùng **Rank-based features** (percentile rank cross-sectional) thay vì raw value để tránh outlier ảnh hưởng
- **Winsorize** return trước khi tính feature momentum/reversal là bắt buộc

---

## 🦁 III. PHÂN TÍCH FAT TAILS

| Ngưỡng \|return\| | Số quan sát vi phạm | Tỷ lệ |
|:---|:---:|:---:|
| > 5% | 304,250 | 5.139% |
| > 10% | 56,220 | 0.950% |
| > 20% | 6,801 | 0.115% |
| > 30% | 1,713 | 0.029% |
| > 50% | 306 | 0.005% |

**Top 5 returns dương (cực đoan)**: +1,364.52% | +1,106.79% | +984.80% | +640.62% | +630.00%  
**Top 5 returns âm (cực đoan)**: -96.66% | -96.52% | -94.97% | -93.13% | -92.67%

### Nhận xét
- Các return > +500%: khả năng cao là **M&A takeover premium** (cổ phiếu được mua lại với giá gấp nhiều lần) hoặc **reverse stock split** được ghi nhận sai. Cần điều tra nếu cần, nhưng với mục đích ranking model, chúng sẽ bị triệt tiêu qua winsorize/rank.
- Return âm ~97%: cổ phiếu gần như về 0 (delisting, phá sản giai đoạn cuối).
- **5.139% quan sát có |return| > 5%/ngày** — con số lớn phản ánh đặc thù của cross-section Russell 1000 (bao gồm small-cap).

---

## 📈 IV. CROSS-SECTIONAL DISPERSION

**CS Dispersion** = Cross-sectional std của return tại mỗi ngày giao dịch (mức độ phân tán giữa các cổ phiếu).

| Chỉ số | Giá trị |
|:---|:---:|
| Mean CS Std | **2.11%/ngày** |
| Median CS Std | **1.79%/ngày** |
| Max CS Std | **43.79%** (2010-04-28) |
| Min CS Std | **0.66%** (2006-12-28) |

> ⚠️ **Max CS Std = 43.79% (2010-04-28)** bất thường — cao hơn cả ngày COVID (2020-03-23 = 20.97%). Nguyên nhân khả năng: có 1–2 cổ phiếu outlier cực đoan ngày đó kéo CS Std lên (ví dụ: M&A announcement hay short squeeze). Sau khi winsorize feature, các ngày "outlier dispersion" này sẽ ổn định.

### Phân loại Market Regime theo CS Dispersion

| Năm | CS Std TB | Regime |
|:---:|:---:|:---:|
| 2000 | 4.42% | ⚡ HIGH |
| 2001 | 3.33% | ⚡ HIGH |
| 2002 | 2.73% | ⚡ HIGH |
| 2003 | 1.87% | NORMAL |
| 2004 | 1.68% | NORMAL |
| 2005 | 1.67% | 😴 LOW |
| 2006 | 1.62% | 😴 LOW |
| 2007 | 1.76% | NORMAL |
| 2008 | 3.30% | ⚡ HIGH |
| 2009 | 2.70% | ⚡ HIGH |
| 2010 | 1.82% | NORMAL |
| 2011 | 1.80% | NORMAL |
| 2012 | 1.68% | NORMAL |
| 2013 | 1.47% | 😴 LOW |
| 2014 | 1.54% | 😴 LOW |
| 2015 | 1.71% | NORMAL |
| 2016 | 1.95% | NORMAL |
| 2017 | 1.54% | 😴 LOW |
| 2018 | 1.66% | 😴 LOW |
| 2019 | 1.68% | NORMAL |
| 2020 | 2.64% | ⚡ HIGH |
| 2021 | 2.03% | NORMAL |
| 2022 | 2.25% | NORMAL |
| 2023 | 1.94% | NORMAL |

### Phân tích Regime
- **⚡ HIGH DISPERSION** (2000–2002, 2008–2009, 2020): Khủng hoảng lớn. Model ranking có nhiều "cơ hội" hơn vì khoảng cách giữa cổ phiếu tốt/xấu rộng.
- **😴 LOW DISPERSION** (2005–2006, 2013–2014, 2017–2018): Thị trường bull ổn định, tất cả cổ phiếu đi cùng chiều. Model sẽ khó phân biệt, IC sẽ thấp hơn.
- **Ý nghĩa cho Walk-Forward CV**: Cần đảm bảo tập validation bao gồm cả HIGH và LOW dispersion periods — không được train toàn bộ trên HIGH rồi test trên LOW (sẽ overestimate performance).

---

## ⚙️ V. KẾT LUẬN & HÀNH ĐỘNG CHO FEATURE ENGINEERING

### Phát hiện chính
1. **Return không chuẩn** (p ≈ 0 với JB test) với kurtosis cực cao → Dùng rank-based ML
2. **Skewness dương mạnh** do outlier M&A/takeover → Cần winsorize
3. **5% quan sát có |return| > 5%** → Winsorize tại P1%/P99% hoặc P0.5%/P99.5%
4. **CS Dispersion regime** rõ ràng → Dùng để thiết kế Walk-Forward splits

### Quy tắc xử lý cho Feature Store (Task T4)
| Quy tắc | Giá trị |
|:---|:---|
| Winsorize return | Clip tại **P1% = -7.3%** và **P99% = +7.7%** (hoặc P0.5%/P99.5%) |
| Rank-transform | Dùng `cs_rank()` (percentile 0→1) cho tất cả raw features |
| Ngưỡng NaN lookback | Ticker phải có ≥ 252 ngày non-NaN trong cửa sổ lookback |
| Volume = 0 | Gán NaN cho Amihud/VWAP khi volume = 0 |

### Hạn chế cần ghi nhận
- CS Dispersion bị kéo cao bởi outlier chưa winsorize → con số raw không phản ánh đúng "thị trường bình thường"
- Skewness +41 và Kurtosis 16,433 là **thống kê raw chưa lọc** — sau winsorize sẽ hợp lý hơn nhiều

---

*Script: `scripts/05_eda/eda_01_return_distribution.py` | Output: `docs/Data report/eda_figures/` | 03/10/2026*
