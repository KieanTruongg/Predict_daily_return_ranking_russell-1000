# Hành trình dữ liệu: từ nguồn đến matrices

Cập nhật nội dung ngày 2026-11-05. Tài liệu giải thích pipeline hiện hành và kết quả ghi trong artifact cục bộ; không phải xác nhận đã tái chạy toàn bộ pipeline trong lượt sửa tài liệu.

Bắt đầu học từ [hướng dẫn từng chặng](../../learning/README.md). Tra schema tại [data dictionary](../../data_dictionary.md); thứ tự chạy thực tế tại [DAG](../../pipeline_dag.md). Số bước trong tên script không phải thứ tự thực thi đầy đủ.

## 1. Bài toán và hai nguồn độc lập

Universe trả lời **ngày nào cần xét chứng khoán nào**. Kho thị trường trả lời **chứng khoán đó có giá/volume gì**. Có dữ liệu giá không tự chứng minh tư cách thành viên Russell 1000.

Nguồn universe là các file lịch sử PDF/CSV/JSON/XLS, gồm tài liệu chỉ số và holdings ETF. Holdings quỹ mô phỏng không tự đồng nhất hoàn toàn với danh sách chỉ số chính thức. File nguồn parser đọc nằm ở `data/raw/universe/raw_universe/`; bản lưu tham khảo trong docs không thay thế đường dẫn này.

Nguồn thị trường là 10 ZIP xuất từ QuantConnect ở chế độ Raw, cùng CSV splits/dividends tải riêng. Dữ liệu Raw chưa điều chỉnh corporate actions; không mặc nhiên đồng nghĩa mọi bar đều đúng thực tế.

## 2. Snapshot → danh sách theo năm

Script: `scripts/01_pipeline/01_parse_all_universe.py`.

- PDF 2000–2007: lấy ticker đầu dòng; 2009–2015: ticker cuối dòng; các PDF giai đoạn sau dùng cấu trúc đan xen.
- CSV 2008, JSON 2019/2023/2024 và XLS 2025/2026 đi qua parser riêng. XLS hiện được đọc như XML Spreadsheet bằng regex trong code, không phải mọi file mang đuôi XLS đều có cấu trúc này.
- Có bộ lọc từ nhiễu và chuẩn hóa dấu chấm thành dấu gạch ngang ở các parser tương ứng. Bộ lọc giảm nhầm lẫn, không chứng minh trích xuất hoàn hảo.
- Đầu ra: JSON tổng hợp `russell1000_pit_by_year.json`, JSON trong `by_year/`, CSV tickers tổng hợp và `extraction_quality_report.csv`.

JSON tổng hợp có cấu trúc `{"2000": ["A", "AA", ...], ...}`; từng JSON năm là một danh sách. Artifact hiện có: 27 năm, 26.919 lượt thành viên-năm, 2.884 chuỗi ticker duy nhất. Một ticker có thể xuất hiện nhiều năm; không được coi 2.884 là số chứng khoán vĩnh viễn.

Ví dụ đầu file CSV 2008 thật: `Company,Ticker`, rồi `ADC TELECOMMUNICATIONS,ADCT`. Parser lấy ADCT vào danh sách, không lấy các từ trong tên công ty. Ví dụ này minh họa một dòng, không phải chứng minh tất cả dòng đã được đối chiếu thủ công.

### Ngày snapshot và khoảng hiệu lực

Quy ước nghiên cứu: danh sách Y dùng trong [01/07/Y, 30/06/Y+1], kỳ cuối chỉ quan sát đến 30/10/2026. Đây là xấp xỉ thường niên, không phải lịch hiệu lực chính thức đã xác minh cho mọi năm; thay đổi nội năm không được tái tạo đầy đủ.

[Bảng truy nguồn 27 năm](universe_source_inventory.csv) đối chiếu extraction report với `raw_files_date_audit.json` cục bộ. Các ngày trong bảng là bằng chứng ứng viên, chưa phải ngày hiệu lực đã xác nhận:

- Không tiếp tục ghi 2001–2004 là bốn năm thiếu ngày: hồ sơ cục bộ có ngày cho các năm này.
- Audit chưa ghi ngày cho 2008/2019/2023/2024; năm 2010 có header `06/28/10` dù regex audit bỏ sót. Ngày thành lập quỹ hoặc copyright trong XLS không phải ngày snapshot.
- File 2026 có dấu ngày 15/09/2026, muộn hơn mốc áp dụng 01/07. Cần đối chiếu nguồn/snapshot: nếu đúng là holdings tháng 9 dùng ngược từ tháng 7 thì có rủi ro dùng thông tin muộn. Lượt này chỉ ghi giới hạn, chưa đổi danh sách hoặc mốc theo năm.

Khả năng parser tái tạo JSON chỉ chứng minh tính tái lập với input, không chứng minh snapshot là đúng ngày hoặc đủ thành viên thực tế.

## 3. Danh sách ticker → 10 ZIP thị trường

Scripts Cloud: availability scan và export 10 batches. Mục đích batch là chia tải truy vấn, không chia universe theo niên độ. Lấy toàn bộ lịch sử có sẵn 1998–2026 của các ticker yêu cầu, kể cả khi ngoài rổ, để giữ warm-up.

Summary trong 10 ZIP ghi 289 tickers cho mỗi batch 1–9, 283 cho batch 10: tổng 2.884 yêu cầu. Trong kho raw hiện có, 2.846 tickers có ít nhất một bar và 38 không có bar toàn kho. Không thay các số này bằng kết quả scan sơ bộ 2.871/13 của quy trình trước.

Mỗi ZIP hiện có 32 entries, ví dụ batch 01:

```text
raw/year=1998/batch_01_of_10.csv
... (29 CSV, đến 2026)
audit/batch_01_of_10_status.csv
audit/batch_01_of_10_identity.csv
audit/batch_01_of_10_summary.json
```

- CSV raw: `date, original_ticker, qc_ticker, sid, open, high, low, close, volume`.
- Status: kiểm tra yêu cầu thành công/rỗng/lỗi theo schema thực của export.
- Identity: lưu quan hệ ticker yêu cầu và định danh nhà cung cấp, chưa tự xác minh continuity.
- Summary: số batch/tickers/rows, phạm vi và chế độ Raw. Script 03 hợp nhất status/identity; summary giữ trong ZIP để đối chiếu, không biến thành nến giá.

## 4. ZIP → kho raw Parquet

Script 03 đọc CSV trực tiếp qua ZipFile, ép kiểu, gộp theo năm và bỏ trùng `(date, original_ticker)`. Lưu ý code dùng `drop_duplicates`: kiểm tra riêng các dòng bất đồng nếu muốn chứng minh an toàn, không chỉ nhìn số dòng cuối.

Đầu ra trong `data/processed/constituents_market_data/`:

- `by_year/`: 29 Parquet.
- `russell1000_constituents_daily_ohlcv_1998_2026.parquet`: 13.147.389 dòng, 9 cột theo báo cáo kho hiện có.
- `master_batch_status.csv`, `master_batch_identity.csv`.

Parquet là định dạng lưu bảng theo cột, không phải bước tự điều chỉnh giá. Gộp không có nghĩa mọi dòng được phép dùng để train.

Null/OHLC checks trong [audit raw](../../Data%20report/market_data_audit/market_data_audit_report.md) chỉ xét các dòng tồn tại. Một ngày vắng hẳn không tạo null trong bảng dài; phải kiểm tra coverage trên lịch và universe riêng.

## 5. Kho raw → canonical identity

Script 04 xây mapping từ `(original_ticker, raw_sid)` về `canonical_sid`. SID định danh chứng khoán, không đồng nhất với doanh nghiệp; nhiều lớp cổ phiếu có thể có SID riêng. Không giải mã chuỗi SID hoặc suy đoán nguyên nhân hậu tố 2T chỉ từ hình dạng chuỗi.

- Mapping hiện có 4.737 dòng, 7 cột, 3.711 canonical SID duy nhất.
- 752 lượt nối 2T: 456 `2T_STITCH_SUCCEEDING`, 296 `2T_STITCH_PRECEDING`, dựa cùng original_ticker và gap ≤10 ngày lịch.
- 94 lượt 2T không nối: 81 `STANDALONE_2T_DISCONTINUOUS`, 13 `STANDALONE_2T_NO_PERM`.
- 3.891 dòng `PERMANENT_CANONICAL`. Các nhóm trên đếm dòng mapping, không nhất thiết số chứng khoán duy nhất.

Kho canonical còn 12.247.081 dòng. Chênh raw−canonical là 900.308 dòng, không phải 1,57 triệu. Đây là chênh số dòng của hai kho; không tự giải thích hết nguyên nhân từng dòng.

Script 04 thống kê khác biệt OHLCV nhưng assertion trước mapping chỉ bắt close khớp trên `(date,sid)`; cuối cùng giữ dòng đầu cho `(date,canonical_sid)`. Không được diễn giải close khớp là toàn bộ OHLCV bit-for-bit hoặc danh tính đã xác minh. Xem [báo cáo identity/corporate actions](step3_corporate_actions_report.md).

## 6. Canonical + corporate actions → kho adjusted

Script 06 đọc kho canonical, CSV splits/dividends và 13 dòng corrections/exceptions. Đầu ra adjusted vẫn 12.247.081 dòng theo artifact, bổ sung factor, adjusted OHLCV, dividend, returns và quality flags (25 cột).

Quy ước duy nhất cho factor giá S: split 2-for-1 → S=0,5; reverse split 1-for-10 → S=10.

```text
CF[i,t] = product(S của các sự kiện có ex_date > t)
adj_price = raw_price * CF
adj_volume = raw_volume / CF
adj_dividend = dividend_amount * CF
price_return[t] = adj_close[t]/adj_close[t-1] - 1
total_return[t] = (adj_close[t]+adj_dividend[t])/adj_close[t-1] - 1
```

Code suffix-product trực tiếp nhân các S đã định nghĩa ở trên; không lấy nghịch đảo lần nữa. `searchsorted(..., side='right')` loại sự kiện tại t khỏi factor áp cho chính t, nhưng vẫn áp cho các ngày trước t.

Có split không đồng nghĩa return bằng 0: giá vẫn thay đổi vì thị trường. Total return là quy ước ghi nhận phân phối tiền trong phép đo, không phải sổ tiền mặt mô phỏng ngày nhận cổ tức, thuế và tái đầu tư thực tế.

Bad data và spin-off chưa tái tạo đầy đủ được cách ly; giữ raw để tra cứu, không điền NaN thành return 0. Giá back-adjusted có thể sử dụng sự kiện sau ngày t; khi đánh giá causality phải xét từng feature và thời điểm biết thông tin, không xem mọi mức giá adjusted là PIT tuyệt đối.

## 7. Adjusted → membership và matrices

DAG: 06 trước audit 04b và reconstruction 05, sau đó 07. Script 07 hiện trực tiếp tạo segment mapping dùng lập mask; không coi bảng temporal năm của 05 là đầu vào duy nhất của membership. Xem [báo cáo matrices](step4_matrices_masks_report.md).

Mỗi field được pivot từ `(date,canonical_sid,value)` sang bảng ngày × SID, reindex cùng tọa độ 7.252 × 3.711. Thiếu giá giữ NaN; flags có quy ước riêng. Lưu 17 fields cơ sở, indices, masks và targets trong `data/processed/matrices/`.

`membership_mask` là universe đã chọn theo mapping/loại trừ. Nó không phải toàn bộ danh sách nguồn chưa phân giải. Vì vậy tỷ lệ hợp lệ trong membership không thay thế coverage so với source universe.

Feature engine dùng `bar_quality_mask` độc lập membership để giữ input trước ngày vào rổ; mỗi feature kiểm tra cửa sổ riêng; membership chỉ lọc output T. Label mask cần tương lai chỉ phục vụ nhãn, không dùng tạo X hoặc quyết định eligibility tại T.

## 8. Kiểm tra và các quyết định tiếp theo

- 08 kiểm tra tọa độ, mask hierarchy, dịch target, ranh giới và round-trip với kho; không chứng minh đúng nguồn thị trường.
- 09 tạo EDA Development; 10 điều tra ngoại lệ. Khi sửa factor/quality upstream phải tái tạo downstream tương ứng, không chỉ vá return trong một báo cáo.
- [EDA](step6_eda_report.md) ghi rõ giới hạn nguồn, thống kê gộp và những diễn giải chưa đủ bằng chứng.
- [Features v1](../../specifications/features_v1.md) và [target/timing v1](../../specifications/target_and_timing_v1.md) là hợp đồng thiết kế; pilot xác minh implementation, chưa phải tuning.

Bốn mức kết luận cần phân biệt: **script chạy xong**, **số liệu trông hợp lý**, **công thức nhất quán**, **đã xác minh thực tế**. Không tự suy mức sau từ mức trước.
