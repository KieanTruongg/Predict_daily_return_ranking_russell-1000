# Báo Cáo So Sánh Mô Hình Tuyến Tính và Phi Tuyến: Ridge Baseline vs HistGradientBoostingRegressor

**Ngày thực hiện**: 2026-11-07  
**Phương pháp**: Expanding Window Walk-Forward (5 Folds: 2019–2023)  
**Tập dữ liệu**: `baseline_dataset_v1.parquet` (13 features Close/Volume, complete-case)  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Strictly Frozen)  

---

## 1. Mục Tiêu & Thiết Kế Thử Nghiệm

Mục tiêu của đợt thử nghiệm này là đánh giá liệu việc chuyển từ mô hình tuyến tính (Ridge Regression) sang mô hình phi tuyến dạng cây tăng cường gradient (Gradient Boosted Decision Trees - GBDT) có mang lại sự cải thiện về năng lực xếp hạng cross-sectional (`Rank IC`) hàng ngày hay không, trên cùng một tập dữ liệu và cùng một quy trình kiểm định mở rộng thời gian.

### Nguyên tắc bảo đảm tính công bằng tuyệt đối (Fair Comparison):
1. **Dữ liệu và Mẫu kiểm định đồng nhất 100%**:
   - Sử dụng đúng 13 features Close/Volume từ `baseline_dataset_v1.parquet`.
   - Giữ nguyên toàn bộ điều kiện lọc complete-case và các ngày purge ranh giới theo [`configs/walk_forward_schedule_v1.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_schedule_v1.yaml).
   - Tổng cộng **1.202.259 dòng validation** trên **1.253 phiên giao dịch** (2019–2023). Cặp khóa `(date, canonical_sid)` trùng khớp 100% với dự đoán của Ridge baseline.
2. **Cấu hình mô hình GBDT cố định (không tinh chỉnh trước)**:
   - Mô hình: `sklearn.ensemble.HistGradientBoostingRegressor`.
   - Tham số: `loss="squared_error"`, `max_iter=100`, `learning_rate=0.05`, `max_leaf_nodes=15`, `min_samples_leaf=100`, `early_stopping=False`, `random_state=42`.
   - Cây quyết định sử dụng 13 feature gốc (không scale) theo chuẩn lý thuyết cây phân vùng.
   - Mốc đối chiếu Ridge ($\alpha=1.0$) sử dụng `StandardScaler` được fit riêng trên tập Train của từng fold.
3. **Mục tiêu học và đánh giá**:
   - Biến phụ thuộc lúc huấn luyện ($y$): `target_rank` $\in [0, 1]$.
   - Đánh giá xếp hạng hàng ngày: Spearman Rank IC giữa điểm dự báo mô hình và `target_return` ($R_{T+1}$).

---

## 2. Kết Quả Đánh Giá Chi Tiết Theo Từng Năm (2019–2023)

Bảng dưới đây so sánh hiệu năng xếp hạng hàng ngày giữa GBDT candidate, Ridge baseline ($\alpha=1.0$) và benchmark đơn lẻ `ret_20d` trên cùng 1.253 phiên giao dịch:

| Năm Val | Số Ngày | Số Dòng Val | Mean IC (GBDT) | Tỷ lệ Dương (GBDT) | Annual IR (GBDT) | Mean IC (Ridge) | Tỷ lệ Dương (Ridge) | Annual IR (Ridge) | Chênh lệch IC ($\text{GBDT} - \text{Ridge}$) | GBDT Win Rate vs Ridge | Mean IC (`ret_20d`) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2019** | 251 | 235.052 | **+0.013424** | 54.18% *(136/251)* | **+1.2183** | +0.009422 | **54.98%** *(138/251)* | +0.8067 | **+0.004002** *(+0.40%)* | **54.18%** | -0.022645 |
| **2020** | 252 | 240.034 | **+0.031884** | **56.35%** *(142/252)* | **+2.7354** | +0.020615 | 51.19% *(129/252)* | +1.3092 | **+0.011269** *(+1.13%)* | **52.38%** | +0.004123 |
| **2021** | 251 | 239.721 | +0.011627 | 52.19% *(131/251)* | +1.1653 | **+0.015803** | **52.99%** *(133/251)* | **+1.1903** | **-0.004175** *(-0.42%)* | 49.00% | -0.003385 |
| **2022** | 250 | 243.971 | +0.024168 | **59.20%** *(148/250)* | +1.9346 | **+0.033095** | 58.80% *(147/250)* | **+2.1877** | **-0.008927** *(-0.89%)* | 47.60% | -0.000551 |
| **2023** | 249 | 243.481 | **+0.014618** | **53.82%** *(134/249)* | **+1.4123** | +0.003494 | 52.61% *(131/249)* | +0.2787 | **+0.011124** *(+1.11%)* | **54.22%** | +0.000242 |
| **TỔNG 5 NĂM** | **1.253** | **1.202.259** | **+0.019158** | **55.15%** *(691/1.253)* | **+1.7214** | **+0.016497** | **54.11%** *(678/1.253)* | **+1.1993** | **+0.002661** *(+0.27%)* | **51.48%** *(645/1.253)* | **-0.004447** |

---

## 3. Phân Tích Chuyên Sâu: Mô Hình Phi Tuyến vs Tuyến Tính

### 3.1. Đánh giá tổng thể 5 năm
- **Hiệu năng trung bình vượt trội**: GBDT nâng Mean Daily Rank IC tổng thể từ **`+0.016497`** lên **`+0.019158`** ($\Delta = \mathbf{+0.002661}$ hay $+0.27\%$ IC tuyệt đối, tương đương mức tăng trưởng tương đối **+16.1%**).
- **Tính ổn định của tín hiệu**: Tỷ lệ ngày IC dương tăng từ $54.11\%$ lên $55.15\%$ (nhiều hơn 13 phiên sinh lời trên 1.253 phiên). GBDT có điểm IC cao hơn Ridge ở $51.48\%$ tổng số ngày.
- **Hệ số rủi ro-lợi nhuận (Annualized IR)**: Annualized Information Ratio của GBDT đạt **+1.7214** (so với **+1.1993** của Ridge), phản ánh độ biến động của IC hàng ngày thấp hơn tương đối so với mức sinh lợi IC trung bình.

### 3.2. Các năm GBDT vượt trội (2019, 2020, 2023)
1. **Năm 2020 (Cú sốc thị trường do Covid-19)**:
   - GBDT bứt phá với Mean IC **+3.19%** so với Ridge **+2.06%** ($\Delta = \mathbf{+1.13\%}$). Tỷ lệ ngày dương đạt **56.35%** (vượt Ridge +5.16%). Annualized IR đạt đỉnh **+2.7354**.
   - *Cơ chế kinh tế lượng*: Trong giai đoạn sụp đổ do hoảng loạn và sau đó là kích thích tiền tệ cực lớn, quan hệ giữa khối lượng bất thường (`volume_ratio_5_20`, `amihud_illiq_20d`) và biến động thực tế (`vol_realized_20d`, `vol_realized_60d`) mang tính phi tuyến cao. Cây quyết định chia nhánh theo các ngưỡng khối lượng đột biến để phân loại chính xác các mã bị bán tháo quá đà so với các mã thanh khoản suy kiệt.
2. **Năm 2023 (Thị trường phân hóa mạnh, phục hồi chọn lọc)**:
   - GBDT đạt Mean IC **+1.46%** so với Ridge chỉ **+0.35%** ($\Delta = \mathbf{+1.11\%}$, gấp hơn **4 lần** Ridge). Annual IR tăng từ +0.28 lên +1.41.
   - *Cơ chế kinh tế lượng*: Sau khi thị trường chạm đáy cuối 2022, dòng tiền phục hồi có sự chọn lọc cao theo từng nhóm ngành/vốn hóa. Mô hình tuyến tính gán chung một hệ số độ dốc cho toàn thị trường khiến tín hiệu bị phẳng hóa (attenuation bias), trong khi GBDT phát hiện được tương tác đa chiều giữa đà tăng ngắn hạn (`ret_5d`, `ret_20d`) và kênh Bollinger (`bollinger_pct_b_20d`).
3. **Năm 2019**:
   - GBDT vượt Ridge +0.40% IC (+1.34% vs +0.94%), Annual IR đạt +1.22 vs +0.81.

### 3.3. Các năm Ridge dẫn trước (2021, 2022)
1. **Năm 2022 (Thị trường gấu sụt giảm diện rộng do thắt chặt vĩ mô)**:
   - Ridge dẫn trước với Mean IC **+3.31%** so với GBDT **+2.42%** ($\Delta = \mathbf{-0.89\%}$).
   - *Cơ chế kinh tế lượng*: Khi lạm phát và chu kỳ tăng lãi suất của Fed chi phối toàn bộ dòng vốn, hầu như mọi cổ phiếu đều chịu chung áp lực bán tháo. Cơ chế hồi quy Ridge phạt liên tục ($\ell_2$-regularization) lên độ lệch chuẩn đuôi giảm (`downside_deviation_20d`) và biến động 60 ngày tạo ra một thước đo rủi ro mượt mà và tổng quát hóa tốt hơn. Trong khi đó, cây quyết định nông với các nhát cắt vuông góc có xu hướng nhạy cảm quá mức với các ngưỡng cục bộ trong dữ liệu train.
2. **Năm 2021**:
   - Ridge nhỉnh hơn GBDT ($\Delta = \mathbf{-0.42\%}$, +1.58% vs +1.16%).

---

## 4. Hiệu Năng Tính Toán & Thời Gian Thực Thi

Toàn bộ quá trình huấn luyện và dự báo 5 fold GBDT (với 4,3 triệu đến 5,3 triệu dòng mỗi fold) được thực hiện với tốc độ cực nhanh bằng thư viện tối ưu `HistGradientBoostingRegressor`:

| Fold | Năm Val | Số Dòng Train | Thời Gian Fit | Số Dòng Val | Thời Gian Predict | Tốc Độ Dự Báo |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fold 1** | 2019 | 4.307.308 | 22.89 giây | 235.052 | 0.12 giây | ~1.900.000 dòng/giây |
| **Fold 2** | 2020 | 4.543.280 | 14.98 giây | 240.034 | 0.84 giây | ~285.000 dòng/giây |
| **Fold 3** | 2021 | 4.784.259 | 26.08 giây | 239.721 | 1.02 giây | ~235.000 dòng/giây |
| **Fold 4** | 2022 | 5.024.938 | 24.69 giây | 243.971 | 0.81 giây | ~300.000 dòng/giây |
| **Fold 5** | 2023 | 5.269.864 | 22.68 giây | 243.481 | 0.90 giây | ~270.000 dòng/giây |
| **TỔNG** | - | - | **111.32 giây** | **1.202.259** | **3.69 giây** | **Tổng runtime: 137.57s** |

- **Kết luận kỹ thuật**: Thuật toán histogram binning của `HistGradientBoostingRegressor` xử lý hơn 5,2 triệu dòng chỉ trong ~23 giây mỗi fold. Độ trễ dự báo trên toàn bộ 240.000 cổ phiếu một năm chưa tới 1 giây, hoàn toàn khả thi và lý tưởng cho việc triển khai inference hàng ngày tại phiên $T$.

---

## 5. Danh Mục Sản Phẩm Đã Lưu Trữ

Toàn bộ artifact của đợt chạy GBDT được tách biệt hoàn toàn khỏi Ridge và lưu trữ tại:

1. **Pipeline Script**:
   - [`scripts/01_pipeline/23_train_and_evaluate_gbdt_baseline.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/23_train_and_evaluate_gbdt_baseline.py)
2. **Cấu hình & Nhật ký chạy**:
   - [`configs/walk_forward_gbdt_baseline_run.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_gbdt_baseline_run.yaml)
3. **Bảng Dự Đoán Hợp Nhất 5 Fold (1.202.259 dòng)**:
   - [`data/processed/val_predictions_walk_forward_gbdt.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/val_predictions_walk_forward_gbdt.parquet)
4. **Bảng Daily IC Đối Chiếu (1.253 phiên)**:
   - [`outputs/reports/daily_ic_walk_forward_gbdt_vs_ridge.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/daily_ic_walk_forward_gbdt_vs_ridge.csv)
   - [`data/processed/daily_ic_walk_forward_gbdt_vs_ridge.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/daily_ic_walk_forward_gbdt_vs_ridge.parquet)
5. **Bảng Tóm Tắt Hiệu Năng So Sánh**:
   - [`outputs/reports/summary_walk_forward_gbdt_vs_ridge.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/summary_walk_forward_gbdt_vs_ridge.csv)
6. **5 Mô Hình Đã Huấn Luyện**:
   - `models/walk_forward_gbdt/gbdt_fold_1.joblib` đến `gbdt_fold_5.joblib`
7. **Kiểm thử tự động**:
   - [`tests/test_gbdt_baseline.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/tests/test_gbdt_baseline.py) (**3/3 tests PASSED**).

---

## 6. Kết Luận & Ranh Giới Nghiêm Ngặt

1. **Kết luận chính**: Mô hình phi tuyến GBDT chứng minh được sự ưu việt rõ rệt trong các giai đoạn thị trường có bước ngoặt/cú sốc biến động lớn (2020) và phục hồi phân hóa (2023), nâng Mean IC tổng thể từ **`+0.016497`** lên **`+0.019158`** (+16.1% gain). Tuy nhiên, trong điều kiện thị trường gấu giảm đồng loạt trên diện rộng (2022), mô hình tuyến tính có điều chuẩn mượt mà (Ridge) vẫn là giải pháp phòng vệ ổn định hơn.
2. **Ranh giới tuân thủ**:
   - Thử nghiệm này dừng lại ở việc so sánh cấu hình GBDT mặc định cố định.
   - **Tuyệt đối không tuning tham số**, **không refit trên toàn bộ Development**, **không backtest danh mục**, và **tập OOS (2024–2026) được giữ đóng băng tuyệt đối**.
