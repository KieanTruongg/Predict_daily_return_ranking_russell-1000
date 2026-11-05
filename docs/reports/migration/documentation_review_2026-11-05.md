# Rà và sửa tài liệu phục vụ người mới — 2026-11-05

## Phạm vi

Chỉnh nội dung tài liệu hiện hành và thêm [hướng dẫn học 9 chặng](../../learning/README.md). Không tái chạy pipeline, điều chỉnh giá, đổi membership theo năm, đổi công thức features/target hoặc huấn luyện model trong công việc này. Không sửa báo cáo/artifact pilot mà agent khác đang cập nhật.

## Đầu vào dùng để đối chiếu

- Scripts 01, 02 export, 03, 04, 06, 07, 09 và loader, đọc code theo phạm vi giải thích cần sửa.
- Tên file/summary trong 10 ZIP; bảng mapping, corporate-action match audits, segment mapping, moments CSV và sanity summary hiện có.
- JSON universe, extraction report và `raw_files_date_audit.json` cục bộ. Dấu ngày là bằng chứng ứng viên, chưa xác nhận ngày hiệu lực thật từng năm.

Đọc artifact không đồng nghĩa đã chạy lại producer. Những kết quả tests có trong báo cáo cũ được giữ theo thời điểm, không dùng để chứng nhận các thay đổi code/pilot đang diễn ra đồng thời.

## Các sửa đổi chính

1. **Lineage:** sửa cấu trúc ZIP (29 CSV + 3 audit mỗi batch), số yêu cầu/ticker có bar, mapping 4.737 dòng về 3.711 SID và chênh raw→canonical 900.308 dòng. Bỏ số 1,57 triệu như lượng dedup cuối; giải thích khác biệt giữa scan sơ bộ và export.
2. **Nguồn universe:** thêm [inventory 27 năm](../data_pipeline/universe_source_inventory.csv). Đính chính việc gán 2001–2004 là thiếu ngày; không đổi quy ước 01/07. Ghi rủi ro dấu ngày 15/09/2026 trong file 2026 và ngày boilerplate không phải snapshot.
3. **Identity:** phân biệt ticker/SID/security/company; dùng ví dụ giả lập. Nối 2T dựa cùng ticker và gap lịch, không tự có xác minh tên/CUSIP. Assertion close không chứng minh OHLCV bit-for-bit hay continuity thật.
4. **Corporate actions:** thống nhất S là hệ số nhân giá trước sự kiện; CF nhân các S tương lai, không nghịch đảo hai lần. Bổ sung ví dụ số cổ phiếu/giá trị, dividend ex-date/payment date và phân loại corrections/cách ly. Nêu rõ `reference_price>0` là điều kiện code, chưa chứng minh phân loại event đầy đủ.
5. **Matrices/masks:** thêm pivot và ví dụ warm-up từng ô, phân biệt masks kho và input hygiene. Không gọi valid_data là chứng nhận khớp lệnh; 20 bars tích lũy chưa đủ mọi lookback. Script 07 tự dựng segment mapping; cập nhật DAG, không mô tả CSV temporal của 05 là dependency duy nhất.
6. **EDA:** sửa p01 thành phân vị 0,01% theo code. Tách std gộp khỏi volatility danh mục, decile hồi cứu khỏi phân nhóm PIT, liquidity khỏi market cap. Bỏ suy luận cấm OLS và sai tỷ lệ gradient MSE. Không coi rank là sửa data/non-stationarity hoặc tối ưu trực tiếp Spearman/P&L.
7. **Nguồn ngoại lệ:** không tiếp tục xác nhận câu chuyện MFA bằng mô tả cũ. Nêu giới hạn URL/accession và chuỗi giá bị thiếu ký tự trong forensic ledger; giữ CSV nguồn, không ngầm vá bằng chứng trong lượt tài liệu.
8. **Tra cứu:** đồng bộ data dictionary/context/DAG, dẫn hướng từ README dự án và mục lục docs. Không chép lại toàn bộ công thức features vào nhiều tài liệu.

## Những gì vẫn chưa được xác minh

- Lịch hiệu lực chính thức của từng snapshot, đặc biệt dữ liệu 2026 dùng từ tháng 7.
- Tất cả identity heuristic hoặc hồ sơ SEC/CUSIP tương ứng.
- Toàn bộ nguồn giá và nguyên nhân lịch sử của ngoại lệ, gồm MFA.
- Tính đúng producer của mọi audit chỉ từ đọc CSV; nguồn và nhãn VERIFIED còn cần kiểm chứng theo từng claim.
- Các kết quả pilot mới, hiệu quả dự đoán của features/model và khả năng thực thi giao dịch.

## Kiểm tra tài liệu

Kiểm tra liên kết file Markdown sau sửa và đối chiếu inventory/ZIP summaries bằng thao tác đọc. Lỗi link hoặc số đếm nếu phát hiện được sửa trước bàn giao. Kiểm tra này không chạy tải dữ liệu hoặc thay đổi processed artifacts.

Kết quả đọc kiểm tra trong lượt này:

- 167 liên kết file Markdown hợp lệ tại thời điểm kiểm tra.
- Inventory có 27 năm, tổng 26.919 ticker-năm.
- 10 ZIP, mỗi ZIP 32 entries; summary cộng 13.147.389 dòng và 2.884 ticker yêu cầu.
- Metadata Parquet: raw 13.147.389×9; canonical 12.247.081×9; adjusted 12.247.081×25. Chênh raw−canonical 900.308 dòng.
- CSV split input 4.788 dòng, điều kiện reference_price>0 chọn 2.391 dòng.

Đây là kiểm tra metadata/schema/số đếm, chưa quét toàn bộ OHLCV hoặc tái xác minh giá. Không chạy lại bộ tests để gán kết quả của thay đổi code đồng thời cho công việc tài liệu này.

Tài liệu học giúp đọc có hệ thống, không thay thế chứng cứ gốc hoặc báo cáo chạy thực tế. Các log migration và archive giữ vai trò lịch sử; HTML tổng hợp có thể vẫn phản ánh phiên bản nội dung trước đây.

## Bổ sung giải thích để hiểu bài đang làm

Đã mở rộng hướng dẫn ở cả 9 chặng theo mạch vấn đề → bằng chứng → kỹ thuật → kiểm chứng → quyết định/giới hạn. Nội dung gồm survivorship/look-ahead, provenance/parsing, batch và audit, schema/OHLC/finite/calendar/coverage, identity/dedup/heuristics, splits/dividends/spin-offs, alignment/warm-up/label purge, forensic EDA và pilot/validation/regularization dự kiến.

Các phát hiện pilot tại lần review 05/11 là ví dụ về giới hạn test coverage, không phải xác nhận trạng thái bản sửa mới. Không sửa code, artifacts hoặc báo cáo pilot trong lần bổ sung hướng dẫn này. Những phần ML/backtest chưa thực hiện được ghi là kế hoạch, không chuyển thành kết quả thực nghiệm.
