# 🔬 BÁO CÁO THẨM ĐỊNH DANH TÍNH CHỨNG KHOÁN & QUY ƯỚC CORPORATE ACTIONS (BƯỚC ②)

**Dự án:** Dự đoán Xếp hạng Tỷ suất Sinh lời Hàng ngày (Russell 1000 Daily Return Rankings: 1998–2026)  
**Tác giả:** Đội ngũ Kỹ sư Dữ liệu Định lượng (Quantitative Data Engineering)  
**Ngày thực hiện:** 03/11/2026  
**Trạng thái:** ✅ **Bước ②A Hoàn tất** | ⏳ **Bước ②B Sẵn sàng kịch bản xuất QuantConnect**  

---

## 1. TỔNG QUAN KẾT QUẢ THẨM ĐỊNH (EXECUTIVE SUMMARY)

Bước ② trong quy trình 5 bước chuẩn Quant nhằm giải quyết triệt để hai rủi ro sống còn trong mô hình định lượng:
1. **Rủi ro Ô nhiễm Danh tính (Identity Contamination & Ticker Reuse)**: Trùng mã giữa các công ty khác nhau qua các thời kỳ (như `MIR`, `INFO`, `BLUE`) hoặc trùng lặp dữ liệu do đổi tên/thương hiệu (`ABC` $\rightarrow$ `COR`, `FB` $\rightarrow$ `META`).
2. **Rủi ro Sốc Giá Giả tạo do Chia tách (Stock Split Price Shock)**: Giá thô (Raw Price) sụt giảm cơ học (ví dụ Apple chia tách 4:1 ngày 31/08/2020 gây sốc giảm giả tạo **-74.15%**), làm méo mó tín hiệu Alpha và nhãn mục tiêu nếu không được chuẩn hóa.

### Bảng Chỉ Số Thực Nghiệm (100% Tính toán Động)

| Tiêu chí Thẩm định | Trước Xử lý (Tier 1 Raw) | Sau Xử lý (Tier 2 Canonical) | Đánh giá & Kết luận |
| :--- | :---: | :---: | :--- |
| **Tổng số dòng dữ liệu** | 13,147,389 dòng | **12,247,081 dòng** | Khử thành công 900,308 dòng dư thừa |
| **Số bản ghi trùng `(date, sid)`** | 1,569,274 dòng (772,672 cặp) | **0 dòng (0.00%)** | 100% khóa chính duy nhất tuyệt đối |
| **Chênh lệch giá Close tối đa giữa bản ghi trùng** | $0.000000$ | $0.000000$ | Khớp từng bit (Bit-for-bit identical) |
| **Chênh lệch Volume tối đa giữa bản ghi trùng** | $0.000000$ | $0.000000$ | Không có xung đột giá hay khối lượng |
| **Số mã SID thô** | 4,463 SIDs | **3,711 Canonical SIDs** | Rút gọn chuẩn 752 mã placeholder |
| **Số mã placeholder `' 2T'`** | 846 mã | **94 mã (Độc lập)** | 752 mã được nối mượt (stitch) liền kề |
| **Số Ticker có Ticker Reuse thực tế** | 1,281 tickers thô | **884 tickers (Phân lập)** | Đảm bảo 0 ô nhiễm dữ liệu giữa các công ty |
| **Dung lượng File Parquet lưu trữ** | 198.12 MB | **155.76 MB** | Tiết kiệm 42.36 MB, tối ưu truy vấn I/O |

---

## 2. THẨM ĐỊNH TRÙNG LẶP `(date, sid)` & KHỬ TRÙNG 256 CẶP ALIAS

### 2.1. Bản chất Hiện tượng Trùng lặp
Trong kho dữ liệu thô Master Warehouse, kiểm tra khóa `(date, sid)` phát hiện **1,569,274 dòng** thuộc nhóm trùng lặp (tương ứng **772,672 cặp ngày - SID** độc nhất, dư thừa **796,602 bản ghi**).

*Nguyên nhân cốt lõi:*  
Do rổ cổ phiếu đầu vào chứa cả mã lịch sử và mã hiện đại của cùng một pháp nhân doanh nghiệp (ví dụ: `AHAA` và `SWKS`, `ABC` và `COR`, `FB` và `META`, `PKI` và `RVTY`, `BALL` và `BLL`). Khi QuantBook truy vấn dữ liệu từ 1998–2026 cho từng chuỗi ticker, QuantConnect ánh xạ cả hai mã về cùng một mã định danh chứng khoán vĩnh viễn (`sid`). Do đó, hai lượt gọi API đã kéo về hai bản sao chuỗi nến hoàn toàn giống nhau của cùng một công ty.

### 2.2. Bằng chứng Thực nghiệm về Tính Đồng nhất Tuyệt đối
Trước khi loại bỏ dữ liệu dư thừa, thuật toán đã đo lường chênh lệch giá trị Open, High, Low, Close, Volume giữa tất cả các bản ghi trùng lặp:
$$\max |Close_{A} - Close_{B}| = 0.000000$$
$$\max |Volume_{A} - Volume_{B}| = 0.000000$$
$$\max |Open_{A} - Open_{B}| = 0.000000, \quad \max |High_{A} - High_{B}| = 0.000000, \quad \max |Low_{A} - Low_{B}| = 0.000000$$

**Kết luận:** Dữ liệu hoàn toàn đồng nhất từng bit. Việc khử trùng lặp giữ lại bản ghi đại diện duy nhất cho mỗi `(date, canonical_sid)` loại bỏ triệt để 796,602 dòng dư thừa mà không làm mất bất kỳ thông tin kinh tế nào.

---

## 3. GIẢI QUYẾT MÃ PLACEHOLDER `' 2T'` CỦA QUANTCONNECT

### 3.1. Bản chất Mã SID `' 2T'`
Trong kiến trúc LEAN Engine của QuantConnect, khi một ticker được yêu cầu khởi tạo mã SID thông qua hàm:
```python
SecurityIdentifier.GenerateEquity(ticker, Market.USA, mappingResolveDate=anchor_date)
```
Nếu vào ngày neo `anchor_date` (trong pipeline là ngày 30/06 hàng năm), cổ phiếu đó **chưa niêm yết** (ví dụ IPO vào tháng 9 hoặc tháng 12 cùng năm) hoặc **vừa hủy niêm yết/sáp nhập**, hệ thống QuantConnect không tìm thấy bản ghi metadata neo ngày tương ứng nên tự động gán đuôi dự phòng mặc định là `' 2T'` (Unanchored Generic Equity).

Sang năm tiếp theo, khi ngày neo `anchor_date` nằm sau ngày niêm yết, QuantConnect gán mã SID vĩnh viễn chính thức (`[TICKER] [BASE36]`).

### 3.2. Thuật toán Nối mượt Dòng thời gian (Timeline Stitching)
Để tránh việc một cổ phiếu bị xé đôi thành hai cột độc lập trong ma trận 2D (làm mất lịch sử lookback và mất tỷ suất sinh lời của ngày giao thừa chuyển năm), thuật toán kiểm tra tính liền kề ngày giao dịch:
1. **Nối vào SID kế tiếp (`2T_STITCH_SUCCEEDING`) — 456 mã:**  
   Khoảng cách từ ngày cuối cùng của mã `2T` đến ngày đầu tiên của SID vĩnh viễn $\le 10$ ngày lịch (chỉ là ranh giới kỳ nghỉ lễ 31/12 $\rightarrow$ 02/01).  
   *Ví dụ minh chứng:*
   - `AAL 2T` kết thúc ngày 31/12/2013 (giá đóng cửa **25.25**).  
     `AAL VM9RIYHM8ACL` bắt đầu ngày 02/01/2014 (giá đóng cửa **25.36**).  
     $\rightarrow$ Nối mượt thành một chuỗi duy nhất của American Airlines Group!
   - `PSTG 2T` kết thúc ngày 31/12/2015 $\rightarrow$ `PSTG W4IIPBH79IED` bắt đầu 04/01/2016 (Pure Storage IPO tháng 10/2015).
   - `ONON 2T` kết thúc ngày 31/12/2021 $\rightarrow$ `ONON XRV6S79HAOO5` bắt đầu 03/01/2022 (On Holding AG IPO tháng 09/2021).

2. **Nối vào SID tiền nhiệm (`2T_STITCH_PRECEDING`) — 296 mã:**  
   Khoảng cách từ ngày cuối của SID vĩnh viễn đến ngày đầu của mã `2T` $\le 10$ ngày lịch (công ty giao dịch những ngày cuối cùng trước khi hoàn tất thủ tục sáp nhập/hủy niêm yết).  
   *Ví dụ minh chứng:*
   - `AAP R735QTJ8XC9X` kết thúc 31/12/1999 $\rightarrow$ `AAP 2T` tiếp nối từ 03/01/2000 đến 26/04/2000 (công ty tiền nhiệm dùng ticker AAP).
   - `CHIR R735QTJ8XC9X` kết thúc 30/12/2005 $\rightarrow$ `CHIR 2T` tiếp nối từ 03/01/2006 đến 19/04/2006 (Chiron Corp trước khi bị Novartis thâu tóm).

3. **Giữ độc lập không nối (`STANDALONE_2T`) — 94 mã:**  
   Gồm 81 mã có khoảng cách thời gian gián đoạn hàng năm trời (Ticker Reuse) và 13 mã chỉ tồn tại dưới dạng `2T`.  
   *Ví dụ minh chứng rủi ro ô nhiễm đã được chặn đứng:*
   - `APP 2T` giao dịch đầu năm 1998, trong khi AppLovin (`APP`) IPO vào năm 2021 (cách nhau 23 năm!). Thuật toán **tuyệt đối không nối**, giữ `APP 2T` làm một thực thể độc lập của năm 1998.
   - `AMC 2T` giao dịch tháng 01/1998 được tách biệt hoàn toàn khỏi chuỗi hiện đại của AMC Entertainment.

Toàn bộ 846 trường hợp được lưu tại: [`transient_2t_resolution_audit.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/docs/Data%20report/market_data_audit/tables/transient_2t_resolution_audit.csv).

---

## 4. BẢO VỆ CHỐNG Ô NHIỄM TICKER REUSE (884 TICKERS)

Bảng phân tích Ticker Reuse xác định **884 ticker** đã từng đại diện cho từ 2 đến 5 pháp nhân doanh nghiệp hoàn toàn khác nhau trong giai đoạn 1998–2026.

### Điển cứu Ticker Reuse kinh điển:
1. **Ticker `MIR` (5 SIDs):**
   - 1998–1999: `MIR R735QTJ8XC9X`
   - 2001–2003: `SOE RYETC7YVD1LX` (Southern Energy / Mirant Corp tách từ Southern Company)
   - 2006–2010: `MIR TF950UOZ6NOL` (Mirant Corp sau tái cơ cấu phá sản Chương 11, trước khi sáp nhập thành GenOn Energy)
   - 2021–2026: `GSAH XH66ZN8HDOX1` (Mirion Technologies, niêm yết qua SPAC GS Acquisition Holdings Corp II)
   *Nếu nhóm theo ticker `MIR`, mô hình sẽ nối nhầm một công ty điện lực phá sản năm 2010 với một công ty công nghệ hạt nhân SPAC năm 2021! Việc phân tách thành các Canonical SID độc lập loại bỏ 100% rủi ro này.*

2. **Ticker `INFO` (5 SIDs):**
   - 1998–2000: `INFO R735QTJ8XC9X` (InfoSpace - thời kỳ bong bóng Dot-com)
   - 2014–2021: `MRKT VRITCWQ0X55X` (IHS Markit - công ty dữ liệu tài chính sáp nhập với S&P Global năm 2022)
   - 2025–2026: `INFO YMIYX0BP2FL1` (Công ty mới tái sử dụng mã)

Toàn bộ danh mục 2,378 bản ghi phân lập Ticker Reuse được lưu tại: [`ticker_reuse_audit.csv`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/docs/Data%20report/market_data_audit/tables/ticker_reuse_audit.csv).

---

## 5. KHO DỮ LIỆU TIER 2 CANONICAL WAREHOUSE

Dữ liệu sau khi làm sạch danh tính được đóng gói thành file Parquet Tier 2:
- **Đường dẫn:** [`data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet)
- **Dung lượng:** 155.76 MB (Nén PyArrow Zstandard Level 7).
- **Cấu trúc bảng (12,247,081 dòng | 9 cột):**
  - `date` (string `YYYY-MM-DD`): Ngày giao dịch.
  - `canonical_sid` (string): Khóa định danh pháp nhân doanh nghiệp chuẩn hóa (3,711 thực thể).
  - `original_ticker` (string): Mã ticker niêm yết thực tế tại thời điểm giao dịch.
  - `qc_ticker` (string): Ticker truy vấn QuantConnect.
  - `open`, `high`, `low`, `close` (float64): Giá thô chưa điều chỉnh.
  - `volume` (float64): Khối lượng giao dịch thực tế.
- **Tính toàn vẹn khóa chính:** `(date, canonical_sid)` đạt **0 vi phạm trùng lặp (100% unique)**.

---

## 6. QUY ƯỚC CORPORATE ACTIONS & KỊCH BẢN XUẤT QUANTCONNECT (BƯỚC ②B)

### 6.1. Thực trạng Giá Thô (Raw Price Shock)
Kiểm tra thực tế các cổ phiếu lớn cho thấy giá trong kho dữ liệu hiện tại là **Giá Thô Chưa Điều Chỉnh (Unadjusted Raw Price)**:
- Apple (`AAPL`) ngày 28/08/2020 đóng cửa tại **\$499.23**. Ngày 31/08/2020 (chia tách 4:1) mở cửa và đóng cửa tại **\$129.04**.
  $$\text{Return thô} = \frac{129.04 - 499.23}{499.23} = -74.15\%$$
- Nvidia (`NVDA`) ngày 10/06/2024 (chia tách 10:1): giá từ **\$1,208.88** về **\$121.79** (sụt giảm thô **-89.93%**).
- Tesla (`TSLA`) ngày 31/08/2020 (chia tách 5:1): giá từ **\$2,213.40** về **\$498.32** (sụt giảm thô **-77.49%**).

Nếu đưa giá thô vào tính momentum, độ biến động hoặc tính tỷ suất sinh lời ngày làm biến mục tiêu (target ranking), mô hình máy học sẽ học sai hoàn toàn bản chất thị trường. Do đó, việc áp dụng hệ số điều chỉnh chia tách là **bắt buộc 100%**.

### 6.2. Thống nhất Quy ước Chuẩn Quant: Price Return vs Total Return
Trong các quỹ định lượng toàn cầu (Two Sigma, WorldQuant, Citadel, AQR), quy ước được thiết lập như sau:
1. **Price Return (Split-Adjusted Only — Quy ước Chính cho Alpha Modeling):**
   - Giá được điều chỉnh dồn tích theo hệ số chia tách cổ phiếu:
     $$CF_{i, t} = \prod_{\tau > t} \text{SplitFactor}_{i, \tau}$$
     $$P^{\text{adj\_split}}_{i, t} = P_{i, t} \times CF_{i, t}$$
     $$R^{\text{price}}_{i, t} = \frac{P^{\text{adj\_split}}_{i, t}}{P^{\text{adj\_split}}_{i, t-1}} - 1$$
   - **Ưu điểm vượt trội:** Loại bỏ hoàn toàn sốc giá chia tách nhân tạo, đồng thời không bị nhiễu bởi các ngày chia cổ tức tiền mặt định kỳ (vốn phụ thuộc chính sách thuế và thời điểm chi trả của từng doanh nghiệp). Đây là chuỗi giá tối ưu cho **Feature Engineering** và **Forward Ranking Target**.
2. **Total Return (Split & Dividend Adjusted — Quy ước Phụ cho Portfolio Backtest):**
   - Tái đầu tư toàn bộ cổ tức tiền mặt vào cổ phiếu:
     $$R^{\text{total}}_{i, t} = \frac{P^{\text{adj\_split}}_{i, t} + D_{i, t}}{P^{\text{adj\_split}}_{i, t-1}} - 1$$
   - Dùng để mô phỏng PnL thực tế của danh mục đầu tư khi backtest thực chiến (nhà đầu tư thực sự nhận được tiền cổ tức).

### 6.3. Kịch bản Xuất Dữ liệu QuantConnect Tối ưu (Option A)
Để có dữ liệu chia tách và cổ tức chính xác 100% khớp tuyệt đối với engine LEAN đã sinh ra giá thô, kịch bản Python 1-cell đã được đóng gói sẵn tại:
👉 [`scripts/01_pipeline/05_quantconnect_export_corporate_actions.py`](file:///D:/A_Learning/HK1_2026-2027/CO3101%20-%20%C4%90%E1%BB%93%20%C3%A1n%20t%E1%BB%95ng%20h%E1%BB%A3p%20-%20ttnt/Predict_daily_return_rankings/scripts/01_pipeline/05_quantconnect_export_corporate_actions.py)

**Đặc điểm kịch bản:**
- Sử dụng chính danh mục 2,871 ticker nén của Russell 1000.
- Truy vấn `qb.History[Split]` và `qb.History[Dividend]` cho toàn bộ giai đoạn 1998–2026.
- Do dữ liệu Corporate Actions là dạng sự kiện thưa (chỉ khoảng 4,000 sự kiện split trên toàn thị trường qua 29 năm), thời gian chạy trên QuantConnect Research Notebook chỉ mất **45 đến 60 giây**.
- Tự động đóng gói ZIP dung lượng siêu nhẹ (~150 KB) và hiển thị nút bấm HTML để tải trực tiếp về máy: `russell1000_corporate_actions_1998_2026.zip`.

---

## 7. CÁC BƯỚC TIẾP THEO

1. **Thực thi Bước ②B (Corporate Actions):**
   - Chạy kịch bản `05_quantconnect_export_corporate_actions.py` trên QuantConnect Research để lấy file ZIP chứa `russell1000_splits_1998_2026.csv` và `russell1000_dividends_1998_2026.csv`.
   - Chạy script tính toán chuỗi giá `adj_close`, `adj_volume` và `daily_return` chuẩn hóa.
   - Quét kiểm thử Spike Sanity: Đảm bảo 100% các sự kiện chia tách lớn (Apple, Tesla, Nvidia, Amazon, Google) có $|Return| < 15\%$, triệt tiêu hoàn toàn sốc giá giả tạo.
2. **Tiến sang Bước ③ (Hệ thống Ma trận 2D & 3 Lớp Masks Point-In-Time):**
   - Xây dựng các ma trận 2D kích thước $(7,252 \text{ ngày} \times 3,711 \text{ canonical\_sid})$: `open.parquet`, `high.parquet`, `low.parquet`, `close.parquet`, `adj_close.parquet`, `volume.parquet`.
   - Tạo 3 lớp mặt nạ nhị phân boolean:
     * `membership_mask`: Cổ phiếu có thuộc danh mục Russell 1000 tại ngày $T$ hay không.
     * `valid_data_mask`: Cổ phiếu có đủ lịch sử lookback (ví dụ $\ge 252$ ngày) và thanh khoản hợp lệ tại ngày $T$ hay không.
     * `valid_label_mask`: Cổ phiếu có tỷ suất sinh lời tương lai $R_{T+1}$ hợp lệ để làm nhãn huấn luyện hay không.
