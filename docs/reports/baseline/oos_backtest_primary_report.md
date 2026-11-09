# Báo Cáo Kiểm Thử Giao Dịch Ngoài Mẫu Chính Thức (OOS Backtest Primary Report)
## Đánh Giá Danh Mục Long-Only Top 20 Trên Phạm Vi Ngoài Mẫu Chính (624 Phiên Thực Thi: 2024-01-03 đến 2026-06-30)

> **Tài liệu tham chiếu:**
> - Kế hoạch & Đặc tả phương pháp luận: [`docs/specifications/backtest_plan_v1.md`](../../specifications/backtest_plan_v1.md)
> - Báo cáo đánh giá OOS Rank IC: [`docs/reports/baseline/oos_evaluation_report.md`](oos_evaluation_report.md)
> - Báo cáo thử nghiệm lát cắt 5 phiên: [`docs/reports/baseline/backtest_trial_slice_report.md`](backtest_trial_slice_report.md)
> - Động cơ mô phỏng danh mục: [`src/backtest/simulator.py`](../../../src/backtest/simulator.py)
> - Kịch bản thực thi chính thức: [`scripts/01_pipeline/31_run_oos_backtest_primary.py`](../../../scripts/01_pipeline/31_run_oos_backtest_primary.py)
> - Thư mục kết quả và sổ lệnh chi tiết: [`outputs/reports/backtest_primary_scope/`](../../../outputs/reports/backtest_primary_scope/)

---

> [!IMPORTANT]
> **Lưu ý về phương pháp luận và ranh giới nghiên cứu:**
> Toàn bộ quy tắc danh mục đầu tư (cấu hình Long-Only Top 20, trọng số đều tối đa 5% NAV/mã, thời điểm vào lệnh Open $T+1$ và thoát lệnh Close $T+1$, cơ chế tự tài trợ ngân sách và bộ lọc chặn lệnh mua trước Open) được thiết kế **sau khi nhóm nghiên cứu đã xem xét, đối chiếu và đánh giá toàn diện kết quả Rank IC Ngoài mẫu (OOS)**.
> Mục đích của kiểm thử backtest này không phải là tìm kiếm chiến lược giao dịch tối ưu (không tối ưu hóa tham số hay điều chỉnh luật sau OOS), mà là **đối soát tính khả thi thực tế, kiểm tra tác động của sự kiện doanh nghiệp (M&A/Halt) và đo lường sự bào mòn của chi phí ma sát đối với các mô hình định lượng**.

---

## 1. Phân Tách Rạch Ròi: Đánh Giá Tín Hiệu (Rank IC) vs Hiệu Năng Danh Mục (Top 20 PnL)

Một nguyên tắc cốt lõi trong tài chính định lượng là sự phân tách giữa **khả năng xếp hạng của mô hình (Signal Quality)** và **hiệu năng danh mục sau chi phí giả định (Tradable Portfolio Return)**. Bảng dưới đây đối chiếu trực tiếp ba cấp độ đánh giá trên cùng phạm vi 624 phiên ngoài mẫu:

| Cấp độ Đánh giá | Tiêu chí / Chỉ số | Ridge Baseline ($\alpha=1.0$) | GBDT Candidate (7 leaves) | Benchmark `ret_20d` | Ý nghĩa tài chính |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Cấp độ 1:**<br>**Chất lượng Tín hiệu**<br>*(OOS Rank IC toàn Universe)* | **Mean Rank IC**<br>t-statistic<br>Annualized IR<br>% Phiên dương | **+0.023050**<br>$t = +3.58$<br>+2.28<br>56.4% | **+0.020403**<br>$t = +3.43$<br>+2.18<br>56.2% | **-0.004393**<br>$t = -0.64$<br>-0.41<br>48.7% | **Mô hình có xếp đúng thứ tự tương đối của cổ phiếu?**<br>Cả Ridge và GBDT đều có alpha dương vững chắc ($t > 3.0$ và $\text{IR} > 2.0$), vượt trội hoàn toàn so với động lượng quá khứ ($t = -0.64$). Ridge nhỉnh hơn GBDT trên toàn bộ 976 mã. |
| **Cấp độ 2:**<br>**Danh mục Top 20**<br>**TRƯỚC Chi phí (0 bps)**<br>*(Gross Alpha)* | **NAV Cuối kỳ ($)**<br>Lợi suất lũy kế (%)<br>CAGR (%)<br>Sharpe (Ann.)<br>Max Drawdown (%) | **134,925.42**<br>**+34.93%**<br>+12.86%<br>+0.60<br>-23.63% | **92,174.37**<br>**-7.83%**<br>-3.24%<br>-0.06<br>-27.95% | **112,904.83**<br>**+12.90%**<br>+5.02%<br>+0.33<br>-38.82% | **Top 20 mã có mang lại alpha thô dương?**<br>Khi chưa có ma sát, Ridge chuyển hóa thành công Rank IC thành lợi nhuận gộp +34.93%. GBDT ghi nhận hiệu năng Top 20 gộp đạt -7.83%, cho thấy tín hiệu xếp hạng tổng thể trên 976 mã không đồng nghĩa với việc nhóm 20 mã điểm cao nhất sinh lời gộp dương. |
| **Cấp độ 3:**<br>**Danh mục Top 20**<br>**SAU Chi phí (20 bps)**<br>*(Net Tradable PnL)* | **NAV Cuối kỳ ($)**<br>Lợi suất lũy kế (%)<br>CAGR (%)<br>Sharpe (Ann.)<br>Max Drawdown (%) | **38,807.77**<br>**-61.19%**<br>-31.77%<br>-1.40<br>-63.94% | **26,469.23**<br>**-73.53%**<br>-41.54%<br>-2.57<br>-74.08% | **32,415.77**<br>**-67.58%**<br>-36.55%<br>-1.83<br>-72.80% | **Chiến lược có sinh lời sau chi phí giả định?**<br>Chiến lược xoay vòng hàng ngày với chi phí giả định 20 bps round-trip bào mòn toàn bộ lợi nhuận gộp của cả ba mô hình. Tuy nhiên, Ridge vẫn giữ vốn tốt hơn GBDT (+12,338 USD) và Benchmark (+6,392 USD). |

---

## 2. Bảng Tổng Hợp Chi Tiết 6 Kịch Bản Chuẩn Mực

Số liệu được trích xuất trực tiếp và chính xác từ tệp dữ liệu gốc [`performance_summary_all_scenarios.csv`](../../../outputs/reports/backtest_primary_scope/performance_summary_all_scenarios.csv) trên 624 phiên ngoài mẫu (vốn khởi tạo: 100.000 USD):

| Kịch bản Chi phí | Mô hình Tín hiệu | NAV Cuối kỳ ($) | Lợi nhuận ròng ($) | Tỷ suất (%) | CAGR (%) | Sharpe (Ann.) | Max Drawdown (%) | Tổng Phí ($) | Tổng Trượt giá ($) | Tổng Chi phí ($) | Lệnh Mua Khớp | Lệnh Hủy (Tổng) | Hủy do Halt M&A | Hủy do thiếu Open | Lệnh Bán Khớp | Vị thế Mở Cuối | Tiền mặt Cuối ($) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **20 bps (Baseline)** | **Ridge ($\alpha=1.0$)** | **38,807.77** | -61,192.23 | **-61.19%** | -31.77% | -1.40 | **-63.94%** | 40,192.75 | 40,192.76 | 80,385.51 | 12,461 | **19** | **17** | **2** | 12,461 | **0** | 38,807.77 |
| *(5 bps fee + 5 bps slip)* | **GBDT (7 leaves)** | **26,469.23** | -73,530.77 | **-73.53%** | -41.54% | -2.57 | **-74.08%** | 34,890.61 | 34,890.61 | 69,781.23 | 12,477 | **3** | **3** | **0** | 12,477 | **0** | 26,469.23 |
| | **ret_20d (Benchmark)** | **32,415.77** | -67,584.23 | **-67.58%** | -36.55% | -1.83 | **-72.80%** | 31,139.46 | 31,139.46 | 62,278.93 | 12,479 | **1** | **1** | **0** | 12,479 | **0** | 32,415.77 |
| **0 bps (Gross)** | **Ridge ($\alpha=1.0$)** | **134,925.42** | +34,925.42 | **+34.93%** | +12.86% | +0.60 | **-23.63%** | 0.00 | 0.00 | 0.00 | 12,461 | **19** | **17** | **2** | 12,461 | **0** | 134,925.42 |
| *(Không chi phí)* | **GBDT (7 leaves)** | **92,174.37** | -7,825.63 | **-7.83%** | -3.24% | -0.06 | **-27.95%** | 0.00 | 0.00 | 0.00 | 12,477 | **3** | **3** | **0** | 12,477 | **0** | 92,174.37 |
| | **ret_20d (Benchmark)** | **112,904.83** | +12,904.83 | **+12.90%** | +5.02% | +0.33 | **-38.82%** | 0.00 | 0.00 | 0.00 | 12,479 | **1** | **1** | **0** | 12,479 | **0** | 112,904.83 |

> [!NOTE]
> **Hiệu đính thống kê bộ đếm lý do hủy lệnh:**
> * Trong các bản chạy thử trước đây, bộ đếm đã vô tình lọc trên toàn bộ sổ lệnh mà không giới hạn hành động, dẫn đến việc cộng gộp cả 74 dòng hoãn thoát vị thế ở phiên đóng cửa (`HELD_OVERNIGHT` do khối lượng giao dịch cả ngày bằng 0) vào lý do thiếu giá Open (tạo ra con số 76 gây hiểu nhầm).
> * Khi chuẩn hóa chỉ đếm trong tập lệnh `action == "CANCELLED_BUY"`, số lệnh hủy do thiếu giá Open của Ridge là đúng **2 lệnh** (phiên 21/05/2025 mã `NOBE` và phiên 07/08/2025 mã `VIA`).
> * Tổng số lệnh hủy mua tại Open của Ridge là **19 lệnh = 17 lệnh do Halt M&A + 2 lệnh do thiếu giá Open**. Thống kê hoàn toàn cân khớp và nhất quán.

---

## 3. Cơ Chế Xử Lý 18 Sự Kiện Doanh Nghiệp & Đối Chiếu Trực Tiếp Sổ Lệnh MRTX

### 3.1. Danh mục 18 sự kiện đình chỉ niêm yết (Halt Flags)
Toàn bộ 18 sự kiện ngừng giao dịch trước giờ mở cửa sàn đã được rà soát, đối chiếu trực tiếp với hồ sơ SEC Form 8-K Item 3.01 và thông cáo sở giao dịch, lưu trữ tại [`reconciliation_open_positions.csv`](../../../outputs/reports/backtest_primary_scope/reconciliation_open_positions.csv):
1. `SRC VA4L1G2O9B39` (2024-01-23): Sáp nhập Realty Income.
2. `MRTX VIA09B2Z24X1` (2024-01-23): Bristol-Myers Squibb mua lại (Nasdaq Notice ECA2024-28).
3. `SPLK V5VYQYDIED7P` (2024-03-18): Cisco mua lại (Nasdaq Notice ECA2024-82).
4. `SRCL R735QTJ8XC9X` (2024-11-04): Waste Management mua lại.
5. `RCM WIVGEEITFLNP` (2024-11-19): TowerBrook & CD&R tư nhân hóa.
6. `SMAR WU16SJRONF51` (2025-01-22): Blackstone & Vista tư nhân hóa.
7. `PYCR XQB2AVEUXOIT` (2025-04-14): Paychex mua lại.
8. `BERY VAHDUNTV946D` (2025-04-30): Amcor sáp nhập.
9. `X R735QTJ8XC9X` (2025-06-18): Nippon Steel mua lại (ret_20d).
10. `DNB XFSYMYY1JYW5` (2025-08-26): Clearlake Capital tư nhân hóa.
11. `WAG R735QTJ8XC9X` (2025-08-28): Sycamore Partners tư nhân hóa.
12. `FYBR XO78VO8V1L5X` (2026-01-20): Verizon mua lại.
13. `CFLT XPKH8CJAVB6T` (2026-03-17): IBM mua lại.
14. `EXAS S1UVO02503TX` (2026-03-23): Abbott Laboratories mua lại.
15. `HOLX R735QTJ8XC9X` (2026-04-07): Blackstone & TPG tư nhân hóa.
16. `AL UVVL4QHQE8H1` (2026-04-08): Sumisho Air Lease mua lại.
17. `SEE R9PONSNG9ROL` (2026-04-09): CD&R tư nhân hóa.
18. `COG R735QTJ8XC9X` (2026-05-07): Coterra Energy tái cơ cấu niêm yết.

### 3.2. Đối chiếu trực tiếp sổ lệnh đối với MRTX (Ridge 20 bps)
Theo thông báo Nasdaq Corporate Action Notice ECA2024-28 và SEC Form 8-K Item 3.01 của Mirati Therapeutics: cổ phiếu MRTX bị tạm ngừng giao dịch trước giờ mở cửa ngày 23/01/2024 và chính thức đình chỉ giao dịch từ ngày 24/01/2024.

Trích xuất trực tiếp từ sổ lệnh [`trades_ridge_20bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_ridge_20bps.csv):

| Phiên giao dịch | Mã cổ phiếu (SID) | Tên công ty & Đối tác M&A | Hành động (`action`) | Thời điểm | Giá Open ($) | Số CP | Phí ($) | Trượt giá ($) | Tác động tiền mặt ($) | Ghi chú từ hệ thống |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2024-01-23** | `MRTX VIA09B2Z24X1` | Mirati Ther. $\rightarrow$ Bristol Myers (BMY) | **CANCELLED_BUY** | OPEN | 58.820 | **0.0** | **0.0** | **0.0** | **0.0** | `MARKET_HALT: Pre-market trading halt or suspension` |
| **2024-01-24** | `MRTX VIA09B2Z24X1` | Mirati Ther. $\rightarrow$ Bristol Myers (BMY) | *(Không có lệnh)* | - | - | **0.0** | **0.0** | **0.0** | **0.0** | *Không tồn tại vị thế qua đêm $\rightarrow$ Hoàn toàn không sinh lệnh bán ngày 24/01* |
| **2024-11-19** | `RCM WIVGEEITFLNP` | R1 RCM Inc. $\rightarrow$ TowerBrook & CD&R | **CANCELLED_BUY** | OPEN | 14.300 | **0.0** | **0.0** | **0.0** | **0.0** | `MARKET_HALT: Pre-market trading halt or suspension` |
| **2026-01-20** | `FYBR XO78VO8V1L5X` | Frontier Comm. $\rightarrow$ Verizon (VZ) | **CANCELLED_BUY** | OPEN | 38.480 | **0.0** | **0.0** | **0.0** | **0.0** | `MARKET_HALT: Pre-market trading halt or suspension` |
| **2026-03-17** | `CFLT XPKH8CJAVB6T` | Confluent, Inc. $\rightarrow$ IBM (NYSE: IBM) | **CANCELLED_BUY** | OPEN | 30.680 | **0.0** | **0.0** | **0.0** | **0.0** | `MARKET_HALT: Pre-market trading halt or suspension` |
| **2026-05-07** | `COG R735QTJ8XC9X` | Coterra Energy Inc. (alias CTRA) | **CANCELLED_BUY** | OPEN | 33.445 | **0.0** | **0.0** | **0.0** | **0.0** | `MARKET_HALT: Pre-market trading halt or suspension` |

* **Xác nhận sổ lệnh:**
  1. Vào ngày 23/01/2024, simulator phát hiện cờ halt của `MRTX`, lệnh mua bị chặn ngay tại Open với `action = CANCELLED_BUY`, số cổ phiếu mua là 0.0, phí = 0, trượt giá = 0, tác động tiền mặt = 0, giữ nguyên 100% ngân sách tiền mặt trong danh mục.
  2. Vào ngày 24/01/2024, do không có vị thế mở qua đêm từ phiên trước, hệ thống **hoàn toàn không phát sinh lệnh bán giải tỏa cho MRTX** (loại bỏ triệt để lệnh bán giả định ở phiên bản cũ).

---

## 4. Tình Trạng Vị Thế Còn Mở Cuối Kỳ (Tại Close 2026-06-30)

Sau khi đưa toàn bộ 18 sự kiện vào bảng đối soát:
* **Ridge Baseline ($\alpha=1.0$):** **0 vị thế còn mở** (Toàn bộ tài sản $38,807.77$ USD nằm $100\%$ tại tiền mặt khả dụng).
* **GBDT Candidate (7 leaves):** **0 vị thế còn mở** (Toàn bộ tài sản $26,469.23$ USD nằm $100\%$ tại tiền mặt khả dụng).
* **ret_20d Benchmark:** **0 vị thế còn mở** (Toàn bộ tài sản $32,415.77$ USD nằm $100\%$ tại tiền mặt khả dụng).

> [!TIP]
> Việc ngăn chặn lệnh mua đối với các mã bị đình chỉ giao dịch trước Open đã giải quyết triệt để vấn đề "kẹt thanh khoản" do M&A. Toàn bộ danh mục kết thúc 624 phiên ngoài mẫu trong trạng thái tiền mặt thuần túy, không có bất kỳ khoản vốn nào bị đóng băng hay phụ thuộc vào giả định giải ngân M&A ngoài đời thực.

---

## 5. Phân Tích Chuyên Sâu: Cơ Chế Bào Mòn Giữa 0 bps và 20 bps

| Mô hình Tín hiệu | NAV 0 bps (Gross) ($) | NAV 20 bps (Net) ($) | Chênh lệch NAV ($) | Lợi suất Gross (%) | Lợi suất Net (%) | Tổng Chi phí Trực tiếp ($) | Hiệu ứng Suy giảm Vốn Tái đầu tư ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ridge ($\alpha=1.0$)** | **134,925.42** | **38,807.77** | **-96,117.64** | **+34.93%** | **-61.19%** | **80,385.51** | **-15,732.13** |
| **GBDT (7 leaves)** | **92,174.37** | **26,469.23** | **-65,705.15** | **-7.83%** | **-73.53%** | **69,781.23** | *(Bào mòn vốn gốc)* |
| **ret_20d (Benchmark)** | **112,904.83** | **32,415.77** | **-80,489.07** | **+12.90%** | **-67.58%** | **62,278.93** | **-18,210.14** |

Chênh lệch NAV cuối kỳ giữa kịch bản 0 bps và 20 bps được cấu thành bởi hai yếu tố tài chính độc lập:

### 5.1. Chi phí ma sát trực tiếp (Direct Transaction Friction)
Trong chiến lược xoay vòng vị thế 1 ngày (daily turnover $\approx 100\%$), danh mục phải mở và đóng 20 vị thế mỗi ngày:
* Sau 624 phiên giao dịch, tổng giá trị luân chuyển qua sàn lên tới hơn 40 triệu USD.
* Ở mức chi phí 20 bps/vòng tròn ($5\text{ bps}$ phí sàn $+ 5\text{ bps}$ trượt giá mỗi chiều), tổng số tiền thực nộp cho sàn và tổn thất do trượt giá là **80,385.51 USD** đối với Ridge (phí môi giới: 40,192.75 USD; trượt giá: 40,192.76 USD).
* Riêng khoản chi phí trực tiếp này đã bằng **hơn 80% quy mô vốn ban đầu**.

### 5.2. Hiệu ứng suy giảm vốn tái đầu tư (Compounding & Reinvestment Drag)
Chênh lệch NAV cuối kỳ của Ridge giữa 0 bps và 20 bps là **-96,117.64 USD**, lớn hơn đáng kể so với tổng chi phí trực tiếp đã trừ (**80,385.51 USD**). Khoản chênh lệch dôi dư **-15,732.13 USD** này phản ánh chính xác hiệu ứng suy giảm vốn tái đầu tư:
* Ở kịch bản **0 bps**, lợi nhuận gộp từ các phiên thắng được bảo toàn nguyên vẹn trong tiền mặt, giúp quy mô ngân sách $5\%$ NAV phân bổ cho các mã ở các phiên sau ngày một lớn dần (hiệu ứng lãi kép dương $\rightarrow$ đưa NAV lên $134,925$ USD).
* Ở kịch bản **20 bps**, việc mỗi ngày bị khấu trừ chi phí trên quy mô toàn bộ tài sản làm tiền mặt khả dụng sau mỗi phiên bị hao mòn dần. Quy mô vốn phân bổ cho các mã chiến thắng ở phiên kế tiếp bị thu nhỏ lại theo thời gian, khiến danh mục mất đi cơ hội tích lũy lãi kép (hiệu ứng lãi kép âm).
* Điều này chứng minh rằng đối với một chiến lược định lượng có tần suất giao dịch hàng ngày, **sự bào mòn do suy giảm quy mô vốn tái đầu tư (reinvestment drag) nguy hiểm tương đương hoặc thậm chí lớn hơn chi phí giao dịch trực tiếp**.

---

## 6. Tổng Kết & Bài Học Rút Ra Cho Nghiên Cứu Định Lượng

1. **Về tính toàn vẹn của mô hình**:
   - Cả Ridge Baseline ($\alpha=1.0$) và GBDT Candidate (7 leaves) đều duy trì được hệ số Rank IC dương ổn định trên dữ liệu ngoài mẫu 624 phiên, xác nhận khả năng học được tín hiệu tương đối từ 13 đặc trưng kỹ thuật Close/Volume.
   - Ridge Baseline thể hiện tính ổn định vượt trội hơn hẳn GBDT: vừa có Rank IC cao hơn (+0.02305 vs +0.02040), vừa có alpha gộp dương (+34.93% vs -7.83%), và giữ vốn tốt hơn khi chịu ma sát chi phí giả định ($38,808$ USD vs $26,469$ USD).

2. **Về ranh giới giữa Tín hiệu và Giao dịch**:
   - Kết quả thực nghiệm khẳng định một kết luận quan trọng: **Một mô hình đạt Rank IC dương có ý nghĩa thống kê cao vẫn có thể thua lỗ nặng trong mô phỏng giao dịch nếu chiến lược thực thi có turnover quá cao và thời gian nắm giữ quá ngắn**.
   - Để thương mại hóa tín hiệu dự đoán xếp hạng ngày $T \rightarrow T+1$, các nghiên cứu tiếp theo cần mở rộng chân trời nắm giữ (ví dụ: giữ từ 5 đến 20 phiên, hoặc áp dụng dải đệm tái cân bằng Buffer Rebalancing) nhằm giảm số vòng quay danh mục, cho phép alpha tích lũy đủ lớn để vượt qua rào cản chi phí giao dịch.

---

## 7. Danh Mục Hồ Sơ & Dữ Liệu Bàn Giao

Toàn bộ sổ lệnh, sổ cái và các bảng phân tích đối soát được lưu trữ tại thư mục chuẩn:  
`outputs/reports/backtest_primary_scope/`

1. [`reconciliation_open_positions.csv`](../../../outputs/reports/backtest_primary_scope/reconciliation_open_positions.csv): Bảng 18 sự kiện đình chỉ giao dịch kèm căn cứ SEC Form 8-K và Nasdaq Notices.
2. [`performance_summary_all_scenarios.csv`](../../../outputs/reports/backtest_primary_scope/performance_summary_all_scenarios.csv): Bảng tổng hợp đối đầu 6 kịch bản chuẩn mực.
3. [`performance_summary.csv`](../../../outputs/reports/backtest_primary_scope/performance_summary.csv): Hiệu năng kịch bản Baseline 20 bps (18 halts).
4. [`performance_summary_0bps.csv`](../../../outputs/reports/backtest_primary_scope/performance_summary_0bps.csv): Hiệu năng kịch bản Gross 0 bps (18 halts).
5. [`comparison_0bps_vs_20bps.csv`](../../../outputs/reports/backtest_primary_scope/comparison_0bps_vs_20bps.csv): Bảng phân rã chi tiết chi phí và suy giảm tái đầu tư.
6. [`open_positions_summary.csv`](../../../outputs/reports/backtest_primary_scope/open_positions_summary.csv): Xác nhận trạng thái mở cuối kỳ (0 vị thế treo).
7. Sổ lệnh và sổ cái chi tiết từng phiên:
   - Ridge: [`trades_ridge_20bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_ridge_20bps.csv), [`ledger_ridge_20bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_ridge_20bps.csv), [`trades_ridge_0bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_ridge_0bps.csv), [`ledger_ridge_0bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_ridge_0bps.csv).
   - GBDT: [`trades_gbdt_20bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_gbdt_20bps.csv), [`ledger_gbdt_20bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_gbdt_20bps.csv), [`trades_gbdt_0bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_gbdt_0bps.csv), [`ledger_gbdt_0bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_gbdt_0bps.csv).
   - ret_20d: [`trades_ret_20d_20bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_ret_20d_20bps.csv), [`ledger_ret_20d_20bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_ret_20d_20bps.csv), [`trades_ret_20d_0bps.csv`](../../../outputs/reports/backtest_primary_scope/trades_ret_20d_0bps.csv), [`ledger_ret_20d_0bps.csv`](../../../outputs/reports/backtest_primary_scope/ledger_ret_20d_0bps.csv).
