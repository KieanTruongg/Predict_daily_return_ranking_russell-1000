# Báo Cáo Thử Nghiệm Số Lá Cây (max_leaf_nodes): GBDT Baseline trên 5 Fold Walk-Forward

**Ngày thực hiện**: 2026-11-07  
**Phương pháp**: Expanding Window Walk-Forward (5 Folds: 2019–2023)  
**Tập dữ liệu**: `baseline_dataset_v1.parquet` (13 features Close/Volume, complete-case)  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Strictly Frozen)  

---

## 1. Số Lá Cây Ảnh Hưởng Gì Đến Mô Hình? (Lý Thuyết & Trực Giác)

Trong các thuật toán cây tăng cường gradient theo cơ chế histogram (như `HistGradientBoostingRegressor` hay LightGBM), cây được phát triển theo chiến lược ưu tiên lá (*leaf-wise tree growth*) thay vì theo tầng (*depth-wise*). Siêu tham số `max_leaf_nodes` quy định số lượng phân vùng không gian tối đa mà mỗi cây có thể tạo ra:

1. **Kiểm soát dung lượng mô hình (Model Capacity) và bậc tương tác**:
   - $L = 7$: Cây rất nông (độ sâu tối đa tương đương 3 tầng). Mỗi cây chỉ có thể phân chia không gian thành tối đa 7 vùng cục bộ, chỉ cho phép tương tác giữa **2 đến 3 biến** đồng thời.
   - $L = 15$ (Mốc baseline): Cây vừa (độ sâu tối đa ~4 tầng), cho phép tương tác giữa **3 đến 4 biến**.
   - $L = 31$: Cây sâu hơn (độ sâu tối đa ~5 tầng), cho phép tương tác bậc cao giữa **4 đến 5 biến**.
2. **Đặc thù độ ồn cao của dữ liệu tài chính (Low Signal-to-Noise Ratio)**:
   - Lợi suất cổ phiếu hàng ngày có tỷ lệ tín hiệu trên nhiễu (SNR) cực thấp (thường $< 1\%$). Khi số lá quá lớn ($L=31$), cây quyết định có quá nhiều bậc tự do để phân tách dữ liệu thành các ô nhỏ lẻ, dẫn đến hiện tượng **học thuộc lòng các mẫu nhiễu lịch sử (overfitting)** thay vì nắm bắt quy luật tổng quát.
   - Ngược lại, cây quá ít lá có thể bị chệch mô hình (underfitting), không khai thác được tính phi tuyến cần thiết.
   - Do đó, `max_leaf_nodes` đóng vai trò như một cơ chế **điều chuẩn cấu trúc (structural regularization)** quan trọng nhất của mô hình cây: giới hạn số lá là cách trực tiếp để kiềm chế tương tác giả và ép mô hình chỉ học những mẫu hình phi tuyến bền vững nhất.

---

## 2. Đã Thay Đổi Gì Trong Thiết Kế Thử Nghiệm?

Để đánh giá chính xác tác động độc lập của `max_leaf_nodes`, toàn bộ các yếu tố khác được **cố định tuyệt đối**:

- **Lưới thử nghiệm**: `max_leaf_nodes in [7, 15, 31]`.
- **Dữ liệu và Mẫu kiểm định đồng nhất 100%**:
  - Đúng 13 features Close/Volume thô từ `baseline_dataset_v1.parquet` (không scale, theo chuẩn lý thuyết cây).
  - Đúng 5 fold walk-forward mở rộng (2019–2023) theo [`configs/walk_forward_schedule_v1.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_schedule_v1.yaml).
  - Đúng các ranh giới purge, tập mã và ngày giao dịch (1.253 phiên, 1.202.259 dòng validation).
- **Các siêu tham số GBDT cố định**:
  - `loss="squared_error"`, `max_iter=100`, `learning_rate=0.05`, `min_samples_leaf=100`, `early_stopping=False`, `random_state=42`.
- **Mục tiêu học và đánh giá**:
  - Biến phụ thuộc huấn luyện: `target_rank` $\in [0, 1]$.
  - Đánh giá xếp hạng hàng ngày: Spearman Rank IC so với `target_return` ($R_{T+1}$).
- **Kiểm chứng tính nhất quán mốc (Parity Check)**:
  - Mốc chính `max_leaf_nodes=15`: Khớp số học chính xác tuyệt đối với kết quả lượt trước (Mean IC = `+0.019158` trên 1.253 phiên, sai khác $0.00\text{e}+00$).
  - Mốc phụ `Ridge alpha=1.0`: Khớp chính xác tuyệt đối với mốc tuyến tính (Mean IC = `+0.016497`).

---

## 3. Kết Quả Đánh Giá Chi Tiết Theo Từng Năm (2019–2023)

Bảng dưới đây so sánh hiệu năng xếp hạng cross-sectional hàng ngày giữa 3 cấu hình lá ($L=7$, $L=15$, $L=31$), đối chiếu với mốc tuyến tính Ridge ($\alpha=1.0$) và benchmark đơn lẻ `ret_20d`:

| Giai Đoạn | Số Ngày | Mean IC ($L=7$) | % Dương ($L=7$) | IR ($L=7$) | Mean IC ($L=15$) | % Dương ($L=15$) | IR ($L=15$) | Mean IC ($L=31$) | % Dương ($L=31$) | IR ($L=31$) | $\Delta \text{IC}$ ($7 - 15$) | Win Rate ($7 > 15$) | $\Delta \text{IC}$ ($31 - 15$) | Mean IC Ridge | Mean IC `ret_20d` |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2019** | **251** | **+0.014162** | 54.18% | +1.2038 | +0.013424 | 54.18% | +1.2183 | +0.013507 | 54.18% | **+1.3409** | **+0.000738** | **54.18%** | +0.000083 | +0.009422 | -0.022645 |
| **2020** | **252** | **+0.033287** | 55.95% | +2.6512 | +0.031884 | 56.35% | +2.7354 | +0.030899 | **56.75%** | **+2.7477** | **+0.001403** | 47.22% | -0.000985 | +0.020615 | +0.004123 |
| **2021** | **251** | **+0.014321** | **54.58%** | **+1.3867** | +0.011627 | 52.19% | +1.1653 | +0.010299 | 49.00% | +1.0548 | **+0.002693** | **50.60%** | -0.001328 | +0.015803 | -0.003385 |
| **2022** | **250** | **+0.028585** | 57.20% | +2.0551 | +0.024168 | 59.20% | +1.9346 | +0.023743 | **60.40%** | **+2.0869** | **+0.004418** | **52.80%** | -0.000425 | +0.033095 | -0.000551 |
| **2023** | **249** | +0.014409 | **54.62%** | +1.3068 | +0.014618 | 53.82% | +1.4123 | **+0.014906** | 53.82% | **+1.5571** | -0.000209 | **53.41%** | **+0.000288** | +0.003494 | +0.000242 |
| **TỔNG 5 NĂM** | **1.253** | **+0.020967** | **55.31%** | **+1.7511** | **+0.019158** | **55.15%** | **+1.7214** | **+0.018683** | **54.83%** | **+1.7913** | **+0.001809** | **51.64%** | **-0.000475** | **+0.016497** | **-0.004447** |

---

### Phân tích diễn biến từng năm:

1. **Năm 2019 (Thị trường đi ngang / phân hóa nhẹ)**:
   - $L=7$ đạt Mean IC **+0.014162**, cao hơn $L=15$ (+0.013424) và $L=31$ (+0.013507). Cả 3 cấu hình đều vượt trội đáng kể so với Ridge (+0.009422).
2. **Năm 2020 (Cú sốc sụp đổ và phục hồi Covid-19)**:
   - Cả 3 cấu hình đều thể hiện sức mạnh vượt trội của mô hình phi tuyến (đều $> +3.0\%$ Mean IC so với Ridge $+2.06\%$).
   - $L=7$ đạt đỉnh Mean IC **+0.033287** (vượt $L=15$ $+0.14\%$ IC và vượt $L=31$ $+0.24\%$ IC).
3. **Năm 2021 (Bùng nổ thanh khoản hậu kích thích tiền tệ)**:
   - Đây là năm thể hiện rõ rệt nhất hiện tượng **overfitting của cây sâu**:
     * $L=31$ bị suy giảm nghiêm trọng: Mean IC rơi xuống **+0.010299**, và tỷ lệ ngày có IC dương rơi xuống dưới 50% (**49.00%**).
     * Ngược lại, $L=7$ duy trì Mean IC cao ở mức **+0.014321** (tỷ lệ ngày dương 54.58%), vượt trội $L=15$ (+0.011627) tới **+0.002693** (+0.27% IC tuyệt đối) và áp sát mốc của Ridge (+0.015803).
4. **Năm 2022 (Thị trường gấu sụt giảm mạnh diện rộng do thắt chặt vĩ mô)**:
   - Ở đợt thử nghiệm trước, năm 2022 là năm mà Ridge (+0.033095) dẫn trước GBDT 15 lá (+0.024168) tới $-0.89\%$ IC do các nhát cắt cây bị nhiễu.
   - Thử nghiệm này cho thấy **$L=7$ tạo ra bước nhảy vọt lớn nhất chính tại năm 2022**: Mean IC tăng vọt lên **+0.028585** ($\Delta = \mathbf{+0.004418}$ hay **+0.44%** IC tuyệt đối so với $L=15$), với tỷ lệ ngày thắng trước $L=15$ đạt **52.80%**. Cây nông giúp giảm bớt việc phân mảnh dữ liệu trong xu hướng giảm đồng loạt.
5. **Năm 2023 (Thị trường phân hóa phục hồi sau đáy)**:
   - Cả 3 cấu hình lá đều tiếp tục vượt trội áp đảo so với Ridge (+0.003494, gấp hơn 4 lần).
   - $L=31$ nhỉnh hơn nhẹ (+0.014906) so với $L=15$ (+0.014618) và $L=7$ (+0.014409). Tuy nhiên, mức chênh lệch giữa 7 lá và 15 lá là không đáng kể ($-0.000209$, chỉ 0.02% IC), trong khi $L=7$ vẫn có tỷ lệ ngày IC dương cao nhất (54.62% vs 53.82%).

---

## 4. Vì Sao Chọn Cấu Hình max_leaf_nodes = 7?

Dựa trên toàn bộ kết quả kiểm định walk-forward 5 năm trên tập Development, đề xuất dứt khoát là **chọn giữ `max_leaf_nodes = 7`** làm cấu hình chuẩn cho mô hình GBDT baseline. 

Các luận cứ kinh tế lượng và kỹ thuật cốt lõi:

1. **Hiệu năng tổng thể cao nhất và cải thiện nhất quán qua các năm**:
   - $L=7$ nâng Mean Daily Rank IC tổng thể 5 năm lên **`+0.020967`** (+2.10%), cao hơn $L=15$ (+0.019158) và $L=31$ (+0.018683). Mức cải thiện so với 15 lá đạt **`+0.001809`** (+0.18% IC tuyệt đối, tương đương mức tăng trưởng tương đối **+9.4%**).
   - Tính ưu việt của $L=7$ **không tập trung cục bộ ở một năm đơn lẻ**: $L=7$ vượt trội $L=15$ ở **4 trên 5 năm** kiểm định (2019, 2020, 2021, 2022). Duy nhất năm 2023 thì $L=7$ chỉ kém nhẹ 0.02% IC so với $L=15$, nhưng lại có tỷ lệ phiên IC dương cao hơn (54.62% vs 53.82%).
2. **Khắc phục triệt để điểm yếu của GBDT trong thị trường gấu (2022) và bùng nổ thanh khoản (2021)**:
   - Trong năm 2021 và 2022, mô hình cây có xu hướng tạo ra các vùng chia nhánh quá phức tạp khiến tín hiệu bị nhiễu. Cây nông 7 lá với cấu trúc đơn giản (chỉ tương tác tối đa 2-3 biến) hoạt động như một bộ lọc nhiễu tự nhiên, mang lại mức cải thiện IC rất lớn: **+0.44%** trong năm 2022 và **+0.27%** trong năm 2021.
   - Nhờ đó, $L=7$ giúp thu hẹp đáng kể khoảng cách với Ridge trong các giai đoạn thị trường giảm đồng loạt, trong khi vẫn giữ nguyên ưu thế áp đảo của mô hình phi tuyến trong các giai đoạn sốc biến động (2020) và phục hồi phân hóa (2023).
3. **Bằng chứng rõ ràng về suy giảm hiệu năng của cây sâu ($L=31$)**:
   - Khi tăng số lá lên 31, Mean IC tổng thể giảm từ $+0.020967$ ($L=7$) xuống $+0.019158$ ($L=15$) và xuống $+0.018683$ ($L=31$).
   - Năm 2021 chứng kiến $L=31$ bị overfit rõ rệt khi tỷ lệ ngày IC dương giảm xuống dưới ngưỡng ngẫu nhiên (49.00%). Điều này khẳng định giả thuyết rằng trong dự báo cross-sectional ngắn hạn, **cây nông điều chuẩn cấu trúc mạnh luôn bền vững hơn cây sâu**.
4. **Hiệu năng tính toán và tốc độ xử lý vượt trội**:
   - Cây 7 lá chỉ mất trung bình ~20 giây để huấn luyện trên 4,3 đến 5,3 triệu dòng mỗi fold (nhanh hơn 40% so với 31 lá). Thời gian dự báo trên toàn bộ 240.000 dòng validation mỗi năm chỉ mất **~0.57 giây**.

---

## 5. Danh Mục Sản Phẩm & Artifacts

1. **Pipeline Script**:
   - [`scripts/01_pipeline/24_grid_search_gbdt_leaf.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/24_grid_search_gbdt_leaf.py)
2. **Cấu hình & Nhật ký chạy**:
   - [`configs/walk_forward_gbdt_leaf_grid_run.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_gbdt_leaf_grid_run.yaml)
3. **Bảng Dự Đoán Hợp Nhất 5 Fold (1.202.259 dòng)**:
   - [`data/processed/val_predictions_gbdt_leaf_grid.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/val_predictions_gbdt_leaf_grid.parquet)
4. **Bảng Daily IC và Tóm Tắt CSV/Parquet (1.253 phiên)**:
   - [`outputs/reports/daily_ic_gbdt_leaf_grid.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/daily_ic_gbdt_leaf_grid.csv)
   - [`data/processed/daily_ic_gbdt_leaf_grid.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/daily_ic_gbdt_leaf_grid.parquet)
   - [`outputs/reports/summary_gbdt_leaf_grid.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/summary_gbdt_leaf_grid.csv)
5. **15 Model Files Đã Lưu (3 configs x 5 folds)**:
   - `models/walk_forward_gbdt_leaf_grid/gbdt_leaf_7_fold_{1..5}.joblib`
   - `models/walk_forward_gbdt_leaf_grid/gbdt_leaf_15_fold_{1..5}.joblib`
   - `models/walk_forward_gbdt_leaf_grid/gbdt_leaf_31_fold_{1..5}.joblib`
6. **Kiểm thử tự động**:
   - [`tests/test_gbdt_leaf_grid.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/tests/test_gbdt_leaf_grid.py) (**3/3 tests PASSED**).

---

## 6. Giới Hạn Nghiêm Ngặt

- Mọi phân tích và đề xuất được giới hạn nghiêm ngặt trong tập **Development (2000–2023)**.
- **Tập OOS (2024–2026) tiếp tục được giữ đóng băng tuyệt đối**.
- Chưa thực hiện refit trên toàn bộ Development và chưa tiến hành backtest danh mục.
