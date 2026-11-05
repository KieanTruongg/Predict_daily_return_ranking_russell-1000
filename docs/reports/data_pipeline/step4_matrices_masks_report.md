# Matrices, membership, quality và nhãn

Cập nhật ngày 2026-11-05 từ code/artifact hiện có, chưa tái tạo matrices trong lượt này. [Hướng dẫn học](../../learning/README.md) · [Lineage](data_lineage_report.md) · [Đặc tả features](../../specifications/features_v1.md).

## 1. Pivot làm gì?

Bảng dài có mỗi dòng là `(date,canonical_sid,value)`. Pivot đưa ngày vào hàng, SID vào cột. Ví dụ giả lập:

```text
D1, S1, 100        thành close:        S1    S2
D2, S1, 102                           D1 100   NaN
D2, S2,  50                           D2 102    50
```

NaN ở D1/S2 nghĩa là không có mức giá tương ứng trong dữ liệu, không phải giá 0. Pivot không tự chọn thành viên; mask làm việc đó. Cùng một ô `(T,SID)` ở close, volume, features và masks phải cùng đối tượng/thời điểm.

Lưới hiện có 7.252 ngày × 3.711 canonical SIDs = 26.912.172 ô mỗi field. Không có nghĩa có 3.711 mã giao dịch hoặc thuộc Russell mỗi ngày. Wide format thuận tiện cho tính theo hàng/cột nhưng tốn bộ nhớ cho ô thiếu; long format vẫn hợp lệ nếu triển khai đúng, không phải cấu trúc sai về nguyên tắc.

## 2. Các artifact

Trong `data/processed/matrices/`:

- Hai tọa độ: `matrix_dates_index.parquet`, `matrix_columns_sids.parquet`.
- 17 fields cơ sở: raw OHLCV, adjusted OHLCV, cumulative_split_factor, adj_dividend, daily_return, total_return, is_consecutive_session, is_bad_data_period, is_spinoff_discontinuity.
- Membership: strict, resolved và `membership_mask` (bản tương thích của resolved).
- `valid_data_mask`, `valid_label_mask`, hai targets next_return/next_total_return.

Giá thiếu giữ NaN. Code 07 fill flags thiếu thành False và adj_dividend thiếu thành 0 theo schema; điều này không biến bar thiếu thành hợp lệ. Không áp quy tắc fill dividend sang return/giá.

## 3. Membership được dựng từ đâu?

Script 07 đọc JSON theo năm và canonical mapping, rồi trực tiếp xuất [segment mapping](../../Data%20report/market_data_audit/tables/universe_constituent_segments_mapping.csv) gồm 27.103 dòng. Mỗi dòng là một phân đoạn của một lượt ticker-năm; có cả phân đoạn bị loại. Một ticker-năm có thể có nhiều dòng, khác 26.919 lượt gốc.

Script 05 ghi bảng temporal theo năm; 04b ghi bảng audit riêng. Cần phân biệt các bảng, không gọi bảng 05 là nguồn duy nhất mà 07 đọc để dựng membership.

- LEVEL_1: permanent duy nhất theo quy tắc pipeline.
- LEVEL_2: chuyển tiếp tuần tự, heuristic chưa xác minh.
- LEVEL_3: 2T heuristic/standalone theo phân loại code.
- LEVEL_4: ambiguous, loại khỏi mask.
- LEVEL_5/6: không có bar trong khoảng hoặc không có mapping, loại khỏi mask.

`is_included_in_mask` quyết định bản resolved. Strict chỉ dùng LEVEL_1. Tên VERIFIED là mức phân loại nội bộ, không tự chứng minh mọi nguồn/corporate identity đã được xác minh pháp lý.

Khoảng [01/07/Y,30/06/Y+1] là xấp xỉ nghiên cứu. Ngày thực có bar/min-max còn ảnh hưởng phân đoạn, vì vậy membership là **universe đã phân giải/chọn dùng**, không phải ground truth chỉ số độc lập hoàn toàn khỏi coverage. Ghi riêng các trường hợp bị loại và coverage so với snapshot.

## 4. Hai hệ mask cần phân biệt

### 4.1. Masks lưu trong kho

`membership_mask[T,i]`: SID được đưa vào universe chọn dùng tại T. 1998–30/06/2000 False vì chỉ dùng làm warm-up.

`valid_data_mask`: membership AND close dương/có giá AND volume dương AND phiên liên tiếp AND có ít nhất 20 bars tích lũy AND không bad/spinoff theo code 07.

Đây là điều kiện dữ liệu của pipeline, **không chứng minh khớp lệnh được**. 20 bars tích lũy có thể nằm rời rạc và không đủ cho return 20 phiên cần 21 giá, chưa nói feature dài hơn.

`valid_label_mask`: valid_data tại T AND điều kiện giá/volume/phiên/return tại T+1 AND không thuộc ngày purge. Do dùng tương lai, chỉ phục vụ nhãn, không quyết định features hoặc eligibility dự đoán/giao dịch tại T. Trước khi dùng cho target v1 phải đối chiếu [hợp đồng target](../../specifications/target_and_timing_v1.md), vì code hiện có điều kiện volume/20 bars ngoài công thức return đơn thuần.

Quan hệ `label ⊆ data ⊆ membership` là invariant nội bộ của các masks lưu này, không phải chứng minh không còn mọi leakage.

### 4.2. Mask dùng để tính features

`load_bar_quality_mask` tạo mask cơ sở từ có adj_close dương và không bad/spinoff, độc lập membership. Hiện được dựng trong loader, không mặc nhiên là một file Parquet mới đã lưu.

Quy trình:

1. Giữ lịch sử giá/volume/return sạch kể cả trước ngày gia nhập.
2. Mỗi feature kiểm tra riêng finite, miền input, đủ cửa sổ và continuity. Mask close chung không kiểm tra hộ mọi high/low/volume/Inf.
3. Tính feature, rồi lọc membership tại ngày đầu ra T.
4. Không đưa label mask vào tính X.

RSI là chỉ báo có trạng thái cần seed/reset, không thể diễn đạt mọi feature bằng `rolling(min_periods=W)`.

## 5. Ví dụ warm-up từng ô

Dùng ví dụ giả lập 5 phiên, S1 gia nhập ở D4; tính return 2 phiên, cần 3 mức giá:

```text
Ngày              D1   D2   D3   D4   D5
Close            100  101  102  103  104
Membership         F    F    F    T    T
Bar quality        T    T    T    T    T
ret_2d output    NaN  NaN  NaN 103/101-1 104/102-1
```

Ở D4 dùng D2–D4 dù D2/D3 chưa thuộc rổ. Nếu lọc input bằng membership trước rolling sẽ mất lịch sử và ra NaN sai ở D4.

Nếu D3 bad tick, ret_2d ở D4/D5 phải NaN; sau khi cửa sổ hoàn toàn thoát bar lỗi mới phục hồi. Với real return 20 phiên, cần 21 mức giá, không chỉ 20.

Tại D4, nhãn close-to-close dùng giá D5. Nếu D5 không có dữ liệu, X tại D4 vẫn có thể hợp lệ nhưng y thiếu; không dùng sự thiếu nhãn để xóa input hay suy rằng tại D4 không thể dự đoán.

## 6. Ranh giới và phiên thiếu

Nếu thứ Sáu T có giá và thứ Hai kế tiếp là phiên hợp lệ, đó là T+1 dù cách ba ngày lịch. Nếu lịch có phiên nhưng mã thiếu bar, không shift tùy ý sang bar sau để gọi là return một phiên.

Ngày 29/12/2023 có features/lịch sử hợp lệ nhưng target sang 02/01/2024 bị purge khỏi Development. Phiên cuối kho 30/10/2026 không có target kế tiếp. Mỗi fold train/validation còn cần purge theo horizon riêng; xử lý một ranh giới OOS không thay thế các kiểm tra đó.

## 7. Kết quả đã ghi và cách diễn giải

[Sanity summary](../../Data%20report/market_data_audit/tables/matrix_sanity_check_summary.csv) ghi: membership 6.333.323 ô, valid_data 6.311.822 ô, valid_label 6.308.873 ô. Không lấy số valid_label làm số strict-membership; hai tập có ý nghĩa khác nhau.

Summary ghi không vi phạm hierarchy, target shift khớp, purge đúng và round-trip mẫu với kho. Đây là kiểm tra tính nhất quán giữa artifact và quy tắc, chưa xác minh tất cả giá thực tế. [Coverage theo kỳ](../../Data%20report/market_data_audit/tables/matrix_and_mask_coverage_by_period.csv) phân biệt coverage vs resolved và vs snapshot; không đánh tráo mẫu số.

[Sửa thư viện](../library/library_edge_cases_and_fixes_report.md) ghi bảo toàn warm-up và tra SID theo ngày. Pilot cần đối chiếu thêm từng feature theo đặc tả, không suy tất cả 16 đã đúng vì bộ tests nền pass.
