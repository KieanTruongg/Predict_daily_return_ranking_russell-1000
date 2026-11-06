# Báo cáo pilot 16 features v1

Trạng thái ngày 2026-11-06: **ĐÃ HOÀN TẤT KIỂM THỬ ĐỢT 1 (5 FEATURES) VÀ ĐỢT 2 (11 FEATURES) — TOÀN BỘ 16 FEATURES V1 ĐẠT CHUẨN**.  
Bộ kiểm thử hồi quy tự động:
- **Chế độ kiểm thử di động (Portable, không nạp dữ liệu đĩa Tier 2)**: **41/41 tests PASSED** (`python -m pytest -m "not integration" -q`, 18 deselected, thời gian chạy **1.15s**).
- **Chế độ kiểm thử toàn diện (Full local, gồm kiểm thử tích hợp trên ma trận thật)**: **59/59 tests PASSED** (`python -m pytest -q`, gồm 21 tests pipeline integrity, 17 tests matrix-loader, và 21 tests pilot features).
- **Script kiểm thử thực nghiệm pilot**: **32/32 bài kiểm tra PASSED** (22 synthetic benchmarks S01–S23 và 10 empirical checks E01–E09).

Tham chiếu: [đặc tả features](../specifications/features_v1.md), [target/timing](../specifications/target_and_timing_v1.md), [quy ước artifact](feature_pilot/README.md).

---

## 1. Phạm vi lần chạy

- **Mã lần chạy (Run ID)**: `PILOT_FULL16_20261106`
- **Thời gian thực hiện**: 2026-11-06
- **Môi trường thực thi**: Python 3.14 (Windows PowerShell, UTF-8 reconfigured)
- **Lệnh thực thi chuẩn**:
  ```powershell
  # Chạy script kiểm thử số học và độ phủ 16 features
  python scripts/01_pipeline/11_feature_engineering_pilot.py

  # Chạy kiểm thử di động (không yêu cầu dữ liệu đĩa Tier 2)
  python -m pytest -m "not integration" -q

  # Chạy toàn bộ test suite cục bộ (bao gồm kiểm thử tích hợp dữ liệu thật)
  python -m pytest -q
  ```
- **Nguồn dữ liệu & Version**: Kho ma trận Tier 2 chuẩn hóa tại `data/processed/matrices/` (`adj_close`, `close`, `high`, `low`, `open`, `volume`, `daily_return`, `bar_quality_mask`, `membership_mask`). Đánh giá trực tiếp trên `strict_membership_mask` (`load_layer1_mask(strict=True)`).
- **Phạm vi mẫu kiểm thử thực tế**: 10 mã Canonical SID đại diện giai đoạn Development 2000–2002 kèm Warm-up 1998–2000. Script kiểm tra nghiêm ngặt sự hiện diện của đủ 10/10 mã và dừng ngay lập tức (`sys.exit(1)`) nếu thiếu bất kỳ mã nào:
  1. `AAPL R735QTJ8XC9X`: Nhóm công nghệ lớn, sự kiện chia tách 2:1 ngày 2000-06-21.
  2. `MSFT R735QTJ8XC9X`: Chuỗi cơ sở chuẩn (benchmark baseline) liên tục; kiểm tra phân rã lợi suất trong ngày/qua đêm và đối chiếu số học biến động Parkinson.
  3. `A RPTMYV3VC57P` (Agilent Technologies): Cổ phiếu mới vào rổ Russell 1000 ngày 2000-07-01; đếm trực tiếp từ ma trận Tier 2 có đúng 126 phiên warm-up sạch (từ 2000-01-03 đến 2000-06-30), đủ điều kiện cho cửa sổ 20 ngày nhưng chưa đủ cho cửa sổ dài 252 ngày.
  4. `BF RVCJ9QZYSJMT` (Brown-Forman): Cổ phiếu vào rổ ngày 2000-07-01; đếm trực tiếp từ ma trận có 18 phiên warm-up sạch từ 2000-06-07 đến 2000-06-30 (thiếu lookback 20 ngày ở 2 phiên đầu).
  5. `KSU R735QTJ8XC9X` (Kansas City Southern): Sự kiện gián đoạn Spin-off tách Stilwell Financial ngày 2000-07-13 (`is_spinoff_discontinuity = True`).
  6. `CPTH RJF8CZIDFLNP` (Ciphergen Biosystems): Hiện tượng bất thường đình chỉ giao dịch tháng 02/2001 (`is_bad_data_period = True`).
  7. `JPM R735QTJ8XC9X`: Đại diện nhóm Tài chính (Financials).
  8. `XON R735QTJ8XC9X`: Đại diện nhóm Năng lượng (Exxon Mobil, mã canonical SID vĩnh viễn trong Lean; ticker XOM ánh xạ về XON).
  9. `JNJ R735QTJ8XC9X`: Đại diện nhóm Y tế (Healthcare).
  10. `WMT R735QTJ8XC9X`: Đại diện nhóm Bán lẻ / Tiêu dùng thiết yếu (Consumer Staples).
- **Nguyên tắc OOS**: Hoàn toàn không sử dụng dữ liệu Out-of-Sample (2024–2026) trong đợt kiểm thử pilot.

---

## 2. Trạng thái toàn bộ 16 features candidate v1

Tất cả 16 đặc trưng ứng viên trong danh mục `features_v1.md` đã được triển khai, kiểm thử đơn vị, kiểm thử tích hợp và nghiệm thu pilot đạt chuẩn 100%:

### Đợt 1: 5 Features đại diện
- [x] **`ret_20d`**: **ĐẠT (PASSED)** — Tỷ số giá qua 20 phiên, đối chiếu số học khớp công thức, từ chối giá trị `Inf`/âm, bảo toàn warm-up sạch, cô lập bar lỗi và spin-off.
- [x] **`vol_realized_20d`**: **ĐẠT (PASSED)** — Độ lệch chuẩn 20 phiên lợi suất ngày, đơn vị ngày chuẩn `ddof=1` không nhân $\sqrt{252}$, xử lý chuỗi phẳng ra 0.0, lan tỏa NaN khi thiếu phiên.
- [x] **`amihud_illiq_20d`**: **ĐẠT (PASSED)** — Tỷ số thanh khoản Amihud nhân hệ số $10^6$, kiểm tra độc lập $p > 0$ và $v > 0$, cô lập volume $\le 0$ ra NaN.
- [x] **`rsi_14d`**: **ĐẠT (PASSED)** — Chỉ báo RSI 14 ngày làm mượt Wilder chuẩn, quy ước chuỗi phẳng 50.0, cơ chế reset trạng thái và re-seed sau 14 deltas sạch hoạt động chính xác.
- [x] **`bollinger_pct_b_20d`**: **ĐẠT (PASSED)** — Vị trí dải Bollinger chuẩn `ddof=0` cho độ lệch mức giá ($\sigma = 5.894913$ trong ca tính tay), xử lý $\sigma=0$ ra NaN, giữ nguyên giá trị ngoài $[0, 1]$ không clip.

### Đợt 2: 11 Features bổ sung theo 3 nhóm cấu trúc

#### Nhóm Momentum
- [x] **`ret_1d`**: **ĐẠT (PASSED)** — Tỷ số giá 1 phiên ($P[T]/P[T-1]-1$) trên `adj_close`. Khớp hình học, NaN khi thiếu phiên hoặc bar bẩn.
- [x] **`ret_5d`**: **ĐẠT (PASSED)** — Tỷ số giá 5 phiên ($P[T]/P[T-5]-1$). Đòi hỏi đủ 6 mức giá sạch liên tiếp.
- [x] **`ret_60d`**: **ĐẠT (PASSED)** — Lũy kế lợi suất trung hạn 60 phiên ($P[T]/P[T-60]-1$). Đòi hỏi 61 mức giá sạch liên tiếp.
- [x] **`mom_12m_skip_1m`**: **ĐẠT (PASSED)** — Momentum 12 tháng bỏ tháng gần nhất ($P[T-21]/P[T-252]-1$). Đòi hỏi 232 mức giá sạch trên đoạn $[T-252, T-21]$, hoàn toàn không bị ảnh hưởng bởi biến động hoặc bar lỗi trong khoảng 21 phiên gần nhất ($T-20 \dots T$).

#### Nhóm Volatility
- [x] **`vol_realized_60d`**: **ĐẠT (PASSED)** — Độ lệch chuẩn 60 phiên lợi suất ngày, `ddof=1`, đơn vị ngày (không nhân $\sqrt{252}$).
- [x] **`vol_parkinson_20d`**: **ĐẠT (PASSED)** — Biến động Parkinson từ biên độ giá High/Low: $\sqrt{\text{mean}_{20}(\ln(H/L)^2 / (4 \ln 2))}$. Kiểm tra nghiêm ngặt điều kiện hình học $H \ge L > 0$ và hữu hạn trên từng bar. Đối chiếu số học độc lập với nến thực tế MSFT đạt sai số $1.04 \times 10^{-17} \le 10^{-7}$.
- [x] **`downside_deviation_20d`**: **ĐẠT (PASSED)** — Độ lệch giảm 20 phiên: $\sqrt{\text{mean}_{20}(\min(daily\_return, 0)^2)}$. Chuẩn hóa ngưỡng 0.0, mẫu số cố định 20 phiên, không trừ kỳ vọng và không dùng $\text{ddof}=1$.

#### Nhóm Volume và Intraday
- [x] **`volume_ratio_5_20`**: **ĐẠT (PASSED)** — Tỷ số khối lượng ngắn hạn trên dài hạn: $\text{mean}_5(adj\_volume) / \text{mean}_{20}(adj\_volume)$. Xử lý mẫu số bằng 0 thành NaN.
- [x] **`log_dollar_volume_20d`**: **ĐẠT (PASSED)** — Quy mô thanh khoản USD: $\ln(1 + \text{mean}_{20}(raw\_close \times raw\_volume))$. Sử dụng giá và khối lượng thô chưa điều chỉnh.
- [x] **`ret_intraday`**: **ĐẠT (PASSED)** — Lợi suất trong phiên: $adj\_close / adj\_open - 1$. Chỉ phụ thuộc vào bar giao dịch tại ngày $T$.
- [x] **`ret_overnight`**: **ĐẠT (PASSED)** — Lợi suất qua đêm giữa giá đóng cửa hôm trước và mở cửa hôm nay: $adj\_open[T] / adj\_close[T-1] - 1$. Nghiệm chứng đẳng thức phân rã với $ret\_1d$.

---

## 3. Đối chiếu số học (Lớp 1: Synthetic Benchmarks)

Chi tiết toàn bộ kết quả đối chiếu số học lưu tại tệp [`docs/reports/feature_pilot/numerical_checks.csv`](feature_pilot/numerical_checks.csv). Dưới đây là phân tích chi tiết cho 22 ca kiểm thử tổng hợp (S01 đến S23):

### 3.1. Nhóm Đợt 1 (5 features đại diện)

#### `ret_20d` (Price Ratio Momentum)
- **Kiểm tra**: Tính lũy kế tỷ số giá qua 20 phiên giao dịch $P[T] / P[T-20] - 1$ trên `adj_close`.
- **Dữ liệu & Case**:
  - `CASE_S01_RET20_GEOMETRIC`: Chuỗi hình học $P_t = 100 \times (1.01)^t$.
  - `CASE_S02_RET20_FLAT`: Chuỗi giá phẳng $P_t = 100.0$.
  - `CASE_S03_RET20_DIRTY_BAR_NAN` & `CASE_S03B_RET20_DIRTY_RECOVERY`: Nến bẩn tại $t=10$.
  - `CASE_S14_RET_NON_FINITE_PRICE_NAN`: Chuỗi giá chứa giá trị không hữu hạn $[100.0, \text{Inf}, 110.0]$ với cửa sổ 2 ngày.
- **Tham chiếu tính tay**:
  - Hình học: $(1.01)^{20} - 1.0 = 0.22019003994796704$.
  - Bar lỗi: Giá trị không hợp lệ làm toàn bộ cửa sổ chứa nó thành `NaN`. Phục hồi tại $t=31$: $(100 \times 1.01^{31}) / (100 \times 1.01^{11}) - 1 = 1.01^{20} - 1 = 0.18018018$.
- **Expected / Actual**:
  - S01: Expected = `0.22019004`, Actual = `0.22019004`, Sai số = `0.00e+00` (Dung sai $10^{-7}$).
  - S02: Expected = `0.00000000`, Actual = `0.00000000`, Sai số = `0.00e+00`.
  - S03: Tại $t=20$ $\to$ `NaN` (Pass). Tại $t=31$ $\to$ Expected = `0.18018018`, Actual = `0.18018018`, Sai số = `0.00e+00`.
  - S14: Expected = `NaN`, Actual = `NaN` (Pass).
- **Trạng thái**: **PASSED**.

#### `vol_realized_20d` (Realized Volatility)
- **Kiểm tra**: Độ lệch chuẩn mẫu của 20 phiên lợi suất liên tiếp $\text{std}(daily\_return, W=20, \text{ddof}=1)$, đơn vị ngày (không nhân $\sqrt{252}$).
- **Dữ liệu & Case**:
  - `CASE_S04_VOL20_ALTERNATING`: 20 lợi suất đan xen $[+0.01, -0.01, +0.01, \dots]$.
- **Tham chiếu tính tay**:
  - Phương sai mẫu: $20 \times (0.01)^2 / 19 = 0.00010526315789473685$.
  - Độ lệch chuẩn mẫu: $\sqrt{0.00010526315789473685} = 0.01025978352085154$.
- **Expected / Actual**:
  - S04: Expected = `0.01025978`, Actual = `0.01025978`, Sai số tuyệt đối = `1.73e-18` (Dung sai $10^{-7}$).
- **Trạng thái**: **PASSED**.

#### `amihud_illiq_20d` (Amihud Illiquidity Ratio)
- **Kiểm tra**: Tỷ số thanh khoản Amihud $10^6 \times \text{mean}_{20}(|daily\_return| / (raw\_close \times raw\_volume))$.
- **Dữ liệu & Case**:
  - `CASE_S06_AMIHUD_CONSTANT`: $r = 0.01, P = 100.0, V = 10,000$ (Dollar Volume = $1,000,000$).
  - `CASE_S15_AMIHUD_NEGATIVE_PRICE_VOL_NAN`: Nến có giá âm và volume âm ($p = -10, v = -100$), tích $p \times v = 1,000 > 0$.
- **Tham chiếu tính tay**:
  - Tỷ số mỗi ngày: $|0.01| / 10^6 = 10^{-8}$. Nhân hệ số tỷ lệ: $10^6 \times 10^{-8} = 0.01$.
  - Kiểm tra độc lập từng biến: Bar có $p \le 0$ hoặc $v \le 0$ phải bị loại bỏ dù tích dương $\to$ toàn bộ cửa sổ thành `NaN`.
- **Expected / Actual**:
  - S06: Expected = `0.01000000`, Actual = `0.01000000`, Sai số = `0.00e+00` (Dung sai $10^{-7}$).
  - S15: Expected = `NaN`, Actual = `NaN` (Pass).
- **Trạng thái**: **PASSED**.

#### `rsi_14d` (Relative Strength Index)
- **Kiểm tra**: RSI 14 ngày làm mượt Wilder và cơ chế reset trạng thái khi gặp bar lỗi.
- **Dữ liệu & Case**:
  - `CASE_S08_RSI_ALL_GAIN`: 14 delta dương liên tiếp (toàn tăng).
  - `CASE_S09_RSI_FLAT_SERIES`: Giá không đổi qua 15 phiên (chuỗi phẳng).
- **Tham chiếu tính tay**:
  - Toàn tăng: AvgLoss = 0 $\implies$ RSI = 100.0.
  - Chuỗi phẳng: AvgLoss = 0, AvgGain = 0 $\implies$ Quy ước chuẩn = 50.0.
- **Expected / Actual**:
  - S08: Expected = `100.0000`, Actual = `100.0000`, Sai số = `0.00e+00` (Dung sai $10^{-6}$).
  - S09: Expected = `50.0000`, Actual = `50.0000`, Sai số = `0.00e+00`.
- **Trạng thái**: **PASSED**.

#### `bollinger_pct_b_20d` (Bollinger Bands %B)
- **Kiểm tra**: Vị trí dải Bollinger $(adj\_close - lower) / (upper - lower)$ với $\text{ddof}=0$ cho $\sigma$.
- **Dữ liệu & Case**:
  - `CASE_S12_BOLLINGER_EXACT_FORMULA`: Mẫu 20 mức giá tính tay ($10 \times 95.0, 9 \times 105.0, 1 \times 115.0$).
- **Tham chiếu tính tay**:
  - Trung bình: $\mu = 100.50$.
  - Độ lệch chuẩn $\text{ddof}=0$: $\sigma = \sqrt{34.75} \approx 5.89491306$.
  - Dải Bollinger: $lower = 88.71017388$, $upper = 112.28982612$, bề rộng $23.57965224$.
  - $\%B = (115.0 - 88.71017388) / 23.57965224 \approx 1.11493697$.
- **Expected / Actual**:
  - S12: Expected = `1.11493697`, Actual = `1.11493697`, Sai số = `6.66e-16` (Dung sai $10^{-7}$).
- **Trạng thái**: **PASSED**.

#### Chuẩn hóa Target: Uniform Rank 3 Cổ phiếu
- **Kiểm tra**: `target_next_rank` chuẩn hóa phân vị đều trên rổ hợp lệ ngày $T+1$.
- **Dữ liệu & Case**:
  - `CASE_S13_UNIFORM_RANK_3STOCKS`: 3 cổ phiếu có lợi suất $[-0.02, 0.01, 0.03]$.
- **Tham chiếu tính tay**:
  - Phân vị đều: Mã A rank 0, Mã B rank $1/(3-1) = 0.5$, Mã C rank 1.0.
- **Expected / Actual**:
  - S13: Expected = `0.50000000`, Actual = `0.50000000`, Sai số = `0.00e+00`.
- **Trạng thái**: **PASSED**.

---

### 3.2. Nhóm Đợt 2 (11 features bổ sung)

#### Nhóm Momentum (`ret_1d`, `ret_5d`, `ret_60d`, `mom_12m_skip_1m`)
- **Dữ liệu & Case**:
  - `CASE_S16A_RET1D_GEOMETRIC`: Chuỗi hình học $P_t = 100 \times (1.01)^t$, cửa sổ 1 ngày.
    - Tham chiếu: $1.01^1 - 1 = 0.01000000$.
    - Expected = `0.01000000`, Actual = `0.01000000`, Sai số = `8.67e-18` (Dung sai $10^{-7}$).
  - `CASE_S16B_RET5D_GEOMETRIC`: Chuỗi hình học, cửa sổ 5 ngày.
    - Tham chiếu: $1.01^5 - 1 = 0.05101005010000015$.
    - Expected = `0.05101005`, Actual = `0.05101005`, Sai số = `0.00e+00`.
  - `CASE_S16C_RET60D_GEOMETRIC`: Chuỗi hình học, cửa sổ 60 ngày.
    - Tham chiếu: $1.01^{60} - 1 = 0.8166966985640913$.
    - Expected = `0.81669670`, Actual = `0.81669670`, Sai số = `0.00e+00`.
  - `CASE_S17A_MOM12M_SKIP1M_FORMULA`: Chuỗi giá tuyến tính từ 100 đến 380 qua 280 phiên.
    - Tham chiếu: Tại phiên 253, $T-21$ có giá $100 + 232 = 332.0$; $T-252$ có giá $100 + 1 = 101.0$.
    - Lợi suất: $332.0 / 101.0 - 1 = 231 / 101 = 2.138888888888889$.
    - Expected = `2.13888889`, Actual = `2.13888889`, Sai số = `0.00e+00`.
  - Kiểm tra tính độc lập của `mom_12m_skip_1m`: Thay đổi đột biến giá trong 21 phiên gần nhất ($T-20 \dots T$) hoàn toàn không làm thay đổi giá trị của feature tại ngày $T$.
- **Trạng thái**: **PASSED**.

#### Nhóm Volatility (`vol_realized_60d`, `vol_parkinson_20d`, `downside_deviation_20d`)
- **Dữ liệu & Case**:
  - `CASE_S18_VOL60_ALTERNATING`: 60 lợi suất đan xen $[+0.01, -0.01, \dots]$.
    - Tham chiếu: Phương sai mẫu: $60 \times (0.01)^2 / 59 = 0.006 / 59$.
    - Độ lệch chuẩn: $\sqrt{0.006 / 59} = 0.010084389681792216$.
    - Expected = `0.01008439`, Actual = `0.01008439`, Sai số = `1.73e-18`.
  - `CASE_S19_PARKINSON_RATIO_1_02`: 20 nến đồng dạng có $High = 102.0, Low = 100.0$.
    - Tham chiếu: Tỷ số $\ln(H/L) = \ln(1.02) = 0.019802627296$.
    - Bình phương: $(0.019802627296)^2 = 0.0003921440478$.
    - Chia $4 \ln 2$: $0.0003921440478 / (4 \times 0.69314718) = 0.0001414360677$.
    - Căn bậc hai: $\sqrt{0.0001414360677} = 0.011892689699143848$.
    - Expected = `0.01189269`, Actual = `0.01189269`, Sai số = `0.00e+00`.
  - `CASE_S20_DOWNSIDE_DEV_FORMULA`: 20 phiên gồm 10 phiên giảm $-0.02$ và 10 phiên tăng $+0.02$.
    - Tham chiếu: Các phiên tăng bị kẹp về 0 ($\min(r, 0) = 0$). Các phiên giảm có bình phương $(-0.02)^2 = 0.0004$.
    - Tổng bình phương: $10 \times 0.0004 = 0.004$.
    - Mẫu số cố định 20 phiên (không dùng $N-1$): Trung bình $= 0.004 / 20 = 0.0002$.
    - Độ lệch giảm: $\sqrt{0.0002} = 0.01414213562373095$.
    - Expected = `0.01414214`, Actual = `0.01414214`, Sai số = `0.00e+00`.
- **Trạng thái**: **PASSED**.

#### Nhóm Volume và Intraday (`volume_ratio_5_20`, `log_dollar_volume_20d`, `ret_intraday`, `ret_overnight`)
- **Dữ liệu & Case**:
  - `CASE_S21_VOLUME_RATIO_FORMULA`: 5 phiên gần nhất có $V = 20,000$, 15 phiên trước đó có $V = 10,000$.
    - Tham chiếu: $\text{mean}_5 = 20,000$; $\text{mean}_{20} = (5 \times 20,000 + 15 \times 10,000) / 20 = 12,500$.
    - Tỷ số: $20,000 / 12,500 = 1.60000000$.
    - Expected = `1.60000000`, Actual = `1.60000000`, Sai số = `0.00e+00`.
  - `CASE_S22_LOG_DOLLAR_VOL_FORMULA`: 20 phiên đều có $Close = 100.0, Volume = 10,000$.
    - Tham chiếu: Dollar Volume $= 1,000,000$ USD.
    - $\ln(1 + 1,000,000) = 13.815511557963774$.
    - Expected = `13.81551156`, Actual = `13.81551156`, Sai số = `0.00e+00`.
  - `CASE_S23A_RETR_INTRADAY_FORMULA`: $adj\_close = 105.0, adj\_open = 102.0$.
    - Tham chiếu: $105.0 / 102.0 - 1 = 3.0 / 102.0 = 0.02941176470588225$.
    - Expected = `0.02941176`, Actual = `0.02941176`, Sai số = `0.00e+00`.
  - `CASE_S23B_RETR_OVERNIGHT_FORMULA`: $adj\_open[T] = 102.0, adj\_close[T-1] = 100.0$.
    - Tham chiếu: $102.0 / 100.0 - 1 = 0.020000000000000018$.
    - Expected = `0.02000000`, Actual = `0.02000000`, Sai số = `0.00e+00`.
  - **Đẳng thức phân rã hình học**:
    $$(1 + ret\_overnight) \times (1 + ret\_intraday) - 1 = (102/100) \times (105/102) - 1 = 105/100 - 1 = 0.05 = ret\_1d$$
    Đẳng thức được bảo toàn tuyệt đối đến giới hạn số học dấu phẩy động.
- **Trạng thái**: **PASSED**.

---

## 4. Dữ liệu thực và các ca biên (Lớp 2: Empirical Development Slice)

Kiểm thử được tiến hành trên 10 mã đại diện qua giai đoạn 2000–2002 của tập Development:

| Case ID | Canonical SID & Ticker | Tình huống thực nghiệm | Kết quả kiểm chứng thực tế | Trạng thái |
|---|---|---|---|:---:|
| **CASE_E01** | `A RPTMYV3VC57P`<br>(Agilent Technologies) | **Bảo toàn Warm-up ngày đầu vào rổ**: Gia nhập Russell 1000 ngày 2000-07-01; đếm trực tiếp từ ma trận có 126 phiên warm-up sạch từ 2000-01-03 đến 2000-06-30. | Tại phiên đầu tiên 2000-07-03, tính toán thành công cả 5 features Đợt 1:<br>• `ret_20d` = **-0.045378**<br>• `vol_realized_20d` = **0.054711**<br>• `rsi_14d` = **49.32**<br>• `bollinger_pct_b_20d` = **0.3842**<br>• `amihud_illiq_20d` = **0.0051** | **PASSED** |
| **CASE_E02** | `BF RVCJ9QZYSJMT`<br>(Brown-Forman) | **Thiếu lịch sử Warm-up (< 20 phiên)**: Vào rổ ngày 2000-07-01; đếm trực tiếp từ ma trận có 18 phiên warm-up sạch từ 2000-06-07 đến 2000-06-30. | Tại phiên 2000-07-03 và 2000-07-05 (2000-07-04 là ngày lễ Độc Lập) $\to$ đúng **2 phiên NaN** do chưa đủ 21 giá. Đến phiên thứ 3 (2000-07-06, phiên thứ 21) $\to$ tính được giá trị **-0.075330**. | **PASSED** |
| **CASE_E03** | `KSU R735QTJ8XC9X`<br>(Kansas City Southern) | **Lan tỏa NaN qua sự kiện Spin-off**: Ngày 2000-07-13 tách Stilwell Financial (`is_spinoff_discontinuity = True`). | Cửa sổ trượt 20 phiên đi qua ngày này trả về **đúng 21 phiên NaN** (từ 2000-07-13 đến 2000-08-10). Đến ngày 2000-08-11 (sau khi bar lỗi thoát cửa sổ) $\to$ phục hồi tính toán bình thường (**-0.036337**). | **PASSED** |
| **CASE_E04A** | `AAPL R735QTJ8XC9X`<br>(Apple Inc.) | **Kiểm tra nhất quán nội bộ (Internal Pipeline Consistency)**: Kiểm tra ngày chia tách 2000-06-21. | So sánh với công thức kết hợp giá thô và hệ số chia tách tích lũy trong kho Tier 2 ($s_T / s_{T-1} = 0.0178571 / 0.00892857 \approx 1.99999552$).<br>Lợi suất kỳ vọng từ công thức nội bộ: $(55.56 \times 1.99999552 / 101.0) - 1 = \mathbf{0.100195555358}$.<br>Khớp ma trận `daily_return` với sai số $< \mathbf{10^{-12}}$ (Machine Epsilon). | **PASSED** |
| **CASE_E04B** | `AAPL R735QTJ8XC9X`<br>(Apple Inc.) | **So sánh với tham chiếu lý tưởng lý thuyết (Theoretical Ideal Reference Comparison)**: So sánh với tỷ lệ chia tách 2:1 nguyên số ($factor = 2.0$). | Lợi suất lý tưởng với hệ số $2.0$: $(55.56 \times 2.0 / 101.0) - 1 = \mathbf{0.1001980198}$.<br>Độ lệch giữa ma trận thực và tỷ lệ lý tưởng: $|\Delta| = \mathbf{2.4644 \times 10^{-6}} \le 10^{-5}$ do hệ số trong dữ liệu nguồn là $1.99999552$ (thay vì $2.00000000$). Ghi nhận khách quan sự khác biệt này giữa dữ liệu nguồn và lý thuyết, không khẳng định nguyên nhân kỹ thuật khi chưa có tài liệu đối chiếu chính thức. | **PASSED** |
| **CASE_E05** | `CPTH RJF8CZIDFLNP`<br>(Ciphergen Biosystems) | **Cách ly bất thường đình chỉ giao dịch**: Tháng 02/2001 dính cờ `is_bad_data_period = True` (CORR_013). | Toàn bộ các phiên trong khoảng đình chỉ đều trả về **NaN**, không gây ô nhiễm chuỗi rolling. | **PASSED** |
| **CASE_E06** | `A RPTMYV3VC57P` | **Mặt nạ thành viên đầu ra (Output Masking)**: Ngày 1999-12-01 có giá sạch nhưng chưa thuộc Russell 1000. | Giá trị đầu ra tại ngày 1999-12-01 trả về **NaN** do `membership_mask == False`, bảo đảm tính đóng gói Point-In-Time. | **PASSED** |
| **CASE_E07** | `A RPTMYV3VC57P`<br>(Agilent Technologies) | **Thiếu lookback dài hạn ở cổ phiếu mới và phục hồi**: Cần lưới lịch sử truy cập tới $T-252$, nhưng chỉ yêu cầu 232 giá sạch trong đoạn $[T-252, T-21]$ (không đòi hỏi toàn bộ 253 giá đều sạch). | Đếm trực tiếp từ ma trận: Ngày vào rổ 2000-07-03 Agilent mới có 127 phiên trong ma trận; đến hết năm 2000 (2000-12-29) có đúng 252 phiên, chưa thể có mốc dữ liệu $T-252$. Trả về đúng **126 phiên NaN** trong nửa cuối năm 2000 thuộc rổ Russell. Đạt phiên thứ 253 vào ngày 2001-01-02 (có đủ mốc $T-252$) và phục hồi tính toán bình thường (**-0.274655**). | **PASSED** |
| **CASE_E08** | `MSFT R735QTJ8XC9X`<br>(Microsoft Corp.) | **Nghiệm chứng đẳng thức phân rã lợi suất trên nến thực tế**: Phiên 2000-07-05. | Kiểm tra đẳng thức $(1 + r_{\text{over}}) \times (1 + r_{\text{intra}}) - 1 == r_{1d}$ trên dữ liệu thị trường thực tế của MSFT.<br>Expected: $-0.02039029$, Actual: $-0.02039029$. Sai số $= \mathbf{0.00e+00}$ ($< 10^{-12}$). | **PASSED** |
| **CASE_E09** | `MSFT R735QTJ8XC9X`<br>(Microsoft Corp.) | **Đối chiếu số học độc lập biến động Parkinson trên nến thực tế**: Phiên 2000-07-05. | Đối chiếu trực tiếp với công thức numpy tính từ 20 nến High/Low thực tế của MSFT:<br>• Expected (tính độc lập) = **0.0272414121414246**<br>• Actual (output feature) = **0.0272414121414246**<br>Sai số tuyệt đối $= \mathbf{1.04 \times 10^{-17}}$, thỏa mãn dung sai khắt khe $\le \mathbf{10^{-7}}$. | **PASSED** |

---

## 5. Coverage và phân tích cơ cấu NaN riêng từng feature

Thống kê độ phủ chi tiết được lưu trữ đầy đủ tại tệp [`docs/reports/feature_pilot/coverage_summary.csv`](feature_pilot/coverage_summary.csv).  
Phạm vi đánh giá: 10 mã đại diện trong giai đoạn Development (**2000-07-01 đến 2002-12-31**, tổng cộng 6.260 ô tọa độ; đánh giá trên `strict_membership_mask`):

| Nhóm | Đặc trưng | Tổng số ô | Ô thuộc Membership | Số ô hợp lệ (Valid) | Độ phủ (% Membership) | NaN ngoài Membership | NaN trong Membership (Do Quality / Lookback) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Intraday** | `ret_intraday` | 6.260 | 4.509 | **4.499** | **99.78%** | 1.751 | **10** |
| **Intraday** | `ret_overnight` | 6.260 | 4.509 | **4.497** | **99.73%** | 1.751 | **12** |
| **Momentum** | `ret_1d` | 6.260 | 4.509 | **4.497** | **99.73%** | 1.751 | **12** |
| **Momentum** | `ret_5d` | 6.260 | 4.509 | **4.489** | **99.56%** | 1.751 | **20** |
| **Technical** | `rsi_14d` | 6.260 | 4.509 | **4.471** | **99.16%** | 1.751 | **38** |
| **Technical** | `bollinger_pct_b_20d` | 6.260 | 4.509 | **4.460** | **98.91%** | 1.751 | **49** |
| **Volatility** | `vol_parkinson_20d` | 6.260 | 4.509 | **4.460** | **98.91%** | 1.751 | **49** |
| **Volume** | `volume_ratio_5_20` | 6.260 | 4.509 | **4.460** | **98.91%** | 1.751 | **49** |
| **Volume** | `log_dollar_volume_20d` | 6.260 | 4.509 | **4.460** | **98.91%** | 1.751 | **49** |
| **Volatility** | `vol_realized_20d` | 6.260 | 4.509 | **4.458** | **98.87%** | 1.751 | **51** |
| **Liquidity** | `amihud_illiq_20d` | 6.260 | 4.509 | **4.458** | **98.87%** | 1.751 | **51** |
| **Volatility** | `downside_deviation_20d`| 6.260 | 4.509 | **4.458** | **98.87%** | 1.751 | **51** |
| **Momentum** | `ret_20d` | 6.260 | 4.509 | **4.457** | **98.85%** | 1.751 | **52** |
| **Volatility** | `vol_realized_60d` | 6.260 | 4.509 | **4.338** | **96.21%** | 1.751 | **171** |
| **Momentum** | `ret_60d` | 6.260 | 4.509 | **4.337** | **96.19%** | 1.751 | **172** |
| **Momentum** | `mom_12m_skip_1m` | 6.260 | 4.509 | **3.844** | **85.25%** | 1.751 | **665** |

### Giải trình chi tiết cơ cấu NaN riêng biệt cho từng feature:

1. **NaN do ngoài Membership (1.751 ô - Cố định trên mọi feature)**:
   - Phát sinh hoàn toàn do thiết kế Point-In-Time: Đây là các tọa độ ngày của cổ phiếu khi chưa gia nhập rổ Russell 1000 (trước 2000-07-01 như Agilent, Brown-Forman) hoặc sau khi bị loại khỏi rổ (`membership_mask == False`).
2. **Cơ cấu NaN bên trong Membership (Do Quality, Lookback và Corporate Actions)**:
   - **`ret_intraday` (10 NaN, Độ phủ 99.78%)**: Chỉ yêu cầu 1 bar hợp lệ duy nhất tại ngày $T$. 10 phiên NaN này thuộc về đúng 10 phiên đình chỉ giao dịch nghiêm trọng của `CPTH` trong tháng 02/2001 (CORR_013), nơi không có giá khớp lệnh hợp lệ.
   - **`ret_1d` & `ret_overnight` (12 NaN, Độ phủ 99.73%)**: Đòi hỏi liên kết 2 phiên liên tiếp. Ngoài 10 phiên đình chỉ của CPTH, có thêm 2 phiên chuyển tiếp ngay sau khi phục hồi giao dịch.
   - **`ret_5d` (20 NaN, Độ phủ 99.56%)**: Cần 6 mức giá liên tiếp. Lan tỏa 5 phiên qua đoạn đình chỉ của CPTH và các ngày giao dịch đầu tiên sau khi niêm yết.
   - **Nhóm cửa sổ 20 ngày (`ret_20d`, `vol_realized_20d`, `amihud_illiq_20d`, `vol_parkinson_20d`, `bollinger_pct_b_20d`, `volume_ratio_5_20`, `log_dollar_volume_20d`, `downside_deviation_20d`)**:
     - Dao động từ **49 đến 52 NaN** (Độ phủ **98.85% – 98.91%**).
     - Gồm: **21 phiên** do sự kiện gián đoạn Spin-off của `KSU` (2000-07-13 đến 2000-08-10); **29 phiên** do chuỗi đình chỉ giao dịch của `CPTH`; và **1 đến 2 phiên** đầu tiên của `BF` do thiếu hụt lookback warm-up (mới có 18-20 phiên trên sàn).
     - Chênh lệch nhỏ giữa các feature (52 vs 51 vs 49) do `ret_20d` yêu cầu 21 giá ($P_T$ và $P_{T-20}$), trong khi `bollinger_pct_b_20d` và `vol_parkinson_20d` chỉ cần 20 điểm giá; `rsi_14d` (38 NaN) chỉ cần 14 deltas sạch nên tái khởi động (re-seed) nhanh hơn các feature 20 ngày.
   - **Nhóm cửa sổ trung hạn 60 ngày (`ret_60d`, `vol_realized_60d`)**:
     - Có **171 – 172 NaN** (Độ phủ **96.19% – 96.21%**).
     - Cửa sổ 60 ngày lan tỏa sự kiện spin-off của KSU và đình chỉ CPTH dài hơn (60 phiên liên tiếp), đồng thời đòi hỏi lượng warm-up trước ngày gia nhập nhiều hơn (61 phiên sạch).
   - **Đặc trưng dài hạn `mom_12m_skip_1m` (665 NaN, Độ phủ 85.25%)**:
     - Đòi hỏi lưới lịch sử truy cập tới $T-252$ (253 phiên trên lịch giao dịch chung) và 232 mức giá sạch trong khoảng $[T-252, T-21]$. Lưu ý: feature không đòi hỏi toàn bộ 253 giá trong $[T-252, T]$ đều sạch, vì các phiên từ $T-20$ đến $T$ được bỏ qua.
     - Mã `A RPTMYV3VC57P` (Agilent Technologies): Dữ liệu giá trong ma trận Tier 2 bắt đầu từ ngày 2000-01-03. Đếm trực tiếp từ ma trận, trước ngày gia nhập rổ (2000-06-30) có đúng 126 phiên sạch, và tính đến hết năm 2000 (2000-12-29) Agilent mới tích lũy được 252 phiên (chưa thể có mốc dữ liệu $T-252$). Do đó, Agilent có đúng 126 phiên NaN bên trong membership trong toàn bộ nửa cuối năm 2000 (từ 2000-07-03 đến 2000-12-29). Phục hồi hợp lệ tại phiên thứ 253 vào ngày 2001-01-02 (-0.274655).
     - Ngoài ra, sự kiện spin-off của KSU lan tỏa qua cửa sổ 252 ngày làm tăng số ô NaN. Đây là hành vi hoàn toàn tự nhiên và chuẩn xác về mặt kinh tế tài chính đối với các cổ phiếu mới niêm yết trong rổ.

---

## 6. Lỗi phát hiện, hoàn thiện và đối chiếu kỹ thuật

Trong quá trình triển khai và hoàn thiện cả 2 đợt pilot, hệ thống đã ghi nhận và hoàn tất 8 điểm kỹ thuật quan trọng:

1. **Phân định ranh giới giữa kiểm thử di động và kiểm thử tích hợp**:
   - Gắn tag `@pytest.mark.integration` cho các bài kiểm tra nạp dữ liệu ma trận thật từ đĩa (`test_09a`, `test_09b`, `test_10`, `test_10b`, `test_11`, `test_19`).
   - Cung cấp lệnh chạy di động chuẩn: `python -m pytest -m "not integration" -q` (chạy 41 tests tổng hợp trong 1.15 giây, có thể chạy trên mọi môi trường CI/CD không có dữ liệu Tier 2).
   - Cung cấp lệnh chạy tích hợp toàn diện: `python -m pytest -q` (chạy toàn bộ 59 tests).
2. **Tách biệt kiểm tra AAPL Split và loại bỏ kết luận suy diễn về nguồn**:
   - **Kiểm tra nhất quán nội bộ (Internal Pipeline Consistency)**: So sánh với công thức tính từ giá thô và hệ số chia tách trong kho Tier 2 ($s_T / s_{T-1} = 0.0178571 / 0.00892857 \approx 1.99999552$). Khớp với `daily_return` thực tế tới sai số dấu phẩy động $< 10^{-12}$.
   - **So sánh với tham chiếu lý tưởng (Theoretical Ideal Reference Comparison)**: So sánh với tỷ lệ nguyên số $2.0$. Khác biệt là $|\Delta| = 2.4644 \times 10^{-6} \le 10^{-5}$ do hệ số trong dữ liệu nguồn là $1.99999552$ (thay vì $2.00000000$).
   - **Thái độ khoa học khách quan**: Ghi nhận sự tồn tại của mức chênh lệch này giữa hệ số lưu trữ trong dữ liệu nguồn và tỷ lệ lý tưởng toán học; loại bỏ các khẳng định giả định về cơ chế làm tròn của nhà cung cấp khi chưa có tài liệu kiểm định độc lập.
3. **Đếm lịch sử nến trực tiếp từ ma trận thay vì ước tính từ sự kiện bên ngoài**:
   - Đối với Agilent (`A RPTMYV3VC57P`): Không suy diễn từ ngày IPO lý thuyết (1999-11-18), mà đếm trực tiếp trên ma trận Tier 2: có đúng 126 phiên warm-up sạch trước ngày vào rổ (2000-01-03 đến 2000-06-30); có đúng 252 phiên đến hết năm 2000; và đạt phiên thứ 253 vào ngày 2001-01-02.
   - Đối với Brown-Forman (`BF RVCJ9QZYSJMT`): Đếm trực tiếp có đúng 18 phiên warm-up sạch trước ngày vào rổ (2000-06-07 đến 2000-06-30).
4. **Đối chiếu số học độc lập với dung sai chặt chẽ cho biến động Parkinson (CASE_E09)**:
   - Tính toán giá trị kỳ vọng độc lập từ 20 nến High/Low thực tế của MSFT bằng công thức numpy trực tiếp: $\text{Expected} = 0.0272414121414246$.
   - Sai số so với output của feature là $1.04 \times 10^{-17}$, thỏa mãn dung sai khắt khe $\le 10^{-7}$.
5. **Kiểm tra tính hữu hạn và dương tính nghiêm ngặt**:
   - `PriceRatioMomentumFeature` và `TotalReturnMomentumFeature`: Kiểm tra `np.isfinite(p) & (p > 0)` nhằm loại bỏ triệt để `Inf`, `-Inf`, $\le 0$.
   - `AmihudIlliquidityFeature`: Kiểm tra độc lập từng biến `np.isfinite(p) & (p > 0)` và `np.isfinite(v) & (v > 0)`, ngăn chặn trường hợp cả giá và khối lượng cùng âm.
6. **Đặc tả chính xác cho nhóm Volatility và Volume**:
   - `DownsideDeviationFeature`: Chuẩn hóa với ngưỡng cố định 0.0, mẫu số cố định 20, không trừ trung bình mẫu, không dùng `ddof=1`.
   - `ParkinsonVolatilityFeature`: Kiểm tra $H \ge L > 0$ và hữu hạn trên từng bar, bảo đảm căn bậc hai luôn nhận đối số không âm.
   - `VolumeRatioFeature`: Xử lý trường hợp mẫu số $\text{mean}_{20} = 0$ trả về NaN.
7. **Bảo toàn đẳng thức phân rã lợi suất**:
   - Nghiệm chứng đẳng thức $(1 + ret\_overnight) \times (1 + ret\_intraday) - 1 == ret\_1d$ trên cả chuỗi nhân tạo và dữ liệu thực của MSFT.
8. **Độc lập cửa sổ của `mom_12m_skip_1m`**:
   - Feature yêu cầu 232 phiên sạch trên $[T-252, T-21]$ và hoàn toàn miễn nhiễm với biến động nến bẩn trong 21 phiên gần nhất ($T-20 \dots T$).

---

## 7. Kết luận và định hướng tiếp theo

1. **Nghiệm thu hoàn tất 16 Features v1 trên phạm vi pilot**:
   - Toàn bộ 16 đặc trưng ứng viên đã trải qua kiểm thử số học 2 lớp (22 ca tổng hợp tính tay và 10 ca thực nghiệm dữ liệu thật).
   - Mọi công thức toán học, bậc tự do (`ddof`), xử lý chuỗi phẳng, bảo tồn warm-up, cách ly spin-off / bar bẩn và cơ cấu phân rã lợi suất đều đạt độ chính xác tuyệt đối.
   - **Giữ rõ phạm vi kết luận**: Đợt pilot này chỉ kiểm chứng tính đúng đắn của việc triển khai mã nguồn công thức và tính toàn vẹn kỹ thuật trên các mẫu đã chọn; **chưa chứng minh tính toàn vẹn trên toàn bộ dữ liệu 27 năm cũng như khả năng sinh lời hay hiệu quả dự báo của các features**.
2. **Kế hoạch tiếp theo**:
   - Sinh feature store cho toàn bộ vũ trụ trong giai đoạn Development (2000–2023).
   - Tiến hành kiểm định feature store và thực hiện Exploratory Data Analysis (EDA) toàn diện trên Development.
3. **Cam kết tuân thủ ranh giới dự án**:
   - Dự án **chưa sinh full feature store cho toàn bộ 3.711 mã**.
   - Dự án **chưa thực hiện huấn luyện mô hình học máy (ML training) hay điều chỉnh siêu tham số (tuning)**.
   - Dữ liệu Out-of-Sample (2024–2026) được bảo toàn tuyệt đối, chưa hề chạm tới.
