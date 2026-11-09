# V1 · Đọc kết quả dự báo và mô phỏng danh mục

Đọc phần này sau khi đã hiểu cách dự án tạo dữ liệu, đặc trưng, nhãn và huấn luyện mô hình. Hai câu hỏi xuyên suốt là *mô hình có xếp hạng tốt hơn mức tương quan bằng 0 trên dữ liệu ngoài mẫu không?* và *đem điểm xếp hạng đó đi mua một danh mục cụ thể thì kết quả ra sao?*

## 1. Từ mô hình đã học đến bảng dự báo ngoài mẫu

**Out-of-sample (OOS), hay ngoài mẫu**, là giai đoạn đứng sau tập dùng để phát triển và huấn luyện mô hình. Ý tưởng là đặt mô hình vào tình huống phải dự đoán trên những phiên tương lai so với lúc nó được huấn luyện. Trong v1, nhóm chọn cấu hình trên Development, tức tập phát triển 2000–2023, rồi **refit**, tức huấn luyện lại trên toàn bộ các dòng đủ điều kiện của tập này. Khi chạy OOS, các hệ số của Ridge, bộ chuẩn hóa đi kèm và các cây của GBDT được giữ nguyên. Đó là **model freeze**, tức đóng băng mô hình. Mỗi ngày đầu vào vẫn được cập nhật theo dữ liệu mới có đến cuối phiên.

Ví dụ phiên (T=02/01/2024), sau khi có giá đóng cửa và khối lượng của phiên đó, hai mô hình dùng 13 đặc trưng để tạo điểm cho từng mã. Lợi suất thực tế sẽ dùng giá đóng cửa của **phiên giao dịch kế tiếp** (T+1=03/01/2024). (T+1) có thể cách (T) nhiều ngày lịch nếu có cuối tuần hoặc ngày nghỉ.

Một dòng dự báo được nhận diện bởi ngày tín hiệu `date` và `canonical_sid`, tức mã định danh chứng khoán dùng xuyên qua các thay đổi mã giao dịch đã được xử lý trong v1. Dòng chứa các đặc trưng và các điểm `ridge_score`, `gbdt_score`. Cột `ret_20d` là điểm của **benchmark**, tức tín hiệu đối chứng để biết mô hình học máy làm được gì so với một quy tắc đơn giản. Đối chứng v1 xếp mã theo lợi suất 20 phiên đã qua. Đây là điểm số, không phải xác suất thắng hay tỷ suất sinh lời dự kiến.

**Inference eligibility** là điều kiện một mã được nhận điểm ở (T). Mã phải thuộc tập thành viên nghiêm ngặt của v1, có nến (T) sạch và liên tục, Close và Volume hữu hạn dương, đủ 13 đặc trưng hữu hạn. Điều kiện **được chấm** lại cần thêm nhãn lợi suất hợp lệ khi đã quan sát (T+1). Cách tách hai việc này ngăn chuyện dùng dữ liệu ngày mai để quyết định hôm nay sẽ dự báo cho mã nào. Trong mã nguồn, bảng dự báo được xuất trước khi ghép nhãn. Ở bước tính Rank IC, ba tín hiệu được chấm trên cùng các mã hợp lệ trong mỗi phiên.

Phạm vi **OOS chính** là 624 ngày tín hiệu từ 02/01/2024 đến 29/06/2026, với 624 ngày kết quả từ 03/01/2024 đến 30/06/2026. Tính theo ngày kết quả, nhóm 2024 có 251 phiên, 2025 có 250 và nửa đầu 2026 có 123. Nếu nhóm theo ngày tín hiệu, số phiên là 252, 250 và 122. Ngày tín hiệu 31/12/2024 nằm trong năm 2024 nhưng ngày kết quả thuộc 2025, và tương tự ở ranh giới 2025–2026. Báo cáo chính dùng mốc nhãn để nằm trọn trước giai đoạn phải dựa vào tệp thành viên `2026.xls` ghi danh mục tháng 9/2026. Kết quả trên giai đoạn sau mốc này là phân tích mở rộng riêng.

**Xem trong repo.** [Pipeline suy luận và ghép nhãn](../../src/models/oos_prediction_pipeline.py) · [Script chạy OOS](../../scripts/01_pipeline/28_run_oos_evaluation.py) · [Báo cáo OOS](../reports/baseline/oos_evaluation_report.md) · [CSV từng phiên](../../outputs/reports/oos_daily_ic_2024_2026.csv).

## 2. Rank IC đo gì và đọc kết quả thế nào?

**Rank IC** là *Rank Information Coefficient*, trong bài là hệ số tương quan thứ hạng Spearman. Tương quan Spearman đo hai dãy có cùng trật tự tương đối tới mức nào. Ở mỗi ngày (T), dự án lấy điểm của các mã hợp lệ và xếp hạng. Dự án cũng xếp hạng chính các mã đó theo lợi suất thực tế Close (T) đến Close (T+1). Sau đó lấy tương quan Pearson, tức hệ số đo mức độ đồng biến tuyến tính, giữa hai dãy **thứ hạng**. Các giá trị bằng nhau nhận hạng trung bình.

Ví dụ có ba mã A, B, C. Theo điểm dự báo, thứ tự từ cao xuống thấp là A, B, C. Nếu lợi suất thực tế theo thứ tự đó là 3%, 1%, −2% thì hai thứ tự trùng nhau và IC bằng +1. Nếu thứ tự thực tế là C, B, A, IC bằng −1. Nếu thực tế là A, C, B, thì IC bằng +0,5. Điểm số dự báo 0,52 và 0,51 cho hai mã đầu vẫn đủ để xếp thứ tự. Độ lớn chênh lệch điểm không phải chênh lệch lợi suất. Nếu điểm của tất cả mã bằng nhau, dãy thứ hạng không có biến động để tính tương quan, nên kết quả được để thiếu.

**Mean Rank IC** là trung bình số học của Rank IC các phiên. Mỗi phiên có trọng số bằng nhau. **Tỷ lệ phiên IC dương** là số phiên có IC lớn hơn 0 chia cho số phiên được chấm. Giá trị +0,02305 là một hệ số tương quan thứ hạng trung bình dương nhỏ. Nó không phải 2,305% cổ phiếu đoán đúng, lợi suất 2,305%, hay tỉ lệ giao dịch lời.

- **Ridge.** Mean IC +0,023050, IC dương 352/624 phiên, tương đương 56,41%. Annualized IC IR +2,28, t-stat +3,58 và p-value hai phía xấp xỉ 0,00037.
- **GBDT.** Mean IC +0,020403, IC dương 351/624 phiên, tương đương 56,25%. Annualized IC IR +2,18, t-stat +3,43 và p-value hai phía xấp xỉ 0,00065.
- **`ret_20d`.** Mean IC −0,004393, IC dương 304/624 phiên, tương đương 48,72%. Annualized IC IR −0,41, t-stat −0,64 và p-value hai phía xấp xỉ 0,522.

**Annualized IC IR**, tức tỷ số thông tin của chuỗi IC quy đổi năm, được tính bằng Mean IC chia độ lệch chuẩn mẫu của IC theo ngày rồi nhân √252. 252 là số phiên quy ước trong một năm. Chỉ số này so mức IC bình quân với mức dao động của IC, dùng đơn vị quy đổi năm. Nó đo chuỗi IC, trong khi **Sharpe** ở phần sau dùng chuỗi lợi suất danh mục.

**Kiểm định t một mẫu** hỏi liệu chuỗi IC quan sát được có tương thích với giả thuyết H₀ rằng kỳ vọng Mean IC bằng 0 hay không. T-stat trong v1 bằng Mean IC chia độ lệch chuẩn mẫu rồi nhân √624. **P-value hai phía** là xác suất, giả sử H₀ và các điều kiện kiểm định đúng, quan sát t-stat có độ lớn ít nhất như đã thấy, theo cả chiều dương lẫn âm. Với phép kiểm định đó, hai mô hình đều cho p < 0,001. Chuỗi IC tài chính có thể phụ thuộc giữa các phiên, trong khi phép kiểm định t thông thường dùng sai số chuẩn theo giả định độc lập. V1 chưa đối chiếu độ nhạy khi cho phép phụ thuộc theo thời gian. Hai p-value trên cũng trả lời hai phép so với 0. Muốn biết chênh lệch Ridge với GBDT có ý nghĩa thống kê hay không, cần xét trực tiếp chuỗi hiệu IC theo từng ngày.

**Cách đọc hai hình IC.** Hình cột theo ngày kết quả cho thấy Ridge khoảng 0,03365 → 0,01814 → 0,01140 và GBDT khoảng 0,03336 → 0,01397 → 0,00704 trong ba giai đoạn. Hai chuỗi có Mean IC thấp hơn ở các giai đoạn sau. GBDT cũng thấp hơn `ret_20d` ở nửa đầu 2026, dù trung bình toàn bộ 624 phiên cao hơn. **Rolling IC**, tức trung bình IC trên một cửa sổ trượt, giúp quan sát biến động trung hạn. Hình dùng tối đa 63 phiên và bắt đầu khi đủ 21 phiên. Các cửa sổ kề nhau chia sẻ phần lớn quan sát. Hình có giá trị mô tả. Các thay đổi thị trường hay thời gian từ lúc huấn luyện đến ngày dự báo có thể liên quan, song đồ thị chưa xác định được nguyên nhân.

**Hình đối chiếu.** [Mean IC theo giai đoạn](../reports/baseline/figures/fig1_mean_rank_ic_by_year.png) · [IC trung bình trượt](../reports/baseline/figures/fig2_rolling_rank_ic_63d.png).

## 3. Backtest Top 20 chuyển điểm thành lệnh ra sao?

**Backtest** là mô phỏng các quy tắc giao dịch trên dữ liệu lịch sử để kiểm tra chúng sẽ tạo lệnh, chi phí và dòng tiền như thế nào theo những giả định cụ thể. Trong v1, mỗi tín hiệu có danh mục riêng. **Long-only** nghĩa là chỉ nắm vị thế mua, không bán khống. **Top 20** nghĩa là ưu tiên tối đa 20 mã có điểm cao nhất, với ngân sách mua bằng tối đa 5% NAV phiên trước mỗi mã và bị giới hạn bởi tiền mặt khả dụng.

1. Sau Close (T), xếp thứ tự từ điểm cao đến thấp. Kết quả ngày (T+1) và cờ nhãn hợp lệ không lọc danh sách này.
2. Tại Open (T+1), kiểm tra giá mở cửa hữu hạn, dương, cờ chất lượng dữ liệu và sự kiện ngừng giao dịch. Lệnh thiếu điều kiện được ghi `CANCELLED_BUY`, tức lệnh mua bị hủy. Phần ngân sách đó giữ bằng tiền mặt, không tính phí và không lấy mã kế tiếp để thay.
3. Tại Close (T+1), bán khi có giá đóng cửa hợp lệ và khối lượng dương theo điều kiện mô phỏng. Nếu không bán được, bộ mô phỏng có thể giữ vị thế sang phiên sau, đánh giá bằng giá hợp lệ gần nhất và thử xử lý khi mở cửa. Sổ cái của **bản chạy 18 sự kiện** cho thấy cả sáu kịch bản có 624 dòng, với số vị thế mở và chuyển tiếp qua đêm bằng 0 ở tất cả các dòng. Đây là quan sát của lần chạy đã lưu. Bộ mô phỏng vẫn hỗ trợ tình huống phải giữ sang ngày kế tiếp.

**NAV (Net Asset Value)** là giá trị tài sản ròng, gồm tiền mặt và giá trị còn lại của các vị thế. **Basis point (bps), hay điểm cơ bản**, là 0,01%. V1 thử 0 bps và danh nghĩa 20 bps mỗi **round-trip**, tức một lượt mua và một lượt bán. Chi phí giả định mỗi chiều gồm 5 bps phí và 5 bps **slippage**, tức độ lệch giá khớp bất lợi so với giá tham chiếu. Khi mua, giá khớp mô phỏng cao hơn giá Open 5 bps. Khi bán, giá khớp thấp hơn giá Close 5 bps. Phí mua nằm trong ngân sách đã cấp, còn phí bán trừ vào tiền nhận về. Chi phí bằng USD phụ thuộc giá trị của từng lệnh, nên không phải lúc nào cũng đúng 0,20% của toàn NAV.

Ví dụ từ sổ lệnh của Ridge 20 bps ngày 03/01/2024, một mã có giá Open 38,09 USD và giá khớp mô phỏng 38,109045 USD. Trong ngân sách 5.000 USD, khoảng 4.997,50 USD mua cổ phiếu và 2,50 USD là phí. Trượt giá làm giảm lượng cổ phiếu mua được trong cùng ngân sách. Ở một phiên khác, MRTX ngày 23/01/2024 có dòng dữ liệu Open nhưng sổ lệnh ghi `CANCELLED_BUY` do cờ ngừng giao dịch trước mở cửa, với số cổ phiếu, phí, trượt giá và dòng tiền đều bằng 0. Ngày 24/01 không có lệnh MRTX ở sổ này. Ví dụ minh họa vì sao một con số Open trong dữ liệu cần đi cùng kiểm tra trạng thái giao dịch.

**Xem trong repo.** [Đặc tả backtest](../specifications/backtest_plan_v1.md) · [Mã mô phỏng](../../src/backtest/simulator.py) · [Script bản chạy chính](../../scripts/01_pipeline/31_run_oos_backtest_primary.py) · [Sổ lệnh Ridge 20 bps](../../outputs/reports/backtest_primary_scope/trades_ridge_20bps.csv) · [Sổ cái Ridge 20 bps](../../outputs/reports/backtest_primary_scope/ledger_ridge_20bps.csv).

## 4. Đọc lợi suất, NAV và chi phí mà không nhầm với khả năng dự báo

**Lợi suất lũy kế** bằng NAV cuối chia NAV đầu rồi trừ 1. **CAGR** là lợi suất năm hóa theo tăng trưởng kép. Script v1 nâng tỷ lệ NAV cuối/đầu lên lũy thừa (252/624), rồi trừ 1. **Sharpe năm hóa** ở đây là trung bình lợi suất ngày chia độ lệch chuẩn mẫu, nhân √252, dùng mốc lợi suất phi rủi ro bằng 0 trong phép tính. **Max Drawdown** là mức giảm sâu nhất từ đỉnh NAV đã quan sát tới một đáy về sau. Script tính trên NAV cuối mỗi phiên trong sổ cái. Ví dụ từ đỉnh 120.000 USD xuống 90.000 USD là drawdown −25%.

Từ vốn ban đầu 100.000 USD, **ở 0 bps** Ridge kết thúc ở 134.925,42 USD (+34,93%), GBDT ở 92.174,37 USD (−7,83%), và `ret_20d` ở 112.904,83 USD (+12,90%). Khoảng đo là 624 phiên, tức khoảng 2,5 năm giao dịch. Dữ liệu hơn 20 năm ở phần huấn luyện là một khoảng khác. **Ở 20 bps** Ridge kết thúc ở 38.807,77 USD (−61,19%), GBDT ở 26.469,23 USD (−73,53%) và `ret_20d` ở 32.415,77 USD (−67,58%). Khi đọc Hình NAV, theo dõi quỹ đạo từng đường và so vị trí cuối đường với đường ngang 100.000 USD.

Ridge chênh **96.117,64 USD** giữa NAV cuối hai kịch bản. Sổ lệnh 20 bps cộng dồn **80.385,51 USD** phí và trượt giá. Phần còn lại **15.732,13 USD** là chênh lệch sau khi đối chiếu chi phí trực tiếp, liên quan đến hai đường đi khác nhau của NAV và quy mô vốn giao dịch. Ví dụ nếu một danh mục trừ chi phí hôm nay thì vốn khả dụng ngày mai giảm. Điều đó thay đổi số USD kiếm được trong một phiên tăng và số USD mất trong một phiên giảm. Khoản còn lại được tính bằng phép trừ giữa hai kịch bản.

Có ba lý do để đọc Rank IC và backtest thành hai kết quả riêng.

- **Tập mã khác nhau.** Rank IC tổng hợp thứ tự trên các mã đủ điều kiện trong cả rổ, bình quân khoảng 976 mã. Danh mục tập trung vào nhóm được xếp cao nhất. GBDT có Mean IC dương nhưng Top 20 vẫn lỗ ở 0 bps. Hai kết quả này có thể cùng xảy ra mà chưa xác định được mô hình xếp sai ở nhóm nào.
- **Khoảng lợi suất khác nhau.** Close-to-Close bao gồm phần từ Close (T) đến Open (T+1) và phần từ Open đến Close (T+1). Một mã tăng từ 100 lên 110 qua đêm và đóng cửa 111 sẽ cho 11% Close-to-Close nhưng chỉ khoảng 0,91% Open-to-Close. Thành phần qua đêm có thể đổi thứ tự giữa các mã. Bài chưa đo riêng phần đóng góp của nó vào kết quả danh mục.
- **Chi phí và quy tắc danh mục.** Rank IC chỉ dùng điểm và thứ hạng thực tế. Backtest dùng ngân sách, trạng thái khớp lệnh và chi phí. Với quy tắc mua rồi bán mỗi ngày, **turnover**, tức lượng danh mục được giao dịch lại, có thể lớn ngay cả khi hai ngày liên tiếp chọn cùng mã. Kết quả v1 mô tả độ nhạy của quy tắc Top 20 trước hai giả định chi phí đã thử.

**Vì sao chỉ gọi backtest là minh họa?** Quy tắc Top 20 được thiết kế sau khi nhóm đã xem Rank IC OOS. Kết quả hữu ích để hiểu khoảng cách giữa dự báo và thực thi theo quy tắc này. Để kiểm tra một quy tắc giao dịch mới, cần chốt quy tắc và chi phí trước khi xem kết quả trên một giai đoạn chưa được dùng để ra quyết định. V1 không ước lượng chi phí hòa vốn và chưa thử thời gian nắm giữ dài hơn.

**Hình và số liệu.** [Quỹ đạo NAV](../reports/baseline/figures/fig3_nav_trajectory_0bps_vs_20bps.png) · [Lợi suất lũy kế](../reports/baseline/figures/fig4_cumulative_returns_cost_impact.png) · [CSV sáu kịch bản](../../outputs/reports/backtest_primary_scope/performance_summary_all_scenarios.csv) · [Báo cáo backtest](../reports/baseline/oos_backtest_primary_report.md).

## 5. Tự kiểm tra sau khi đọc

1. Tại sao ngày 02/01/2024 có thể có điểm dự báo mà phải tới 03/01 mới có kết quả chấm? Hãy thử chỉ ra ba mốc Close (T), Open (T+1) và Close (T+1).
2. Nếu 56,41% số phiên IC dương thì 56,41% đang đếm phiên, mã cổ phiếu hay lệnh có lãi? Hãy đối chiếu với định nghĩa Mean Rank IC.
3. Vì sao cùng một tín hiệu có thể cho Mean IC dương, Top 20 lời trước chi phí và lỗ sau chi phí? Hãy kể riêng tập mã, khoảng lợi suất và chi phí.
4. Nếu muốn so Ridge với GBDT về ý nghĩa thống kê, tại sao hai p-value hiện có chưa trả lời câu hỏi đó?

**Phạm vi rà soát.** Các quy tắc được đối chiếu với mã nguồn. Mốc ngày và nhóm năm được kiểm tra trên CSV IC. Các số dư cuối kỳ, sáu dòng hiệu năng và ví dụ MRTX được đối chiếu với CSV sổ cái, sổ lệnh và tổng hợp đã lưu. Chương này sử dụng lại các hình và kết quả hiện có. Không cần chạy lại mô hình hay bộ mô phỏng để đọc chương này.
