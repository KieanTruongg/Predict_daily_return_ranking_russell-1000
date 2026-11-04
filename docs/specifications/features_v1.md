# Đặc tả features ứng viên v1

Ngày cập nhật: 2026-11-05. Đây là hợp đồng thiết kế, không phải báo cáo triển khai hoặc bằng chứng hiệu quả dự đoán.

## 1. Danh sách 16 ứng viên

1. `ret_1d`
2. `ret_5d`
3. `ret_20d`
4. `ret_60d`
5. `mom_12m_skip_1m`
6. `vol_realized_20d`
7. `vol_realized_60d`
8. `vol_parkinson_20d`
9. `downside_deviation_20d`
10. `amihud_illiq_20d`
11. `volume_ratio_5_20`
12. `log_dollar_volume_20d`
13. `ret_intraday`
14. `ret_overnight`
15. `rsi_14d`
16. `bollinger_pct_b_20d`

Cả 16 ứng viên đã được trao đổi và thống nhất thiết kế công thức dưới đây. Chưa xác nhận code tuân thủ hoặc features có hiệu quả dự đoán. Không tự thêm `vol_ratio_20_60`, thay cửa sổ volume ratio hoặc thay đổi phép log mà không cập nhật quyết định.

## 2. Quy tắc chung

- Mỗi đầu ra có khóa `(date T, canonical_sid i)`; thông tin được biết đến hết phiên T. Xem [đặc tả target/timing](target_and_timing_v1.md).
- Giữ lịch sử sạch trước ngày gia nhập universe để warm-up. Làm sạch input bằng `bar_quality_mask`, độc lập membership; áp dụng membership chỉ tại ngày đầu ra T.
- Mask cơ sở không thay thế kiểm tra hợp lệ riêng của mỗi feature: input phải hữu hạn, đúng miền giá trị và đúng phiên giao dịch.
- Không dùng `valid_label_mask` để tính features. Không fill return thiếu thành 0 hoặc tự động nối qua gián đoạn chưa xử lý.
- NaN là kết quả hợp lệ khi không đủ dữ liệu. Không đồng nhất warm-up được bảo toàn với đủ lịch sử cho mọi mã.
- Giữ feature gốc trước khi thử biến đổi/ranking/scaling. Mọi tham số học từ dữ liệu phải fit trong phần train tương ứng.

## 3. Nhóm momentum — đã thống nhất

### 3.1. Input và ý nghĩa

Đặt `P[i,T] = adj_close[i,T]`: giá đóng cửa điều chỉnh chia tách theo kho dữ liệu hiện hành, chưa bao gồm tái đầu tư cổ tức. Dùng loại giá này nhất quán với target giá v1. Phải chọn loại input tường minh, không chuyển ngầm sang total return khi thiếu dữ liệu.

Giá back-adjusted là hợp đồng dữ liệu hiện hành; mức độ point-in-time của toàn bộ chuỗi điều chỉnh không được xem là đã xác minh chỉ nhờ văn bản này. Các tỷ số trong nhóm này phải được đối chiếu qua split khi pilot.

Feature mô tả lợi suất đã xảy ra, không mặc định khẳng định dấu dự đoán tương lai. Mô hình học từ feature gốc; không thêm đồng thời feature và số đối của nó như hai nguồn thông tin độc lập.

### 3.2. `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`

Với W thuộc {1, 5, 20, 60}:

```text
ret_Wd[i,T] = P[i,T] / P[i,T-W] - 1
```

- Đơn vị: lợi suất dạng số thập phân, ví dụ 0.05 = 5%.
- Cần W+1 mức giá từ T−W đến T, tương ứng W khoảng lợi suất.
- V1 yêu cầu mọi mức giá trên đoạn đó hữu hạn, dương, sạch và liên tục trên lịch giao dịch chung. Nếu có phiên thiếu hoặc quality flag không hợp lệ, đầu ra là NaN kể cả hai đầu mút có giá.
- Thiếu lịch sử do IPO hoặc đầu kho: NaN.
- Giá không đổi trên cửa sổ sạch: 0, không phải NaN.
- Ví dụ W=5: P[T−5]=100, P[T]=105, các phiên trung gian hợp lệ → ret_5d=0.05.
- Sau khi tính, T ngoài membership → NaN; lịch sử trước membership vẫn tham gia lookback.

### 3.3. `mom_12m_skip_1m`

```text
mom_12m_skip_1m[i,T] = P[i,T-21] / P[i,T-252] - 1
```

- Đo khoảng lợi suất từ T−252 đến T−21; bỏ đoạn gần nhất đến T.
- Đây là quy ước 252/21 phiên, không phải tròn năm/tháng lịch.
- Đo 231 khoảng lợi suất, cần 232 mức giá trên đoạn T−252…T−21; phải truy cập lịch sử xa đến T−252.
- Đoạn được đo phải có giá hữu hạn, dương, sạch và liên tục. Không được dùng tỷ số hai đầu mút để bắc qua gián đoạn chưa xử lý bên trong đoạn đó.
- Đầu ra tại T vẫn phải thuộc membership. Quy tắc eligibility chung khi dự đoán được quản lý riêng; không đưa dữ liệu trong tháng bị bỏ vào công thức lợi suất một cách ngầm định.
- Ví dụ P[T−252]=100 và P[T−21]=130, đoạn đo hợp lệ → 0.30. Thay riêng giá P[T] không thay kết quả công thức.

### 3.4. Kiểm tra cần thực hiện trong pilot

Đây là tiêu chí chưa xác nhận đã chạy:

- Đối chiếu tỷ số giá với tính tay trên vài mẫu.
- Kiểm tra W khoảng return cần W+1 giá, không lệch phiên.
- Kiểm tra split không tạo bước nhảy giả trong return.
- Kiểm tra bar lỗi giữa cửa sổ làm NaN, sau khi bar lỗi thoát cửa sổ thì phục hồi.
- Kiểm tra có đủ lịch sử trước gia nhập thì tính được ngay ngày đầu membership.
- Kiểm tra IPO chưa đủ lịch sử nhận NaN.
- Với momentum bỏ tháng: kiểm tra đúng T−252 và T−21, thay giá ngoài đoạn đo không thay kết quả số học.
- Kiểm tra không dùng nhãn tương lai, không nối qua phiên thiếu.

## 4. Nhóm volatility — đã thống nhất thiết kế

### 4.1. `vol_realized_20d`, `vol_realized_60d`

Với W=20 hoặc 60, dùng return giá điều chỉnh split (không gồm cổ tức), tính độ lệch chuẩn mẫu của W return gần nhất từ T−W+1 đến T: `std(ddof=1)`. Giữ đơn vị ngày, không nhân sqrt(252).

Cần W return sạch, tương ứng W+1 mức giá liên tiếp. Return phải hữu hạn; cửa sổ qua dữ liệu lỗi hoặc gián đoạn chưa xử lý là NaN. Return không đổi trên cửa sổ hợp lệ cho volatility bằng 0. Đây là feature mô tả dao động quá khứ, không phải lệnh giảm vị thế mặc định.

Tên `realized` được giữ theo quy ước dự án; phép tính cụ thể ở đây là rolling standard deviation của daily simple returns, không phải realized variance từ dữ liệu intraday tần suất cao.

### 4.2. `vol_parkinson_20d`

```text
vol_parkinson_20d = sqrt(mean_20(log(adj_high / adj_low)^2) / (4*log(2)))
```

Dùng 20 cặp high/low, cùng hệ điều chỉnh. Yêu cầu mỗi phiên hữu hạn và high >= low > 0, qua quality policy. High=low hợp lệ và đóng góp 0. Cửa sổ thiếu hoặc lỗi là NaN; không annualize. Không trực tiếp đo overnight gap.

Nguồn công thức: Michael Parkinson (1980), The Extreme Value Method for Estimating the Variance of the Rate of Return, Journal of Business 53(1), 61–65. [Bản bài báo](https://www.cmegroup.com/trading/fx/files/michael_parkinson.pdf). Đây là estimator có giả định mô hình; không mặc nhiên coi tốt hơn close-to-close trong dữ liệu thực tế của dự án.

### 4.3. `downside_deviation_20d`

```text
downside_deviation_20d = sqrt(sum_20(min(daily_return, 0)^2) / 20)
```

Ngưỡng là 0, mẫu số là toàn bộ 20 phiên hợp lệ, không chỉ số phiên âm; không trừ trung bình và không dùng ddof=1. Đây là căn lower partial moment bậc hai tại ngưỡng 0, không phải standard deviation riêng các ngày âm.

Dùng return giá điều chỉnh split như realized volatility. Cần 20 return sạch và 21 mức giá liên tiếp; không annualize. Return dương đóng góp 0, return thiếu vẫn thiếu và làm cửa sổ NaN. Nếu tất cả return không âm, đầu ra bằng 0.

Ví dụ r=[0.02,-0.01,0.03,-0.04] với cửa sổ minh họa 4 phiên: sqrt((0+0.0001+0+0.0016)/4) ≈ 0.0206155.

### 4.4. Kiểm tra pilot cần có

So sánh với tính tay; cửa sổ đủ/thiếu; chuỗi return hằng; downside toàn phiên không âm; high=low; high<low; input Inf/NaN; splits; bar lỗi và phục hồi sau khi thoát cửa sổ. Chưa xác nhận đã chạy các kiểm tra này.

## 5. Nhóm liquidity/volume — đã thống nhất thiết kế

### 5.1. Dollar volume dùng chung

`DV[T] = raw_close[T] * raw_volume[T]`, đơn vị USD theo dữ liệu nguồn. Đây là proxy giá trị giao dịch, không phải tổng giá trị khớp lệnh chính xác vì dùng một giá đóng cửa cho mọi giao dịch. Không trộn raw price với adjusted volume.

### 5.2. `amihud_illiq_20d`

```text
amihud_illiq_20d = 1e6 * mean_20(abs(daily_return) / DV)
```

Dùng simple price return điều chỉnh split, không gồm cổ tức. Tính tỷ số theo từng phiên rồi mới lấy trung bình, không lấy tỷ số của hai trung bình. Cần 20 cặp return/DV sạch (và 21 mức close liên tiếp cho return), DV dương, mọi input hữu hạn. Return 0 với DV dương đóng góp 0; volume 0 hoặc thiếu làm cửa sổ NaN.

Hệ số 1e6 chỉ đổi thang đo. Giá trị lớn mô tả biến động giá cao so với giá trị giao dịch, không chứng minh quan hệ nhân quả hay chi phí khớp lệnh thực tế.

Nguồn: [Amihud (2002), Illiquidity and stock returns: cross-section and time-series effects](https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf). Cửa sổ rolling 20 phiên là lựa chọn của dự án, không tuyên bố sao chép nguyên toàn bộ thiết kế thực nghiệm của bài báo.

### 5.3. `volume_ratio_5_20`

```text
volume_ratio_5_20 = mean_5(adj_volume) / mean_20(adj_volume)
```

Cả hai cửa sổ kết thúc tại T; 5 phiên nằm trong 20 phiên. Dùng volume điều chỉnh split nhất quán. Cần 20 volume hữu hạn, dương, sạch; mẫu số dương. Không dùng raw volume qua split để tránh thay đổi cơ học về đơn vị cổ phiếu. Giá trị 2 nghĩa là trung bình 5 phiên gấp đôi trung bình 20 phiên, không nói hướng giá.

### 5.4. `log_dollar_volume_20d`

```text
log_dollar_volume_20d = log1p(mean_20(DV))
```

DV được biểu diễn bằng USD trước khi lấy log; không đổi ngầm sang triệu USD. Lấy trung bình trước rồi log, không phải mean(log1p(DV)). Cần 20 phiên DV hữu hạn, dương, sạch. Đây là phép biến đổi nén thang đo, không thay thế preprocessing fit trong train nếu mô hình cần.

## 6. Nhóm intraday/technical — đã thống nhất thiết kế

### 6.1. `ret_intraday`

`ret_intraday[T] = adj_close[T] / adj_open[T] - 1`.

Cần open/close cùng phiên, cùng hệ điều chỉnh, hữu hạn, dương, sạch. Không yêu cầu phiên trước chỉ để tính công thức này. Ví dụ 100→103 cho 0.03.

### 6.2. `ret_overnight`

`ret_overnight[T] = adj_open[T] / adj_close[T-1] - 1`.

Cần hai phiên liên tiếp trên lịch chung, giá hữu hạn/dương/sạch, không qua discontinuity chưa xử lý. Đây là overnight đã xảy ra trước phiên T, không phải return tương lai. Không điều chỉnh thêm cổ tức tiền mặt vào công thức v1.

Kiểm tra trên các phiên hợp lệ: `(1+ret_1d) = (1+ret_overnight)*(1+ret_intraday)` trong tolerance số học.

### 6.3. `rsi_14d`

Dùng adj_close và Wilder smoothing:

```text
delta[T] = P[T] - P[T-1]
gain[T] = max(delta[T], 0)
loss[T] = max(-delta[T], 0)
```

Khởi tạo AvgGain/AvgLoss bằng trung bình 14 delta sạch đầu tiên (15 giá). Sau đó:

```text
AvgGain[T] = (13*AvgGain[T-1] + gain[T]) / 14
AvgLoss[T] = (13*AvgLoss[T-1] + loss[T]) / 14
RSI = 100 - 100/(1 + AvgGain/AvgLoss)
```

Nếu AvgLoss=0 và AvgGain>0: 100; AvgGain=0 và AvgLoss>0: 0; cả hai=0: quy ước dự án 50. Không cắt các giá trị lỗi để che sai công thức. RSI phải trong [0,100] trong tolerance số học.

Đây là phép tính có trạng thái, không phải rolling mean đơn giản 14 phiên. Gặp input không hợp lệ hoặc discontinuity chưa xử lý thì reset trạng thái, chờ 14 delta sạch liên tiếp để seed lại; không nối delta qua gap. Thay đổi membership không reset trạng thái. Phải ghi ngày seed và dùng cùng lịch sử khởi tạo khi đối chiếu để tránh khác biệt do warm-up.

Tham khảo triển khai: [TradingView RSI](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/). Các quy ước flat-series và reset ở trên là hợp đồng dự án.

### 6.4. `bollinger_pct_b_20d`

```text
middle = mean_20(adj_close)
sigma = std_20(adj_close, ddof=0)
upper = middle + 2*sigma
lower = middle - 2*sigma
bollinger_pct_b_20d = (adj_close - lower)/(upper - lower)
```

Cần 20 mức giá hữu hạn/dương/sạch/liên tiếp. Std ở đây tính trên mức giá, không phải return; khác ddof=1 đã chọn cho realized volatility. Dải rộng bằng 0 → NaN. Giá trị ngoài [0,1] hợp lệ, không clip. Ví dụ lower=90, upper=110, close=115 → 1.25. Không coi vượt dải là lệnh mua/bán mặc định.

Nguồn khái niệm: [John Bollinger, Bollinger Bands](https://www.bollingerbands.com/bollinger-bands). Cửa sổ 20, hệ số 2 và ddof=0 được chọn tường minh trong dự án.

## 7. Pilot: phạm vi và tiêu chí bàn giao

Chưa chạy pilot khi viết tài liệu này. Chỉ triển khai pilot sau khi rà sự phù hợp giữa code và hai đặc tả features/target; không mặc nhiên tái sử dụng mask nhãn nếu định nghĩa khác hợp đồng.

### 7.1. Hai lớp kiểm tra

- Dữ liệu tổng hợp nhỏ: đối chiếu số học cho toàn bộ 16 công thức, đủ/thiếu lookback, NaN/Inf, mẫu số 0 và reset RSI. Ví dụ tính tay hoặc tham chiếu độc lập phải có expected values; không chỉ gọi cùng implementation hai lần.
- Mẫu dữ liệu thực Development: chọn SID và khoảng ngày theo các tình huống cần kiểm tra, không cố định mọi mẫu vào 2000–2002. Có thể dùng vài mã đại diện nhưng phải ghi rõ lý do chọn, date range và nguồn bars.

Nếu triển khai thực nghiệm theo đợt nhỏ, ưu tiên ret_20d, vol_realized_20d, amihud_illiq_20d, rsi_14d và bollinger_pct_b_20d để bao phủ tỷ số giá, return-window, nhiều input, trạng thái và price-window. Các feature còn lại vẫn cần kiểm tra trước full store.

### 7.2. Tình huống thực bắt buộc

Lịch sử bình thường; ngày gia nhập universe với warm-up trước đó; IPO thiếu lịch sử; split; missing bar; bad tick và phục hồi; spin-off bị cách ly; ra khỏi universe. Kiểm tra chất lượng không chỉ dựa vào membership hoặc một mask close chung.

Không cần chọn theo tên ticker đơn thuần: ghi canonical_sid và khoảng hiệu lực để tránh ticker reuse. Cho phép lấy lịch sử warm-up trước mẫu đầu ra. Không dùng OOS để chọn công thức hoặc đánh giá hiệu quả pilot.

### 7.3. Đầu ra pilot cần bàn giao

- Báo cáo công thức/phiên bản code, input, mẫu chọn và các khác biệt với đặc tả.
- CSV đối chiếu các ô chọn: feature, date, SID, input hoặc đường dẫn truy input, expected, actual, sai số, lý do NaN và pass/fail.
- Tóm tắt eligibility/coverage và kiểm tra ô ngoài membership đều NaN; giữ input warm-up trước membership.
- Dung sai công bố theo công thức; không ép mọi phép tính floating-point phải bằng 0 tuyệt đối.
- Lệnh tái tạo và kết quả tests thực chạy. Phân biệt test đã chạy với kiểm tra chưa làm.

Chưa tuning, chọn feature theo IC hay sinh full feature store trong pilot số học. Sau khi pilot đạt mới sang kiểm tra phân phối/coverage/tương quan/IC trên Development.

## 8. Nội dung còn cần rà soát

- Bổ sung nguồn học thuật cho các họ feature còn thiếu và phân biệt công thức dự án với thiết kế thực nghiệm trong nguồn.
- Chính sách eligibility đầu ra chung khi có discontinuity sau đoạn đo của momentum bỏ tháng.
- Biến đổi cross-sectional, scaling, chính sách thiếu features khi train và tiêu chí chọn/loại feature sau đánh giá Development.

Chưa triển khai full feature store hoặc thay đổi code bằng việc tạo tài liệu này.
