# Báo Cáo Kỹ Thuật Bước 6: Khám Phá Dữ Liệu (EDA) Tập Huấn Luyện & Điều Tra Pháp Y 34 Biến Cố Lợi Suất Cực Đoan

**Dự án**: Dự đoán xếp hạng lợi suất hàng ngày rổ cổ phiếu Russell 1000 (Russell 1000 Daily Return Rankings)  
**Milestone**: M3 — Hệ Thống Báo Cáo Dữ Liệu & Kiểm Toán Pháp Y (Section R5)  
**Tác giả**: Đội ngũ Kỹ thuật Dữ liệu & Định lượng (Quantitative Data Engineering Team)  
**Ngày thực hiện thẩm định**: 04/11/2026  
**Phân vùng dữ liệu**: Development Partition (2000-07-01 đến 2023-12-29 — 23.5 năm) | **OOS Partition (2024-01-02 đến 2026-10-30 — ĐÓNG BĂNG TUYỆT ĐỐI)**  
**Tài liệu đối soát nguồn**:
- `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv`
- `docs/Data report/market_data_audit/tables/eda_cross_sectional_dispersion.csv`
- `docs/Data report/market_data_audit/tables/eda_liquidity_deciles.csv`
- `docs/Data report/market_data_audit/tables/eda_universe_dynamics_by_year.csv`
- `docs/Data report/market_data_audit/tables/extreme_returns_forensic_investigation.csv`
- `docs/Data report/market_data_audit/tables/top_50_positive_returns_audit.csv`
- `docs/Data report/market_data_audit/tables/top_50_negative_returns_audit.csv`

---

## 1. Tổng Quan & Thiết Lập Biên Giới Tập Phát Triển (Development Partition)

Báo cáo này công bố toàn bộ kết quả phân tích thống kê khám phá dữ liệu (Exploratory Data Analysis — EDA) và hồ sơ điều tra pháp y chuyên sâu 34 biến cố lợi suất cực đoan thuộc Bước 6 trong quy trình tiền xử lý định lượng cho bài toán dự đoán xếp hạng lợi suất hàng ngày của rổ cổ phiếu Russell 1000.

### 1.1. Nguyên Tắc Cách Ly Phân Vùng Bất Khả Xâm Phạm (Strict Data Partitioning)

Nhằm đảm bảo tính khách quan khoa học cao nhất và ngăn chặn triệt để nguy cơ quá khớp (overfitting) hoặc nhìn trộm dữ liệu ngoài mẫu (data snooping / look-ahead bias), dự án thiết lập ranh giới phân vùng bất khả xâm phạm:
1. **Tập Phát Triển (Development Partition: 2000-07-01 đến 2023-12-29)**:
   - Bao gồm đúng **23.5 năm lịch sử** với **5,912 phiên giao dịch NYSE**.
   - Là tập dữ liệu **duy nhất** được sử dụng cho toàn bộ hoạt động EDA, nghiên cứu đặc trưng (Feature Engineering Design), lựa chọn siêu tham số và huấn luyện mô hình (Cross-Validation Training).
   - Tổng quy mô mẫu hợp lệ phục vụ học máy có giám sát (`valid_label_mask == True`): **5,610,691 quan sát cổ phiếu-ngày (stock-days)**.
2. **Tập Ngoài Mẫu (Out-Of-Sample — OOS Partition: 2024-01-02 đến 2026-10-30)**:
   - Bao gồm gần **3 năm gần nhất** với **710 phiên giao dịch NYSE**.
   - **TRẠNG THÁI: ĐÓNG BĂNG HOÀN TOÀN (FROZEN)**. Tuyệt đối không được tính toán thống kê, không chạy EDA, không fit scaler, không tối ưu hóa feature trên tập này.
   - Phiên giao dịch chuyển tiếp $T = \text{2023-12-29}$ đã được **thanh lọc (purged 100%)** trong `valid_label_mask` để triệt tiêu mọi rò rỉ thông tin từ ngày 2024-01-02 vào nhãn giám sát.

---

## 2. Các Mômen Phân Phối Thống Kê Chuẩn Mực Của Lợi Suất Hàng Ngày

Toàn bộ các tham số thống kê mô tả (Distribution Moments) dưới đây được trích xuất trực tiếp từ tệp kiểm toán chuẩn `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv`, tính toán trên toàn bộ 5,610,691 quan sát hợp lệ của tập Development:

### 2.1. Bảng Tổng Hợp Các Mômen Phân Phối (Statistical Moments Table):

| Chỉ Số Thống Kê (Moment / Metric) | Giá Trị Thực Nghiệm Đo Được | Biểu Diễn Tỷ Lệ (%) | Ý Nghĩa Kinh Tế & Bản Chất Phân Phối |
|:---|:---:|:---:|:---|
| **Số lượng quan sát hợp lệ ($N$)** | **5,610,691** | 100.0% mẫu sạch | Quy mô mẫu lớn hàng đầu trong các nghiên cứu định lượng tài chính Hoa Kỳ |
| **Giá trị trung bình (Mean Return, $\mu$)** | **+0.0003787** | **+0.0379% / ngày** | Lợi suất kỳ vọng dương phản ánh phần bù rủi ro vốn chủ sở hữu (Equity Risk Premium) dài hạn |
| **Giá trị trung vị (Median Return)** | **+0.0003547** | **+0.0355% / ngày** | Trung vị xấp xỉ kỳ vọng, phản ánh xu thế tăng trưởng tự nhiên của các cổ phiếu vốn hóa lớn |
| **Độ biến động ngày (Daily Volatility, $\sigma$)** | **0.026530** | **2.653% / ngày** | Độ lệch chuẩn phân phối lợi suất hàng ngày của cổ phiếu đơn lẻ trong rổ Russell 1000 |
| **Độ biến động năm hóa (Annualized Vol)** | **0.421156** | **42.12% / năm** | $=\sigma \times \sqrt{252}$, phản ánh rủi ro phi hệ thống đáng kể của từng cổ phiếu thành phần |
| **Độ lệch (Skewness, $S$)** | **+0.5634** | $+0.563$ | Lệch phải nhẹ (Positive Skewness), do các phiên hồi phục kỹ thuật cực mạnh và mua lại doanh nghiệp |
| **Độ nhọn dư (Excess Kurtosis, $\kappa$)** | **66.875** | **66.88** | Đặc trưng đuôi rất dày (Heavy Tails) so với phân phối chuẩn ($\kappa = 0$), giảm từ 16,433 trước hiệu chỉnh |
| **Lợi suất ngày nhỏ nhất (Min Return)** | **-0.949735** | **-94.97%** | Vụ nộp đơn phá sản ngân hàng Lehman Brothers (LEH) ngày 2008-09-15 |
| **Lợi suất ngày lớn nhất (Max Return)** | **+2.278689** | **+227.87%** | Thỏa thuận hoãn nợ Repo & gói cứu trợ Fed TALF của MFA Financial ngày 2020-03-25 |

### 2.2. Bảng Phân Vị Chi Tiết Của Phân Phối Lợi Suất (Percentile Distribution Table):

| Phân Vị (Percentile) | Giá Trị Thập Phân | Tỷ Lệ Phần Trăm (%) | Giải Thích Vị Trí Phân Phối |
|:---:|:---:|:---:|:---|
| **p0.1 (0.1%)** | $-0.348835$ | **-34.88%** | Ngưỡng đuôi trái cực đoan (1 trên 1,000 phiên) |
| **p1.0 (1.0%)** | $-0.072822$ | **-7.28%** | Ngưỡng rủi ro Value-at-Risk 99% (VaR 99%) |
| **p5.0 (5.0%)** | $-0.035300$ | **-3.53%** | Ngưỡng sụt giảm mạnh thông thường (VaR 95%) |
| **p25.0 (Q1 - 25%)** | $-0.009835$ | **-0.98%** | Tứ phân vị thứ nhất |
| **p50.0 (Median)** | **+0.000355** | **+0.0355%** | Trung vị phân phối |
| **p75.0 (Q3 - 75%)** | $+0.010535$ | **+1.05%** | Tứ phân vị thứ ba (Độ trải giữa $IQR = Q3 - Q1 = 2.03\%$) |
| **p95.0 (95.0%)** | $+0.035634$ | **+3.56%** | Ngưỡng tăng trưởng mạnh thông thường |
| **p99.0 (99.0%)** | $+0.075145$ | **+7.51%** | Ngưỡng bứt phá đuôi phải 99% |
| **p99.9 (99.9%)** | $+0.174965$ | **+17.50%** | Ngưỡng đuôi phải cực đoan (1 trên 1,000 phiên) |

### 2.3. Tần Suất Xuất Hiện Các Cú Sốc Giá Cực Đoan (Tail Risk Frequencies):

- **Tần suất $|r| > 10\%$**:
  - Lợi suất tăng $> +10\%$: Chiếm **0.4918%** toàn bộ mẫu (tương đương **27,592 quan sát** stock-days).
  - Lợi suất giảm $< -10\%$: Chiếm **0.4342%** toàn bộ mẫu (tương đương **24,359 quan sát** stock-days).
- **Tần suất $|r| > 20\%$**:
  - Lợi suất tăng $> +20\%$: Chiếm **0.0655%** toàn bộ mẫu (tương đương **3,673 quan sát** stock-days).
  - Lợi suất giảm $< -20\%$: Chiếm **0.0535%** toàn bộ mẫu (tương đương **2,999 quan sát** stock-days).

### 2.4. Phân Tích Hiện Tượng Đuôi Dày (Heavy Tails) & So Sánh Với Phân Phối Chuẩn

Nếu lợi suất hàng ngày tuân theo phân phối chuẩn Gaussian với $\mu = 0.0379\%$ và $\sigma = 2.653\%$:
- Xác suất xuất hiện một biến cố sụt giảm $-34.88\%$ ($Z = \frac{-0.3488 - 0.00038}{0.02653} \approx -13.16\sigma$) là xấp xỉ $10^{-39}$ (về mặt thống kê lý thuyết là không bao giờ xảy ra trong toàn bộ tuổi thọ của vũ trụ).
- Tuy nhiên, trong thực tế thị trường chứng khoán, phân vị $p0.1\%$ ghi nhận mức $-34.88\%$, nghĩa là cứ 1,000 phiên thì có 1 phiên giảm sâu như vậy.
- Độ nhọn dư $\kappa = 66.88$ là bằng chứng thực nghiệm rõ ràng nhất khẳng định: **Không bao giờ được sử dụng mô hình hồi quy tuyến tính OLS thông thường trực tiếp trên giá trị lợi suất tuyệt đối**, vì các giả định phân phối chuẩn sẽ bị vi phạm hoàn toàn, dẫn đến tham số ước lượng bị chi phối và bóp méo bởi các điểm dị biệt (outliers).

---

## 3. Báo Cáo Điều Tra Pháp Y Chuyên Sâu 34 Ca Lợi Suất Cực Đoan

Toàn bộ 34 trường hợp lợi suất cực đoan nhất trong lịch sử 24 năm của rổ Russell 1000 được phân loại và kiểm toán pháp y chi tiết trong file `docs/Data report/market_data_audit/tables/extreme_returns_forensic_investigation.csv`. Dưới đây là phân tích chi tiết theo 3 nhóm chức năng:

### 3.1. Nhóm I: 13 Ca Hiệu Chỉnh Kỹ Thuật & Ngoại Lệ (CORR_001 đến CORR_013)

Đây là các ca biến dạng giá do lỗi dữ liệu của nhà cung cấp hoặc sự kiện phân tách cấu trúc doanh nghiệp:

| Investigation ID | Ngày Biến Cố | Ticker | Canonical SID | Lợi Suất Thô Chưa Chỉnh | Lợi Suất Sạch Trong Ma Trận | Phân Loại Pháp Y | Hành Động Kỹ Thuật Đã Xử Lý |
|:---:|:---:|:---:|:---|:---:|:---:|:---|:---|
| **CORR_001** | 2020-04-15 | `CHK` | `CHK R735QTJ8XC9X` | $+12,371.4\%$ | **-37.64%** | `CORRECTED_REVERSE_SPLIT` | Bổ sung Reverse Split 200:1 (factor=200.0) vào bảng Splits |
| **CORR_002** | 2016-06-01 | `CRC` | `CRC VW1A4C2VJMN9` | $+925.0\%$ | **+2.50%** | `CORRECTED_REVERSE_SPLIT` | Bổ sung Reverse Split 10:1 (factor=10.0) vào bảng Splits |
| **CORR_003** | 2005-05-10 | `ADCT`| `ADCT R735QTJ8XC9X`| $+620.0\%$ | **+2.86%** | `CORRECTED_REVERSE_SPLIT` | Bổ sung Reverse Split 7:1 (factor=7.0) vào bảng Splits |
| **CORR_004** | 2016-10-06 | `AA` | `AA R735QTJ8XC9X` | $+205.6\%$ | **+1.86%** | `CORRECTED_REVERSE_SPLIT` | Bổ sung Reverse Split 3:1 (factor=3.0) vào bảng Splits |
| **CORR_005** | 2010-05-25 | `DYN` | `DYN RRWGXYWP5HET` | $+391.2\%$ | **-1.76%** | `CORRECTED_REVERSE_SPLIT` | Bổ sung Reverse Split 5:1 (factor=5.0) vào bảng Splits |
| **CORR_006** | 2000-07-13 | `KSU` | `KSU R735QTJ8XC9X` | $-96.7\%$ | **QUARANTINED_NAN** | `SPECIAL_CORPORATE_SPINOFF`| Cách ly Spin-off Stilwell/Janus: return=NaN, vô hiệu hóa mask |
| **CORR_007** | 2008-07-01 | `SSP` | `SSP R735QTJ8XC9X` | $-92.7\%$ | **QUARANTINED_NAN** | `SPECIAL_CORPORATE_SPINOFF`| Cách ly Spin-off Scripps Networks: return=NaN, vô hiệu hóa mask |
| **CORR_008** | 2000-07-28 | `COMS`| `COMS R735QTJ8XC9X`| $-80.0\%$ | **QUARANTINED_NAN** | `SPECIAL_CORPORATE_SPINOFF`| Cách ly Spin-off Palm Inc: return=NaN, vô hiệu hóa mask |
| **CORR_009** | 2013-11-04 | `PENN`| `PENN R735QTJ8XC9X`| $-76.7\%$ | **QUARANTINED_NAN** | `SPECIAL_CORPORATE_SPINOFF`| Cách ly Spin-off GLPI REIT: return=NaN, vô hiệu hóa mask |
| **CORR_010** | 2010-04-19 | `MKL` | `MKL R735QTJ8XC9X` | $+1,364.5\% / -93.1\%$ | **QUARANTINED_NAN** | `CORRECTED_QUALITY_FLAG` | Cách ly 7 phiên nến lỗi Markel: return=NaN, vô hiệu hóa mask |
| **CORR_011** | 2020-03-20 | `SABR`| `SABR VPSS70OE3M1X`| $+630.0\% / -86.9\%$ | **QUARANTINED_NAN** | `CORRECTED_QUALITY_FLAG` | Cách ly lệnh khớp lỗi Triple Witching Sabre: return=NaN |
| **CORR_012** | 2008-06-10 | `LOW` | `LOW R735QTJ8XC9X` | $+229.7\% / -67.8\%$ | **QUARANTINED_NAN** | `CORRECTED_QUALITY_FLAG` | Cách ly 6 phiên trùng ticker Lowe's: return=NaN, vô hiệu hóa mask |
| **CORR_013** | 2001-02-02 | `CPTH`| `CPTH RJF8CZIDFLNP`| $+288.0\%$ | **QUARANTINED_NAN** | `CORRECTED_QUALITY_FLAG` | Cách ly chuỗi báo giá rác khi ngừng giao dịch CPTH: return=NaN |

### 3.2. Nhóm II: 9 Biến Cố Khủng Hoảng Thị Trường Thực Tế Đã Xác Minh (HIST_001 đến HIST_009)

Đây là các biến cố kinh tế có thật 100%, được xác thực qua hồ sơ nộp đơn tòa án phá sản Hoa Kỳ, thông cáo báo chí khẩn cấp của FDIC, FED, FHFA và SEC:

| Investigation ID | Ngày Biến Cố | Ticker | Canonical SID | Lợi Suất Thực Tế Trong Ma Trận | Căn Cứ Bằng Chứng Pháp Lý Độc Lập | Bản Chất Biến Cố Lịch Sử | Chính Sách Xử Lý Trong Pipeline |
|:---:|:---:|:---:|:---|:---:|:---|:---|:---|
| **HIST_001** | 2008-09-15 | `LEH` | `LEH R735QTJ8XC9X` | **-94.97%** | SEC Form 8-K nộp 15/09/2008; Tòa án Phá sản Quận Nam New York Case 08-13555 | Vụ phá sản lớn nhất lịch sử ngành tài chính ngân hàng Mỹ. Lehman Brothers nộp đơn Chapter 11 sau khi đàm phán giải cứu thất bại. | **Giữ nguyên 100% trong tập dữ liệu**. Mô hình cần học cách nhận diện tín hiệu sụp đổ. |
| **HIST_002** | 2002-07-01 | `WCOME`| `WCOM R735QTJ8XC9X`| **-91.67%** | SEC Litigation Release No. 17588 (WorldCom Accounting Fraud); Chapter 11 Filing | Đại án gian lận kế toán 11 tỷ USD bị phanh phui, cổ phiếu rớt từ $0.84 về $0.07 trước khi phá sản. | **Giữ nguyên 100% trong tập dữ liệu**. Rủi ro kế toán thực tế. |
| **HIST_003** | 2008-09-26 | `WM` | `WAMU R735QTJ8XC9X`| **-90.96%** | Thông cáo báo chí FDIC PR-85-2008 (JPMorgan tiếp quản mảng ngân hàng WaMu) | Vụ sụp đổ ngân hàng thương mại lớn nhất lịch sử Hoa Kỳ. FDIC phong tỏa và tịch thu tài sản trong đêm 25/09/2008. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_004** | 2008-09-08 | `FNM` | `FNM R735QTJ8XC9X` | **-90.14%** | Tuyên bố của Cơ quan Tài chính Nhà ở Liên bang (FHFA) ngày 07/09/2008 | Chính phủ Mỹ tiếp quản Fannie Mae vào diện quản chế đặc biệt để ngăn sụp đổ hệ thống thế chấp. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_005** | 2008-09-08 | `FRE` | `FRE R735QTJ8XC9X` | **-82.58%** | Tuyên bố của FHFA Conservatorship Statement ngày 07/09/2008 | Freddie Mac bị đặt dưới quyền quản chế của chính phủ cùng Fannie Mae. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_006** | 2001-11-28 | `ENE` | `ENE R735QTJ8XC9X` | **-85.10%** | SEC Form 8-K nộp 28/11/2001 (Termination of Dynegy Merger Agreement) | Dynegy hủy thỏa thuận sáp nhập cứu trợ Enron sau khi phát hiện các khoản nợ ngầm khổng lồ ngoài bảng cân đối. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_007** | 2008-03-17 | `BSC` | `BSC R735QTJ8XC9X` | **-84.17%** | SEC Form 8-K nộp 17/03/2008; Gói hỗ trợ thanh khoản khẩn cấp của Cục Dự trữ Liên bang | Bear Stearns bán tháo khẩn cấp cho JPMorgan Chase với giá $2/cổ phiếu dưới sự bảo lãnh thanh khoản của Fed. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_008** | 2008-09-29 | `WB` | `WB R735QTJ8XC9X` | **-80.63%** | Thông cáo báo chí FDIC PR-88-2008 (Thỏa thuận ban đầu với Citigroup trước khi sáp nhập Wells Fargo) | Ngân hàng Wachovia đối mặt với làn sóng rút tiền gửi hàng loạt trong cơn bão khủng hoảng tín dụng. | **Giữ nguyên 100% trong tập dữ liệu**. |
| **HIST_009** | 2020-03-25 | `MFA` | `MFA R9ULW9HANJHH` | **+227.87%** | SEC Form 8-K nộp 24/03/2020 (Thỏa thuận hoãn Margin Call); Thông cáo Fed TALF | MFA Financial đạt thỏa thuận trì hoãn lệnh gọi ký quỹ repo, đồng thời Cục Dự trữ Liên bang (Fed) công bố gói cứu trợ TALF khẩn cấp. | **Giữ nguyên 100% trong tập dữ liệu**. Biến cố phục hồi thanh khoản có thật trong COVID-19. |

#### Luận Điểm Học Thuật Về Việc Giữ Lại 100% Biến Cố Khủng Hoảng Lịch Sử:
Một số nhà thực hành dữ liệu thiếu kinh nghiệm thường có xu hướng loại bỏ các phiên giảm sâu $-80\%$ đến $-95\%$ (như LEH, WCOM, ENE) với lý do "outlier làm hỏng mô hình". Đây là sai lầm chết người:
- **Ngăn chặn Thiên lệch Kẻ Sống Sót (Survivorship Bias)**: Nếu chỉ giữ lại các ngày bình thường và xóa bỏ các ngày cổ phiếu sụp đổ, mô hình sẽ hình thành niềm tin sai lệch rằng rủi ro sụt giảm của thị trường luôn có giới hạn.
- **Bảo toàn Khả năng Quản trị Rủi ro Đuôi (Tail Risk Awareness)**: Một mô hình lượng hóa chuẩn phải học được các tín hiệu suy yếu trước khi sụp đổ (khối lượng bất thường, đà giảm liên tục, biến động tăng vọt) để hạ thấp thứ hạng của các mã này xuống đáy rổ.

### 3.3. Nhóm III: 12 Ca Cú Sốc Giá Chưa Xác Minh Độc Lập (UNVER_001 đến UNVER_012)

Đây là các phiên có bước nhảy giá lớn trên dữ liệu nến của nhà cung cấp nhưng đội ngũ kiểm toán chưa tìm thấy tài liệu SEC Form 8-K hoặc thông cáo báo chí chính thức xác nhận:

| Investigation ID | Ngày Biến Cố | Ticker | Canonical SID | Lợi Suất Ghi Nhận Trong Ma Trận | Phân Loại Học Thuật | Chính Sách Xử Lý Trong Pipeline |
|:---:|:---:|:---:|:---|:---:|:---|:---|
| **UNVER_001** | 2001-04-11 | `MRCH` | `WHIT R735QTJ8XC9X` | **+181.82%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_002** | 2020-06-08 | `CHK` | `CHK R735QTJ8XC9X` | **+175.49%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_003** | 2001-04-23 | `WBVN` | `WBVN RPGU5NCOCC4L`| **+128.57%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_004** | 2012-03-06 | `AWH` | `CIPH RYGS8EP7IJXH` | **+127.07%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_005** | 2016-03-04 | `SDRL` | `SDRL ULS968IG5U91` | **+121.85%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_006** | 2001-12-04 | `ENE` | `ENE R735QTJ8XC9X` | **+120.51%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_007** | 2002-07-03 | `WCOME`| `WCOM R735QTJ8XC9X`| **+120.00%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_008** | 2016-06-01 | `WCN` | `WCNX RB0Y4A7JXZDX` | **+112.53%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_009** | 2001-10-02 | `MFNX` | `MFNX R735QTJ8XC9X` | **+112.12%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_010** | 2020-03-24 | `MFA` | `MFA R9ULW9HANJHH` | **-86.69%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_011** | 2008-03-04 | `LCAPA`| `LCAPA TIIB7Z82AFS5`| **-84.99%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |
| **UNVER_012** | 2009-01-15 | `SSCC` | `JJSC R735QTJ8XC9X` | **-82.86%** | `UNVERIFIED_PRICE_SHOCK` | Giữ nguyên trong dữ liệu; Chế ngự bằng Uniform Rank Target |

#### Nguyên Tắc Liêm Chính Khoa Học (Academic Integrity Policy):
Tuân thủ nguyên tắc liêm chính học thuật: Khi chưa có tài liệu SEC Form 8-K hoặc thông cáo sàn giao dịch xác thực độc lập, chúng tôi **tuyệt đối không tự tiện gán nhãn là "đã xác nhận" (confirmed)**, mà gắn nhãn minh bạch `UNVERIFIED_PRICE_SHOCK`. Các biến cố này được giữ lại trong dữ liệu để bảo đảm tính khách quan, và mức độ ảnh hưởng của chúng được vô hiệu hóa tự nhiên thông qua chuẩn hóa mục tiêu Uniform Rank Target $[0, 1]$.

---

## 4. Phân Tích Độ Phân Tán Chéo (Cross-Sectional Dispersion) & Động Học Rổ Cổ Phiếu

### 4.1. Độ Phân Tán Chéo Của Thị Trường Qua Các Năm (Cross-Sectional Dispersion)

Độ phân tán chéo đo lường độ lệch chuẩn của lợi suất giữa các cổ phiếu trong cùng một phiên giao dịch:
$$\text{Dispersion}_t = \text{std}_{i \in \text{valid\_label}_t}(r_{i, t})$$

Dữ liệu từ `docs/Data report/market_data_audit/tables/eda_cross_sectional_dispersion.csv`:

| Năm Giao Dịch | Độ Phân Tán Trung Bình (Avg Dispersion) | Độ Phân Tán Đỉnh Điểm (Max Dispersion) | Độ Trải Giữa Trung Bình (Avg IQR) | Bối Cảnh Thị Trường Kinh Tế Vĩ Mô |
|:---:|:---:|:---:|:---:|:---|
| **2000** | **0.041681** (4.17%) | **0.080073** (8.01%) | 0.037206 | Sụp đổ bong bóng Dot-com; Cổ phiếu công nghệ phân hóa cực độ |
| **2001** | **0.036527** (3.65%) | **0.096669** (9.67%) | 0.030286 | Suy thoái kinh tế Mỹ và biến cố 11/09 |
| **2002** | **0.029596** (2.96%) | **0.059971** (6.00%) | 0.024868 | Đáy thị trường gấu và đại án WorldCom/Enron |
| **2005** | **0.015780** (1.58%) | **0.028860** (2.89%) | 0.013739 | Thị trường tăng trưởng bình lặng (Low Volatility Regime) |
| **2008** | **0.033422** (3.34%) | **0.083656** (8.37%) | 0.030871 | Đại khủng hoảng tài chính toàn cầu (GFC); Ngân hàng sụp đổ hàng loạt |
| **2009** | **0.027823** (2.78%) | **0.063239** (6.32%) | 0.026859 | Đáy khủng hoảng tháng 3/2009 và giai đoạn phục hồi ban đầu |
| **2013** | **0.014471** (1.45%) | **0.024940** (2.49%) | 0.012371 | Năm thị trường tăng trưởng kỷ lục, độ biến động chạm đáy |
| **2017** | **0.014866** (1.49%) | **0.030899** (3.09%) | 0.012547 | Năm có chỉ số VIX thấp nhất lịch sử tài chính |
| **2020** | **0.026133** (2.61%) | **0.097971** (9.80%) | 0.026816 | Đại dịch COVID-19; Độ phân tán phiên cao kỷ lục lịch sử (9.80%) |
| **2022** | **0.022599** (2.26%) | **0.047726** (4.77%) | 0.021425 | Chu kỳ thắt chặt tiền tệ quyết liệt của Fed và xung đột địa chính trị |
| **2023** | **0.020118** (2.01%) | **0.044095** (4.41%) | 0.017444 | Sự trỗi dậy của nhóm vốn hóa khổng lồ "Magnificent Seven" |

**Nhận định định lượng**: Độ phân tán chéo phản ánh cơ hội sinh lời của chiến lược Long-Short và mô hình xếp hạng. Trong các năm khủng hoảng (2000, 2008, 2020), độ phân tán mở rộng gấp 2.5–3 lần so với giai đoạn bình lặng, tạo ra biên độ phân hóa rất lớn cho các mô hình học máy khai thác tín hiệu phân biệt giữa cổ phiếu dẫn dắt (Top Rank) và cổ phiếu suy yếu (Bottom Rank).

### 4.2. Phân Tích Decile Thanh Khoản (Liquidity Deciles Analysis)

Dữ liệu từ `docs/Data report/market_data_audit/tables/eda_liquidity_deciles.csv`, phân chia rổ cổ phiếu thành 10 nhóm decile thanh khoản dựa trên giá trị giao dịch trung bình hàng ngày (Dollar Volume):

| Decile Thanh Khoản | Số Lượng Mã Trung Bình | Thị Giá Trung Vị (Median Price) | Độ Biến Động Năm Hóa Trung Bình (%) | Đặc Điểm Cấu Trúc Nhóm |
|:---:|:---:|:---:|:---:|:---|
| **D1 (Thấp nhất)** | 257 | $23.14 | **50.46%** | Vốn hóa nhỏ, thanh khoản mỏng, biến động cực cao, rủi ro trượt giá lớn |
| **D2** | 257 | $26.42 | **47.93%** | Nhóm Mid/Small-cap cận dưới |
| **D3** | 257 | $30.93 | **47.13%** | Nhóm vốn hóa trung bình |
| **D4** | 257 | $32.81 | **47.00%** | Nhóm vốn hóa trung bình |
| **D5** | 257 | $39.44 | **47.07%** | Cận trung vị của rổ Russell 1000 |
| **D6** | 257 | $39.39 | **50.18%** | Nhóm biến động đặc thù |
| **D7** | 257 | $43.40 | **44.84%** | Vốn hóa lớn, biến động bắt đầu giảm |
| **D8** | 257 | $43.45 | **48.20%** | Vốn hóa lớn |
| **D9** | 257 | $49.22 | **46.48%** | Nhóm Blue-chips thanh khoản cao |
| **D10 (Cao nhất)** | 257 | $52.80 | **47.23%** | Nhóm Mega-caps (Apple, Microsoft, Nvidia,...), thanh khoản dồi dào nhất |

---

## 5. Luận Giải Thiết Kế Mục Tiêu Mô Hình Machine Learning (Target Engineering)

Kết quả phân tích thống kê EDA tại Mục 2 đã chỉ ra một rào cản nền tảng: **Phân phối lợi suất cổ phiếu có Excess Kurtosis lên tới 66.88 và tồn tại các cú sốc cực đoan từ $-94.97\%$ đến $+227.87\%$**.

Nếu xây dựng mô hình dự đoán trực tiếp giá trị lợi suất tuyệt đối $\hat{r}_{i, t+1}$ bằng hàm mất mát sai số bình phương trung bình (Mean Squared Error — MSE):
$$\mathcal{L}_{\text{MSE}} = \frac{1}{N} \sum_{i=1}^N (r_{i, t+1} - \hat{r}_{i, t+1})^2$$
Một điểm dị biệt duy nhất như $r = +227.87\%$ (khoảng $86\sigma$) sẽ đóng góp một lượng gradient sai số gấp $(86)^2 \approx 7,400$ lần một mẫu thông thường, chi phối hoàn toàn việc cập nhật trọng số của cây quyết định (LightGBM/XGBoost) hoặc mạng nơ-ron, khiến mô hình bị mất ổn định nghiêm trọng.

### Giải Pháp Tối Ưu: Chuẩn Hóa Mục Tiêu Xếp Hạng Tỷ Đối (Cross-Sectional Uniform Rank Target)

Thay vì dự đoán lợi suất tuyệt đối, dự án thiết kế biến mục tiêu là **Xếp Hạng Tỷ Đối Đều (Uniform Rank Target)** được chuẩn hóa trên từng phiên giao dịch:
$$Y_{i, t} = \frac{\text{Rank}(r_{i, t+1}) - 1}{N_t - 1} \in [0.0, 1.0]$$
Trong đó:
- $N_t = \sum_{i} \text{valid\_label}_{i, t}$ là tổng số cổ phiếu hợp lệ trong phiên giao dịch $t$ (trung bình ~912 đến 987 mã).
- $\text{Rank}(r_{i, t+1})$ là thứ tự lợi suất tăng dần của cổ phiếu $i$ tại phiên $T+1$ (cổ phiếu giảm sâu nhất nhận Rank 1, cổ phiếu tăng mạnh nhất nhận Rank $N_t$).
- $Y_{i, t} = 0.0$: Cổ phiếu có hiệu suất kém nhất rổ trong phiên $T+1$ (Bottom 1).
- $Y_{i, t} = 1.0$: Cổ phiếu có hiệu suất tốt nhất rổ trong phiên $T+1$ (Top 1).

### Các Ưu Thế Toán Học Và Định Lượng Của Uniform Rank Target:
1. **Triệt tiêu hoàn toàn tác động của Fat Tails**:
   - Biến ngẫu nhiên $Y \sim \mathcal{U}[0, 1]$ tuân theo phân phối đều, có **Excess Kurtosis lý thuyết cố định bằng $-1.2$** và **Skewness bằng $0.0$**.
   - Mọi biến cố cực đoan dù là $+227\%$ hay $+1,000\%$ đều chỉ nhận giá trị cận biên trên bằng $1.0$, hoàn toàn không tạo ra bất kỳ đột biến gradient nào.
2. **Khắc phục hiện tượng bất biến phương sai thị trường (Non-stationarity of Volatility)**:
   - Trong phiên thị trường hoảng loạn (2008, 2020), khoảng cách lợi suất giữa Top và Bottom có thể lên tới $40\%$. Trong phiên thị trường bình lặng (2017), khoảng cách này chỉ là $4\%$.
   - Mục tiêu Uniform Rank $[0, 1]$ giữ nguyên thang đo đồng nhất $100\%$ qua mọi phiên giao dịch trong suốt 24 năm, giúp mô hình học được mối tương quan thứ hạng thực chất mà không bị méo mó theo chu kỳ biến động của vĩ mô.
3. **Phù hợp hoàn hảo với chiến lược giao dịch định lượng thực tế**:
   - Trong thực tế, các quỹ định lượng không cần biết một cổ phiếu sẽ tăng chính xác bao nhiêu phần trăm, mà cần biết **trong 1,000 cổ phiếu hôm nay, 10 cổ phiếu nào có xác suất cao nhất nằm trong Top 1% (Long Basket) và 10 cổ phiếu nào có nguy cơ nằm trong Bottom 1% (Short Basket)**.
   - Hàm mục tiêu xếp hạng tối ưu hóa trực tiếp độ đo tương quan thứ hạng Spearman Rank Correlation ($\text{Rank IC}$) và tỷ lệ lợi nhuận danh mục Long-Short.

---

## 6. Kết Luận Kỹ Thuật (Engineering Sign-off)

1. **Khẳng định tính lành mạnh dữ liệu**: Tập Development với 5,610,691 quan sát đã được làm sạch triệt để, các mômen phân phối đạt chuẩn mực tài chính định lượng với Kurtosis 66.88.
2. **Thấu hiểu toàn diện các cú sốc cực đoan**: Toàn bộ 34 ca biến cố cực biên đã được phân định rõ ràng giữa nến lỗi cần cách ly (13 ca), khủng hoảng thị trường thật cần giữ lại (9 ca), và các cú sốc chưa xác minh được kiểm soát bằng xếp hạng (12 ca).
3. **Cơ sở toán học vững chắc cho Bước 7**: Thiết kế biến mục tiêu Uniform Rank Target $[0, 1]$ giải quyết triệt để vấn đề fat tails, mở đường hoàn hảo cho giai đoạn thiết kế 16 đặc trưng định lượng tại Bước 7.

*(Báo cáo được hoàn thành và nghiệm thu kỹ thuật cho Milestone M3)*
