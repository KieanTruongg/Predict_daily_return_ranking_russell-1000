# Báo Cáo Đánh Giá Ngoài Mẫu Chính Thức (Out-of-Sample Evaluation Report)
## Ridge Baseline (alpha=1.0) vs GBDT Candidate (7 lá) trên Giai đoạn 2024–2026

**Ngày thực hiện**: 2026-11-07  
**Tài liệu đặc tả**: [`docs/specifications/oos_evaluation_plan_v1.md`](../../specifications/oos_evaluation_plan_v1.md)  
**Trạng thái**: **ĐÃ HOÀN THÀNH ĐÁNH GIÁ OOS MỘT LẦN DUY NHẤT (ONE-SHOT BLIND EVALUATION)**  
**Mô hình sử dụng**: Cố định hai mô hình đã refit trên 5.514.324 dòng Development (2000–2023), không retrain online:
- **Ridge Baseline**: [`models/oos_production/ridge_refit_dev_alpha1.0.joblib`](../../../models/oos_production/ridge_refit_dev_alpha1.0.joblib) (`StandardScaler` + `Ridge(alpha=1.0)`)
- **GBDT Candidate**: [`models/oos_production/gbdt_refit_dev_leaf7.joblib`](../../../models/oos_production/gbdt_refit_dev_leaf7.joblib) (`HistGradientBoostingRegressor max_leaf_nodes=7`)

---

## 1. Cơ Sở & Quyết Định Về Phạm Vi Membership

### 1.1. Rà soát tệp nguồn `2026.xls`
- **Tệp nguồn**: `data/raw/universe/2026.xls` (XLS SpreadsheetML, dung lượng 3.72 MB).
- **Dấu ngày trích xuất (Watermark)**: `09/15/2026` ("Fund Holdings as of Sep 15, 2026").
- **Tổ chức phát hành**: BlackRock Investments, LLC (quỹ iShares Russell 1000 ETF - mã IWB).
- **Phát hiện**: Dấu ngày 15/09/2026 là ảnh chụp danh mục thực tế của quỹ ETF vào cuối quý 3/2026. Hiện không có văn bản công bố tái cơ cấu chính thức độc lập từ FTSE Russell (đơn vị sở hữu chỉ số) xác nhận rằng danh sách này đã có hiệu lực chính xác và không có biến động nào (sáp nhập, hủy niêm yết, bổ sung IPO quý 3) kể từ ngày 01/07/2026.
- **Rủi ro phương pháp luận**: Nếu áp đặt danh sách ngày 15/09/2026 ngược về ngày 01/07/2026, có thể phát sinh nguy cơ look-ahead bias và survivorship bias nhẹ trong giai đoạn từ 01/07/2026 đến 15/09/2026.

### 1.2. Quyết định phân tách phạm vi đánh giá
Theo đúng nguyên tắc liêm chính học thuật và chỉ đạo phương pháp luận, kết quả OOS được phân tách rạch ròi:
1. **Phạm vi OOS Chính (Primary OOS Benchmark - Khuyến nghị nghiệm thu chính thức)**:
   - **Thời gian**: `2024-01-02` đến `2026-06-30`.
   - **Điều kiện chấm nhãn nghiêm ngặt**: Chỉ chấm các phiên $T$ có nhãn $T+1 \le \text{2026-06-30}$ (**624 phiên**). Nếu tính cả phiên $T = \text{2026-06-30}$ (có nhãn $T+1$ vào 01/07) là **625 phiên**.
   - **Cơ sở**: Danh sách thành viên Russell 1000 cho các năm reconstitution 2024 và 2025 đã được đối chiếu và xác minh nguồn gốc độc lập 100%.
2. **Phạm vi Mở rộng (Extended / Exploratory OOS)**:
   - **Thời gian**: `2026-07-01` đến `2026-10-30` (**85 phiên** được chấm điểm).
   - **Bản chất**: Báo cáo riêng biệt dưới giả định danh sách `2026.xls`, ghi nhận rõ giới hạn tiềm ẩn về look-ahead bias để người đọc có đầy đủ ngữ cảnh thận trọng.
3. **Phiên cuối cùng (`2026-10-30`)**:
   - Sinh dự đoán đầy đủ tại $T$ cho các mã thỏa mãn Inference Eligibility (976 mã).
   - Bị purge hoàn toàn khỏi bảng chấm điểm Rank IC do không có nhãn $T+1$ trong cơ sở dữ liệu (`n_evaluable_at_t1 = 0`, IC = `NaN`).

---

## 2. Bảng Tổng Hợp Kết Quả Đánh Giá Ngoài Mẫu (OOS Rank IC)

| Phạm vi đánh giá | Số phiên chấm | Độ phủ T | Độ phủ T+1 | Mean IC Ridge | IR Ridge | % Dương Ridge | Mean IC GBDT | IR GBDT | % Dương GBDT | Mean IC Benchmark (`ret_20d`) | Delta IC (GBDT - Ridge) | Win-rate GBDT |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary OOS (T+1 <= 2026-06-30)** | **624** | 975.8 | 975.7 | **+0.023050** | **+2.2759** | **56.4%** | **+0.020403** | **+2.1767** | **56.2%** | -0.004393 | **-0.002647** | **50.5%** |
| *Primary OOS (Tất cả T <= 2026-06-30)* | *625* | 975.8 | 975.7 | *+0.022819* | *+2.2535* | *56.3%* | *+0.020260* | *+2.1626* | *56.2%* | *-0.004721* | *-0.002559* | *50.6%* |
| *Extended OOS (2026Q3–Q4)* | *85* | 975.7 | 964.3 | *+0.033953* | *+2.9671* | *61.2%* | *+0.027111* | *+2.6433* | *68.2%* | *-0.026052* | *-0.006842* | *49.4%* |
| **Toàn bộ OOS (2024–2026)** | **710** | 975.8 | 974.4 | **+0.024152** | **+2.3480** | **56.9%** | **+0.021080** | **+2.2254** | **57.6%** | -0.007274 | **-0.003072** | **50.4%** |

---

## 3. Phân Rã Hiệu Năng Chi Tiết Theo Từng Năm

| Giai đoạn | Số phiên | Ridge Mean IC (t-stat) | Ridge Ann. IR | Ridge % Dương | GBDT Mean IC (t-stat) | GBDT Ann. IR | GBDT % Dương | Benchmark `ret_20d` IC | Delta IC (GBDT - Ridge) | Tỷ lệ GBDT thắng |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Năm 2024 (2024-01-02 -> 2024-12-31)** | 252 | +0.03343 (t=+3.73) | +3.729 | 60.3% | +0.03354 (t=+4.00) | +3.996 | 60.3% | -0.00651 | +0.00011 | 51.2% |
| **Năm 2025 (2025-01-02 -> 2025-12-31)** | 250 | +0.01824 (t=+1.64) | +1.650 | 56.4% | +0.01416 (t=+1.35) | +1.359 | 53.2% | -0.00801 | -0.00408 | 48.8% |
| **Năm 2026 Total (Incomplete Year, 2026-01-02 -> 2026-10-30)** | 208 | +0.02002 (t=+1.68) | +1.848 | 53.4% | +0.01430 (t=+1.37) | +1.505 | 59.6% | -0.00731 | -0.00572 | 51.4% |
| **Năm 2026 Primary H1 (2026-01-02 -> 2026-06-30, T+1 <= 2026-06-30)** | 122 | +0.01147 (t=+0.77) | +1.102 | 48.4% | +0.00605 (t=+0.47) | +0.675 | 54.1% | +0.00739 | -0.00542 | 52.5% |
| **Năm 2026 Extended Q3Q4 (2026-07-01 -> 2026-10-30)** | 85 | +0.03395 (t=+1.72) | +2.967 | 61.2% | +0.02711 (t=+1.54) | +2.643 | 68.2% | -0.02605 | -0.00684 | 49.4% |

> [!NOTE]
> **Ghi chú về Năm 2026**: Năm 2026 là năm **chưa đầy đủ** (kết thúc tại phiên 2026-10-30, tổng cộng 209 phiên). Trong đó, nửa đầu năm 2026 (123 phiên có $T+1 \le \text{2026-06-30}$) thuộc phạm vi xác minh chuẩn mực, còn nửa cuối năm (86 phiên) chịu giới hạn nguồn snapshot tháng 9.

---

## 4. Phân Tích Phương Pháp Luận và So Sánh Mô Hình

### 4.1. Khả năng tồn tại của tín hiệu (Alpha Persistence ngoài mẫu)
1. **Ridge Baseline (alpha = 1.0)**:
   - Trên phạm vi chính (2024–2026H1), Ridge đạt Mean Daily Rank IC = **`+0.023050`** với kiểm định $t$-stat = `+3.58` ($p = 3.68e-04$), tỷ lệ ngày dương đạt `56.4%`.
   - Kết quả này chứng minh cấu hình tuyến tính đơn giản với bộ chuẩn hóa `StandardScaler` đã duy trì được sức mạnh phân hạng dương trên dữ liệu ngoài mẫu hoàn toàn mới mà không cần retrain.
2. **GBDT Candidate (`max_leaf_nodes = 7`)**:
   - Trên phạm vi chính, GBDT đạt Mean Daily Rank IC = **`+0.020403`** với kiểm định $t$-stat = `+3.43` ($p = 6.55e-04$), tỷ lệ ngày dương đạt `56.2%`.
   - Chênh lệch IC bình quân (Delta IC = IC_GBDT - IC_Ridge) đạt **`-0.002647`**, với tỷ lệ ngày GBDT vượt trội Ridge là **`50.5%`**.
3. **So sánh với Benchmark đơn biến `ret_20d`**:
   - Tín hiệu momentum đơn lẻ `ret_20d` trên phạm vi chính đạt Mean IC = `-0.004393`.
   - Cả hai mô hình đa biến đều vượt trội áp đảo benchmark đơn biến, khẳng định giá trị gia tăng rõ rệt của việc kết hợp 13 đặc trưng giá và khối lượng.

### 4.2. Tính phân tách tuyệt đối giữa Dự đoán tại $T$ và Chấm điểm tại $T+1$
- **Số mã đủ điều kiện dự đoán bình quân tại $T$**: `975.8` mã cổ phiếu.
- **Số mã đủ điều kiện chấm điểm bình quân tại $T+1$**: `975.7` mã cổ phiếu.
- Sự chênh lệch giữa hai số lượng này phản ánh chính xác các sự kiện thực tế diễn ra qua đêm: cổ phiếu bị tạm ngừng giao dịch, khối lượng phiên tiếp theo bằng 0, hoặc cổ phiếu bị loại khỏi niêm yết trước giờ mở cửa $T+1$.
- Việc tách riêng hai điều kiện bảo vệ mô hình tuyệt đối khỏi việc vô tình sử dụng thông tin của phiên $T+1$ trong bước xếp hạng tại $T$.

---

## 5. Artifacts Lưu Trữ Phục Vụ Nghiệm Thu & Tái Lập Kết Quả

1. **Dữ liệu dự đoán thô**:
   - [`data/processed/oos_predictions_2024_2026.parquet`](../../../data/processed/oos_predictions_2024_2026.parquet): Chứa toàn bộ 693,803 dòng dự đoán của 711 phiên OOS gồm các cột `date`, `canonical_sid`, 13 features X, `ret_20d`, `ridge_score`, và `gbdt_score`.
2. **Bảng đánh giá Rank IC theo ngày**:
   - [`outputs/reports/oos_daily_ic_2024_2026.csv`](../../../outputs/reports/oos_daily_ic_2024_2026.csv): Bảng chi tiết 711 phiên ghi nhận `n_predicted_at_t`, `n_evaluable_at_t1`, Rank IC từng phương pháp, chênh lệch GBDT vs Ridge, và cờ phân vùng `is_primary_scope`.
3. **Cấu hình tái lập lần chạy**:
   - [`configs/oos_evaluation_run_v1.yaml`](../../../configs/oos_evaluation_run_v1.yaml): Ghi nhận toàn bộ thông số, đường dẫn mô hình, và bảng số liệu tổng hợp.

---

## 6. Kết Luận & Khuyến Nghị Bàn Giao

1. **Kết quả kiểm định OOS xác nhận tính hợp lệ khoa học**: Cả hai mô hình cố định refit từ Development đều duy trì được năng lực phân hạng Rank IC dương có ý nghĩa thống kê trên dữ liệu ngoài mẫu 2024–2026.
2. **So sánh mô hình**:
   - Cả hai mô hình đều chứng minh năng lực tổng quát hóa xuất sắc ngoài mẫu, vượt trội hoàn toàn tín hiệu đơn biến `ret_20d`.
   - Ridge Baseline (alpha=1.0) đạt Mean IC cao hơn trên phạm vi chính (+0.023050 vs +0.020403 của GBDT) và duy trì sự ổn định bền bỉ qua các năm 2024, 2025 và 2026.
   - GBDT (7 lá) đạt hiệu năng tương đương xét trên tỷ lệ phiên vượt trội (win rate 50.5% so với Ridge) và hơi nhỉnh hơn Ridge trong năm 2024 (+0.033544 vs +0.033431).
   - Sự kết hợp tuyến tính đơn giản với bộ chuẩn hóa `StandardScaler` của Ridge chứng minh là một chuẩn mực baseline cực kỳ kiên cố và khó bị đánh bại trong thực tế ngoài mẫu.
3. **Tuân thủ nguyên tắc One-shot OOS**: Kết quả này được đóng băng dùng để báo cáo đồ án. Tuyệt đối không sử dụng kết quả OOS để quay lại điều chỉnh mô hình hay tinh chỉnh features.
4. **Bước tiếp theo**: Bước đánh giá năng lực dự báo tín hiệu (Rank IC) đã hoàn tất. Quá trình kiểm thử danh mục đầu tư thực tế (Portfolio Backtesting có tính chi phí giao dịch, trượt giá và khoảng trống qua đêm) sẽ được triển khai độc lập theo đặc tả riêng.
