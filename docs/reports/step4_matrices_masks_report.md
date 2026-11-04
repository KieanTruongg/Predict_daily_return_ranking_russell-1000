# Báo Cáo Kỹ Thuật Bước 4: Kiến Trúc Hệ Thống Ma Trận 2D, Hệ Thống 3 Lớp Point-In-Time (PIT) Masks & Cơ Chế Zero Look-Ahead Purge

**Dự án**: Dự đoán xếp hạng lợi suất hàng ngày rổ cổ phiếu Russell 1000 (Russell 1000 Daily Return Rankings)  
**Milestone**: M3 — Hệ Thống Báo Cáo Dữ Liệu & Kiểm Toán Pháp Y (Section R5)  
**Tác giả**: Đội ngũ Kỹ thuật Dữ liệu & Định lượng (Quantitative Data Engineering Team)  
**Ngày thực hiện thẩm định**: 04/11/2026  
**Phân vùng dữ liệu**: Development Partition (2000-07-01 đến 2023-12-29) | Warm-up (1998-01-02 đến 2000-06-30) | OOS Frozen (2024-01-02 đến 2026-10-30)  
**Tài liệu đối soát nguồn**:
- `data/processed/matrices/*.parquet` (Hệ thống 17 ma trận 2D cơ sở + Targets + Masks)
- `docs/Data report/market_data_audit/tables/matrix_sanity_check_summary.csv`
- `docs/Data report/market_data_audit/tables/matrix_reconciliation_audit.csv`
- `docs/Data report/market_data_audit/tables/matrix_and_mask_coverage_by_period.csv`
- `docs/Data report/market_data_audit/tables/universe_constituent_segments_mapping.csv`

---

## 1. Tổng Quan Kiến Trúc Lưới Tọa Độ 2D (Grid Architecture)

Trong các bài toán định lượng tài chính truyền thống, dữ liệu bảng thường được lưu trữ dưới dạng bảng dài (Long-format DataFrame với các cột `[date, ticker, price, volume, ...]`). Tuy nhiên, đối với bài toán học máy dự đoán xếp hạng tỷ đối chéo (Cross-Sectional Daily Return Rankings) trên quy mô lớn, cấu trúc bảng dài bộc lộ nhiều điểm nghẽn nghiêm trọng:
1. **Chi phí gom nhóm (Groupby Overhead)**: Thao tác tính toán xếp hạng chéo (cross-sectional ranking) hoặc chuẩn hóa $Z$-score theo từng ngày đòi hỏi hàng triệu phép tính `groupby('date')`, gây nghẽn cổ chai CPU và phân mảnh bộ nhớ.
2. **Lệch pha chuỗi thời gian (Temporal Misalignment)**: Các cổ phiếu niêm yết mới hoặc hủy niêm yết khiến số lượng hàng mỗi ngày không đồng nhất, dễ phát sinh lỗi khi trượt cửa sổ thời gian (rolling window features) hoặc dịch nhãn ($T+1$).
3. **Hiệu năng I/O**: Việc đọc một đặc trưng đơn lẻ từ bảng dài đòi hỏi quét toàn bộ tệp dữ liệu khổng lồ.

### Giải Pháp Kiến Trúc Ma Trận 2D Dày (Dense 2D Matrix Grid)

Toàn bộ kho dữ liệu thị trường và tín hiệu đặc trưng được chuẩn hóa thành một lưới tọa độ 2 chiều cố định:
- **Trục Tung (Trục Thời Gian - Index)**: $N_{\text{dates}} = 7,252$ phiên giao dịch chính thức của Sở Giao dịch Chứng khoán New York (NYSE) từ ngày 1998-01-02 đến 2026-10-30. Lưu trữ độc lập tại `matrix_dates_index.parquet`.
- **Trục Hoành (Trục Tài Sản - Columns)**: $N_{\text{sids}} = 3,711$ Canonical SIDs chính quy đại diện cho toàn bộ các thực thể kinh tế từng có mặt trong rổ Russell 1000 trong lịch sử 27 năm. Lưu trữ độc lập tại `matrix_columns_sids.parquet`.
- **Quy mô ma trận đơn vị**:
  $$\text{Cells per Matrix} = 7,252 \times 3,711 = 26,912,172 \text{ ô (cells)}$$

```
                   Trục Hoành: 3,711 Canonical SIDs (Tài Sản)
                 A_R735...   AAPL_R735...   MSFT_R735...  ...  ZTS_R735...
Trục Tung:     ┌────────────────────────────────────────────────────────┐
1998-01-02     │  NaN           0.1425         0.4512     ...    NaN    │
1998-01-05     │  NaN           0.1480         0.4550     ...    NaN    │
   ...         │  ...            ...            ...       ...    ...    │
2023-12-29     │ 139.63        192.53         376.04      ...   197.37  │ (OOS Boundary Purge)
   ...         │  ...            ...            ...       ...    ...    │
2026-10-30     │ 145.20        225.10         415.50      ...   210.80  │ (Terminal Day)
(7,252 phiên)  └────────────────────────────────────────────────────────┘
```

**Ưu Thế Vận Hành Của Kiến Trúc 2D**:
- Bộ nhớ liên tục C-contiguous: Cho phép các phép toán ma trận NumPy/SciPy/PyTorch chạy với tốc độ tối đa của phần cứng.
- Truy cập lát cắt thời gian chéo (Cross-sectional slice tại ngày $t$) bằng phép indexing $O(1)$: `matrix[t, :]`.
- Tính xếp hạng tỷ đối tức thời: `scipy.stats.rankdata(daily_return[t, valid_label_mask[t]])`.
- Định dạng nén Parquet Snappy cho phép tải một ma trận 26.9 triệu ô chỉ trong ~0.15 giây.

---

## 2. Đặc Tả Kỹ Thuật Hệ Thống 17 Ma Trận 2D Cơ Sở & Ma Trận Bổ Trợ

Hệ thống lưu trữ tại thư mục `data/processed/matrices/` bao gồm 17 ma trận cơ sở được tái tạo trực tiếp từ kho Tier 2 Adjusted Warehouse (`russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet`), cùng 2 ma trận mục tiêu học máy (Targets), 4 ma trận mặt nạ (Masks), và 2 tệp metadata chỉ mục:

### Bảng Đặc Tả Chi Tiết Hệ Thống 17 Ma Trận 2D Cơ Sở:

| STT | Tên Tệp Ma Trận Parquet | Kiểu Dữ Liệu (Dtype) | Đơn Vị Đo Lường | Kích Thước Tệp (Bytes) | Ý Nghĩa Kinh Tế & Bản Chất Kỹ Thuật | Ngữ Nghĩa Giá Trị NaN / Mặc Định |
|:---:|:---|:---:|:---:|:---:|:---|:---|
| **1** | `open.parquet` | `float64` | USD | 50,867,446 | Giá mở cửa giao dịch thô (Unadjusted Open Price) | `NaN`: Cổ phiếu chưa niêm yết, đã hủy niêm yết hoặc ngừng giao dịch |
| **2** | `high.parquet` | `float64` | USD | 52,831,024 | Giá cao nhất trong phiên thô (Unadjusted High Price) | `NaN`: Phiên không có giao dịch |
| **3** | `low.parquet` | `float64` | USD | 52,555,601 | Giá thấp nhất trong phiên thô (Unadjusted Low Price) | `NaN`: Phiên không có giao dịch |
| **4** | `close.parquet` | `float64` | USD | 51,994,106 | Giá đóng cửa chính thức thô (Unadjusted Close Price) | `NaN`: Phiên không có giao dịch |
| **5** | `volume.parquet` | `float64` | Cổ phiếu | 80,913,562 | Tổng khối lượng giao dịch trong phiên thô | `NaN`: Không giao dịch; `0.0`: Phiên đóng băng thanh khoản |
| **6** | `adj_open.parquet` | `float64` | USD | 55,893,915 | Giá mở cửa đã điều chỉnh chia tách lùi ($=\text{open} \times CF$) | `NaN`: Tương ứng theo giá thô |
| **7** | `adj_high.parquet` | `float64` | USD | 57,881,846 | Giá cao nhất đã điều chỉnh chia tách lùi ($=\text{high} \times CF$) | `NaN`: Tương ứng theo giá thô |
| **8** | `adj_low.parquet` | `float64` | USD | 57,599,447 | Giá thấp nhất đã điều chỉnh chia tách lùi ($=\text{low} \times CF$) | `NaN`: Tương ứng theo giá thô |
| **9** | `adj_close.parquet` | `float64` | USD | 57,237,774 | Giá đóng cửa đã điều chỉnh chia tách lùi ($=\text{close} \times CF$) | `NaN`: Cơ sở chuẩn để tính Return và Rolling Volatility |
| **10**| `adj_volume.parquet` | `float64` | Cổ phiếu | 84,354,676 | Khối lượng cổ phiếu đã điều chỉnh tương đương ($=\text{vol} / CF$) | `NaN`: Tương ứng theo volume thô |
| **11**| `cumulative_split_factor.parquet`| `float64`| Hệ số vô thứ nguyên | 2,478,875 | Hệ số dồn tích chia tách $CF_t = \prod_{s \ge t} \text{SplitFactor}_s$ | Giá trị $\in (0, +\infty)$, phiên cuối cùng $CF_T = 1.0$ |
| **12**| `adj_dividend.parquet` | `float64` | USD / Cổ phiếu | 2,948,127 | Cổ tức tiền mặt đã điều chỉnh hệ số chia tách ($=\text{div} \times CF$) | Mặc định điền `0.0` nếu trong phiên không chia cổ tức |
| **13**| `daily_return.parquet` | `float64` | Tỷ lệ thập phân | 114,240,026 | Lợi suất giá phiên $r_t = (\text{AdjClose}_t - \text{AdjClose}_{t-1})/\text{AdjClose}_{t-1}$ | `NaN`: Phiên đầu tiên của chuỗi, phiên ngắt quãng hoặc bị cách ly |
| **14**| `total_return.parquet` | `float64` | Tỷ lệ thập phân | 114,252,719 | Lợi suất tổng có cổ tức $r^{\text{tot}}_t = (\text{AdjClose}_t + \text{AdjDiv}_t - P_{t-1})/P_{t-1}$ | `NaN`: Tương ứng daily_return |
| **15**| `is_consecutive_session.parquet`| `bool` | Nhị phân (0/1) | 2,200,812 | Cờ xác nhận phiên $t$ và $t-1$ là 2 phiên liên tiếp trên sàn NYSE (gap=1) | `False`: Phiên đầu tiên, hoặc cổ phiếu bị đình chỉ/tạm ngừng giao dịch |
| **16**| `is_bad_data_period.parquet` | `bool` | Nhị phân (0/1) | 2,178,773 | Cờ đánh dấu nến lỗi / xung đột ticker bị cách ly (CORR_010..013) | `True`: Cần bị loại bỏ khỏi mọi phân tích và huấn luyện |
| **17**| `is_spinoff_discontinuity.parquet`| `bool`| Nhị phân (0/1) | 2,178,771 | Cờ đánh dấu bước nhảy gián đoạn do tách công ty con (CORR_006..009) | `True`: Cần bị cách ly nhãn để tránh méo mó mô hình |

### Bổ Sung: Ma Trận Mục Tiêu (Targets) & Chỉ Mục (Indices):
- `target_next_return.parquet` (61.76 MB): Lợi suất giá của phiên tiếp theo $r_{t+1}$, dịch ngược 1 phiên (`shift(-1)`), gán `NaN` tại tất cả các ô không thỏa mãn `valid_label_mask`.
- `target_next_total_return.parquet` (61.76 MB): Lợi suất tổng của phiên tiếp theo $r^{\text{tot}}_{t+1}$, phục vụ so sánh chiến lược phân phối cổ tức.
- `matrix_dates_index.parquet` (63 KB, 7,252 dòng): Trục ngày giao dịch (`timestamp[us]`).
- `matrix_columns_sids.parquet` (46 KB, 3,711 dòng): Danh sách Canonical SIDs chuẩn (`string`).

---

## 3. Kiến Trúc & Logic Vận Hành Của Hệ Thống 3 Lớp PIT Masks

Trong nghiên cứu tài chính thực chiến, việc trộn lẫn giữa "cổ phiếu có thuộc rổ chỉ số hay không", "cổ phiếu có thể giao dịch được hay không", và "nhãn huấn luyện mô hình có hợp lệ hay không" là nguyên nhân hàng đầu dẫn đến thiên lệch nhìn trước (look-ahead bias) và thiên lệch kẻ sống sót (survivorship bias). Dự án áp dụng mô hình phân tách 3 lớp mặt nạ độc lập và nghiêm ngặt:

```
[ Toàn bộ Lưới Ma Trận: 26,912,172 cells ]
     │
     ▼ Tầng 1: Lọc Tư Cách Thành Viên Điểm-Thời-Gian
┌────────────────────────────────────────────────────────┐
│  membership_mask: 6,333,323 cells (True)               │ ──> Xác nhận thuộc rổ Russell 1000 tại ngày T
└────────────────────────────────────────────────────────┘
     │
     ▼ Tầng 2: Lọc Khả Năng Khớp Lệnh & Chất Lượng Dữ Liệu
┌────────────────────────────────────────────────────────┐
│  valid_data_mask: 6,311,822 cells (99.66%)             │ ──> Giá > 0, Vol > 0, Liên tục, Nến sạch, Đủ warm-up
└────────────────────────────────────────────────────────┘
     │
     ▼ Tầng 3: Lọc Tính Hợp Lệ Của Nhãn Giám Sát & Purge OOS
┌────────────────────────────────────────────────────────┐
│  valid_label_mask: 6,308,873 cells (99.61%)            │ ──> Phiên T+1 sạch, không ngắt quãng, PURGE 2023-12-29
└────────────────────────────────────────────────────────┘
```

### 3.1. Tầng 1: `membership_mask.parquet` (PIT Constituent Membership)

- **Mục đích**: Xác định chính xác vào ngày giao dịch $t$, cổ phiếu $i$ có tư cách là thành viên chính thức của rổ Russell 1000 hay không (Point-in-Time).
- **Nguyên tắc xây dựng**:
  1. Được trích xuất hoàn toàn từ bảng ánh xạ phân đoạn `universe_constituent_segments_mapping.csv`, dựa trên các biên bản tái cơ cấu hàng năm của Russell (hàng năm vào thứ Sáu cuối cùng của tháng 6 hoặc ngày 1 tháng 7).
  2. **Tuyệt đối không suy diễn từ nến giá**: Cổ phiếu có nến giá nhưng không nằm trong danh mục công bố của Russell thì mặt nạ vẫn mang giá trị `False`.
  3. **Giai đoạn khởi tạo đặc trưng (Warm-up Period: 1998-01-02 đến 2000-06-30, 630 phiên)**: Mang giá trị `False` **100%** (0 cells). Toàn bộ dữ liệu 1998–2000 chỉ phục vụ làm lịch sử trượt tính toán các đặc trưng kỹ thuật (252-day momentum, 60-day volatility), không bao giờ được coi là thuộc universe kiểm thử.
- **Hệ thống 2 phiên bản (Strict vs Resolved)**:
  - `strict_membership_mask.parquet`: Chỉ kích hoạt các phân đoạn đạt chuẩn chứng cứ cao nhất `LEVEL_1_VERIFIED_PERMANENT` (**6,308,873 cells**).
  - `resolved_membership_mask.parquet` (đồng nhất với `membership_mask.parquet`): Cho phép kích hoạt thêm các phân đoạn chuyển tiếp tuần tự hợp lý `LEVEL_2` và ghép mã tạm thời `LEVEL_3` (**6,333,323 cells**). Chênh lệch 24,450 cells (chiếm 0.38%) giúp duy trì độ phủ đầy đủ cho các công ty sáp nhập hoặc đổi mã niêm yết mà không vi phạm tính khách quan.

### 3.2. Tầng 2: `valid_data_mask.parquet` (Tradability & Data Quality Filter)

- **Mục đích**: Xác định xem tại ngày giao dịch $t$, cổ phiếu $i$ có thực sự **giao dịch được trên thị trường** với dữ liệu nến hoàn toàn đáng tin cậy hay không.
- **Biểu thức logic liên kết (Vectorized AND)**:
  $$\text{valid\_data}_{i, t} = \text{member}_{i, t} \land (\text{AdjClose}_{i, t} > 0) \land (\text{AdjVolume}_{i, t} > 0) \land \text{is\_consecutive}_{i, t} \land (\text{cum\_bars}_{i, t} \ge 20) \land \neg\text{is\_bad}_{i, t} \land \neg\text{is\_spinoff}_{i, t}$$
- **Ý nghĩa từng điều kiện**:
  - $\text{member}_{i, t}$: Phải thỏa mãn tư cách thành viên rổ (Tầng 1).
  - $\text{AdjClose}_{i, t} > 0$ và $\text{AdjVolume}_{i, t} > 0$: Loại bỏ các phiên đóng băng thanh khoản, phiên sàn không có lệnh khớp.
  - $\text{is\_consecutive}_{i, t} == \text{True}$: Khoảng cách giữa phiên hiện tại và phiên có nến trước đó trên sàn NYSE phải đúng bằng 1 phiên. Nếu cổ phiếu bị ngừng giao dịch 3 ngày rồi mở cửa trở lại, phiên đầu tiên mở lại sẽ có `is_consecutive = False`, loại trừ biến động giá tích lũy của nhiều ngày nghỉ.
  - $\text{cum\_bars}_{i, t} \ge 20$: Cổ phiếu mới niêm yết phải có ít nhất 20 phiên lịch sử nến để các chỉ báo cơ bản (MA20, Volatility 20d) đạt trạng thái ổn định.
  - $\neg\text{is\_bad}_{i, t}$ và $\neg\text{is\_spinoff}_{i, t}$: Loại bỏ các phiên rơi vào vùng nến lỗi (MKL, SABR, LOW, CPTH) hoặc phiên gián đoạn spin-off (KSU, SSP, COMS, PENN) từ bảng hiệu chỉnh pháp y.
- **Kết quả thực nghiệm**: Đạt **6,311,822 True cells** (tỷ lệ khả dụng đạt **99.66%** so với resolved membership, loại bỏ 21,501 cells không đủ điều kiện giao dịch).

### 3.3. Tầng 3: `valid_label_mask.parquet` (Supervised Label Guard & Zero Look-Ahead Purge)

- **Mục đích**: Xác định xem tại ngày giao dịch $t$, cổ phiếu $i$ có đủ điều kiện để **tạo ra nhãn giám sát mục tiêu ($r_{t+1}$)** cho thuật toán học máy hay không.
- **Biểu thức logic liên kết**:
  $$\text{valid\_label}_{i, t} = \text{valid\_data}_{i, t} \land (\text{AdjClose}_{i, t+1} > 0) \land (\text{AdjVolume}_{i, t+1} > 0) \land \text{is\_consecutive}_{i, t+1} \land \text{isfinite}(r_{i, t+1}) \land \neg\text{is\_purged}_t$$
- **Ý nghĩa kỹ thuật**:
  - Một mẫu học máy tại ngày $t$ chỉ có ý nghĩa nếu tín hiệu đầu vào tại ngày $t$ sạch (`valid_data = True`) VÀ kết quả thực hiện giao dịch tại ngày $t+1$ là một phiên giao dịch bình thường, thanh khoản dương, không bị ngắt quãng phiên.
  - Nếu ngày $t+1$ cổ phiếu bị đình chỉ giao dịch hoặc dính nến lỗi, nhãn tại ngày $t$ sẽ bị vô hiệu hóa (`valid_label = False`), ngăn mô hình học các tín hiệu rác.

#### Cơ Chế Thanh Lọc Ranh Giới Tuyệt Đối (Zero Look-Ahead Boundary Purge)
Đây là quy tắc bảo mật học máy tối quan trọng được thiết kế riêng cho dự án:
1. **Ranh giới Development / OOS ($T = \text{2023-12-29}$)**:
   - Ngày 2023-12-29 là phiên giao dịch cuối cùng của tập phát triển (Development Partition). Phiên tiếp theo $T+1$ chính là ngày 2024-01-02 — phiên mở đầu của tập ngoài mẫu (Out-Of-Sample Partition) vốn đang bị **ĐÓNG BĂNG TUYỆT ĐỐI**.
   - Nếu giữ nhãn tại ngày 2023-12-29, mô hình trong quá trình huấn luyện sẽ gián tiếp "nhìn thấy" lợi suất của ngày 2024-01-02, gây ra rò rỉ dữ liệu ngoài mẫu (OOS Data Leakage).
   - **Hành động kỹ thuật**: Toàn bộ hàng ngày **2023-12-29 bị PURGE 100%**:
     $$\text{valid\_label\_mask}[\text{'2023-12-29'}, :] = \text{False}$$
     $$\text{target\_next\_return}[\text{'2023-12-29'}, :] = \text{NaN}$$
   - Kết quả: **0% rò rỉ dữ liệu**, bảo vệ tính toàn vẹn tuyệt đối cho bài toán kiểm thử ngoài mẫu.
2. **Phiên cuối cùng của tập dữ liệu ($T = \text{2026-10-30}$)**:
   - Không tồn tại phiên $T+1$, do đó toàn bộ hàng ngày 2026-10-30 được gán `valid_label_mask = False` và `target = NaN` (100% Clean).

- **Kết quả thực nghiệm**: Đạt **6,308,873 True cells** (tỷ lệ **99.61%** so với membership mask).

---

## 4. Các Ví Dụ Minh Họa Trực Quan (Concrete Walk-Through Cases)

Để hiểu rõ cách thức hoạt động đồng bộ của 3 lớp mặt nạ, chúng tôi xem xét 4 kịch bản thực tế đại diện:

### Kịch Bản 1: Cổ phiếu giao dịch bình thường liên tục (Ví dụ: Apple Inc. — AAPL phiên ngày 2021-05-14)
- **Tình trạng**: AAPL là thành viên chính thức Russell 1000, giá $127.45$, vol 81 triệu cổ phiếu, phiên liền kề bình thường, phiên $T+1$ (2021-05-17) giao dịch bình thường.
- **Trạng thái Mask**:
  - `membership_mask`: **True** (nằm trong khoảng hiệu lực của kỳ tái cơ cấu 2020).
  - `valid_data_mask`: **True** (giá dương, vol dương, liên tục, lịch sử nến > 20).
  - `valid_label_mask`: **True** (phiên $T+1$ hợp lệ).
  - `target_next_return`: Được tính toán bằng $+1.22\%$ ($r_{T+1}$).

### Kịch Bản 2: Cổ phiếu bị đình chỉ giao dịch tạm thời (Trading Halt / Gap Session)
- **Tình trạng**: Cổ phiếu $X$ là thành viên chỉ số, ngừng giao dịch vào thứ Ba và thứ Tư do chờ công bố thông tin M&A, mở cửa trở lại vào thứ Năm.
- **Trạng thái Mask tại phiên thứ Năm**:
  - `membership_mask`: **True**.
  - `valid_data_mask`: **False** vì `is_consecutive_session == False` (khoảng cách phiên giao dịch trên sàn NYSE là 3 ngày, không phải 1). Điều này ngăn chặn việc tính lợi suất 1 ngày bị sai lệch do dồn nén tin tức nhiều ngày.
  - `valid_label_mask`: **False** (kế thừa từ valid_data).

### Kịch Bản 3: Phiên ranh giới phân vùng Development / OOS (Ngày 2023-12-29)
- **Tình trạng**: Tất cả ~980 cổ phiếu thành viên Russell 1000 giao dịch bình thường trong phiên cuối cùng của năm 2023.
- **Trạng thái Mask**:
  - `membership_mask`: **True**.
  - `valid_data_mask`: **True** (dữ liệu phiên 2023-12-29 hoàn toàn hợp lệ để tính các đặc trưng kỹ thuật).
  - `valid_label_mask`: **False (100% PURGED)**.
  - `target_next_return`: **NaN (100% BLOCKED)**.
  - **Ý nghĩa**: Các đặc trưng tại ngày $T$ vẫn có thể dùng làm dữ liệu lịch sử, nhưng không mẫu nào tại ngày này được tham gia huấn luyện hàm mất mát học máy vì nhãn thuộc về tương lai OOS.

### Kịch Bản 4: Cổ phiếu có biến cố gián đoạn Spin-off (Ví dụ: KSU ngày 2000-07-13)
- **Tình trạng**: Kansas City Southern tách công ty con Janus Capital, giá cổ phiếu mẹ sụt $-96.66\%$ do phân phối tài sản.
- **Trạng thái Mask**:
  - Ngày 2000-07-12 ($T$): `membership_mask = True`, `valid_data_mask = True`, nhưng `valid_label_mask = False` vì phiên $T+1$ (ngày 13) bị cách ly.
  - Ngày 2000-07-13 ($T+1$): `membership_mask = True`, `valid_data_mask = False` (do cờ `is_spinoff_discontinuity = True`), `valid_label_mask = False`.
  - **Kết quả**: Cả hai ngày xung quanh biến cố đều không tạo ra bất kỳ nhãn huấn luyện rác nào.

---

## 5. Kết Quả Thẩm Định & Kiểm Thử Toàn Vẹn Hệ Thống (Sanity Checks & Audit Reconciliation)

Quy trình thẩm định Bước 4 được xác thực độc lập thông qua script `08_validate_matrices_and_sanity_checks.py`. Kết quả được đối soát đối chiếu với bảng tổng hợp `docs/Data report/market_data_audit/tables/matrix_sanity_check_summary.csv`:

### Bảng Kết Quả Sanity Checks Toàn Diện (14/14 Tiêu Chí PASSED):

| STT | Hạng Mục Kiểm Thử (Audit Metric) | Giá Trị Thực Nghiệm Đo Được | Chuẩn Kỳ Vọng | Trạng Thái Thẩm Định |
|:---:|:---|:---:|:---:|:---:|
| **1** | Lưới tọa độ ma trận (Dates $\times$ Canonical SIDs) | **7,252 $\times$ 3,711** | $7,252 \times 3,711$ | ✅ **PASSED** |
| **2** | Tổng số ô (cells) mỗi ma trận 2D | **26,912,172** | $26,912,172$ | ✅ **PASSED** |
| **3** | Số ô True của Membership Mask | **6,333,323** | Khớp Segment Mapping | ✅ **PASSED** |
| **4** | Số ô True của Valid Data Mask | **6,311,822** (99.66%) | $\le$ Membership True | ✅ **PASSED** |
| **5** | Số ô True của Valid Label Mask | **6,308,873** (99.61%) | $\le$ Valid Data True | ✅ **PASSED** |
| **6** | Vi phạm phân cấp: $\text{Valid Label} > \text{Valid Data}$ | **0 vi phạm** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **7** | Vi phạm phân cấp: $\text{Valid Data} > \text{Membership}$ | **0 vi phạm** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **8** | Độ lệch lớn nhất khi dịch mục tiêu Target Shift ($T \rightarrow T+1$) | **0.00e+00** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **9** | Thanh lọc ranh giới OOS (2023-12-29 Boundary Purge) | **100% Purged (0 leakage)** | $100\%$ Purged | ✅ **PASSED** |
| **10**| Phiên kết thúc dữ liệu 2026-10-30: $\text{Target} = \text{NaN}$ | **100% Clean** | $100\%$ Clean | ✅ **PASSED** |
| **11**| Ô có giá $\le 0$ hoặc NaN trong vùng Valid Data | **0 ô** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **12**| Ô có khối lượng $\le 0$ hoặc NaN trong vùng Valid Data | **0 ô** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **13**| Độ lệch lớn nhất khi đối chiếu ngược với Kho Giá Tier 2 | **0.00e+00** | Tuyệt đối bằng 0 | ✅ **PASSED** |
| **14**| Kiểm thử tính liên tục của chia tách / chia tách ngược | **10/10 Hoàn hảo liên tục** | 10/10 Hoàn hảo | ✅ **PASSED** |

### Đối Chiếu Chéo 50,000 Cells Ngẫu Nhiên Với Kho Giá (`matrix_reconciliation_audit.csv`):
Để bảo đảm việc xoay trục (pivot) từ bảng dài sang ma trận 2D không làm rơi rụng hoặc xáo trộn giá trị, hệ thống đã rút mẫu ngẫu nhiên 50,000 cells trên 5 trường cốt lõi:
- `adj_close`: 50,000 matched, 0 mismatches, sai số tuyệt đối lớn nhất = **0.000000**.
- `adj_volume`: 50,000 matched, 0 mismatches, sai số tuyệt đối lớn nhất = **0.000000**.
- `daily_return`: 49,989 matched số thực, 11 matched NaN, 0 mismatches, sai số lớn nhất = **0.000000**.
- `total_return`: 49,989 matched số thực, 11 matched NaN, 0 mismatches, sai số lớn nhất = **0.000000**.
- `cumulative_split_factor`: 50,000 matched, 0 mismatches, sai số tuyệt đối lớn nhất = **0.000000**.

### Thống Kê Độ Phủ Của Hệ Thống Ma Trận Qua Các Kỳ Tái Cơ Cấu Đại Diện:
Dữ liệu trích từ `docs/Data report/market_data_audit/tables/matrix_and_mask_coverage_by_period.csv`:

| Kỳ Tái Cơ Cấu (Reconstitution Period) | Khoảng Thời Gian Hiệu Lực | Số Phiên Giao Dịch | Số Mã Công Bố Chính Thức | Số Cổ Phiếu-Ngày Hợp Lệ (Valid Data Stock-Days) | Số Mã Trung Bình / Phiên (Valid Data Count) | Tỷ Lệ Phủ So Với Membership (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Warm-up History** | 1998-01-02 đến 2000-06-30 | 630 | 0 | 0 | 0.0 | 0.00% (Quy chuẩn) |
| **2000 Reconstitution** | 2000-07-03 đến 2001-06-29 | 251 | 996 | 228,985 | 912.3 | 99.56% |
| **2005 Reconstitution** | 2005-07-01 đến 2006-06-30 | 252 | 987 | 232,656 | 923.2 | 99.44% |
| **2010 Reconstitution** | 2010-07-01 đến 2011-06-30 | 253 | 981 | 237,551 | 938.9 | 99.55% |
| **2015 Reconstitution** | 2015-07-01 đến 2016-06-30 | 253 | 1,026 | 246,938 | 976.0 | 99.67% |
| **2020 Reconstitution** | 2020-07-01 đến 2021-06-30 | 252 | 994 | 243,149 | 964.9 | 99.98% |
| **2023 Reconstitution** | 2023-07-03 đến 2024-06-28 | 250 | 1,011 | 246,727 | 986.9 | 99.90% |
| **2026 Reconstitution** | 2026-07-01 đến 2026-10-30 | 86 | 1,011 | 85,555 | 994.8 | 99.93% |

Độ phủ qua các năm tăng dần đều từ $912$ cổ phiếu/phiên vào năm 2000 lên gần $995$ cổ phiếu/phiên vào năm 2026, phản ánh chất lượng thu thập dữ liệu ngày càng hoàn thiện của cơ sở hạ tầng thị trường hiện đại, đồng thời chứng minh tính ổn định tuyệt đối của hệ thống ma trận 2D qua gần 3 thập kỷ.

---

## 6. Kết Luận Kỹ Thuật (Engineering Sign-off)

Hệ thống 17 ma trận 2D và 3 lớp PIT masks tại Bước 4 đã hoàn thành xuất sắc toàn bộ các tiêu chuẩn định lượng khắt khe nhất:
1. Đảm bảo cấu trúc dữ liệu tối ưu hóa cho mô hình học máy hiện đại (NumPy/PyTorch/LightGBM C-contiguous).
2. Phân tách rành mạch 3 tầng kiểm soát (Thành viên - Khả năng giao dịch - Nhãn giám sát).
3. Triệt tiêu hoàn toàn rò rỉ dữ liệu thông qua cơ chế Zero Look-Ahead Purge tại ranh giới OOS.
4. Đạt tỷ lệ đối soát 100% khớp đẳng thức toán học trên 50,000 cells kiểm toán độc lập.

*(Báo cáo được hoàn thành và nghiệm thu kỹ thuật cho Milestone M3)*
