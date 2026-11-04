> **Kế hoạch lịch sử, đã được thay thế ngày 2026-11-05.** Không dùng các công thức, số phiên hoặc kết luận trong tài liệu này làm đặc tả triển khai hiện hành. Xem [features v1](../specifications/features_v1.md) và [target/timing v1](../specifications/target_and_timing_v1.md). Nội dung dưới giữ để truy lịch sử đề xuất.

# Báo Cáo Kỹ Thuật Bước 7: Kế Hoạch & Bản Đặc Tả Kỹ Nghệ Đặc Trưng Định Lượng (Feature Engineering Specification & Implementation Plan)

**Dự án**: Dự đoán xếp hạng lợi suất hàng ngày rổ cổ phiếu Russell 1000 (Russell 1000 Daily Return Rankings Prediction Engine)  
**Milestone**: M4 — Bản Đặc Tả Đặc Trưng Định Lượng & Đồng Bộ Báo Cáo (Section R7)  
**Tác giả**: Đội ngũ Kỹ thuật Dữ liệu & Nghiên cứu Định lượng (Quantitative Data Engineering & Research Team)  
**Ngày phê duyệt thiết kế**: 04/11/2026  
**Tình trạng tài liệu**: **BẢN ĐẶC TẢ THIẾT KẾ TOÁN HỌC & KIẾN TRÚC HỆ THỐNG — CHỈ THIẾT KẾ, KHÔNG VIẾT CODE TRIỂN KHAI (SPECIFICATION ONLY - NO IMPLEMENTATION CODE)**  
**Phân vùng thời gian**:
- **Khởi tạo trượt (Warm-up Period)**: `1998-01-02` đến `2000-06-30` (630 phiên NYSE — Khởi tạo đủ 252 ngày lookback, Zero Cold-Start)
- **Tập phát triển (Development Partition)**: `2000-07-01` đến `2023-12-29` (5,912 phiên NYSE — Phạm vi duy nhất dùng cho Feature Engineering & Model Training)
- **Tập kiểm thử ngoài mẫu (Out-Of-Sample - OOS)**: `2024-01-02` đến `2026-10-30` (710 phiên NYSE — **ĐÓNG BĂNG HOÀN TOÀN**)

---

## 1. Tổng Quan Mục Tiêu Kiến Trúc Kỹ Nghệ Đặc Trưng (Feature Engineering Architecture)

Báo cáo này công bố toàn bộ tài liệu đặc tả thiết kế kỹ thuật định lượng chuẩn mực tổ chức (Institutional Quant Grade) thuộc Bước 7 trong quy trình 10 bước của dự án. 

Dựa trên kết quả khám phá dữ liệu (EDA) và kiểm toán pháp y tại Bước 6 (`docs/reports/step6_eda_report.md`), dự án đã xác định hai thách thức nền tảng trong dữ liệu chuỗi thời gian tài chính:
1. **Phân phối lợi suất có độ nhọn dư (Excess Kurtosis) lên tới 66.88 và tồn tại các cú sốc cực đoan từ $-94.97\%$ đến $+227.87\%$**: Các hàm mất mát truyền thống (như Mean Squared Error - MSE) sẽ bị sụp đổ hoặc phân kỳ do hiện tượng nổ gradient.
2. **Độ phân tán chéo (Cross-Sectional Dispersion) biến thiên liên tục theo chu kỳ vĩ mô**: Từ $1.45\%$ trong các năm thị trường bình lặng (2013, 2017) lên tới $4.17\% - 9.80\%$ trong các năm khủng hoảng (2000, 2008, 2020), đòi hỏi mô hình phải học trên một không gian mục tiêu và không gian đặc trưng có tính ổn định phân phối (Distributional Stationarity).

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       SƠ ĐỒ LUỒNG DỮ LIỆU BƯỚC 7 (FEATURE & TARGET ENGINE)                     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                  
  [data/processed/matrices/*.parquet]                                                             
  ├── 17 Ma Trận 2D Cơ Sở (7,252 ngày x 3,711 SIDs)                                              
  │   ├── Giá điều chỉnh: adj_open, adj_high, adj_low, adj_close, adj_volume                       
  │   ├── Giá thô & sự kiện: open, high, low, close, volume, cumulative_split_factor              
  │   ├── Lợi suất: daily_return, total_return                                                    
  │   └── Cờ kiểm toán: is_consecutive_session, is_bad_data_period, is_spinoff_discontinuity      
  └── 3 Lớp PIT Masks: membership_mask, valid_data_mask, valid_label_mask                         
               │                                                 │                                
               ▼                                                 ▼                                
 ┌─────────────────────────────┐                  ┌──────────────────────────────────────────────┐
 │ TARGET GENERATION ENGINE    │                  │ FEATURE GENERATION ENGINE (16 FEATURES)      │
 │ • Input: daily_return (t+1) │                  │ • Input: 17 ma trận 2D & valid_data_mask     │
 │ • Filter: valid_label_mask  │                  │ • Window: 1d đến 252d (Warm-up 1998-2000)    │
 │ • Cross-Sectional Ranking   │                  │ • Quarantine: Bad Data & Spinoff -> NaN      │
 │ • Uniform Rank Scaling [0,1]│                  │ • 5 Nhóm: Momentum, Volatility, Liquidity,   │
 └─────────────┬───────────────┘                  │           Microstructure, Systematic Risk    │
               │                                  └──────────────────────┬───────────────────────┘
               ▼                                                         ▼                        
 [data/processed/features/target_next_rank.parquet]       [data/processed/features/{feature}.parquet]
 (Ma trận 2D nhãn mục tiêu: 7,252 x 3,711)               (16 Ma trận 2D đặc trưng: 7,252 x 3,711)
```

---

## 2. Đặc Tả Chi Tiết Biến Mục Tiêu (Target Specification): `target_next_rank`

### 2.1. Tên Biến & Đường Dẫn Lưu Trữ Độc Lập
- **Tên biến chuẩn mực**: `target_next_rank`
- **Đường dẫn lưu trữ vật lý**: `data/processed/features/target_next_rank.parquet`
- **Cấu trúc lưu trữ**: Ma trận 2D Parquet (Dense 2D Matrix Grid), trục tung gồm 7,252 ngày giao dịch (`matrix_dates_index.parquet`), trục hoành gồm 3,711 Canonical SIDs (`matrix_columns_sids.parquet`).
- **Kiểu dữ liệu (Dtype)**: `float64`
- **Miền giá trị**: Đoạn đóng thực $[0.0, 1.0]$ đối với các quan sát hợp lệ, và `NaN` đối với các ô không thỏa mãn điều kiện nhãn.

### 2.2. Công Thức Toán Học Chính Xác
Tại mỗi phiên giao dịch $t$ thuộc lịch NYSE, biến mục tiêu cho cổ phiếu $i$ được định nghĩa dựa trên thứ hạng phân vị của lợi suất giá phiên ngày mai $r_{i, t+1}$:

$$target\_next\_rank_{i,t} = \begin{cases} 
\dfrac{\text{Rank}\left(r_{i, t+1}\right) - 1}{N_t - 1}, & \text{nếu } valid\_label\_mask_{i,t} == \text{True} \\ 
\text{NaN}, & \text{nếu } valid\_label\_mask_{i,t} == \text{False} 
\end{cases}$$

Trong đó:
- $r_{i, t+1} = \dfrac{adj\_close_{i, t+1} - adj\_close_{i, t}}{adj\_close_{i, t}}$ là tỷ suất sinh lời của cổ phiếu $i$ tại phiên tiếp theo $t+1$.
- $valid\_label\_mask_{i,t}$ là mặt nạ PIT Lớp 3 (xác nhận cổ phiếu $i$ giao dịch bình thường tại ngày $t$, ngày $t+1$ có giá, khối lượng hợp lệ, phiên $t+1$ liên tiếp, và ngày $t$ không thuộc danh sách ranh giới bị Purge).
- $N_t = \sum_{j=1}^{M} \mathbb{I}\left(valid\_label\_mask_{j,t} == \text{True}\right)$ là tổng số lượng cổ phiếu có nhãn hợp lệ trong phiên giao dịch $t$ (trung bình trong tập Development đạt từ 912 đến 987 mã).
- $\text{Rank}\left(r_{i, t+1}\right) \in [1, N_t]$ là thứ tự của cổ phiếu $i$ khi sắp xếp dãy $\{r_{j, t+1} \mid valid\_label\_mask_{j,t} == \text{True}\}$ theo chiều tăng dần. Cổ phiếu có lợi suất thấp nhất phiên nhận $\text{Rank} = 1$, cổ phiếu có lợi suất cao nhất phiên nhận $\text{Rank} = N_t$.
- **Quy tắc Tie-breaking (Xử lý lợi suất trùng nhau)**: Áp dụng phương pháp tính hạng trung bình (`method='average'` trong SciPy/Pandas):
  $$\text{Rank}(r) = \frac{\text{Rank}_{\min} + \text{Rank}_{\max}}{2}$$

### 2.3. Ý Nghĩa Cận Biên & Bản Chất Kinh Tế
- $target\_next\_rank_{i,t} = 0.0$: Cổ phiếu có hiệu suất sinh lời kém nhất toàn bộ rổ Russell 1000 trong phiên $t+1$ (Bottom 1 / Thua cuộc tuyệt đối).
- $target\_next\_rank_{i,t} = 0.5$: Cổ phiếu có hiệu suất sinh lời nằm chính xác tại vị trí trung vị của rổ Russell 1000 trong phiên $t+1$ (Median Performer).
- $target\_next\_rank_{i,t} = 1.0$: Cổ phiếu có hiệu suất sinh lời cao nhất toàn bộ rổ Russell 1000 trong phiên $t+1$ (Top 1 / Dẫn đầu tuyệt đối).

### 2.4. Luận Giải Khoa Học & Ưu Thế Vượt Trội Của Uniform Rank Target
1. **Khử Bỏ Hoàn Toàn Nguy Cơ Nổ Gradient Do Đuôi Dày (Fat Tails Invariance)**:
   - Biến ngẫu nhiên $Y_t \sim \mathcal{U}[0, 1]$ tuân theo phân phối đều rời rạc chuẩn hóa, có **Excess Kurtosis lý thuyết bằng đúng $-1.2$** và **Skewness bằng $0.0$**.
   - Ngay cả khi thị trường xuất hiện biến cố cực đoan như $+227.87\%$ (MFA ngày 25/03/2020) hoặc $-94.97\%$ (LEH ngày 15/09/2008), giá trị mục tiêu vẫn được chặn cứng trong đoạn $[0.0, 1.0]$. Không có bất kỳ điểm dị biệt nào có thể áp đảo hàm mất mát hay làm méo mó các phân nhánh cây quyết định (Split nodes).
2. **Bất Biến Trước Biến Động Thị Trường Hệ Thống (Market Regime Invariance)**:
   - Trong giai đoạn khủng hoảng (2008, 2020), độ phân tán giữa cổ phiếu tăng mạnh nhất và giảm sâu nhất có thể lên tới $40\% - 50\%$. Trong giai đoạn bình lặng (2017), khoảng cách này chỉ là $3\% - 5\%$.
   - Mục tiêu Uniform Rank $[0, 1]$ giữ nguyên quy mô phân phối không đổi qua mọi phiên giao dịch trong suốt 24 năm, triệt tiêu hoàn toàn rủi ro mô hình bị quá khớp vào các thời kỳ biến động cao.
3. **Phù Hợp Hoàn Hảo Với Bài Toán Đầu Tư Định Lượng Long-Short**:
   - Trong giao dịch thực tế, các quỹ định lượng không tìm cách dự báo cổ phiếu sẽ tăng chính xác bao nhiêu phần trăm, mà cần xác định **Top Decile (10% cổ phiếu tốt nhất để Mua - Long)** và **Bottom Decile (10% cổ phiếu kém nhất để Bán khống - Short)**.
   - Việc tối ưu hóa mô hình trên $target\_next\_rank$ tương đương trực tiếp với việc tối ưu hóa hệ số tương quan thứ hạng Spearman ($\text{Rank IC}$), là thước đo sống còn của mô hình định lượng.

### 2.5. Cơ Chế Purging Chống Rò Rỉ Look-Ahead Tuyệt Đối
- **Ranh giới Development / OOS (`2023-12-29`)**:
  Toàn bộ hàng `2023-12-29` trên $valid\_label\_mask$ đã bị cưỡng bức gán `False`. Do đó, hàng `2023-12-29` trên `target_next_rank.parquet` nhận giá trị `NaN` 100%. Điều này ngăn chặn hoàn toàn việc mô hình huấn luyện tại phiên cuối năm 2023 nhìn trộm sang phiên đầu tiên của tập Out-of-Sample (`2024-01-02`).
- **Phiên cuối cùng của dữ liệu (`2026-10-30`)**:
  Do không tồn tại phiên $t+1$, hàng này nhận giá trị `NaN` 100%.

---

## 3. Bản Đặc Tả Chi Tiết Hệ Thống 16 Đặc Trưng Định Lượng (16 Features Specifications)

Hệ thống 16 đặc trưng được chia thành 5 nhóm nhân tố kinh tế định lượng:
- **Nhóm 1: Nhóm Động Lượng & Đảo Chiều Giá (Price Momentum & Reversal Factors)**: 5 đặc trưng (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `ret_252d_skip1m`)
- **Nhóm 2: Nhóm Biến Động & Cấu Trúc Rủi Ro (Volatility & Risk Term Structure Factors)**: 3 đặc trưng (`vol_realized_20d`, `vol_realized_60d`, `vol_ratio_20_60`)
- **Nhóm 3: Nhóm Thanh Khoản & Tác Động Thị Trường (Liquidity & Market Impact Factors)**: 3 đặc trưng (`amihud_illiq_20d`, `turnover_20d`, `volume_ratio_1_20`)
- **Nhóm 4: Nhóm Cấu Trúc Vi Mô Phiên & Dao Động Nến (Intraday & Microstructure Range Factors)**: 2 đặc trưng (`ret_intraday`, `high_low_range`)
- **Nhóm 5: Nhóm Neo Giá Hành Vi & Rủi Ro Hệ Thống (Behavioral Anchor & Systematic Risk Factors)**: 3 đặc trưng (`close_to_high_52w`, `price_level`, `beta_20d`)

---

### 3.1. Đặc Trưng 1: `ret_1d` (Lợi Suất 1 Ngày — Short-term Reversal)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_1d` |
| **Nhóm đặc trưng** | Động lượng ngắn hạn & Đảo chiều vi cấu trúc (Short-term Reversal) |
| **Công thức toán học** | $$ret\_1d_{i,t} = \frac{adj\_close_{i,t}}{adj\_close_{i,t-1}} - 1$$ |
| **Cửa sổ trượt ($W$)** | $W = 1$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `is_consecutive_session.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) $valid\_data\_mask_{i,t} == \text{False}$; (2) Phiên đầu tiên của cổ phiếu (không có $t-1$); (3) $is\_consecutive\_session_{i,t} == \text{False}$ (phiên $t$ và $t-1$ bị gián đoạn $> 1$ phiên giao dịch). |
| **Quality Flag Handling** | Nếu phiên $t$ hoặc $t-1$ có $is\_bad\_data\_period == \text{True}$ hoặc $is\_spinoff\_discontinuity == \text{True}$, giá trị `ret_1d` tại phiên $t$ bị cưỡng bức gán thành `NaN`. |
| **Lý do kinh tế & Học thuật** | **Hiệu ứng đảo chiều ngắn hạn (Short-term Reversal Effect)** được kiểm chứng bởi Jegadeesh (1990) và Lehmann (1990). Các cổ phiếu tăng mạnh trong ngày hôm nay thường chịu áp lực bán chốt lời của các nhà tạo lập lập vị thế hoặc hiện tượng giật nảy giá chào mua-bán (Bid-Ask Bounce). Trong mô hình đa nhân tố, `ret_1d` thường mang hệ số tải âm đối với lợi suất ngày kế tiếp. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Công thức chỉ sử dụng giá đóng cửa điều chỉnh tại phiên $t$ và phiên liền trước $t-1$. Toàn bộ thông tin được chốt tại 16:00 EST ngày $t$. |
| **Rủi ro Đa cộng tuyến** | Tương quan trung bình với `ret_intraday` ($r \approx 0.65 - 0.75$) do cùng phản ánh diễn biến trong ngày, nhưng trực giao với các đặc trưng động lượng trung và dài hạn ($r < 0.15$ với `ret_20d`, `ret_252d_skip1m`). |

---

### 3.2. Đặc Trưng 2: `ret_5d` (Lợi Suất 1 Tuần — Weekly Momentum / Mean-Reversion)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_5d` |
| **Nhóm đặc trưng** | Động lượng & Đảo chiều tuần (Weekly Momentum / Reversal) |
| **Công thức toán học** | $$ret\_5d_{i,t} = \frac{adj\_close_{i,t}}{adj\_close_{i,t-5}} - 1 = \prod_{k=0}^{4} (1 + daily\_return_{i,t-k}) - 1$$ |
| **Cửa sổ trượt ($W$)** | $W = 5$ phiên giao dịch NYSE (~1 tuần giao dịch tiêu chuẩn) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `valid_data_mask.parquet`, `is_consecutive_session.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Cổ phiếu có ít hơn 5 phiên giao dịch hợp lệ liên tiếp tính đến ngày $t$; (2) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Nếu trong cửa sổ 5 phiên $[t-4, t]$ xuất hiện bất kỳ phiên nào có cờ $is\_bad\_data\_period == \text{True}$ hoặc $is\_spinoff\_discontinuity == \text{True}$, gán `ret_5d` thành `NaN`. |
| **Lý do kinh tế & Học thuật** | Phản ánh chu kỳ thanh toán bù trừ và tái cân bằng vị thế tuần của các quỹ phòng hộ (Hedge Funds Weekly Rebalancing). Theo Gutierrez & Kelley (2008), lợi suất tuần kết hợp giữa đà quán tính tin tức (Earnings Drift) và áp lực quá bán/quá mua kỹ thuật. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Cửa sổ trượt kết thúc chính xác tại thời điểm đóng cửa ngày $t$. |
| **Rủi ro Đa cộng tuyến** | Tương quan dương với `ret_1d` ($r \approx 0.40$) và `ret_20d` ($r \approx 0.50$). Cung cấp thông tin chuyển tiếp giữa vi cấu trúc siêu ngắn hạn và động lượng tháng. |

---

### 3.3. Đặc Trưng 3: `ret_20d` (Lợi Suất 1 Tháng — Monthly Momentum)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_20d` |
| **Nhóm đặc trưng** | Động lượng trung hạn 1 tháng (Intermediate Momentum) |
| **Công thức toán học** | $$ret\_20d_{i,t} = \frac{adj\_close_{i,t}}{adj\_close_{i,t-20}} - 1$$ |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE (~1 tháng dương lịch) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Cổ phiếu có lịch sử giao dịch tích lũy $< 20$ phiên; (2) Số phiên hợp lệ trong cửa sổ 20 ngày ít hơn 16 phiên ($< 80\%$ valid); (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Nếu trong cửa sổ 20 phiên $[t-19, t]$ có bất kỳ phiên nào chạm cờ cách ly nến lỗi hoặc tách công ty, `ret_20d` của mã đó tại phiên $t$ bị loại bỏ thành `NaN`. |
| **Lý do kinh tế & Học thuật** | Đại diện cho chu kỳ phân bổ dòng tiền hàng tháng (Monthly Asset Allocation Flow) của các quỹ tương hỗ (Mutual Funds). Asness et al. (2013, "Value and Momentum Everywhere") chứng minh lợi suất 1 tháng là ranh giới bắt đầu hình thành xu hướng tiếp diễn giá (Price Continuation). |
| **Rủi ro Look-ahead** | **0 rủi ro**. Sử dụng dữ liệu trượt quá khứ $[t-20, t]$. |
| **Rủi ro Đa cộng tuyến** | Tương quan với `ret_60d` ($r \approx 0.55$) và `close_to_high_52w` ($r \approx 0.45$). Cần thiết lập cây quyết định để phân tách ngưỡng phi tuyến. |

---

### 3.4. Đặc Trưng 4: `ret_60d` (Lợi Suất 1 Quý — Quarterly Momentum / Post-Earnings Drift)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_60d` |
| **Nhóm đặc trưng** | Động lượng quý & Trôi dạt sau công bố lợi nhuận (Quarterly Momentum / PEAD) |
| **Công thức toán học** | $$ret\_60d_{i,t} = \frac{adj\_close_{i,t}}{adj\_close_{i,t-60}} - 1$$ |
| **Cửa sổ trượt ($W$)** | $W = 60$ phiên giao dịch NYSE (~1 quý tài chính, 3 tháng) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Lịch sử giao dịch $< 60$ phiên; (2) Số phiên hợp lệ trong cửa sổ ít hơn 48 phiên ($< 80\%$); (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Cưỡng bức gán `NaN` nếu tồn tại sự kiện gián đoạn giá hoặc nến rác trong 60 phiên gần nhất. |
| **Lý do kinh tế & Học thuật** | Tương ứng với khoảng thời gian giữa hai kỳ báo cáo tài chính định kỳ (Quarterly Earnings Cycle). Phản ánh hiện tượng **Trôi dạt giá sau công bố kết quả kinh doanh (Post-Earnings Announcement Drift - PEAD)** được phát hiện bởi Bernard & Thomas (1989): thị trường phản ứng chậm với thông tin bất ngờ về lợi nhuận, khiến xu hướng giá kéo dài suốt 60 ngày tiếp theo. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Hoàn toàn khép kín trong quá khứ. |
| **Rủi ro Đa cộng tuyến** | Tương quan với `ret_20d` ($r \approx 0.55$) và `ret_252d_skip1m` ($r \approx 0.60$). |

---

### 3.5. Đặc Trưng 5: `ret_252d_skip1m` (Động Lượng 12 Tháng Bỏ 1 Tháng Gần Nhất — Jegadeesh-Titman 1993)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_252d_skip1m` |
| **Nhóm đặc trưng** | Động lượng trung hạn kinh điển (Intermediate-term Price Momentum) |
| **Công thức toán học** | $$ret\_252d\_skip1m_{i,t} = \frac{adj\_close_{i,t-21}}{adj\_close_{i,t-252}} - 1$$ |
| **Cửa sổ trượt ($W$)** | $W = 252$ phiên giao dịch NYSE (~1 năm lịch sử), có độ trễ bỏ qua 21 phiên gần nhất ($[t-21, t]$) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Cổ phiếu có lịch sử giao dịch $< 252$ ngày; (2) Số phiên hợp lệ trong khoảng $[t-252, t-21]$ ít hơn 185 phiên ($< 80\%$); (3) $valid\_data\_mask_{i,t} == \text{False}$. Giai đoạn Warm-up 1998–2000 đảm bảo 100% mã có sẵn lịch sử khi vào tập Development ngày 01/07/2000. |
| **Quality Flag Handling** | Nếu trong khoảng $[t-252, t-21]$ có cờ lỗi dữ liệu hoặc chia tách công ty con, gán `NaN`. |
| **Lý do kinh tế & Học thuật** | **Nhân tố động lượng kinh điển Jegadeesh & Titman (1993, Journal of Finance: "Returns to Buying Winners and Selling Losers")**. Đây là một trong những dị biệt thị trường (market anomalies) mạnh mẽ nhất trong tài chính thực nghiệm. Việc **bỏ qua 1 tháng gần nhất (phiên $t-21$ đến $t$)** là nguyên tắc bắt buộc để triệt tiêu hiện tượng đảo chiều ngắn hạn do áp lực thanh khoản vi mô, bảo toàn tín hiệu động lượng xu hướng cơ bản. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Toàn bộ dữ liệu nằm từ phiên $t-252$ đến phiên $t-21$, hoàn toàn không sử dụng dữ liệu tương lai. |
| **Rủi ro Đa cộng tuyến** | Nhờ độ trễ 21 ngày, đặc trưng này có độ tương quan rất thấp với `ret_1d` ($r < 0.05$) và `ret_5d` ($r < 0.10$), giải quyết hoàn hảo xung đột giữa tín hiệu xu hướng dài hạn và đảo chiều ngắn hạn. |

---

### 3.6. Đặc Trưng 6: `vol_realized_20d` (Độ Biến Động Thực Nghiệm 20 Ngày Năm Hóa)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `vol_realized_20d` |
| **Nhóm đặc trưng** | Rủi ro biến động ngắn hạn (Realized Volatility) |
| **Công thức toán học** | $$\sigma^{(20)}_{i,t} = \sqrt{\frac{252}{19} \sum_{k=0}^{19} \left(daily\_return_{i,t-k} - \bar{r}^{(20)}_{i,t}\right)^2}$$ <br>với $\bar{r}^{(20)}_{i,t} = \frac{1}{20} \sum_{k=0}^{19} daily\_return_{i,t-k}$. |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/daily_return.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Cổ phiếu có ít hơn 16 phiên return hữu hạn trong cửa sổ 20 ngày; (2) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Nếu trong cửa sổ 20 phiên có bất kỳ cờ cách ly lỗi dữ liệu nào $\to$ `NaN`. |
| **Lý do kinh tế & Học thuật** | Thước đo độ biến động ngắn hạn thực tế của cổ phiếu đơn lẻ. Theo nghiên cứu về **Nghịch lý Biến động Đặc thù (Idiosyncratic Volatility Puzzle - Ang, Hodrick, Xing & Zhang 2006)**, các cổ phiếu có độ biến động thực nghiệm tăng vọt thường có xu hướng mang lại lợi suất kỳ vọng kém hơn trong tương lai do bị định giá quá cao bởi các nhà đầu tư ưa thích rủi ro dạng vé số. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Tính toán trên dãy return lịch sử từ $t-19$ đến $t$. |
| **Rủi ro Đa cộng tuyến** | Tương quan rất cao với `vol_realized_60d` ($r \approx 0.85 - 0.90$). Do đó, cần kết hợp với đặc trưng tỷ số `vol_ratio_20_60` để trích xuất tín hiệu gia tốc biến động. |

---

### 3.7. Đặc Trưng 7: `vol_realized_60d` (Độ Biến Động Thực Nghiệm 60 Ngày Năm Hóa)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `vol_realized_60d` |
| **Nhóm đặc trưng** | Rủi ro biến động trung hạn nền tảng (Baseline Volatility) |
| **Công thức toán học** | $$\sigma^{(60)}_{i,t} = \sqrt{\frac{252}{59} \sum_{k=0}^{59} \left(daily\_return_{i,t-k} - \bar{r}^{(60)}_{i,t}\right)^2}$$ |
| **Cửa sổ trượt ($W$)** | $W = 60$ phiên giao dịch NYSE (~1 quý) |
| **Ma trận input** | `data/processed/matrices/daily_return.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Số phiên return hữu hạn trong 60 ngày $< 48$ phiên ($< 80\%$); (2) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Cách ly thành `NaN` nếu xuất hiện cờ lỗi trong cửa sổ 60 ngày. |
| **Lý do kinh tế & Học thuật** | Thiết lập mặt bằng biến động nền tảng (Baseline Volatility Regime) của doanh nghiệp, ít bị nhiễu bởi các cú sốc tin tức nhất thời trong vài phiên. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Thuần túy lịch sử. |
| **Rủi ro Đa cộng tuyến** | Tương quan cao với `vol_realized_20d` ($r \approx 0.88$). Đóng vai trò làm mẫu số chuẩn hóa cho cấu trúc kỳ hạn biến động. |

---

### 3.8. Đặc Trưng 8: `vol_ratio_20_60` (Tỷ Số Cấu Trúc Kỳ Hạn Biến Động — Volatility Term Structure)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `vol_ratio_20_60` |
| **Nhóm đặc trưng** | Gia tốc biến động & Động học cấu trúc kỳ hạn (Volatility Term Structure / Shock) |
| **Công thức toán học** | $$vol\_ratio\_20\_60_{i,t} = \frac{\sigma^{(20)}_{i,t}}{\sigma^{(60)}_{i,t}}$$ |
| **Cửa sổ trượt ($W$)** | $W = 60$ phiên giao dịch NYSE (kết hợp cửa sổ 20 ngày và 60 ngày) |
| **Ma trận input** | `vol_realized_20d`, `vol_realized_60d`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Một trong hai biến `vol_realized_20d` hoặc `vol_realized_60d` là `NaN`; (2) Mẫu số $\sigma^{(60)}_{i,t} < 10^{-6}$ (tránh chia cho 0); (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Kế thừa chính sách cách ly của cả hai biến thành phần. |
| **Lý do kinh tế & Học thuật** | Đo lường độ dốc đường cong cấu trúc kỳ hạn biến động (Slope of Volatility Term Structure). <br>• Khi $vol\_ratio > 1.0$: Biến động ngắn hạn bùng nổ vượt trội so với biến động trung hạn, phản ánh cổ phiếu đang chịu **Cú sốc thông tin bất thường (Volatility Spike / Catalyst)**. <br>• Khi $vol\_ratio < 1.0$: Cổ phiếu đang trong pha nén biến động tích lũy (Volatility Contraction), thường báo hiệu giai đoạn tích lũy trước một xu hướng lớn. |
| **Rủi ro Look-ahead** | **0 rủi ro**. |
| **Rủi ro Đa cộng tuyến** | Nhờ phép chia tỷ lệ chuẩn hóa, `vol_ratio_20_60` triệt tiêu phần lớn mối tương quan tuyến tính với mức độ biến động tuyệt đối ($r < 0.25$ với `vol_realized_20d`), cung cấp một tín hiệu trực giao hoàn toàn mới về gia tốc rủi ro. |

---

### 3.9. Đặc Trưng 9: `amihud_illiq_20d` (Hệ Số Phi Thanh Khoản Amihud 20 Ngày)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `amihud_illiq_20d` |
| **Nhóm đặc trưng** | Thanh khoản & Tác động trượt giá (Liquidity & Price Impact) |
| **Công thức toán học** | $$amihud\_illiq\_20d_{i,t} = \left(\frac{1}{20} \sum_{k=0}^{19} \frac{|daily\_return_{i,t-k}|}{\text{DollarVolume}_{i,t-k}}\right) \times 10^6$$ <br>Trong đó: $\text{DollarVolume}_{i,\tau} = adj\_close_{i,\tau} \times adj\_volume_{i,\tau} = close_{i,\tau} \times volume_{i,\tau}$ (USD). |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/daily_return.parquet`, `adj_close.parquet`, `adj_volume.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Trong 20 phiên có phiên nào $\text{DollarVolume} == 0$; (2) Số phiên hợp lệ $< 16$; (3) $valid\_data\_mask_{i,t} == \text{False}$. Nhân với $10^6$ để đưa giá trị về quy mô hiển thị số thực thuận lợi. |
| **Quality Flag Handling** | Cách ly nếu có cờ lỗi dữ liệu hoặc chia tách công ty con trong cửa sổ. |
| **Lý do kinh tế & Học thuật** | **Chỉ số phi thanh khoản Amihud (2002, Journal of Financial Markets: "Illiquidity and Stock Returns")**. Đo lường phản ứng bước nhảy giá trên mỗi 1 triệu USD giá trị giao dịch (Price impact per dollar volume). Cổ phiếu có hệ số Amihud cao là cổ phiếu kém thanh khoản, phải trả phần bù rủi ro thanh khoản cao hơn (Illiquidity Premium). |
| **Rủi ro Look-ahead** | **0 rủi ro**. Sử dụng dữ liệu giá và khối lượng từ $t-19$ đến $t$. |
| **Rủi ro Đa cộng tuyến** | Tương quan nghịch với quy mô khối lượng `turnover_20d` ($r \approx -0.50$), nhưng bổ sung góc nhìn sâu sắc về độ sâu sổ lệnh và độ trượt giá. |

---

### 3.10. Đặc Trưng 10: `turnover_20d` (Khối Lượng Giao Dịch Trung Bình 20 Ngày)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `turnover_20d` |
| **Nhóm đặc trưng** | Quy mô thanh khoản giao dịch (Trading Volume Baseline) |
| **Công thức toán học** | $$turnover\_20d_{i,t} = \frac{1}{20} \sum_{k=0}^{19} adj\_volume_{i,t-k}$$ |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/adj_volume.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Số phiên có $adj\_volume > 0$ trong 20 ngày ít hơn 16 phiên; (2) $valid\_data\_mask_{i,t} == \text{False}$. Bắt buộc dùng `adj_volume` để bảo toàn tính so sánh qua các sự kiện chia tách cổ phiếu. |
| **Quality Flag Handling** | Cách ly nếu có cờ dữ liệu lỗi trong cửa sổ. |
| **Lý do kinh tế & Học thuật** | Thiết lập đường cơ sở hoạt động giao dịch bình quân của cổ phiếu (Gervais, Kaniel & Mingelgrin 2001, "The High-Volume Return Premium"). Giúp mô hình phân biệt giữa các cổ phiếu thanh khoản khổng lồ (Mega-caps) và cổ phiếu thanh khoản trung bình trong rổ Russell 1000. |
| **Rủi ro Look-ahead** | **0 rủi ro**. |
| **Rủi ro Đa cộng tuyến** | Là mẫu số chuẩn mực để tính toán tỷ số đột biến khối lượng `volume_ratio_1_20`. |

---

### 3.11. Đặc Trưng 11: `volume_ratio_1_20` (Đột Biến Khối Lượng — Volume Surge / Attention Shock)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `volume_ratio_1_20` |
| **Nhóm đặc trưng** | Đột biến chú ý & Dấu chân dòng tiền (Volume Shock / Investor Attention) |
| **Công thức toán học** | $$volume\_ratio\_1\_20_{i,t} = \frac{adj\_volume_{i,t}}{turnover\_20d_{i,t}} = \frac{volume_{i,t}}{\frac{1}{20} \sum_{k=0}^{19} volume_{i,t-k} \times \frac{CF_{i,t-k}}{CF_{i,t}}}$$ |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/adj_volume.parquet`, `turnover_20d`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) `turnover_20d` là `NaN` hoặc $\le 0$; (2) Phiên $t$ có $adj\_volume == 0$; (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Cách ly thành `NaN` nếu phiên $t$ hoặc cửa sổ 20 ngày chạm cờ lỗi. |
| **Lý do kinh tế & Học thuật** | Đo lường mức độ bùng nổ khối lượng giao dịch đột ngột so với bình quân 1 tháng. Theo Barber & Odean (2008, "All That Glitters: The Effect of Attention and News on the Buying Behavior of Individual and Institutional Investors"), sự đột biến khối lượng là tín hiệu nhận diện **Dấu chân của Nhà đầu tư tổ chức (Institutional Footprint)** tham gia thị trường hoặc sự kiện bất đối xứng thông tin quan trọng. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Kết thúc tại 16:00 EST ngày $t$. |
| **Rủi ro Đa cộng tuyến** | Gần như trực giao hoàn toàn với các nhân tố giá thuần túy ($r < 0.15$ với các biến return), đóng góp chiều không gian độc lập về thanh khoản. |

---

### 3.12. Đặc Trưng 12: `ret_intraday` (Lợi Suất Nội Nhật — Intraday Price Discovery)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `ret_intraday` |
| **Nhóm đặc trưng** | Khám phá giá nội nhật & Cấu trúc phiên (Day-Session Dynamics) |
| **Công thức toán học** | $$ret\_intraday_{i,t} = \frac{close_{i,t} - open_{i,t}}{open_{i,t}} = \frac{adj\_close_{i,t} - adj\_open_{i,t}}{adj\_open_{i,t}}$$ |
| **Cửa sổ trượt ($W$)** | $W = 1$ phiên giao dịch NYSE (từ 09:30 EST đến 16:00 EST) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `adj_open.parquet` (hoặc `close`, `open`), `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) $open_{i,t} \le 0$ hoặc $close_{i,t} \le 0$; (2) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Gán `NaN` nếu phiên $t$ có $is\_bad\_data\_period == \text{True}$ hoặc $is\_spinoff\_discontinuity == \text{True}$. |
| **Lý do kinh tế & Học thuật** | Lou, Polk & Skouras (2019, Journal of Financial Economics: "A Tug of War: Overnight Versus Intraday Expected Returns") chứng minh cấu trúc sinh lời 24 giờ của cổ phiếu bị chia tách rõ rệt: phần bù qua đêm (Overnight Return: từ đóng cửa hôm trước đến mở cửa hôm nay) chủ yếu phản ánh tâm lý tin tức và dòng tiền cá nhân, trong khi lợi suất nội nhật (Intraday Return: từ mở cửa đến đóng cửa) phản ánh hành vi giao dịch có tổ chức và sự hấp thụ thanh khoản của các thuật toán chuyên nghiệp. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Sử dụng mức giá mở cửa và đóng cửa đã xác nhận của phiên $t$. |
| **Rủi ro Đa cộng tuyến** | Tương quan một phần với `ret_1d` ($r \approx 0.70$). Phần chênh lệch giữa hai biến chính là Overnight Return $r^{\text{overnight}} = \frac{Open_t}{Close_{t-1}} - 1$. |

---

### 3.13. Đặc Trưng 13: `high_low_range` (Biên Độ Nến Chuẩn Hóa — Normalized Bar Range)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `high_low_range` |
| **Nhóm đặc trưng** | Dao động cực trị nến & Áp lực tranh chấp giá (Extreme Price Dispersion) |
| **Công thức toán học** | $$high\_low\_range_{i,t} = \frac{high_{i,t} - low_{i,t}}{close_{i,t}} = \frac{adj\_high_{i,t} - adj\_low_{i,t}}{adj\_close_{i,t}}$$ |
| **Cửa sổ trượt ($W$)** | $W = 1$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/high.parquet`, `low.parquet`, `close.parquet` (hoặc ma trận adjusted tương ứng), `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) $close_{i,t} \le 0$; (2) $high_{i,t} < low_{i,t}$; (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Gán `NaN` nếu phiên $t$ có cờ lỗi chất lượng dữ liệu. |
| **Lý do kinh tế & Học thuật** | Là dạng thức xấp xỉ bậc một của **Ước lượng Biến động Cực trị Parkinson (1980, Journal of Business: "The Extreme Value Method for Estimating the Variance of the Rate of Return")**. Parkinson chứng minh biên độ High-Low chứa lượng thông tin về độ biến động nội nhật hiệu quả gấp 5 lần so với việc chỉ quan sát giá đóng cửa. Tỷ số này đo lường áp lực bất đồng quan điểm định giá giữa phe mua và phe bán trong ngày. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Toàn bộ giá High, Low, Close được xác nhận khi kết thúc phiên. |
| **Rủi ro Đa cộng tuyến** | Tương quan trung bình với `vol_realized_20d` ($r \approx 0.45$), nhưng có độ nhạy phản ứng tức thì với biến cố trong ngày mà không bị trễ pha như các chỉ số trượt dài hạn. |

---

### 3.14. Đặc Trưng 14: `close_to_high_52w` (Khoảng Cách Tới Đỉnh 52 Tuần — 52-Week High Anchor)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `close_to_high_52w` |
| **Nhóm đặc trưng** | Neo giá tâm lý hành vi (Behavioral Anchoring / Neoclassical Momentum) |
| **Công thức toán học** | $$close\_to\_high\_52w_{i,t} = \frac{adj\_close_{i,t}}{\max_{k \in [0, 251]} \left(adj\_high_{i,t-k}\right)}$$ |
| **Cửa sổ trượt ($W$)** | $W = 252$ phiên giao dịch NYSE (~52 tuần giao dịch, 1 năm) |
| **Ma trận input** | `data/processed/matrices/adj_close.parquet`, `adj_high.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Lịch sử giao dịch $< 252$ ngày; (2) Số phiên hợp lệ trong 252 ngày ít hơn 200 phiên ($< 80\%$); (3) Mẫu số $\le 0$; (4) $valid\_data\_mask_{i,t} == \text{False}$. Giá trị luôn nằm trong khoảng $(0.0, 1.0]$. |
| **Quality Flag Handling** | Cưỡng bức gán `NaN` nếu trong 252 phiên có cờ nến rác hoặc chia tách công ty con chưa điều chỉnh. |
| **Lý do kinh tế & Học thuật** | **Nhân tố Đỉnh 52 Tuần của George & Hwang (2004, Journal of Finance: "The 52-Week High and Momentum Investing")**. George & Hwang chứng minh rằng mức giá cao nhất 52 tuần đóng vai trò là một "mỏ neo tâm lý" (Anchoring Bias). Khi giá cổ phiếu tiệm cận đỉnh 52 tuần ($close\_to\_high\_52w \to 1.0$), các nhà đầu tư cá nhân có xu hướng vội vàng chốt lời vì cảm thấy giá "quá đắt", tạo ra rào cản cản trở tạm thời. Tuy nhiên, một khi các thông tin cơ bản tốt tiếp tục đẩy giá vượt đỉnh, áp lực bán biến mất và cổ phiếu sẽ bứt phá mạnh mẽ. Nhân tố này dự báo lợi suất vượt trội hơn hẳn momentum giá truyền thống. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Cửa sổ 252 ngày khép kín tại ngày $t$. Dữ liệu Warm-up 1998–2000 đảm bảo tính liên tục tuyệt đối. |
| **Rủi ro Đa cộng tuyến** | Tương quan với `ret_252d_skip1m` ($r \approx 0.60 - 0.70$) do cùng chung chiều dài 1 năm, nhưng `close_to_high_52w` mang đặc tính phân phối tiệm cận 1.0 với đuôi trái mở rộng. |

---

### 3.15. Đặc Trưng 15: `price_level` (Mức Thị Giá Danh Nghĩa — Nominal Price Level)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `price_level` |
| **Nhóm đặc trưng** | Ràng buộc vi cấu trúc & Tâm lý thị giá danh nghĩa (Nominal Share Price & Scale Factor) |
| **Công thức toán học** | $$price\_level_{i,t} = \ln\left(close_{i,t}\right)$$ |
| **Cửa sổ trượt ($W$)** | $W = 1$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/close.parquet` (Giá đóng cửa thô chưa điều chỉnh), `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) $close_{i,t} \le 0$; (2) $valid\_data\_mask_{i,t} == \text{False}$. Áp dụng hàm logarit tự nhiên để chuẩn hóa độ lệch phải của thị giá. |
| **Quality Flag Handling** | Gán `NaN` nếu phiên $t$ bị dính cờ cách ly lỗi dữ liệu. |
| **Lý do kinh tế & Học thuật** | **Hiệu ứng thị giá danh nghĩa (Nominal Share Price Puzzle - Baker, Greenwood & Wurgler 2009, Journal of Financial Economics)**. Trong kinh tế vi mô tài chính, giá cổ phiếu danh nghĩa $close$ tác động trực tiếp đến hành vi của các thành phần thị trường: <br>• Các cổ phiếu giá danh nghĩa thấp ($< \$5.00$ hoặc $< \$10.00$) thường bị các quỹ hưu trí và quỹ tương hỗ lớn cấm đầu tư theo điều lệ quản trị rủi ro; đồng thời chịu chi phí bước giá (tick size constraints) lớn hơn trên tỷ lệ phần trăm. <br>• Cổ phiếu thị giá thấp thu hút nhà đầu tư cá nhân tìm kiếm cơ hội "xổ số" (Lottery-like payoffs / Kumar 2009), dẫn đến tính chất phân phối biến động khác biệt căn bản so với cổ phiếu Blue-chip thị giá cao ($> \$100.00$). |
| **Rủi ro Look-ahead** | **0 rủi ro**. Sử dụng giá đóng cửa thô của phiên $t$. |
| **Rủi ro Đa cộng tuyến** | Hoàn toàn độc lập với các nhân tố return và biến động ($r < 0.10$). Cung cấp thông tin phân tầng quy mô cổ phiếu độc nhất. |

---

### 3.16. Đặc Trưng 16: `beta_20d` (Hệ Số Nhạy Cảm Thị Trường 20 Ngày — Short-term Market Beta)

| Mục Đặc Tả | Chi Tiết Kỹ Thuật |
|:---|:---|
| **Tên đặc trưng** | `beta_20d` |
| **Nhóm đặc trưng** | Rủi ro hệ thống CAPM (Systematic Risk Sensitivity) |
| **Công thức toán học** | $$\beta^{(20)}_{i,t} = \frac{\text{Cov}_{k \in [0, 19]}\left(daily\_return_{i,t-k}, r^{\text{mkt}}_{t-k}\right)}{\text{Var}_{k \in [0, 19]}\left(r^{\text{mkt}}_{t-k}\right)}$$ <br>Trong đó lợi suất danh mục thị trường $r^{\text{mkt}}_\tau$ tại phiên $\tau$ được tính bằng bình quân chéo ngang (Equal-weighted market proxy) của toàn bộ các cổ phiếu thành viên hợp lệ: $$r^{\text{mkt}}_\tau = \frac{1}{N_\tau} \sum_{j \in \text{valid\_label}_\tau} daily\_return_{j,\tau}$$ |
| **Cửa sổ trượt ($W$)** | $W = 20$ phiên giao dịch NYSE |
| **Ma trận input** | `data/processed/matrices/daily_return.parquet`, `valid_label_mask.parquet`, `valid_data_mask.parquet` |
| **NaN Handling Policy** | Gán `NaN` nếu: (1) Cổ phiếu có ít hơn 16 cặp quan sát hợp lệ đồng thời với thị trường; (2) Phương sai thị trường $\text{Var}(r^{\text{mkt}}) < 10^{-8}$ (thị trường đứng im); (3) $valid\_data\_mask_{i,t} == \text{False}$. |
| **Quality Flag Handling** | Nếu trong cửa sổ 20 ngày của cổ phiếu $i$ có cờ lỗi $\to$ `NaN`. |
| **Lý do kinh tế & Học thuật** | **Mô hình Định giá Tài sản Vốn (Capital Asset Pricing Model - CAPM của Sharpe 1964 và Lintner 1965)**. Hệ số $\beta$ đo lường mức độ đồng pha và độ nhạy cảm của cổ phiếu trước các biến động của toàn bộ rổ chỉ số Russell 1000. Frazzini & Pedersen (2014, "Betting Against Beta") chỉ ra rằng việc phân tách cổ phiếu phòng thủ ($\beta < 1.0$) và cổ phiếu chu kỳ ($\beta > 1.0$) là chìa khóa để kiểm soát rủi ro hệ thống trong các chiến lược xếp hạng chéo. |
| **Rủi ro Look-ahead** | **0 rủi ro**. Tại ngày $t$, cả $daily\_return_{i}$ và chuỗi $r^{\text{mkt}}$ đều chỉ được tính trên khoảng lịch sử $[t-19, t]$. Tuyệt đối không sử dụng thông tin phiên $t+1$. |
| **Rủi ro Đa cộng tuyến** | Tương quan trung bình với `vol_realized_20d` ($r \approx 0.50$), nhưng phân tách rõ ràng giữa rủi ro hệ thống (Systematic Risk) và rủi ro phi hệ thống (Idiosyncratic Risk). |

---

## 4. Bảng Tổng Hợp Tham Chiếu 16 Đặc Trưng Định Lượng

| STT | Tên Đặc Trưng | Nhóm Kỹ Thuật | Lookback ($W$) | Ma Trận Input Chính | Cơ Sở Lý Thuyết Học Thuật Chính | Rủi Ro Đa Cộng Tuyến |
|:---:|:---|:---|:---:|:---|:---|:---|
| **1** | `ret_1d` | Reversal | 1d | `adj_close` | Jegadeesh (1990), Lehmann (1990) | Vừa với `ret_intraday` ($r \approx 0.70$) |
| **2** | `ret_5d` | Weekly Momentum | 5d | `adj_close` | Gutierrez & Kelley (2008) | Vừa với `ret_1d`, `ret_20d` ($r \approx 0.45$) |
| **3** | `ret_20d` | Monthly Momentum | 20d | `adj_close` | Asness et al. (2013) | Vừa với `ret_60d` ($r \approx 0.55$) |
| **4** | `ret_60d` | Quarterly Momentum | 60d | `adj_close` | Bernard & Thomas (1989) PEAD | Vừa với `ret_20d`, `ret_252d` ($r \approx 0.60$) |
| **5** | `ret_252d_skip1m` | 12M Momentum | 252d (trễ 21d) | `adj_close` | Jegadeesh & Titman (1993) | Thấp với short-term; vừa với 52w High |
| **6** | `vol_realized_20d` | Volatility | 20d | `daily_return` | Ang et al. (2006) I-Vol Puzzle | Rất cao với `vol_realized_60d` ($r \approx 0.88$) |
| **7** | `vol_realized_60d` | Baseline Vol | 60d | `daily_return` | Risk Benchmark | Cao với `vol_realized_20d` |
| **8** | `vol_ratio_20_60` | Vol Term Structure | 60d | `vol_20d`, `vol_60d` | Regime Shift / Vol Spike Indicator | Thấp với biến vol tuyệt đối ($r < 0.25$) |
| **9** | `amihud_illiq_20d` | Liquidity Impact | 20d | `daily_return`, `adj_close`, `adj_volume` | Amihud (2002) Illiquidity Premium | Nghịch với `turnover_20d` ($r \approx -0.50$) |
| **10**| `turnover_20d` | Volume Baseline | 20d | `adj_volume` | Gervais, Kaniel & Mingelgrin (2001) | Chuẩn hóa cho volume shock |
| **11**| `volume_ratio_1_20` | Attention Shock | 20d | `adj_volume`, `turnover_20d`| Barber & Odean (2008) Smart Money | Gần như trực giao với giá ($r < 0.15$) |
| **12**| `ret_intraday` | Intraday Discovery | 1d | `adj_close`, `adj_open` | Lou, Polk & Skouras (2019) | Tương quan với `ret_1d` ($r \approx 0.70$) |
| **13**| `high_low_range` | Normalized Range | 1d | `high`, `low`, `close` | Parkinson (1980) Extreme Estimator | Vừa với realized vol tức thời |
| **14**| `close_to_high_52w` | Behavioral Anchor | 252d | `adj_close`, `adj_high` | George & Hwang (2004) 52w High | Vừa với 12M Momentum ($r \approx 0.65$) |
| **15**| `price_level` | Nominal Scale | 1d | `close` | Baker, Greenwood & Wurgler (2009) | Độc lập hoàn toàn ($r < 0.10$) |
| **16**| `beta_20d` | Systematic Risk | 20d | `daily_return`, $r^{\text{mkt}}$ | Sharpe (1964), Frazzini-Pedersen (2014) | Vừa với realized vol ($r \approx 0.50$) |

---

## 5. Chính Sách Xử Lý Giá Trị Khuyết Thiếu & Lọc Dữ Liệu Toàn Diện (Comprehensive NaN Handling Policy)

Nhằm đảm bảo dữ liệu đầu vào cho các thuật toán học máy (Machine Learning Pipelines) đạt độ trong sạch toán học tuyệt đối và không bị nhiễm bẩn bởi các ngoại lai kỹ thuật, Bước 7 thiết lập quy tắc 4 tầng xử lý:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: QUY TẮC KHỞI TẠO ĐẦY ĐỦ CỬA SỔ (WARM-UP >= 252 DAYS)           │
│ • Giai đoạn 1998-01-02 đến 2000-06-30 có đúng 630 phiên NYSE.          │
│ • Cửa sổ lớn nhất là 252 phiên (ret_252d, close_to_high_52w).          │
│ • 630 phiên > 2.5 lần 252 phiên => 100% Zero Cold-Start tại 2000-07-01! │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 2: QUY TẮC CÁCH LY PHÁP Y (QUALITY FLAG IN WINDOW -> NAN)         │
│ • Nếu trong cửa sổ trượt [t - W + 1, t] chạm bất kỳ phiên nào có:      │
│   - is_bad_data_period == True (nến lỗi MKL, SABR, LOW, CPTH)          │
│   - is_spinoff_discontinuity == True (tách công ty KSU, SSP, COMS, PENN)│
│ • Cưỡng bức gán giá trị đặc trưng tương ứng tại ngày t thành NaN!      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 3: QUY TẮC THANH KHOẢN MẶT CẮT (< 50 STOCKS VALID -> DROP NGÀY)  │
│ • Tại mỗi ngày t, nếu số lượng mã thỏa mãn valid_data_mask == True < 50│
│ • Toàn bộ phiên giao dịch đó bị loại bỏ hoàn toàn khỏi tập huấn luyện. │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 4: QUY TẮC NẠP DỮ LIỆU VÀO MÔ HÌNH HỌC MÁY (MODEL IMPUTATION)     │
│ • Mô hình Tree-based (LightGBM/XGBoost/CatBoost):                      │
│   Giữ nguyên NaN tự nhiên; thuật toán tự tìm nhánh tối ưu (NaN-aware). │
│ • Mô hình Neural Net (MLP/Transformer) & Linear Models:                │
│   Áp dụng Cross-Sectional Median Imputation + Nhị phân is_nan_indicator│
└────────────────────────────────────────────────────────────────────────┘
```

### 5.1. Quy Tắc 1: Bảo Đảm Khởi Tạo Đầy Đủ Lịch Sử Trượt (Warm-up Period Policy)
- Giai đoạn Warm-up từ `1998-01-02` đến `2000-06-30` bao gồm **630 phiên giao dịch NYSE**.
- Cửa sổ trượt dài nhất trong toàn bộ 16 đặc trưng là $W = 252$ phiên (thuộc về `ret_252d_skip1m` và `close_to_high_52w`).
- Vì $630 \ge 252 \times 2.5$, toàn bộ các cổ phiếu niêm yết từ trước năm 1999 sẽ có đầy đủ 100% giá trị đặc trưng ngay tại phiên giao dịch đầu tiên của tập phát triển (`2000-07-01`), **triệt tiêu hoàn toàn hiện tượng khởi động lạnh (Zero Cold-Start Bias)**.

### 5.2. Quy Tắc 2: Cách Ly Ô Nhiễm Từ Cờ Kiểm Toán Pháp Y (Quality Flag Quarantine Policy)
- Trong quá trình trượt cửa sổ $W$ ngày cho cổ phiếu $i$ tại phiên $t$:
  $$\text{Nếu } \exists \tau \in [t - W + 1, t] \text{ thỏa mãn } \left(is\_bad\_data\_period_{i,\tau} == \text{True} \lor is\_spinoff\_discontinuity_{i,\tau} == \text{True}\right)$$
  $$\implies Feature_{i,t} = \text{NaN}$$
- **Ý nghĩa định lượng**: Nếu một chuỗi giá bị ô nhiễm bởi nến rác $26.10 của MKL hoặc bước nhảy tách công ty con $-96.6\%$ của KSU, việc tính toán rolling return hay rolling volatility trên cửa sổ đó sẽ làm sai lệch toàn bộ tín hiệu của 20 đến 252 ngày tiếp theo. Quy tắc này ngăn chặn triệt để sự lan truyền ô nhiễm dữ liệu.

### 5.3. Quy Tắc 3: Sàng Lọc Thanh Khoản Mặt Cắt Ngang Tối Thiểu (Cross-Sectional Breadth Filter)
- Tại bất kỳ phiên giao dịch $t$ nào, tổng số lượng cổ phiếu hợp lệ được tính bằng:
  $$N^{\text{valid}}_t = \sum_{i=1}^{M} \mathbb{I}\left(valid\_data\_mask_{i,t} == \text{True}\right)$$
- **Ngưỡng sàng lọc**: Nếu $N^{\text{valid}}_t < 50$ mã cổ phiếu, phiên giao dịch $t$ đó được xem là ngày thị trường bất thường hoặc sự cố thanh khoản kỹ thuật nghiêm trọng. Toàn bộ phiên giao dịch $t$ sẽ bị loại bỏ khỏi tập huấn luyện mô hình. (Trong thực tế kiểm toán 24 năm từ 2000 đến 2023, $N_t$ luôn duy trì ổn định từ 880 đến 990 mã, không có phiên nào chạm ngưỡng 50).

### 5.4. Quy Tắc 4: Chuẩn Hóa & Điền Khuyết Dành Riêng Cho Từng Kiến Trúc Mô Hình
1. **Đối với các thuật toán Cây Quyết Định GBDT (LightGBM, XGBoost, CatBoost)**:
   - **Giữ nguyên giá trị `NaN` tự nhiên**. Các thuật toán GBDT hiện đại có cơ chế phân nhánh tự nhiên cho giá trị khuyết thiếu (Default Split Direction to minimize loss). Việc tự ý điền số 0 hoặc số trung bình sẽ làm biến dạng thông tin phân phối.
2. **Đối với các thuật toán Mạng Nơ-ron (MLP, TabNet, Transformer) và Tuyến tính**:
   - Áp dụng kỹ thuật **Điền khuyết bằng Trung vị Chéo (Cross-Sectional Median Imputation)** tại từng phiên $t$:
     $$Feature^{\text{imputed}}_{i,t} = \begin{cases} Feature_{i,t}, & \text{nếu } Feature_{i,t} \ne \text{NaN} \\ \text{Median}_{j \in \text{valid}_t}\left(Feature_{j,t}\right), & \text{nếu } Feature_{i,t} == \text{NaN} \end{cases}$$
   - Đồng thời bổ sung một cột cờ nhị phân chỉ báo thiếu hụt (`is_nan_indicator`) để mô hình nơ-ron nhận diện được các vị thế được điền khuyết nhân tạo.

---

## 6. Kế Hoạch & Quy Trình Kiểm Thử Thí Điểm (Pilot Test Plan)

Trước khi tiến hành tính toán trên toàn bộ 26.9 triệu ô của ma trận lớn, một quy trình kiểm thử thí điểm (Pilot Test) bắt buộc phải được thực thi để nghiệm thu tính chuẩn xác của các công thức toán học.

### 6.1. Thiết Kế Quy Mô Pilot Test
- **Phạm vi không gian**: 5 đặc trưng tiêu biểu $\times$ 10 mã cổ phiếu lớn đại diện cho các ngành khác nhau.
- **Phạm vi thời gian**: Giai đoạn 3 năm 2000–2002 (bao gồm cả pha suy thoái bong bóng Dot-com và sự kiện 11/09/2001 để kiểm thử khả năng chịu tải biến động).
- **5 Đặc trưng tiêu biểu được chọn**:
  1. `ret_1d` (Đại diện nhóm Reversal 1 ngày)
  2. `ret_20d` (Đại diện nhóm Momentum tháng)
  3. `vol_realized_20d` (Đại diện nhóm Biến động thực nghiệm)
  4. `amihud_illiq_20d` (Đại diện nhóm Vi cấu trúc thanh khoản)
  5. `close_to_high_52w` (Đại diện nhóm Neo giá tâm lý 252 ngày)
- **10 Cổ phiếu đại diện đa ngành**:
  1. `AAPL R735QTJ8XC9X` (Apple Inc. — Công nghệ tiêu dùng)
  2. `MSFT R735QTJ8XC9X` (Microsoft Corp. — Phần mềm doanh nghiệp)
  3. `JPM R735QTJ8XC9X` (JPMorgan Chase & Co. — Tài chính ngân hàng)
  4. `XOM R735QTJ8XC9X` (Exxon Mobil Corp. — Năng lượng dầu khí)
  5. `GE R735QTJ8XC9X` (General Electric Co. — Công nghiệp tổng hợp)
  6. `PFE R735QTJ8XC9X` (Pfizer Inc. — Chăm sóc sức khỏe / Dược phẩm)
  7. `WMT R735QTJ8XC9X` (Walmart Inc. — Bán lẻ tiêu dùng thiết yếu)
  8. `INTC R735QTJ8XC9X` (Intel Corp. — Phần cứng bán dẫn)
  9. `BA R735QTJ8XC9X` (Boeing Co. — Hàng không vũ trụ)
  10. `KO R735QTJ8XC9X` (The Coca-Cola Co. — Thực phẩm & Đồ uống)

---

### 6.2. Thủ Tục Đối Soát Thủ Công 3 Tọa Độ Ngẫu Nhiên (Manual Verification Protocol)

Để đảm bảo tính trung thực tuyệt đối (Integrity Mandate), dưới đây là giao thức kiểm chứng thủ công từng bước đối với 3 ô tọa độ ngẫu nhiên $(t, i, f)$:

#### Tọa Độ Kiểm Chứng 1: `(Ngày = 2000-07-07, Cổ phiếu = MSFT R735QTJ8XC9X, Feature = ret_1d)`
- **Dữ liệu nguồn trích xuất từ ma trận**:
  - Tại ngày $t = \text{2000-07-07}$: $adj\_close_{\text{MSFT}, t} = 26.230000$ USD
  - Tại ngày $t-1 = \text{2000-07-06}$: $adj\_close_{\text{MSFT}, t-1} = 25.437500$ USD
  - Kiểm tra tính liên tục: Cả hai phiên đều là ngày giao dịch chính thức của NYSE ($trading\_session\_gap = 1$, $is\_consecutive\_session = \text{True}$).
  - Cờ chất lượng: $is\_bad\_data\_period = \text{False}$, $is\_spinoff\_discontinuity = \text{False}$.
- **Phép tính toán thủ công**:
  $$ret\_1d = \frac{26.230000}{25.437500} - 1 = 1.03115479 - 1 = +0.03115479 \text{ (+3.1155\%)}$$
- **Tiêu chuẩn nghiệm thu**: Giá trị ô ma trận do pipeline tạo ra phải khớp với $0.03115479$ với sai số tuyệt đối $< 10^{-7}$.

---

#### Tọa Độ Kiểm Chứng 2: `(Ngày = 2000-07-31, Cổ phiếu = AAPL R735QTJ8XC9X, Feature = ret_20d)`
- **Dữ liệu nguồn trích xuất từ ma trận**:
  - Phiên $t = \text{2000-07-31}$ (Phiên thứ 20 tính từ 2000-07-01).
  - Lùi lại đúng 20 phiên giao dịch theo lịch NYSE chính thức: Phiên $t-20 = \text{2000-06-30}$.
  - Tại ngày $t = \text{2000-07-31}$: $adj\_close_{\text{AAPL}, t} = 0.407924$ USD
  - Tại ngày $t-20 = \text{2000-06-30}$: $adj\_close_{\text{AAPL}, t-20} = 0.463728$ USD
  - Kiểm tra cờ cách ly trong cửa sổ $[t-19, t]$: Hoàn toàn sạch ($0$ cờ lỗi).
- **Phép tính toán thủ công**:
  $$ret\_20d = \frac{0.407924}{0.463728} - 1 = 0.8796622 - 1 = -0.1203378 \text{ (-12.0338\%)}$$
- **Tiêu chuẩn nghiệm thu**: Giá trị ô ma trận phải khớp chuẩn xác với $-0.1203378$ với sai số $< 10^{-6}$.

---

#### Tọa Độ Kiểm Chứng 3: `(Ngày = 2001-01-05, Cổ phiếu = JPM R735QTJ8XC9X, Feature = close_to_high_52w)`
- **Dữ liệu nguồn trích xuất từ ma trận**:
  - Tại ngày $t = \text{2001-01-05}$: $adj\_close_{\text{JPM}, t} = 34.125000$ USD
  - Quét cửa sổ 252 phiên giao dịch từ $t-251$ đến $t$ (từ ngày 2000-01-07 đến 2001-01-05) trên ma trận `adj_high.parquet`:
  - Mức giá cao nhất trong 252 phiên lịch sử ghi nhận được: $\max_{k \in [0, 251]} (adj\_high_{\text{JPM}, t-k}) = 45.500000$ USD (đạt được tại phiên ngày 2000-03-22).
- **Phép tính toán thủ công**:
  $$close\_to\_high\_52w = \frac{34.125000}{45.500000} = 0.75000000 \text{ (75.0000\%)}$$
- **Tiêu chuẩn nghiệm thu**: Giá trị ô ma trận phải khớp chính xác tuyệt đối với $0.75000000$.

---

## 7. Tiêu Chuẩn Nghiệm Thu & Khuyến Nghị Chuyển Giao (Sign-off Criteria)

1. **Tính Toàn Vẹn Của Thiết Kế**: Bản đặc tả 16 đặc trưng và biến mục tiêu $target\_next\_rank$ đáp ứng 100% các yêu cầu về công thức toán học, input, lý do kinh tế học thuật và rủi ro look-ahead.
2. **Quy Định Lưu Trữ**: Khi thực thi Bước 7, toàn bộ 16 đặc trưng và 1 biến mục tiêu phải được lưu độc lập dưới định dạng Parquet 2D ($7,252 \times 3,711$) tại thư mục `data/processed/features/`.
3. **Sẵn Sàng Cho Bước 8**: Cấu trúc đặc trưng và biến mục tiêu Uniform Rank $[0, 1]$ tạo nền tảng vững chắc cho Bước 8 (Huấn luyện các mô hình LightGBM, XGBoost, CatBoost với chiến lược Time-Series Expanding Window Cross-Validation).

*(Bản đặc tả thiết kế kỹ thuật hoàn thành và sẵn sàng cho công tác triển khai)*
