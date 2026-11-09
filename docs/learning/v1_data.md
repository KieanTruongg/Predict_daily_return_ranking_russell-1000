# V1 từ nguồn thô đến ma trận dữ liệu

Mỗi chặng dưới đây trả lời một câu hỏi, giải thích phương pháp bằng ví dụ và chỉ tới bằng chứng của v1. Các ví dụ giả lập dùng để học phép tính. Số liệu lịch sử lấy từ kết quả lưu sẵn và mã xử lý.

## 1. Chọn đúng đối tượng ở đúng thời điểm

**Universe** là tập chứng khoán được xét. V1 dùng Russell 1000, chỉ số chứng khoán Mỹ vốn hóa lớn. **Membership** là trạng thái thuộc tập ở một ngày cụ thể. **Snapshot** là ảnh chụp danh sách ở một thời điểm. Dự án cần nhiều snapshot vì thành phần chỉ số thay đổi.

**Point-in-time (PIT)** nghĩa là dựng lại trạng thái theo thông tin có thể biết tại thời điểm nghiên cứu. Đây là cách giảm hai thiên lệch:

- **Survivorship bias**, thiên lệch sống sót, xảy ra khi giữ những mã còn tồn tại ở hiện tại rồi áp ngược danh sách về quá khứ. Ví dụ giả lập, năm 2005 có A, B, C. Sau đó C phá sản. Chỉ lấy A và B sẽ xóa kết quả của C khỏi mẫu năm 2005.
- **Look-ahead bias**, thiên lệch nhìn trước, xảy ra khi dùng thông tin đến sau lúc ra quyết định. Ví dụ giả lập, dùng danh sách chụp tháng 9 để chọn mã vào tháng 7. Việc giữ cả mã phá sản vẫn chưa giải quyết được lỗi thời điểm này.

**Đầu vào và đầu ra.** Script 01 dùng **parser**, chương trình đọc cấu trúc file, để bóc ticker từ PDF, CSV, JSON và bảng tính. **Ticker** là ký hiệu giao dịch, ví dụ AAPL. Các định dạng cần cách nhận cột hoặc dòng riêng để tránh lấy nhầm tiêu đề và tên công ty. Kết quả là JSON tổng hợp dạng năm → danh sách ticker và các JSON từng năm. Theo báo cáo, có 27 năm, 26.919 lượt ticker-năm và 2.884 chuỗi ticker duy nhất. Nếu A xuất hiện 20 năm thì A có 20 lượt và đóng góp một ticker duy nhất.

**Quyết định của v1.** Dùng 01/07 năm Y đến 30/06 năm Y+1 làm khoảng hiệu lực theo quy ước dự án. Snapshot thường niên có thể bỏ sót biến động nội năm. Một phần danh sách lấy từ tài liệu quỹ mô phỏng chỉ số, nên thành phần quỹ và chỉ số có thể khác nhau. Bốn năm 2008, 2019, 2023, 2024 chưa ghi được ngày snapshot trong hồ sơ kiểm toán nguồn. Tệp 2026 có dấu tháng 9, vì vậy kết quả ngoài mẫu chính giới hạn ở các nhãn đến 30/06/2026 để tránh dùng tệp đó hồi tố.

**Kiểm tra và ý nghĩa.** So đếm số mã, chọn mẫu ticker đối chiếu từng dòng nguồn, chạy lại parser để so với JSON, rồi rà ngày và xuất xứ tài liệu. Đếm gần 1.000 giúp phát hiện lỗi lớn. Tái tạo đúng JSON xác nhận khả năng lặp lại của parser. Xác nhận thông tin sẵn có vào ngày nghiên cứu cần đối chiếu nguồn riêng. **Provenance** là hồ sơ nguồn gốc, gồm tài liệu, ngày và cách trích. Ngày chưa xác định cần giữ đúng trạng thái đó. [Nguồn, cách trích và kết quả](../reports/data_pipeline/data_lineage_report.md) · [Danh mục nguồn](../reports/data_pipeline/universe_source_inventory.csv) · [Mã parser](../../scripts/01_pipeline/01_parse_all_universe.py)

## 2. Tải lịch sử giao dịch và kiểm độ phủ

**OHLCV** là năm giá trị của một phiên: mở cửa (Open), cao nhất (High), thấp nhất (Low), đóng cửa (Close) và khối lượng giao dịch (Volume). Một bản ghi theo mã và phiên gọi là **bar**, hay nến. **Raw** là giá theo thang gốc trước điều chỉnh. **Batch** là nhóm yêu cầu tải. **Metadata** mô tả dữ liệu hoặc lần tải, ví dụ mã đã yêu cầu, mã nhà cung cấp phân giải được và số dòng trả về.

**Vì sao tải giá trước khi mã vào rổ?** Giả lập, A vào Russell ngày 03/07 nhưng đã giao dịch từ tháng 1. Tại ngày 03/07 có thể dùng giá tháng 6 để tính đặc trưng. Hợp 2.884 ticker giúp lập yêu cầu tải, còn membership theo ngày xác định cổ phiếu được xét ở đầu ra.

**Từ ZIP đến Parquet.** Script 02 xuất 10 batch từ QuantConnect. Mỗi ZIP gồm 29 CSV nến theo năm 1998–2026 và ba tệp kiểm toán. Status ghi tình trạng trả dữ liệu, identity ghi quan hệ mã yêu cầu với mã nhà cung cấp, summary ghi tổng kết batch. Script 03 gộp CSV, chuẩn hóa **schema** (cột và kiểu dữ liệu) và lưu 29 Parquet theo năm cùng một Parquet tổng 13.147.389 dòng. **Parquet** là định dạng lưu theo cột, thuận tiện khi cần đọc riêng vài trường. Theo báo cáo, 2.846 ticker có ít nhất một bar và 38 ticker không có bar toàn kho. Lần quét thử và lần tải cuối có thể cho số khác nhau. [Đặc tả ZIP và kho tổng](../reports/data_pipeline/data_lineage_report.md) · [Mã gộp](../../scripts/01_pipeline/03_process_10_batches_to_parquet.py)

**Coverage** là độ phủ, tức phần dữ liệu nhận được trên số quan sát kỳ vọng. Giả lập, có nến ở D1 và D3, thiếu nến D2. Hai dòng hiện có đều có giá, nhưng độ phủ chỉ là 2/3. Nếu sau khi loại mã không ánh xạ được chỉ còn 900 ô trên 1.000 ô nguồn, thì 891 ô có dữ liệu tương ứng 99% trên tập đã chọn và 89,1% trên tập ban đầu. Khi đọc tỷ lệ cần hỏi mẫu số là gì.

**Cách kiểm tra.** Đối chiếu số dòng với summary và tình trạng ticker với status. Kiểm tra kiểu cột, ngày hợp lệ, giá hữu hạn và dương, khối lượng không âm, quan hệ High/Low, trùng khóa và phiên thiếu trên lịch sàn. **NaN** là giá trị thiếu hoặc không tính được. Một nến đủ cột vẫn có thể mang giá sai. Thiếu cả dòng sẽ qua được phép đếm ô trống trên những dòng hiện có. Phiên sàn nghỉ khác với phiên sàn mở nhưng mã không có nến. Các nguyên nhân khác nhau cần được giữ để xử lý đúng ở bước tiếp theo. [Báo cáo kiểm toán kho giá](../Data%20report/market_data_audit/market_data_audit_report.md)

## 3. Phân giải định danh và khử trùng

**SID (Security Identifier)** là mã định danh chứng khoán từ nhà cung cấp. **Canonical SID** là khóa định danh kho v1 sử dụng sau khi đối chiếu. Một công ty có thể có nhiều lớp cổ phiếu và một ticker có thể được tái sử dụng.

**Giả lập.** OLD và NEW cùng chỉ chứng khoán S1. Hai yêu cầu tải trả đúng một nến S1 ở ngày D. Hai dòng cho một quan sát (D,S1) sau khử trùng. Trường hợp ABC chỉ S2 ở giai đoạn cũ và S3 ở giai đoạn mới đòi hỏi giữ khóa riêng. Nối theo ABC sẽ so giá của hai tài sản và có thể tạo một lợi suất giả. Vì quan hệ ticker và SID có thể nhiều-nhiều, 2.884 ticker và 3.711 canonical SID có thể cùng đúng.

**Xử lý và kết quả.** Script 04 xây bảng đối chiếu và gộp về một dòng theo ngày và canonical SID. Từ 13.147.389 còn 12.247.081 dòng. Mã giữ dòng đầu tiên sau các bước kiểm tra và lựa chọn. Số dòng giảm xác nhận khóa đã được gộp. Để hiểu vì sao giữ một dòng, cần xem bằng chứng định danh, ngày và chênh lệch giữa các trường Open/High/Low/Close/Volume. **Heuristic** là quy tắc suy đoán. Ví dụ, cùng ticker và hai đoạn 2T liền kề trong phạm vi 10 ngày lịch là tín hiệu để xem xét ghép. Khoảng cách ngắn chỉ cung cấp căn cứ kỹ thuật, còn bằng chứng độc lập cần xem riêng. [Báo cáo định danh](../Data%20report/market_data_audit/step2_identity_and_corporate_actions_report.md) · [Mã đối chiếu và khử trùng](../../scripts/01_pipeline/04_audit_identity_and_build_canonical_mapping.py)

**Ghép membership theo khoảng.** Script 05 liên hệ ticker-năm với SID có lịch sử phù hợp. Script 07 lập phân đoạn gồm ngày đầu, ngày cuối và cấp bằng chứng. Hai SID chồng thời gian hoặc thiếu giá toàn kỳ cần được ghi riêng. **Strict membership** chỉ dùng phân đoạn cấp 1 theo tiêu chí SID vĩnh viễn trong quy trình. **Resolved membership** gồm các phân đoạn cấp 1 và các phân đoạn heuristic được chấp nhận. Tên cấp bằng chứng mô tả tiêu chí đối chiếu trong kho. V1 học trên strict, còn các thống kê kiểm toán dùng resolved cần đọc theo đúng mẫu số. [Quy tắc phân đoạn](../reports/data_pipeline/step4_matrices_masks_report.md) · [Mã tạo hai mặt nạ](../../scripts/01_pipeline/07_build_2d_matrices_and_masks.py)

## 4. Điều chỉnh giá để đo đúng biến động

**Corporate action** là sự kiện doanh nghiệp làm thay đổi cổ phần hoặc quyền lợi của người nắm giữ. Nó có thể tạo bước nhảy trên giá thô dù giá trị kinh tế thay đổi ít hơn. **Return** là tỷ suất thay đổi giữa hai thời điểm, tính từ giá hoặc giá trị nắm giữ tùy định nghĩa.

- **Split**, chia tách cổ phiếu. Giả lập, một cổ phiếu giá 100 USD chia 2:1 thành hai cổ phiếu giá 50 USD. Tổng vẫn 100 USD. So 50/100 cho −50% giả. Đưa giá cũ về cùng đơn vị cổ phiếu mới thì so 50/50, lợi suất bằng 0. **Reverse split** là gộp cổ phiếu, có thể làm giá đơn vị tăng mạnh. Logic quy đổi tương tự.
- **Cash dividend**, cổ tức tiền mặt. Giả lập, giá từ 100 xuống 98 USD và người nắm giữ nhận 2 USD. **Price return** là −2%, còn **total return** tính cả tiền mặt nên bằng 0 trong ví dụ. Ngày thực tế còn có giao dịch và tin tức, vì vậy mức giảm có thể khác 2 USD.
- **Spin-off**, tách công ty con. Cổ đông có thể nhận cổ phiếu công ty con, còn chuỗi giá công ty mẹ chỉ ghi phần mẹ. Nếu chưa đo được phần nhận thêm, dự án cách ly bước giảm để tránh tính sai lợi suất hoặc đưa vào cửa sổ đặc trưng.
- **Bad tick** là mức giá ghi nhận lỗi hoặc nghi lỗi. **Ticker collision** là nhầm dữ liệu với chứng khoán có ký hiệu trùng hoặc gần giống. **Corrections and exceptions** là bảng quyết định sửa và ngoại lệ theo định danh, ngày, loại lỗi và bằng chứng. Cờ cách ly giúp dừng dùng đoạn dữ liệu trong phép tính và giữ dấu vết.

**Từ đầu vào đến cột đầu ra.** Script 06 nối bảng splits và dividends với giá theo mã và ngày. Từ 4.788 bản ghi split, quy trình lọc 2.391 bản ghi có giá tham chiếu dương, rồi bổ sung 5 reverse split từ bảng hiệu chỉnh. Số này mô tả cách sàng lọc. Để biết bao nhiêu sự kiện khớp SID và được áp vào nến cần xem trạng thái ghép riêng. Hệ số chia tách lũy tích CF quy giá về cùng đơn vị. Giá điều chỉnh bằng giá thô nhân CF, khối lượng điều chỉnh bằng khối lượng thô chia CF, cổ tức điều chỉnh bằng cổ tức thô nhân CF. Price return là giá điều chỉnh hôm nay chia giá điều chỉnh phiên trước, trừ 1. Total return cộng cổ tức điều chỉnh vào tử số trước khi chia. Nhãn v1 lấy price return điều chỉnh split giữa hai phiên liền nhau. [Công thức, số khớp và ví dụ](../reports/data_pipeline/step3_corporate_actions_report.md) · [Mã xử lý](../../scripts/01_pipeline/06_process_corporate_actions_and_adjusted_prices.py)

**Cách kiểm tra.** Chọn sự kiện biết tỷ lệ và ngày, tính lại hai đầu giá rồi đối chiếu. Kiểm tra hiệu total return trừ price return có bằng cổ tức điều chỉnh chia giá trước. Dùng lịch sàn để tránh coi hai bar qua một phiên trống là lợi suất một ngày. Khớp công thức xác nhận logic trong ca đã thử. Xác minh mức giá và nguyên nhân kinh tế cần nguồn độc lập. Đặc trưng dùng tỷ lệ giá cùng thang đo và đặc trưng dùng mức giá điều chỉnh tuyệt đối có tính chất khác nhau, nên mỗi đặc trưng cần ghi rõ giá đưa vào.

## 5. Tạo ma trận, mặt nạ và lịch sử đệm

**Pivot** là đổi bảng dài (ngày, SID, giá trị) sang ma trận ngày × SID. V1 dùng lưới 7.252 phiên × 3.711 cột. Có ô thiếu trước niêm yết, sau khi rời sàn hoặc ở phiên thiếu dữ liệu. **Mask**, mặt nạ, là bảng True/False cùng tọa độ. Mỗi mặt nạ trả lời một câu hỏi:

1. **Membership mask** hỏi mã có thuộc tập đang xét tại T không. Strict là lựa chọn của bộ dữ liệu học v1.
2. **Bar quality mask** hỏi nến lịch sử có thể đưa vào phép tính không. Bộ nạp xét có giá điều chỉnh dương, tránh cờ nến lỗi và spin-off, đồng thời có thể thêm ngoại lệ theo trường giá. Kiểm tra hữu hạn, khối lượng và độ đủ cửa sổ còn do từng đặc trưng hoặc tập học thực hiện.
3. **Valid data mask** trong script 07 dùng tập resolved, giá và khối lượng dương, phiên liên tiếp, số nến tích lũy ít nhất 20 và cờ chất lượng. Đây là tiêu chí dữ liệu của ma trận kiểm toán. Tập học strict có quy tắc chọn hàng riêng.
4. **Valid label mask** trong script 07 xét thêm nến và lợi suất kế tiếp để biết có chấm được nhãn. Khi sinh điểm tại T, chỉ dùng điều kiện biết tại T. Khi chấm, mới xét dữ liệu T+1.

**Warm-up** là lịch sử đệm để tính đủ đặc trưng. **Rolling window** là cửa sổ lịch sử trượt theo ngày. Giả lập, để tính lợi suất 20 phiên với yêu cầu đủ nến sạch liên tiếp, cần 21 mức giá qua 20 khoảng. Nếu mã vừa vào rổ tại T, lịch sử sạch trước đó vẫn dùng được. Nếu một nến giữa cửa sổ thiếu, kết quả phải thiếu theo hợp đồng. Số nến tích lũy đạt 20 ở mặt nạ kiểm toán chưa bảo đảm cửa sổ 21 hoặc 253 nến đều sạch. Quy trình dùng mặt nạ chất lượng để lọc lịch sử và membership khi xuất đặc trưng ở T.

**Nhãn** là kết quả cần dự đoán. Lợi suất từ Close 02/01 tới Close 03/01 nằm ở hàng tín hiệu 02/01. **Purge** là loại mẫu có khoảng nhãn cắt ranh giới. Phiên 29/12/2023 vẫn có thể sinh điểm, nhưng nhãn rơi vào 02/01/2024 nên bị loại khỏi Development, tức tập dùng để xây mô hình. Phiên cuối kho 30/10/2026 thiếu giá kế tiếp.

**Cách kiểm tra.** So tọa độ, kiểm thứ bậc valid label ⊆ valid data ⊆ resolved membership, kiểm nhãn dịch đúng một phiên, kiểm ranh giới, rồi đối chiếu mẫu ô với kho giá. Lần kiểm toán lưu sẵn ghi 6.333.323 ô resolved membership, 6.311.822 ô valid data và 6.308.873 ô valid label. Những con số này mô tả ma trận kiểm toán. Báo cáo học máy dùng mẫu số strict riêng. [Báo cáo ma trận](../reports/data_pipeline/step4_matrices_masks_report.md) · [Bộ nạp chất lượng](../../src/data/matrix_loader.py) · [Mã kiểm tra](../../scripts/01_pipeline/08_validate_matrices_and_sanity_checks.py)

## 6. Khám phá dữ liệu và điều tra điểm cực đoan

**EDA (Exploratory Data Analysis)** là phân tích khám phá dữ liệu trước khi học mô hình. Nó giúp hỏi phân phối trông ra sao, vùng nào thiếu dữ liệu và ca nào cần xem lại. Script 09 xem lợi suất ngày trong Development bằng mặt nạ dữ liệu. Script 10 điều tra giá trị bất thường. **Stock-day** là một cặp chứng khoán–phiên. 5.610.691 stock-days là số ô trong mẫu EDA, và các ô cùng ngày có thể phụ thuộc nhau.

- **Mean** là trung bình, **median** là mốc chia đôi mẫu, **standard deviation** là độ lệch chuẩn đo độ phân tán. Kết quả lưu mean khoảng +0,0379% và độ lệch chuẩn gộp khoảng 2,653% theo stock-day. Đo biến động danh mục cần chuỗi lợi suất của chính danh mục.
- **Histogram** là biểu đồ tần suất theo khoảng giá trị. **Q-Q plot** đối chiếu phân vị mẫu với phân vị phân phối chuẩn. **Phân vị** là mốc để một tỷ lệ quan sát nằm dưới nó. **Đuôi dày** cho biết các điểm ở xa vùng giữa xuất hiện nhiều hơn hình chuẩn gợi ý. Các hình giúp đặt câu hỏi, còn nguyên nhân cần xem từng trường hợp. Hình giới hạn quanh vùng giữa vẫn có thể đến từ kho chứa giá trị ngoài hình.
- **Dispersion** đo độ khác biệt lợi suất giữa các mã cùng phiên. **Liquidity** là thanh khoản. Trong hình EDA, giá nhân khối lượng là đại diện gần đúng cho lượng tiền giao dịch. Dự án chia SID thành mười nhóm dựa trên giá trị này trong toàn Development. Hình mô tả mẫu hồi cứu. Dùng nguyên nhóm toàn kỳ để ra quyết định tại một ngày lịch sử sẽ đưa thông tin muộn vào quyết định.

**Cách điều tra.** Lấy đúng SID và các ngày trước/sau. Xem nến thô, giá điều chỉnh, hệ số split và phiên thiếu. Kiểm tra định danh có bị nối nhầm rồi tìm nguồn xác nhận sự kiện và mức giá. Ví dụ CHK từ 0,1313 lên 16,375 cho lợi suất thô khoảng +12.371%. Với hệ số gộp 200, phép tính 16,375/(0,1313×200)−1 cho khoảng −37,64%. Đây là đối chiếu số học. Xác minh hai mức giá là bước riêng. MFA +227,87% vẫn cần nguồn độc lập cho mức giá và nguyên nhân. Bản ghi chưa rõ cần giữ trạng thái để có thể truy lại. [Báo cáo EDA, hình và bảng ngoại lệ](../reports/data_pipeline/step6_eda_report.md)

## Tự kiểm tra trước khi sang đặc trưng

1. Một mã mới vào rổ tháng 7 nhưng có lịch sử từ tháng 6. Mình dùng dữ liệu tháng 6 ở bước nào và chọn mã ở bước nào?
2. Vì sao có thể có nhiều SID hơn ticker? Khi hai dòng cùng ngày và SID có giá khác nhau, thông tin nào cần xem trước khi chọn dòng?
3. Vì sao một split có thể tạo lợi suất giả? Vì sao cổ tức làm price return khác total return?
4. Nếu một mã thiếu nến thứ Ba, tại sao nến thứ Tư không dùng nến thứ Hai để tính lợi suất một phiên?
5. Giá sau điều chỉnh khớp công thức xác nhận được điều gì? Để xác nhận sự kiện có thật cần thêm bằng chứng gì?
