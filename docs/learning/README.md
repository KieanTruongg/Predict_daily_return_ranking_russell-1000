# Học pipeline từ đầu, theo từng chặng

## Đọc v1 từ đầu

Nếu cậu mới bắt đầu với định dạng file, Python hoặc học máy, mở [V1 từ đầu — Từng file và từng công cụ làm gì?](v1_files_and_tools.md) trước. Tài liệu đi từ nguồn thô đến báo cáo, giải thích từng công cụ và dẫn sang các chương chi tiết bên dưới.

1. [Dữ liệu và cách kiểm tra](v1_data.md). Tìm hiểu vì sao cần danh sách Russell 1000 theo thời điểm, cách nhận diện đúng cổ phiếu, điều chỉnh giá và kiểm tra dữ liệu trước khi học.
2. [Đặc trưng, nhãn và mô hình](v1_features_models.md). Theo dõi một dòng dữ liệu từ lịch sử giá đến điểm dự báo. Xem cách nhóm thử từng cấu hình trên quá khứ và chốt mô hình.
3. [Đánh giá ngoài mẫu và mô phỏng danh mục](v1_evaluation.md). Tự tính thử tương quan thứ hạng, đọc kết quả 624 phiên và đối chiếu lợi suất trước và sau chi phí.
4. [Biên bản rà soát v1](v1_review.md). Xem phép kiểm nào đã được đối chiếu, giới hạn nào còn lại và tài liệu nào đã được dọn.

[Báo cáo thực nghiệm v1](../reports/baseline/comprehensive_course_project_report.md) là bản tổng hợp số liệu và hình. Ba chương trên là bản giải thích dành cho người học. Phần chín chặng bên dưới là hướng dẫn có từ trước khi hoàn tất huấn luyện và mô phỏng danh mục, hữu ích khi muốn đào sâu dữ liệu và lịch sử sửa lỗi.

Cập nhật: 2026-11-05. Dành cho người biết ML cơ bản nhưng mới làm dữ liệu chứng khoán. Đọc lần lượt; mỗi chặng có câu hỏi tự kiểm tra và phần giải thích theo mạch vấn đề → bằng chứng → kỹ thuật → kiểm chứng → quyết định/giới hạn. Các ví dụ ghi **giả lập** để giải thích, không phải bằng chứng kiểm thử đã chạy.

## Chọn chặng cần đọc

1. [Bài toán và hai loại bias](#chặng-1--bài-toán-là-gì-vì-sao-xây-lại)
2. [Universe và provenance](#chặng-2--tìm-universe-lịch-sử)
3. [Thu thập theo batch](#chặng-3--thu-thập-lịch-sử-thị-trường-và-hiểu-zip)
4. [Merge và chất lượng/coverage](#chặng-4--merge-parquet-và-kiểm-tra-chất-lượngcoverage)
5. [Identity và dedup](#chặng-5--identity-và-khử-trùng)
6. [Corporate actions và corrections](#chặng-6--split-dividend-spin-off-và-corrections)
7. [Matrices, masks và nhãn](#chặng-7--matrices-masks-warm-up-và-nhãn)
8. [EDA và điều tra ngoại lệ](#chặng-8--eda-ngoại-lệ-và-bằng-chứng)
9. [Features, pilot và đánh giá ML](#chặng-9--features-target-pilot-rồi-mới-model)

## Cách hiểu bài đang làm

Đọc phần khái niệm/ví dụ trước, sau đó đọc mục **Từ vấn đề đến phương pháp** của cùng chặng. Mỗi lựa chọn kỹ thuật phải gắn với lỗi hoặc rủi ro cụ thể, không chỉ liệt kê tên hàm Python.

Để hiểu mỗi bước, lần lượt trả lời: **vấn đề và hệ quả → bằng chứng dự án quan sát được → phương pháp và lý do chọn → kiểm chứng/đối chiếu → kết quả và giới hạn → nguồn code/artifact/tài liệu học thuật**. Phân biệt ví dụ giả lập với kết quả đã chạy thật. Code cho biết chương trình làm gì; tài liệu tham khảo giúp hiểu cơ sở của kỹ thuật đó.

Các trạng thái trong hướng dẫn:

- **Đã triển khai/quan sát:** có code hoặc artifact được dẫn; phạm vi xác minh được ghi riêng.
- **Giả định/policy:** quyết định kỹ thuật đang chấp nhận, không phải sự thật đã chứng minh.
- **Cần kiểm tra/đề xuất:** chưa được xem là đã chạy hoặc đã đạt.
- **Kế hoạch ML/backtest:** phần tương lai, phải có đặc tả và kết quả riêng sau này.

Hướng dẫn này giải thích cách làm và lý do chọn từng kỹ thuật. Kết quả kiểm thử cụ thể được ghi trong báo cáo pilot theo từng phiên bản code.

### Một số từ thường gặp

- **Artifact:** file được lưu lại, như bảng dữ liệu, CSV kiểm tra hoặc hình kết quả.
- **Provenance/lineage:** nguồn gốc dữ liệu và các bước đã biến đổi dữ liệu đó.
- **Policy:** quy tắc xử lý mà dự án lựa chọn.
- **Schema:** các cột, kiểu dữ liệu và cấu trúc dự kiến của bảng.
- **Bar:** một nến giá của một mã trong một khoảng, ở đây thường là một phiên.
- **Finite:** giá trị hữu hạn, không phải NaN hay vô cực (`Inf`).
- **Gap:** khoảng thiếu phiên hoặc thiếu dữ liệu; cần phân biệt với ngày sàn nghỉ.
- **Lookback/window:** đoạn lịch sử được dùng để tính một feature.
- **Cutoff:** thời điểm cuối cùng được phép lấy thông tin cho dự đoán.
- **Horizon:** khoảng tương lai mà mình muốn dự đoán.
- **Seed/reset:** khởi tạo hoặc xóa trạng thái tích lũy của chỉ báo.
- **Purge:** loại mẫu có khoảng nhãn vượt qua ranh giới tập dữ liệu.
- **Expected/actual:** kết quả tham chiếu và kết quả code tính được.
- **Tolerance:** mức sai số số học chấp nhận khi đối chiếu.
- **Regression test:** kiểm thử giữ lại để ngăn một lỗi đã sửa xuất hiện lại.
- **P&L:** lãi/lỗ của vị thế hoặc danh mục.

## Trước khi bắt đầu: bốn mức kết luận

1. **Script chạy xong:** chương trình không lỗi ở lần chạy đó.
2. **Số liệu trông hợp lý:** chưa thấy bất thường theo kiểm tra đã chọn.
3. **Công thức nhất quán:** input, phép tính, output khớp quan hệ đã quy định.
4. **Đã xác minh thực tế:** có nguồn độc lập truy được xác nhận đúng sự kiện, thời điểm, chứng khoán và số liệu cần chứng minh.

Không tự suy mức 4 từ mức 1–3. Báo cáo test pass phải ghi phạm vi, không có nghĩa toàn bộ lịch sử giá đã được xác minh.

## Chặng 1 — Bài toán là gì, vì sao xây lại?

**Khái niệm.** Return là tỷ lệ thay đổi giá hoặc giá trị nắm giữ trong một khoảng. Cross-sectional ranking so nhiều chứng khoán trong cùng một ngày. Time series theo một chứng khoán qua nhiều ngày; dự án có cả hai chiều.

**Vấn đề.** Muốn học trên quá khứ phải dùng đúng đối tượng và thông tin có thể biết lúc đó. Nếu lấy danh sách hiện tại để nghiên cứu năm 2005, có thể mất các công ty đã phá sản: survivorship bias. Nếu dùng danh sách hoặc kết quả được biết sau ngày dự đoán cho ngày trước đó: look-ahead bias. Hai loại bias có liên quan nhưng không đồng nhất.

**Input → output của ML.** Mỗi mẫu `(SID i, ngày T)` có 16 features quá khứ; output là điểm dự đoán để xếp hạng return phiên sau. Một ngày có hàng trăm mẫu chứng khoán, không phải một mẫu mỗi năm. 24 năm dữ liệu không có nghĩa chỉ có 24 giá trị học.

**Ví dụ giả lập.** Tại T, model dự đoán A tốt hơn B. Sang phiên sau, A giảm 1%, B giảm 5%: A có thứ hạng cao hơn dù cả hai đều lỗ. Xếp hạng đúng chưa đồng nghĩa danh mục thực thi có lợi nhuận sau chi phí.

**Quyết định.** Xây lại nền dữ liệu và kiểm tra thời gian trước khi thử model. Prediction score là output model; alpha signal là tín hiệu dùng thể hiện kỳ vọng; portfolio là vị thế sau quy tắc/ràng buộc. Trung hòa rủi ro là lựa chọn thiết kế, không phải điều kiện để mọi signal được gọi là alpha.

### Từ vấn đề đến phương pháp: hai bias khác nhau

**Survivorship bias — chọn mẫu bằng kết quả tương lai.** Ví dụ giả lập: năm 2005 có A/B/C, sau này C phá sản. Nếu chỉ lấy các mã còn sống hôm nay thì C biến mất khỏi quá khứ. Không chỉ mất một mã: phân phối mẫu và những kết quả xấu mà model cần được đánh giá cũng thay đổi. Kết quả có thể bị đánh giá quá lạc quan, nhưng không được tự khẳng định mức ảnh hưởng khi chưa đo.

- **Dấu hiệu/rủi ro của dự án:** nghiên cứu nhiều năm trong một rổ có thay đổi thành viên. Đây là lý do thiết kế universe lịch sử; chưa có phép đo riêng xác định bias của toàn bộ phiên bản cũ là bao nhiêu.
- **Kỹ thuật đã chọn:** lưu danh sách theo năm, giữ lịch sử các mã rời rổ và dùng membership theo thời gian. Không chọn lịch sử bằng việc cổ phiếu còn tồn tại ở cuối kho.
- **Kiểm chứng cần đọc:** counts theo năm, các trường hợp rời rổ, source inventory và coverage. Kho có LEH/ENE không tự chứng minh đã giữ đầy đủ mọi mã chết hoặc delisting return.
- **Quyết định/giới hạn:** giảm một nguồn selection bias, không tuyên bố loại hết survivorship bias khi còn thiếu giá hoặc unresolved mapping.

**Look-ahead bias — đưa thông tin chưa biết vào quyết định T.** Ví dụ giả lập: một danh sách công bố tháng 9 bị dùng ngược cho giao dịch tháng 7. Các tên có thể đúng trong file, nhưng sai thời điểm được biết. Khác với ví dụ survivorship, vấn đề không chỉ là bỏ người thua cuộc mà là sử dụng thông tin muộn.

- **Kỹ thuật đã chọn:** phân biệt ngày snapshot, thời điểm biết thông tin, khoảng membership áp dụng, cutoff X và horizon y. Có target tương lai trong dữ liệu huấn luyện là hợp lệ; dùng target/mask tương lai để tạo X thì không.
- **Bằng chứng và giới hạn:** mốc tháng 7 là quy ước đang chấp nhận, không tự chữa một snapshot thực sự muộn. Dấu ngày tháng 9 trong nguồn 2026 phải được đối chiếu, không được bảo chứng bởi tests masks pass.
- **Điều cần nhớ:** phân biệt bias, cách phòng ngừa và giới hạn còn lại; không kết luận “đã loại hoàn toàn look-ahead” chỉ vì đã có PIT mask.

**Đọc tiếp:** [README dự án](../../README.md), [target/timing §1–3](../specifications/target_and_timing_v1.md).

**Tự kiểm tra:** Tại sao dự đoán chính xác thứ hạng vẫn có thể lỗ? Vì sao dữ liệu của một mã đã phá sản vẫn cần được giữ?

## Chặng 2 — Tìm universe lịch sử

**Khái niệm.** Universe là tập đối tượng được xét. Snapshot là danh sách tại một thời điểm; không phải toàn bộ lịch sử thêm/bớt trong năm. PIT (point-in-time) yêu cầu xem xét thông tin đúng thời điểm.

**Vấn đề.** Russell 1000 thay đổi thành viên. Cần giữ danh sách từng năm, không áp một danh sách cố định cho 27 năm.

**Input.** PDF/CSV/JSON/XML-XLS trong `data/raw/universe/raw_universe/`. File quỹ mô phỏng và danh sách chỉ số có thể khác nhau; cần ghi nguồn, không tự gọi mọi holdings là thành viên chỉ số chính thức.

**Xử lý.** Script 01 đọc từng định dạng, lấy ticker, lọc từ nhiễu, chuẩn hóa theo parser, xuất JSON và extraction report. Ví dụ nguồn CSV 2008 có `ADC TELECOMMUNICATIONS,ADCT`; cột Ticker cho ADCT. Dòng tiêu đề không phải chứng khoán.

**Output.** JSON tổng hợp dạng `{"2000": ["A", "AA", ...], ...}`; mỗi file JSON năm là một list. Artifact có 27 năm, 26.919 lượt ticker-năm và 2.884 chuỗi ticker duy nhất. JSON này không tự chứa lịch sử SID, mọi ngày hiệu lực thực tế hoặc bằng chứng nguồn đầy đủ.

**Kiểm tra.** Đếm theo năm; so JSON với nguồn; kiểm tra ticker đặc biệt/tiêu đề bị lấy nhầm; replay parser và so artifact. Số gần 1.000 là gợi ý, không chứng minh đúng đủ.

**Quyết định và giới hạn.** Áp quy ước 01/07/Y–30/06/Y+1, chấp nhận xấp xỉ thường niên. Không tái tạo đầy đủ biến động nội năm. [Source inventory](../reports/data_pipeline/universe_source_inventory.csv) ghi ngày ứng viên và chỗ cần đối chiếu, đặc biệt dấu ngày tháng 9 trong nguồn 2026. Không gán ngày thành lập quỹ thành ngày snapshot, không mặc định metadata creation date là ngày hiệu lực.

### Từ vấn đề đến phương pháp: parser tái lập và provenance

**Vấn đề:** cùng một tên cột hoặc vị trí token không ổn định qua PDF/CSV/JSON/XML. Regex lấy ticker đầu dòng có thể lấy nhầm tên công ty hoặc bỏ sót mã nhiều ký tự nếu áp mọi năm.

**Dấu hiệu:** file đầu vào của dự án có nhiều cấu trúc và code 01 có parser theo từng era/định dạng. Đây là quan sát từ code/nguồn; không phải thực nghiệm chứng minh mọi regex sai trước đây.

**Kỹ thuật:** chọn parser theo cấu trúc nguồn, lọc từ nhiễu, lưu output theo năm và extraction report. Đây là schema-aware parsing: dựa vào cấu trúc dự kiến, không coi mọi chữ in hoa là mã. Giữ file thô để có thể kiểm lại quyết định bóc tách.

**Ví dụ giả lập:** dòng `ABC ABC INDUSTRIES` phải cho một ticker ABC; dòng `RUSSELL INDEX MEMBERSHIP` phải không tạo ba ticker. Cả hai danh sách đều có thể cho tổng gần 1.000 nếu vừa thiếu mã vừa nhận nhầm tiêu đề, nên kiểm count một mình không đủ.

**Kiểm chứng:** chạy lại parser rồi so với JSON hiện có để kiểm tra tính tái lập; chọn mẫu đối chiếu dòng nguồn để kiểm tra nội dung; đối chiếu ngày/nguồn để kiểm tra thời điểm áp dụng. Đây là ba bài kiểm tra khác nhau. Extraction report hiện không chứng nhận 100% các tên đúng.

**Quyết định/giới hạn:** source inventory giữ tên file, loại, count, ngày ứng viên và ghi chú. Nó chưa phải hồ sơ Wayback URL/capture timestamp và ngày công bố đã xác minh đầy đủ. Thông tin thiếu phải để trạng thái chưa rõ, không điền ngày giả làm ngày xác nhận.

**Điều cần nhớ:** hiểu parser lấy ticker như thế nào, kiểm tra bằng cách nào và phân biệt ngày tài liệu với ngày áp dụng giả định.

**Đọc tiếp:** [Lineage §2](../reports/data_pipeline/data_lineage_report.md).

**Tự kiểm tra:** JSON 2000 và bảng membership từng ngày khác nhau ở đâu? Parser tái lập hoàn toàn đã đủ chứng minh universe đúng ngày chưa?

## Chặng 3 — Thu thập lịch sử thị trường và hiểu ZIP

**Khái niệm.** OHLCV là open/high/low/close/volume của phiên. Raw chưa điều chỉnh split/dividend. Batch là nhóm yêu cầu tải; audit là dữ liệu để kiểm tra quá trình tải, không phải nến.

**Vấn đề.** Không thể chỉ tải từ ngày cổ phiếu vào rổ nếu cần tính feature có lookback ngay ngày đầu gia nhập.

**Input → xử lý.** Lấy hợp các ticker lịch sử, chia 10 batches, yêu cầu lịch sử có sẵn 1998–2026 trên QC. Scan thử và kết quả export cuối là hai thời điểm khác nhau, số mã rỗng có thể khác.

**Output.** Mỗi ZIP hiện có 29 CSV theo năm và ba file audit status/identity/summary. Ví dụ `raw/year=1998/batch_01_of_10.csv`. Chín batch đầu yêu cầu 289 tickers/batch, batch cuối 283. Có 2.846 tickers xuất hiện ít nhất một bar trong kho raw; 38 không có bar toàn kho.

**Metadata là gì?** Thông tin mô tả dữ liệu: tên batch, ticker yêu cầu, SID phân giải, số dòng, phạm vi và chế độ giá. Nó giúp hiểu/kiểm tra giá nhưng không phải chính giá.

**Kiểm tra.** ZIP đủ file, năm/cột đúng, tổng row summary đối chiếu raw, status không bị bỏ qua, identity không tự đồng nhất ticker với công ty. Fallback truy vấn riêng chỉ tăng khả năng thu thập, không bảo đảm không thiếu bất cứ ngày nào.

**Quyết định.** Giữ lịch sử sàn thu thập được trong warehouse; khi nghiên cứu mới lọc universe đúng T. Không gọi mọi ngày trong kho là ngày thuộc Russell.

### Từ vấn đề đến phương pháp: tải theo batch và giữ audit

**Vấn đề:** truy vấn lớn có thể lỗi tài nguyên hoặc chỉ trả một phần; nếu chỉ kiểm tra có ZIP thì có thể coi một lần tải thiếu là hoàn thành. Đồng thời, chỉ tải trong kỳ membership sẽ làm mất lookback cần cho ngày đầu kỳ.

**Kỹ thuật đã có:** chia yêu cầu thành batch/sub-group; fallback theo symbol khi nhóm lỗi; lưu status, identity, summary cùng raw bars. Đây là kiểm soát thu thập và truy vết, không phải mô hình dự đoán.

**Kiểm chứng:** đối chiếu tickers yêu cầu, tickers có kết quả, số dòng và phạm vi theo batch. Metadata của ZIP cho biết đã yêu cầu gì; kho giá cho biết thực sự có gì. Scan sơ bộ chỉ mô tả một lần khảo sát, không có quyền thay số đếm export cuối.

**Ví dụ giả lập:** batch yêu cầu 100 mã, có 98 mã có bars. File ZIP hợp lệ không có nghĩa thành công 100/100. Hai mã còn lại phải có trạng thái/ngoại lệ; không biến thành hai mã có return 0.

**Quyết định/giới hạn:** tải lịch sử rộng rồi chọn membership tại output T. Danh sách hợp ticker dùng để thu thập không được coi là universe giao dịch cố định cho mọi năm. Khi vận hành thực tế, không có sẵn danh sách mã sẽ xuất hiện trong tương lai như trong kho hồi cứu; điều kiện chọn mã tại T phải chỉ dùng thông tin đã biết.

**Truy nguồn:** [export batches](../../scripts/01_pipeline/02_quantconnect_export_10_batches.py), [ingestion](../../scripts/01_pipeline/03_process_10_batches_to_parquet.py). Không chạy lại hai script chỉ để đọc tài liệu.

**Đọc tiếp:** [Lineage §3–4](../reports/data_pipeline/data_lineage_report.md), data dictionary mục 0.2.

**Tự kiểm tra:** Vì sao có giá năm 1999 nhưng membership năm đó False? Summary và identity khác vai trò thế nào?

## Chặng 4 — Merge, Parquet và kiểm tra chất lượng/coverage

**Khái niệm.** Parquet là định dạng lưu bảng theo cột. Merge/gộp không tự làm dữ liệu sạch. Null là giá trị thiếu trong dòng đã tồn tại; thiếu cả dòng là vấn đề khác.

**Input → output.** Script 03 đọc 10 ZIP, chuẩn hóa schema và gộp theo năm; xuất 29 Parquet, raw master 13.147.389 dòng và master status/identity. Dòng giá có date, ticker gốc, ticker QC, SID và OHLCV.

**Ví dụ giả lập.** Một mã phải có bar D1/D2/D3 nhưng chỉ tải D1/D3, hai dòng đều đủ 9 cột. Null check bằng 0 nhưng coverage chỉ 2/3. Khi tính daily return không được coi D3/D1 là return một phiên.

**Kiểm tra.** Cột/kiểu; ngày hợp lệ; giá hữu hạn và dương; high ≥ open/close/low; low ≤ open/close; volume không âm; duplicate keys; missing sessions; coverage từng mã/kỳ; zero-bar cases. Các kiểm tra có miền áp dụng khác nhau và có thể chưa kiểm đủ Inf hoặc từng field; đọc code/audit cụ thể.

**Coverage có nhiều mẫu số.** Có ít nhất một bar toàn kho, đủ bar trong kỳ, đủ bar trên universe đã chọn và đủ feature/label là các phép đo khác nhau. Luôn ghi numerator/denominator. Không dùng tỷ lệ cao trên tập đã loại unresolved để che phần thiếu so với nguồn.

**Quyết định.** Giữ audit và danh sách thiếu. Không fill return 0 để tăng coverage. Script 03 bỏ trùng `(date,original_ticker)`; assertion chất lượng cho mọi dòng bất đồng chưa được suy ra chỉ từ việc dedup chạy xong.

### Từ vấn đề đến phương pháp: kiểm schema, lịch ngày và mẫu số

**Vấn đề:** một bảng có thể đúng schema nhưng sai nội dung hoặc thiếu quan sát. Mỗi phép kiểm chỉ chặn một loại lỗi.

- **Schema/type check:** phát hiện thiếu cột hoặc sai kiểu. Nó không phát hiện một mức giá sai nhưng vẫn là số dương.
- **OHLC constraints:** phát hiện high thấp hơn close hoặc low cao hơn open. Một bad tick tự nhất quán cả bốn giá vẫn có thể qua kiểm tra.
- **Finite check:** loại NaN/Inf theo từng input. `notna()` chỉ loại missing, không loại Inf; tính được một con số không chứng minh cửa sổ hợp lệ.
- **Calendar reindex:** tạo lưới phiên chung để ngày vắng bar hiện thành ô thiếu; rolling theo số hàng khi đã bỏ ngày thiếu có thể bắc cầu qua một gap.
- **Coverage:** đối chiếu các ô kỳ vọng với ô thật, ghi mẫu số theo snapshot/membership/feature/label riêng.

**Ví dụ giả lập:** 100 thành viên × 10 phiên là 1.000 ô kỳ vọng. Sau mapping chỉ chọn 90 mã, 900 ô; có 891 ô đủ dữ liệu thì coverage trên tập chọn là 99%, nhưng trên nguồn ban đầu chỉ 89,1%. Cả hai phép chia đúng; chỉ báo một cái mà bỏ mẫu số dễ gây kết luận sai.

**Bằng chứng:** raw audit có null/OHLC/duplicate checks; matrices giúp biểu diễn missing sessions; các báo cáo coverage dùng nhiều mẫu số. Ví dụ kiểm thử: cửa sổ giá `[100, Inf, 110]` phải bị loại theo quy tắc giá hữu hạn. Nếu chỉ kiểm tra hai đầu mút và đếm `notna()`, code có thể trả 10% dù bên trong có giá vô cực. Vì thế cần kiểm tra finite riêng cho toàn cửa sổ.

**Quyết định/giới hạn:** missing do chưa IPO, delisting, halt, lỗi tải hoặc mapping là các nguyên nhân khác nhau. Một danh mục nguyên nhân chung chưa phải phân loại từng ô. Không fill toàn bộ bằng 0 hoặc forward-fill qua gap chưa hiểu, vì đó là thêm giả định kinh tế.

**Đọc tiếp:** [Audit raw](../Data%20report/market_data_audit/market_data_audit_report.md), [lineage §4](../reports/data_pipeline/data_lineage_report.md).

**Tự kiểm tra:** Null=0 có bảo đảm đủ dữ liệu không? Coverage 99,66% đang so với tập nào?

## Chặng 5 — Identity và khử trùng

**Khái niệm.** Ticker là tên; SID là định danh nguồn; canonical SID là khóa kho sau quy tắc mapping. Mapping là bảng đối chiếu khóa, có thể kèm khoảng ngày và mức bằng chứng.

**Vấn đề.** Ticker đổi tên hoặc được tái sử dụng; nhiều yêu cầu ticker có thể trả về cùng lịch sử. Số tên ticker không quyết định số chứng khoán/SID.

**Input → xử lý → output.** Script 04 đọc raw master, kiểm tra trùng, gán canonical, giữ một dòng `(date,canonical_sid)`. Bảng mapping 4.737 dòng về 3.711 SID; canonical warehouse 12.247.081 dòng, giảm 900.308 so raw.

**Ví dụ giả lập.** OLD/NEW cùng SID S1 và bars giống nhau có thể là hai alias của một lịch sử; giữ một dòng để không nhân đôi. ABC/S1 ở thời kỳ cũ và ABC/S2 ở thời kỳ mới không tự được nối. ABC 2T cách SID chính bốn ngày chỉ là điều kiện heuristic, không phải xác nhận cùng chứng khoán.

**Kiểm tra và giới hạn.** Close trùng không đủ chứng minh toàn OHLCV bit-for-bit; cần so các field và mapping theo khoảng. Code 04 có assertion close và thống kê một số field, không phải tất cả đều đã được assert. 752 lượt nối 2T dùng cùng ticker và ≤10 ngày lịch; chưa có bước tự xác minh SEC/CUSIP. Không suy đoán cấu trúc hash hoặc nguyên nhân 2T khi chưa có nguồn.

**Quyết định.** Giữ bảng nguồn và evidence, loại ambiguous/unresolved khỏi mask theo policy; mapping không rõ không âm thầm gán một SID bất kỳ. Một công ty nhiều lớp cổ phiếu có thể có nhiều SID.

### Từ vấn đề đến phương pháp: entity resolution và dedup có điều kiện

**Vấn đề:** khác tên chưa chắc khác chứng khoán; giống tên chưa chắc cùng chứng khoán. Nếu dùng ticker làm trục, có thể nhân đôi cùng lịch sử hoặc nối nhầm hai tài sản.

**Kỹ thuật:** entity resolution qua bảng `(original_ticker,raw_sid)→canonical_sid`, giữ min/max thời gian, resolution_type và ledger. Membership dùng SID đúng phân đoạn thay vì gộp mọi SID thành một tên.

**Ví dụ thực trong mapping cục bộ:** ticker XOM ánh xạ tới `XON R735QTJ8XC9X`. Không được ghép chuỗi `ticker + hậu tố quen thuộc` để đoán canonical SID. Nếu tự tạo `XOM R735QTJ8XC9X` rồi bỏ qua tên không tìm thấy, mẫu yêu cầu 10 mã có thể chỉ còn 9. Phải tra mapping và đối chiếu danh sách thực nhận; không im lặng bỏ mã bắt buộc.

**Dedup là gì?** Giữ một bản đại diện khi nhiều dòng thật sự diễn tả cùng bar; không cộng volume của hai alias, vì sẽ nhân đôi hoạt động giao dịch. Nếu cùng khóa mà giá khác, giữ first/last không tự giải quyết đúng sai.

**Heuristic là gì?** Quy tắc kỹ thuật khi chưa có chứng cứ đủ mạnh. Cùng ticker và gap ≤10 ngày lịch là điều kiện đang dùng, không phải định luật rằng hai đoạn là một tài sản. Không trùng ngày chỉ chứng minh chúng không cùng có bar ở những ngày đó, chưa chứng minh continuity kinh tế.

**Kiểm chứng:** kiểm tra field conflicts trước/sau mapping, duplicate keys sau dedup, tra theo ngày và đối chiếu nguồn identity. Ngày hỏi không có interval phải trả rỗng, không fallback mọi SID lịch sử. Độ nhạy có thể so strict và resolved, nhưng chưa gọi phép so đó đã chạy nếu chưa có kết quả.

**Quyết định/giới hạn:** giữ evidence levels và ca loại trừ để người khác tái xét. Số dòng mapping, số SID và số ticker là ba đại lượng khác nhau; không dùng số lượng “đẹp” làm mục tiêu ép mapping.

**Truy nguồn:** [script 04](../../scripts/01_pipeline/04_audit_identity_and_build_canonical_mapping.py), [tra universe/SID](../../src/data/universe.py).

**Đọc tiếp:** [Identity/corporate actions §1–2](../reports/data_pipeline/step3_corporate_actions_report.md), data dictionary mục 4.4.

**Tự kiểm tra:** Tại sao 2.884 ticker có thể dẫn đến 3.711 SID? Khi nào xóa một dòng trùng là an toàn, khi nào cần điều tra?

## Chặng 6 — Split, dividend, spin-off và corrections

**Khái niệm.** Corporate actions là các hành động doanh nghiệp làm thay đổi cổ phần/phân phối tài sản. Split thay đơn vị cổ phiếu; dividend phân phối tiền; spin-off có thể phân phối cổ phiếu tài sản khác.

**Ví dụ giả lập split.** Một cổ phiếu giá 100 đổi thành hai cổ phiếu giá 50. Không có biến động thị trường thì tổng giá trị vẫn 100, không lỗ 50%. Điều chỉnh đưa hai mức giá về cùng đơn vị. Giá sau split 51 vẫn có thể tương ứng return +2%.

**Ví dụ giả lập dividend.** Giá 100 →98 và phân phối 2: price return −2%, phép đo gồm phân phối bằng 0%. Giá thực có thể khác 98 vì thị trường biến động. Ex-date và ngày trả tiền không nhất thiết giống nhau.

**Input → output.** Canonical bars + splits/dividends + corrections CSV → script 06 → adjusted OHLCV, factor, returns và quality flags. S là hệ số nhân giá trước split: 2-for-1 dùng 0,5, reverse 1-for-10 dùng 10. Không lấy nghịch đảo S lần nữa.

**Vì sao số sự kiện giảm?** Raw split export 4.788 bản ghi; điều kiện code `reference_price>0` giữ 2.391, thêm 5 overrides thành 2.396. Đây là thao tác thực của code; muốn khẳng định mọi loại event đều phân loại đúng cần metadata nguồn. Event không khớp bar đúng ngày vẫn có thể ảnh hưởng factor lịch sử.

**Corrections khác nhau.** Sửa event factor; cách ly khoảng nghi dữ liệu lỗi; cách ly spin-off chưa tái tạo lợi ích cổ đông. Không gộp chúng thành “sửa toàn bộ giá cho đúng”. Giá/return raw vẫn cần để tra.

**Kiểm tra.** Factor ratio trước/sau, return ngày split, đẳng thức dividend, price×volume, ngày sự kiện và mapping SID. Khớp đại số khác với xác nhận nguồn. Không fill NaN thành return 0 hoặc nối cửa sổ qua gián đoạn chưa xử lý.

### Từ vấn đề đến phương pháp: đồng nhất đơn vị và phân phối tài sản

**Split adjustment là thiết kế cần có trước EDA.** Raw prices qua split khác đơn vị cổ phần. Một chuỗi nhìn như sụp 50% có thể chỉ là 2-for-1; cần events và factor để so cùng đơn vị. Không phải chờ thấy return lạ mới biết phải xét corporate actions.

**EDA có vai trò phát hiện xử lý còn thiếu.** Trong trường hợp CHK đã ghi nhận, return raw cực lớn dẫn tới kiểm tra giá trước/sau và reverse split. Sửa event upstream làm công thức adjusted return nhất quán; sau đó mới kiểm lại phân phối. Không viết “kurtosis giảm nên factor chắc đúng”: tỷ lệ/ngày sự kiện phải có bằng chứng riêng.

**Vì sao tính CF trên lịch sự kiện?** Nếu chỉ nhân factor sau khi join được đúng bar ex-date, sự kiện vào ngày không có bar có thể bị bỏ. Script 06 lập suffix product theo event dates và dùng searchsorted để tìm các sự kiện sau từng ngày giá. Cần biết `side='right'` để sự kiện tại t không điều chỉnh chính mức giá đã ở đơn vị sau split tại t. Input event sai thì thuật toán đúng vẫn cho output sai.

**Dividend là luồng giá trị thêm, không chỉ một cú sụt cần xóa.** Price return và total return trả lời hai câu hỏi khác nhau. Thêm dividend đúng đơn vị giúp đối chiếu giá trị được phân phối, nhưng chưa mô phỏng ngày tiền được trả hoặc được tái đầu tư. Cổ tức không phải giải thích tự động cho mọi return âm.

**Spin-off cần nhiều tài sản.** Nếu cổ đông giữ một cổ phiếu mẹ và nhận cổ phiếu con, chỉ nhìn giá mẹ chưa đủ đo tổng tài sản. Khi chưa có chuỗi tài sản nhận thêm, cách ly discontinuity là giới hạn dữ liệu được công bố, không phải đã tính đúng total wealth.

**Kiểm chứng:** raw→adjusted cùng đơn vị; factor ratio đúng ngày; đẳng thức return/dividend; price×volume nhất quán. Test chỉ kiểm tra |return|<15% là sanity bound, chưa xác nhận split factor hoặc return thực: một biến động thật >15% có thể bị gắn sai, một factor sai vẫn có thể tạo return nhỏ.

**Quyết định/giới hạn:** phân biệt bổ sung factor với cách ly quality; ghi action trong corrections rồi tái tạo downstream cần thiết. Giá back-adjusted hồi cứu và giá có thể biết tại T không mặc nhiên giống nhau; phải xem từng công thức feature, không kết luận mọi adjusted feature có hoặc không có leakage chỉ từ tên cột.

**Truy nguồn:** [script 06](../../scripts/01_pipeline/06_process_corporate_actions_and_adjusted_prices.py), [corrections ledger](../Data%20report/market_data_audit/tables/market_data_corrections_and_exceptions.csv).

**Đọc tiếp:** [Corporate actions §3–7](../reports/data_pipeline/step3_corporate_actions_report.md).

**Tự kiểm tra:** Tại sao return ngày split không bắt buộc bằng 0? Cổ phiếu mẹ giảm 80% sau spin-off có chắc cổ đông mất 80% không?

## Chặng 7 — Matrices, masks, warm-up và nhãn

**Khái niệm.** Pivot đổi bảng dài sang ngày × SID. Mask là bảng True/False cùng tọa độ để lựa chọn ô. Warm-up là lịch sử khởi tạo feature, không phải train model.

**Input → output.** Adjusted warehouse + universe/mapping → matrices 7.252×3.711, segment mapping, masks và next-return targets. Có 3.711 cột không có nghĩa mọi mã cùng nằm trong rổ mỗi ngày.

**Ví dụ giả lập.** Mã gia nhập ở D4, có giá sạch từ D1. Return 2 phiên tại D4 cần D2/D3/D4; được dùng hai phiên trước membership. Lọc input bằng membership sớm sẽ xóa warm-up và gây NaN sai.

**Các vai trò riêng.** Bar quality làm sạch lịch sử độc lập membership. Từng feature kiểm tra đủ cửa sổ/field. Membership lọc output T. Valid data là điều kiện dữ liệu có sẵn, chưa chứng minh khớp lệnh. Valid label dùng kết quả T+1, chỉ lọc mẫu có đáp án khi train/evaluate, không lọc input hoặc danh sách dự đoán tại T.

**Kiểm tra.** Tọa độ khớp; không duplicate `(date,SID)`; return 20 phiên cần 21 giá; không shift qua ngày thiếu; target tại T lấy đúng kết quả phiên sau. Ranh giới 29/12/2023 purge nhãn sang OOS, vẫn giữ X/lịch sử hợp lệ. Mỗi fold cần kiểm tra ranh giới riêng.

**Giới hạn.** Membership là tập đã phân giải và chọn dùng, không tự đại diện toàn bộ nguồn ban đầu. Feature quality cần finite/high-low/volume theo công thức; mask close không kiểm hết. RSI có trạng thái, không chỉ rolling W.

### Từ vấn đề đến phương pháp: tọa độ, input hygiene và ranh giới nhãn

**Vấn đề tọa độ:** cộng hai arrays cùng shape nhưng thứ tự SID khác nhau có thể trộn A với B mà không gây lỗi kích thước. Vì thế cần so cả date index, SID columns và thứ tự, không chỉ `(T,N)`.

**Kỹ thuật:** dùng lưới chung, pivot/reindex, kiểm alignment. Đây là tính nhất quán tọa độ, không phải chứng minh dữ liệu nhân quả. Một ma trận giá tương lai shift sai vẫn có thể cùng shape và index.

**Vấn đề warm-up:** membership là điều kiện được xét ở T, không phải quyền được sử dụng mọi quan sát lịch sử. Lọc cả lịch sử bằng membership trước rolling tạo cold-start giả cho mã đã giao dịch đủ lâu.

**Kỹ thuật đã sửa:** làm sạch input bằng bar quality độc lập membership, kiểm window theo feature, chỉ lọc membership sau tính. Hai test cần phân biệt: lịch sử trước entry sạch phải được giữ; lịch sử đó có bar lỗi phải làm feature entry NaN. Giữ warm-up không có nghĩa bỏ kiểm chất lượng trước entry.

**Vấn đề label mask:** muốn biết y hợp lệ phải nhìn T+1. Nếu chỉ chọn danh sách dự đoán tại T bằng valid_label, đã dùng việc ngày mai có dữ liệu/giao dịch được để chọn hôm nay. Trong training, lọc mẫu có đáp án là cần thiết, nhưng phải báo sample attrition và giới hạn của delisting/missing labels.

**Vấn đề ranh giới:** X tại ngày cuối train có thể chỉ dùng quá khứ, nhưng y của nó đi vào ngày validation. Cần xét interval của y khi chia fold. Purge hàng 29/12/2023 chỉ xử lý ranh giới Development/OOS của target một phiên, không thay thế toàn bộ thiết kế validation.

**Kiểm chứng:** perturb thông tin sau cutoff để xem X cũ có đổi hay không là một kiểm tra cần thiết cho causality; hierarchy và shift checks bổ sung nhưng không thay thế nó. Không gọi mọi kiểm tra được đề xuất ở đây là đã có regression test; đối chiếu code/tests thực.

**Quyết định/giới hạn:** masks là các hợp đồng riêng. `valid_data` có 20 bars tích lũy không đủ cho mọi window; finite/high-low/volume và trạng thái RSI vẫn kiểm tra theo feature. Membership strict/resolved phải được ghi rõ khi so coverage.

**Truy nguồn:** [matrix builder](../../scripts/01_pipeline/07_build_2d_matrices_and_masks.py), [loader](../../src/data/matrix_loader.py), [quality utilities](../../src/quality/quality_window.py).

**Đọc tiếp:** [Matrices và ví dụ từng ô](../reports/data_pipeline/step4_matrices_masks_report.md), [sửa thư viện](../reports/library/library_edge_cases_and_fixes_report.md).

**Tự kiểm tra:** Vì sao y thiếu ở T không chứng minh X tại T sai? 20 bars tích lũy có bảo đảm volatility 20 phiên tính được không?

## Chặng 8 — EDA, ngoại lệ và bằng chứng

**Khái niệm.** Mean/median/std mô tả trung tâm/độ trải; skew mô tả bất đối xứng; kurtosis nhạy với tails. Stock-day là một mã ở một ngày; không phải các quan sát đều độc lập.

**Input → xử lý → output.** Daily returns trong Development, lọc theo valid_data và finite → phân phối, phân vị, dispersion, churn, liquidity deciles và hình. EDA chỉ gợi ý nơi cần điều tra.

**Ví dụ CHK.** Hai raw close đã ghi 0,1313 và 16,375 cho raw return khoảng +12.371%. Chia đúng đơn vị với factor 200 cho khoảng −37,64%. Ví dụ chứng minh cách tính; xác minh hai giá và event gốc là bước riêng.

**Cách điều tra.** Kiểm tra raw/adjusted/factor/volume trước-sau, continuity và mapping, rồi đối chiếu nguồn độc lập. Phân biệt bằng chứng sự kiện với bằng chứng đúng mức giá. MFA +227,87% còn cần đối chiếu; không xác nhận chỉ vì câu chuyện khủng hoảng hợp lý.

**Đọc hình.** Histogram bị clip để nhìn vùng giữa không phải đã sửa tails trong kho. Q-Q cho thấy khác phân phối chuẩn. Dispersion cao không chứng minh model có lợi nhuận. Decile toàn Development chỉ là phân nhóm hồi cứu, không phải gate giao dịch PIT.

**Những diễn giải đã sửa.** `p01` trong code là 0,01%, không phải 0,1%; std gộp không phải volatility danh mục; kurtosis cao không cấm OLS/Ridge; rank không sửa giá lỗi, không loại beta hay mọi non-stationarity.

### Từ vấn đề đến phương pháp: vòng điều tra EDA

**Vấn đề:** kiểm schema/OHLC có thể qua hết nhưng return vẫn có điểm +12.000%. EDA cho thấy chỗ cần điều tra; chỉ nhìn histogram không biết đó là split, lỗi bar, ticker reuse hay biến động thật.

**Chuỗi suy luận hợp lệ:** quan sát → lập các giả thuyết cạnh tranh → đọc cửa sổ dữ liệu/metadata → tìm chứng cứ phân biệt → chọn action → kiểm lại tác động. Ví dụ giả lập: cùng return +200% có thể do reverse split thiếu, giá hôm trước in sai hoặc tin doanh nghiệp. Ba trường hợp cần action khác nhau.

**Case CHK của dự án:** quan sát bước nhảy raw, tra reverse split, tính lại theo factor 200, rồi đưa correction upstream. Thay đổi từ return cực lớn sang khoảng −37,64% giải thích tính nhất quán số học; chứng cứ event/giá quyết định tính đúng lịch sử. Không viết EDA đã tự xác minh giá.

**Case chưa rõ:** MFA +227,87% có số liệu trong kho và câu chuyện kinh tế từng được ghi, nhưng chưa có đủ bằng chứng truy được để xác nhận hai giá và nguyên nhân. Giữ hoặc loại là policy phải công bố; không dùng rank làm lý do bỏ qua xác minh.

**Kỹ thuật thống kê phục vụ điều tra:** quantiles chỉ vị trí đuôi; tail frequencies đo tần suất theo mẫu số stock-day; Q-Q cho khác biệt với chuẩn; dispersion cho độ phân hóa từng ngày; heatmap coverage có thể giúp thấy khoảng thiếu nhưng chưa coi hình đó đã tồn tại nếu chưa được tạo. Trực quan hóa là bằng chứng hỗ trợ, không thay thế số liệu và test.

**Sau xử lý kiểm gì?** Các đẳng thức sự kiện; mức giá/return trước-sau; số ô bị ảnh hưởng; NaN lan qua lookback; distributions ở đúng sample/mask. Kurtosis giảm có thể do sửa lỗi hoặc do xóa nhầm tail thật, nên không dùng giảm kurtosis làm tiêu chí tối ưu làm sạch.

**Giới hạn quan trọng:** OLS không yêu cầu target có phân phối biên chuẩn; chỉ so pooled moments không chọn được model. Rank bounded giảm ảnh hưởng độ lớn trong y nhưng một bar lỗi vẫn có thể đổi thứ tự toàn cross-section. Liquidity deciles gộp toàn kỳ chỉ dùng khảo sát hồi cứu, chưa phải tín hiệu PIT.

**Điều cần nhớ:** theo một ca cụ thể từ dữ liệu trước/sau, cách xử lý đến phần còn chưa xác minh. Không gom mọi ngoại lệ thành kết luận “đã sạch 100%”.

**Truy nguồn:** [EDA script](../../scripts/01_pipeline/09_run_development_eda.py), [investigation script](../../scripts/01_pipeline/10_investigate_extreme_returns.py), [forensic ledger](../Data%20report/market_data_audit/tables/extreme_returns_forensic_investigation.csv).

**Đọc tiếp:** [EDA đã sửa diễn giải](../reports/data_pipeline/step6_eda_report.md). Khi xem forensic CSV, nhớ mô tả nguồn có chỗ chưa truy được và chưa xác minh lại toàn bộ.

**Tự kiểm tra:** Vì sao số liệu bớt cực đoan chưa chứng minh toàn kho đúng? Mean return gộp có phải lợi nhuận của một chiến lược không?

## Chặng 9 — Features, target, pilot rồi mới model

**Khái niệm.** Feature là thông tin đầu vào; signal là cách dùng thông tin để biểu diễn kỳ vọng; model học ánh xạ input→output từ train. Một return quá khứ có thể làm feature, không tự là bằng chứng alpha.

**Đã chốt.** 16 ứng viên gồm momentum, volatility, liquidity/volume và intraday/technical. Target chính là rank price return Close T→Close T+1, chưa gồm dividend; dự đoán sau đóng cửa T. Không giả định mua được tại chính Close T sau khi biết hết dữ liệu T.

**Ví dụ giả lập target.** Return phiên sau A=−2%, B=1%, C=3% cho rank chuẩn hóa 0/0,5/1. Ties dùng average; nhãn thiếu giữ NaN; model score như Ridge không bắt buộc trong [0,1].

**Pilot hỏi tính đúng chưa.** Đối chiếu công thức bằng dữ liệu tổng hợp và sample thực, kiểm tra warm-up/gap/split/quality/reset, expected/actual và tolerance cho đủ 16. Sau pilot mới full store và đánh giá coverage/phân phối/correlation/IC trên Development theo thiết kế đã định.

**Train/evaluate hỏi hữu ích không.** Train/validation theo thời gian; scaler/imputer/feature selection chỉ fit train từng fold. Dùng validation để chọn hyperparameters, không lặp chọn bằng OOS. OOS giữ cho đánh giá cuối, và backtest cần execution/cost riêng. Regularization thuộc mô hình, khác làm mượt RSI hoặc công thức volatility.

### Từ vấn đề đến phương pháp: pilot, validation và kiểm soát thử nhiều lần

**Vấn đề 1 — đúng tên nhưng khác công thức.** Momentum có thể dùng price return hoặc total return; volatility có thể daily/annualized; RSI có thể rolling mean hoặc Wilder; Bollinger std có ddof khác nhau. Code chạy được không có nghĩa đang đo cùng khái niệm.

**Kỹ thuật:** đặc tả tường minh loại input, đơn vị, cửa sổ, số giá cần, initialization, NaN và output mask. Những lựa chọn này là hợp đồng v1, chưa phải tham số tốt nhất đã được tối ưu. Không tự biến công thức để khớp một benchmark khác quy ước.

**Vấn đề 2 — tests đúng nhưng thiếu tình huống.** Hai ca cần chủ động thử: Inf giữa cửa sổ giá; raw price và raw volume cùng âm làm tích DV dương. Một bộ tests chỉ chứa dữ liệu hợp lệ có thể pass mà vẫn bỏ sót hai lỗi này. Cần kiểm thử cả trường hợp sai/biên, không chỉ ví dụ dễ tính.

**Kỹ thuật:** synthetic checks có expected tính độc lập; empirical checks trên mẫu thật; regression tests cho lỗi đã tìm; fail-fast khi thiếu SID bắt buộc hoặc có case FAILED. Với RSI, chuỗi toàn tăng chỉ kiểm tra trường hợp biên 100, chưa xác minh tỷ lệ làm mượt trên chuỗi có cả gains/losses.

**Giới hạn pilot:** mẫu thực và synthetic nhỏ không xác minh mọi dòng toàn kho. Coverage cao không phải tiêu chí feature có alpha. Phải ghi số SID thực tế, policy membership, run/commit, input và tolerance. Báo cáo pilot là nơi cập nhật kết quả, phần này chỉ giải thích lý do kiểm tra.

**Vấn đề 3 — chọn model bằng tương lai.** Nếu fit scaler trên cả train+validation, trung bình/độ lệch đã chứa thông tin validation. Nếu thử nhiều mô hình bằng OOS rồi chọn tốt nhất, OOS đã tham gia tuning dù không dùng để tính gradient.

**Phương pháp dự kiến:** chia train/validation theo thời gian; fit preprocessing/feature selection trên train mỗi fold; validation để chọn model/hyperparameters; cuối cùng đánh giá OOS theo quy trình được chốt. Walk-forward, regularization và execution còn cần đặc tả chi tiết trước khi chạy, chưa phải kết quả đã có.

**Regularization để làm gì?** Ví dụ Ridge phạt độ lớn trọng số bằng một hạng L2, giúp kiểm soát độ phức tạp theo thiết kế mô hình. Nó khác điều chỉnh split, làm mượt RSI hoặc clipping hình vẽ. Tham số phạt được chọn bằng validation, không chọn từ test cuối. Correlation cao giữa features gợi ý trùng thông tin, chưa đủ để tự loại trước khi thử quy trình đánh giá.

**Đánh giá cần nhiều góc:** lỗi dự đoán/rank IC theo ngày, độ ổn định theo thời gian, top-minus-bottom và cuối cùng P&L sau lịch thực thi/chi phí. Một metric tốt không chứng minh mọi metric khác tốt; rank regression không tự tối ưu trực tiếp P&L.

**Điều cần nhớ:** tách implementation validation (tính đúng), predictive evaluation (có thông tin dự báo) và trading evaluation (thực thi có ích). Phân biệt phần đã chạy với phần còn là kế hoạch; pilot pass chưa có nghĩa cả bài đã hoàn tất.

**Output và trạng thái.** [Features spec](../specifications/features_v1.md) và [target spec](../specifications/target_and_timing_v1.md) là hợp đồng; [quy ước pilot](../reports/feature_pilot/README.md) hướng dẫn lưu bằng chứng. Báo cáo kết quả `docs/reports/feature_pilot_report.md` đang được rà soát riêng, chưa gộp vào commit tài liệu này; khi công bố kết quả cần ghi run/commit của từng lần chạy.

**Tự kiểm tra:** Một feature đã tính đúng có chắc dự đoán tốt không? Vì sao chỉ số test cuối không được dùng để thử nhiều lựa chọn rồi chọn cái tốt nhất?

## Khi đọc xong

Thử tự kể lại một SID từ nguồn đến mẫu `(X[T],y[T])`, nêu rõ file đầu vào/đầu ra, điều kiện được chọn, lý do NaN và mức bằng chứng. Chỗ nào chưa kể được thì quay về báo cáo của chặng đó hoặc ghi câu hỏi cụ thể.

Các giới hạn còn mở không được biến thành kết luận đã làm xong: ngày snapshot và nguồn 2026; mapping heuristic; nguồn corrections/MFA; eligibility sau discontinuity của momentum bỏ tháng; các tham số train/validation/execution chưa chốt. Không cần học hết stochastic calculus hoặc mọi chiến lược quant mới hiểu được pipeline hiện tại.
