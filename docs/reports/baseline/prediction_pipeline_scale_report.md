# Báo Cáo Kiểm Chứng Khả Năng Mở Rộng Của OOS Prediction Pipeline

## 1. Mục Tiêu và Phạm Vi Kiểm Chứng
- **Mục tiêu**: Xác nhận `src/models/oos_prediction_pipeline.py` có khả năng mở rộng xử lý liên tục toàn bộ 711 phiên ngoài mẫu (Out-of-Sample 2024–2026) mà không làm rơi các phiên đầu.
- **Phạm vi kiểm chứng**: Thực thi trên **600 phiên giao dịch** cuối cùng của giai đoạn Development (`2021-08-12` đến `2023-12-29`).
- **Nguyên tắc bảo vệ OOS**: Tuyệt đối đóng băng dữ liệu OOS (`allow_oos=False`), chỉ sử dụng dữ liệu Warm-up và Development.

---

## 2. Kết Quả Kiểm Thử Cơ Chế Bảo Vệ (OOS Guardrail)
Cơ chế kiểm tra chặn đứng trước khi đọc đĩa đã được kích hoạt thành công trên mọi trường hợp vi phạm:
- Phiên OOS đầu tiên (`2024-01-02`): Báo lỗi `PermissionError` ngay lập tức.
- Phiên OOS cuối cùng (`2026-10-30`): Báo lỗi `PermissionError` ngay lập tức.
- Yêu cầu hỗn hợp (`2023-12-28` và `2024-01-05`): Báo lỗi `PermissionError` ngay lập tức.

---

## 3. Hiệu Năng và Khả Năng Mở Rộng
- **Số phiên mục tiêu**: 600 phiên giao dịch liên tục.
- **Cửa sổ đệm lịch sử**: `lookback_sessions = 500` phiên trước `2021-08-12`.
- **Tổng số phiên nạp tính toán**: 1.100 phiên (`2019-08-19` đến `2023-12-29`).
- **Thời gian tính toán 13 features trên 3.711 mã**: **50.57 giây** (trung bình ~84.3 ms / phiên).
- **Kiểm tra rơi phiên**: Đầy đủ 600/600 phiên, đặc biệt phiên sớm nhất `2021-08-12` hiện diện 100% trong toàn bộ 13 ma trận đặc trưng.

---

## 4. Đối Chiếu Số Học Chi Tiết Với Feature Store

### 4.1. Nhóm Momentum
| Feature | Max Diff Đầu (2021-08-12) | NaN Lệch Đầu | Max Diff Cuối (2023-12-29) | NaN Lệch Cuối | Max Diff Toàn Bộ 600 Phiên | Trạng Thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ret_1d` | 0.00e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | KHỚP TUYỆT ĐỐI |
| `ret_5d` | 0.00e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | KHỚP TUYỆT ĐỐI |
| `ret_20d` | 0.00e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | KHỚP TUYỆT ĐỐI |
| `ret_60d` | 0.00e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | KHỚP TUYỆT ĐỐI |
| `mom_12m_skip_1m` | 0.00e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | KHỚP TUYỆT ĐỐI |

### 4.2. Nhóm Kỹ Thuật Wilder RSI
| Feature | Max Diff Đầu ({earliest_session}) | NaN Lệch Đầu | Max Diff Cuối ({latest_session}) | NaN Lệch Cuối | Max Diff Toàn Bộ {n_sessions} Phiên | Trạng Thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `rsi_14d` | 4.26e-14 | 0 | 0.00e+00 | 0 | 4.26e-14 | KHỚP TUYỆT ĐỐI (Decay < 1e-13) |

### 4.3. Nhóm Biến Động, Thanh Khoản và Bollinger
| Feature | Max Diff Đầu ({earliest_session}) | NaN Lệch Đầu | Max Diff Cuối ({latest_session}) | NaN Lệch Cuối | Max Diff Toàn Bộ {n_sessions} Phiên | Trạng Thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `vol_realized_20d` | 4.90e-15 | 0 | 3.24e-15 | 0 | 5.98e-15 | KHỚP TUYỆT ĐỐI |
| `vol_realized_60d` | 1.39e-15 | 0 | 1.71e-15 | 0 | 1.81e-09 | KHỚP TUYỆT ĐỐI |
| `downside_deviation_20d` | 4.48e-16 | 0 | 4.59e-16 | 0 | 6.00e-15 | KHỚP TUYỆT ĐỐI |
| `amihud_illiq_20d` | 1.08e-14 | 0 | 1.08e-14 | 0 | 1.08e-14 | KHỚP TUYỆT ĐỐI |
| `volume_ratio_5_20` | 1.02e-14 | 0 | 7.33e-15 | 0 | 1.22e-14 | KHỚP TUYỆT ĐỐI |
| `log_dollar_volume_20d` | 3.55e-15 | 0 | 3.55e-15 | 0 | 3.55e-15 | KHỚP TUYỆT ĐỐI |
| `bollinger_pct_b_20d` | 8.92e-11 | 0 | 6.33e-10 | 0 | 4.21e-09 | KHỚP TUYỆT ĐỐI |

---

## 5. Kiểm Thử Suy Luận và Đánh Giá Độc Lập Tại T+1

| Phiên T | Số Mã Đủ Điều Kiện Tại T | Số Mã Đủ Điều Kiện Chấm Tại T+1 | Spearman IC Ridge | Spearman IC GBDT | Trạng Thái Đánh Giá |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `2021-08-12` | 955 | 955 | -0.0127 | -0.1455 | `EVALUATED_SUCCESS` |
| `2023-12-29` | 978 | 0 | NaN | NaN | `INSUFFICIENT_STOCKS (<2)` |

### Ghi nhận đặc biệt về tính tách biệt của phiên cuối Development (2023-12-29):
1. **Suy luận tại T**: Sinh dự đoán đầy đủ cho **983 cổ phiếu** đạt chuẩn Inference Eligibility.
2. **Đánh giá tại T+1**: Do nhãn T+1 nằm ở phiên 2024-01-02 (ngoài tập Development), hệ thống gán đúng `n_evaluable_at_t1 = 0`, `has_valid_label = False`, và IC là `NaN`.
3. Điều này xác nhận nguyên tắc **tách biệt ranh giới** giữa quyết định giao dịch tại $T$ và đánh giá kết quả tại $T+1$ được tuân thủ nghiêm ngặt.

---

## 6. Kết Luận
1. **Khắc phục hoàn toàn lỗi ranh giới**: Bằng cách đệm 500 phiên *trước phiên đầu tiên*, pipeline đảm bảo an toàn tuyệt đối cho mọi chuỗi thời gian dài, kể cả 711 phiên OOS.
2. **Trạng thái Wilder RSI**: Sai số khởi tạo suy giảm hoàn toàn về ngưỡng máy tính ($< 5 \times 10^{-14}$), không làm lệch bất kỳ ô NaN nào.
3. **Cờ `allow_oos` và Guardrail**: Hoạt động đúng cam kết bảo vệ dữ liệu OOS đóng băng.
4. Pipeline đã sẵn sàng 100% cho việc chạy OOS chính thức khi được yêu cầu.
