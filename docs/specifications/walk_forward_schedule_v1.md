# Đặc Tả Kỹ Thuật: Lịch Walk-Forward 5 Folds cho Ridge Baseline v1

**Tác giả**: Dự án Dự đoán Thứ hạng Lợi suất Cổ phiếu Hàng ngày  
**Ngày ban hành**: 2026-11-07  
**Tập dữ liệu nguồn**: [`data/processed/baseline_dataset_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/baseline_dataset_v1.parquet) (5.514.324 dòng, 17 cột)  
**Tệp cấu hình máy đọc**: [`configs/walk_forward_schedule_v1.yaml`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/configs/walk_forward_schedule_v1.yaml)  
**Trạng thái OOS (2024–2026)**: Đóng băng tuyệt đối (Strictly Frozen)  

---

## 1. Mục Đích & Nguyên Tắc Thiết Kế

Lịch Walk-Forward được xây dựng nhằm phục vụ đánh giá thực nghiệm mô hình **Ridge Baseline v1 (13 features Close/Volume)** theo phương thức **Cửa sổ Mở rộng (Expanding Window Walk-Forward)** trên toàn bộ giai đoạn phát triển và kiểm định (Development Window 2000–2023).

### Nguyên tắc cốt lõi:
1. **Phân chia theo phiên giao dịch (Session-Level Partitioning)**: Toàn bộ cổ phiếu thuộc cùng ngày ra quyết định $T$ bắt buộc phải nằm trọn trong cùng một tập (Train hoặc Validation). Không chia tách chéo ngang trong cùng phiên.
2. **Triệt tiêu Lookahead Bias tại Ranh giới (Causal Boundary Purge)**:
   - Sử dụng lịch giao dịch chuẩn của dự án để ánh xạ ngày đóng nhãn $T+1$ của lợi suất mục tiêu $R_{T+1} = Close_{T+1} / Close_T - 1$.
   - **Tập Train**: Loại bỏ hoàn toàn các phiên $T$ có $T+1 \ge \text{val\_start}$ (nhãn chạm sang tập Validation).
   - **Tập Validation**: Loại bỏ các phiên $T$ có $T+1 > \text{val\_end}$ (nhãn kết thúc sau năm validation đó). Riêng năm 2023, phiên cuối `2023-12-29` đã được loại bỏ ở dataset nguồn để tránh rò rỉ sang OOS 2024.
3. **Bảo toàn Nhãn & Features (No Re-ranking, No Re-scaling)**:
   - Giữ nguyên toàn bộ 13 features và nhãn `target_rank` đã được tính chéo ngang trên tập hợp lệ tại phiên $T$. Tuyệt đối không tính lại rank sau khi chia tập.
4. **Tái lập Trực tiếp Không Sinh File Thừa (In-Memory Slicing)**:
   - Cấu hình cung cấp bộ lọc chuỗi ngày (`query_filter`) để nạp trực tiếp từ `baseline_dataset_v1.parquet`, không cần lưu thêm 10 tệp Parquet vật lý trung gian gây lãng phí ổ đĩa (~6 GB).

---

## 2. Bảng Tổng Hợp 5 Folds Walk-Forward

| Fold ID | Tập | Nhãn Giai Đoạn | Khoảng Ngày Thực Tế | Số Phiên | Dòng Danh Nghĩa | Dòng Bị Purge | Dòng Sạch Sau Purge | Danh Sách Phiên Bị Purge & Lý Do |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Fold 1** | **Train** | `2000-2018` | `2000-07-03` $\to$ `2018-12-28` | **4.652** | 4.308.228 | **920** | **4.307.308** | `2018-12-31`: Nhãn $T+1 = \text{2019-01-02}$ chạm Val 2019 |
| | **Val** | `2019` | `2019-01-02` $\to$ `2019-12-30` | **251** | 235.997 | **945** | **235.052** | `2019-12-31`: Nhãn $T+1 = \text{2020-01-02}$ kết thúc sau năm 2019 |
| **Fold 2** | **Train** | `2000-2019` | `2000-07-03` $\to$ `2019-12-30` | **4.904** | 4.544.225 | **945** | **4.543.280** | `2019-12-31`: Nhãn $T+1 = \text{2020-01-02}$ chạm Val 2020 |
| | **Val** | `2020` | `2020-01-02` $\to$ `2020-12-30` | **252** | 240.992 | **958** | **240.034** | `2020-12-31`: Nhãn $T+1 = \text{2021-01-04}$ kết thúc sau năm 2020 |
| **Fold 3** | **Train** | `2000-2020` | `2000-07-03` $\to$ `2020-12-30` | **5.157** | 4.785.217 | **958** | **4.784.259** | `2020-12-31`: Nhãn $T+1 = \text{2021-01-04}$ chạm Val 2021 |
| | **Val** | `2021` | `2021-01-04` $\to$ `2021-12-30` | **251** | 240.676 | **955** | **239.721** | `2021-12-31`: Nhãn $T+1 = \text{2022-01-03}$ kết thúc sau năm 2021 |
| **Fold 4** | **Train** | `2000-2021` | `2000-07-03` $\to$ `2021-12-30` | **5.409** | 5.025.893 | **955** | **5.024.938** | `2021-12-31`: Nhãn $T+1 = \text{2022-01-03}$ chạm Val 2022 |
| | **Val** | `2022` | `2022-01-03` $\to$ `2022-12-29` | **250** | 244.950 | **979** | **243.971** | `2022-12-30`: Nhãn $T+1 = \text{2023-01-03}$ kết thúc sau năm 2022 |
| **Fold 5** | **Train** | `2000-2022` | `2000-07-03` $\to$ `2022-12-29` | **5.660** | 5.270.843 | **979** | **5.269.864** | `2022-12-30`: Nhãn $T+1 = \text{2023-01-03}$ chạm Val 2023 |
| | **Val** | `2023` | `2023-01-03` $\to$ `2023-12-28` | **249** | 243.481 | **0** | **243.481** | `2023-12-29` đã bị loại bỏ ở dataset nguồn; phiên `2023-12-28` có nhãn kết thúc ngày `2023-12-29` hoàn toàn trong năm 2023 |

> [!IMPORTANT]
> **Đối chiếu Mốc Kiểm Định (Benchmark Parity)**:
> - **Fold 1 Train sạch**: Đúng **4.307.308 dòng** (4.652 phiên từ `2000-07-03` đến `2018-12-28`), khớp hoàn toàn với file [`data/processed/train_baseline_v1.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/train_baseline_v1.parquet) đã dùng trong bài kiểm tra baseline đơn lẻ.
> - **Tính rời nhau (Disjointness)**: Mọi fold đều thỏa mãn $\text{Train Sessions} \cap \text{Val Sessions} = \emptyset$ (0 phiên trùng lặp) và $\text{actual\_end}_{\text{train}} < \text{actual\_start}_{\text{val}}$.

---

## 3. Cách Thức Tái Tạo Dữ Liệu Từng Fold (Direct Slicing Protocol)

Trong bước thực thi tiếp theo, việc nạp và chia tập sẽ được thực hiện trực tiếp trong bộ nhớ bằng predicate pushdown hoặc filtering:

```python
import pandas as pd
import yaml

# 1. Nạp cấu hình walk-forward
with open("configs/walk_forward_schedule_v1.yaml", "r", encoding="utf-8") as f:
    wf_cfg = yaml.safe_load(f)

# 2. Nạp dataset baseline nguồn
df_all = pd.read_parquet("data/processed/baseline_dataset_v1.parquet")

# 3. Lặp qua từng fold để huấn luyện và đánh giá
for fold in wf_cfg["folds"]:
    f_id = fold["fold_id"]
    tr_meta = fold["train"]
    vl_meta = fold["validation"]

    # Cắt tập Train và Validation trực tiếp
    df_train = df_all.query(f"date >= '{tr_meta['actual_start']}' and date <= '{tr_meta['actual_end']}'")
    df_val = df_all.query(f"date >= '{vl_meta['actual_start']}' and date <= '{vl_meta['actual_end']}'")

    print(f"Fold {f_id}: Train={len(df_train):,} dòng, Val={len(df_val):,} dòng")
```

---

## 4. Kế Hoạch Bước Tiếp Theo (Subsequent Execution Scope)

1. **Chuẩn hóa & Huấn luyện Từng Fold**:
   - Khởi tạo riêng biệt `StandardScaler()` và `Ridge(alpha=1.0, fit_intercept=True)` cho từng fold.
   - Fit `StandardScaler` và `Ridge` chỉ trên tập `df_train` của fold đó.
   - Áp dụng scaler và dự đoán trên `df_val` của fold đó để thu được `ridge_score`.
2. **Đánh giá Hiệu năng**:
   - Tính toán **Mean Daily Spearman Rank IC**, Positive IC Ratio và IC IR chéo ngang theo từng ngày giao dịch trên tập Validation của từng năm (2019, 2020, 2021, 2022, 2023).
   - So sánh với tín hiệu benchmark `ret_20d` trên cùng tập mã và cùng ngày.
   - Đánh giá độ ổn định của Rank IC qua 5 chu kỳ thị trường khác biệt (2019 tăng trưởng, 2020 biến động Covid-19, 2021 phục hồi, 2022 lạm phát/siết tiền tệ, 2023 phục hồi công nghệ).
3. **Mục đích của giai đoạn 2019–2023**: Dùng để phân tích cơ cấu đặc trưng, chọn lọc siêu tham số $\alpha$, và hoàn thiện baseline trước khi chạm tới tập kiểm thử mù cuối cùng.
4. **Tập OOS 2024–2026**: Giữ nguyên tắc đóng băng tuyệt đối, chỉ mở duy nhất một lần khi toàn bộ kiến trúc mô hình đã được cố định.
