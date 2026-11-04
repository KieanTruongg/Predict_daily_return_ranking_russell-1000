# Tests Archive (Legacy Phase 1 Tests)

Thư mục này lưu trữ các test suites cũ từ Phase 1 của dự án. 
Các test này phụ thuộc vào các module `src.metrics`, `src.portfolio`, `src.alphas`, `src.data.pit_universe` vốn đã được chuyển vào `src/archive_v1/`.

## Danh sách tệp đã lưu trữ:
- `test_metrics.py`: Test cho các hàm performance metric cũ.
- `test_neutralization.py`: Test cho module neutralizer phase 1.
- `test_operators.py`: Test cho toán tử alpha cũ.
- `test_pit_universe.py`: Test cho logic universe cũ dựa trên quy ước "thứ Sáu cuối tháng 6" (đã thay bằng quy ước `01/07/Y -> 30/06/Y+1`).
- `run_tests_legacy.py`: Script runner cũ chạy 4 test suites trên.

Tất cả các bộ test mới của dự án nằm trực tiếp trong thư mục `tests/` và chạy thông qua `python tests/run_tests.py` hoặc `pytest tests/`.
