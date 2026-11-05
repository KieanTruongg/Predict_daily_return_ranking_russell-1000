> Báo cáo artifact raw ngày 2026-11-03, không phải kết luận chất lượng cuối mọi tầng. Diễn giải được cập nhật ngày 2026-11-05. Xem [lineage hiện hành](../../reports/data_pipeline/data_lineage_report.md) và [hướng dẫn từng chặng](../../learning/README.md). Các số dưới là ghi nhận của báo cáo cũ, không được lượt này tái tính từ toàn bộ kho.

# 📑 Báo Cáo Thẩm Định Toàn Diện Dữ Liệu Thị Trường & Độ Phủ PIT Thực Tế
**Dự án:** Dự Đoán Thứ Hạng Lợi Suất Hàng Ngày (Russell 1000 Daily Return Rankings)  
**Quy ước kỳ thành viên:** Danh sách năm Y áp dụng từ `01/07/Y` đến `30/06/Y+1` (Không giả lập biến động giữa kỳ).  
**Thời gian thẩm định:** 2026-11-03 00:29:38  

---

## 1. Thẩm Định Động Kho Dữ Liệu Gốc (Tier 1: Constituents Market Data)

Các chỉ số dưới đây là kết quả đã ghi trong audit ở thời điểm tạo; đối chiếu artifact/code trước khi dùng làm kết luận mới:

* **File Master:** `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet`
* **Tổng số dòng dữ liệu:** `13,147,389` dòng | **Số cột:** `9`
* **Dải thời gian:** `1998-01-02` đến `2026-10-30` (**7,252 ngày giao dịch**)
* **Mã độc nhất có dữ liệu:** `2,846` mã | **Số SID độc nhất:** `4,463`
* **Kiểm định Null:** **0 nulls (0.00%)** trên tất cả 9 cột (`date`, `original_ticker`, `qc_ticker`, `sid`, `open`, `high`, `low`, `close`, `volume`).
* **Kiểm định Sanity (Logic giá thị trường):** **0 vi phạm** trên toàn bộ 8 ràng buộc:
  - High < Low: 0 vi phạm
  - High < max(Open, Close): 0 vi phạm
  - Low > min(Open, Close): 0 vi phạm
  - Open <= 0 hoặc Close <= 0: 0 vi phạm
  - Volume < 0: 0 vi phạm
* **Khóa chính duy nhất:** Khóa `(date, original_ticker)` có **0 trùng lặp**.

> ⚠️ **Phát hiện quan trọng về trùng lặp `(date, sid)`:**  
> Có **796,602 dòng** trùng lặp trên cặp `(date, sid)`. Nguyên nhân xuất phát từ **256 cặp đổi tên/mã công ty** (ví dụ: `ABC` đổi thành `COR` Cencora, `FB` đổi thành `META`, `ANTM` đổi thành `ELV`).  
> QuantConnect trả về cùng chuỗi giá của doanh nghiệp cho cả mã cũ lẫn mã mới. Kho canonical cần xử lý alias và dedup theo identity; membership chọn đối tượng theo thời gian, không thay thế khử trùng. Xem báo cáo identity hiện hành.

---

## 2. Đo Lường Độ Phủ Point-In-Time (PIT) Daily Membership Thực Tế

Khác với thống kê thô trước đây (chỉ đo sự xuất hiện ít nhất 1 lần trong năm dương lịch đạt 98.11%), phép đo này áp dụng **nghiêm ngặt khung thời gian thành viên thực tế từ `01/07/Y` đến `30/06/Y+1`**:

* **Tổng số kỳ tái cơ cấu thẩm định:** `27 kỳ` (2000 đến 2026).
* **Tổng số lượt quan sát kỳ vọng (Constituent-Days):** `6,599,893` lượt.
* **Tổng số lượt quan sát thực tế có nến giao dịch:** `6,362,735` lượt.
* **TỶ LỆ ĐỘ PHỦ DAILY PIT MEMBERSHIP THỰC TẾ:** **`96.41%`**.
* **Số cổ phiếu hoạt động trung bình mỗi ngày trong rổ:** **`960.8 / ~1,000 cổ phiếu`**.

### Bảng Theo Dõi Độ Phủ Từng Kỳ Tái Cơ Cấu (Reconstitution Periods)

| Kỳ Reconstitution | Khung Thời Gian | Số Ngày GD | Thành Viên Chính Thức | TB Hoạt Động/Ngày | Độ Phủ Daily (%) | Số Mã Đủ 100% Ngày | Số Mã Có Dữ Liệu Một Phần Kỳ (Partial) | Số Mã 0 Nến (Zero) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2000 | `2000-07-01` đến `2001-06-30` | 251 | 996 | 941.2 | **94.50%** | 905 | 74 | 17 |
| 2001 | `2001-07-01` đến `2002-06-30` | 247 | 989 | 943.0 | **95.35%** | 917 | 56 | 16 |
| 2002 | `2002-07-01` đến `2003-06-30` | 252 | 988 | 954.8 | **96.64%** | 946 | 20 | 22 |
| 2003 | `2003-07-01` đến `2004-06-30` | 252 | 988 | 952.9 | **96.45%** | 943 | 21 | 24 |
| 2004 | `2004-07-01` đến `2005-06-30` | 253 | 990 | 949.9 | **95.95%** | 937 | 27 | 26 |
| 2005 | `2005-07-01` đến `2006-06-30` | 252 | 987 | 934.2 | **94.65%** | 905 | 56 | 26 |
| 2006 | `2006-07-01` đến `2007-06-30` | 250 | 982 | 939.8 | **95.71%** | 918 | 44 | 20 |
| 2007 | `2007-07-01` đến `2008-06-30` | 252 | 1013 | 958.6 | **94.63%** | 940 | 48 | 25 |
| 2008 | `2008-07-01` đến `2009-06-30` | 252 | 1002 | 956.8 | **95.49%** | 941 | 36 | 25 |
| 2009 | `2009-07-01` đến `2010-06-30` | 252 | 967 | 934.4 | **96.63%** | 918 | 27 | 22 |
| 2010 | `2010-07-01` đến `2011-06-30` | 253 | 981 | 948.1 | **96.65%** | 925 | 38 | 18 |
| 2011 | `2011-07-01` đến `2012-06-30` | 252 | 982 | 942.7 | **96.00%** | 929 | 29 | 24 |
| 2012 | `2012-07-01` đến `2013-06-30` | 249 | 987 | 951.3 | **96.38%** | 939 | 26 | 22 |
| 2013 | `2013-07-01` đến `2014-06-30` | 252 | 1000 | 966.8 | **96.68%** | 958 | 20 | 22 |
| 2014 | `2014-07-01` đến `2015-06-30` | 252 | 1023 | 989.2 | **96.69%** | 974 | 27 | 22 |
| 2015 | `2015-07-01` đến `2016-06-30` | 253 | 1026 | 983.2 | **95.83%** | 961 | 45 | 20 |
| 2016 | `2016-07-01` đến `2017-06-30` | 252 | 991 | 953.8 | **96.24%** | 937 | 36 | 18 |
| 2017 | `2017-07-01` đến `2018-06-30` | 251 | 980 | 946.3 | **96.56%** | 929 | 35 | 16 |
| 2018 | `2018-07-01` đến `2019-06-30` | 250 | 976 | 946.3 | **96.96%** | 933 | 28 | 15 |
| 2019 | `2019-07-01` đến `2020-06-30` | 253 | 1001 | 968.4 | **96.74%** | 957 | 22 | 22 |
| 2020 | `2020-07-01` đến `2021-06-30` | 252 | 994 | 968.1 | **97.39%** | 953 | 28 | 13 |
| 2021 | `2021-07-01` đến `2022-06-30` | 252 | 1017 | 988.9 | **97.24%** | 973 | 33 | 11 |
| 2022 | `2022-07-01` đến `2023-06-30` | 251 | 1013 | 987.6 | **97.50%** | 975 | 27 | 11 |
| 2023 | `2023-07-01` đến `2024-06-30` | 250 | 1011 | 991.4 | **98.06%** | 978 | 20 | 13 |
| 2024 | `2024-07-01` đến `2025-06-30` | 250 | 1010 | 987.0 | **97.72%** | 976 | 20 | 14 |
| 2025 | `2025-07-01` đến `2026-06-30` | 251 | 1014 | 985.1 | **97.15%** | 972 | 29 | 13 |
| 2026 | `2026-07-01` đến `2026-10-30` | 86 | 1011 | 995.5 | **98.47%** | 993 | 3 | 15 |

---

## 3. Phân Tích Sự Thiếu Hụt (~3.59% Khoảng Trống)

Độ phủ 96,41% mô tả phép đo và mẫu số của phiên bản này. Các lý do dưới là phân loại/giả thuyết cần đối chiếu từng trường hợp, không tự chứng minh nguyên nhân thực tế:
1. **Các mã có dữ liệu một phần kỳ (Partial Coverage):** Trung bình mỗi kỳ có **~25 đến 56 mã** có thể do lên sàn giữa kỳ, tạm ngừng giao dịch, hoặc hủy niêm yết/M&A trước khi kết thúc kỳ.
2. **Các mã không có nến (Zero Bars):** Chỉ có **~15 đến 26 mã mỗi kỳ** hoàn toàn không có dữ liệu, tập trung chủ yếu ở:
   - Các cổ phiếu Class A (`BRK.A`, `JW.A`, `FCE.A`).
   - Nhóm 5 mã có chưa ghi nhận dữ liệu trong cơ sở dữ liệu hiện tại (`CR`, `PL`, `AVX`, `ENR`, `BTU`).
   - Các mã tái cấu trúc đổi SID chưa phân giải (`RF`, `FNF`, `WM`, `UAL`).

---

## 4. Danh Mục Bảng Dữ Liệu Kiểm Soát Động

Các bảng dữ liệu kiểm soát đã được cập nhật đầy đủ trong thư mục `docs/Data report/market_data_audit/tables/`:
1. `tables/warehouse_sanity_check.csv`: Kết quả live test 0 nulls, 0 vi phạm giá.
2. `tables/daily_pit_coverage_by_period.csv`: Bảng chi tiết độ phủ daily của 27 kỳ tái cơ cấu.
3. `tables/zero_bar_constituents_by_period.csv`: Danh sách 512 lượt thành viên-kỳ không có nến.
4. `tables/batch_execution_summary.csv`: Thống kê 10 batch thu thập từ QC.
5. `tables/ticker_identity_transitions.csv`: Danh sách 1,668 mã có biến động danh tính SID.

## Đọc coverage đúng phạm vi

Null=0 chỉ xét các dòng hiện có; thiếu cả bar/ngày cần kiểm tra coverage riêng. 96,41% so với source snapshot và 99,66% so với membership đã phân giải là hai mẫu số khác nhau. Không dùng tỷ lệ trên tập đã loại unresolved để tuyên bố toàn bộ nguồn đầy đủ. 2.846 ticker có bar toàn kho khác số mã đủ bar trong từng kỳ hoặc đủ feature/target.
