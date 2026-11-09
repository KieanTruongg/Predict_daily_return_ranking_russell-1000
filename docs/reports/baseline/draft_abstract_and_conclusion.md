# Bản Nháp Đồ Án: Tóm Tắt (Abstract) Và Kết Luận (Conclusion)

> **Thông tin văn bản:**  
> - **Mã tài liệu:** `docs/reports/baseline/draft_abstract_and_conclusion.md`
> - **Nhiệm vụ:** Soạn thảo hai đoạn văn hoàn chỉnh phục vụ trực tiếp cho phần **Tóm tắt (Abstract)** và phần **Kết luận (Conclusion)** trong báo cáo đồ án môn học CO3101 (Đồ án tổng hợp - Trí tuệ nhân tạo).
> - **Tài liệu tham chiếu đã chốt:**
>   - Bản nháp mục Rank IC: [`draft_section_oos_rank_ic_results.md`](draft_section_oos_rank_ic_results.md)
>   - Bản nháp mục Backtest Top 20: [`draft_section_oos_backtest_results.md`](draft_section_oos_backtest_results.md)
>   - Báo cáo kết quả thực nghiệm tổng hợp: [`comprehensive_experimental_results_report.md`](comprehensive_experimental_results_report.md)
>   - Báo cáo kiểm thử backtest kỹ thuật: [`oos_backtest_primary_report.md`](oos_backtest_primary_report.md)

---

## 1. Bản Nháp Phần Tóm Tắt (Abstract)

> **Tóm tắt (Abstract):**  
> Nghiên cứu này đánh giá thực nghiệm năng lực ứng dụng học máy trong bài toán dự báo thứ tự xếp hạng tỷ suất sinh lời hàng ngày của cổ phiếu trên không gian chỉ số Russell 1000 ($\approx 976$ mã) trong 624 phiên ngoài mẫu (Out-of-Sample - OOS) chính từ ngày 03/01/2024 đến 30/06/2026 (ngày nhãn kết quả thực thi $T+1$). Từ chuỗi dữ liệu giá đóng cửa và khối lượng giao dịch, 13 đặc trưng kỹ thuật được trích xuất để huấn luyện mô hình hồi quy tuyến tính Ridge Baseline ($\alpha=1.0$, kết hợp chuẩn hóa `StandardScaler`) và mô hình cây quyết định tăng cường độ dốc dạng histogram `HistGradientBoostingRegressor` (GBDT 7 leaves, không qua scaler) trên tập dữ liệu Phát triển (2000–2023). Cả hai mô hình được đóng băng nguyên trạng tham số trong suốt 624 phiên OOS chính.  
> 
> Đặt bài toán dự báo xếp hạng trên 624 phiên OOS làm **kết quả chính**, Ridge Baseline và GBDT Candidate đạt Mean Spearman Rank IC lần lượt là **0,023050** ($t\text{-statistic} = +3,58, p = 0,00037$) và **0,020403** ($t\text{-statistic} = +3,43, p = 0,00065$) khi xếp hạng cổ phiếu theo tỷ suất sinh lời Close-to-Close của phiên kế tiếp. Cả hai mô hình đều có Mean IC dương và đạt mức ý nghĩa thống kê cao ($p < 0,001$) trong kiểm định hai phía so với giả thuyết không ($\text{Mean IC} = 0$), trong đó Ridge có Mean IC quan sát được cao nhất. Ngược lại, tín hiệu đối chứng động lượng 20 phiên (`ret_20d`) đạt Mean IC âm **-0,004393** ($t = -0,64, p = 0,522$) và không có ý nghĩa thống kê.  
> 
> Nhằm kiểm tra tính khả thi thực tế và đo lường sự bào mòn của ma sát giao dịch, nhóm triển khai **backtest minh họa** trên danh mục Long-Only Top 20 (mua Open $T+1$, bán Close $T+1$, tự tài trợ và tích hợp bộ lọc 18 sự kiện ngừng giao dịch), với lưu ý quy tắc danh mục được thiết kế sau khi đã xem xét kết quả Rank IC OOS. Khi chưa tính chi phí (0 bps), Ridge chuyển hóa thành công Rank IC thành lợi nhuận gộp danh mục **+34,93%** (CAGR +12,86%, Sharpe 0,60), trong khi GBDT đạt **-7,83%** và ret_20d đạt **+12,90%**. Tuy nhiên, dưới mức chi phí giả định 20 bps mỗi vòng mua–bán (round-trip), tần suất tái cân bằng 100% hàng ngày đã bào mòn toàn bộ lợi nhuận gộp, đưa NAV cuối kỳ của Ridge xuống **-61,19%** (do chịu 80.385,51 USD chi phí trực tiếp và hiệu ứng suy giảm vốn tái đầu tư qua từng phiên). Nghiên cứu khẳng định mô hình học máy tuyến tính thực sự học được tín hiệu alpha xếp hạng ngắn hạn từ dữ liệu giá và khối lượng, nhưng việc thương mại hóa khả thi bắt buộc phải đi kèm với các giải pháp kiểm soát vòng quay vốn và kéo dài chu kỳ nắm giữ.

---

## 2. Bản Nháp Phần Kết Luận Toàn Đồ Án (Conclusion)

> **Kết luận (Conclusion):**  
> Dựa trên toàn bộ kết quả nghiên cứu và thực nghiệm kiểm định độc lập trên 624 phiên ngoài mẫu chính (2024–2026), đồ án rút ra bốn kết luận học thuật và phương pháp luận cốt lõi:
> 
> ### 1. Năng lực dự báo xếp hạng là kết quả chính của nghiên cứu
> Kết quả đánh giá trên 624 phiên ngoài mẫu độc lập khẳng định các mô hình học máy thực sự học được quy luật phân loại thứ tự tương đối của tỷ suất sinh lời cổ phiếu cho ngày kế tiếp:
> - Cả Ridge Baseline ($\alpha=1.0$) và GBDT Candidate (7 leaves) đều duy trì được hệ số tương quan hạng trung bình dương, đạt Mean Spearman Rank IC lần lượt là **+0,023050** và **+0,020403** trên rổ $\approx 976$ cổ phiếu Russell 1000.
> - Thống kê kiểm định hai phía so với giả thuyết không ($\text{Mean IC} = 0$) cho thấy cả hai mô hình đều đạt mức ý nghĩa thống kê rất cao với $t\text{-statistic} = +3,58$ ($p = 0,00037$) cho Ridge và $t\text{-statistic} = +3,43$ ($p = 0,00065$) cho GBDT. Xác suất các kết quả này xảy ra do ngẫu nhiên là dưới $0,1\%$ ($p < 0,001$).
> - Trên tập mẫu 624 phiên OOS chính, Ridge có Mean Rank IC quan sát được cao nhất trong ba tín hiệu nghiên cứu.
> - Số liệu thực tế đo lường theo từng năm nhãn $T+1$ cho thấy Mean Rank IC của cả hai mô hình thấp hơn ở các giai đoạn sau trong phạm vi đánh giá chính (giảm từ $\sim +0,033$ trong năm 2024 xuống $\sim +0,018$ ở Ridge và $\sim +0,014$ ở GBDT năm 2025, rồi tiếp tục ở mức $\sim +0,011$ và $\sim +0,007$ trong nửa đầu 2026), nhưng vẫn bảo toàn giá trị dương ở mọi năm.
> - Ngược lại, tín hiệu đối chứng động lượng quá khứ `ret_20d` đạt Mean IC âm **-0,004393** ($t = -0,64, p = 0,522$), hoàn toàn không có ý nghĩa thống kê, chứng minh rằng việc kết hợp đa đặc trưng kỹ thuật giá và khối lượng mang lại ưu thế vượt bậc so với việc bám theo đà tăng giá đơn thuần.
> 
> ### 2. Backtest danh mục Top 20 đóng vai trò minh họa và kiểm tra ma sát
> Nhóm nghiên cứu nhấn mạnh rằng thử nghiệm mô phỏng giao dịch danh mục Long-Only Top 20 (mua Open $T+1$, bán Close $T+1$) được **thiết kế sau khi đã xem xét và đối chiếu kết quả Rank IC OOS**. Vai trò của backtest không phải là tìm kiếm chiến lược giao dịch tối ưu, mà đóng vai trò là một bài kiểm tra ma sát (friction stress test) nhằm đo lường tính khả thi thực tế:
> - **Hiệu năng gộp (0 bps):** Ridge Baseline chuyển hóa thành công năng lực xếp hạng thành lợi nhuận gộp danh mục **+34,93%** (NAV tăng từ 100.000 USD lên 134.925,42 USD, CAGR +12,86%, Sharpe 0,60, Max Drawdown -23,63%). Trong khi đó, GBDT đạt **-7,83%** và ret_20d đạt **+12,90%**.
> - **Hiệu năng sau chi phí giả định (20 bps):** Dưới mức chi phí giả định 20 bps mỗi vòng mua–bán (round-trip), lợi suất ròng của cả ba mô hình đều bị kéo tụt xuống mức âm sâu: Ridge đạt **-61,19%** (NAV còn 38.807,77 USD), ret_20d đạt **-67,58%** (NAV còn 32.415,77 USD) và GBDT đạt **-73,53%** (NAV còn 26.469,23 USD).
> - **Phân rã chênh lệch NAV của Ridge:** Khoản chênh lệch NAV cuối kỳ **-96.117,64 USD** giữa hai kịch bản phản ánh hai thành phần cụ thể: (1) Tổng chi phí trực tiếp nộp phí và trượt giá bị trừ trong sổ lệnh là **80.385,51 USD** (chiếm hơn 80% vốn ban đầu); và (2) Phần chênh lệch NAV còn lại **-15.732,13 USD** phản ánh quy mô vốn tái đầu tư bị thu hẹp dần qua từng phiên do bị trừ chi phí hàng ngày.
> 
> ### 3. Bản chất cơ học của sự phân kỳ giữa Rank IC toàn rổ và PnL danh mục Top 20
> Thực nghiệm làm sáng tỏ nguyên nhân vì sao một mô hình có Rank IC dương có ý nghĩa thống kê vẫn có thể ghi nhận kết quả danh mục âm:
> 1. **Toàn Universe vs. Đuôi phân phối cực đoan:** Rank IC đánh giá tính đơn điệu thứ bậc trên toàn thể $\approx 976$ mã, trong khi danh mục Top 20 chỉ giao dịch đúng 20 mã ở đỉnh phân phối (top $2\%$). Tại vùng cực đoan này, các dự báo có thể bị phân tán bởi độ biến động cá biệt của cổ phiếu (như minh chứng từ GBDT có Mean IC dương mạnh nhưng danh mục gộp lại thua lỗ -7,83%).
> 2. **Close-to-Close vs. Open-to-Close và Lợi suất qua đêm:** Rank IC đo lường thứ hạng của lợi suất Close-to-Close ($P_{T+1}^{\text{close}} / P_T^{\text{close}} - 1$), trong khi danh mục thực tế chỉ giao dịch trong phiên Open-to-Close ($P_{T+1}^{\text{close}} / P_{T+1}^{\text{open}} - 1$). Sự xuất hiện của lợi suất qua đêm $R_{i, T \rightarrow T+1}^{\text{overnight}} = \frac{P_{i, T+1}^{\text{open}}}{P_{i, T}^{\text{close}}} - 1$ tạo ra độ lệch cơ học tất yếu giữa hai thước đo.
> 3. **Ma sát chi phí đối với chiến lược xoay vòng hàng ngày:** Tần suất tái cân bằng 100% mỗi ngày làm nhân bội chi phí giao dịch, biến một chiến lược có alpha gộp dương thành một danh mục thua lỗ ròng sau ma sát.
> 
> ### 4. Ranh giới nghiên cứu và Khuyến nghị phát triển
> - **Ranh giới dữ liệu:** Toàn bộ kết luận học thuật chính thức của đồ án được neo giữ chặt chẽ trên **624 phiên ngoài mẫu chính**, kết thúc tại ngày nhãn thực thi kết quả là **30/06/2026** (tương ứng ngày sinh tín hiệu 29/06/2026). Dữ liệu sau thời điểm này chịu giới hạn về snapshot rổ Russell 1000 và không được sử dụng để đưa ra các kết luận khoa học chính thức.
> - **Khuyến nghị phát triển tiếp theo:** Để thương mại hóa khả thi tín hiệu alpha từ mô hình Ridge Baseline, các nghiên cứu tiếp theo cần: (1) Mở rộng chân trời nắm giữ từ 1 ngày lên 5–20 ngày; (2) Áp dụng kỹ thuật dải đệm tái cân bằng (Buffer Rebalancing) nhằm tránh mua bán các mã dao động quanh ngưỡng Top 20; và (3) Tối ưu hóa hàm mục tiêu hướng trực tiếp tới lợi suất trong phiên Open-to-Close thay vì Close-to-Close thuần túy.

---

## 3. Danh Mục Liên Kết Tài Liệu Đối Chiếu

Toàn bộ số liệu, công thức, bảng biểu và đồ thị trực quan được lưu trữ và đối soát tại các tài liệu sau:
* **Bản nháp mục kết quả Rank IC:** [`draft_section_oos_rank_ic_results.md`](draft_section_oos_rank_ic_results.md)
* **Bản nháp mục backtest danh mục Top 20:** [`draft_section_oos_backtest_results.md`](draft_section_oos_backtest_results.md)
* **Báo cáo kết quả thực nghiệm tổng hợp toàn diện:** [`comprehensive_experimental_results_report.md`](comprehensive_experimental_results_report.md)
* **Báo cáo kiểm thử backtest kỹ thuật (18 sự kiện):** [`oos_backtest_primary_report.md`](oos_backtest_primary_report.md)
* **Báo cáo đánh giá OOS Rank IC gốc:** [`oos_evaluation_report.md`](oos_evaluation_report.md)
* **Chuỗi Rank IC chi tiết 624 phiên (CSV):** [`outputs/reports/oos_daily_ic_2024_2026.csv`](../../../outputs/reports/oos_daily_ic_2024_2026.csv)
* **Bảng tổng hợp hiệu năng 6 kịch bản (CSV):** [`outputs/reports/backtest_primary_scope/performance_summary_all_scenarios.csv`](../../../outputs/reports/backtest_primary_scope/performance_summary_all_scenarios.csv)
