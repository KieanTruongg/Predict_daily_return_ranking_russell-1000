# 📊 BÁO CÁO T4: BUILD FEATURE STORE

> **Script**: [`scripts/06_features/build_feature_store.py`](../../scripts/06_features/build_feature_store.py)  
> **Module**: [`src/features/feature_engineer.py`](../../src/features/feature_engineer.py) (v4 — rewritten)  
> **Ngày thực hiện**: 03/10/2026  
> **Input**: `data/processed/in_sample/` (close, high, low, volume, forward_returns)  
> **Output**: `data/processed/features/` — 31 wide parquets + 1 long-format (1,103 MB)

---

## 🎯 Mục đích

Xây dựng Feature Store từ in-sample data (2000–2023) để cung cấp input cho ML model training. Đây là bước chuyển từ raw price/volume data sang feature matrix có thể đưa thẳng vào LightGBM/XGBoost/LambdaMART.

**Những vấn đề cần giải quyết (từ Sanity Checks + EDA):**
1. `feature_engineer.py` v3 dùng schema sai (`Close`, `Adj Close` viết hoa) → fix sang lowercase
2. Chưa có winsorize → outlier return ±1000% ảnh hưởng feature momentum
3. 589 tickers out-sample-only đang chiếm cột trong matrix → lọc ra
4. `volume = 0` → chia cho 0 trong Amihud/VWAP → gán NaN
5. Ticker-by-ticker loop → chậm, không scalable

---

## 🔧 I. THAY ĐỔI `feature_engineer.py` (v3 → v4)

| Vấn đề cũ (v3) | Giải pháp mới (v4) |
|:---|:---|
| Schema: `df["Close"]`, `df["Adj Close"]` | Fix: `df["close"]`, bỏ `adj_close` (≡ close) |
| Ticker-by-ticker loop (chậm) | **Vectorized matrix operations** — 77s cho toàn bộ |
| Không winsorize | Winsorize P1%/P99% cross-sectional mỗi ngày |
| Không lọc ticker validity | Validity mask: ticker cần ≥ 252 ngày non-NaN |
| Không handle volume = 0 | `vol_clean = volume.replace(0, np.nan)` |
| Không có Amihud | Thêm `amihud_20d = mean(|ret|/dollar_vol, 20d)` |
| Không có CS rank features | Thêm `ret_1d_rank`, `ret_5d_rank`, `rsi_14_rank`... |

---

## 📐 II. FEATURES ĐƯỢC TÍNH

### Momentum / Reversal (7 features)
| Feature | Window | Mô tả |
|:---|:---:|:---|
| `ret_1d` | 1 ngày | Short-term reversal signal (Jegadeesh 1990) |
| `ret_2d` | 2 ngày | 2-day momentum |
| `ret_5d` | 5 ngày | Weekly momentum |
| `ret_10d` | 10 ngày | 2-week momentum |
| `ret_20d` | 20 ngày | 1-month momentum |
| `ret_60d` | 60 ngày | 3-month momentum |
| `ret_252d` | 252 ngày | 12-month momentum (Jegadeesh & Titman 1993) |

> ⚠️ Tất cả đều dùng **winsorized daily returns** (P1%/P99%) → compound product → tránh outlier kéo momentum signal

### Moving Averages & Price Ratios (4 features)
| Feature | Mô tả |
|:---|:---|
| `close_to_sma_20` | (Close/SMA20) - 1 |
| `close_to_sma_50` | (Close/SMA50) - 1 |
| `close_to_sma_200` | (Close/SMA200) - 1 |
| `macd_hist_norm` | (MACD - Signal) / Close |

### Technical Indicators (5 features)
| Feature | Mô tả |
|:---|:---|
| `rsi_14` | RSI 14 ngày |
| `bb_pct_b` | Bollinger %B = (Close - BB_lower) / (BB_upper - BB_lower) |
| `bb_bandwidth` | (BB_upper - BB_lower) / BB_mid |
| `hl_spread` | (High - Low) / Close — intraday range |
| `close_to_high` | (High - Close) / (High - Low) |

### Volume Features (4 features)
| Feature | Mô tả |
|:---|:---|
| `vol_ratio_5_20` | Vol_MA5 / Vol_MA20 — recent activity vs baseline |
| `vol_zscore_20` | (Volume - MA20) / Std20 |
| `close_to_vwap_5` | Close / VWAP_5d - 1 |
| `amihud_20d` | mean(\|ret\| / dollar_vol, 20d) × 1e6 — illiquidity |

### Volatility (3 features)
| Feature | Mô tả |
|:---|:---|
| `realized_vol_5d` | Annualized realized vol 5 ngày |
| `realized_vol_20d` | Annualized realized vol 20 ngày |
| `realized_vol_60d` | Annualized realized vol 60 ngày |

### Cross-Sectional Rank (6 features)
| Feature | Base feature | Mô tả |
|:---|:---|:---|
| `ret_1d_rank` | ret_1d | Percentile rank per day [0,1] |
| `ret_5d_rank` | ret_5d | Percentile rank per day |
| `ret_20d_rank` | ret_20d | Percentile rank per day |
| `rsi_14_rank` | rsi_14 | Percentile rank per day |
| `realized_vol_20d_rank` | realized_vol_20d | Percentile rank per day |
| `amihud_20d_rank` | amihud_20d | Percentile rank per day |

### Target Variables (2)
| Feature | Mô tả |
|:---|:---|
| `target_forward_return` | Raw forward return ngày T+1 |
| `target_return_rank` | Cross-sectional percentile rank của forward return |

---

## 📊 III. KẾT QUẢ BUILD

### Pipeline
```
in_sample/ (6,021 × 2,852) → filter OOS (589) → (6,021 × 2,263) → features → (5,820,358 rows × 33 cols)
```

### Thống kê tổng thể

| Chỉ tiêu | Giá trị |
|:---|:---:|
| Tickers đầu vào | 2,852 |
| Tickers loại (OOS ≥95% NaN) | **589** |
| Tickers giữ lại | **2,263** |
| Trading days | 6,021 |
| Features computed | **31** |
| Build time (features) | **77.4 giây** (vectorized) |
| Long-format rows | **5,820,358** |
| Long-format NaN rate | **10.8%** |
| File size (long-format) | **1,103 MB** |

### Feature Statistics

| Feature | Non-NaN% | Mean | Std | P1% | P99% |
|:---|:---:|:---:|:---:|:---:|:---:|
| ret_1d | 37.8% | +0.04% | 2.25% | -6.26% | +6.43% |
| ret_5d | 37.8% | +0.21% | 4.91% | -13.50% | +13.78% |
| ret_20d | 37.8% | +0.81% | 9.46% | -26.17% | +26.42% |
| ret_252d | 37.8% | +10.54% | 35.17% | -66.00% | +119.84% |
| rsi_14 | 37.8% | 51.99 | 16.87 | 14.22 | 88.50 |
| realized_vol_20d | 37.8% | 30.16% | 19.49% | 8.59% | 110.79% |
| amihud_20d | 37.8% | 0.0017 | 0.170 | ~0 | 0.0057 |
| **target_return_rank** | **42.7%** | **0.5005** | **0.289** | **0.010** | **0.991** |

### Kiểm chứng chất lượng

| Kiểm tra | Kết quả | Nhận xét |
|:---|:---:|:---|
| Non-NaN ~37.8% | ✅ Hợp lý | ~1,000 active tickers/năm trên 2,263 total |
| Target_return_rank mean ≈ 0.5 | ✅ 0.5005 | Phân bổ đều, không bias |
| Winsorize effect | ✅ P99% ret_1d = 6.43% | Không còn +1364% outlier |
| Validity mask | ✅ | Tickers < 252 valid days → NaN |
| volume=0 → NaN | ✅ | amihud_20d phân bổ hợp lý |

---

## ⚠️ IV. HẠN CHẾ VÀ LƯU Ý

1. **Non-NaN chỉ 37.8%**: Do tính chất cross-section — trong bất kỳ ngày nào chỉ có ~1,000/2,263 tickers active. Đây là hành vi bình thường, không phải lỗi.

2. **Amihud 20d có std lớn (0.170 vs mean 0.0017)**: Một số cổ phiếu rất illiquid có Amihud cực cao. CS rank (`amihud_20d_rank`) sẽ robust hơn khi đưa vào model.

3. **`hl_spread` std = 12.04** (quá lớn): Một số ngày `Low = 0` hoặc `High = Low` gây chia cho 0 mặc dù đã mask. Khi dùng feature này cần thêm clip hoặc dùng rank version.

4. **Long-format 1,103 MB**: Quá lớn để load toàn bộ vào RAM khi train. Khi train model cần dùng **chunking by year** hoặc load từng năm một.

5. **`ret_1d_rank` Non-NaN khác với các feature khác**: Do `future_stack=True` behavior — không ảnh hưởng đến tính đúng.

---

## 📁 V. OUTPUT FILES

```
data/processed/features/
├── ret_1d.parquet              (49.6 MB)   ← Date×Ticker matrix
├── ret_2d.parquet              (50.2 MB)
├── ret_5d.parquet              (50.3 MB)
├── ...                         (×31 files total)
├── target_forward_return.parquet (55.7 MB)
├── target_return_rank.parquet    (54.3 MB)
└── feature_store_long.parquet  (1,103 MB)  ← ML-ready long format
```

---

*Script: `scripts/06_features/build_feature_store.py` | 03/10/2026*
