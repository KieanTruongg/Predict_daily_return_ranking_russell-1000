# Báo Cáo Đánh Giá Walk-Forward: Ridge Baseline v1 (alpha=1.0)

**Ngày thực hiện**: 2026-11-07  
**Phương pháp**: Expanding Window Walk-Forward (5 Folds: 2019–2023)  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Strictly Frozen)  

---

## 1. Cấu Hình Thực Nghiệm

- **Pipeline**: `StandardScaler(with_mean=True, with_std=True)` $\to$ `Ridge(alpha=1.0, fit_intercept=True)`.
- **Fit độc lập**: Từng fold được fit lại hoàn toàn cả scaler và model trên tập Train của fold đó (không dùng thông tin tương lai).
- **Tập biến $X$**: 13 features Close/Volume chuẩn hóa.
- **Nhãn học ($y$)**: `target_rank` $\in [0, 1]$.
- **Nhãn đánh giá**: `target_return` ($R_{T+1}$).
- **Benchmark so sánh**: `ret_20d` (momentum 20 ngày, giá trị cao hơn = điểm cao hơn) trên cùng ngày và cùng mã.

---

## 2. Kết Quả Đánh Giá Chi Tiết Theo Từng Năm (2019–2023)

| Năm Val | Số Ngày | Số Dòng Val | Mean IC (Ridge) | Tỷ lệ Dương (Ridge) | Annual IR (Ridge) | Mean IC (`ret_20d`) | Tỷ lệ Dương (`ret_20d`) | Annual IR (`ret_20d`) | Chênh lệch ($\Delta$ IC) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2019** | **251** | 235.052 | **+0.009422** | **54.98%** *(138/251)* | +0.8067 | -0.022645 | 45.42% *(114/251)* | -2.0136 | **+0.032067** |
| **2020** | **252** | 240.034 | **+0.020615** | **51.19%** *(129/252)* | +1.3092 | +0.004123 | 52.38% *(132/252)* | +0.2624 | **+0.016492** |
| **2021** | **251** | 239.721 | **+0.015803** | **52.99%** *(133/251)* | +1.1903 | -0.003385 | 55.38% *(139/251)* | -0.2430 | **+0.019188** |
| **2022** | **250** | 243.971 | **+0.033095** | **58.80%** *(147/250)* | +2.1877 | -0.000551 | 52.40% *(131/250)* | -0.0400 | **+0.033646** |
| **2023** | **249** | 243.481 | **+0.003494** | **52.61%** *(131/249)* | +0.2787 | +0.000242 | 51.00% *(127/249)* | +0.0215 | **+0.003252** |
| **TỔNG** | **1.253** | **1.202.259** | **+0.016497** | **54.11%** *(678/1.253)* | **+1.1993** | **-0.004447** | **51.32%** *(643/1.253)* | **-0.3347** | **+0.020944** |

---

## 3. Nhận Xét & Phân Tích Hiệu Năng

1. **Tính Ổn Định Tuyệt Đối Qua Các Chu Kỳ**:
   - Ridge Baseline duy trì **Mean Daily Rank IC dương trong 5/5 năm** (100% các năm kiểm định).
   - Ngược lại, tín hiệu đơn lẻ `ret_20d` bị âm trong 3/5 năm (2019, 2021, 2022) do hiệu ứng đảo chiều 1 tháng (1-month reversal).
2. **Năm Thể Hiện Xuất Sắc Nhất**:
   - **Năm 2022** (Giai đoạn thị trường gấu giảm mạnh do lạm phát và lãi suất tăng): Ridge đạt đỉnh cao với **Mean IC = +3.31%**, tỷ lệ ngày dương đạt **58.80%**, và Annualized IR đạt **+2.19**. Mô hình phát huy tối đa sức mạnh kiểm soát rủi ro đuôi giảm (`downside_deviation_20d`).
3. **Năm 2020 Biến Động Covid-19**:
   - Ridge duy trì hiệu suất cao với **Mean IC = +2.06%** và Annualized IR = **+1.31**, vượt trội so với benchmark.
4. **Chỉ Số Thống Kê Tổng Thể (1.253 Phiên)**:
   - **Mean IC**: **+0.016497** (+1.65%)
   - **Tỷ lệ ngày IC dương**: **54.11%**
   - **Annualized IC IR**: **+1.1993** (Vượt ngưỡng chuẩn chất lượng định lượng $> 1.0$)
   - **t-statistic**: **+2.6743** ($p = 0.0076 < 0.01$, ý nghĩa thống kê cao)

---

## 4. Danh Mục Tệp Sản Phẩm

- **Bảng Daily IC**:
  - [`outputs/reports/daily_ic_walk_forward_ridge_alpha1.0.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/daily_ic_walk_forward_ridge_alpha1.0.csv)
  - [`data/processed/daily_ic_walk_forward_ridge_alpha1.0.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/daily_ic_walk_forward_ridge_alpha1.0.parquet)
- **Bảng Dự Đoán Hợp Nhất 5 Fold (1.202.259 dòng)**:
  - [`data/processed/val_predictions_walk_forward_ridge_alpha1.0.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/val_predictions_walk_forward_ridge_alpha1.0.parquet)
- **5 Model Pipelines**:
  - `models/walk_forward/ridge_fold_1_alpha1.0.joblib` đến `ridge_fold_5_alpha1.0.joblib`
- **Cấu hình tái lập**:
  - [`configs/walk_forward_ridge_alpha1.0_run.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_ridge_alpha1.0_run.yaml)
- **Pipeline Script**:
  - [`scripts/01_pipeline/21_train_and_evaluate_walk_forward.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/21_train_and_evaluate_walk_forward.py)
- **Kiểm thử tự động**:
  - [`tests/test_walk_forward_evaluation.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/tests/test_walk_forward_evaluation.py) (**3/3 tests PASSED**).
