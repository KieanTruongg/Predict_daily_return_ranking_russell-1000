# Russell 1000 — Free Point-in-Time Data Notes

## 1. Russell 1000 chọn theo tiêu chí gì?

Russell 1000 nhằm đại diện cho **large-cap segment của US equity market**. Logic cốt lõi của Russell US indexes là xác định eligible US securities rồi **rank theo market capitalization** vào Rank Day. Russell 1000 chứa khoảng 1,000 cổ phiếu lớn nhất theo methodology của Russell.

Nói ngắn gọn:

\[
\text{US eligible stocks}
\xrightarrow{\text{market-cap ranking}}
\boxed{\text{Russell 1000}}
\]

Do đó nó **không chọn stock dựa trên past return/performance**.

Tất nhiên Russell còn eligibility rules, free float, corporate actions, banding để giảm turnover, v.v.; nên không đơn giản tuyệt đối là sort market cap rồi lấy đúng 1,000. Nhưng với câu hỏi bias, điểm quan trọng là **membership không được lựa chọn vì stock trước đó tăng giá tốt hay có profitability tốt**.

Đặc biệt Russell xác định membership dựa trên information tại Rank Day; ví dụ năm 2026 Rank Day là 30/4 và market cap tại close ngày đó được dùng để xác định eligibility.

Official reference:
- FTSE Russell / LSEG Russell Reconstitution: https://www.lseg.com/en/ftse-russell/russell-reconstitution
- 2026 schedule: https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/russell-reconstitution-2026-schedule

---

## 2. Lấy current/full list FREE

Có hai ETF full-replication/tracking rất hữu ích.

### iShares Russell 1000 ETF — IWB

IWB track Russell 1000 và BlackRock cung cấp **Download Holdings CSV** miễn phí.

Trang:
https://www.ishares.com/us/products/239707/ishares-russell-1000-etf

CSV holdings có các trường hữu ích như:

```text
Ticker
Name
Sector
Asset Class
Market Value
Weight
Quantity
CUSIP
ISIN
SEDOL
```

Do đó ngoài ticker còn có CUSIP/ISIN/SEDOL, hữu ích cho việc identify securities.

### Vanguard Russell 1000 ETF — VONE

VONE cũng track Russell 1000. Vanguard mô tả fund sử dụng **full-replication strategy**.

Trang:
https://advisors.vanguard.com/investments/products/vone/vanguard-russell-1000-etf

Số holdings của ETF có thể không bằng chính xác số securities trong benchmark do cash, derivatives, tracking differences, multiple share classes, corporate actions, v.v.

Do đó:

\[
Holdings(IWB/VONE)\approx Russell1000
\]

chứ không nên mặc định mathematically identical.

Tuy nhiên, để có một **free approximation rất sát của full constituent list tại một thời điểm**, đây là nguồn rất hữu ích.

---

## 3. Historical point-in-time holdings của ETF

### Vanguard VONE

Website Vanguard hiện expose **monthly full-holdings snapshots** gần đây, ví dụ:

```text
31-Jul-2026
30-Jun-2026
31-May-2026
30-Apr-2026
...
31-Aug-2025
```

và cho phép **Export full holdings**.

VONE inception từ **20/09/2010**, nên fund holdings tồn tại từ 2010. Tuy nhiên, điều đó **không có nghĩa Vanguard public toàn bộ historical holdings archive từ 2010 trên website hiện tại**.

Hiện chưa xác nhận được rằng public full-holdings endpoint cho phép arbitrary requests sâu về các năm cũ.

### iShares IWB

IWB cũng cho historical holdings snapshots. UI hiện expose một số recent dates, ví dụ:

```text
02-Sep-2026
31-Aug-2026
30-Jun-2026
31-Dec-2025
```

và mỗi snapshot có downloadable holdings.

Tuy nhiên, chưa có bằng chứng đủ chắc rằng BlackRock public arbitrary historical full holdings nhiều năm về trước.

### Kết luận về ETF archive

> **Current/recent point-in-time: solved. Deep historical point-in-time: ETF archive một mình chưa solved.**

---

## 4. Suy ngược annual point-in-time Russell 1000

FTSE Russell publish **additions/deletions** trong annual reconstitution.

Giả sử có full snapshot:

\[
R_{2026}
\]

và annual reconstitution cho biết:

\[
A_{2026}=\{\text{additions}\}
\]

\[
D_{2026}=\{\text{deletions}\}
\]

thì:

\[
R_{2026}
=
(R_{2025}-D_{2026})\cup A_{2026}
\]

Do đó có thể suy ngược:

\[
\boxed{
R_{2025}
=
(R_{2026}-A_{2026})\cup D_{2026}
}
\]

Sau đó tiếp tục:

\[
R_{2024}
=
(R_{2025}-A_{2025})\cup D_{2025}
\]

v.v.

Conceptually:

```text
          IWB / VONE
              |
              v
     Full Russell 1000-like
          snapshot 2026
              |
       reverse 2026
              |
              v
          R1000 2025
              |
       reverse 2025
              |
              v
          R1000 2024
              |
             ...
```

Official Russell reconstitution information:
https://www.lseg.com/en/ftse-russell/russell-reconstitution

---

## 5. Important caveat khi reconstruct

Annual additions/deletions **không nhất thiết đủ để reconstruct daily-exact membership**.

Các complication có thể gồm:

- IPO additions
- mergers
- acquisitions
- delistings
- ticker/security changes
- intra-year corporate actions
- other exceptional constituent changes

Vì vậy nếu mục tiêu là:

> exact Russell 1000 membership cho từng trading day

thì cần track thêm các intra-year changes.

Nhưng nếu requirement chỉ là:

> **annual point-in-time Russell 1000 snapshot**

thì bài toán đơn giản hơn nhiều.

Có thể chọn một thời điểm chuẩn mỗi năm, chẳng hạn **ngay sau annual reconstitution**, rồi reconstruct các annual snapshots. Khi đó annual additions/deletions là thành phần chính, sau đó reconcile các exceptional corporate actions/IPO changes nếu chúng ảnh hưởng giữa các chosen snapshot dates.

---

# Full process

## A. Ý nghĩa của universe

\[
\boxed{\text{Russell 1000 ≈ 1,000 largest eligible US stocks}}
\]

Selection chủ yếu dựa trên:

- market capitalization;
- Russell eligibility/investability methodology;
- point-in-time information tại Rank Day.

Nó **không lựa chọn constituents dựa trên historical stock-return performance**.

## B. Full list hiện tại — FREE

Download holdings từ:

1. **iShares Russell 1000 ETF (IWB)**  
   https://www.ishares.com/us/products/239707/ishares-russell-1000-etf

2. **Vanguard Russell 1000 ETF (VONE)**  
   https://advisors.vanguard.com/investments/products/vone/vanguard-russell-1000-etf

VONE đặc biệt hữu ích vì Vanguard mô tả strategy là full replication.

## C. Recent point-in-time list

- VONE: monthly historical holdings snapshots hiện được expose cho các tháng gần đây.
- IWB: một số recent historical holdings snapshots.

## D. Older annual point-in-time lists

Lấy một full snapshot \(R_T\), rồi dùng official Russell annual additions/deletions để đi ngược:

\[
\boxed{
R_{t-1}=(R_t-A_t)\cup D_t
}
\]

Sau đó lưu thành:

```text
russell1000_2026.csv
russell1000_2025.csv
russell1000_2024.csv
...
```

## Overall conclusion

Với requirement:

**FREE + annual point-in-time Russell 1000**

phương án này có tính khả thi khá cao.

Phần labor chính còn lại là:

1. lấy một full recent snapshot từ IWB/VONE;
2. thu thập historical annual Russell additions/deletions;
3. reverse annual membership;
4. reconcile corporate-action / IPO / exceptional cases nếu cần.

Không cần reconstruct toàn bộ ~1,000 securities của từng năm từ đầu.
