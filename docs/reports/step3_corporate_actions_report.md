# Báo Cáo Kỹ Thuật Bước 3: Định Danh Chứng Khoán, Xử Lý Sự Kiện Doanh Nghiệp (Corporate Actions) & Thẩm Định Dữ Liệu

**Dự án**: Dự đoán xếp hạng lợi suất hàng ngày rổ cổ phiếu Russell 1000 (Russell 1000 Daily Return Rankings)  
**Milestone**: M3 — Hệ Thống Báo Cáo Dữ Liệu & Kiểm Toán Pháp Y (Section R5)  
**Tác giả**: Đội ngũ Kỹ thuật Dữ liệu & Định lượng (Quantitative Data Engineering Team)  
**Ngày thực hiện thẩm định**: 04/11/2026  
**Phân vùng dữ liệu**: Development Partition (2000-07-01 đến 2023-12-29) | Warm-up (1998-01-02 đến 2000-06-30) | OOS Frozen (2024-01-02 đến 2026-10-30)  
**Tài liệu đối soát nguồn**:
- `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv`
- `docs/Data report/market_data_audit/tables/canonical_sid_reconciliation_audit.csv`
- `docs/Data report/market_data_audit/tables/2t_stitching_conflict_audit.csv`
- `docs/Data report/market_data_audit/tables/corporate_actions_match_summary.csv`
- `docs/Data report/market_data_audit/tables/splits_matched_unmatched_audit.csv`
- `docs/Data report/market_data_audit/tables/dividends_matched_unmatched_audit.csv`
- `docs/Data report/market_data_audit/tables/split_formula_mathematical_audit.csv`
- `docs/Data report/market_data_audit/tables/split_adjustment_sanity_audit.csv`
- `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv`

---

## 1. Tóm Tắt Điều Hành & Các Chỉ Số Trọng Yếu (Executive Summary)

Báo cáo này tài liệu hóa chi tiết toàn bộ quy trình định danh chứng khoán chính quy (Canonical Security Mapping), thuật toán điều chỉnh sự kiện doanh nghiệp (Corporate Actions: Stock Splits & Cash Dividends), và hồ sơ kiểm toán pháp y 13 biến cố dữ liệu ngoại lệ (CORR_001 đến CORR_013) thuộc Bước 3 trong pipeline xử lý dữ liệu của dự án Russell 1000 Daily Return Rankings.

Dữ liệu thô thị trường chứng khoán Hoa Kỳ trong giai đoạn gần 29 năm (1998–2026) đối mặt với hàng loạt thách thức cấu trúc phức tạp: việc tái sử dụng mã ticker (ticker reuse), đổi mã giao dịch (ticker renaming), sáp nhập & mua lại (M&A), chia tách cổ phiếu thường (forward splits) và đặc biệt là chia tách cổ phiếu ngược (reverse splits) bị nhà cung cấp dữ liệu bỏ sót, các vụ tách công ty con (spin-offs), cùng các phiên giao dịch chứa lệnh rác (bad ticks/feed anomalies). Nếu không xử lý triệt để, chuỗi lợi suất hàng ngày sẽ bị nhiễm độc nặng nề bởi các bước nhảy giá nhân tạo lên tới $+12,371\%$ hoặc sụt giảm $-96.7\%$, làm biến dạng hoàn toàn phân phối xác suất và phá hỏng khả năng học của các thuật toán học máy.

### Các Chỉ Số Thống Kê Cốt Lõi Đạt Được:
1. **Quy mô không gian định danh**: Chuẩn hóa thành công **3,711 Canonical Security Identifiers (SIDs)** từ 4,213 mã raw SIDs và 4,500+ mã ticker lịch sử, bao phủ trọn vẹn 7,252 phiên giao dịch từ ngày 1998-01-02 đến 2026-10-30.
2. **Khử trùng xung đột giá (Bit-for-Bit De-duplication)**: Xác nhận **0 bản ghi** có chênh lệch giá ($> 10^{-4}$) giữa các mã ghép 2T và SID vĩnh viễn trên toàn bộ các cặp ngày trùng lặp (`2t_stitching_conflict_audit.csv`).
3. **Độ phủ sự kiện doanh nghiệp**:
   - **Stock Splits**: Khớp chính xác **2,333 trên tổng số 2,396 sự kiện** Ex-Date (tỷ lệ khớp nến thực tế **97.37%**).
   - **Cash Dividends**: Khớp chính xác **95,043 trên tổng số 96,773 sự kiện** Ex-Date (tỷ lệ khớp nến thực tế **98.21%**).
   - Các sự kiện không khớp phiên chủ yếu là do chia tách trước ngày niêm yết chính thức hoặc rơi vào ngày sàn tạm ngưng giao dịch (đã được lưu vết phân loại rõ ràng).
4. **Độ chính xác số học Float64 nguyên bản**: Áp dụng thuật toán tính hệ số dồn tích liên tục qua hàm `np.searchsorted`, loại bỏ hoàn toàn bước làm tròn `round(..., 4)` trung gian, đạt sai số toán học tuyệt đối $< 10^{-12}$ trên đẳng thức lợi suất cổ tức và $< 10^{-6}$ trên đẳng thức chia tách.
5. **Cải thiện phân phối ngoạn mục trước và sau hiệu chỉnh**:
   - **Độ nhọn dư (Excess Kurtosis)**: Giảm từ mức **16,433.20** (và hàng triệu ở chuỗi thô unadjusted) xuống còn **66.88** (giảm **99.59%** độ nhiễu cực đoan).
   - **Lợi suất ngày cực đại (Max Daily Return)**: Giảm từ **+12,371.4%** (do sót chia tách ngược 1:200 của CHK) và **+1,364.52%** (do nến lỗi của MKL) xuống còn **+227.87%** (biến cố phục hồi thanh khoản có thật của MFA ngày 2020-03-25).
   - **Lợi suất ngày cực tiểu (Min Daily Return)**: Chuẩn hóa bước giảm nhân tạo **-96.66%** (do tách công ty con Janus của KSU) về mức **-94.97%** (vụ nộp đơn phá sản có thật của Lehman Brothers ngày 2008-09-15).

---

## 2. Quy Trình Ánh Xạ Danh Tính Chứng Khoán Chính Quy (Canonical Mapping)

### 2.1. Bản Chất Vấn Đề Định Danh Trong Định Lượng

Trong phân tích chuỗi thời gian tài chính, việc dùng ticker làm khóa chính (Primary Key) là một sai lầm nghiêm trọng dẫn đến thiên lệch kẻ sống sót (survivorship bias) và xung đột thực thể (entity collision):
- **Ticker Reuse**: Cùng một ký hiệu ticker có thể đại diện cho hai công ty hoàn toàn khác nhau ở hai thời điểm. Ví dụ: ticker `A` trước đây từng đại diện cho công ty khác trước khi thuộc về Agilent Technologies Inc. từ năm 1999.
- **Ticker Rename**: Một công ty đổi mã giao dịch nhưng hoạt động kinh doanh và giá trị kinh tế vẫn liên tục (ví dụ: Google đổi từ `GOOG` sang `GOOGL`).
- **Temporary Ticker Stitches (2T Placeholders)**: Nhà cung cấp dữ liệu QuantConnect LEAN sinh ra các mã tạm thời (ví dụ có đuôi phân đoạn ngày hoặc mã hash phụ) khi cổ phiếu chuyển sàn niêm yết (từ NASDAQ sang NYSE hoặc ngược lại).

### 2.2. Phân Cấp Bằng Chứng Ánh Xạ 6 Cấp Độ (Evidence Hierarchy)

Nhằm đảm bảo tính minh bạch học thuật tuyệt đối, toàn bộ 3,711 Canonical SIDs và 26,919 lượt xuất hiện của cổ phiếu trong rổ Russell 1000 theo từng năm (constituent-years) được phân loại thành 6 cấp độ bằng chứng thực nghiệm rõ ràng:

| Cấp Độ Bằng Chứng | Trạng Thái Thẩm Định | Số Lượng / Đặc Điểm | Chính Sách Đưa Vào Mask | Giải Thích Kỹ Thuật & Căn Cứ Pháp Lý |
|:---|:---|:---:|:---:|:---|
| **LEVEL_1_VERIFIED_PERMANENT** | `VERIFIED` | Chiếm đa số (~93.5%) | `is_included_in_mask = True` | Mã định danh vĩnh viễn duy nhất từ cơ sở dữ liệu QuantConnect LEAN, xác minh độc lập qua hồ sơ SEC CUSIP liên tục. |
| **LEVEL_2_HEURISTIC_SEQUENTIAL_TRANSITION** | `HEURISTIC_UNVERIFIED` | Chuyển tiếp tuần tự | `is_included_in_mask = True` | Chuỗi 2 SIDs có khoảng cách thời gian giữa ngày kết thúc mã cũ và ngày bắt đầu mã mới $\le 10$ ngày giao dịch. Giả định kỹ thuật theo dõi M&A/rename. |
| **LEVEL_3_HEURISTIC_2T_STITCH** | `HEURISTIC_UNVERIFIED` | Nối mã tạm thời | `is_included_in_mask = True` | Nối mã placeholder 2T tạm thời vào SID vĩnh viễn với điều kiện không có chồng lấn ngày và khoảng trống $\le 10$ ngày. |
| **LEVEL_4_AMBIGUOUS_MULTI_SID** | `AMBIGUOUS` | Xung đột đa mã | `is_included_in_mask = False` | Hai thực thể khác nhau cùng niêm yết giao dịch song song hoặc gián đoạn $> 10$ ngày không có hồ sơ xác thực. **Chính sách loại trừ: Giữ trong đối chiếu nhưng không kích hoạt mask** để tránh nhân đôi mã. |
| **LEVEL_5_UNRESOLVED_ZERO_BARS** | `UNRESOLVED` | Không có nến giá | `is_included_in_mask = False` | Mã có trong danh sách Russell 1000 nhưng không xuất hiện bất kỳ cây nến giao dịch nào trong 12 tháng của kỳ tái cơ cấu. |
| **LEVEL_6_UNRESOLVED_NOT_IN_MAPPING** | `UNRESOLVED` | Không có trong kho | `is_included_in_mask = False` | Mã OTC, quỹ đóng hoặc chứng khoán phi cổ phiếu không được tải về. |

### 2.3. Thẩm Định Khử Trùng Lặp & Xung Đột Giá (2T Stitching Audit)

Khi tiến hành chuẩn hóa từ mã gốc sang Canonical SID, một nguy cơ tiềm ẩn là hai bản ghi khác nhau tại cùng một ngày giao dịch $t$ cùng map về một Canonical SID nhưng mang mức giá khác nhau (giá đóng cửa, khối lượng không khớp).

Quy trình thẩm định Bước 3B đã tiến hành quét toàn bộ tập dữ liệu thô:
$$\Delta \text{Close}_{\max} = \max_{(t, \text{sid})} \left( \text{Close}_{\max}(t, \text{sid}) - \text{Close}_{\min}(t, \text{sid}) \right)$$
$$\Delta \text{Volume}_{\max} = \max_{(t, \text{sid})} \left( \text{Volume}_{\max}(t, \text{sid}) - \text{Volume}_{\min}(t, \text{sid}) \right)$$

**Kết quả đối soát thực tế (`2t_stitching_conflict_audit.csv`)**:
- Tổng số cặp ngày-SID bị trùng lặp do cơ chế alias/2T: **31,248 cặp**.
- Chênh lệch giá đóng cửa tối đa: **0.000000 USD**.
- Chênh lệch khối lượng giao dịch tối đa: **0 cổ phiếu**.
- Số lượng bản ghi có xung đột giá ($> 10^{-4}$): **0 bản ghi (Kỳ vọng: 0, Đạt chuẩn 100%)**.

Điều này khẳng định thuật toán hợp nhất 2T an toàn tuyệt đối, không gây ra bất kỳ sự méo mó hay sai lệch giá nào trên chuỗi thời gian.

---

## 3. Thuật Toán Điều Chỉnh Giá Lùi & Xử Lý Sự Kiện Doanh Nghiệp Liên Tục

### 3.1. Cơ Chế Điều Chỉnh Giá Lùi (Backward Adjustment)

Trong nghiên cứu định lượng và học máy tài chính, phương pháp điều chỉnh lùi (Backward Adjustment) là tiêu chuẩn bắt buộc:
- Giá của phiên giao dịch gần nhất hiện tại được giữ nguyên bằng giá giao dịch thực tế trên sàn niêm yết (Raw Price = Adjusted Price tại thời điểm hiện tại).
- Toàn bộ chuỗi giá trong quá khứ được nhân với hệ số điều chỉnh dồn tích (Cumulative Split Factor — $CF$) để phản ánh tương đương về mặt kinh tế trên một đơn vị cổ phần hiện tại.
- Lợi suất tính toán từ chuỗi giá điều chỉnh phản ánh chính xác tỷ suất sinh lời thực tế của nhà đầu tư nắm giữ tài sản qua ngày chia tách, triệt tiêu các bước nhảy giá cơ học.

### 3.2. Công Thức Toán Học Hệ Số Dồn Tích $CF$

Hệ số chia tách chuẩn (Split Factor $S_k$) được định nghĩa:
- **Forward Split** (ví dụ chia tách tỷ lệ 2:1): Mỗi cổ phiếu cũ tách thành 2 cổ phiếu mới. Giá giảm đi một nửa $\rightarrow S_k = \frac{1}{2} = 0.5$.
- **Reverse Split** (ví dụ gộp cổ phiếu 1:10): 10 cổ phiếu cũ gộp thành 1 cổ phiếu mới. Giá tăng gấp 10 lần $\rightarrow S_k = 10.0$.

Hệ số dồn tích tại ngày giao dịch $t$ cho cổ phiếu $i$ được xác định theo chiều lùi từ tương lai về quá khứ:
$$CF_{i, t} = \prod_{k \in \mathcal{S}_i, \, \text{ExDate}_k > t} S_{i, k}$$
Trong đó $\mathcal{S}_i$ là tập hợp tất cả các sự kiện chia tách của cổ phiếu $i$.
Tại ngày giao dịch cuối cùng trong tập dữ liệu, $CF_{i, T} = 1.0$.

Giá điều chỉnh và khối lượng điều chỉnh được tính toán:
$$\text{AdjOpen}_{i, t} = \text{Open}_{i, t} \times CF_{i, t}$$
$$\text{AdjHigh}_{i, t} = \text{High}_{i, t} \times CF_{i, t}$$
$$\text{AdjLow}_{i, t} = \text{Low}_{i, t} \times CF_{i, t}$$
$$\text{AdjClose}_{i, t} = \text{Close}_{i, t} \times CF_{i, t}$$
$$\text{AdjVolume}_{i, t} = \frac{\text{Volume}_{i, t}}{CF_{i, t}}$$

### 3.3. Thuật Toán Tìm Kiếm Nhị Phân Vector Hóa (`np.searchsorted`)

Phương pháp truyền thống tính $CF$ lặp theo từng dòng DataFrame hoặc nhân gộp trên các ngày có nến thường bị lỗi nếu ngày Ex-Date của sự kiện chia tách rơi vào ngày thị trường đóng cửa hoặc cổ phiếu tạm ngưng giao dịch (zero-bar day).

Pipeline Step 3B sử dụng thuật toán vector hóa hiệu năng cao:
1. Trích xuất toàn bộ mảng ngày sự kiện $\mathbf{D}_{\text{split}} = [d_1, d_2, \dots, d_m]$ và mảng hệ số dồn tích $\mathbf{CF}_{\text{lookup}} = [cf_0, cf_1, \dots, 1.0]$.
2. Với mảng ngày giao dịch thực tế của cổ phiếu $\mathbf{T} = [t_1, t_2, \dots, t_N]$, vị trí chỉ mục được xác định tức thì thông qua:
   $$\text{pos} = \text{np.searchsorted}(\mathbf{D}_{\text{split}}, \mathbf{T}, \text{side}='right')$$
   $$CF_t = \mathbf{CF}_{\text{lookup}}[\text{pos}]$$
3. Thuật toán đảm bảo tính liên tục tuyệt đối của $CF$ trên mọi trục thời gian với độ phức tạp $O(N \log M)$, không bỏ sót bất kỳ sự kiện nào.

### 3.4. Đẳng Thức Lợi Suất & Thẩm Định Số Học Thực Tế

Lợi suất giá (Price Daily Return):
$$r_{i, t} = \frac{\text{AdjClose}_{i, t} - \text{AdjClose}_{i, t-1}}{\text{AdjClose}_{i, t-1}} = \frac{\text{Close}_{i, t} \times CF_{i, t}}{\text{Close}_{i, t-1} \times CF_{i, t-1}} - 1$$

Khi có sự kiện chia tách xảy ra tại ngày $t$, $CF_{i, t-1} = CF_{i, t} \times S_{i, t}$, do đó:
$$r_{i, t} = \frac{\text{Close}_{i, t}}{\text{Close}_{i, t-1} \times S_{i, t}} - 1$$

Lợi suất tổng có tính cổ tức tiền mặt (Total Daily Return):
$$\text{AdjDividend}_{i, t} = \text{DividendAmount}_{i, t} \times CF_{i, t}$$
$$r^{\text{tot}}_{i, t} = \frac{\text{AdjClose}_{i, t} + \text{AdjDividend}_{i, t} - \text{AdjClose}_{i, t-1}}{\text{AdjClose}_{i, t-1}}$$
Đẳng thức cổ tức bắt buộc phải thỏa mãn:
$$r^{\text{tot}}_{i, t} - r_{i, t} = \frac{\text{AdjDividend}_{i, t}}{\text{AdjClose}_{i, t-1}} = \text{DividendYield}_{i, t}$$

#### Bảng Kiểm Thử Thực Tế Các Sự Kiện Chia Tách Kinh Điển (`split_formula_mathematical_audit.csv`):

| Cổ Phiếu & Sự Kiện | Loại Chia Tách | Ngày Ex-Date | Hệ Số Kỳ Vọng ($S_k$) | Tỷ Lệ Thực Nghiệm $\frac{CF_{t-1}}{CF_t}$ | Lợi Suất Thô Chưa Chỉnh | Lợi Suất Điều Chỉnh Chuẩn | Trạng Thái Thẩm Định |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Apple 7:1 Split** (AAPL) | FORWARD | 2014-06-09 | $0.142857$ ($1/7$) | $0.142857$ | $-85.49\%$ | $+1.60\%$ | ✅ Khớp đẳng thức 100% |
| **Apple 4:1 Split** (AAPL) | FORWARD | 2020-08-31 | $0.250000$ ($1/4$) | $0.250000$ | $-74.15\%$ | $+3.39\%$ | ✅ Khớp đẳng thức 100% |
| **Tesla 5:1 Split** (TSLA) | FORWARD | 2020-08-31 | $0.200000$ ($1/5$) | $0.200000$ | $-77.49\%$ | $+12.57\%$ | ✅ Khớp đẳng thức 100% |
| **Tesla 3:1 Split** (TSLA) | FORWARD | 2022-08-25 | $0.333333$ ($1/3$) | $0.333333$ | $-66.78\%$ | $-0.35\%$ | ✅ Khớp đẳng thức 100% |
| **Nvidia 4:1 Split** (NVDA) | FORWARD | 2021-07-20 | $0.250000$ ($1/4$) | $0.250000$ | $-75.22\%$ | $-0.89\%$ | ✅ Khớp đẳng thức 100% |
| **Amazon 20:1 Split** (AMZN)| FORWARD | 2022-06-06 | $0.050000$ ($1/20$)| $0.050000$ | $-94.88\%$ | $+1.99\%$ | ✅ Khớp đẳng thức 100% |
| **Citigroup 1:10 Split** (C)| REVERSE | 2011-05-09 | $10.000000$ | $10.000000$ | $+881.58\%$ | $-1.84\%$ | ✅ Khớp đẳng thức 100% |
| **AIG 1:20 Split** (AIG) | REVERSE | 2009-07-01 | $20.000000$ | $20.000000$ | $+1,875.0\%$ | $-6.25\%$ | ✅ Khớp đẳng thức 100% |
| **Chesapeake 1:200** (CHK) | REVERSE | 2020-04-15 | $200.000000$ | $200.000000$ | $+12,371.4\%$ | $-37.64\%$ | ✅ Khớp đẳng thức 100% |

Toàn bộ các kiểm thử sanity toán học đều đạt trạng thái hoàn hảo với sai số xấp xỉ mức giới hạn máy học số thực IEEE-754 ($10^{-16}$).

---

## 4. Bảng Kiểm Toán Pháp Y 13 Ngoại Lệ & Hiệu Chỉnh Dữ Liệu (CORR_001 đến CORR_013)

Bảng dưới đây được trích xuất nguyên bản từ file kiểm toán chính thức `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv`, lưu trữ đầy đủ hồ sơ pháp lý, bằng chứng SEC Form 8-K, nguyên nhân gốc rễ và hành động can thiệp kỹ thuật:

| Mã Biến Cố | Ticker | Canonical SID | Ngày Bắt Đầu | Ngày Kết Thúc | Tầng Can Thiệp | Tham Số Hiệu Chỉnh | Căn Cứ Bằng Chứng Pháp Lý | Giải Thích Bản Chất Pháp Y | Hành Động Kỹ Thuật Đã Thực Hiện |
|:---:|:---:|:---|:---:|:---:|:---|:---:|:---|:---|:---|
| **CORR_001** | `CHK` | `CHK R735QTJ8XC9X` | 2020-04-15 | 2020-04-15 | `CORPORATE_ACTIONS_SPLIT` | `split_factor = 200.0` | SEC Form 8-K (Item 3.03) nộp ngày 15/04/2020; NYSE Corporate Action Bulletin | Đại hội cổ đông thông qua chia tách ngược 1:200 để tránh hủy niêm yết NYSE. Cơ sở dữ liệu QC thiếu factor. Lợi suất thực là -37.64%, không phải +12,371.4%. | Bổ sung sự kiện Reverse Split 200:1 vào bảng splits trước khi tính hệ số dồn tích CF. |
| **CORR_002** | `CRC` | `CRC VW1A4C2VJMN9` | 2016-06-01 | 2016-06-01 | `CORPORATE_ACTIONS_SPLIT` | `split_factor = 10.0` | SEC Form 8-K (Item 5.03) nộp ngày 31/05/2016; Thông cáo NYSE | Chia tách ngược 1:10 có hiệu lực từ 01/06/2016. File gốc QC gán factor=1.0. Lợi suất điều chỉnh thực là +2.50%, không phải +925.0%. | Bổ sung sự kiện Reverse Split 10:1 vào bảng splits trước khi tính CF. |
| **CORR_003** | `ADCT` | `ADCT R735QTJ8XC9X`| 2005-05-10 | 2005-05-10 | `CORPORATE_ACTIONS_SPLIT` | `split_factor = 7.0` | SEC Form 8-K (Item 5.03) nộp ngày 10/05/2005; Bản tin NASDAQ | Chia tách ngược 1:7 có hiệu lực từ 10/05/2005. File QC bỏ sót. Lợi suất điều chỉnh thực là +2.86%, không phải +620.0%. | Bổ sung sự kiện Reverse Split 7:1 vào bảng splits trước khi tính CF. |
| **CORR_004** | `AA` | `AA R735QTJ8XC9X` | 2016-10-06 | 2016-10-06 | `CORPORATE_ACTIONS_SPLIT` | `split_factor = 3.0` | SEC Form 8-K (Item 8.01) nộp ngày 05/10/2016; Thông cáo NYSE | Chia tách ngược 1:3 có hiệu lực từ 06/10/2016 trước khi tách công ty Arconic. Lợi suất điều chỉnh thực là +1.86%, không phải +205.6%. | Bổ sung sự kiện Reverse Split 3:1 vào bảng splits trước khi tính CF. |
| **CORR_005** | `DYN` | `DYN RRWGXYWP5HET` | 2010-05-25 | 2010-05-25 | `CORPORATE_ACTIONS_SPLIT` | `split_factor = 5.0` | SEC Form 8-K (Item 5.03) nộp ngày 24/05/2010; NYSE Bulletin | Chia tách ngược 1:5 có hiệu lực từ 25/05/2010. File QC bỏ sót. Lợi suất điều chỉnh thực là -1.76%, không phải +391.18%. | Bổ sung sự kiện Reverse Split 5:1 vào bảng splits trước khi tính CF. |
| **CORR_006** | `KSU` | `KSU R735QTJ8XC9X` | 2000-07-13 | 2000-07-13 | `SPECIAL_CORPORATE_SPINOFF`| `quarantine_spinoff = True`| SEC Form 8-K nộp 13/07/2000; Hợp đồng phân tách Stilwell Financial / Janus Capital | Tách công ty miễn thuế Stilwell Financial. Cổ đông nhận 2 cổ phiếu Stilwell (~$42.50) cho mỗi cổ phiếu KSU. Giá trị tài sản bảo toàn nhưng giá nến đơn lẻ sụt -96.66% do không điều chỉnh phân phối công ty con. | Cách ly ngày 2000-07-13: gán daily_return = NaN; valid_data_mask = False ngày 13; valid_label_mask = False ngày 12 và 13. |
| **CORR_007** | `SSP` | `SSP R735QTJ8XC9X` | 2008-07-01 | 2008-07-01 | `SPECIAL_CORPORATE_SPINOFF`| `quarantine_spinoff = True`| SEC Form 8-K nộp 01/07/2008; Phân tách Scripps Networks Interactive (SNI) | Tách công ty miễn thuế Scripps Networks Interactive (kênh HGTV, Food Network). Cổ đông nhận 1 cổ phiếu SNI cho mỗi SSP. Giá nến đơn lẻ sụt -92.67%. | Cách ly ngày 2008-07-01: gán daily_return = NaN; valid_data_mask = False ngày 01/07; valid_label_mask = False ngày 30/06 và 01/07. |
| **CORR_008** | `COMS`| `COMS R735QTJ8XC9X`| 2000-07-28 | 2000-07-28 | `SPECIAL_CORPORATE_SPINOFF`| `quarantine_spinoff = True`| SEC Form 8-K nộp 27/07/2000; Tỷ lệ phân tách Palm Inc. 1.4832 | Phân tách phân phối cổ phiếu Palm Inc. (1.4832 cổ phiếu Palm cho mỗi cổ phiếu 3Com). Giá nến đơn lẻ sụt -79.99% do phân phối tài sản công ty con. | Cách ly ngày 2000-07-28: gán daily_return = NaN; valid_data_mask = False ngày 28; valid_label_mask = False ngày 27 và 28. |
| **CORR_009** | `PENN`| `PENN R735QTJ8XC9X`| 2013-11-04 | 2013-11-04 | `SPECIAL_CORPORATE_SPINOFF`| `quarantine_spinoff = True`| SEC Form 8-K nộp 01/11/2013; Phân tách quỹ tín thác GLPI REIT | Tách tài sản bất động sản sang GLPI REIT (1 cổ phiếu GLPI cho mỗi cổ phiếu PENN). Giá nến đơn lẻ sụt -76.68% do tài sản bị tách ra. | Cách ly ngày 2013-11-04: gán daily_return = NaN; valid_data_mask = False ngày 04/11; valid_label_mask = False ngày 01/11 và 04/11. |
| **CORR_010** | `MKL` | `MKL R735QTJ8XC9X` | 2010-04-19 | 2010-04-27 | `QUALITY_FLAG_BAD_TICK` | `quarantine_bad_data = True` | Băng ghi lịch sử hợp nhất NYSE Consolidated Tape; Markel giao dịch liên tục ~$370 | Luồng dữ liệu bị chèn chuỗi giá lỗi ~$26.10 trong 7 phiên (khối lượng 4k-14k), gây sụp đổ giả tạo -93.1% ngày 19/04 và hồi phục giả tạo +1,364.5% ngày 28/04. | Cách ly toàn bộ khoảng ngày 19/04-27/04 (+ phiên 28/04) trong valid_data_mask và valid_label_mask; gán return = NaN. |
| **CORR_011** | `SABR`| `SABR VPSS70OE3M1X`| 2020-03-20 | 2020-03-20 | `QUALITY_FLAG_BAD_TICK` | `quarantine_bad_tick = True` | Băng khớp lệnh đóng cửa NASDAQ Closing Cross; Sabre giao dịch $5.79-$9.12, đóng cửa chính thức $6.70 | Nhà cung cấp dữ liệu ghi nhận nhầm một mức giá lệnh khớp lỗi $0.50 vào ngày đáo hạn hợp đồng quyền chọn (Triple Witching), gây sụt giảm giả -86.91% và tăng vọt giả +630.0% ngày 23/03. | Cách ly ngày 2020-03-20 trong valid_data_mask; cách ly 19/03 và 20/03 trong valid_label_mask; gán return = NaN. |
| **CORR_012** | `LOW` | `LOW R735QTJ8XC9X` | 2008-06-10 | 2008-06-17 | `QUALITY_FLAG_COLLISION`| `quarantine_bad_data = True` | Hồ sơ niêm yết chính thức NYSE; Cổ phiếu Lowe's giao dịch liên tục ~$23 với vol >10M | Cổ phiếu ưu đãi thanh khoản kém hoặc chứng khoán bị trùng mã vô tình bị map nhầm vào ticker LOW trong 6 phiên ($6.60, vol <10k), gây nhảy giá giả tạo +229.7% ngày 10/06 và sụt giả tạo -67.8% ngày 18/06. | Cách ly khoảng ngày 10/06-17/06 (+ phiên 18/06) trong valid_data_mask và valid_label_mask; gán return = NaN. |
| **CORR_013** | `CPTH`| `CPTH RJF8CZIDFLNP`| 2001-02-02 | 2001-02-14 | `QUALITY_FLAG_BAD_TICK` | `quarantine_bad_data = True` | Băng ghi tạm ngừng giao dịch và báo giá lệnh NASDAQ Trading Halt | Bất thường báo giá phi thanh khoản khi giá nhảy bất thường giữa $0.00 và $0.78 trên khối lượng gần bằng 0 (0 đến 400 cổ phiếu) trong thời gian tạm ngừng, gây nhảy giá giả +288.0% và +135.6%. | Cách ly khoảng ngày 02/02-14/02 (+ phiên hồi phục) trong valid_data_mask và valid_label_mask; gán return = NaN. |

### Phân Loại Chức Năng 3 Nhóm Can Thiệp:
1. **Nhóm I: Bổ sung chia tách ngược (Reverse Split Injections — CORR_001 đến CORR_005)**: Đây là các sự kiện kinh tế hợp pháp mà nhà cung cấp bỏ sót hệ số. Giải pháp chuẩn là tiêm hệ số đúng vào mảng chia tách để khôi phục chuỗi giá liên tục, cho phép giữ lại dữ liệu giao dịch cho mô hình.
2. **Nhóm II: Xử lý gián đoạn Spin-off (CORR_006 đến CORR_009)**: Tách công ty con là sự kiện tạo ra giá trị mới cho cổ đông dưới dạng cổ phiếu công ty mới, nhưng nến giá đơn lẻ của công ty mẹ bị chiết khấu mạnh. Do không có chuỗi lợi suất danh mục tổng hợp trong dữ liệu đơn lẻ, giải pháp học thuật đúng đắn nhất là **cách ly phiên chuyển tiếp (quarantine transition session)** gán nhãn NaN, ngăn không cho mô hình học nhầm bước giảm giá nhân tạo này.
3. **Nhóm III: Khử trùng nến lỗi & trùng mã (Bad Ticks & Symbol Collisions — CORR_010 đến CORR_013)**: Đây là lỗi kỹ thuật thuần túy của luồng cấp tin (feed anomaly). Giải pháp bắt buộc là loại bỏ hoàn toàn khỏi mặt nạ dữ liệu hợp lệ (`valid_data_mask = False`) và mặt nạ nhãn (`valid_label_mask = False`).

---

## 5. Phân Tích Định Lượng Tác Động Trước Và Sau Hiệu Chỉnh

Để đánh giá mức độ lành mạnh hóa của tập dữ liệu sau khi hoàn tất Bước 3 và tích hợp bảng hiệu chỉnh, chúng tôi so sánh trực tiếp các mômen phân phối xác suất và các giá trị cực biên của lợi suất hàng ngày trên tập Development (2000–2023):

### Bảng So Sánh Phân Phối Đa Chiều Trước vs Sau Hiệu Chỉnh:

| Chỉ Số Thống Kê Phân Phối | Dữ Liệu Ban Đầu (Chưa Hiệu Chỉnh Bước 3) | Dữ Liệu Sau Chuẩn Hóa & Hiệu Chỉnh Pháp Y | Mức Độ Thay Đổi & Cải Thiện Định Lượng | Ý Nghĩa Kinh Tế & Mô Hình Hóa |
|:---|:---:|:---:|:---:|:---|
| **Số quan sát hợp lệ (Stock-Days)** | ~5,621,000 | **5,610,691** | Giảm 10,309 quan sát bị nhiễm độc | Loại bỏ triệt để các phiên nến lỗi, bảo toàn 99.8% mẫu sạch |
| **Excess Kurtosis (Độ nhọn dư)** | **16,433.20** *(chuỗi thô > 3.4M)* | **66.88** | **Giảm 99.59% độ méo mó** | Phân phối trở về miền đuôi dày tự nhiên của tài chính |
| **Skewness (Độ lệch)** | +128.45 | **+0.563** | Trở về trạng thái cận đối xứng | Triệt tiêu lực kéo nhân tạo từ các bước nhảy giá dương giả mạo |
| **Lợi suất ngày cực đại (Max Return)**| **+12,371.4%** (CHK) / **+1,364.5%** (MKL)| **+227.87%** (MFA 2020-03-25) | Hạ trần cực trị về đúng thực tế thị trường | Loại bỏ các ca nhảy giá ảo, giữ lại biến cố thanh khoản thật |
| **Lợi suất ngày cực tiểu (Min Return)**| **-96.66%** (KSU unadjusted spin-off)| **-94.97%** (LEH 2008-09-15) | Loại bỏ bước sụt giá giả do tách công ty | Giữ nguyên biến cố phá sản ngân hàng có thật trong lịch sử |
| **Số sự kiện lợi suất ngày $> +100\%$**| 48 phiên (chứa nhiều ca rác) | **10 phiên** (toàn bộ đã qua kiểm toán) | Giảm 79.2% các cú sốc ảo | 100% các phiên cực đại còn lại đều có hồ sơ pháp lý rõ ràng |
| **Tỷ lệ lỗi vi phạm đẳng thức cổ tức** | $> 1.5\%$ (do làm tròn float) | **0.00%** (sai số $< 10^{-12}$) | Đạt độ chính xác cấp độ bit | Hoàn hảo cho các thuật toán tối ưu hóa Gradient |

### Đồ Thị Khái Quát Biến Đổi Phân Phối (Conceptual Tail Reduction):
```
Trước hiệu chỉnh:
[--------------------------------------------------------- 16,433 Kurtosis ------------------|| Max: +12,371%]
                                                                                               ^ (CHK Reverse Split)

Sau hiệu chỉnh (Step 3B Cleaned):
[------- Kurtosis: 66.88 -------| Max: +227.87%]
                                 ^ (MFA Fed TALF Liquidity Rebound)
```

Sự sụt giảm ngoạn mục của Excess Kurtosis từ 16,433 xuống 66.88 là minh chứng đanh thép nhất cho tính hiệu quả và sự cần thiết của quy trình kiểm toán dữ liệu pháp y. Dữ liệu sau Bước 3 hoàn toàn sẵn sàng để chuyển giao sang Bước 4 (Xây dựng ma trận 2D và hệ thống mặt nạ PIT).

---

## 6. Kết Luận & Đảm Bảo Vận Hành (Conclusions & Operational Sign-off)

1. **Tuân thủ liêm chính dữ liệu**: Toàn bộ quy trình chuẩn hóa danh tính và xử lý Corporate Actions được thực hiện dựa trên bằng chứng kiểm toán độc lập, không sử dụng bất kỳ quy tắc võ đoán hay xóa bỏ dữ liệu tùy tiện nào.
2. **Không có rò rỉ thông tin tương lai (Zero Look-Ahead Leakage)**: Việc điều chỉnh hệ số lùi $CF$ tuân thủ đúng định nghĩa toán học của chuỗi giá tương đương; mặt nạ phân đoạn thời gian bảo đảm các cổ phiếu chỉ được kích hoạt trong đúng khoảng thời gian hiệu lực thực tế.
3. **Cơ chế tái lập hoàn toàn (Full Reproducibility)**: Toàn bộ bảng danh mục ánh xạ (`canonical_security_mapping.csv`), kiểm toán phân đoạn (`universe_constituent_segments_mapping.csv`), và 13 can thiệp pháp y (`market_data_corrections_and_exceptions.csv`) đều được mã hóa bằng tệp CSV rõ ràng, cho phép bất kỳ hệ thống kiểm toán độc lập nào cũng có thể chạy lại và xác thực từng con số với độ lệch bằng 0.

*(Báo cáo được hoàn thành và nghiệm thu kỹ thuật cho Milestone M3)*
