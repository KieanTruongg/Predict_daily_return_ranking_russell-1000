# Báo Cáo Thử Nghiệm Lát Cắt OOS Backtest (Trial Slice Report)
## Đối Chiếu Ridge (alpha=1.0) vs GBDT (7 leaves) vs ret_20d

> **Tài liệu tham chiếu liên quan:**
> - Đặc tả kiểm thử danh mục: [backtest_plan_v1.md](../../specifications/backtest_plan_v1.md)
> - Đặc tả đánh giá OOS: [oos_evaluation_plan_v1.md](../../specifications/oos_evaluation_plan_v1.md)
> - Mã nguồn động cơ mô phỏng: [`src/backtest/simulator.py`](../../../src/backtest/simulator.py)
> - Kịch bản thực thi thử nghiệm: [`scripts/01_pipeline/30_run_oos_backtest_slice.py`](../../../scripts/01_pipeline/30_run_oos_backtest_slice.py)
> - Dữ liệu kết quả lát cắt: [`outputs/reports/backtest_trial_slice/`](../../../outputs/reports/backtest_trial_slice/)

---

## 1. Tóm Tắt & Mục Tiêu Thử Nghiệm

Mục tiêu của lượt thử nghiệm này là **kết nối hoàn chỉnh bộ mô phỏng [`PortfolioSimulator`](../../../src/backtest/simulator.py) với bảng dự đoán OOS đã lưu (`oos_predictions_2024_2026.parquet`) và hệ thống ma trận giá thị trường thực tế**, thực thi kiểm thử trên lát cắt **5 phiên giao dịch đầu tiên của giai đoạn Out-of-Sample (OOS)** từ ngày `2024-01-02` đến `2024-01-09`.

### Các nguyên tắc phương pháp luận bắt buộc:
1. **Lựa chọn Top 20 tại $T$ độc lập với $T+1$ (No Look-Ahead Bias)**:
   Tại mỗi phiên tín hiệu $T$, danh sách Top 20 được trích xuất hoàn toàn dựa trên bảng điểm dự đoán sinh ra tại Close $T$, sắp xếp giảm dần theo điểm số của mô hình (`ridge_score`, `gbdt_score`, `ret_20d`). Tuyệt đối không đọc bất kỳ dữ liệu giá, khối lượng hay điều kiện nào tại $T+1$ trước khi chốt danh sách đặt lệnh.
2. **Kiểm tra tính hợp lệ của giá và cách ly đúng trường (Field-Level Quarantine)**:
   - Giá $P^{\text{open}}$ và $P^{\text{close}}$ phải là số thực hữu hạn (`np.isfinite`) và dương ($> 0$).
   - Nếu một mã bị cách ly trường Open (ví dụ do lỗi tick mở cửa trong `market_data_corrections_and_exceptions.csv`), giá trị $P^{\text{open}}$ bị gán `NaN`, lệnh mua bị hủy và giữ tiền mặt. Tuy nhiên, giá $P^{\text{close}}$ của mã đó **vẫn được bảo toàn nguyên vẹn** nếu Close không bị lỗi.
   - Chỉ khi toàn bộ phiên bị cờ `is_bad_data_period == True` hoặc `is_spinoff_discontinuity == True` (Full-Bar Quarantine) thì cả Open và Close mới đồng thời bị vô hiệu hóa.
3. **Phân loại tường minh lý do không khớp lệnh**:
   - `MISSING_SIM_PRICE`: Thiếu giá mô phỏng do lỗi cấp dữ liệu, giá `NaN`, không dương, hoặc bị quarantine kỹ thuật.
   - `EVIDENCE_UNFILLED`: Có bằng chứng giao dịch thực tế không thể khớp (cổ phiếu bị tạm ngừng giao dịch trước giờ mở cửa, hoặc khối lượng cả ngày $V = 0$ tại Close do halt giữa phiên).
4. **Cơ chế xử lý Corporate Actions khi vị thế bị giữ qua đêm**:
   Trường hợp cổ phiếu không thể bán tại Close $T+1$ và phải giữ qua đêm sang $T+2$, nếu ngày $T+2$ là ngày giao dịch không hưởng quyền:
   - **Chia tách / Gộp cổ phiếu (Stock Split / Reverse Split)**: Tự động điều chỉnh số lượng cổ phiếu sở hữu $Q_{T+2} = Q_{T+1} \times S$ và điều chỉnh giá vốn / giá tham chiếu $P_{T+2} = P_{T+1} / S$ để bảo toàn giá trị Mark-to-Market.
   - **Cổ tức tiền mặt (Cash Dividend)**: Nhà đầu tư được hưởng trọn vẹn cổ tức do đã nắm giữ cổ phiếu qua thời điểm chốt quyền, tài khoản nhận tiền mặt $\text{Cash} += Q_{T+1} \times D$ và ghi log `DIVIDEND_PAYOUT`.
5. **So sánh công bằng trên cùng một quy tắc giao dịch**:
   Cả 3 mô hình đều chạy trên cùng một cấu hình: vốn khởi tạo $100.000$ USD, Top 20 mã, ngân sách tối đa $5\%$ NAV/mã (tự cân đối phí mua), trượt giá $5\text{ bps}$/chiều, phí môi giới $5\text{ bps}$/chiều (tổng chi phí round-trip $20\text{ bps}$).

---

## 2. Kết Quả Tổng Hợp Lát Cắt 5 Phiên Thử Nghiệm

Dưới đây là kết quả thực thi của 3 mô hình trên chuỗi 5 phiên tín hiệu $T \in [2024-01-02 \to 2024-01-08]$ tương ứng 5 phiên thực thi $T+1 \in [2024-01-03 \to 2024-01-09]$:

| Mô hình | Vốn khởi tạo ($) | NAV Cuối ($) | Lợi nhuận PnL ($) | Tỷ suất tích lũy | Tổng phí trả ($) | Lệnh Mua Khớp | Lệnh Mua Hủy | Lệnh Bán Khớp | Vị thế Kẹt Qua Đêm |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ridge ($\alpha=1.0$)** | 100,000.00 | **102,496.42** | **+2,496.42** | **+2.496%** | 501.17 | 100 / 100 | 0 | 100 / 100 | 0 |
| **GBDT (7 lá)** | 100,000.00 | **101,546.63** | **+1,546.63** | **+1.547%** | 498.29 | 100 / 100 | 0 | 100 / 100 | 0 |
| **ret_20d (Benchmark)** | 100,000.00 | **99,220.21** | **-779.79** | **-0.780%** | 490.02 | 100 / 100 | 0 | 100 / 100 | 0 |

### Nhận xét sơ bộ:
- **Khả năng sinh lời**: Cả hai mô hình Machine Learning đều tạo ra tỷ suất dương vượt trội so với Benchmark động lượng 20 ngày (`ret_20d`). Trong 5 phiên này, Ridge dẫn đầu với mức lợi nhuận $+2,496.42$ USD ($+2.496\%$), tiếp theo là GBDT với $+1,546.63$ USD ($+1.547\%$). Trong khi đó, chiến lược mua đuổi mã có đà tăng 20 ngày cao nhất (`ret_20d`) bị sụt giảm $-0.780\%$.
- **Ma sát giao dịch**: Chi phí giao dịch (phí môi giới + phí Sở) xấp xỉ $\sim 500$ USD cho mỗi mô hình qua 5 phiên (trung bình $\sim 100$ USD/phiên, tương đương $0.10\%$ NAV/phiên), khớp chính xác với thiết kế phí tự cân đối trong ngân sách ($5\text{ bps}$ mua + $5\text{ bps}$ bán trên $100\%$ NAV).
- **Thực thi lệnh**: Trong 5 phiên đầu này, toàn bộ 20 mã được chọn mỗi ngày của cả 3 mô hình đều có giá Open/Close hợp lệ, thanh khoản dồi dào ($V > 0$) và không có cờ dữ liệu lỗi. Tỷ lệ khớp lệnh đạt $100\%$ (100 mua, 100 bán, 0 kẹt qua đêm).

---

## 3. Trích Lục Sổ Cái Hằng Ngày (Daily Ledger)

### 3.1. Sổ cái Ridge ($\alpha=1.0$)
| Ngày giao dịch | Tiền mặt đầu ngày ($) | Tiền mặt cuối ngày ($) | Giá trị cổ phiếu (MtM) | NAV ($) | Lợi suất ngày | Lệnh Mua | Lệnh Bán | Phí giao dịch ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2024-01-03** | 100,000.00 | 98,989.38 | 0.00 | 98,989.38 | -1.011% | 20 | 20 | 99.49 |
| **2024-01-04** | 98,989.38 | 99,379.35 | 0.00 | 99,379.35 | +0.394% | 20 | 20 | 99.18 |
| **2024-01-05** | 99,379.35 | 99,763.34 | 0.00 | 99,763.34 | +0.386% | 20 | 20 | 99.57 |
| **2024-01-08** | 99,763.34 | 101,784.96 | 0.00 | 101,784.96 | +2.026% | 20 | 20 | 100.77 |
| **2024-01-09** | 101,784.96 | 102,496.42 | 0.00 | 102,496.42 | +0.699% | 20 | 20 | 102.14 |

### 3.2. Sổ cái GBDT (7 leaves)
| Ngày giao dịch | Tiền mặt đầu ngày ($) | Tiền mặt cuối ngày ($) | Giá trị cổ phiếu (MtM) | NAV ($) | Lợi suất ngày | Lệnh Mua | Lệnh Bán | Phí giao dịch ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2024-01-03** | 100,000.00 | 98,701.58 | 0.00 | 98,701.58 | -1.298% | 20 | 20 | 99.35 |
| **2024-01-04** | 98,701.58 | 99,014.71 | 0.00 | 99,014.71 | +0.317% | 20 | 20 | 98.86 |
| **2024-01-05** | 99,014.71 | 99,043.96 | 0.00 | 99,043.96 | +0.030% | 20 | 20 | 99.03 |
| **2024-01-08** | 99,043.96 | 100,751.78 | 0.00 | 100,751.78 | +1.724% | 20 | 20 | 99.90 |
| **2024-01-09** | 100,751.78 | 101,546.63 | 0.00 | 101,546.63 | +0.789% | 20 | 20 | 101.15 |

### 3.3. Sổ cái ret_20d (Benchmark)
| Ngày giao dịch | Tiền mặt đầu ngày ($) | Tiền mặt cuối ngày ($) | Giá trị cổ phiếu (MtM) | NAV ($) | Lợi suất ngày | Lệnh Mua | Lệnh Bán | Phí giao dịch ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2024-01-03** | 100,000.00 | 97,379.84 | 0.00 | 97,379.84 | -2.620% | 20 | 20 | 98.69 |
| **2024-01-04** | 97,379.84 | 96,631.52 | 0.00 | 96,631.52 | -0.768% | 20 | 20 | 97.01 |
| **2024-01-05** | 96,631.52 | 97,209.38 | 0.00 | 97,209.38 | +0.598% | 20 | 20 | 96.92 |
| **2024-01-08** | 97,209.38 | 99,194.12 | 0.00 | 99,194.12 | +2.042% | 20 | 20 | 98.20 |
| **2024-01-09** | 99,194.12 | 99,220.21 | 0.00 | 99,220.21 | +0.026% | 20 | 20 | 99.21 |

---

## 4. Danh Sách Top 20 Đại Diện Tại $T=2024-01-02$

Bảng dưới đây trích xuất Top 10 mã cổ phiếu được xếp hạng cao nhất của từng mô hình tại thời điểm đóng cửa phiên đầu tiên của năm 2024 (`2024-01-02`), trước khi gửi lệnh vào đầu phiên `2024-01-03`:

| Hạng | Ridge ($\alpha=1.0$) [Điểm] | GBDT (7 lá) [Điểm] | ret_20d [Lợi suất 20d] |
| :---: | :--- | :--- | :--- |
| **#1** | `EDA TGRALZT9E5ID` (0.5156) | `CLHB R735QTJ8XC9X` (0.5284) | `W VUE7AQ4QYD0L` (+51.78%) |
| **#2** | `COIN XNNJXSXHIHYD` (0.5136) | `DEAC X5UJWXSLPCH1` (0.5273) | `AFRM XL5Y9AN4JUCL` (+46.81%) |
| **#3** | `GSAH WWLQTC5JUC85` (0.5123) | `GSAH WWLQTC5JUC85` (0.5249) | `GSAH WWLQTC5JUC85` (+44.07%) |
| **#4** | `DEAC X5UJWXSLPCH1` (0.5117) | `DV XNUG2GHO1S2T` (0.5229) | `COIN XNNJXSXHIHYD` (+43.59%) |
| **#5** | `SZI SYLHRWX6L6XX` (0.5096) | `PLTR XIAKBH8EIMHX` (0.5215) | `CVNA XIJFFUAB5L35` (+42.92%) |
| **#6** | `RCL R735QTJ8XC9X` (0.5089) | `MANH RA4GD74ZF339` (0.5210) | `DEAC X5UJWXSLPCH1` (+41.01%) |
| **#7** | `NVDA RHM8UTD8DT2D` (0.5082) | `PEGA R735QTJ8XC9X` (0.5204) | `SZI SYLHRWX6L6XX` (+39.46%) |
| **#8** | `FB V6OIPNZEM8V9` (0.5079) | `OLLI W28SLK46WW2T` (0.5201) | `BLD W1U0W5MNRKO5` (+38.74%) |
| **#9** | `W VUE7AQ4QYD0L` (0.5077) | `CRWD X59VIZ423I3P` (0.5186) | `HOOD X45R56D08R0H` (+38.56%) |
| **#10**| `MANH RA4GD74ZF339` (0.5075) | `SZI SYLHRWX6L6XX` (0.5180) | `RCL R735QTJ8XC9X` (+37.89%) |

*(Toàn bộ danh sách 20 mã của cả 5 ngày tín hiệu được lưu đầy đủ tại [`outputs/reports/backtest_trial_slice/top20_candidates_trial_slice.csv`](../../../outputs/reports/backtest_trial_slice/top20_candidates_trial_slice.csv)).*

---

## 5. Trích Lục Mẫu Sổ Lệnh (Trade Execution Log)

Dưới đây là một phần sổ lệnh thực tế trong phiên `2024-01-03` của mô hình **Ridge ($\alpha=1.0$)**, thể hiện rõ cơ chế tự cân đối ngân sách mua ($5.000$ USD/mã), trượt giá thực hiện và phí hoa hồng:

| Thời điểm | Mã SID | Lệnh | Timing | Giá thị trường | Giá khớp thực tế | Số cổ phiếu | Giá trị gộp ($) | Phí ($) | Tác động tiền mặt ($) | Ghi chú |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2024-01-03** | `EDA TGRALZT9E5ID` | `BUY` | OPEN | 38.09 | 38.1090 | 131.1369 | 4,997.50 | 2.50 | -5,000.00 | New position filled at Open |
| **2024-01-03** | `COIN XNNJXSXHIHYD` | `BUY` | OPEN | 146.00 | 146.0730 | 34.2124 | 4,997.50 | 2.50 | -5,000.00 | New position filled at Open |
| **2024-01-03** | `GSAH WWLQTC5JUC85` | `BUY` | OPEN | 45.00 | 45.0225 | 111.0001 | 4,997.50 | 2.50 | -5,000.00 | New position filled at Open |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| **2024-01-03** | `EDA TGRALZT9E5ID` | `SELL` | CLOSE | 37.60 | 37.5812 | 131.1369 | 4,928.28 | 2.46 | +4,925.82 | Intraday exit at Close |
| **2024-01-03** | `COIN XNNJXSXHIHYD` | `SELL` | CLOSE | 157.15 | 157.0714 | 34.2124 | 5,373.78 | 2.69 | +5,371.10 | Intraday exit at Close |
| **2024-01-03** | `GSAH WWLQTC5JUC85` | `SELL` | CLOSE | 43.85 | 43.8281 | 111.0001 | 4,864.92 | 2.43 | +4,862.48 | Intraday exit at Close |

---

## 6. Kết Quả Quét Toàn Bộ 711 Phiên OOS & Tình Huống Kẹt Thanh Khoản

Để chuẩn bị cho giai đoạn backtest dài hạn, hệ thống đã quét qua toàn bộ **711 phiên OOS (2024–2026)** đối với danh sách Top 20 của từng mô hình:

1. **Thống kê các phiên xuất hiện dị biệt thanh khoản / thiếu giá**:
   - **Ridge**: Ghi nhận **20 trường hợp** dị biệt trong 711 phiên ($\sim 0.14\%$ tổng số lệnh).
     - Tiêu biểu: Ngày `2024-01-23`, mã `SRC VA4L1G2O9B39` (xếp hạng #11) và `MRTX VIA09B2Z24X1` (xếp hạng #13) có giá Open hợp lệ, nhưng tại Close ghi nhận khối lượng $V = 0.0$ do cổ phiếu bị hoàn tất thâu tóm/sáp nhập hoặc halt bất ngờ trong phiên.
     - Ngày `2024-03-18`, mã `SPLK V5VYQYDIED7P` (xếp hạng #12) ghi nhận $V = 0.0$ tại Close do Cisco hoàn tất thương vụ mua lại Splunk.
   - **GBDT**: Ghi nhận **4 trường hợp** (ví dụ `PYCR`, `BERY`, `SEE`, `BLD` có $V=0$ tại Close).
   - **ret_20d**: Ghi nhận **1 trường hợp** (mã `X` US Steel vào `2025-06-18`).
2. **Khẳng định tính đúng đắn của State Machine đa phiên**:
   Kết quả quét thực tế trên chứng minh rằng: **Các trường hợp cổ phiếu bị halt giữa phiên khiến lệnh bán MOC tại Close không khớp là hiện tượng có thật trên thị trường chứng khoán**. Nhờ cơ chế `HELD_OVERNIGHT` và thanh lý ưu tiên tại `Open` ngày hôm sau, mô phỏng phản ánh trung thực thực tế giao dịch, không bị sập lỗi (crash) hay bỏ qua khoản vốn bị giam cầm.

---

## 7. Cơ Chế Xử Lý Corporate Actions Cho Vị Thế Giữ Qua Đêm

Khi một vị thế buộc phải giữ qua đêm (`HELD_OVERNIGHT`) từ phiên $T+1$ sang $T+2$, hệ thống áp dụng các quy chuẩn hạch toán tài chính sau nếu ngày $T+2$ là ngày giao dịch không hưởng quyền ($T_{\text{ex}}$):

### 7.1. Chia tách và Gộp cổ phiếu (Stock Splits & Reverse Splits)
- Hệ số chia tách hiệu lực vào phiên $T+2$:
  $$S = \frac{CF_{T+1}}{CF_{T+2}}$$
  *(trong đó $CF$ là Cumulative Split Factor lấy từ `cumulative_split_factor.parquet`).*
- Số lượng cổ phiếu được điều chỉnh:
  $$Q_{T+2} = Q_{T+1} \times S$$
- Giá vốn bình quân và giá tham chiếu được điều chỉnh tương ứng:
  $$P_{T+2}^{\text{cost}} = \frac{P_{T+1}^{\text{cost}}}{S}, \quad P_{T+2}^{\text{last}} = \frac{P_{T+1}^{\text{last}}}{S}$$
- **Bảo toàn Mark-to-Market**: Tổng giá trị vị thế $Q_{T+2} \times P_{T+2}^{\text{last}} = Q_{T+1} \times P_{T+1}^{\text{last}}$, ngăn ngừa hiện tượng NAV biến động ảo do điều chỉnh kỹ thuật của sàn.
- Ghi log bản ghi `SPLIT_ADJUSTMENT` trong sổ lệnh.

### 7.2. Cổ tức bằng tiền mặt (Cash Dividends)
- Mức cổ tức trên mỗi cổ phần $D_{T+2}$ được xác định từ ma trận cổ tức (`adj_dividend.parquet` chia cho $CF_{T+2}$).
- Do vị thế đã được mua ở $T+1$ (trước ngày $T_{\text{ex}}$) và nắm giữ qua đêm, nhà đầu tư có tên trong danh sách cổ đông hưởng quyền:
  $$\text{Cash}_{\text{dividend}} = Q_{T+1} \times D_{T+2}$$
- Tiền mặt cổ tức được cộng trực tiếp vào số dư tiền mặt khả dụng của tài khoản (`self.cash += cash_dividend`).
- Ghi log bản ghi `DIVIDEND_PAYOUT` trong sổ lệnh với `cash_impact = + cash_dividend`.

### 7.3. Kiểm thử tự động (Unit Test Verification)
Toàn bộ logic chia tách và cổ tức tiền mặt cho vị thế qua đêm đã được kiểm chứng độc lập thông qua test case tự động [`test_case_4_carried_position_with_split_and_dividend`](../../../tests/test_backtest_simulator.py), đạt độ chính xác số học máy tính ($100\%$ pass, sai số $< 10^{-7}$).

---

## 8. Kết Luận & Điểm Dừng Nghiệm Thu

Lát cắt thử nghiệm 5 phiên đã xác nhận:
1. Động cơ mô phỏng danh mục [`PortfolioSimulator`](../../../src/backtest/simulator.py) hoạt động ổn định, chính xác về số học và tuân thủ chặt chẽ các nguyên tắc chống rò rỉ dữ liệu.
2. Quy tắc tự cân đối ngân sách mua đảm bảo tài khoản không phát sinh đòn bẩy ngầm.
3. Quy tắc cấm chọn mã thay thế và theo dõi vị thế qua đêm hoạt động đúng theo thiết kế đặc tả [backtest_plan_v1.md](../../specifications/backtest_plan_v1.md).

> [!IMPORTANT]
> **Giới hạn phương pháp luận (Post-hoc Simulation Caveat)**:
> Bộ quy tắc giao dịch này được thiết kế sau khi đã quan sát kết quả Rank IC OOS. Kết quả thực thi mô phỏng này mang ý nghĩa minh họa khả năng khai thác alpha và kiểm soát ma sát giao dịch, không thay thế cho kiểm định mù trước khi mở dữ liệu OOS.

**Điểm dừng**: Hệ thống dừng lại tại đây để người dùng duyệt sổ lệnh, sổ cái và phương pháp hạch toán trước khi tiến hành backtest toàn bộ 711 phiên OOS.
