# Predict Daily Return Rankings

Dự án nghiên cứu ứng dụng học máy để dự đoán thứ hạng lợi suất ngày tiếp theo giữa các chứng khoán thuộc universe (danh mục thành phần) Russell 1000 theo từng thời kỳ. Dữ liệu được tổ chức theo cấu trúc tọa độ 2D (ngày giao dịch × định danh chứng khoán), kết hợp chuỗi giá lịch sử, sự kiện doanh nghiệp và danh sách thành viên rổ chỉ số theo năm.

Đây là đề tài phục vụ đồ án môn học CO3101 (Đồ án tổng hợp - Trí tuệ nhân tạo). Dự án tập trung vào phương pháp luận xử lý dữ liệu định lượng, bảo vệ tính trung thực lịch sử và thiết kế mô hình; nội dung chưa được kiểm chứng hay chứng minh là một hệ thống đầu tư có khả năng sinh lời trong thực tế.

---

## 1. Bài toán và phạm vi nghiên cứu

- **Bản chất bài toán:** Tại mỗi ngày giao dịch $t$, thị trường có một tập hợp nhiều chứng khoán đang lưu hành. Mô hình sử dụng các thông tin đã biết tính đến thời điểm dự đoán để dự báo thứ hạng tương đối của lợi suất ở phiên tiếp theo ($t+1$).
- **Dạng học máy:** Đây là bài toán xếp hạng chéo trên dữ liệu chuỗi thời gian (*cross-sectional ranking on time-series data*), không nhằm dự đoán mức giá tuyệt đối của từng cổ phiếu.
- **Đầu vào dự kiến:** Các đặc trưng (*features*) được trích xuất từ dữ liệu giá lịch sử, lợi suất nhiều kỳ lookback, khối lượng giao dịch, độ biến động và các chỉ số thanh khoản.
- **Đầu ra dự kiến:** Điểm số dự đoán (*predicted score/rank*) để xếp hạng các chứng khoán đủ điều kiện trong ngày từ thấp đến cao (thường chuẩn hóa về khoảng $[0, 1]$).
- **Phân biệt ranh giới nghiên cứu:**
  - *Điểm dự đoán (Prediction score):* Giá trị đầu ra thuần túy của thuật toán học máy.
  - *Tín hiệu alpha (Alpha signal):* Tín hiệu định lượng thể hiện kỳ vọng tương đối (có thể giữ nguyên hoặc áp dụng thêm các bước xử lý rủi ro như trung hòa ngành hay trung hòa thị trường tùy thuộc vào thiết kế chiến lược cụ thể; đây là bước xử lý tùy chọn, không bắt buộc của mọi mô hình).
  - *Danh mục giao dịch (Trading portfolio):* Vị thế thực tế sau khi tính đến chi phí giao dịch, phí vay cổ phiếu để bán khống, trượt giá (*slippage*) và hạn mức thanh khoản.
  - Khả năng dự đoán thứ hạng tốt (*Rank IC dương*) là điều kiện cần nhưng chưa đồng nghĩa với việc tạo ra lợi nhuận dương sau chi phí trong thực tế.
- **Quy ước thời điểm (Timing & Horizon):**
  - Features dùng thông tin đến hết T, dự đoán sau đóng cửa. Target v1 là rank lợi suất giá Close T → Close T+1, điều chỉnh split và chưa gồm cổ tức. Lịch khớp lệnh/backtest chưa chốt; không giả định vào lệnh tại Close T sau khi đã biết đủ dữ liệu T. Xem [đặc tả target/timing](docs/specifications/target_and_timing_v1.md).
- **Các giả định cần lưu ý:**
  - Phép xếp hạng chéo (*cross-sectional rank*) không tự động triệt tiêu hoàn toàn rủi ro thị trường (*beta*), sai số dữ liệu hoặc tác động của các giá trị ngoại lai cực đoan (*outliers*).
  - Dự án chưa ấn định bất kỳ mô hình cụ thể nào (như LightGBM, XGBoost hay Neural Networks) làm phương án chính thức; các thuật toán sẽ được đánh giá so sánh trong giai đoạn mô hình hóa.

---

## 2. Trạng thái hiện tại

Mốc bàn giao ngày 2026-11-05: [phạm vi, kiểm thử và giới hạn v1](docs/reports/handoff/handoff_v1_2026-11-05.md). Nhóm có thể bắt đầu triển khai features theo đặc tả; pilot là bước tiếp theo.

- **Đã triển khai:**
  - Thu thập và xử lý danh sách thành viên Russell 1000 giai đoạn 2000–2026 từ các nguồn lưu trữ lịch sử.
  - Trích xuất kho dữ liệu giá ngày thô (Raw OHLCV) và các sự kiện doanh nghiệp (chia tách, cổ tức).
  - Chuẩn hóa định danh chứng khoán canonical SID (*Security Identifier*) cho 3.711 mã duy nhất (từ 4.737 dòng mapping).
  - Điều chỉnh giá theo chia tách (backward split adjustment) và xử lý cờ chất lượng (*quality flags* cho bad ticks và gián đoạn spin-off).
  - Xây dựng kho ma trận 2D ($7.252 \times 3.711$) và các lớp mặt nạ Point-In-Time (PIT).
  - Hoàn thành phân tích khám phá dữ liệu (EDA) trên tập Development và điều tra 34 trường hợp lợi suất cực đoan.
  - Tái cấu trúc thư viện nền tảng (`src/`) theo hướng vector hóa trên ma trận 2D.
- **Đã kiểm thử:**
  - Chạy bộ kiểm thử tự động với lệnh `python -m pytest -q`.
  - Kết quả tại mốc bàn giao `281c410`: **32/32 tests passed** (bao gồm kiểm thử nạp ma trận, phân vùng thời gian, tính toàn vẹn đường dẫn, tra cứu PIT không fallback, bảo toàn warm-up và công thức uniform rank).
- **Còn giới hạn:**
  - Các ca nối mã bằng heuristic (khoảng cách ngày) vẫn cần tiếp tục kiểm chứng thêm với hồ sơ niêm yết.
  - Một số phiên có biến động giá cực đoan hoặc gián đoạn spin-off chưa có chuỗi giá độc lập hiện đang được cách ly tạm thời dưới dạng `NaN`.
- **Đang chuẩn bị:**
  - Đã chốt đặc tả 16 features ứng viên và target/timing v1; chuẩn bị pilot. Chưa chứng minh khả năng dự đoán của bộ features.
- **Chưa thực hiện ở pipeline mới:**
  - Chưa sinh toàn bộ kho feature store hoàn chỉnh.
  - Chưa huấn luyện mô hình, chưa tinh chỉnh siêu tham số và chưa thực hiện backtest danh mục đầu tư.

---

## 3. Nguồn dữ liệu và cách chia thời gian

### 3.1. Universe theo năm
- **Nguồn gốc:** Tổng hợp từ tài liệu lưu trữ của nhà cung cấp chỉ số (Frank Russell / FTSE Russell), báo cáo danh mục ETF iShares Russell 1000 (IWB) và các bản lưu trữ web lịch sử qua Wayback Machine.
- **Quy ước niên độ:** Danh sách năm $Y$ được áp dụng cho chu kỳ từ **01/07/Y đến 30/06/Y+1**.
- **Tính chất xấp xỉ:** Đây là xấp xỉ thường niên dựa trên snapshot; quy ước này không tái hiện được toàn bộ các đợt thêm/bớt đột xuất trong năm (*intra-year additions/deletions*) hoặc ngày hiệu lực chính thức của từng năm. Ngày snapshot chưa rõ được ghi như giả định nghiên cứu; không gán nhầm 2001–2004 là thiếu ngày. Nguồn 2026 có dấu ngày tháng 9 cần đối chiếu với khoảng dùng từ tháng 7 (chi tiết xem tại [`docs/reports/data_pipeline/data_lineage_report.md`](docs/reports/data_pipeline/data_lineage_report.md)).
- **Ticker vs. Chứng khoán:** 2.884 ticker duy nhất trong lịch sử snapshot không đồng nghĩa với 2.884 chứng khoán duy nhất, do hiện tượng một công ty đổi ticker hoặc cùng một ticker được tái cấp cho công ty khác ở các thời kỳ khác nhau.

### 3.2. Dữ liệu thị trường
- **Nguồn trích xuất:** Dữ liệu thanh nến ngày (OHLCV) và các sự kiện doanh nghiệp (splits, cash dividends) được trích xuất từ nền tảng QuantConnect Lean.
- **Bảo toàn lịch sử:** Lịch sử giao dịch của cổ phiếu được trích xuất cả ở các giai đoạn trước khi cổ phiếu gia nhập Russell 1000 nhằm giữ dữ liệu khởi động (*warm-up*) cho các phép tính rolling lookback dài ngày.
- **Nguyên tắc sử dụng:** Việc một cổ phiếu có dòng giá trong kho dữ liệu không đồng nghĩa với việc cổ phiếu đó được phép đưa vào universe tại mọi ngày; quyền tham gia phụ thuộc vào mặt nạ thành viên (*membership mask*).
- **Giá thô và giá điều chỉnh:** Dữ liệu điều chỉnh chia tách được dùng để tính toán lợi suất liên tục; dữ liệu giá thô được giữ nguyên vẹn trong kho để phục vụ đối chiếu kiểm toán.

### 3.3. Phân vùng thời gian
Tổng thể dữ liệu gồm **7.252 phiên giao dịch NYSE** từ 1998 đến 2026, được phân chia theo cấu hình tại [`configs/base_config.yaml`](configs/base_config.yaml):
- **Warm-up (Khởi động):** Từ 1998-01-02 đến 2000-06-30 (**630 phiên**). Dùng để tích lũy dữ liệu lịch sử lookback (ví dụ: momentum 252 ngày, độ biến động quá khứ). Giai đoạn này không dùng để tính nhãn hay đánh giá mô hình.
- **Development (Phát triển):** Từ 2000-07-01 đến 2023-12-29 (**5.911 phiên**). Dùng cho toàn bộ quá trình nghiên cứu: khám phá dữ liệu (EDA), thiết kế features, phân chia train/validation theo thời gian, lựa chọn mô hình và tinh chỉnh siêu tham số.
- **Out-of-Sample (OOS):** Từ 2024-01-02 đến 2026-10-30 (**711 phiên**). Phân vùng dữ liệu được đóng băng theo nguyên tắc phương pháp luận: tuyệt đối không dùng để lựa chọn đặc trưng (feature selection), định hình kiến trúc mô hình hay tinh chỉnh siêu tham số. Điều này không đồng nghĩa với việc dữ liệu chưa từng được quét qua ở khâu tiền xử lý (các kiểm tra kỹ thuật về cú pháp, schema bảng và lịch ngày đã xử lý toàn bộ dải 1998–2026 để bảo đảm tính tương thích hạ tầng). Việc truy cập ngoài mẫu trong quá trình nghiên cứu được kiểm soát bởi cơ chế chặn tự động trong thư viện nạp ma trận (`OOSFreezeViolationError`).

*Lưu ý:* Tập Development không phải là một tập huấn luyện duy nhất; việc phân chia cụ thể thành các fold huấn luyện/kiểm thực (train/validation splits hoặc walk-forward cross-validation) sẽ được quy định cụ thể trong giai đoạn xây dựng mô hình.

---

## 4. Pipeline tổng quan

Quy trình dữ liệu được tổ chức theo đồ thị luồng xử lý (DAG):

```
[Snapshots Universe] + [Dữ liệu thị trường Lean]
                    │
                    ▼
     [Hợp nhất và kiểm tra dữ liệu thô]
                    │
                    ▼
          [Chuẩn hóa định danh SID]
                    │
                    ▼
  [Xử lý Corporate Actions & Quality Flags]
                    │
                    ▼
     [Tái tạo Membership theo thời gian]
                    │
                    ▼
        [Trích xuất 2D Matrices & Masks]
                    │
                    ▼
    [Kiểm định Sanity & EDA Development] ◄─── (Kiểm toán & điều chỉnh nếu phát hiện sai lệch)
                    │
                    ▼
         [Feature Engineering] (Đang chuẩn bị)
                    │
                    ▼
       [Model Training & Validation] (Chưa thực hiện)
                    │
                    ▼
           [Đánh giá độc lập OOS] (Chưa thực hiện)
```

Thứ tự thực thi thực tế của các script không hoàn toàn đi theo số thứ tự tên file mà tuân theo quan hệ phụ thuộc nhân quả. Ví dụ: script kiểm toán danh mục cần đọc kho giá đã điều chỉnh để đối chiếu. Chi tiết về thứ tự chạy và các ràng buộc phụ thuộc được mô tả tại [`docs/pipeline_dag.md`](docs/pipeline_dag.md).

---

## 5. Cấu trúc repository

```
Predict_daily_return_rankings/
├── configs/                     # Cấu hình tham số hệ thống và phân vùng thời gian
│   └── base_config.yaml
├── data/
│   ├── raw/                     # Dữ liệu snapshot universe thô
│   └── processed/
│       ├── constituents_market_data/  # Kho dữ liệu giá thô và giá điều chỉnh
│       └── matrices/            # 17 tệp ma trận 2D tọa độ (7.252 x 3.711) và các masks
├── docs/
│   ├── data_dictionary.md       # Từ điển dữ liệu chi tiết từng cột và từng ma trận
│   ├── pipeline_dag.md          # Đồ thị phụ thuộc và thứ tự thực thi pipeline
│   ├── reports/                 # Báo cáo kỹ thuật chi tiết theo từng cột mốc
│   ├── Data report/             # Báo cáo HTML tương tác và bảng kiểm toán dữ liệu
│   └── archive/                 # Báo cáo và tài liệu giai đoạn cũ (lưu trữ tham khảo)
├── scripts/
│   ├── 01_pipeline/             # Các script thực thi chính thức của pipeline
│   └── archive/                 # Scripts và prototype cũ đã ngừng sử dụng
├── src/                         # Thư viện mã nguồn dùng chung cho pipeline mới
│   ├── data/                    # Nạp ma trận, xử lý universe và masks
│   ├── features/                # Lớp cơ sở tính toán đặc trưng và biến đổi chéo
│   ├── quality/                 # Kiểm soát cửa sổ chất lượng và chặn truy cập OOS
│   ├── utils/                   # Xử lý cấu hình và đường dẫn dự án
│   └── archive_v1/              # Mã nguồn cũ từ giai đoạn 1 (lưu trữ tham khảo)
├── tests/                       # Bộ kiểm thử tự động
│   ├── test_matrix_loader.py    # Kiểm thử bộ nạp ma trận và biến đổi
│   ├── test_pipeline_integrity.py  # Kiểm thử tính toàn vẹn pipeline và hợp đồng dữ liệu
│   ├── test_library_fixes.py    # Kiểm thử hồi quy các trường hợp biên
│   ├── run_tests.py             # Runner unittest cũ, chỉ chạy một phần tests
│   └── archive_v1/              # Các bài test cũ phụ thuộc vào src/archive_v1/
├── pytest.ini                   # Cấu hình pytest (bỏ qua các thư mục archive)
├── requirements.txt             # Danh sách thư viện Python phụ thuộc
└── README.md
```

*Lưu ý:* Các thư mục có hậu tố `archive/` hoặc `archive_v1/` chứa các tệp mã nguồn và báo cáo lịch sử phục vụ mục đích đối chiếu nguồn gốc dữ liệu; chúng không nằm trong luồng thực thi mặc định của pipeline hiện hành.

---

## 6. Bắt đầu sử dụng

### 6.1. Thiết lập môi trường
Bộ kiểm thử nền đã chạy trên **Python 3.14** trong môi trường hiện tại. Chưa xác minh cài mới toàn bộ dependencies hoặc tính tương thích trên các phiên bản Python/hệ điều hành khác.

Khởi tạo môi trường ảo trên Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6.2. Chuẩn bị dữ liệu
Dữ liệu thô của dự án được lưu trữ tại liên kết Google Drive sau:
- **Tải dữ liệu:** [Google Drive Raw Data Archive](https://drive.google.com/file/d/1M8AvM3C0uGnw5I1zrtiqNpRa-IlxdiLK/view?usp=sharing)

Đây là bản dữ liệu thô do người thực hiện cung cấp. Trước khi giải nén, người sử dụng cần đối chiếu cấu trúc thư mục mục tiêu trong [`configs/base_config.yaml`](configs/base_config.yaml) và [`docs/data_dictionary.md`](docs/data_dictionary.md) để đặt đúng các tệp vào `data/raw/` và `data/processed/`.

Các ZIP và Parquet không đi kèm Git clone. Các bài test nạp dữ liệu cần matrices/mapping cục bộ; clone code đơn thuần chưa đủ để chạy các tests cần dữ liệu cục bộ. Link Drive hiện là bản raw do chủ dự án cung cấp, chưa xác nhận chứa matrices đã xử lý. Xem DAG để tái tạo nếu chưa được chia sẻ matrices riêng.

File tài liệu `docs/Teacher Resource/quant overview.pdf` (~77 MB) và audit sinh tự động `2t_stitching_conflict_audit.csv` (~63 MB) được giữ cục bộ, không đưa vào commit bàn giao. Audit có thể tái tạo bằng script 06 sau khi chuẩn bị input theo DAG; tài liệu giảng dạy được nhận riêng từ người phụ trách.

### 6.3. Sử dụng các đầu ra có sẵn (Dành cho thành viên phát triển Features)
Nếu đã có sẵn kho ma trận tại `data/processed/matrices/`, thành viên không cần tải lại dữ liệu từ QuantConnect hay chạy lại toàn bộ pipeline từ đầu:

1. Đọc kỹ quy ước ma trận tại [`docs/data_dictionary.md`](docs/data_dictionary.md).
2. Chạy kiểm thử để xác nhận môi trường:
   ```powershell
   python -m pytest -q
   ```
3. Nạp dữ liệu lát Development thông qua API thư viện hiện hành:
   ```python
   from src.data.matrix_loader import load_matrix, load_bar_quality_mask, load_layer1_mask

   # Nạp cùng tọa độ Warm-up + Development cho input và masks
   adj_close_dev = load_matrix("adj_close", dev_only=True, include_warmup=True)
   print("Shape adj_close (Warmup + Dev):", adj_close_dev.shape)  # (6541, 3711)

   # Nạp Bar Quality Mask (kèm 630 phiên warm-up) để làm sạch đầu vào trước khi tính rolling
   bar_quality_warmup = load_bar_quality_mask(dev_only=True, include_warmup=True)
   print("Shape bar_quality (Warmup + Dev):", bar_quality_warmup.shape)  # (6541, 3711)

   # Nạp Membership Mask cùng tọa độ; warm-up có membership=False
   membership_dev = load_layer1_mask(strict=True, dev_only=True, include_warmup=True)
   print("Shape membership (Warmup + Dev):", membership_dev.shape)  # (6541, 3711)
   ```

### 6.4. Tái tạo pipeline từ dữ liệu thô
Để chạy lại các bước sinh dữ liệu từ tệp thô:
- Xem chi tiết thứ tự chạy và sơ đồ phụ thuộc tại [`docs/pipeline_dag.md`](docs/pipeline_dag.md).
- **Phân biệt môi trường:**
  - Các script như `02_quantconnect_availability_scan.py`, `02_quantconnect_export_10_batches.py`, `05_quantconnect_export_corporate_actions.py` được đánh dấu `[CLOUD-ONLY]`, cần chạy trên tài khoản QuantConnect Cloud kết nối kho dữ liệu Lean.
  - Các script từ `01`, `03`, `04`, `06`, `07`, `08`, `09`, `10` chạy trực tiếp tại dòng lệnh Local CLI khi đã có tệp đầu vào tương ứng.
- Pipeline hiện tại gồm các giai đoạn riêng biệt theo DAG; người dùng không chạy gộp toàn bộ bằng một lệnh duy nhất khi chưa kiểm tra các điều kiện phụ thuộc.

---

## 7. Quy ước sử dụng dữ liệu và masks

- **Cấu trúc tọa độ 2D:** Mọi ma trận dữ liệu đều có hàng là ngày giao dịch NYSE và cột là mã định danh chứng khoán canonical SID (ví dụ: `AAPL R735QTJ8XC9X`). Định danh này cố định theo thực thể chứng khoán, giải quyết triệt để vấn đề thay đổi hoặc tái sử dụng ticker.
- **Phân tách mặt nạ đầu vào và đầu ra:**
  - `bar_quality_mask`: Độc lập hoàn toàn với tư cách thành viên chỉ số. Mặt nạ này xác định xem tại một ngày, thanh giá có hợp lệ trên sàn hay không (không dính bad tick, không phải phiên nhảy giá do spin-off chưa điều chỉnh). Dùng để làm sạch dữ liệu đầu vào trước khi tính toán.
  - `membership_mask`: Xác định tư cách thành viên Russell 1000 theo quy ước Point-In-Time. Mặt nạ này **chỉ áp dụng để lọc kết quả tại ngày đầu ra $T$**, không lọc dữ liệu lịch sử đầu vào. Nhờ đó, cổ phiếu mới vào rổ vẫn giữ được dữ liệu warm-up sạch từ các phiên trước ngày gia nhập.
  - `valid_data_mask`: Điều kiện kết hợp giữa tư cách thành viên và tính sẵn có của thanh nến sạch tại ngày $T$. Đây là điều kiện kỹ thuật của dữ liệu, không phải cam kết rằng cổ phiếu có thể giao dịch không có tác động thị trường.
  - `valid_label_mask`: Dành riêng cho việc lọc nhãn mục tiêu ở ngày tương lai ($t+1$). **Tuyệt đối không dùng mặt nạ này để lọc biến đầu vào của ngày $t$**.
- **Kiểm soát cửa sổ chất lượng (Quality-Window Hygiene):**
  - Mọi thanh giá không thỏa mãn `bar_quality_mask` bị gán thành `NaN` trước khi đưa vào hàm rolling.
  - Nếu trong cửa sổ lookback có bất kỳ phiên nào không hợp lệ, giá trị feature tại ngày đầu ra sẽ tự động nhận giá trị `NaN`.
- **Nguyên tắc xử lý dữ liệu định lượng:**
  - Không tự ý điền giá trị 0 vào các phiên thiếu lợi suất.
  - Không điền tiến (*forward-fill*) chuỗi giá qua các giai đoạn gián đoạn định danh hoặc sự kiện doanh nghiệp chưa rõ nguyên nhân.
  - Mọi thao tác chuẩn hóa (*standardization*), điền khuyết (*imputation*) hoặc lựa chọn biến đều phải được fit riêng trên tập huấn luyện của từng fold, không fit trên toàn bộ dữ liệu.

Chi tiết về cấu trúc và ý nghĩa kinh tế từng cột xem tại [`docs/data_dictionary.md`](docs/data_dictionary.md) và [`docs/reports/data_pipeline/step4_matrices_masks_report.md`](docs/reports/data_pipeline/step4_matrices_masks_report.md).

---

## 8. Kiểm thử và phạm vi xác minh

GitHub Actions chạy **code/synthetic tests**, không có kho dữ liệu cục bộ. Dùng `python -m pytest -q -ra --strict-markers -m "not integration"` để chạy cùng phạm vi CI. Các tests cần dữ liệu thật được đánh dấu `integration`; lệnh không lọc marker bên dưới vẫn chạy toàn suite và báo lỗi nếu thiếu input. Xem [hướng dẫn kiểm thử](docs/testing.md).

Lệnh thực thi toàn bộ kiểm thử từ thư mục gốc dự án:
```powershell
python -m pytest -q
```

Các nhóm kiểm thử chính đang vận hành:
- **Nạp ma trận và phân vùng (`tests/test_matrix_loader.py`):** Kiểm tra kích thước ma trận ($7.252 \times 3.711$), trích xuất phân vùng Development (5.911 phiên) và kiểm tra cơ chế chặn truy cập OOS.
- **Tính toàn vẹn pipeline (`tests/test_pipeline_integrity.py`):** Biên dịch cú pháp các script pipeline hiện có, kiểm tra không còn đường dẫn ổ đĩa tuyệt đối, đối chiếu đường dẫn đầu ra bước 03 và đầu vào bước 04, và phân lập bảng kiểm toán giữa bước 04b và bước 05.
- **Kiểm thử hồi quy các trường hợp biên (`tests/test_library_fixes.py`):**
  - Tra cứu SID theo ngày không tự ý fallback sang toàn bộ lịch sử.
  - Truy vấn thành viên năm 2020 không phát sinh cảnh báo OOS giả.
  - Cửa sổ rolling tự động trả về `NaN` khi đi qua phiên có cờ dữ liệu xấu.
  - Bảo toàn warm-up sạch trước ngày gia nhập chỉ số, cho phép tính feature ngay ngày đầu tiên vào rổ.
  - Kiểm tra công thức xếp hạng đồng nhất: $\text{rank}_{\text{norm}} = \frac{\text{rank} - 1}{N - 1} \in [0, 1]$.
  - Kiểm tra cơ chế xóa nhãn ranh giới (*boundary purge*) tại ngày 2023-12-29.

*Phạm vi xác minh:* Các bài test tự động xác nhận rằng mã nguồn và các quy tắc kỹ thuật vận hành đúng theo thiết kế. Kết quả test không phải là bằng chứng khẳng định toàn bộ lịch sử thị trường hoặc mọi sự kiện corporate actions trong 26 năm qua đều không có sai sót thực tế. Các nội dung đối chiếu tài liệu và chứng cứ được ghi nhận trong các báo cáo kiểm toán riêng.

---

## 9. Giới hạn hiện tại

1. **Giả định xấp xỉ danh sách thành viên:** Quy ước 01/07 – 30/06 dựa trên snapshot thường niên bỏ qua các thay đổi phát sinh đột xuất giữa hai kỳ tái cơ cấu. Chi tiết tại [`docs/reports/data_pipeline/data_lineage_report.md`](docs/reports/data_pipeline/data_lineage_report.md).
2. **Các ca mapping heuristic:** 752 trường hợp mã tạm ` 2T` được nối định danh vào SID chính dựa trên khoảng cách ngày dương lịch ($\le 10$ ngày lịch: 456 nối phía sau, 296 nối phía trước). Các trường hợp này được gắn nhãn giả định và cách ly riêng trong báo cáo kiểm toán [`docs/reports/data_pipeline/step3_corporate_actions_report.md`](docs/reports/data_pipeline/step3_corporate_actions_report.md) để đánh giá độ nhạy khi cần thiết.
3. **Cổ phiếu penny, OTC và hủy niêm yết:** Một số thực thể giao dịch trên thị trường phi tập trung hoặc giải thể trong quá khứ không có chuỗi giá đầy đủ trên các nhà cung cấp dữ liệu thương mại.
4. **Sự kiện spin-off chưa xử lý toàn diện:** Các trường hợp công ty mẹ tách công ty con quy mô lớn (ví dụ: KSU năm 2000) hiện được cách ly bằng cờ gián đoạn (`is_spinoff_discontinuity = True`, lợi suất gán `NaN`) do chưa có chuỗi giá độc lập của tài sản được chia tách để tái hiện giá trị tổng lợi nhuận (*Total Return*).
5. **Mức độ chứng cứ trong bảng điều chỉnh:** 13 trường hợp điều chỉnh bổ sung trong [`market_data_corrections_and_exceptions.csv`](docs/Data%20report/market_data_audit/tables/market_data_corrections_and_exceptions.csv) có mức độ chứng cứ khác nhau (từ hồ sơ SEC Form 8-K, thông cáo FDIC đến quan sát bất thường thống kê).
6. **Chưa có kết luận về hiệu quả thực tế:** Toàn bộ công việc hiện tại mới dừng ở tầng chuẩn bị dữ liệu và thư viện nền tảng; dự án chưa đưa ra kết luận nào về năng lực sinh alpha hay khả năng ứng dụng giao dịch thực tế của các mô hình tiếp theo.

---

## 10. Tài liệu nên đọc tiếp

Muốn hiểu từ đầu như người mới: đọc [hướng dẫn theo 9 chặng](docs/learning/README.md), rồi mở báo cáo được dẫn ở cuối từng chặng.

Trong mỗi chặng, mục **Từ vấn đề đến phương pháp** giải thích vì sao chọn kỹ thuật, dấu hiệu/bằng chứng, cách kiểm chứng và giới hạn, để hiểu từng bước của bài đang làm. Ví dụ giả lập và kết quả thực nghiệm được phân biệt.

Xem [mục lục docs](docs/README.md) để tìm tài liệu hiện hành, báo cáo theo chủ đề và tài liệu lịch sử. [Quy ước theo dõi pilot](docs/reports/feature_pilot/README.md) nêu cách lưu kết quả; báo cáo chi tiết đang được rà soát riêng, chưa gộp vào commit docs.

Tùy theo nhu cầu nghiên cứu, người đọc có thể tham khảo các tài liệu chuyên biệt sau:

- **Dành cho thành viên mới bắt đầu:**
  - [`docs/reports/data_pipeline/data_lineage_report.md`](docs/reports/data_pipeline/data_lineage_report.md): Hành trình dữ liệu từ tệp snapshot thô, cấu trúc SID đến ma trận 2D.
  - [`docs/reports/migration/code_review_report.md`](docs/reports/migration/code_review_report.md): Rà soát chi tiết mã nguồn từng script trong pipeline.
- **Dành cho thành viên xây dựng Features và Mô hình:**
  - [`docs/data_dictionary.md`](docs/data_dictionary.md): Bảng tra cứu định nghĩa, kiểu dữ liệu, đơn vị và ý nghĩa kinh tế của toàn bộ các trường dữ liệu và 17 ma trận.
  - [`docs/reports/data_pipeline/step4_matrices_masks_report.md`](docs/reports/data_pipeline/step4_matrices_masks_report.md): Chi tiết kiến trúc 3 lớp mặt nạ và kết quả kiểm định ma trận.
  - [Đặc tả 16 features v1](docs/specifications/features_v1.md): Công thức, input, lookback, NaN và kế hoạch pilot.
  - [Đặc tả target/timing v1](docs/specifications/target_and_timing_v1.md): Nhãn, tập đối tượng, ranh giới và giới hạn khớp lệnh.
  - [Context bàn giao](docs/pipeline_migration_and_feature_readiness_context.md): Quyết định và lộ trình hiện hành.
- **Dành cho thành viên vận hành và tái tạo dữ liệu:**
  - [`docs/pipeline_dag.md`](docs/pipeline_dag.md): Đồ thị phụ thuộc, thứ tự thực thi và hướng dẫn chạy các script Local / Cloud.
  - [`docs/reports/migration/phase2_pipeline_verification_log.md`](docs/reports/migration/phase2_pipeline_verification_log.md): Nhật ký chạy kiểm định end-to-end của pipeline.
- **Dành cho kiểm toán chất lượng và pháp y dữ liệu:**
  - [`docs/reports/data_pipeline/step3_corporate_actions_report.md`](docs/reports/data_pipeline/step3_corporate_actions_report.md): Báo cáo chuẩn hóa định danh và bảng 13 trường hợp điều chỉnh bổ sung.
  - [`docs/reports/data_pipeline/step6_eda_report.md`](docs/reports/data_pipeline/step6_eda_report.md): Báo cáo thống kê mô tả (Kurtosis, Volatility) và điều tra pháp y 34 ca ngoại lai.
  - [`docs/reports/library/library_edge_cases_and_fixes_report.md`](docs/reports/library/library_edge_cases_and_fixes_report.md): Báo cáo chi tiết về việc khắc phục các ca biên trong thư viện nền tảng.
  - [`docs/Data report/project_report.html`](docs/Data%20report/project_report.html): Báo cáo trực quan tổng thể dự án.
- **Dành cho việc tra cứu lịch sử:**
  - [`docs/archive/README.md`](docs/archive/README.md), [`scripts/archive/README.md`](scripts/archive/README.md), [`src/archive_v1/README.md`](src/archive_v1/README.md): Giải trình lý do lưu trữ các mã nguồn và báo cáo cũ.

---

## 11. Công việc tiếp theo

Theo kế hoạch nghiên cứu, các công việc sắp tới sẽ được tiến hành tuần tự:
1. **Đối chiếu triển khai với đặc tả v1 đã chốt:** 16 features và target/timing; execution cho backtest được thiết kế riêng.
2. **Triển khai thử nghiệm Pilot:** Xây dựng script thử nghiệm tính toán trên nhóm nhỏ (ví dụ: 10 cổ phiếu đại diện qua một số năm) để đối chiếu kết quả tính toán với số liệu thủ công.
3. **Phân tích đặc trưng trên tập Development:** Đánh giá độ phủ, phân phối thống kê, tương quan giữa các biến và hệ số tương quan thứ hạng đơn lẻ (*Information Coefficient - IC*).
4. **Thiết kế phân vùng huấn luyện / kiểm thực:** Xây dựng khung kiểm thực chéo theo thời gian (*time-series / walk-forward validation*) trên giai đoạn 2000–2023.
5. **Huấn luyện và đánh giá mô hình:** Thử nghiệm các mô hình học máy xếp hạng, phân tích độ quan trọng của đặc trưng (*feature importance*) và độ nhạy siêu tham số.
6. **Kiểm định Out-of-Sample:** Đóng băng toàn bộ mô hình và thực hiện đánh giá độc lập một lần duy nhất trên tập dữ liệu 2024–2026.
