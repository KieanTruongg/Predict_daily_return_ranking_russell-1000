# Bối Cảnh Chuyển Đổi Pipeline & Mức Độ Sẵn Sàng Cho Feature Engineering (Bước ⑦)
## Pipeline Migration & Feature Readiness Context

> **Tài liệu tham chiếu nội bộ**: Dành cho các thành viên nhóm nghiên cứu định lượng và phát triển mô hình.  
> **Ngày cập nhật**: 2026-11-05  
> **Trạng thái**: Đã chuẩn hóa thư viện nền tảng, hoàn tất kiểm thử hồi quy các trường hợp biên, đang trong giai đoạn thảo luận và chuẩn bị đặc tả thử nghiệm Pilot Feature Engineering.

---

## 1. Các Quyết Định Thiết Kế Đã Chốt (Frozen Architectural Decisions)

Các quyết định dưới đây đã được thảo luận, kiểm chứng thực nghiệm và chốt cố định trong kiến trúc phần mềm, không thay đổi tùy tiện trong quá trình phát triển mô hình:

### 1.1. Cấu Trúc Dữ Liệu Tọa Độ 2D (Wide Matrix Grid)
- Toàn bộ dữ liệu giá, khối lượng, lợi suất và mặt nạ được tổ chức dưới dạng **Ma trận 2D** kích thước cố định:
  $$\mathbf{M} \in \mathbb{R}^{T 	imes N}, \quad T = 7.252 	ext{ phiên giao dịch NYSE}, \quad N = 3.711 	ext{ mã Canonical SID}$$
- **Hàng (Index)**: Trục thời gian là `pd.DatetimeIndex` chuẩn gồm 7.252 ngày giao dịch (1998-01-02 đến 2026-10-30), không bỏ sót phiên và không có phiên trùng lặp.
- **Cột (Columns)**: Định danh chứng khoán duy nhất `canonical_sid` (ví dụ: `AAPL R735QTJ8XC9X`), ánh xạ từ 4.737 dòng mapping thô. Không dùng Ticker thô làm khóa chính để triệt tiêu lỗi do đổi ticker hoặc ticker tái sử dụng (*ticker reuse*).

### 1.2. Quy Ước Niên Độ Thành Viên Point-In-Time (PIT Membership)
- Danh mục thành viên năm $Y$ từ snapshot thường niên có hiệu lực trong khoảng thời gian:
  $$	ext{Effective Window}(Y) = [01/07/Y, \; 30/06/Y+1]$$
- Không suy diễn tư cách thành viên từ việc có dòng giá trên sàn. Một chứng khoán có thể giao dịch bình thường trên sàn NYSE/NASDAQ nhưng chỉ được coi là thành viên khi nằm trong khoảng thời gian có hiệu lực của rổ chỉ số.

### 1.3. Phân Vùng Thời Gian & Quy Định Đóng Băng Dữ Liệu Ngoài Mẫu (OOS)
- **Warm-up (Khởi động)**: 1998-01-02 đến 2000-06-30 (**630 phiên**). Dùng để tích lũy lịch sử trượt dài hạn (như biến động 60 ngày, momentum 252 ngày). Giai đoạn này không dùng để tính nhãn hay đánh giá mô hình.
- **Development (Phát triển)**: 2000-07-01 đến 2023-12-29 (**5.911 phiên**). Dùng cho toàn bộ nghiên cứu: EDA, trích xuất đặc trưng, chia tập huấn luyện/kiểm thực (train/validation) theo chuỗi thời gian, lựa chọn mô hình và tinh chỉnh siêu tham số.
- **Out-of-Sample (OOS)**: 2024-01-02 đến 2026-10-30 (**711 phiên**).
  - *Chính sách phương pháp luận*: Tuyệt đối không dùng dữ liệu OOS để lựa chọn đặc trưng (feature selection), định hình kiến trúc mô hình hay tinh chỉnh siêu tham số (tuning). Điều này không đồng nghĩa với việc dữ liệu chưa từng được quét qua ở khâu tiền xử lý (các kiểm tra kỹ thuật về cú pháp, schema bảng và lịch ngày đã xử lý toàn bộ dải 1998–2026 để bảo đảm tính tương thích hạ tầng).
  - *Cơ chế kỹ thuật trong phần mềm*: Thư viện nạp ma trận tích hợp kiểm tra tự động kích hoạt ngoại lệ `OOSFreezeViolationError` nếu có truy vấn vượt quá mốc `2023-12-29` mà không có cờ cho phép chuyên biệt.

### 1.4. Kiến Trúc Phân Tầng Mặt Nạ (Three-Layer Mask Decoupling)
Để bảo vệ toàn vẹn dữ liệu và tránh hiện tượng mất dữ liệu khởi động (*cold-start*), hệ thống phân tách rõ 3 tầng mặt nạ:
1. **`bar_quality_mask` (Input Hygiene - Làm sạch đầu vào)**:
   - Độc lập 100% với tư cách thành viên chỉ số.
   - Định nghĩa: $	ext{has\_bar} \land 
eg 	ext{is\_bad\_data\_period} \land 
eg 	ext{is\_spinoff\_discontinuity}$.
   - Dùng để gán `NaN` vào các ô lỗi của ma trận giá/lợi suất trước khi thực hiện các phép tính trượt (*rolling calculations*).
   - **Bảo tồn lịch sử warm-up**: Các phiên giao dịch hợp lệ trước ngày cổ phiếu gia nhập Russell 1000 được giữ nguyên vẹn để phục vụ warm-up cho các mã đã niêm yết đủ thời gian. Cần lưu ý rằng cơ chế này không bảo đảm 100% đầy đủ cho mọi mã, bởi các cổ phiếu mới phát hành (IPO) hoặc mới niêm yết chưa đủ số phiên lookback vẫn sẽ nhận giá trị `NaN` hợp lệ theo quy tắc `min_periods = W`.
2. **`membership_mask` (Output Mask - Lọc đầu ra tại ngày T)**:
   - Xác định tư cách thành viên rổ chỉ số tại ngày hiện tại $t$.
   - **Chỉ áp dụng tại ngày đầu ra $t$**. Nếu tại ngày $t$, cổ phiếu là thành viên và đã có đủ lịch sử sạch từ các phiên trước đó, đặc trưng được tính toán hợp lệ ngay từ ngày đầu tiên gia nhập rổ.
3. **`valid_label_mask` (Target Mask - Dành riêng cho nhãn học máy)**:
   - Đại diện cho việc có thanh nến hợp lệ tại ngày $t$ và có lợi suất ngày tiếp theo tại $t+1$.
   - **Tuyệt đối không dùng `valid_label_mask` để lọc đầu vào đặc trưng** nhằm loại trừ hoàn toàn nguy cơ rò rỉ dữ liệu tương lai (*look-ahead leakage*).

### 1.5. Công Thức Chuẩn Hóa Xếp Hạng Chéo (Cross-Sectional Uniform Rank)
- Thống nhất áp dụng công thức ánh xạ đều về khoảng $[0.0, 1.0]$:
  $$	ext{rank}_{	ext{norm}, i, t} = egin{cases} \dfrac{	ext{rank}_{i, t} - 1}{N_t - 1} & 	ext{khi } N_t > 1 \ 0.5 & 	ext{khi } N_t = 1 \ 	ext{NaN} & 	ext{khi } N_t = 0 \end{cases}$$
- Đồng hạng (*ties*) mặc định giải quyết bằng phương pháp trung bình (`method='average'`).
- Các chứng khoán ngoài mặt nạ thành viên hoặc có giá trị khuyết thiếu giữ nguyên `NaN`, tuyệt đối không điền 0 hay hằng số.
- **Tính chất toán học & rủi ro**: Phép biến đổi thứ tự này chỉ chuẩn hóa phân phối về dạng đều tại từng ngày, **không triệt tiêu rủi ro thị trường (Market Beta) hay rủi ro ngành**. Nó không tương đương với phép hồi quy trung hòa nhân tố; tương quan giữa các chứng khoán vẫn chịu tác động của các biến động hệ thống chung.

### 1.6. Minh Bạch Hóa Loại Lợi Suất & Giá (Explicit Return/Price Contracts)
- Các lớp tính đặc trưng yêu cầu chỉ định rõ ràng loại giá/lợi suất đầu vào (ví dụ: `price_type="total_return"` hoặc `price_type="adjusted_close"` trong `TotalReturnMomentumFeature`; `return_type="daily_return"` hoặc `return_type="total_return"` trong `RealizedVolatilityFeature`).
- Nghiêm cấm cơ chế tự động chuyển đổi ngầm (*silent fallback*) khi thiếu cột dữ liệu.

---

## 2. Các Nội Dung Đã Xác Minh Thực Tế (Empirically Verified Work)

Hệ thống phân biệt rõ ràng giữa 3 cấp độ thẩm định:
1. **Kiểm thử phần mềm (Software Test Verification)**: Bộ 32 bài test tự động pass xác nhận mã nguồn vận hành đúng logic toán học và các quy ước kỹ thuật.
2. **Tính nhất quán nội bộ (Internal Data Consistency)**: Lưới tọa độ $7.252 	imes 3.711$ không có duplicate primary key, các ma trận mask thỏa mãn quan hệ tập con phân cấp nghiêm ngặt.
3. **Xác minh nguồn thực tế (External Source Verification)**: Dữ liệu lịch sử phụ thuộc vào snapshot định kỳ của bên thứ ba; các trường hợp nối mã dựa trên heuristic $\le 10$ ngày lịch và đối chiếu một phần hồ sơ doanh nghiệp (SEC Form 8-K/10-K), không tuyên bố là "Ground Truth tuyệt đối 100%".

| Hạng mục kiểm chứng | Kết quả xác minh thực tế | Bằng chứng kiểm thử / Tệp đối chiếu |
|---|---|---|
| **Bộ kiểm thử chuẩn** | **32/32 tests PASSED** (thời gian chạy ~3.8s) | Lệnh `python -m pytest -q` |
| **Trích xuất Universe độc lập** | Chạy độc lập 100% từ local CLI, không phụ thuộc kho giá cũ. Xử lý sạch 27/27 năm snapshot, trích xuất đúng 2.884 PIT tickers và 26.919 lượt thành viên–năm, khớp hoàn toàn JSON gốc. | `scripts/01_pipeline/01_parse_all_universe.py` |
| **Thống nhất I/O Bước 03 & 04** | Cùng ghi ra và đọc vào một đường dẫn chuẩn duy nhất: `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` (13.147.389 dòng). | `tests/test_pipeline_integrity.py::test_05` |
| **Phân lập bảng kiểm toán** | Bước 04b xuất `temporal_mapping_heuristic_audit.csv` (10 cột); Bước 05 xuất `universe_constituent_temporal_mapping.csv` (9 cột). Không còn hiện tượng ghi đè schema. | `tests/test_pipeline_integrity.py::test_06` |
| **Tra cứu SID theo thời điểm** | `ticker_to_canonical_sids("AAPL", "1900-01-01")` trả về rỗng `[]` (triệt tiêu fallback lịch sử). Tra cứu năm 2020 trả về đúng SID active. | `tests/test_library_fixes.py::test_01, test_02` |
| **Phân vùng OOS an toàn** | Truy vấn thành viên năm 2020 không bị báo lỗi OOS giả (nhờ chỉ nạp slice development). Truy vấn năm 2025 bị chặn chính xác bởi `OOSFreezeViolationError`. | `tests/test_library_fixes.py::test_03, test_04` |
| **Vệ sinh cửa sổ chất lượng** | Mô phỏng bar lỗi ở giữa chuỗi giá: mọi cửa sổ trượt đi qua bar lỗi đều trả về `NaN`, cửa sổ sau khi thoát khỏi bar lỗi tự động tính toán lại bình thường. | `tests/test_library_fixes.py::test_05` |
| **Bảo toàn warm-up** | Cổ phiếu có lịch sử giao dịch trước khi vào rổ Russell 1000: tính được đặc trưng hợp lệ ngay tại Ngày 1 gia nhập rổ. Nếu lịch sử warm-up dính bar lỗi thì ngày gia nhập ra `NaN`. | `tests/test_library_fixes.py::test_09, test_10` |
| **Xóa nhãn ranh giới OOS** | Cơ chế purge ranh giới tại ngày 2023-12-29 xác nhận 100% nhãn bị gán `NaN`, triệt tiêu rò rỉ lợi suất phiên đầu năm 2024 vào tập Development. | `tests/test_library_fixes.py::test_08` |
| **Thống kê mô tả Development** | 5.610.691 quan sát hợp lệ (2000–2023); Excess Kurtosis giảm từ 3.428.210 xuống **66.88**; Biến động ngày **2.65%**; Max return **+227.87%** (MFA 2020); Min return **-94.97%** (LEH 2008). | `docs/reports/step6_eda_report.md` |

---

## 3. Các Giả Định Đang Chấp Nhận (Accepted Working Assumptions)

Trong quá trình xây dựng dữ liệu định lượng, một số giả định mang tính kỹ thuật đã được thống nhất chấp nhận để dự án có thể tiếp tục tiến triển mà không bị đình trệ:

1. **Giả định xấp xỉ chu kỳ tái cơ cấu thường niên:**
   - *Bản chất*: Quy ước thành viên cố định từ 01/07 năm $Y$ đến 30/06 năm $Y+1$ là một mô hình xấp xỉ Point-In-Time.
   - *Hạn chế chấp nhận*: Không phản ánh các đợt thêm/bớt đột xuất trong năm (ví dụ: công ty bị thâu tóm giữa kỳ hoặc đợt tái cơ cấu tháng 9/tháng 12).
2. **Bốn snapshot thiếu ngày chính xác trong hồ sơ lưu trữ:**
   - Các snapshot của các năm 2001, 2002, 2003, 2004 trên hồ sơ web chỉ lưu năm hoặc tháng mà không ghi rõ ngày. Giả định chấp nhận: áp dụng ngày hiệu lực chuẩn 01/07.
3. **Các ca ghép mã bằng Heuristic (Khoảng cách $\le 10$ ngày dương lịch):**
   - Bảng `canonical_security_mapping.csv` gồm đúng **4.737 dòng $\times$ 7 cột**, ánh xạ về **3.711 Canonical SID duy nhất**.
   - Trong đó có đúng **752 trường hợp mã tạm ` 2T`** được nối vào SID chính dựa trên điều kiện khoảng cách ngày dương lịch $\le 10$ ngày (`gap_calendar_days <= 10`), không phải 10 phiên giao dịch:
     - 456 trường hợp nối phía sau (`2T_STITCH_SUCCEEDING`).
     - 296 trường hợp nối phía trước (`2T_STITCH_PRECEDING`).
   - *Quy ước nghiên cứu*: Các trường hợp này được gắn nhãn giả định và được cách ly riêng trong báo cáo audit để phục vụ kiểm tra độ nhạy khi cần thiết.
4. **Cách ly gián đoạn Spin-off (KSU, SSP, COMS, PENN):**
   - Khi công ty mẹ chia tách công ty con quy mô lớn, giá cổ phiếu mẹ sụt giảm cơ học rất mạnh (ví dụ KSU giảm -96.66% vào 13/07/2000 do tách Stilwell Financial).
   - *Quy ước nghiên cứu*: Do kho dữ liệu hiện tại chưa có chuỗi giá độc lập của tài sản được tách ra để điều chỉnh tổng lợi nhuận (*Total Return*), các phiên này được cách ly bằng `is_spinoff_discontinuity = True` và lợi suất gán `NaN`. Cổ phiếu không bị loại khỏi rổ, nhưng các phiên gián đoạn không tham gia vào huấn luyện nhãn.
5. **Phân cấp độ tin cậy của 13 ca điều chỉnh dữ liệu (`CORR_001` đến `CORR_013`):**
   - *Mức 1 (Văn bản pháp lý cấp cao)*: Các ca reverse split và spinoff có đối chiếu hồ sơ SEC Form 8-K hoặc thông cáo FDIC (CHK, CRC, ADCT, AA, DYN, KSU, SSP, COMS, PENN, LEH, WM).
   - *Mức 2 (Băng giá & đối chiếu liên thị trường)*: Ca lỗi in giá SABR ($0.50), nến rác Markel ($26.10), xung đột mã LOW ($0.60).
   - *Mức 3 (Quan sát thống kê)*: Hiện tượng gián đoạn thanh khoản CPTH trong kỳ đình chỉ giao dịch.

---

## 4. Mốc bàn giao và lộ trình tiếp theo

Đã chốt thiết kế target/timing và 16 features ứng viên ngày 2026-11-05. Hai tài liệu chính:

- [Đặc tả features v1](specifications/features_v1.md).
- [Đặc tả target và timing v1](specifications/target_and_timing_v1.md).

Nếu kế hoạch cũ khác hai đặc tả này, dùng hai đặc tả làm căn cứ thiết kế và báo rõ chênh lệch code. Chốt thiết kế không đồng nghĩa đã triển khai hoặc kiểm chứng đầy đủ features.

Mốc bàn giao GitHub sau bước 1–3 gồm thư viện nền đã kiểm thử, tài liệu hiện hành và đặc tả. Không yêu cầu pilot trước mốc này.

- Bước 4: pilot số học và các tình huống dữ liệu theo mục 7 của đặc tả features; chưa tuning/training.
- Bước 5: kiểm tra features trên Development: coverage, phân phối, tương quan, IC; sau đó thiết kế train/validation theo thời gian và thử mô hình.
- Backtest cần đặc tả execution riêng; target v1 close-to-close không được coi trực tiếp là lợi nhuận có thể giao dịch.

Các báo cáo dữ liệu hiện có ghi nhận kết quả tại thời điểm tạo. Không xem nhãn VERIFIED trong CSV hoặc câu chuyện kinh tế hợp lý là bằng chứng mọi mức giá đã được xác minh độc lập. Nguồn corrections và diễn giải MFA còn cần rà theo mức bằng chứng.
