# Chạy kiểm thử local và CI

## Hai phạm vi khác nhau

GitHub clone không có kho Parquet và một số CSV output parser đã bị Git ignore. Vì vậy tests dùng toàn kho không thể chạy trên hosted runner chỉ bằng checkout code.

- **CI portable:** logic trên dữ liệu tổng hợp, loader trên Parquet nhỏ tạo trong thư mục tạm, kiểm tra code/config và các artifact đã có trong Git. Chạy bằng `python -m pytest -q -ra --strict-markers -m "not integration"`.
- **Integration với dữ liệu thật:** tests cần matrices hoặc CSV parser cục bộ. Chạy bằng `python -m pytest -q -ra --strict-markers -m integration` sau khi chuẩn bị dữ liệu theo DAG/data dictionary.
- **Toàn bộ local:** `python -m pytest -q -ra --strict-markers`. Không lọc marker; vẫn báo lỗi nếu thiếu input. CI xanh không có nghĩa integration đã pass hoặc pilot được nghiệm thu.

Không tự skip tests chỉ vì thiếu file. Hosted CI chủ động chọn phạm vi bằng marker; pytest ghi rõ số tests bị deselect. Integration không được chạy trong hosted workflow hiện tại và được nêu rõ trong GitHub job summary.

## Cài dependencies

```powershell
# Chỉ cho code/synthetic tests
python -m pip install -r requirements-ci.txt
python -m pytest -q -ra --strict-markers -m "not integration"

# Khi có input thật, kiểm tra riêng integration
python -m pytest -q -ra --strict-markers -m integration
```

`requirements.txt` vẫn dành cho môi trường nghiên cứu rộng hơn; CI dùng danh sách nhỏ, không cài torch/model/deployment chỉ để kiểm tra loader và công thức nền. Workflow kiểm tra Python 3.10 và 3.14; kết quả mỗi run nằm trong GitHub Actions.

## Phân loại tests

`tests/conftest.py` gắn marker integration cho các ca sẵn có cần file ngoài Git, theo module và tên test. Cách này tránh sửa các file đang được phát triển đồng thời cho pilot. Khi thêm test dữ liệu mới, dùng trực tiếp:

```python
import pytest

@pytest.mark.integration
def test_against_local_dataset():
    # Đọc và kiểm tra dataset thật ở đây; thiếu input phải báo lỗi.
    ...
```

Đăng ký marker trong `pytest.ini`; `--strict-markers` bắt lỗi tên marker sai. Không đánh dấu integration chỉ để giấu một test logic thất bại. Các phép tính độc lập có thể kiểm tra bằng fixtures tổng hợp nên thuộc nhóm portable.

`tests/test_loader_synthetic.py` tạo Parquet rất nhỏ bằng `tmp_path`, kiểm tra slicing Development/warm-up, chặn OOS, alignment và input quality không phụ thuộc membership. Dữ liệu này kiểm tra hành vi thư viện, không thay thế kiểm chứng 7.252×3.711 ô thị trường.

## Vì sao không dùng runner unittest cũ trong CI?

`tests/run_tests.py` chỉ khám phá tests kiểu unittest, bỏ các hàm pytest và không áp dụng phân loại marker của pytest. Lệnh chuẩn là `python -m pytest`, dùng cho cả tests kiểu hàm và unittest. Giữ runner cũ để tham khảo, không dùng nó làm kết quả toàn suite.

## Đọc kết quả GitHub Actions

Mỗi phiên bản Python có log pytest và summary nêu số tests đã chạy, lỗi/skips và phạm vi chưa thực hiện. Lỗi cài dependencies hoặc không tạo được báo cáo vẫn phải xem trong log; không được hiểu thiếu XML là đã pass.

Workflow hiện là **CI kiểm thử code**, chưa triển khai ứng dụng hoặc chạy training/backtest. Không tải tự động dữ liệu Drive hay bỏ đóng băng OOS để làm CI xanh.

Tham khảo: [pytest markers](https://docs.pytest.org/en/stable/example/markers.html), [GitHub: build/test Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
