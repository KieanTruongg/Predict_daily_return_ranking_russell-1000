# Báo Cáo Đánh Giá Mô Hình Baseline v1: Ridge Regression (13 Features)

**Ngày thực hiện**: 2026-11-07  
**Phạm vi**: Development Window (Train 2000–2018 sau Causal Boundary Purge, Validation 2019–2023)  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Frozen)  

---

## 1. Cấu Hình Thực Nghiệm & Tái Lập (Experiment Configuration)

Mô hình baseline đầu tiên được thiết kế và huấn luyện theo đúng đặc tả kỹ thuật tại [`baseline_dataset_v1.md`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/docs/specifications/baseline_dataset_v1.md) và cấu hình phân chia thời gian tại [`baseline_split_v1.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/baseline_split_v1.yaml).

- **Kiến trúc mô hình**: `sklearn.pipeline.Pipeline` gồm:
  1. `StandardScaler(with_mean=True, with_std=True)`: Chuẩn hóa z-score từng feature trên toàn bộ dữ liệu Train.
  2. `Ridge(alpha=1.0, fit_intercept=True)`: Hồi quy tuyến tính có hiệu chỉnh phạt chuẩn $L_2$.
- **Tập biến độc lập $X$**: Đúng **13 features Close/Volume** (không dùng 3 features OHLC đang tạm hoãn):
  `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `mom_12m_skip_1m`, `vol_realized_20d`, `vol_realized_60d`, `downside_deviation_20d`, `amihud_illiq_20d`, `volume_ratio_5_20`, `log_dollar_volume_20d`, `rsi_14d`, `bollinger_pct_b_20d`.
- **Cặp khóa thực thể**: `date` (ngày quyết định $T$) và `canonical_sid` (mã cổ phiếu chuẩn hóa).
- **Nhãn mục tiêu huấn luyện ($y$)**: `target_rank` $\in [0.0, 1.0]$ (thứ hạng chéo ngang chuẩn hóa tại phiên $T$).
- **Nhãn mục tiêu đánh giá**: `target_return` (lợi suất đóng cửa phiên tiếp theo $R_{T+1} = Close_{T+1} / Close_T - 1$, đã qua mask).
- **Tín hiệu Benchmark so sánh**: `ret_20d` (momentum 20 ngày, giá trị cao hơn tương ứng với điểm cao hơn, so sánh trên cùng mã và cùng ngày).
- **Dữ liệu huấn luyện (Train)**:
  - Nguồn: [`data/processed/train_baseline_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/train_baseline_v1.parquet)
  - Số dòng: **4.307.308 dòng** (4.652 phiên, từ `2000-07-03` đến `2018-12-28`).
  - Đã loại bỏ hoàn toàn phiên `2018-12-31` (920 dòng) để triệt tiêu rò rỉ ranh giới sang Validation.
- **Dữ liệu kiểm định (Validation)**:
  - Nguồn: [`data/processed/val_baseline_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/val_baseline_v1.parquet)
  - Số dòng: **1.206.096 dòng** (1.257 phiên, từ `2019-01-02` đến `2023-12-28`).
  - Phiên cuối `2023-12-29` có 0 dòng (do nhãn chạm OOS).

---

## 2. Trọng Số Mô Hình Đã Học (Learned Ridge Coefficients)

- **Hệ số tự do (Intercept)**: $\beta_0 = +0.500103$ (trung khớp với kỳ vọng toán học $\mathbb{E}[target\_rank] = 0.5$).
- **Bảng trọng số chuẩn hóa các features (Ridge Coefficients)**:

| STT | Feature ($X_k$) | Trọng số ($\beta_k$) | Tác động định hướng | Ý nghĩa Kinh tế & Vi cấu trúc |
|:---:|---|:---:|:---:|---|
| 1 | `downside_deviation_20d` | **-0.003149** | Âm mạnh nhất | Cổ phiếu có rủi ro giảm giá lớn bị phạt điểm mạnh; phản ánh hiệu ứng biến động bất đối xứng. |
| 2 | `vol_realized_60d` | **-0.002949** | Âm mạnh | Cổ phiếu biến động cao trung hạn mang lợi suất kém (Low-Volatility Anomaly kinh điển). |
| 3 | `ret_5d` | **-0.002604** | Âm | Hiệu ứng đảo chiều ngắn hạn 1 tuần (Short-term reversal). |
| 4 | `bollinger_pct_b_20d` | **+0.002420** | Dương mạnh | Cổ phiếu giữ vị thế giá cao tương đối trong dải biến động được ưu tiên. |
| 5 | `ret_1d` | **-0.002299** | Âm | Đảo chiều vi cấu trúc sau phiên biến động mạnh. |
| 6 | `vol_realized_20d` | **+0.002241** | Dương | Biến động ngắn hạn mang tính đột biến dòng tiền trong bối cảnh kiểm soát biến động dài hạn. |
| 7 | `ret_20d` | **-0.002204** | Âm | Đảo chiều ngắn hạn 1 tháng (1-month reversal). |
| 8 | `mom_12m_skip_1m` | **+0.002181** | Dương mạnh | Hiệu ứng Momentum trung hạn kinh điển Jegadeesh-Titman (12-1 momentum). |
| 9 | `rsi_14d` | **-0.001567** | Âm | Chỉ báo quá mua RSI kích hoạt áp lực chốt lời đảo chiều. |
| 10 | `log_dollar_volume_20d` | **-0.001381** | Âm nhẹ | Hiệu ứng quy mô thanh khoản: thanh khoản siêu lớn thường có quán tính sinh lời biên thấp hơn. |
| 11 | `volume_ratio_5_20` | **+0.000569** | Dương nhẹ | Dòng tiền ngắn hạn đột biến mang lại xung lực giá tích cực. |
| 12 | `amihud_illiq_20d` | **-0.000509** | Âm nhẹ | Kém thanh khoản cực đoan bị chiết khấu nhẹ. |
| 13 | `ret_60d` | **+0.000439** | Dương nhẹ | Quán tính lợi suất 1 quý có đóng góp dương nhẹ. |

---

## 3. Kết Quả Đánh Giá Hiệu Năng: Ridge Baseline vs. Benchmark `ret_20d`

Chỉ số đánh giá chính là **Spearman Rank Information Coefficient (Rank IC)** tính chéo ngang theo từng ngày giao dịch trên toàn bộ 1.257 phiên của tập Validation (2019–2023).

### Bảng so sánh tổng hợp

| Chỉ số Đánh giá | Ridge Baseline (13 features) | Benchmark Đơn lẻ (`ret_20d`) | Chênh lệch ($\Delta$) | Kết luận & Ý nghĩa |
| :--- | :---: | :---: | :---: | :--- |
| **Tổng số phiên giao dịch** | **1.257** | **1.257** | 0 | Đánh giá trên cùng giai đoạn 2019–2023 |
| **Số phiên tính được IC** | **1.257** | **1.257** | 0 | 100% phiên đủ điều kiện tính toán |
| **Số phiên không xác định (NaN)** | **0** | **0** | 0 | Zero phiên thiếu mã ($N \ge 2$) hay hằng số |
| **Mean Daily Spearman IC** | **+0.017352** | **-0.004452** | **+0.021804** | **Ridge dương vượt trội; ret_20d mang dấu âm do đảo chiều** |
| **Median Daily Spearman IC** | **+0.023150** | **+0.008345** | **+0.014805** | Phân phối lệch phải tích cực |
| **Độ lệch chuẩn IC ($\sigma_{IC}$)** | **0.215343** | **0.210674** | +0.004669 | Mức biến động IC hàng ngày tương đương |
| **Tỷ lệ ngày IC dương (> 0)** | **54.34%** *(683 / 1.257)* | **51.31%** *(645 / 1.257)* | **+3.03%** | Tỷ lệ phiên dự đoán đúng chiều cao hơn |
| **Daily IC IR** ($\mu_{IC} / \sigma_{IC}$) | **+0.0806** | **-0.0211** | **+0.1017** | Hiệu suất trên một đơn vị rủi ro dự báo |
| **Annualized IC IR** ($IR \times \sqrt{252}$) | **+1.2791** | **-0.3354** | **+1.6145** | **Đạt ngưỡng chất lượng của mô hình định lượng ($> 1.0$)** |
| **t-statistic** ($\mu / (\sigma / \sqrt{T})$) | **+2.8568** | **-0.7492** | **+3.6060** | **Ý nghĩa thống kê cao ($p = 0.0043 < 0.01$)** |

> [!NOTE]
> **Nhận xét chuyên sâu**:
> - Tín hiệu đơn lẻ `ret_20d` khi sử dụng trực tiếp có Mean IC âm ($-0.004452$). Điều này hoàn toàn phù hợp với lý thuyết tài chính định lượng về **hiệu ứng đảo chiều 1 tháng** (1-month short-term reversal) trên thị trường chứng khoán Mỹ.
> - Mô hình Ridge Baseline v1 kết hợp đa nhân tố (momentum trung hạn `mom_12m_skip_1m`, dải biến động `bollinger_pct_b_20d`, và kiểm soát rủi ro đuôi giảm qua `downside_deviation_20d`) đã đảo ngược hoàn toàn tín hiệu nhiễu, đạt **Mean IC = +0.017352** với **t-stat = 2.86**, chứng minh năng lực dự báo xếp hạng thực sự trên tập Validation độc lập.

---

## 4. Minh Chứng Chi Tiết Cách Tính Spearman Rank IC (Phiên Mẫu `2019-01-02`)

Để đảm bảo tính minh bạch và khả năng kiểm chứng độc lập, dưới đây là chi tiết tính toán trên phiên mở màn tập Validation (`2019-01-02`):

- **Số lượng cổ phiếu hợp lệ ($N$)**: **920 mã**.
- **Công thức tính toán**:
  $$\text{Spearman Rank IC} = \rho\Big(\text{rank}(\text{score}), \text{rank}(\text{target\_return})\Big) = \frac{\sum_{i=1}^N (r_{score, i} - \bar{r})(r_{y, i} - \bar{r})}{\sqrt{\sum_{i=1}^N (r_{score, i} - \bar{r})^2 \sum_{i=1}^N (r_{y, i} - \bar{r})^2}}$$
  *(áp dụng phương pháp gán hạng trung bình `method='average'` cho các giá trị đồng hạng)*.
- **Kết quả tính toán**:
  - **Ridge Rank IC**: **`+0.263805`** ($p\text{-value} = 4.11 \times 10^{-16}$).
  - **ret_20d Rank IC**: **`-0.026389`** ($p\text{-value} = 0.424$).
  - Đối chiếu giữa `scipy.stats.spearmanr` và hệ số tương quan Pearson trên thứ hạng: **Khớp chính xác tuyệt đối từng chữ số thập phân (`0.263805 == 0.263805`)**.

### Bảng mẫu 5 cổ phiếu điểm cao nhất và 5 cổ phiếu điểm thấp nhất theo Ridge tại phiên `2019-01-02`:

| Nhóm | Canonical SID | Điểm Ridge (`ridge_score`) | Lợi suất thực tế $T+1$ (`target_return`) | Thứ hạng thực tế (`target_rank`) | Tín hiệu Benchmark (`ret_20d`) |
|:---:|---|:---:|:---:|:---:|:---:|
| **Top 1** | `LOPE U7T3QGL72B8L` | **0.507584** | +0.2354% | 0.8026 | -23.62% |
| **Top 2** | `ATR R735QTJ8XC9X` | **0.507424** | -1.2087% | 0.5837 | -13.33% |
| **Top 3** | `IEI R735QTJ8XC9X` | **0.506109** | -0.0139% | 0.7629 | +0.15% |
| **Top 4** | `ERIE R735QTJ8XC9X` | **0.505755** | +1.8587% | 0.9667 | -4.86% |
| **Top 5** | `ARD WIVGEEITFLNP` | **0.505294** | -3.4873% | 0.1685 | -18.45% |
| ... | ... | ... | ... | ... | ... |
| **Bottom 5** | `NBR R735QTJ8XC9X` | **0.479522** | +6.8493% | 0.9979 | -32.20% |
| **Bottom 4** | `GE R735QTJ8XC9X` | **0.479274** | +0.1242% | 0.7822 | +7.33% |
| **Bottom 3** | `CHK R735QTJ8XC9X` | **0.478401** | -2.7397% | 0.2758 | -25.26% |
| **Bottom 2** | `EVI R735QTJ8XC9X` | **0.477815** | 0.0000% | 0.7650 | -31.58% |
| **Bottom 1** | `EQT R735QTJ8XC9X` | **0.475334** | -2.9146% | 0.2479 | +6.36% |

---

## 5. Danh Mục Tệp Sản Phẩm Lưu Trữ (Deliverables Inventory)

1. **Tệp Mô Hình Huấn Luyện**:
   - [`models/ridge_baseline_v1.joblib`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/models/ridge_baseline_v1.joblib) (Dung lượng: 1.37 KB).
2. **Cấu Hình Tái Lập (Run Configuration)**:
   - [`configs/ridge_baseline_run_v1.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/ridge_baseline_run_v1.yaml).
3. **Bảng Dự Đoán Tập Validation**:
   - [`data/processed/val_predictions_ridge_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/val_predictions_ridge_v1.parquet) (1.206.096 dòng $\times$ 6 cột, 32.48 MB).
4. **Bảng Đánh Giá IC Theo Ngày**:
   - [`outputs/reports/daily_ic_ridge_vs_ret20d_v1.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/daily_ic_ridge_vs_ret20d_v1.csv) (1.257 dòng).
   - [`data/processed/daily_ic_ridge_vs_ret20d_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/daily_ic_ridge_vs_ret20d_v1.parquet).
5. **Kịch Bản Pipeline Chính Thức**:
   - [`scripts/01_pipeline/19_train_and_evaluate_ridge_baseline.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/19_train_and_evaluate_ridge_baseline.py).
6. **Bộ Kiểm Thử Tự Động**:
   - [`tests/test_ridge_baseline.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/tests/test_ridge_baseline.py) (3/3 tests PASSED).
