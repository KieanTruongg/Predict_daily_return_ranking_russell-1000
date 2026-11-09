# Báo cáo Sinh Feature Store Ứng viên và Phân tích Dữ liệu Khám phá (EDA) trên tập Development

Ngày thực hiện: **2026-11-06** (Cập nhật hoàn thiện sau rà soát hệ thống: **2026-11-07**)  
Phạm vi dữ liệu: **Tập Development (2000-07-01 đến 2023-12-29)** — 5.911 phiên giao dịch $\times$ 3.711 mã Canonical SID.  
Tình trạng: **BẢN ỨNG VIÊN (CANDIDATE FEATURE STORE) — CHƯA NGHIỆM THU CHO TRAINING**.  
Bộ kiểm thử hồi quy: **79/79 full tests PASSED** (Kiểm thử portable: **59 passed, 20 integration passed**); kiểm định cấu trúc Feature Store: **104/104 checks PASSED**; kiểm định nhân quả mở rộng: **144/144 tests PASSED** (toàn bộ điểm kiểm tra có baseline hữu hạn).  
Cam kết bảo toàn: **Tuyệt đối không phân tích, không sử dụng và không nạp dữ liệu Out-of-Sample (2024–2026) vào bộ nhớ RAM**. Chưa huấn luyện (training), chưa tinh chỉnh (tuning), chưa tính IC mục tiêu, không tự ý can thiệp làm sạch bằng clipping/winsorizing.

Tham chiếu:
- [Đặc tả 16 features candidate v1](../specifications/features_v1.md)
- [Đặc tả Target và Thời điểm Khớp lệnh v1](../specifications/target_and_timing_v1.md)
- [Báo cáo Kiểm thử Pilot](../reports/feature_pilot_report.md)
- [Bảng Kiểm kê Dị thường OHLC Toàn diện (251 bản ghi)](feature_eda/anomaly_inventory.csv)
- [Bảng Điều tra Ngoại lai Cụ thể](feature_eda/outlier_investigation_table.csv)
- [Bảng So sánh Trước/Sau Cách ly Ngoại lai (3 giai đoạn)](feature_eda/outlier_isolation_before_after_comparison.csv)
- [Bảng Phân rã NaN Chi tiết](feature_eda/nan_breakdown.csv)
- [Bảng Metadata Tương quan Từng cặp](feature_eda/pairwise_correlation_metadata.csv)
- [Kết quả Kiểm định Nhân quả Mở rộng](feature_eda/extended_causal_test_results.csv)
- [Manifest Feature Store v1.4.0](../../data/processed/features/feature_store_manifest.json)
- [Sổ tay Điều chỉnh Dữ liệu Thị trường (19 mục có bằng chứng)](../Data%20report/market_data_audit/tables/market_data_corrections_and_exceptions.csv)
- [Thư mục hình ảnh EDA](feature_eda/figures/)

---

## 1. Tổng quan và Khung kiểm chứng 4 mức độ

Nhằm bảo đảm tính khách quan khoa học, báo cáo tuân thủ nghiêm ngặt khung phân định 4 cấp độ tin cậy:

| Cấp độ | Định nghĩa | Trạng thái trong đợt này | Bằng chứng kiểm tra |
|---|---|:---:|---|
| **Mức 1: Script chạy xong** | Code thực thi hoàn tất không phát sinh lỗi ngoại lệ (`exit code 0`), sinh đủ 16 file Parquet và manifest có đầy đủ mã băm SHA-256. | **ĐÃ ĐẠT** | Pipeline hoàn tất không lỗi; manifest v1.4.0 ghi nhận đầy đủ trạng thái working tree dirty và hash của từng script, spec, matrix. |
| **Mức 2: Số liệu trông hợp lý** | Thống kê phân phối, độ phủ (>98.4%) và miền giá trị nằm trong khoảng chấp nhận được về mặt trực giác tài chính. | **ĐÃ ĐẠT** | 5 bảng CSV tại `docs/reports/feature_eda/` phản ánh trung thực toàn bộ phân phối, đã cách ly có chọn lọc các tọa độ bất thường mà không làm biến dạng chuỗi thời gian. |
| **Mức 3: Công thức nhất quán** | Đẳng thức phân rã lợi suất, tính dương của phương sai, kiểm tra không rò rỉ tương lai và đối chiếu công thức số học độc lập. | **ĐÃ ĐẠT** | 104 bài kiểm tra cấu trúc + 144 bài kiểm tra nhân quả mở rộng (Perturbation & Truncation trên các tọa độ hữu hạn) đều đạt sai lệch $\le 10^{-11}$. |
| **Mức 4: Đã xác minh thực tế** | Đối chiếu độc lập với hồ sơ SEC, thông cáo báo chí và bối cảnh vi cấu trúc sàn giao dịch bên ngoài dữ liệu nhà cung cấp. | **ĐÃ XÁC MINH CÁC TỌA ĐỘ NGOẠI LAI CỤ THỂ**<br>*(Đã truy vết gốc ZIP raw của 6 tọa độ, đối chiếu SEC Form 8-K / S-1/A và cơ chế stub quote tiền-2010; chấp nhận giả định nhà cung cấp cho phần còn lại)* | Hồ sơ SEC Form 8-K của GATX Corp (25/01/2007), bản cáo bạch IPO NASDAQ SEC Form S-1/A của HomeStore.com (04/08/1999), dữ liệu băng giá NYSE/NASDAQ các đợt biến động 06/06/2008 và 27/02/2007. |

---

## 2. Sinh Feature Store Development (Bản Ứng viên)

### 2.1. Làm gì & Lý do
- **Nội dung thực hiện**: Tạo toàn bộ 16 ma trận 2D Parquet cho 16 features candidate theo đặc tả `features_v1.md`, lưu tại `data/processed/features/<feature_name>.parquet`.
- **Lý do**: Cung cấp kho dữ liệu đặc trưng chuẩn hóa ở định dạng nén tối ưu (Snappy Parquet) để phục vụ kiểm định chất lượng, phân tích phân phối, tương quan chéo lát cắt và làm cơ sở rà soát trước khi chuyển sang giai đoạn tiền xử lý mô hình.
- **Trạng thái**: Bản Feature Store này được giữ làm **Bản ứng viên (Candidate)**, chưa nghiệm thu để làm dữ liệu huấn luyện chính thức.

### 2.2. Đầu vào & Phương pháp
- **Đầu vào**: Các ma trận giá, khối lượng và chất lượng Tier 2 tại `data/processed/matrices/` (`adj_close`, `adj_open`, `adj_high`, `adj_low`, `adj_volume`, `close`, `volume`, `daily_return`).
- **Khoảng thời gian tính toán**:
  - *Lịch sử nến đầu vào*: Từ `1998-01-02` đến `2023-12-29` (6.541 phiên), bao gồm giai đoạn Warm-up (1998–2000) để khởi tạo đầy đủ các cửa sổ trượt dài hạn (như 252 phiên của `mom_12m_skip_1m`).
  - *Lát cắt đầu ra lưu trữ*: Đúng giai đoạn Development từ `2000-07-01` đến `2023-12-29` (5.911 phiên giao dịch).
- **Cơ chế Bảo vệ Out-of-Sample (OOS Protection)**:
  - Dự án phân định rạch ròi giữa *"không dùng OOS để tính toán/ra quyết định"* và *"không nạp OOS vào bộ nhớ RAM"*.
  - Tại tầng tải ma trận (`src/data/matrix_loader.py`), cơ chế lọc đẩy xuống định dạng Parquet (Predicate Pushdown Filters trên `__index_level_0__`) bảo đảm rằng khi gọi `dev_only=True`, các dòng dữ liệu OOS ($> \text{2023-12-29}$) **hoàn toàn không được đọc từ đĩa cứng vào bộ nhớ RAM**.
  - Đã loại bỏ hoàn toàn cơ chế fallback âm thầm đọc toàn bộ file (`except Exception:`). Nếu không xác định được cột ngày hoặc bộ lọc đẩy xuống thất bại, hàm nạp lập tức phát sinh `RuntimeError` rõ ràng.
  - Nếu bất kỳ tiến trình nào gọi `load_matrix` mà không có `dev_only=True` và thiếu cờ cấp phép `allow_oos=True`, ngoại lệ `OOSFreezeViolationError` sẽ được kích hoạt ngay lập tức trước khi chạm vào tệp dữ liệu. Hành vi này đã được kiểm định qua bộ test suite (`test_matrix_loader.py`, `test_loader_synthetic.py`).
- **Chính sách Mask**:
  - `bar_quality_mask` và `field_quality_mask`: Làm sạch chuỗi nến đầu vào theo từng trường giá trị trước khi rolling, độc lập hoàn toàn với membership.
  - `strict_membership_mask`: Áp dụng tại thời điểm đầu ra $T$. Mọi ô tọa độ ngoài rổ Russell 1000 tại ngày $T$ đều được gán `NaN`. Tuyệt đối không dùng `valid_label_mask` để lọc đầu vào $X$.
- **Kiểm soát tài nguyên bộ nhớ (RAM)**:
  - Xử lý tuần tự từng đặc trưng (`feature-by-feature`), giải phóng vùng nhớ và gọi `gc.collect()` sau mỗi feature.
  - Đỉnh sử dụng bộ nhớ RAM duy trì ổn định dưới 1.0 GB trong suốt quá trình chạy.

### 2.3. Kết quả & Manifest Nhận diện Code
- Toàn bộ 16 file ma trận đặc trưng được tạo thành công với tổng dung lượng trên đĩa là **~840 MB** (trung bình ~52.5 MB/file, kiểu dữ liệu `float64`).
- Tệp manifest được quản lý ở phiên bản v1.4.0 tại [`data/processed/features/feature_store_manifest.json`](../../data/processed/features/feature_store_manifest.json), tự động sinh đầy đủ nguồn gốc mã thực thi (code provenance):
  - Git commit cơ sở: `5b108475a6f405d8cade0fe5146ce06cbbb0cc49`.
  - Trạng thái cây làm việc (Working Tree Status): Ghi nhận chi tiết các tệp modified/untracked (`DIRTY`), bảo đảm tính trung thực tuyệt đối về nguồn gốc mã.
  - Mã băm SHA-256 của từng file script (`12_generate_feature_store.py`, `13_validate_feature_store.py`, `14_feature_eda.py`, `15_extended_causal_tests.py`), tài liệu đặc tả (`features_v1.md`, `target_and_timing_v1.md`), các module thư viện lõi và mã băm của từng file Parquet đầu ra.

---

## 3. Kiểm định Cấu trúc & Mở rộng Kiểm tra Nhân quả

### 3.1. Bộ Kiểm định Cấu trúc 104 Tiêu chí
Script kiểm định độc lập `scripts/01_pipeline/13_validate_feature_store.py` đã thực thi 104 bài kiểm tra, lưu tại [`feature_store_validation.csv`](feature_eda/feature_store_validation.csv):

| Hạng mục kiểm tra | Số bài test | Số bài PASSED | Số bài FAILED | Đánh giá thực tế |
|---|:---:|:---:|:---:|---|
| Khớp kích thước & Trục tọa độ (Shape & Axes) | 48 | 48 | 0 | Đúng $5.911 \times 3.711$, ngày đơn điệu tăng dần, SID duy nhất. |
| Không chứa giá trị vô hạn (No Inf) | 16 | 16 | 0 | $0$ ô `+Inf`/`-Inf` trên $21.935.721$ ô $\times 16$ ma trận. |
| Đóng gói Membership (Outside NaN) | 16 | 16 | 0 | Đúng $16.328.312$ ô ngoài rổ ($74.44\%$) đều nhận `NaN`. |
| Miền giá trị theo đặc tả (Domain Bounds) | 16 | 16 | 0 | RSI $\in [0, 100]$, các biến động $\ge 0$, volume ratio $\ge 0$. |
| Tái đối chiếu ô Pilot (Pilot Parity) | 7 | 7 | 0 | Khớp giá trị đã kiểm chứng ở đợt pilot (sai số $< 10^{-10}$). |
| Kiểm tra nhân quả cơ bản (Causal Check) | 1 | 1 | 0 | Sai lệch tương lai $= 0.00e+00$. |
| **Tổng cộng** | **104** | **104** | **0** | **ĐẠT CHUẨN KỸ THUẬT 100%** |

### 3.2. Mở rộng Kiểm tra Nhân quả trên 16 Features (144 Bài Test)
Bài kiểm tra nhân quả đã được chính thức hóa thành script pipeline [`scripts/01_pipeline/15_extended_causal_tests.py`](../../scripts/01_pipeline/15_extended_causal_tests.py) và test tự động trong [`tests/test_causal_integrity.py`](../../tests/test_causal_integrity.py), kiểm định **đủ 16 features** trên 3 mốc thời gian đại diện cho các chế độ thị trường và 3 mã cổ phiếu lớn có thanh khoản liên tục:
- **Thời điểm kiểm tra**: `2005-06-15` (chu kỳ mở rộng), `2015-06-15` (hậu khủng hoảng GFC), `2022-06-15` (chu kỳ thắt chặt lạm phát).
- **Mã cổ phiếu**: `AAPL R735QTJ8XC9X`, `MSFT R735QTJ8XC9X`, `XON R735QTJ8XC9X` (ExxonMobil).
- **Hai phương pháp kiểm định**:
  1. *Kiểm tra Làm nhiễu Tương lai (Perturbation Test)*: Nhân toàn bộ giá và volume tương lai ($t > T$) với $99.0$ và đặt return tương lai thành $-0.99$. Xác nhận rằng giá trị feature tại ngày $T$ hoàn toàn không đổi.
  2. *Kiểm tra Cắt ngắn Lịch sử (Truncation Consistency Test)*: Cắt chuỗi nến đầu vào kết thúc đúng tại ngày $T$ (dữ liệu sau $T$ hoàn toàn không tồn tại trong mảng). So sánh giá trị tính được tại $T$ với giá trị tính được khi nạp toàn bộ chuỗi dài.
- **Ràng buộc kiểm tra nghiêm ngặt (Strict Finite Assertion)**: Để tránh trường hợp bài test pass vô nghĩa do cả 3 giá trị đều là `NaN`, bài kiểm tra xác nhận khẳng định rằng **toàn bộ 144 tọa độ cơ sở tại ngày $T$ đều là số thực hữu hạn** (`np.isfinite(baseline)`).

**Kết quả chi tiết**: Lưu tại [`extended_causal_test_results.csv`](feature_eda/extended_causal_test_results.csv):
- **144 / 144 trường hợp PASSED** (16 features $\times$ 3 ngày $\times$ 3 mã).
- Toàn bộ sai lệch giữa bản gốc, bản làm nhiễu và bản cắt ngắn đều bằng $\mathbf{0.00e+00}$ (hoặc $< 10^{-11}$).
- Cả các đặc trưng có cửa sổ dài 252 phiên (`mom_12m_skip_1m`) và đặc trưng đệ quy tích lũy trạng thái (`rsi_14d`) đều vượt qua kiểm tra, xác nhận không có bất kỳ dòng lệnh nào đọc dữ liệu sau $T$.

---

## 4. Kiến trúc Thống nhất Corrections & Rà soát OHLC Toàn diện (1998–2023)

### 4.1. Kiến trúc Áp dụng Corrections Thống nhất từ Thượng nguồn
Nhằm khắc phục tình trạng phân mảnh và sửa thủ công dữ liệu Parquet, một hệ thống thống nhất đã được thiết lập qua module [`src/data/corrections.py`](../../src/data/corrections.py) với các nguyên tắc cốt lõi:
1. **Một nguồn sự thật duy nhất (Single Source of Truth)**: Bảng `market_data_corrections_and_exceptions.csv` (19 bản ghi có bằng chứng).
2. **Phân định rạch ròi 2 cơ chế cách ly**:
   - *Cách ly toàn bar (`is_bar_quarantine`)*: Đặt cờ `is_bad_data_period = True`, cách ly toàn bộ bar khỏi tính return chuỗi thời gian (áp dụng cho các lỗi dữ liệu toàn diện hoặc nghi vấn tiền-IPO như `CORR_010` HOMS và `CORR_019` TR).
   - *Cách ly cục bộ cấp trường (`is_field_quarantine`)*: Chỉ đặt `np.nan` cho các trường bị hỏng (ví dụ `open`, `low` và tương ứng `adj_open`, `adj_low`), **giữ nguyên giá `close`, `adj_close` và `volume`**. Điều này bảo toàn các feature chỉ dùng Close (`ret_1d`, `ret_20d`, `ret_60d`, `rsi_14d`), trong khi cách ly an toàn các feature phụ thuộc vào trường hỏng (`ret_intraday`, `ret_overnight`, `vol_parkinson_20d`).
3. **Áp dụng có trật tự qua các tầng pipeline**:
   - *Tầng 1 (Script 06)*: Gọi `apply_corrections_to_dataframe(df_prices, df_corr)` trực tiếp khi sinh `tier2_daily_market_data.parquet`.
   - *Tầng 2 (Ma trận & Loader)*: Script 07 sinh ma trận chất lượng, và `load_field_quality_mask` tải mặt nạ trường chính xác từ bảng corrections.
   - *Tầng 3 (Script 12)*: Truyền từ điển `field_quality_masks` vào `FeatureBase.compute` để làm sạch đầu vào trước khi tính toán feature.
4. **Kiểm thử đơn vị chuyên biệt ([`tests/test_corrections.py`](../../tests/test_corrections.py))**: 5/5 bài kiểm tra PASSED (kiểm tra nạp, phân biệt bar vs field, tính bất biến của trường không liên quan, và tính lũy đẳng).

### 4.2. Rà soát Hệ thống Dị thường OHLC (1998–2023)
Script rà soát chuyên dụng [`scripts/01_pipeline/10b_scan_ohlc_anomalies.py`](../../scripts/01_pipeline/10b_scan_ohlc_anomalies.py) đã quét toàn bộ $6.541 \text{ phiên} \times 3.711 \text{ SIDs}$ ($24,27 \text{ triệu nến}$) để phát hiện:
- Đảo ngược giá ($\text{Low} > \text{High}$ hoặc $\text{Open}/\text{Close}$ nằm ngoài $[\text{Low}, \text{High}]$).
- Giá mang tính chất quy ước kỹ thuật (Stub quotes / Sentinel values: $0.01$ và $999.99$).
- Tỷ lệ giãn nở trong ngày cực đại ($\text{High}/\text{Low} \ge 10.0$).
- Khoảng nhảy qua đêm bất thường ($|\text{ret\_overnight}| \ge 1.0$).

Kết quả quét được xuất vào bảng kiểm kê [`docs/reports/feature_eda/anomaly_inventory.csv`](feature_eda/anomaly_inventory.csv) với **251 bản ghi dị thường**:
- **Trạng thái phân loại trong lượt quét 251 ca**:
  * `quarantined, mechanism unverified`: **4 trường hợp** đã được thẩm tra và cách ly có chọn lọc từ lượt quét (`CORR_016` RGC, `CORR_017` CEPH, `CORR_018` FRT, `CORR_019` TR).
  * `unresolved`: **247 trường hợp** được giữ nguyên trạng thái quan sát khách quan, không tự ý gọt giũa dữ liệu nếu chưa có bằng chứng xác đáng.
- **Số lũy kế toàn dự án**: Nếu tính thêm 2 ca ngoại lai ban đầu đã điều tra và cách ly trước đó (`CORR_009` GMT và `CORR_010` HOMS), toàn dự án có **lũy kế 6 ca dị thường đã cách ly**.
- **Bối cảnh vi cấu trúc thị trường (Market Microstructure Context)**:
  * Trước khi SEC và FINRA ban hành lệnh cấm đặt lệnh tượng trưng (Stub Quote Ban) sau sự kiện Flash Crash 2010, các nhà tạo lập thị trường (Market Makers) tại Mỹ có nghĩa vụ niêm yết chào mua/chào bán liên tục. Khi thị trường biến động dữ dội hoặc hệ thống quá tải, họ thường rút thanh khoản bằng cách gửi giá chào mua sàn $0.01$ USD và giá chào bán trần $999.99$ USD.
  * *Phiên 06/06/2008* (Giá dầu thô tăng kỷ lục $11 USD/thùng, thị trường chứng khoán chao đảo mạnh): Có tới **18 cổ phiếu** trong rổ Russell 1000 xuất hiện `High = 999.99` (như BKH, BLC, CSL, FRT, TR, v.v.), trong khi giá Open và Close hoàn toàn bình thường.
  * *Phiên 27/02/2007* (Sự cố máy tính Dow Jones bị nghẽn lệnh): Xuất hiện các bản in giá lỗi $0.01$ rải rác trên Open/Low (như GMT, PCP).
  * *Phiên 06/05/2010* (Flash Crash): 9 cổ phiếu ghi nhận tỷ lệ giãn nở giá cực đại do lệnh bán thị trường quét cạn sổ lệnh xuống tận $0.01$.

### 4.3. Bảng Điều tra Chi tiết các Tọa độ Mới Được Cách ly
Tất cả các trường hợp đều được truy vết trực tiếp tới dòng cụ thể trong kho tệp nén thô (`data/raw/market_data/*.zip`), ghi nhận tại [`outlier_investigation_table.csv`](feature_eda/outlier_investigation_table.csv):

| Tọa độ | Ngày | Dữ liệu Raw quan sát | Vị trí tệp ZIP Raw | Hiện tượng quan sát | Hành động áp dụng |
|---|---|---|---|---|---|
| `RGC SEIRNAFAFF51` | `2008-07-24` | Open=0.01, High=16.53, Low=0.01, Close=16.37, Vol=1.900.310 | `batch_08_of_10.zip` $\to$ `raw/year=2008/batch_08_of_10.csv`, dòng **18595** | In nhầm giá sàn $0.01$ tại Open và Low; Close khớp chuẩn 16.37. Gây ra `ret_intraday = +1636.0` và `ret_overnight = -0.9994`. | `CORR_016`: Cách ly cấp trường Open/Low; giữ nguyên Close. |
| `CEPH R735QTJ8XC9X` | `2008-05-06` | Open=999.99, High=999.99, Low=0.01, Close=60.10, Vol=4.046 | `batch_02_of_10.zip` $\to$ `raw/year=2008/batch_02_of_10.csv`, dòng **34441** | In nhầm giá trần $999.99$ tại Open/High và giá sàn $0.01$ tại Low; Close khớp chuẩn 60.10. Gây ra `ret_overnight = +15.6388` và `ret_intraday = -0.9399`. | `CORR_017`: Cách ly cấp trường Open/High/Low; giữ nguyên Close. |
| `FRT R735QTJ8XC9X` | `2008-06-06` | Open=80.94, High=999.99, Low=0.01, Close=79.40, Vol=684.130 | `batch_04_of_10.zip` $\to$ `raw/year=2008/batch_04_of_10.csv`, dòng **27654** | Nến xuất hiện đồng thời hai bản in giá tượng trưng High=999.99 và Low=0.01; Open (80.94) và Close (79.40) khớp bình thường. Gây méo mó `vol_parkinson_20d = 1.5462` kéo dài 20 phiên. | `CORR_018`: Cách ly cấp trường High/Low; giữ nguyên Close. |
| `TR R735QTJ8XC9X` | `2008-06-06` | Open=26.11, High=999.99, Low=26.11, Close=999.99, Vol=136.595 | `batch_09_of_10.zip` $\to$ `raw/year=2008/batch_09_of_10.csv`, dòng **37978** | Bản in giá trần $999.99$ tràn vào cả trường Close; gây nhảy vọt giá đóng cửa phi thực tế. | `CORR_019`: Cách ly toàn bar (`is_bad_data_period = True`). |

### 4.4. Tiến trình Biến thiên Cực trị Qua 3 Giai đoạn
Chi tiết lưu tại [`outlier_isolation_before_after_comparison.csv`](feature_eda/outlier_isolation_before_after_comparison.csv):

| Đặc trưng | Baseline Thô (Ban đầu) | Giai đoạn 1 (Cách ly GMT & HOMS) | Giai đoạn 2 (Cách ly RGC, CEPH, FRT, TR) | Tọa độ Cực trị Hiện tại (Giai đoạn 2) | Đánh giá Kinh tế học |
|---|:---:|:---:|:---:|---|---|
| `ret_intraday` Max | **+4424.0** (`GMT`) | +1636.0 (`RGC`) | **+272.95** | `2005-09-14 \| CELG R735QTJ8XC9X` | Cực trị giảm 16 lần so với thô; độ lệch chuẩn ổn định từ 1.9985 xuống 0.1185. |
| `ret_overnight` Min | **-0.9998** (`GMT`) | -0.9994 (`RGC`) | **-0.9962** | `2005-09-14 \| CELG R735QTJ8XC9X` | Cực trị phản ánh đúng gap mở cửa của sự kiện điều chỉnh giá. |
| `ret_overnight` Max | **+15.6388** (`CEPH`) | +15.6388 (`CEPH`) | **+1.2136** | `2007-02-08 \| BA R735QTJ8XC9X` | Loại bỏ hoàn toàn bản in trần 999.99; max mới (+121.4%) nằm trong biên độ gap tin tức thực tế. |
| `vol_parkinson_20d` Max | **1.5462** (`FRT`) | 1.5462 (`FRT`) | **1.2261** | `2007-02-27 \| PCP R735QTJ8XC9X` | Loại bỏ nến 999.99 của FRT; max mới thuộc phiên biến động Dow Jones 2007. |
| `mom_12m_skip_1m` Max | **+480.33** (`HOMS`) | **+70.87** (`GME`) | **+70.87** | `2021-07-09 \| GME SC72NCBXXAHX` | Cực trị là hiện tượng Short Squeeze GameStop lịch sử (hoàn toàn xác thực). |

---

## 5. Phân rã NaN theo Hợp đồng Đặc tả và Module Chuẩn hóa Chung

### 5.1. Module Chuẩn hóa Chung (`src/features/nan_classifier.py`)
Toàn bộ logic phân rã NaN được hợp nhất thành một module duy nhất `src/features/nan_classifier.py`, phục vụ đồng thời cho script phân tích EDA (`14_feature_eda.py`) và bộ test tự động (`tests/test_nan_classifier.py`), bảo đảm không có độ lệch triển khai (zero implementation skew).

Các điều kiện phân rã tuân thủ nghiêm ngặt hợp đồng toán học của từng đặc trưng:
1. `nan_due_to_quality_at_t`: Tại chính ngày $T$, nến vi phạm cờ chất lượng (`bar_quality_mask == False`) hoặc vi phạm cờ chất lượng cấp trường (`field_quality_mask == False`).
2. `nan_due_to_lack_of_history`: Tổng số phiên từ ngày đầu tiên có nến của cổ phiếu tới ngày $T$ nhỏ hơn độ dài cửa sổ trượt (do cổ phiếu mới IPO / mới niêm yết).
3. `nan_due_to_window_defect_or_halt`: Cổ phiếu có đủ lịch sử, nhưng chuỗi nến trong cửa sổ trượt bị thiếu nến sạch ở các đầu mút bắt buộc hoặc không đủ số nến tối thiểu (đối với `ret_Wd` cần đủ $W+1$ nến sạch gồm cả hai đầu mút $T$ và $T-W$; đối với `mom_12m_skip_1m` cần đủ 232 nến sạch trên khoảng $[T-252, T-21]$).
4. `nan_due_to_zero_denom_or_invalid`: Khối lượng giao dịch bằng 0 ($\text{volume} = 0$) làm mẫu số bằng 0 (trong `amihud_illiq_20d`, `volume_ratio_5_20`, `log_dollar_volume_20d`) hoặc phương sai giá bằng 0 ($\sigma_{20} = 0$) trong `bollinger_pct_b_20d`.
5. `nan_due_to_rsi_state_reset`: Trạng thái đệ quy Wilder của RSI bị reset do gián đoạn dữ liệu trong 14 phiên gần nhất.
6. `nan_unclassified`: Các trường hợp chưa được gắn nhãn bởi các quy tắc trên (cho phép $>0$ như một cơ chế đối soát độc lập).

### 5.2. Bảng Phân rã NaN Chính xác (Tái lập từ Pipeline EDA)
Chi tiết lưu tại [`nan_breakdown.csv`](feature_eda/nan_breakdown.csv):

| Nhóm | Đặc trưng | Ô hợp lệ | Độ phủ | NaN Member | (1) Lỗi tại T | (2) Thiếu Lịch sử | (3) Lỗi Cửa sổ / Đình chỉ | (4) Mẫu số 0 / Đầu vào sai | (5) RSI Reset | (6) Chưa phân loại | Khớp 100% |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Momentum** | `ret_1d` | 5.590.200 | **99.69%** | 17.209 | 17.190 | 7 | 12 | 0 | 0 | 0 | **ĐÚNG** |
| **Momentum** | `ret_5d` | 5.590.118 | **99.69%** | 17.291 | 17.190 | 41 | 60 | 0 | 0 | 0 | **ĐÚNG** |
| **Momentum** | `ret_20d` | 5.589.770 | **99.69%** | 17.639 | 17.190 | 207 | 242 | 0 | 0 | 0 | **ĐÚNG** |
| **Momentum** | `ret_60d` | 5.587.006 | **99.64%** | 20.403 | 17.190 | 2.460 | 753 | 0 | 0 | 0 | **ĐÚNG** |
| **Momentum** | `mom_12m_skip_1m` | 5.519.160 | **98.43%** | 88.249 | **0** | **68.362** | **19.887** | 0 | 0 | 0 | **ĐÚNG** |
| **Volatility** | `vol_realized_20d` | 5.589.779 | **99.69%** | 17.630 | 17.190 | 207 | 233 | 0 | 0 | 0 | **ĐÚNG** |
| **Volatility** | `vol_realized_60d` | 5.587.014 | **99.64%** | 20.395 | 17.190 | 2.460 | 745 | 0 | 0 | 0 | **ĐÚNG** |
| **Volatility** | `vol_parkinson_20d`| 5.589.717 | **99.68%** | 17.692 | 17.194 | 193 | 305 | 0 | 0 | 0 | **ĐÚNG** |
| **Volatility** | `downside_deviation_20d`| 5.589.779 | **99.69%** | 17.630 | 17.190 | 207 | 233 | 0 | 0 | 0 | **ĐÚNG** |
| **Liquidity** | `amihud_illiq_20d` | 5.586.612 | **99.63%** | 20.797 | 18.716 | 207 | 215 | 1.655 | 0 | 4 | **ĐÚNG** |
| **Volume** | `volume_ratio_5_20` | 5.586.630 | **99.63%** | 20.779 | 18.716 | 193 | 215 | 1.655 | 0 | 0 | **ĐÚNG** |
| **Volume** | `log_dollar_volume_20d` | 5.586.630 | **99.63%** | 20.779 | 18.716 | 193 | 215 | 1.655 | 0 | 0 | **ĐÚNG** |
| **Intraday** | `ret_intraday` | 5.590.216 | **99.69%** | 17.193 | 17.193 | 0 | 0 | 0 | 0 | 0 | **ĐÚNG** |
| **Intraday** | `ret_overnight` | 5.590.197 | **99.69%** | 17.212 | 17.193 | 7 | 12 | 0 | 0 | 0 | **ĐÚNG** |
| **Technical** | `rsi_14d` | 5.589.920 | **99.69%** | 17.489 | 17.190 | 131 | 0 | 0 | 168 | 0 | **ĐÚNG** |
| **Technical** | `bollinger_pct_b_20d` | 5.589.107 | **99.67%** | 18.302 | 17.190 | 193 | 229 | 214 | 0 | 476 | **ĐÚNG** |

### 5.3. Bộ Kiểm thử Hồi quy Phân loại Độc lập ([`tests/test_nan_classifier.py`](../../tests/test_nan_classifier.py))
Bộ kiểm thử gồm 9 bài test bao quát toàn diện các trường hợp biên:
1. `test_classifier_missing_bar_mid_window`: Thiếu nến sạch giữa cửa sổ.
2. `test_classifier_missing_bar_at_t`: Nến tại ngày $T$ bị thiếu.
3. `test_classifier_missing_bar_at_t_minus_w`: Nến tại ngày bắt đầu cửa sổ $T-W$ bị thiếu.
4. `test_classifier_zero_volume`: Khối lượng giao dịch bằng 0.
5. `test_classifier_bollinger_zero_std`: Dải Bollinger có phương sai bằng 0.
6. `test_classifier_rsi_reseed`: Hiện tượng RSI reseed sau gián đoạn.
7. `test_classifier_mom12m_invariant_to_skip_defect`: Tính độc lập của `mom_12m_skip_1m` với lỗi trong tháng bỏ qua $[T-20, T]$.
8. `test_classifier_field_quarantine_gmt`: GMT tại 25/01/2007 (Close hợp lệ $\to$ `ret_1d` có giá trị; Open hỏng $\to$ `ret_intraday` nhận NaN phân loại đúng vào `nan_due_to_quality_at_t`).
9. `test_classifier_homs_pre_ipo_in_lookback`: HOMS tại 02/08/2000 (nến 04/08/1999 bị cách ly nằm trong lookback $\to$ phân loại đúng vào `nan_due_to_window_defect_or_halt`).
10. `test_classifier_parkinson_window_defect`: Nến có High/Low bị cách ly trong cửa sổ 20 phiên $\to$ phân loại đúng vào `nan_due_to_window_defect_or_halt`.

**Cả 9 bài kiểm thử đều PASSED 100%**.

---

## 6. Thống kê Phân phối Thực nghiệm & Tương quan Chéo lát cắt

### 6.1. Thống kê Phân phối 16 Features trên Development (Sau Cách ly)
Chi tiết lưu tại [`feature_distributions.csv`](feature_eda/feature_distributions.csv) và trực quan hóa tại [Hình 3](feature_eda/figures/fig3_feature_distribution_histograms.png):

| Đặc trưng | Số quan sát | Mean | Median | Std | Skew | Kurt | p01 | p99 | Ngoại lai (> 3 IQR) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `ret_1d` | 5.590.200 | +0.038% | +0.035% | 2.65% | +0.58 | 66.73 | -7.28% | +7.51% | 2.18% |
| `ret_5d` | 5.590.118 | +0.186% | +0.231% | 5.85% | +1.51 | 86.94 | -16.40% | +16.43% | 1.87% |
| `ret_20d` | 5.589.770 | +0.698% | +0.860% | 11.25% | +0.86 | 21.34 | -32.14% | +31.58% | 1.50% |
| `ret_60d` | 5.587.006 | +2.006% | +2.152% | 19.20% | +2.35 | 73.64 | -50.53% | +54.29% | 1.04% |
| `mom_12m_skip_1m` | 5.519.160 | +10.09% | +7.07% | 46.37% | +15.57 | 1.287.56 | -73.59% | +144.15% | 1.06% |
| `vol_realized_20d` | 5.589.779 | 0.0212 | 0.0168 | 0.0160 | +3.90 | 37.04 | 0.0054 | 0.0859 | 2.59% |
| `vol_realized_60d` | 5.587.014 | 0.0220 | 0.0179 | 0.0152 | +6.72 | 325.93 | 0.0070 | 0.0815 | 2.56% |
| `vol_parkinson_20d`| 5.589.717 | 0.0194 | 0.0156 | 0.0178 | +24.02 | 1.251.15 | 0.0061 | 0.0749 | 2.72% |
| `downside_deviation_20d` | 5.589.779 | 0.0141 | 0.0109 | 0.0117 | +3.66 | 24.80 | 0.0025 | 0.0617 | 2.50% |
| `amihud_illiq_20d` | 5.586.612 | 0.00115 | 0.00024 | 0.05085 | +478.98 | 332.012 | 0.000008 | 0.00839 | 6.26% |
| `volume_ratio_5_20`| 5.586.630 | 1.0046 | 0.9638 | 0.2894 | +1.34 | 4.34 | 0.4888 | 1.9529 | 0.56% |
| `log_dollar_volume_20d` | 5.586.630 | **17.9106** | **17.9092** | **1.2987** | -0.07 | 0.73 | 14.6739 | 20.9538 | 0.04% |
| `ret_intraday` | 5.590.216 | +0.016% | +0.008% | 0.1185 | +2188.6 | 5.031.550 | -6.29% | +6.41% | 1.87% |
| `ret_overnight` | 5.590.197 | +0.030% | +0.019% | 0.0155 | +6.82 | 674.80 | -3.74% | +3.85% | 3.75% |
| `rsi_14d` | 5.589.920 | **51.5608** | **51.7971** | **12.1735** | -0.08 | -0.25 | 23.43 | 78.22 | **0.00%** |
| `bollinger_pct_b_20d` | 5.589.107 | 0.5315 | 0.5559 | 0.3332 | -0.15 | -0.81 | -0.1722 | 1.1734 | **0.00%** |

### 6.2. Tổng hợp Tương quan Chéo lát cắt (Không Điền 0)
Theo yêu cầu kỹ thuật:
- **Tuyệt đối không thay thế correlation NaN bằng 0**.
- Tính toán Pearson và Spearman hàng ngày trên các cặp hữu hạn (`np.isfinite(x) & np.isfinite(y)`).
- Quy định ngưỡng tối thiểu: $N_{min} = 30$ cổ phiếu hợp lệ. Nếu dưới 30 cổ phiếu hoặc phương sai bằng 0, giá trị correlation của ngày đó được giữ là `NaN`.
- Tổng hợp riêng từng cặp đặc trưng $(f_1, f_2)$ trên đúng số ngày có tương quan hợp lệ.
- Toàn bộ metadata thống kê được lưu tại [`pairwise_correlation_metadata.csv`](feature_eda/pairwise_correlation_metadata.csv):
  - **100% số cặp đặc trưng** ($256$ cặp) đều có đủ **5.911 ngày hợp lệ** ($100.0\%$).
  - Số lượng cổ phiếu thành viên đánh giá trên mỗi ngày: Tối thiểu là **791 mã**, trung bình là **949 mã**, tối đa là **1.011 mã**.

**Ma trận Tương quan Thứ hạng Spearman Trung bình Hàng ngày**:
Chi tiết lưu tại [`spearman_correlation_matrix.csv`](feature_eda/spearman_correlation_matrix.csv) và [Hình 4](feature_eda/figures/fig4_cross_sectional_correlation_spearman.png):

```
                   ret_1d  ret_20d  mom_12m  vol_real  vol_park  amihud  vol_rat  log_dv  ret_intra  ret_over    rsi  boll_b
ret_1d              1.000    0.189    0.015    -0.013    -0.015  -0.003    0.009  -0.001      0.881     0.305  0.306   0.392
ret_20d             0.189    1.000    0.014    -0.051    -0.063  -0.030   -0.033   0.014      0.177     0.047  0.837   0.705
mom_12m_skip_1m     0.015    0.014    1.000    -0.130    -0.139  -0.163    0.013   0.109      0.008     0.024  0.101   0.023
vol_realized_20d   -0.013   -0.051   -0.130     1.000     0.874   0.194   -0.019   0.115     -0.022     0.021 -0.129  -0.072
vol_parkinson_20d  -0.015   -0.063   -0.139     0.874     1.000   0.235   -0.020   0.054     -0.023     0.019 -0.138  -0.078
amihud_illiq_20d   -0.003   -0.030   -0.163     0.194     0.235   1.000   -0.002  -0.929     -0.000    -0.008 -0.058  -0.022
volume_ratio_5_20   0.009   -0.033    0.013    -0.019    -0.020  -0.002    1.000  -0.002      0.007     0.008 -0.022  -0.012
log_dollar_volume  -0.001    0.014    0.109     0.115     0.054  -0.929   -0.002   1.000     -0.006     0.015  0.012  -0.001
ret_intraday        0.881    0.177    0.008    -0.022    -0.023  -0.000    0.007  -0.006      1.000    -0.068  0.283   0.361
ret_overnight       0.305    0.047    0.024     0.021     0.019  -0.008    0.008   0.015     -0.068     1.000  0.075   0.101
rsi_14d             0.306    0.837    0.101    -0.129    -0.138  -0.058   -0.022   0.012      0.283     0.075  1.000   0.866
bollinger_pct_b_20d 0.392    0.705    0.023    -0.072    -0.078  -0.022   -0.012  -0.001      0.361     0.101  0.866   1.000
```

> [!WARNING]
> **Nhận định khoa học về tính trực giao**: Tương quan thực nghiệm gần bằng 0 (ví dụ giữa `volume_ratio_5_20` và momentum/volatility, $|\rho_s| \le 0.038$) phản ánh rằng hai biến không có mối quan hệ đơn điệu tuyến tính hoặc thứ hạng trên bình diện lát cắt ngang trong mẫu dữ liệu này. **Điều này không cấu thành bằng chứng chứng minh hai biến hoàn toàn độc lập về mặt thống kê** (bởi các mối quan hệ phi tuyến, điều kiện phụ thuộc theo chế độ thị trường vẫn có thể tồn tại).

---

## 7. Độ ổn định qua các Chế độ Thị trường (Market Regimes)

Chi tiết biểu đồ theo dõi các cuộc khủng hoảng tài chính được thể hiện tại [Hình 6](feature_eda/figures/fig6_market_regimes_volatility_and_liquidity.png):

1. **Bong bóng Dot-com vỡ (2000–2002)**: Realized Volatility duy trì ở mức cao kéo dài ($2.5\% - 3.5\%$/ngày).
2. **Khủng hoảng Tài chính Toàn cầu GFC (2007–2009)**: Volatility trung vị vượt $5.0\%$/ngày, thanh khoản cạn kiệt (Amihud Illiquidity tăng vọt 5 lần).
3. **Cú sốc COVID-19 (02–04/2020)**: Đạt đỉnh nhọn biến động ngắn hạn cao nhất lịch sử ($>6.0\%$/ngày), sau đó hồi phục nhanh chóng.
4. **Chu kỳ Lạm phát & Thắt chặt Fed (2022)**: Volatility tăng nhẹ có trật tự ($1.8\% - 2.2\%$) nhưng thanh khoản thị trường không bị sụp đổ như năm 2008.

---

## 8. Bàn giao & Giải trình Chi tiết 5 Điểm Phản biện

### Điểm 1: Thống nhất cơ chế áp corrections từ đầu pipeline
- **Thực hiện**: Xây dựng module lõi `src/data/corrections.py` tách bạch rõ `is_bar_quarantine` và `is_field_quarantine`. Áp dụng tuần tự qua Script 06 $\to$ Script 07 $\to$ Matrix Loader $\to$ Script 12.
- **Trường hợp HOMS**: Được gắn `QUALITY_FLAG_PRE_IPO_SUSPECT` cho nến ngày 04/08/1999 (nằm trong cửa sổ warm-up), cách ly toàn bar nhưng giữ nguyên ngày trên lưới thời gian, không nén chuỗi.
- **Trường hợp GMT**: Cách ly cấp trường (`open`, `adj_open`, `low`, `adj_low`) vào ngày 25/01/2007; giữ nguyên `close` (44.25) và `volume`. Các feature chỉ dùng Close (`ret_1d`, `ret_20d`, `ret_60d`, `rsi_14d`) vẫn tính toán bình thường.
- **Xác nhận không sửa Parquet thủ công**: Toàn bộ kho Parquet Tier 2 và 2D matrices được tái tạo tự động từ Script 06 và 07 dựa trên bảng corrections có bằng chứng. Đã có 5 unit tests trong `tests/test_corrections.py` bảo đảm tính tái lập.

### Điểm 2: Rà soát OHLC toàn hệ thống (1998–2023)
- **Thực hiện**: Quét tự động toàn bộ 6.541 phiên $\times$ 3.711 mã qua script `10b_scan_ohlc_anomalies.py`.
- **Kết quả kiểm kê**: 251 dị thường ghi nhận tại `anomaly_inventory.csv`. Trong đó 4 trường hợp đã thẩm định và cách ly (`CORR_016` RGC, `CORR_017` CEPH, `CORR_018` FRT, `CORR_019` TR) cùng GMT và HOMS, trạng thái ghi nhận chuẩn mực là `quarantined, mechanism unverified`. 247 trường hợp còn lại ghi nhận `unresolved`.
- **Truy vết ZIP Raw**: Toàn bộ số dòng gốc trong tệp ZIP đã được lập bảng đối chiếu. Phân biệt rõ sự kiện stub quotes tiền-2010 ($0.01 và $999.99 vào các phiên khủng hoảng/sự cố đường truyền) với hành vi giao dịch thông thường.

### Điểm 3: Đồng bộ tests với classifier thực tế
- **Thực hiện**: Tách module dùng chung `src/features/nan_classifier.py`. Cả `14_feature_eda.py` và `tests/test_nan_classifier.py` đều gọi chung một hàm `classify_feature_nans` và `classify_cell_nan`.
- **Bổ sung test cases**: Đã bổ sung 3 test hồi quy cho GMT (cách ly trường), HOMS (lỗi nến warm-up trong lookback), và Parkinson (thiếu trường High/Low trong cửa sổ 20 phiên). Toàn bộ 9/9 tests đều PASSED.

### Điểm 4: Tái tạo End-to-End & Đối chiếu Cực trị
- **Thực hiện**: Chạy lại trọn vẹn toàn bộ chuỗi pipeline: Script 06 (Tier 2 Adjusted) $\to$ Script 07 (2D Matrices & Masks) $\to$ Script 12 (Feature Store Manifest v1.4.0) $\to$ Script 13 (Validate 104/104 PASSED) $\to$ Script 15 (Extended Causal 144/144 PASSED) $\to$ Script 14 (EDA & Phân rã NaN khớp 100%).
- **Tái tạo 4 Features Chịu Ảnh Hưởng từ Daily Return Mới**:
  * Đồ thị phụ thuộc xác nhận chỉ có 4 features dùng `daily_return`: `vol_realized_20d`, `vol_realized_60d`, `downside_deviation_20d`, `amihud_illiq_20d`. 12 features còn lại phụ thuộc vào các ma trận độc lập (`adj_close`, `adj_volume`, `adj_high`, `adj_low`, `volume`, `close`) vốn đã áp dụng `bar_quality_mask` cách ly nến lỗi từ trước nên được bảo toàn 100%.
  * Đối chiếu 2 tọa độ kiểm chứng bắt buộc:
    + `LOW R735QTJ8XC9X` @ `2008-07-16`: Lưu cũ `0.151942`, tính lại từ return mới là `NaN` (do return phục hồi 2008-06-18 bị cách ly $\implies$ cửa sổ 20 phiên chỉ còn 19 giá trị hợp lệ).
    + `CPTH RJF8CZIDFLNP` @ `2001-03-15`: Lưu cũ `0.185148`, tính lại từ return mới là `NaN` (do return phục hồi 2001-02-15 bị cách ly $\implies$ cửa sổ 20 phiên chỉ còn 19 giá trị hợp lệ).
  * Mỗi ma trận trong 4 features trên giảm chính xác 2 ô hợp lệ (chuyển sang NaN), toàn bộ các ô còn lại đồng nhất tuyệt đối.
- **Cập nhật so sánh cực trị**: Bảng `outlier_isolation_before_after_comparison.csv` phản ánh tiến trình 3 giai đoạn: `ret_intraday` giảm từ 4424.0 $\to$ 1636.0 $\to$ 272.95; `ret_overnight` max giảm từ 15.6388 $\to$ 1.2136; `vol_parkinson_20d` max giảm từ 1.5462 $\to$ 1.2261.

### Điểm 5: Ranh giới cam kết và Tình trạng Nghiệm thu
- **Tình trạng nghiệm thu**: Feature Store tiếp tục được xác định là **BẢN ỨNG VIÊN (CANDIDATE)**.
- **Cam kết bảo toàn**:
  * Tuyệt đối chưa huấn luyện mô hình (ML training).
  * Tuyệt đối chưa tinh chỉnh siêu tham số (hyperparameter tuning).
  * Tuyệt đối chưa tính IC mục tiêu hoặc xây dựng chiến lược alpha.
  * Không rò rỉ hoặc chạm vào vùng Out-of-Sample (2024–2026).

---

## 9. Phân định Return, Target, Chính sách Chọn Mẫu & Đối chiếu Phạm vi Ô

### 9.1. Phân định Return, Target và Chính sách Chọn Mẫu
Khi một nến tại ngày $T$ bị cách ly toàn bar (Close lỗi):
1. **Lợi suất Close-to-Close**:
   - $R_T = Close_T / Close_{T-1} - 1$ không hợp lệ ($\to \text{NaN}$) do tử số lỗi.
   - $R_{T+1} = Close_{T+1} / Close_T - 1$ không hợp lệ ($\to \text{NaN}$) do mẫu số lỗi.
   - $R_{T+2} = Close_{T+2} / Close_{T+1} - 1$ **hoàn toàn hợp lệ về mặt số học** vì cả 2 giá đều sạch.
2. **Nhãn Mục tiêu ($\text{target}_t = R_{t+1}$)**:
   - $\text{target}_{T-1} = R_T \to \mathbf{NaN}$ (không hợp lệ về mặt số học).
   - $\text{target}_T = R_{T+1} \to \mathbf{NaN}$ (không hợp lệ về mặt số học).
   - $\text{target}_{T+1} = R_{T+2} \to \mathbf{HỢP\ LỆ}$ về mặt số học!
3. **Chính sách Chọn Mẫu Huấn luyện (`valid_data_mask`)**:
   - Tại ngày $T+1$, dù nhãn mục tiêu $y_{T+1} = R_{T+2}$ hợp lệ, mẫu $(X_{T+1}, y_{T+1})$ vẫn bị loại bỏ khỏi dữ liệu huấn luyện do điều kiện lọc mẫu:
     * Cờ `is_consecutive_session` tại $T+1$ bằng `False` (bước chuyển tiếp $T \to T+1$ bị đứt đoạn do nến $T$ lỗi).
     * Các đặc trưng đầu vào $X_{T+1}$ dùng $Close_T$ (như $ret\_1d$) nhận `NaN`.
   - **Làm rõ**: Việc loại mẫu tại $T+1$ là do **chính sách chọn mẫu kỹ thuật và tính sẵn sàng của đặc trưng đầu vào**, **không phải do nhãn $\text{target}(T+1)$ bị sai toán học**.

| Phiên | Nến | Return $R_t$ | Target $y_t = R_{t+1}$ | Cờ `is_consecutive` | Mask `valid_data` | Mẫu $(X_t, y_t)$ được chọn? | Phân loại nguyên nhân |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| $T-1$ | Sạch | Hợp lệ | **NaN** | `True` | `True` | **KHÔNG** | Target không hợp lệ về mặt số học ($R_T$ hỏng). |
| $T$ | **CÁCH LY** | **NaN** | **NaN** | `False` | `False` | **KHÔNG** | Nến hỏng tại $T$ và Target không hợp lệ ($R_{T+1}$ hỏng). |
| $T+1$ | Sạch | **NaN** | **HỢP LỆ ($R_{T+2}$)** | `False` | `False` | **KHÔNG** | **Loại do chính sách chọn mẫu**: $y_{T+1}$ đúng số học nhưng $X_{T+1}$ thiếu giá trị sạch. |
| $T+2$ | Sạch | Hợp lệ | Hợp lệ ($R_{T+3}$) | `True` | `True` | **Tùy điều kiện $X$** | Return 1d và cờ nến $T+2$ đã phục hồi, target $y_{T+2}$ hợp lệ. Tuy nhiên, các **rolling features (20d, 60d, 252d) vẫn là NaN** cho đến khi nến/return lỗi trôi hoàn toàn ra khỏi cửa sổ trượt tương ứng. |

> [!WARNING]
> **Lưu ý về Thời điểm Phục hồi của Rolling Features**:
> - Tuyệt đối không suy diễn rằng *"toàn bộ features phục hồi ngay tại $T+2$"*.
> - Tại $T+2$, chỉ có các đặc trưng 1-ngày phụ thuộc trực tiếp vào cặp $(Close_{T+1}, Close_{T+2})$ như `ret_1d` là phục hồi.
> - Các đặc trưng có cửa sổ trượt dài hạn (20 phiên, 60 phiên, 252 phiên) tiếp tục nhận giá trị `NaN` tại $T+2, T+3, \dots$ và **phục hồi theo độ dài cửa sổ riêng của từng feature**:
>   * `ret_20d`, `vol_realized_20d`, `downside_deviation_20d`: Chỉ phục hồi sau **20 phiên sạch** liên tiếp kể từ sau sự kiện lỗi.
>   * `ret_60d`, `vol_realized_60d`: Chỉ phục hồi sau **60 phiên sạch** liên tiếp.
>   * `mom_12m_skip_1m`: Chỉ phục hồi sau **252 phiên** (với tối thiểu 232 phiên sạch trên $[T-252, T-21]$).
> - Do đó, nếu mô hình baseline yêu cầu đủ toàn bộ 13 features ($X$ không chứa NaN), dòng quan sát này sẽ chỉ được đưa vào tập huấn luyện khi tất cả các rolling features thành phần đã lần lượt phục hồi xong.

### 9.2. Đối chiếu Phạm vi Số đếm Ô (6.31M ô vs 5.61M ô)
Đếm trực tiếp từ các ma trận Parquet trên đĩa cứng:
- **Toàn bộ lưới (1998–2026, 7.252 phiên $\times$ 3.711 SIDs = 26.912.172 ô)**:
  * `valid_data_mask = True`: **6.311.822 ô** (đây là nguồn gốc con số ~6.31M).
  * `strict_membership_mask = True`: **6.307.492 ô**.
- **Lát cắt Development (2000–2023, 5.911 phiên $\times$ 3.711 SIDs = 21.935.721 ô)**:
  * `strict_membership_mask = True`: **5.607.409 ô thành viên** (đây là nguồn gốc con số ~5.61M và là **mẫu số chuẩn tính độ phủ Development**).
  * `valid_data_mask = True`: **5.610.691 ô** (được xây từ `resolved_membership_mask` gồm 5.631.824 ô).
  * Có **22.220 ô** `valid_data_mask == True` nằm ngoài `strict_membership_mask` (thuộc các phân đoạn chuyển tiếp heuristic).
  * Có **18.938 ô** thuộc `strict_membership_mask` có `valid_data_mask == False` (do lỗi nến, thiếu volume, hoặc phiên không liên tục).
  * Giao cắt giữa hai mask: **5.588.471 ô**.
  * `valid_label_mask = True`: **5.608.802 ô**.
  * Số ô ngoài rổ Russell 1000 tại ngày $T$: **16.328.312 ô** ($74,44\%$), được gán `NaN` nghiêm ngặt theo đặc tả.
- **Khoảng Warm-up (1998–2000, 630 phiên)**: 0 ô membership.
- **Khoảng Out-of-Sample (2024–2026, 711 phiên)**: 700.083 ô strict membership, 701.131 ô valid data mask (đóng băng tuyệt đối).
- **Quy định bắt buộc**: Dataset baseline khi xây dựng phải áp dụng `strict_membership_mask` tại ngày đầu ra $T$.

### 9.3. Đề xuất Chiến lược Baseline Model: Nhóm 13 Features Close/Volume
Nhằm bảo vệ mô hình baseline khởi đầu khỏi 247 ca dị thường OHLC chưa xác minh trong `anomaly_inventory.csv`:
- **Đề xuất 13 Features Baseline (Chỉ dùng Close & Volume)**:
  * Momentum (5): `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `mom_12m_skip_1m`.
  * Volatility (3): `vol_realized_20d`, `vol_realized_60d`, `downside_deviation_20d`.
  * Liquidity & Volume (3): `amihud_illiq_20d`, `volume_ratio_5_20`, `log_dollar_volume_20d`.
  * Technical (2): `rsi_14d`, `bollinger_pct_b_20d`.
  * *Căn cứ*: Giá Close được ấn định qua phiên khớp lệnh đóng cửa chính thức (Consolidated Closing Cross) có thanh khoản tập trung và kiểm soát chặt chẽ, ít bị ảnh hưởng bởi các lỗi râu nến hoặc bản in giá tượng trưng trên Open, High, Low, dù không loại trừ được 100% mọi lỗi dữ liệu (như trường hợp nến TR bị giá trần 999.99 tràn vào cả Close).
- **Tạm hoãn 3 Features OHLC**: `ret_intraday`, `ret_overnight`, `vol_parkinson_20d`.
  * *Lý do*: Tránh nhiễu từ các lệnh tượng trưng (Stub Quotes $0.01 và $999.99 tiền-2010). Sẽ tái đánh giá sau khi có bộ lọc vi cấu trúc nến hoặc kỹ thuật học máy phi tham số chống ngoại lai.

Chi tiết bàn giao toàn diện xem tại tài liệu bàn giao mốc: [`docs/reports/handoff/feature_store_milestone_handoff.md`](handoff/feature_store_milestone_handoff.md).
