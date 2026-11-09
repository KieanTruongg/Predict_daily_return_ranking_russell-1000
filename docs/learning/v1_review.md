# Biên bản rà soát thực nghiệm v1

Phạm vi là phiên bản dữ liệu, dự báo và mô phỏng đã lưu trước khi mở v2. Đọc kèm [hướng dẫn v1](README.md) và [báo cáo thực nghiệm](../reports/baseline/comprehensive_course_project_report.md). Bản nháp có trang bìa được giữ để tham khảo cách trình bày. Giảng viên chưa công bố mẫu nộp hay bảng tiêu chí chấm điểm.

## Đã đối chiếu những gì?

- **Nguồn và chất lượng dữ liệu.** Đọc hợp đồng dữ liệu, báo cáo ánh xạ và quy tắc tạo mặt nạ. Tách danh sách thành viên dự kiến theo thời điểm khỏi tập thực tế có giá và đủ điều kiện. Các trường hợp nối mã theo quy tắc suy đoán, ngày nguồn bị thiếu và giá bị gián đoạn vẫn phải được ghi riêng. Mốc 01/07–30/06 là quy ước nghiên cứu. Xem [chương dữ liệu](v1_data.md).
- **Bảng học.** Kiểm tra phần mô tả cấu trúc nhúng trong tệp Parquet. Bảng Development có **5.514.324 dòng và 17 cột**, gồm hai cột khóa, 13 đặc trưng, lợi suất mục tiêu và thứ hạng mục tiêu. Hai bảng dùng cho lần chia Train/Validation ban đầu có **4.307.308** và **1.206.096** dòng, chênh **920** dòng so với bảng nguồn vì loại nhãn vượt ranh giới. Đối chiếu cấu hình năm lượt kiểm thực theo thời gian và cấu hình hai mô hình đã chốt. Xem [chương đặc trưng và mô hình](v1_features_models.md).
- **Dự báo ngoài mẫu.** Tính lại từ CSV theo cờ phạm vi chính. Có **624 phiên phát tín hiệu**, từ 02/01/2024 đến 29/06/2026. Ngày kết quả từ 03/01/2024 đến 30/06/2026. Mean Rank IC của Ridge, GBDT và tín hiệu đối chứng lần lượt là **0,023050**, **0,020403** và **−0,004393**. Kiểm định t hai phía so từng giá trị trung bình với 0. Sự phụ thuộc giữa các phiên là giới hạn cần lưu ý khi đọc p-value.
- **Mô phỏng danh mục.** Đối chiếu bảng sáu kịch bản với CSV tổng hợp, kiểm đếm từng sổ cái và xem lệnh MRTX bị hủy trong bản Ridge. Cả sáu sổ cái đều có 624 phiên và 0 vị thế chuyển tiếp trong bản chạy đã lưu. Bộ mô phỏng vẫn có quy tắc xử lý vị thế chuyển tiếp khi chưa bán được. Ridge đạt **+34,93%** ở 0 bps và **−61,19%** ở mức giả định 20 bps mỗi vòng mua–bán. Xem [chương đánh giá](v1_evaluation.md).

## Cách đọc mức xác minh

- **Đọc code và đặc tả** cho biết quy tắc đang được triển khai. Chẳng hạn, phép kiểm đủ lịch sử của một đặc trưng phụ thuộc vào cửa sổ thật sự của công thức.
- **Tính lại từ đầu ra đã lưu** giúp xác nhận báo cáo khớp với dữ liệu của lần chạy đó. Đợt này tính lại Mean Rank IC và thống kê t từ CSV, đối chiếu NAV và kiểm đếm sổ cái.
- **Kiểm thử bằng ví dụ tạo sẵn** kiểm tra logic trong tình huống kiểm soát được. **Kiểm thử tích hợp** kiểm tra các bước làm việc với tệp cục bộ. Hai phạm vi và lệnh chạy được mô tả trong [tài liệu kiểm thử](../testing.md).
- **Xác nhận nguồn thị trường** cần hồ sơ cho từng sự kiện hoặc bản công bố theo thời điểm. Rà soát lần này đọc các nguồn và báo cáo đối chiếu đã lưu. Việc xác minh độc lập toàn bộ lịch sử giá, thành viên và sự kiện nằm ngoài phạm vi lần rà soát này.

## Dọn tài liệu

Hai bản `data_exploration_report.md` và `data_exploration_report.html` trong `clear/old_docs/` được xóa sau khi đối chiếu mã băm và kiểm tra tham chiếu. Bản lưu cùng nội dung ở `clear/v1_reports/` vẫn còn. Giữ các tệp lịch sử có nội dung riêng, các bản nháp còn được dẫn nguồn, tài liệu đề bài, dữ liệu và đầu ra tái lập. Báo cáo của khóa trước là tài liệu tham khảo cách trình bày và ý tưởng.

## Kết quả chạy kiểm thử ngày 09/11/2026

Chạy `python -m pytest -q --strict-markers -m "not integration"` bằng Python 3.14, với thư mục tạm riêng trong workspace. Kết quả **79 đạt, 2 lỗi kiểm thử, 35 kiểm thử tích hợp nằm ngoài lượt chạy**. Lần đầu gặp lỗi tạo thư mục tạm mặc định. Dùng `--basetemp` giải quyết được lỗi môi trường đó.

Hai lỗi còn lại nằm trong [kiểm tra cấu trúc pipeline](../../tests/test_pipeline_integrity.py).

1. Kiểm thử cú pháp dừng ở điều kiện số lượng script. Repo có **37 script**, còn kiểm thử chỉ cho phép từ 13 đến 35. Kiểm tra riêng bằng `compile()` đọc được cả 37 script mà không thấy lỗi cú pháp.
2. Kiểm tra đường dẫn phát hiện script 31, 32 và 33 chứa đường dẫn cố định trên ổ D. Điều này ảnh hưởng khả năng chạy lại trên máy có cấu trúc thư mục khác. Việc đối chiếu số liệu đã lưu và tính di động của script là hai việc riêng.

### Kiểm tra lại sau khi sửa

Bài kiểm tra cú pháp hiện kiểm tra từng script tìm được, với điều kiện thư mục phải có script. Script 31 và 32 tìm thư mục dự án từ vị trí của chính tệp Python. Ba script 31–33 ghi kết quả vào cây thư mục của bản checkout đang chạy. Đã bỏ bước tự sao chép sang thư mục cá nhân ghi cứng.

Lượt chạy riêng nhóm kiểm tra pipeline và bộ mô phỏng cho kết quả **13 bài đạt, 2 bài tích hợp nằm ngoài lượt chạy, 37 kiểm tra cú pháp con đạt**. Lượt đầu chạy toàn bộ nhóm nhẹ gặp lỗi Windows khi nạp thư viện của scikit-learn. Chạy lại bằng Python 3.14 trực tiếp và import scikit-learn trước khi khởi động pytest cho kết quả **81 bài đạt, 35 bài tích hợp nằm ngoài lượt chạy, 37 kiểm tra cú pháp con đạt**. Kết quả v1 đã lưu được giữ nguyên.
