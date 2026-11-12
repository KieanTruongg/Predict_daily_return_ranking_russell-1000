# V1 — Từ dữ liệu đã lọc đến mô hình dự báo

Chặng này bắt đầu với ma trận ngày × mã định danh chứng khoán đã được rà chất lượng. Đích đến là hai mô hình đóng băng để đánh giá ngoài mẫu. Mỗi công đoạn bên dưới giải thích câu hỏi cần giải quyết, đầu vào, cách kiểm tra và quyết định đã dùng trong v1. Số liệu kiểm tra là số liệu từ báo cáo và cấu hình trong repo.

## 1. Xác định đúng điều mình muốn dự báo

**Cross-sectional ranking** là xếp hạng chéo ngang. Trong cùng một phiên, ta so mã A, B, C với nhau. **Time series** là chuỗi thời gian. Ta nhìn các phiên trước của từng mã để tính đầu vào. V1 dùng chuỗi thời gian để tạo đầu vào và xếp hạng chéo ngang để tạo mục tiêu.

T là ngày phát điểm sau khi dữ liệu đóng cửa đã sẵn sàng. T+1 là phiên giao dịch tiếp theo trên lịch chung. Ví dụ, nếu đóng cửa 02/01/2024 là T, mục tiêu dự báo là lợi suất từ Close ngày đó đến Close 03/01/2024. Giá đóng cửa đã điều chỉnh chia tách là P. Lợi suất giá bằng P[T+1]/P[T] − 1. V1 dùng lợi suất giá, chưa gồm cổ tức tiền mặt. Nếu P[T] = 100 và P[T+1] = 103, lợi suất nhãn là 3%.

**Feature** là đặc trưng đầu vào X, ví dụ lợi suất 20 phiên tính đến T. **Target** hay **label** là mục tiêu hoặc nhãn y, được biết khi đã có kết quả T+1. Trên mỗi ngày T:

1. Tính `target_return` cho các mã có nhãn hợp lệ.
2. Xếp tăng dần trong tập có nhãn hợp lệ. Mã lợi suất thấp nhất có hạng 1.
3. Chuẩn hóa hạng thành `target_rank` = (hạng − 1)/(N − 1). N là số mã có nhãn hợp lệ trong phiên. Các giá trị bằng nhau được chia hạng trung bình, ví dụ hạng 2 và 3 cùng nhận 2,5. Với một mã duy nhất, quy ước rank = 0,5.

Ví dụ A −2%, B +1%, C +3% cho nhãn A = 0, B = 0,5, C = 1. Số 1 là đầu bảng trong ngày, khác với lợi suất 100%. Khi một mã thiếu X, nó bị loại khỏi bảng huấn luyện nhưng hạng của những mã còn lại vẫn giữ nguyên. Nhờ vậy mục tiêu xếp hạng được định nghĩa trên tập nhãn, thay vì đổi mục tiêu theo số cột đầu vào còn đủ.

**Alpha signal** là tín hiệu dùng để xếp ưu tiên các mã, ví dụ điểm `ridge_score`. Cùng một đại lượng `ret_20d` có thể vừa là một feature trong mô hình, vừa là một tín hiệu đối chứng nếu đem nó xếp trực tiếp. Điểm dự báo càng lớn thì mã được xếp càng cao. Điểm đó chưa phải xác suất hoặc lợi suất dự báo theo phần trăm. [Đặc tả nhãn và thời điểm](../specifications/target_and_timing_v1.md) · [Đặc tả bảng huấn luyện](../specifications/baseline_dataset_v1.md)

## 2. Tạo đặc trưng và giữ đúng chiều thời gian

**Lookback** là số phiên nhìn lùi. **Rolling window** là cửa sổ trượt. Cửa sổ 20 phiên tại T lấy 20 phiên đến hết T, rồi dời một phiên vào ngày kế tiếp. Nếu tính 20 lợi suất Close-to-Close thì cần 21 mức giá vì mỗi lợi suất dùng hai đầu mút liên tiếp. **Warm-up** là lịch sử khởi động trước ngày cần tính. Một mã vừa gia nhập Russell 1000 có thể dùng lịch sử giao dịch sạch trước khi gia nhập để tính X ngay ngày đầu.

**Mask** là ma trận cờ đúng/sai. Có ba câu hỏi riêng:

- Bar lịch sử có đáng dùng để tính công thức không? `bar_quality_mask` sàng chất lượng lịch sử. **Bar** là bản ghi giao dịch gộp của một phiên. Một số cờ còn đánh dấu riêng trường Open, High, Low hoặc Close.
- Tại ngày phát điểm T, mã có thuộc rổ được chấp nhận không? Membership được áp dụng ở đầu ra ngày T. Cửa sổ lịch sử có thể chứa những phiên mã còn ngoài rổ.
- Sau khi T+1 kết thúc, có kết quả thật hợp lệ để train hoặc chấm không? `valid_label_mask` dành cho nhãn. Dùng cờ này để chọn đầu vào hoặc quyết định đặt lệnh tại T sẽ đưa thông tin tương lai vào quá khứ, tức **look-ahead bias**.

**NaN** đánh dấu thiếu hoặc không xác định. Ví dụ, khi không có đủ 20 lợi suất sạch, độ biến động 20 phiên có thể là NaN. Nếu đủ 20 lợi suất sạch đều giống nhau, độ biến động bằng 0. Điền 0 vào NaN sẽ trộn hai tình huống và có thể biến một cửa sổ lỗi thành tín hiệu giả.

### 2.1. Đọc từng công thức trong 13 đặc trưng v1

Trong các công thức bên dưới, P là Close điều chỉnh chia tách, r[t] = P[t]/P[t−1] − 1, và W là số phiên trong cửa sổ. Giá điều chỉnh chia tách giữ tỷ lệ so sánh qua các đợt đổi đơn vị cổ phiếu. **Raw Close/Volume** là giá và khối lượng thô. **Adjusted volume** là khối lượng đã quy về cùng đơn vị qua chia tách.

**Momentum** là động lượng. Giả thuyết thường xét là xu hướng vừa quan sát có thể tiếp tục. **Reversal** là đảo chiều. Với một chân trời khác, lợi suất vừa tăng có thể bị kéo ngược. Dấu của lợi suất trong feature cho biết quá khứ, còn dấu quan hệ dự báo là câu hỏi thực nghiệm.

- **`ret_1d`** ($\mathrm{ret}_{1\text{d}} = \frac{P[T]}{P[T-1]} - 1$): Đo biến động giá một phiên, hữu ích khi xét phản ứng hoặc đảo chiều rất ngắn.
- **`ret_5d`** ($\mathrm{ret}_{5\text{d}} = \frac{P[T]}{P[T-5]} - 1$): Đo khoảng một tuần giao dịch. Nếu 100 lên 105 qua đoạn sạch, feature là 0,05.
- **`ret_20d`** ($\mathrm{ret}_{20\text{d}} = \frac{P[T]}{P[T-20]} - 1$): Đo khoảng một tháng giao dịch. V1 dùng giá trị dương trực tiếp làm điểm cho đối chứng động lượng 20 phiên.
- **`ret_60d`** ($\mathrm{ret}_{60\text{d}} = \frac{P[T]}{P[T-60]} - 1$): Đo khoảng một quý giao dịch. Nó có thể chung thông tin với lợi suất ngắn hơn vì các cửa sổ lồng nhau.
- **`mom_12m_skip_1m`** ($\mathrm{mom}_{12\text{m, skip 1m}} = \frac{P[T-21]}{P[T-252]} - 1$): Đo 231 khoảng lợi suất xa hơn, bỏ đoạn gần nhất để tách xu hướng dài khỏi tín hiệu tháng vừa qua. Cần truy cập tới T−252, còn 232 mức giá phải sạch nằm trong đoạn T−252…T−21. Ví dụ hai đầu đoạn là 100 và 130 thì feature bằng 0,30. Thay P[T] riêng lẻ không đổi tỷ số này.

**Volatility** là độ biến động. **Độ lệch chuẩn** đo mức tản quanh giá trị trung bình. Hai chuỗi có cùng lợi suất trung bình vẫn có độ biến động khác nhau.

- **`vol_realized_20d`** = $\sigma_{20}(r)$: Tính độ lệch chuẩn mẫu của 20 lợi suất giá một phiên đến T. Dùng mẫu số 19 trong phương sai, tức `ddof=1`. Giữ đơn vị biến động ngày.
- **`vol_realized_60d`** = $\sigma_{60}(r)$: Dùng cùng phép tính trên 60 lợi suất. Cửa sổ dài phản ứng chậm hơn khi thị trường đột nhiên đổi mức dao động.
- **`downside_deviation_20d`** = $\sqrt{\frac{1}{20} \sum \min(r, 0)^2}$: Lấy căn bậc hai của trung bình 20 giá trị min(r, 0)². **Downside** là phía giảm. Ngày tăng đóng góp 0, ngày giảm 4% đóng góp 0,0016 trước khi lấy trung bình. Mẫu số vẫn là 20, gồm cả ngày tăng. Đại lượng này tách độ lớn các phiên giảm khỏi độ dao động hai phía.

**Liquidity** là thanh khoản, tức mức độ có thể giao dịch thuận lợi. **Dollar volume** là giá trị giao dịch quy ra tiền. Trong v1, DV = raw Close × raw Volume là một **proxy**, tức đại lượng đại diện dễ tính. Ví dụ đóng cửa 100 USD, khớp 10.000 cổ phiếu thì DV đại diện là 1 triệu USD. Phép nhân dùng một mức giá cho cả phiên nên chỉ xấp xỉ giá trị khớp thực.

- **`amihud_illiq_20d`** = $10^6 \times \frac{1}{20} \sum_{t=0}^{19} \frac{|r_{T-t}|}{\text{DV}_{T-t}}$: **Illiquidity** là kém thanh khoản. Cùng mức đổi giá, DV nhỏ hơn cho tỷ số lớn hơn. Khi |r| = 1% và DV = 1 triệu USD, đóng góp sau đổi thang là 0,01. Đây là proxy theo ý tưởng Amihud. Công thức chỉ cho biết biến động quan sát trên mỗi đơn vị DV, chưa đo trực tiếp phí khớp lệnh.
- **`volume_ratio_5_20`** = $\frac{\overline{\text{Vol}}_{5d}}{\overline{\text{Vol}}_{20d}}$: Giá trị 2 nghĩa là giao dịch gần đây sôi động gấp đôi mức nền. Riêng con số này chưa cho biết giá sẽ tăng hay giảm.
- **`log_dollar_volume_20d`** = $\ln(1 + \overline{\text{DV}}_{20d})$: **Logarithm** là logarit, phép biến đổi giúp nén khoảng cách giữa các mã giao dịch vài triệu và vài trăm triệu USD. Tính trung bình trước rồi lấy log.

**Technical indicator** là chỉ báo kỹ thuật, tức cách tóm tắt mẫu hình trong lịch sử giá hoặc khối lượng.

- **`rsi_14d`** = $100 - \frac{100}{1 + \text{RS}}$: Là **Relative Strength Index**, chỉ số sức mạnh tương đối của các bước tăng và giảm của cùng cổ phiếu. Với mỗi thay đổi giá, phần tăng là max(chênh lệch, 0) và phần giảm là max(−chênh lệch, 0). Lấy trung bình hai dãy này trên 14 thay đổi giá đầu tiên để khởi tạo. Sau đó dùng **Wilder smoothing**, phép làm mượt cho trung bình cũ trọng số 13/14 và quan sát mới trọng số 1/14. RSI = 100 − 100/(1 + trung bình tăng/trung bình giảm). Ví dụ tỷ số tăng/giảm = 3 thì RSI = 75. Nếu chuỗi phẳng thì quy ước RSI = 50. Gặp gián đoạn không hợp lệ thì khởi tạo lại, vì phép tính dùng trạng thái trước đó.
- **`bollinger_pct_b_20d`** = $\frac{P - \text{Lower}}{\text{Upper} - \text{Lower}}$: Đo vị trí giá trong **Bollinger Bands**, dải quanh trung bình giá 20 phiên. Dải trên/dưới = trung bình ± hai độ lệch chuẩn của mức giá với `ddof=0`. %B = (giá − dải dưới)/(dải trên − dải dưới). Nếu dải là 90–110 và giá 115 thì %B = 1,25. Giá trị vượt 1 hợp lệ. Khi hai dải trùng nhau thì mẫu số bằng 0 và %B là NaN.

### 2.2. Ba đặc trưng đã thiết kế và hoãn khỏi v1

**OHLC** gồm Open, High, Low và Close, tức giá mở, cao nhất, thấp nhất và đóng cửa. Ba công thức dưới đây có kiểm tra triển khai trong đợt thử đặc trưng, nhưng bộ X v1 dùng 13 cột Close/Volume để tránh phụ thuộc vào các trường giá còn nghi vấn trong đợt rà OHLC.

- **`vol_parkinson_20d`** = $\sqrt{\frac{1}{20} \sum \frac{\ln(H/L)^2}{4 \ln 2}}$: Dùng biên độ High/Low trong phiên. Hai phiên có cùng lợi suất đóng cửa nhưng khác biên độ trong ngày sẽ cho đóng góp khác nhau. Công thức dựa trên giả định về quá trình giá và phụ thuộc mạnh vào chất lượng High/Low.
- **`ret_intraday`** = $\frac{\text{Close}[T]}{\text{Open}[T]} - 1$: **Intraday** là trong cùng phiên. Đặc trưng này dùng thông tin đã biết ở Close T. Backtest ở chặng sau giao dịch Open→Close T+1, một cửa sổ khác.
- **`ret_overnight`** = $\frac{\text{Open}[T]}{\text{Close}[T-1]} - 1$: **Overnight** là đoạn giữa đóng cửa phiên trước và mở cửa phiên kế. Mức giá mở sai có thể làm cả hai feature dùng Open cực đoan cùng lúc.

Việc hoãn ba cột là quyết định về độ tin cậy của đầu vào v1. Nó chưa đo được phần cải thiện dự báo nếu có nguồn Open/High/Low sạch hơn. [Công thức và nguồn tham khảo của đặc trưng](../specifications/features_v1.md) · [Code tính đặc trưng](../../src/features/base.py) · [Báo cáo rà OHLC](../reports/feature_eda_report.md#4-kiến-trúc-thống-nhất-corrections--rà-soát-ohlc-toàn-diện-19982023)

## 3. Kiểm tra đặc trưng trước khi huấn luyện

**Pilot** là chạy thử quy mô nhỏ để đối chiếu phép tính. Dữ liệu **synthetic** là chuỗi mình dựng nên có thể tính tay. Ví dụ 20 lợi suất xen kẽ +1% và −1% có trung bình bằng 0, độ lệch chuẩn mẫu khoảng 0,0102598. **Empirical check** là kiểm tra trên mẫu thực tế, ví dụ ngày chia tách AAPL hoặc mã chưa đủ lịch sử. Chạy trên hai loại mẫu giúp tách kiểm tra công thức khỏi những vấn đề chỉ thấy khi tích hợp dữ liệu. Sai số nhỏ nằm trong **tolerance**, tức dung sai số học đã quy định. [Báo cáo pilot](../reports/feature_pilot_report.md) · [Script pilot](../../scripts/01_pipeline/11_feature_engineering_pilot.py)

**Feature store** là kho đặc trưng đã tính, dùng lại khi tạo bảng học và chấm mẫu. **EDA**, viết tắt của Exploratory Data Analysis, là phân tích khám phá dữ liệu. Sau pilot, EDA trên Development xem phân phối, ngoại lệ, độ phủ, lý do NaN và tương quan giữa đặc trưng. Ví dụ một giá Open bất thường rất thấp có thể khiến lợi suất trong phiên tăng tới hàng trăm lần dù giá Close nhìn hợp lý. Rà dữ liệu gốc trước khi sửa đặc trưng giúp tránh học nhầm lỗi nguồn. **Correlation** là tương quan, thước đo hai đại lượng biến động cùng chiều hay ngược chiều. Hai feature có tương quan cao có thể cùng mang thông tin, nhưng vẫn cần kiểm tra dự báo để biết bỏ cột nào có ích.

**Causal test** trong pipeline là kiểm tra hướng thời gian, chẳng hạn sửa giá và khối lượng *sau* T rồi tính lại X tại T. X[T] phải giữ nguyên. Cắt dữ liệu tới T rồi đối chiếu cũng giúp phát hiện code dùng sai chiều. Các phép kiểm tra này giới hạn ở điều kiện đã thực hiện. Chúng không tự xác nhận ngày công bố snapshot hoặc độ đúng của từng giá lịch sử. [Báo cáo EDA và kiểm tra hướng thời gian](../reports/feature_eda_report.md) · [Bàn giao đặc trưng và chất lượng OHLC](../reports/handoff/feature_store_milestone_handoff.md)

## 4. Tạo bảng học rồi chia theo thời gian

**Dataset** là bảng dữ liệu học. Mỗi dòng có ngày T, mã chứng khoán chuẩn, 13 feature, `target_return` và `target_rank`, tổng cộng 17 cột. Chính sách **complete-case** giữ các dòng có đủ các cột đầu vào và nhãn hợp lệ. Điều này thuận tiện khi dùng chung mẫu cho Ridge và cây. Nó có thể loại nhiều mã mới hoặc có lịch sử gián đoạn, nên khi so với tổng số mã thành viên cần báo cáo độ phủ. Bảng Development đã ghi nhận 5.514.324 dòng, từ 03/07/2000 đến 28/12/2023. Tỷ lệ ~98,34% là trên 5.607.409 ô strict membership của Development, tức các cặp ngày–mã đủ điều kiện thành viên theo chính sách nghiêm ngặt.

**Development** là khoảng dùng để phát triển phương pháp. **Train** là phần dùng để học trọng số, **validation** là phần dùng để so cấu hình. **Out-of-sample (OOS)** là dữ liệu ngoài mẫu huấn luyện, dành để chấm cấu hình đã chốt. Với dữ liệu tài chính, một ngày có nhiều mã và mọi mã cùng chia sẻ thời điểm thông tin. Xáo trộn dòng ngẫu nhiên có thể đưa thông tin giai đoạn sau vào tập học. V1 chia theo ngày.

**Walk-forward validation** mô phỏng việc đứng tại từng mốc quá khứ, học từ trước mốc và dự báo giai đoạn sau. **Fold** là một lượt train/validation. **Expanding window** nghĩa là mốc bắt đầu của train giữ nguyên và mốc cuối lùi dần về phía hiện tại. Năm lượt của v1:

1. Train 2000–2018, validation 2019.
2. Train 2000–2019, validation 2020.
3. Train 2000–2020, validation 2021.
4. Train 2000–2021, validation 2022.
5. Train 2000–2022, validation 2023.

**Boundary purge** là loại các dòng có khoảng nhãn vượt ranh giới đã chốt. Phiên phát tín hiệu 31/12/2018 có lợi suất mục tiêu kết thúc 02/01/2019, nằm bên validation, nên bỏ phiên đó khỏi train ở lượt đầu. Lịch cũng giữ nhãn validation trong năm tương ứng. Phiên 29/12/2023 có nhãn kết thúc 02/01/2024 nên bị loại khỏi Development ngay khi tạo bảng. Có thể dùng lịch sử trước mốc validation/OOS để tính features của ngày đầu vì lịch sử đó đã biết tại T. [Bộ dựng bảng](../../scripts/01_pipeline/17_build_baseline_dataset.py) · [Lịch và quy tắc chia tập](../../configs/walk_forward_schedule_v1.yaml)

## 5. Hai mô hình học điểm thế nào?

**Model** là mô hình, tức quy tắc biến vector X thành điểm dự báo. **Fit** là dùng tập train để ước lượng tham số. **Baseline** là mốc tham chiếu để đo mô hình mới có cải thiện hay không. Trong v1, Ridge là mốc mô hình và `ret_20d` là mốc tín hiệu theo công thức.

### Ridge Regression

**Regression** là hồi quy. V1 dự báo một đại lượng số liên tục, ở đây là hạng đã chuẩn hóa từ 0 đến 1. **StandardScaler** chuẩn hóa thang đo bằng z = (x − trung bình train)/độ lệch chuẩn train. Ví dụ feature có trung bình train 0,01 và độ lệch chuẩn 0,04. Giá trị 0,05 tương ứng z = 1. Đưa các cột về cùng thang độ lệch chuẩn giúp mức phạt L2 dễ so sánh giữa hệ số của những cột vốn có đơn vị rất khác nhau. V1 học các thống kê này trên train của từng fold rồi áp dụng lại cho validation. Khi refit, thống kê được học lại trên Development.

Điểm Ridge có dạng b + β₁z₁ + ⋯ + β₁₃z₁₃. **Coefficient** là hệ số β. **Intercept** là hằng số b. Ridge học các hệ số bằng cách tối thiểu hóa tổng sai số bình phương giữa điểm dự báo và nhãn, cộng α × tổng bình phương các hệ số. Đây là **L2 regularization**, tức điều chuẩn L2, làm chi phí tăng khi hệ số lớn. **Hyperparameter** là siêu tham số đặt ngoài quá trình fit, như α. Chữ α này chỉ mức phạt, khác với cách gọi tín hiệu alpha trong đầu tư.

Ví dụ hệ số âm cho lợi suất 5 phiên và dương cho momentum dài hạn có nghĩa là trong công thức Ridge đã fit, khi các đặc trưng còn lại giữ nguyên, hai cột làm điểm đổi theo hai hướng khác nhau. Một hệ số đơn lẻ chưa cho biết đặc trưng đó dự báo tốt khi đứng riêng hoặc có tác động nhân quả. Cửa sổ chồng nhau làm hệ số phụ thuộc vào các cột khác trong mô hình.

### Histogram Gradient Boosting

**Decision tree** là cây quyết định, gồm các câu hỏi chia dữ liệu theo ngưỡng, ví dụ `ret_5d` ≤ −2%. **Leaf** là nút lá cuối đường đi, nơi cây trả một giá trị. **Boosting** ghép nhiều cây, mỗi cây mới tìm cách sửa lỗi dự báo còn lại theo hàm mất mát. **Histogram** là cách gom giá trị feature vào các khoảng để xét các ngưỡng chia hiệu quả hơn.

V1 dùng `HistGradientBoostingRegressor` của scikit-learn, nhận 13 feature trực tiếp. Mô hình có thể học **interaction**, tức tác động của một đặc trưng phụ thuộc giá trị của đặc trưng khác. Ví dụ chỉ thưởng điểm đảo chiều ngắn hạn trong nhánh có biến động thấp. Đó là ví dụ về khả năng biểu diễn của cây, chưa phải quy tắc rút ra từ mô hình thật. `max_leaf_nodes=7` giới hạn số lá *mỗi cây*. Cấu hình còn có tối đa 100 vòng boosting và bước đóng góp `learning_rate=0.05`.

**Overfitting** là quá khớp. Mô hình có thể học chi tiết đặc thù của quá khứ mà không lặp lại trên giai đoạn mới. Phạt L2 và giới hạn số lá giúp kiểm soát độ phức tạp. Validation theo thời gian là nơi kiểm tra một cấu hình có giữ được giá trị dự báo trên các giai đoạn sau không. [Code và tham số refit](../../scripts/01_pipeline/25_refit_final_models_development.py)

## 6. Chọn cấu hình, fit lại và đóng băng

**Grid search** là thử một lưới giá trị đã đặt trước. **Spearman Rank IC** là tương quan giữa hạng điểm dự báo và hạng lợi suất thực tế, tính riêng cho từng phiên. Trung bình IC qua các phiên giúp so khả năng xếp hạng trên validation. Tất cả so sánh bên dưới đều thuộc Development.

- Ridge α = 1 đạt Mean IC +0,016497 trên 1.253 phiên validation. Mức phạt 1.000.000 đạt +0,016867 nhưng cải thiện nhỏ và khác theo năm. V1 giữ α = 1 làm mốc đơn giản. Vì vậy cấu hình được giữ không phải cấu hình có Mean IC cao nhất trong lưới thử.
- GBDT thử 7, 15 và 31 lá mỗi cây. Mean IC lần lượt là +0,020967, +0,019158 và +0,018683. V1 chọn 7 lá theo kết quả quan sát được trong lưới này. Kết quả không bao phủ mọi cấu hình cây hay mọi loại mô hình.
- `ret_20d` chấm cùng giao thức để đối chiếu với mô hình học máy.

**Refit** là fit lại cấu hình đã chọn trên toàn bộ Development có nhãn hợp lệ. **Model freeze** là giữ nguyên cấu hình, bộ chuẩn hóa và tham số đã học khi đi qua OOS. Feature vẫn được tính lại theo dữ liệu đã quan sát ở từng phiên T. Một mã mới có thể nhận điểm khi đủ điều kiện và đủ đặc trưng. Mô hình nhận đặc trưng, còn mã định danh dùng để ghép đúng dòng dữ liệu. [Thử lưới Ridge](../reports/baseline/ridge_alpha_grid_search_report.md) · [Thử số lá GBDT](../reports/baseline/gbdt_leaf_grid_report.md) · [Manifest mô hình đóng băng](../../configs/oos_production_models_manifest.yaml)

## Tự kiểm tra sau khi đọc

1. Vì sao `ret_20d` cần 21 giá nhưng trung bình khối lượng 20 phiên cần 20 số?
2. Mã vừa vào rổ tại T có thể dùng lịch sử trước T. Tại sao nhãn ở T+1 lại không được dùng để chọn mã dự báo?
3. Khi một mã thiếu feature sau khi đã tính nhãn rank, tại sao giữ nguyên hạng của các mã còn lại?
4. Nêu sự khác nhau giữa hệ số β của feature, tham số α của Ridge, điểm alpha của mã và tỷ trọng danh mục.
5. Với hai ngày sát ranh giới train/validation, trường hợp nào cần purge? Sau khi đóng băng tham số, thông tin nào vẫn thay đổi mỗi ngày?
