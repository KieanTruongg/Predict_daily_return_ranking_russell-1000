# Đặc tả target và thời điểm dự đoán v1

- Ngày chốt thiết kế: 2026-11-05.
- Trạng thái: đã thống nhất thiết kế với người thực hiện; chưa xác nhận toàn bộ code/artifact hiện tại tuân thủ đặc tả này.
- Phạm vi: mục tiêu nghiên cứu dự đoán thứ hạng; chưa đặc tả chiến lược khớp lệnh hay lợi nhuận danh mục.

## 1. Bài toán và đơn vị mẫu

Mỗi mẫu là một cặp `(date T, canonical_sid i)`. Mô hình nhận features có thể tính từ thông tin đến hết phiên T, rồi xuất điểm để xếp hạng lợi suất phiên tiếp theo giữa các chứng khoán đủ điều kiện tại T.

`T+1` chỉ phiên giao dịch tiếp theo trên lịch giao dịch của dự án, không phải ngày lịch tiếp theo hoặc dòng giá kế tiếp tùy ý của từng mã.

## 2. Thời điểm thông tin

- Chốt thông tin đầu vào: hết phiên T.
- Tính features và dự đoán: sau khi dữ liệu phiên T đã sẵn sàng.
- Không dùng giá, volume, sự kiện hoặc trạng thái nhãn chỉ biết tại T+1 để tính `X[i,T]` hoặc xác định eligibility dự đoán tại T.
- Mỗi feature phải quy định riêng loại dữ liệu và giới hạn sử dụng giá điều chỉnh theo lịch sử. Không mặc nhiên coi mọi mức giá back-adjusted là dữ liệu point-in-time đã xác minh.

## 3. Lợi suất mục tiêu chính

```text
next_price_return[i,T] = adj_close[i,T+1] / adj_close[i,T] - 1
```

`adj_close` ở đây là giá điều chỉnh chia tách theo hợp đồng dữ liệu hiện hành. Target chính là lợi suất giá close-to-close, chưa gồm cổ tức tiền mặt. Không thay ngầm bằng total return hoặc open-to-close. Total return có thể được đánh giá như một mục tiêu bổ sung sau khi chốt đặc tả riêng.

Nhãn được lưu tại hàng T dù giá trị kết quả sử dụng phiên T+1. Việc có dữ liệu tương lai trong nhãn huấn luyện là có chủ đích; không được đưa thông tin đó vào features.

## 4. Tập đối tượng và tính hợp lệ của nhãn

Tập đối tượng dự đoán được chọn bằng membership và các điều kiện đã biết tại T. Không yêu cầu membership tại T+1 chỉ để giữ nhãn của một đối tượng đã được chọn tại T.

Một lợi suất mục tiêu chỉ hợp lệ khi:

1. Chứng khoán thuộc universe tại T theo mapping được chấp nhận.
2. Hai giá đóng cửa tại T và T+1 hữu hạn, dương và đúng định danh theo thời gian.
3. T và T+1 là hai phiên liên tiếp trên lịch dự án; không nhảy qua phiên thiếu giá để tính return.
4. Khoảng tính return không bị ảnh hưởng bởi dữ liệu lỗi hoặc gián đoạn corporate action chưa xử lý theo quality policy.
5. Khoảng nhãn không vượt ranh giới tập đang huấn luyện/kiểm thực/kiểm thử.

Ngày không có phiên tiếp theo trong kho có nhãn `NaN`. Không thay nhãn thiếu bằng 0. Các trường hợp hủy niêm yết, thiếu giá cuối kỳ hoặc chưa tái tạo được lợi ích kinh tế phải được ghi nhận trong coverage và giới hạn; không coi nhãn còn lại là mẫu đầy đủ của mọi kết quả đầu tư.

Đối chiếu `valid_label_mask` hiện tại với hợp đồng này trước khi tái sử dụng. Mask nhãn không được lọc input features hoặc quyết định danh sách có thể dự đoán/giao dịch tại T.

## 5. Chuẩn hóa thành nhãn thứ hạng

Trên mỗi ngày T, lấy tập nhãn hợp lệ ở mục 4. Gọi số phần tử của tập đó là `N[T]`:

```text
rank = ascending_rank(next_price_return, method="average")
target_next_rank = (rank - 1) / (N[T] - 1)  khi N[T] > 1
target_next_rank = 0.5                    khi N[T] = 1
```

- Rank được tính riêng theo từng ngày, không gộp ngày hoặc tính riêng theo toàn bộ lịch sử một mã.
- Lợi suất cao hơn nhận nhãn cao hơn; đồng hạng dùng thứ hạng trung bình.
- N[T] đếm nhãn hợp lệ, không phải tổng cột SID hay số thành viên danh nghĩa.
- Ngoài tập nhãn hợp lệ: `NaN`. Không có nhãn hợp lệ: cả hàng `NaN`.
- Không trừ trung vị thị trường trước khi rank: trừ cùng một số trên cùng tập không đổi thứ tự.
- Đây là nhãn thứ hạng tương đối, không phải phép trung hòa beta hoặc ngành. Có ties thì không được diễn giải là phân phối đều chính xác.

Ví dụ: lợi suất A=-2%, B=1%, C=3% cho nhãn A=0, B=0.5, C=1. Điểm mô hình dự đoán không bắt buộc nằm trong [0,1]; vẫn xếp hạng được theo điểm.

## 6. Phân vùng và preprocessing

- Warm-up dùng lịch sử sạch để tính features; không cung cấp mẫu đánh giá trong giai đoạn warm-up.
- Development dùng để thiết kế và đánh giá ứng viên, chia train/validation theo thời gian và tuning.
- OOS 2024–2026 không dùng để lựa chọn features, mô hình hoặc hyperparameters. Kiểm tra kỹ thuật dữ liệu phải được phân biệt với nghiên cứu kết quả dự đoán.
- Mỗi fold phải loại các mẫu train có khoảng nhãn vượt sang validation/test. Ranh giới Development cuối 2023 cũng phải được xử lý tương tự.
- Scaler, imputer, lựa chọn biến và các tham số học từ dữ liệu chỉ fit trên train của fold tương ứng.

## 7. Phân biệt dự đoán và giao dịch

Features dùng đầy đủ phiên T và được tính sau đóng cửa. Không giả định có thể vào lệnh tại chính giá đóng cửa T sau khi đã biết đầy đủ dữ liệu phiên đó.

Target close-to-close bao gồm biến động qua đêm. Rank IC hoặc độ chính xác trên target này không phải lợi suất có thể giao dịch trực tiếp. Trước backtest cần đặc tả riêng thời điểm vào/ra lệnh, loại lệnh, dữ liệu giá khớp, chi phí, trượt giá và xử lý corporate actions. Nếu thay horizon để khớp lịch giao dịch, phải đặt target riêng và đánh giá lại.

## 8. Hợp đồng lưu trữ dự kiến

- Lợi suất nền: `data/processed/matrices/target_next_return.parquet`, chỉ tái sử dụng sau đối chiếu tính đúng với mục 3–4.
- Rank dự kiến: `data/processed/features/target_next_rank.parquet`; chưa sinh trong công việc viết đặc tả này.
- Cùng trục ngày và canonical SID với matrices nguồn; rank được lưu tại ngày dự đoán T.
- Lưu kèm coverage theo ngày: số đối tượng tại T, số nhãn hợp lệ và số bị loại theo lý do. Báo cáo riêng số mẫu thực sự dùng được sau khi kết hợp feature eligibility.
- Không tính lại target rank trên tập con thay đổi theo từng mô hình một cách ngầm định. Mọi so sánh phải ghi rõ tập đánh giá và chính sách thiếu features.

## 9. Các kiểm tra cần có trước khi sinh nhãn chính thức

Đây là tiêu chí cần kiểm tra, chưa phải báo cáo đã chạy đạt:

- Đối chiếu thủ công return của một số cặp giá và sự kiện split.
- Kiểm tra lệch một phiên: hàng T lấy return đúng T→T+1.
- Kiểm tra ties, N=0, N=1 và NaN; không xếp hạng chung nhiều ngày.
- Kiểm tra mã ra khỏi universe tại T+1 vẫn được xét nhãn nếu thuộc tại T và có kết quả hợp lệ.
- Kiểm tra phiên thiếu, quality flags, gián đoạn spin-off và phiên cuối kho.
- Kiểm tra purge ở ranh giới từng fold và Development/OOS.
- Đối chiếu coverage trước/sau lọc nhãn, nêu giới hạn của các kết quả không quan sát được.

## 10. Quan hệ với đặc tả features

16 features hiện là bộ ứng viên đang được đặc tả từng nhóm, chưa phải bộ đã chứng minh hiệu quả. Mỗi feature phải có công thức, nguồn input, lookback thực, chính sách NaN/quality, thời điểm sẵn có và ví dụ đối chiếu. Không thay danh sách hay loại return ngầm trong quá trình triển khai.

Nếu tài liệu kế hoạch cũ hoặc code hiện tại khác nội dung này, ghi rõ khác biệt và cập nhật có chủ đích; không xem văn bản này là bằng chứng code đã tuân thủ.
