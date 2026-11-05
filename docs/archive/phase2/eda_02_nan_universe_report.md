# 📊 BÁO CÁO EDA TASK 2: NaN PATTERN & UNIVERSE DYNAMICS

> **Script**: [`scripts/05_eda/eda_02_nan_universe_dynamics.py`](../../../scripts/archive/05_eda/eda_02_nan_universe_dynamics.py)  
> **Ngày thực hiện**: 03/10/2026  
> **Dữ liệu**: `in_sample/close.parquet` (6,021 × 2,852) + `raw/universe/by_year/*.json` (27 năm)  
> **Biểu đồ**: [`docs/Data report/eda_figures/eda_02_nan_universe_dynamics.png`](figures/eda_02_nan_universe_dynamics.png)

---

## 🎯 Mục đích

1. Hiểu **NaN phân bổ thế nào** trong ma trận Date × Ticker — cổ phiếu nào đủ dữ liệu, cổ phiếu nào không?
2. Phân tích **Universe Dynamics** — Russell 1000 thay đổi thành phần như thế nào mỗi năm?
3. Phân tích **Ticker Lifespan** — cổ phiếu tồn tại bao nhiêu năm trong chỉ số?
4. **Quyết định ngưỡng lọc** cụ thể cho Feature Store (Task T4)

---

## 📋 I. NaN PROFILE CHI TIẾT THEO TỪNG TICKER

**Tổng tickers trong in_sample matrix: 2,852**

| Nhóm | Số tickers | Tỷ lệ | Đặc điểm |
|:---|:---:|:---:|:---|
| **Full** (0% NaN — có data toàn bộ 24 năm) | **240** | 8.4% | Blue-chip ổn định liên tục: MSFT, XOM, JNJ, KO… |
| **Partial** (0–95% NaN — IPO/delisting giữa chừng) | **2,023** | 70.9% | Vào/ra Russell 1000 trong giai đoạn 2000–2023 |
| **Out-sample only** (≥95% NaN — chỉ xuất hiện 2024+) | **589** | 20.7% | Mới gia nhập 2024–2026, không có data in-sample |

### Phân bố số ngày valid per ticker

| Khoảng | Số tickers | Tỷ lệ | Ghi chú |
|:---|:---:|:---:|:---|
| < 50 ngày | 155 | 5.4% | Chủ yếu là out-sample-only tickers |
| 50–251 ngày (< 1 năm) | 144 | 5.0% | IPO giữa năm cuối / delisting đầu năm đầu |
| 252–1,259 ngày (1–5 năm) | 1,060 | 37.2% | Nhóm lớn nhất — active ngắn hạn |
| 1,260–3,023 ngày (5–12 năm) | 751 | 26.3% | Active trung hạn |
| ≥ 3,024 ngày (12–24 năm) | **502** | 17.6% | Core holdings — có data dài hạn đầy đủ |

### Ngưỡng lọc cho Feature Store

| Tiêu chí | Giá trị | Kết quả |
|:---|:---:|:---:|
| Tickers có ≥ 252 ngày valid | ≥ 1 năm data | **2,553 tickers (89.5%)** → được đưa vào Feature Store |
| Tickers bị loại | < 252 ngày | **299 tickers (10.5%)** → quá ít data để tính feature |

> ✅ **Quyết định ngưỡng lọc**: Một ticker phải có **≥ 252 ngày non-NaN** trong cửa sổ lookback **tại mỗi ngày tính feature**. Đây là điều kiện tối thiểu để tính momentum 12 tháng và các indicator kỹ thuật có cửa sổ dài.

---

## 📈 II. UNIVERSE DYNAMICS — THÀNH PHẦN CHỈ SỐ THEO NĂM

**Trung bình (2001–2026): Entry = 88 tickers/năm | Exit = 88 tickers/năm | Turnover = 8.8%/năm**

| Năm | N tickers | Entry | Exit | Turnover | Nhận xét |
|:---:|:---:|:---:|:---:|:---:|:---|
| 2001 | 989 | 205 | 212 | **20.9%** ⚡ | Cao nhất — Dot-com bust, nhiều tech delisting |
| 2002 | 988 | 177 | 178 | **17.9%** ⚡ | Tiếp tục hậu Dot-com |
| 2003 | 988 | 117 | 117 | 11.8% | Phục hồi |
| 2009 | 967 | 61 | 96 | 7.8% | GFC aftermath — exit nhiều hơn entry |
| 2013 | 1,000 | 65 | 52 | 5.9% | Bull market ổn định, thấp nhất |
| 2024 | 1,010 | 49 | 50 | 4.9% | Thấp nhất toàn giai đoạn |
| 2026 | 1,011 | 87 | 90 | 8.7% | Bình thường |

### Nhận xét

- **2001–2002 có turnover cao bất thường (18–21%)**: Dot-com crash khiến nhiều tech companies phá sản/bị mua lại, đồng thời nhiều công ty truyền thống được thêm vào.
- **2009 có Exit > Entry (96 vs 61)**: Hậu GFC, nhiều công ty tài chính/real estate bị loại ra, Russell tái cơ cấu mạnh.
- **Từ 2010 trở đi turnover ổn định 5–10%/năm**: Phù hợp với lịch sử chỉ số (FTSE Russell tái cơ cấu 1 lần/năm vào tháng 6).
- **Ý nghĩa cho ML**: Cần thiết kế Walk-Forward CV với **annual rebalancing** — không dùng static train/test split.

---

## ⏱️ III. TICKER LIFESPAN — PHÂN BỐ THỜI GIAN TỒN TẠI

**Tổng unique tickers trong Russell 1000 (2000–2026): 2,884**

| Nhóm lifespan | Số tickers | Tỷ lệ |
|:---|:---:|:---:|
| 1 năm (one-hit) | 486 | **16.9%** |
| 2–3 năm | 499 | 17.3% |
| 4–5 năm | 327 | 11.3% |
| 6–10 năm | 593 | 20.6% |
| 11–20 năm | 542 | 18.8% |
| **21–27 năm (Blue Chip)** | **437** | **15.2%** |

**Top 15 tickers tồn tại lâu nhất (27 năm liên tục, 2000–2026):**

`MSFT` | `XOM` | `SO` | `BDX` | `KR` | `FDX` | `NEM` | `PPL` | `EL` | `MCK` | `RSG` | `EIX` | `UHS` | `AVY` | `JBL`

### Nhận xét

- **16.9% tickers chỉ xuất hiện 1 năm** — phần lớn là công ty nhỏ tạm thời vào Russell 1000 rồi rơi xuống Russell 2000 sau reconstitution tiếp theo.
- **15.2% tickers là blue-chip 21–27 năm** — đây là backbone của chỉ số, đóng góp phần lớn liquidity và stability.
- **Phân bố bimodal** (nhiều ở 1 năm + nhiều ở 6–10 năm) cho thấy Russell 1000 có 2 nhóm rõ ràng: công ty nhỏ volatile và công ty lớn ổn định.

---

## 🏆 IV. TỔNG KẾT & QUYẾT ĐỊNH CHO FEATURE STORE

| Quyết định | Giá trị | Lý do |
|:---|:---|:---|
| **Ngưỡng lọc ticker** | ≥ 252 ngày valid trong lookback | Đảm bảo đủ data tính momentum 12 tháng |
| **Loại out-sample tickers** | 589 tickers (≥95% NaN) | Không có data in-sample, vô nghĩa với feature |
| **Số tickers đưa vào Feature Store** | ~2,553 (dynamic theo ngày) | Khác nhau theo ngày giao dịch |
| **Walk-Forward split** | Annual rebalancing | Phù hợp với index turnover 8.8%/năm |

> ⚠️ **Hạn chế**: Ngưỡng 252 ngày là heuristic — một số tickers có 252–500 ngày data nhưng vẫn có lookback gaps (IPO giữa năm). Feature store cần handle NaN trong rolling windows bằng `min_periods` parameter.

---

*Script: `scripts/05_eda/eda_02_nan_universe_dynamics.py` | Output: `docs/Data report/eda_figures/` | 03/10/2026*
