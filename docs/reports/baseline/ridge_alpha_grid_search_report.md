# Báo Cáo Grid Search Siêu Tham Số Alpha Cho Ridge Baseline (5 Folds Walk-Forward)

**Ngày thực hiện**: 2026-11-07  
**Phạm vi**: 5 Folds Expanding Window Walk-Forward (Development Window 2019–2023, 1.253 phiên giao dịch)  
**Lưới tham số thử nghiệm**: $\alpha \in [1, 1000, 10000, 100000, 1000000]$  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Strictly Frozen)  

---

## 1. Đối Chiếu Tính Nhất Quán & Mốc Parity ($\alpha = 1.0$)

Trước khi so sánh các mức $\alpha$ khác nhau, hệ thống đã kiểm tra đối chiếu kết quả của $\alpha = 1.0$ với lượt chạy Walk-Forward độc lập trước đó:
- **Số phiên giao dịch kiểm định**: **1.253 phiên** (Kỳ vọng: 1.253).
- **Mean Daily Spearman Rank IC ($\alpha = 1.0$)**: **`+0.016497`** (Kỳ vọng: `+0.01649668`).
- **Tỷ lệ ngày dương**: **`54.11%`** (Kỳ vọng: `54.11%`).
- **Kết luận**: **Khớp tuyệt đối 100%**. Quy trình chuẩn hóa `StandardScaler` và chia tập giữ nguyên vẹn tính nhân quả và độ tái lập.

---

## 2. Bảng Tổng Hợp Kết Quả Grid Search Trên 5 Fold Walk-Forward

| Alpha ($\alpha$) | Mean IC Toàn Bộ (1.253 phiên) | Chênh lệch so với $\alpha=1$ ($\Delta$ IC) | Tỷ lệ Ngày Dương | Annualized IC IR | t-statistic | IC 2019 (251 phiên) | IC 2020 (252 phiên) | IC 2021 (251 phiên) | IC 2022 (250 phiên) | IC 2023 (249 phiên) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$1$** *(Mốc gốc)* | **+0.016497** | $0.000000$ | **54.11%** | **1.1993** | **2.6743** | +0.0094 | +0.0206 | **+0.0158** | **+0.0331** | +0.0035 |
| **$1.000$** | **+0.016499** | $+0.000003$ | 54.11% | 1.1992 | 2.6741 | +0.0094 | +0.0206 | +0.0158 | +0.0331 | +0.0035 |
| **$10.000$** | **+0.016518** | $+0.000021$ | 54.11% | 1.1985 | 2.6725 | +0.0095 | +0.0207 | +0.0158 | +0.0331 | +0.0035 |
| **$100.000$** | **+0.016617** | $+0.000120$ | **54.27%** | 1.1946 | 2.6639 | +0.0099 | **+0.0209** | +0.0156 | **+0.0332** | +0.0035 |
| **$1.000.000$** | **+0.016867** | **+0.000370** | 53.63% | 1.1985 | 2.6725 | **+0.0119** | +0.0207 | +0.0153 | +0.0325 | **+0.0039** |

---

## 3. Phân Tích Chuyên Sâu & Đánh Giá Tính Nhất Quán

1. **Hiệu ứng Quy mô Mẫu Lớn ($N \approx 5 \times 10^6$ dòng)**:
   - Trong hồi quy Ridge với ma trận hiệp phương sai mẫu cỡ lớn, độ lệch đường chéo của $X^T X$ có bậc độ lớn $\sim N \approx 5.000.000$.
   - Các mức $\alpha \le 10.000$ chỉ tạo ra độ dịch chuyển cực nhỏ ($\alpha / N \le 0.002$), khiến trọng số $\beta$ và hệ số IC gần như không thay đổi so với $\alpha = 1$ (chênh lệch chỉ xuất hiện ở chữ số thập phân thứ 5 hoặc 6).
2. **Đánh giá mức $\alpha = 1.000.000$ (Mức có Mean IC danh nghĩa cao nhất)**:
   - Mức $\alpha = 1.000.000$ có Mean IC cao nhất đạt **`+0.016867`**, tăng **`+0.000370`** (+0.037% IC) so với $\alpha = 1$.
   - **Tuy nhiên, lợi thế này KHÔNG nhất quán qua các năm**:
     * **Lợi thế tập trung cục bộ ở năm 2019**: Mức tăng tại năm 2019 là $+0.002474$ (từ $+0.0094$ lên $+0.0119$), đóng góp tới **67%** tổng mức chênh lệch của toàn bộ 5 năm.
     * **Bị suy giảm hiệu năng ở 2 năm quan trọng**: Tại năm 2021, Mean IC giảm từ $+0.0158$ xuống $+0.0153$ ($\Delta = -0.00053$). Tại năm 2022 (năm thị trường biến động mạnh nhất), Mean IC giảm từ $+0.0331$ xuống $+0.0325$ ($\Delta = -0.00056$).
     * **Tỷ lệ ngày dương bị sụt giảm**: Tỷ lệ ngày IC dương giảm từ **$54.11\%$** xuống **$53.63\%$** (mất đi 6 ngày chiến thắng).
     * **Chỉ số rủi ro IR không cải thiện**: Annualized IC IR giữ nguyên ở mức $1.1985$ (thậm chí thấp hơn nhẹ so với $1.1993$ của $\alpha=1$), t-statistic hầu như không đổi ($2.672$ vs $2.674$).

---

## 4. Đề Xuất Lựa Chọn Cấu Hình Mô Hình

> [!TIP]
> **Đề xuất khuyến nghị**: **GIỮ NGUYÊN $\alpha = 1.0$ LÀM BASELINE CHÍNH THỨC**
> 
> **Lý do**:
> 1. Bằng chứng cải thiện thống kê của các mức $\alpha$ lớn hơn là **rất yếu và không nhất quán** qua các năm (tổng chênh lệch chỉ $+0.037\%$ IC, phụ thuộc chủ yếu vào năm 2019 trong khi làm giảm hiệu suất của 2021 và 2022).
> 2. $\alpha = 1.0$ mang lại **tỷ lệ ngày có IC dương cao hơn (54.11% vs 53.63%)** và Annualized IC IR tốt hơn.
> 3. Giữ $\alpha = 1.0$ giúp mô hình giữ được sự mộc mạc, không rơi vào bẫy "overfitting siêu tham số trên validation", tạo chuẩn đối sánh (benchmark) tin cậy và khắt khe nhất để so sánh với các lớp mô hình phi tuyến (GBDT, RankNet) ở các bước sau.

---

## 5. Danh Mục Tệp Sản Phẩm Đã Lưu Trữ

- **Bảng Daily IC đa tham số**:
  - CSV: [`outputs/reports/daily_ic_ridge_alpha_grid.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/daily_ic_ridge_alpha_grid.csv)
  - Parquet: [`data/processed/daily_ic_ridge_alpha_grid.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/daily_ic_ridge_alpha_grid.parquet)
- **Bảng tổng hợp đối soát theo Alpha**:
  - [`outputs/reports/summary_ridge_alpha_grid.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/outputs/reports/summary_ridge_alpha_grid.csv)
- **Cấu hình tái lập YAML**:
  - [`configs/ridge_alpha_grid_search_run.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/ridge_alpha_grid_search_run.yaml)
- **Kịch bản Pipeline Grid Search**:
  - [`scripts/01_pipeline/22_grid_search_ridge_alpha.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/22_grid_search_ridge_alpha.py)
- **Kiểm thử tự động**:
  - [`tests/test_grid_search_ridge.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/tests/test_grid_search_ridge.py) (**2/2 tests PASSED**).
  - Toàn bộ test suite liên quan: **22/22 tests PASSED**.
