# Identity, corporate actions và corrections

Cập nhật giải thích ngày 2026-11-05. Các số đếm bên dưới đọc từ artifact đã có; chưa tái chạy kho giá trong lượt này. [Hướng dẫn học](../../learning/README.md) · [Lineage](data_lineage_report.md) · [Data dictionary](../../data_dictionary.md).

## 1. Ticker, SID và canonical SID

Ticker là tên giao dịch có thể đổi hoặc tái sử dụng. SID là định danh nhà cung cấp; canonical SID là định danh kho sau quy tắc hợp nhất. Một công ty có nhiều lớp cổ phiếu có thể có nhiều chứng khoán. Không phải mọi SID đều tương ứng một công ty riêng và không phải mọi cặp cùng ticker là cùng chứng khoán.

Ba ví dụ **giả lập**, không phải ca thị trường đã xác minh:

- Đổi tên: OLD và NEW cùng raw SID S1, cùng bars → lưu S1 một lần/ngày, giữ bảng alias để truy nguồn.
- Tái sử dụng: ABC có S1 trong thời kỳ cũ, S2 trong thời kỳ mới → không nối chỉ vì giống ticker. Snapshot ngày nào phải tra đúng khoảng.
- 2T: ABC 2T kết thúc 01/06, SID S2 bắt đầu 05/06 → gap 4 ngày lịch là điều kiện heuristic, chưa chứng minh cùng thực thể. Nếu áp quy tắc nối thì phải giữ nhãn giả định.

## 2. Mapping thực tế và dedup

[canonical_security_mapping.csv](../../Data%20report/market_data_audit/tables/canonical_security_mapping.csv): 4.737 dòng × 7 cột, 3.711 canonical SID duy nhất. 752 dòng nối 2T gồm 456 nối sau, 296 nối trước. 81 2T gián đoạn và 13 không có permanent tương ứng được giữ riêng. 3.891 dòng permanent. Các số này đếm dòng mapping, không phải tất cả là unique security counts.

Script 04 chọn cùng original_ticker, xét khoảng min/max ngày và ngưỡng ≤10 ngày lịch. Không có bước tự xác minh tên công ty/CUSIP/SEC trong quy tắc này. Nhãn VERIFIED trong bảng là nhãn phân loại của pipeline, không mặc nhiên là xác minh pháp lý độc lập.

Raw 13.147.389 dòng → canonical 12.247.081 dòng: chênh 900.308. Giữ một dòng `(date,canonical_sid)` bằng `keep='first'`. Script 04 có thống kê khác biệt OHLCV nhưng assertion ban đầu chỉ kiểm tra close cho `(date,sid)`; không được gọi toàn bộ chuỗi bit-for-bit chỉ từ assertion này. Bảng conflict do 06 tạo hỗ trợ đối chiếu thêm, không xác minh identity chỉ nhờ hai giá giống nhau.

CSV segment có 27.103 dòng, khác 26.919 lượt thành viên-năm do một lượt có thể chia nhiều khoảng SID. Phân đoạn ambiguous/unresolved giữ trong ledger, không kích hoạt membership. Xem [matrices](step4_matrices_masks_report.md) về bảng dùng thực sự.

## 3. Split: thay đơn vị cổ phiếu

Ví dụ giả lập: trước split có 1 cổ phiếu giá 100. Split 2-for-1 tạo 2 cổ phiếu giá tham chiếu 50. Tổng vẫn 100 nếu không có biến động thị trường. Return raw 50/100−1 = −50% là sai cách so đơn vị.

Định nghĩa S là hệ số nhân giá trước sự kiện: 2-for-1 → S=0,5; reverse 1-for-10 → S=10. Quy ước duy nhất:

```text
CF[t] = product(S[k] for ex_date[k] > t)
adj_OHLC[t] = raw_OHLC[t] * CF[t]
adj_volume[t] = raw_volume[t] / CF[t]
```

Ví dụ sau split giá thực đóng cửa 51: adjusted trước=50, sau=51 → return +2%, không ép về 0. Giá × volume điều chỉnh bảo toàn theo đại số; dùng tolerance khi kiểm tra floating-point.

Factor tại ngày split không bao gồm chính sự kiện đó; các ngày trước có bao gồm. Code dùng suffix product và `searchsorted(side='right')`. Không lấy nghịch đảo S lần nữa. Có ngày sự kiện nhưng không có bar không đồng nghĩa mọi factor đó vô dụng: factor vẫn có thể ảnh hưởng đoạn lịch sử trước sự kiện.

## 4. Vì sao 4.788 bản ghi split không dùng nguyên 4.788?

Đầu vào export chứa nhiều loại bản ghi; script 06 chọn `reference_price > 0`, còn 2.391 bản ghi trong quy trình hiện hành. Bổ sung 5 reverse splits từ corrections → audit 2.396 dòng.

Đây là **điều kiện lọc đang triển khai**, không phải bằng chứng `reference_price` tự xác định đúng loại sự kiện trong mọi trường hợp. Muốn xác minh đầy đủ cần đối chiếu split_type/metadata nguồn. Không gọi 2.397 dòng bị lọc là những sự kiện thị trường thật bị mất hoặc đã giải quyết hết chỉ dựa vào số đếm.

[splits audit](../../Data%20report/market_data_audit/tables/splits_matched_unmatched_audit.csv): 2.333 MATCHED_EXACT_BAR; 48 PRIOR_TO_LISTING; 12 NON_TRADING_DAY_OR_HALT; 3 SID_NOT_IN_WAREHOUSE. Tên category do code suy từ coverage, không xác minh lý do thật như IPO/halt bằng hồ sơ bên ngoài.

[dividends audit](../../Data%20report/market_data_audit/tables/dividends_matched_unmatched_audit.csv): 96.773 dòng, 95.043 khớp bar; 1.191 prior, 379 non-trading/halt, 156 SID absent, 4 post. Các nhóm cùng giới hạn suy luận như trên.

## 5. Dividend: phân phối tiền

Ví dụ giả lập: trước ngày không hưởng quyền, giá 100; phân phối 2 tiền/cổ phiếu. Nếu hôm đó đóng cửa 98, price return = −2% nhưng phép đo gồm tiền phân phối là (98+2)/100−1=0%.

Đây là ví dụ không có biến động khác. Giá thực tế không bắt buộc giảm đúng 2 vì giao dịch thị trường vẫn diễn ra. Ex-date xác định quyền hưởng; payment date là lúc thanh toán tiền và có thể khác ngày. Tổng lợi suất ở đây ghi nhận dividend theo quy ước dữ liệu, chưa mô phỏng tiền khả dụng, thuế, chi phí hoặc chiến lược tái đầu tư.

```text
adj_dividend[t] = dividend_amount[t] * CF[t]
r_price[t] = adj_close[t]/adj_close[t-1] - 1
r_total[t] = (adj_close[t]+adj_dividend[t])/adj_close[t-1] - 1
r_total[t] - r_price[t] = adj_dividend[t]/adj_close[t-1]
```

Chỉ tính daily return trên hai phiên hợp lệ, đúng định danh/liền nhau. Target chính v1 chọn price return chưa gồm dividend; không tự đổi loại return.

## 6. Ba dạng can thiệp, không gộp thành sửa giá

[Corrections/exceptions CSV](../../Data%20report/market_data_audit/tables/market_data_corrections_and_exceptions.csv) hiện có 13 dòng:

- CORR_001–005: bổ sung/override split factor cho CHK, CRC, ADCT, AA, DYN trước khi tính adjusted series. Đây là sửa event input, không chỉ vá một return.
- CORR_006–009: KSU, SSP, COMS, PENN có discontinuity spin-off chưa tái tạo đủ lợi ích từ tài sản nhận thêm. Cách ly, không gọi price drop là toàn bộ mức lỗ của cổ đông.
- CORR_010–013: khoảng nghi lỗi MKL, SABR, LOW, CPTH được gắn quality flags và return NaN, gồm recovery theo chính sách code.

Mỗi dòng cần nguồn truy được, ngày, SID, tham số và action. CSV hiện có chuỗi mô tả nguồn, chưa phải mọi dòng đều có URL/accession và bằng chứng giá được kiểm tra độc lập. Không khẳng định đã xem Bloomberg/CRSP/tape nếu không có artifact truy được. Những câu chuyện về collision/halt là giả thuyết cần bằng chứng tương ứng.

Ví dụ CHK trong dữ liệu đã điều tra: close 0,1313 → 16,375 với factor 200 → 16,375/(0,1313×200)−1 ≈ −37,64%, thay vì raw khoảng +12.371%. Đây là đối chiếu số học trên hai giá đã ghi; việc xác nhận nguồn giá/sự kiện là mức bằng chứng khác.

## 7. Kiểm tra, kết quả và giới hạn

[split formula audit](../../Data%20report/market_data_audit/tables/split_formula_mathematical_audit.csv) kiểm tra factor/return; [match summary](../../Data%20report/market_data_audit/tables/corporate_actions_match_summary.csv) kiểm tra đối chiếu ngày có bar. Khớp công thức không chứng minh split input đúng; return nhỏ hơn 25% cũng không chứng minh đúng sự kiện.

EDA sau corrections ghi std gộp khoảng 2,653%, excess kurtosis 66,875 và max +227,87%. Phân phối bớt cực đoan hỗ trợ phát hiện lỗi cũ nhưng không phải chuẩn chất lượng tuyệt đối. MFA và một số nguồn còn cần kiểm tra độc lập; không gọi mọi điểm còn lại là thị trường thật vì thống kê trông hợp lý.

Khi xây features, giữ raw để tra, làm sạch input bằng quality flags trước rolling, kiểm tra toàn cửa sổ và reset chỉ báo có trạng thái khi cần. Không fill NaN thành return 0 hoặc tự nối qua spin-off. [Đặc tả features](../../specifications/features_v1.md) quy định riêng cho từng công thức.
