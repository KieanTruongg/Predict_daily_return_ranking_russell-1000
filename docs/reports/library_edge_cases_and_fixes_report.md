# Báo Cáo Sửa Lỗi Thư Viện Cốt Lõi & Kiểm Chứng Biên (Library Edge Cases & Fixes Report)

> **Ngày thực hiện:** 2026-11-05  
> **Mục tiêu:** Khắc phục triệt để các lỗ hổng logic tinh vi trong tầng thư viện cốt lõi (`src/data/`, `src/features/`, `src/quality/`, `tests/`) được phát hiện qua kiểm toán độc lập trước khi triển khai Feature Engineering (Bước ⑦).

---

## 1. Tóm Tắt Các Điểm Sửa Đổi & Giải Pháp Triệt Để

| # | Hạng mục | Hiện trạng lỗi trước khi sửa | Giải pháp đã triển khai | File ảnh hưởng | Trạng thái |
|---|---|---|---|---|---|
| **1** | **Tra SID theo ngày** | `ticker_to_canonical_sids("AAPL", "1900-01-01")` âm thầm fallback trả về mọi SID thay vì rỗng. | Ép chặt ngữ nghĩa PIT: nếu truyền `as_of_date` mà không có dải ngày nào thỏa mãn $\to$ trả về `[]`. Thêm hỗ trợ `as_of_date` cho `canonical_sid_to_ticker`. | `src/data/universe.py` | ✅ RESOLVED |
| **2** | **Hỏi thành viên 2020 bị chặn OOS** | `get_active_constituents("2020-01-02")` ném `OOSFreezeViolationError` do nạp toàn bộ ma trận (kèm 2024–2026) trước khi lọc ngày. | Nhận diện ngày truy vấn: nếu thuộc Development window ($< 2024-01-02$), chỉ nạp slice development + warmup mà không kích hoạt kiểm tra OOS. Chỉ chặn khi truy vấn thực sự $\ge 2024-01-02$. | `src/data/universe.py` | ✅ RESOLVED |
| **3** | **Quality-Window cho Rolling Feature** | `FeatureBase` tính rolling trước rồi mới đắp mask ở ngày đầu ra $T$ $\to$ bar lỗi (bad tick/spinoff) ở giữa cửa sổ làm bẩn giá trị các ngày sau. | Tiền xử lý dữ liệu: gán `NaN` cho mọi ô có `bar_quality_mask == False` **trước khi** tính rolling. Bất kỳ cửa sổ nào đi qua bar lỗi sẽ tự động ra `NaN`. Minh bạch hóa tham số return (`total_return` vs `adjusted_close`). | `src/features/base.py` | ✅ RESOLVED |
| **4** | **Thống nhất Công thức Uniform Rank** | Dùng `pandas.DataFrame.rank(pct=True)` cho phân vị $[1/N, 1.0]$ thay vì chuẩn $[0.0, 1.0]$. | Áp dụng công thức chuẩn: $\frac{\text{rank} - 1}{N - 1} \in [0.0, 1.0]$. Với $N=1$ gán $0.5$. Non-members giữ nguyên `NaN`. Ties dùng `method='average'`. | `src/features/transforms.py`, `tests/test_matrix_loader.py` | ✅ RESOLVED |
| **5** | **Test Legacy chưa Archive** | 4 file test cũ (`test_metrics`, `test_neutralization`, `test_operators`, `test_pit_universe`) gây lỗi import vì gọi code phase 1 đã archive. | Chuyển toàn bộ vào `tests/archive_v1/`, cấu hình `pytest.ini` bỏ qua archive, viết lại `tests/run_tests.py` chuẩn. | `tests/archive_v1/`, `pytest.ini`, `tests/run_tests.py` | ✅ RESOLVED |
| **6** | **Chính xác hóa Phạm vi Causal & OOS Checks** | `assert_causal_alignment` chỉ kiểm tra bằng kích thước tọa độ ma trận mà chưa kiểm tra boundary purge. | Tách rõ `assert_coordinate_alignment`, bổ sung hàm `verify_boundary_purge` kiểm tra 100% nhãn tại $2023-12-29$ bị purge sạch sẽ. | `src/quality/quality_window.py` | ✅ RESOLVED |
| **7** | **Tách `bar_quality_mask` độc lập Membership** | Dùng `valid_data_mask` làm sạch input sẽ vô tình xóa lịch sử giao dịch trước ngày gia nhập Russell 1000 $\to$ mất warm-up của cổ phiếu mới vào rổ. | Tách hoàn toàn `bar_quality_mask` (chỉ phụ thuộc có giá sạch trên sàn, không phụ thuộc rổ chỉ số). Membership mask chỉ áp dụng tại ngày đầu ra $T$. Cách ly tuyệt đối `valid_label_mask`. | `src/features/base.py`, `src/data/matrix_loader.py` | ✅ RESOLVED |

---

## 2. Chi Tiết Kiến Trúc 3 Tầng Bảo Vệ Của Feature Engine

```
[ Dữ liệu giá/khối lượng/return thô ]
                 │
                 ▼
     ┌──────────────────────┐
     │  bar_quality_mask    │  <-- Độc lập 100% với Membership!
     │ (Sạch bad tick,      │      Giữ nguyên lịch sử giao dịch sàn trước khi vào rổ
     │  spinoff, missing)   │      để phục vụ warm-up (ví dụ 252d momentum/volatility).
     └──────────┬───────────┘
                 │
                 ▼ (Ép các ô lỗi thành NaN)
     ┌──────────────────────┐
     │ Feature Calculation  │  <-- Tính toán rolling (min_periods = W).
     │ (Rolling Window W)   │      Nếu có bất kỳ bar lỗi nào trong cửa sổ lookback,
     │                      │      kết quả rolling tự động ra NaN (Quality-Window Hygiene).
     └──────────┬───────────┘
                 │
                 ▼
     ┌──────────────────────┐
     │   membership_mask    │  <-- Áp dụng DUY NHẤT tại ngày đầu ra T.
     │  (Russell 1000 PIT)  │      Nếu ngày T là thành viên và đã có đủ warm-up sạch,
     │                      │      tính được feature ngay tại Ngày 1 gia nhập rổ!
     └──────────┬───────────┘
                 │
                 ▼
     [ Ma trận Feature sạch $X_t$ ]
```

### Cách ly tuyệt đối `valid_label_mask`:
- `valid_label_mask` chỉ được sử dụng cho nhãn target tương lai $y_{t+1}$ (kiểm tra ngày $T+1$ có giá và nhãn hay không).
- Tuyệt đối không đưa `valid_label_mask` vào làm sạch input feature $X_t$ nhằm triệt tiêu hoàn toàn nguy cơ look-ahead bias và leakage xuyên thời gian.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Full Test Suite)

Chạy trên môi trường Python 3.14:
```powershell
python -m pytest tests/
============================= 32 passed in 8.35s ==============================
```
- **`tests/test_library_fixes.py` (11 tests):**
  - `test_01`: Tra SID nghiêm ngặt theo ngày, không fallback (PASS).
  - `test_02`: Tra ngược ticker theo ngày (PASS).
  - `test_03`: Truy vấn thành viên 2020 không dính lỗi OOS (PASS).
  - `test_04`: Truy vấn ngày OOS thực sự (2025) bị chặn bởi OOSFreezeViolationError (PASS).
  - `test_05`: Rolling window đi qua bar lỗi tự động trả về NaN (PASS).
  - `test_06`: Minh bạch loại return, cấm suy đoán ngầm (PASS).
  - `test_07`: Công thức uniform rank $(rank-1)/(N-1)$ chính xác (PASS).
  - `test_08`: Kiểm tra boundary purge tại 2023-12-29 (PASS).
  - `test_09`: **Bảo toàn warm-up sạch trước ngày gia nhập: tính được feature ngay ngày đầu membership** (PASS).
  - `test_10`: **Bar lỗi trong thời gian warm-up pre-entry làm feature ngày gia nhập thành NaN** (PASS).
  - `test_11`: **Cách ly hoàn toàn valid_label_mask khỏi tầng tính feature** (PASS).
- **`tests/test_matrix_loader.py` (11 tests):** Tải ma trận, kiểm tra kích thước 7252x3711, cắt window development, transform rank (PASS).
- **`tests/test_pipeline_integrity.py` (10 tests):** Kiểm tra biên dịch cú pháp, không ổ đĩa cứng, schema và hợp đồng I/O (PASS).
