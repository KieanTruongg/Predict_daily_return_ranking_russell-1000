# Artifact hỗ trợ pilot features

Thư mục lưu bằng chứng pilot. Xem báo cáo chung để biết trạng thái từng đợt; không tạo CSV kết quả rỗng hoặc số liệu minh họa trông như lần chạy thật.

Khi thực hiện, lưu:

- `numerical_checks.csv`: run_id, feature, date, canonical_sid, case_id, expected, actual, absolute_error, tolerance, nan_reason, status, input_reference. Có thể bổ sung cột theo tình huống.
- `coverage_summary.csv`: run_id, feature, phạm vi ngày/mẫu, số ô xét, số hợp lệ, số thiếu và lý do; ghi rõ mẫu số.
- `figures/`: hình đối chiếu khi có ích, tên chứa feature hoặc case_id.

Run ID phải liên kết được tới commit, input/version và lệnh chạy trong báo cáo chung `docs/reports/feature_pilot_report.md`. Báo cáo và kết quả pilot đang được rà soát riêng, chưa gộp vào commit cập nhật docs. Giữ kết quả theo đợt một cách truy được, không ghi đè mất bằng chứng failed rồi chỉ giữ passed. Không đưa toàn bộ ma trận giá/features lớn vào thư mục tài liệu.
