# 📊 BÁO CÁO T5: ALPHA BENCHMARK EVALUATION — REVERSAL 5D & FEATURE IC

> **Script**: [`scripts/07_alpha_eval/eval_benchmark_alpha.py`](../../../scripts/archive/07_alpha_eval/eval_benchmark_alpha.py)  
> **Ngày thực hiện**: 03/10/2026 | **Thời gian chạy**: 247.6 giây  
> **Dữ liệu**: `in_sample/` (2000–2023) — 6,021 ngày × 2,263 tickers  
> **Biểu đồ**: [`docs/Data report/eda_figures/t5_alpha_benchmark_ic.png`](figures/t5_alpha_benchmark_ic.png)

---

## 🎯 Mục đích

Đánh giá sức mạnh dự báo thực tế của:
1. **Alpha Benchmark Reversal 5D** (công thức thầy) — làm baseline cho ML model
2. **Toàn bộ 23 features** trong Feature Store — để chọn features có IC cao nhất cho model

**Metric chính**: **Rank IC (Spearman)** — Correlation giữa signal rank và forward return rank, tính cross-sectional mỗi ngày.

> **Ngưỡng tham khảo thực tế** (quant research):  
> Mean IC > 0.03 → Tốt | 0.01–0.03 → Yếu nhưng có | < 0.01 → Rất thấp  
> ICIR > 0.5 → Solid | > 1.0 → Exceptional

---

## 📐 I. REVERSAL 5D ALPHA — CÔNG THỨC THẦY

**Công thức:**
$$\alpha_i = \frac{P_{t-5} - P_{t-1}}{5}, \quad \text{sau đó } \alpha_i \leftarrow \alpha_i - \bar{\alpha}$$

Stocks giảm mạnh 5 ngày qua → dự báo tăng (reversal). Dollar-neutral (sum = 0).

### Kết quả thực tế

| Chỉ tiêu | Giá trị | Nhận xét |
|:---|:---:|:---|
| **Mean Rank IC** | **+0.00736** | Rất thấp (< 0.01) nhưng có chiều dương |
| IC Std | 0.13394 | Biến động lớn theo ngày |
| **ICIR** | **0.0550** | Rất thấp (ngưỡng tốt > 0.5) |
| **Positive IC %** | **51.5%** | Nhẹ hơn 50% — tốt hướng |
| t-statistic | +4.264 | |
| p-value | 0.000020 | ✅ Có ý nghĩa thống kê (p << 0.001) |
| N ngày đánh giá | 6,016 | |

### Phân tích trung thực

> ⚠️ **Mean IC = 0.00736 rất thấp** so với ngưỡng "tốt" (0.03). Đây là con số **thực tế và trung thực** — đơn lẻ Reversal 5D không đủ mạnh để xây dựng chiến lược độc lập.

> ✅ **Tuy nhiên, p-value = 0.00002 (***) cho thấy signal có ý nghĩa thống kê** — trên 6,016 ngày, tồn tại xu hướng dương nhỏ nhưng thật. Điều này phù hợp với nghiên cứu học thuật: Jegadeesh (1990) ghi nhận reversal IC ~0.01–0.04 trên US large-cap.

> ✅ **Positive IC % = 51.5%**: Trong hơn nửa số ngày, signal đúng chiều — consistent nhưng không mạnh.

---

## 📅 II. REVERSAL 5D — IC THEO TỪNG NĂM (REGIME ANALYSIS)

| Năm | Mean IC | IC Std | Positive % | Regime |
|:---:|:---:|:---:|:---:|:---:|
| 2000 | +0.01278 | 0.163 | 45.6% | 🟡 WEAK |
| **2001** | **+0.02823** | 0.159 | 57.5% | **🟢 STRONG** |
| 2002–2010 | +0.005–+0.013 | 0.10–0.16 | 49–56% | 🟡 WEAK |
| 2011–2016 | +0.002–+0.005 | 0.09–0.13 | 49–52% | ⚪ NEUTRAL |
| 2017 | **-0.00406** | 0.121 | 47.0% | ⚪ NEUTRAL |
| 2018 | **-0.00498** | 0.137 | 44.4% | ⚪ NEUTRAL |
| 2019–2023 | -0.000–+0.016 | 0.13–0.18 | 48–52% | ⚪ NEUTRAL |

### Nhận xét Regime

- **2001 là năm tốt nhất (IC = +0.028)**: Dot-com crash → thị trường biến động lớn, reversal rất mạnh.
- **2017–2018 có IC âm**: Bull market momentum — reversal không hoạt động trong trend ổn định.
- **2020 IC = +0.016**: COVID volatility tạm thời làm reversal mạnh lên.
- **Xu hướng suy giảm từ 2013 trở đi**: Thị trường hiệu quả hơn theo thời gian, HFT làm mòn signal.

> ⚠️ **Kết luận regime**: Reversal 5D hoạt động tốt nhất trong **High Dispersion / High Volatility regimes** (2001, 2008, 2020). Trong bull markets ổn định, signal gần như vô hiệu hoặc đảo chiều.

---

## 🏆 III. RANKING TẤT CẢ FEATURES THEO MEAN IC

| # | Feature | Mean IC | ICIR | Pos IC% | t-stat | Significance |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **close_to_high** | **+0.01887** | **+0.169** | **57.6%** | +12.862 | *** |
| 2 | ret_252d | +0.00994 | +0.048 | 53.4% | +3.632 | *** |
| 3 | **Reversal_5D** | **+0.00736** | **+0.055** | **51.5%** | +4.264 | *** |
| 4 | vol_zscore_20 | +0.00701 | +0.108 | 54.7% | +8.227 | *** |
| 5 | close_to_sma_200 | +0.00524 | +0.027 | 53.1% | +2.020 | * |
| 6 | vol_ratio_5_20 | +0.00330 | +0.052 | 51.7% | +3.931 | *** |
| 7 | amihud_20d | -0.00010 | -0.001 | 49.2% | -0.065 | — |
| 8 | ret_60d | -0.00100 | -0.006 | 51.0% | -0.422 | — |
| … | … | … | … | … | … | … |
| 22 | close_to_vwap_5 | -0.01364 | -0.086 | 47.5% | -6.525 | *** |
| 23 | **ret_1d** | **-0.01444** | **-0.093** | **45.6%** | -7.072 | *** |

### Phân tích các phát hiện quan trọng

#### 🥇 `close_to_high` — Feature mạnh nhất (IC = +0.019)

**Định nghĩa**: `(High - Close) / (High - Low)` = 0 nếu đóng cửa tại đỉnh, 1 nếu đóng cửa tại đáy.

**Giải thích**: Cổ phiếu **đóng cửa gần đáy ngày** (close_to_high cao → gần Low) có xu hướng **tăng ngày hôm sau**. Đây là hiệu ứng **intraday reversal / closing price effect** — áp lực bán cuối ngày thường bị đảo ngược vào ngày tiếp theo. Phù hợp với nghiên cứu Heston et al. (2010).

#### ✅ `ret_252d` — IC = +0.00994 (Momentum 12 tháng)

Phù hợp với Jegadeesh & Titman (1993): cross-sectional momentum 12 tháng có IC dương (+). Hiệu ứng momentum tồn tại ngay cả trên Russell 1000 large-cap.

#### ⚠️ `ret_1d` — IC = **-0.01444** (Mạnh NHẤT nhưng đảo chiều)

`ret_1d` có IC âm → cổ phiếu **tăng mạnh hôm nay thường giảm ngày mai** (và ngược lại). Đây là **mean-reversion rất ngắn hạn** (1-day reversal). Phải dùng **đảo dấu** của `ret_1d` làm signal. Lưu ý: `Reversal_5D` dùng PRICE LEVEL (không phải return) nên có chiều dương.

#### ⚠️ `amihud_20d` — IC ≈ 0 (p = 0.95, không có ý nghĩa)

Amihud illiquidity không có predictive power cho forward return trên Russell 1000. Hợp lý — Russell 1000 là large-cap, tất cả đều liquid, không có illiquidity premium đáng kể.

#### ❌ `realized_vol` tất cả các window — IC âm

Volatility cao → return tiếp theo thấp hơn. Consistent với **volatility drag** và **flight-to-quality** behavior. Không dùng raw volatility làm signal dương; có thể dùng đảo dấu hoặc kết hợp với momentum.

---

## 📊 IV. SO SÁNH VỚI KỲ VỌNG LÝ THUYẾT

| Feature | Mean IC thực tế | Kỳ vọng từ literature | Đánh giá |
|:---|:---:|:---|:---:|
| Reversal_5D | +0.00736 | 0.01–0.04 (Jegadeesh 1990) | ⚠️ Thấp hơn kỳ vọng |
| ret_252d (momentum) | +0.00994 | 0.01–0.05 (Jegadeesh & Titman 1993) | ✅ Hợp lý |
| ret_1d (đảo dấu) | +0.01444 | 0.01–0.02 (Lehmann 1990) | ✅ Đúng lý thuyết |
| close_to_high | +0.01887 | Ít tài liệu — ~ 0.01–0.02 | ✅ Tốt |
| amihud | ≈ 0 | 0.005–0.02 (Amihud 2002) | ❌ Không có trên R1000 |

---

## 🔧 V. KHUYẾN NGHỊ CHO ML MODEL

Dựa trên IC analysis, ưu tiên features sau cho ML model:

| Nhóm | Features | Lý do |
|:---|:---|:---|
| **Ưu tiên cao** | `close_to_high`, `vol_zscore_20`, `vol_ratio_5_20` | IC > 0.005, ICIR > 0.05, *** |
| **Ưu tiên trung bình** | `ret_252d` (momentum), `close_to_sma_200` | IC > 0.005, *** |
| **Dùng đảo dấu** | `-ret_1d`, `-ret_2d`, `-ret_5d`, `-close_to_vwap_5` | IC âm mạnh → reverse làm signal |
| **Có thể bỏ** | `amihud_20d`, `ret_60d` | p-value > 0.05 (không có ý nghĩa) |
| **Dùng kèm regime** | `Reversal_5D` | Tốt khi high-volatility, kém khi bull market |

> ⚠️ **Lưu ý quan trọng**: Tất cả IC đều rất thấp (< 0.02). Đây là bình thường với large-cap. Giá trị thực của ML model đến từ **kết hợp nhiều features yếu** (ensemble effect) và **tối ưu phi tuyến** — không phải từ IC cao của từng feature riêng lẻ.

---

## ⚠️ VI. HẠN CHẾ (TRUNG THỰC)

1. **IC thấp toàn bộ** (< 0.02): Đây là thực tế của large-cap US equity. Đừng kỳ vọng IC > 0.05 với single features.
2. **IC không ổn định theo năm**: ICIR thấp (0.05–0.17) → signal có năm hoạt động, có năm không. Walk-Forward CV cần thiết.
3. **`close_to_high` mạnh nhất có thể bị transaction cost**: Nếu mua cổ phiếu đóng cửa gần đáy → spread + slippage có thể ăn mòn alpha.
4. **Amihud = 0 trên Russell 1000**: Phù hợp với lý thuyết nhưng cần xem xét bỏ feature này.
5. **IC tính trên toàn 24 năm không regime-adjusted**: Một số features có thể tốt hơn trong specific regimes nhưng bị "trung bình hóa" qua 24 năm.

---

*Script: `scripts/07_alpha_eval/eval_benchmark_alpha.py` | Output: `docs/Data report/eda_figures/` | 03/10/2026*
