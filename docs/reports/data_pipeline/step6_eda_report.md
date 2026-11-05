# EDA Development và điều tra ngoại lệ

Cập nhật diễn giải ngày 2026-11-05. Tài liệu đọc artifact đã lưu và code 09/10; không tái chạy EDA hoặc xác minh nguồn thị trường bên ngoài trong lượt sửa này. [Hướng dẫn học](../../learning/README.md) · [Lineage](data_lineage_report.md).

## 1. EDA hỏi gì?

EDA là khám phá dữ liệu: phân phối có gì bất thường, thiếu ở đâu, các mã/ngày khác nhau thế nào. Nó giúp tìm vấn đề để điều tra, không tự chứng minh nguyên nhân hay khả năng sinh lời.

Script 09 lấy Development 01/07/2000–29/12/2023, dùng `valid_data_mask` để chọn daily_return hữu hạn. Không dùng label mask lọc return hiện tại. Các thao tác đọc file toàn kỳ rồi slice không cho phép tuyên bố OOS chưa từng được đọc; chính sách là không dùng kết quả OOS để chọn feature/model/tuning.

## 2. Đơn vị quan sát và thống kê

[moments CSV](../../Data%20report/market_data_audit/tables/eda_daily_return_moments.csv) ghi:

- 5.610.691 quan sát **stock-day**: một mã ở một ngày, không phải 5.610.691 ngày độc lập.
- Mean 0,0003787287 ≈ +0,0379%; median 0,0003547357 ≈ +0,0355%.
- Std gộp 0,0265303641 ≈ 2,653%.
- Skewness 0,5634315; excess kurtosis 66,875076.
- Min −94,9735%; max +227,8689% trong mẫu đã chọn.

Mean là trung bình mẫu, không phải dự đoán lợi suất ngày mai. Median là mốc giữa mẫu, không được nhân 252 để gọi là lợi nhuận năm. Std gộp mọi mã/ngày không phải volatility của danh mục hay một cổ phiếu cố định.

CSV có trường annualized_volatility = std_gộp×sqrt(252) ≈42,12%; đó là phép đổi thang trong script, **không diễn giải thành rủi ro năm của danh mục hoặc rủi ro phi hệ thống đã ước lượng**. Muốn volatility danh mục phải có chuỗi return danh mục và xét giả định annualization.

Skew dương mô tả bất đối xứng mẫu, không tự xác nhận nguyên nhân kinh tế. Kurtosis cao cho biết tails/moment bậc bốn lớn so với chuẩn, không tồn tại ngưỡng 66,88 là chứng nhận dữ liệu sạch.

### Phân vị: sửa nhãn p01

Code đặt `percentiles=[0.01,0.1,1,...]` và lưu `p01=pct_values[0]`. Vì vậy giá trị −0,3488352444 là **phân vị 0,01%**, không phải 0,1% như báo cáo cũ. Nó ứng với khoảng 1/10.000 stock-days nằm dưới ngưỡng trong mẫu (bỏ qua ties), không phải 1/1.000.

Các mốc khác: p1≈−7,2822%; p5≈−3,5300%; median≈0,0355%; p95≈3,5634%; p99≈7,5145%; p99,9≈17,4965%. Đây là phân vị lịch sử gộp, chưa phải VaR dự báo có điều kiện cho một danh mục.

CSV ghi tỷ lệ >10%=0,491775%, <−10%=0,434153%, >20%=0,065464%, <−20%=0,053452%. Cần giữ mẫu số stock-days đã lọc khi so sánh phiên bản khác.

## 3. Đọc các hình đã có

- [Histogram và Q-Q](../../Data%20report/market_data_audit/figures/eda_daily_return_distribution_qq.png): histogram cho mật độ giá trị, Q-Q so với phân phối chuẩn. Code clip dữ liệu vẽ ở ±15% để nhìn vùng giữa; không được tưởng toàn bộ tails chỉ đến ±15% hoặc dữ liệu kho đã bị winsorize. Kiểm tra code khi đọc mỗi panel.
- [Dispersion theo thời gian](../../Data%20report/market_data_audit/figures/eda_cross_sectional_dispersion_history.png): mỗi phiên đo khác biệt return giữa các mã hợp lệ, rồi tóm tắt theo năm. Mẫu dựa `valid_data_mask` ở ngày đó, không dựa nhãn tương lai.
- [Universe dynamics](../../Data%20report/market_data_audit/figures/eda_universe_turnover_and_active_count.png): số ticker thêm/bớt giữa snapshot không tự phân biệt đổi tên với đổi chứng khoán. Churn ở đây là theo chuỗi ticker trong JSON.
- [Liquidity deciles](../../Data%20report/market_data_audit/figures/eda_liquidity_vs_volatility_deciles.png): nhóm theo median dollar volume của từng SID trong toàn Development. Đây là phân nhóm hồi cứu, không được mang nguyên nhóm toàn kỳ vào quyết định giao dịch quá khứ.

Dispersion cao nghĩa là kết quả giữa các mã cách nhau xa, không chứng minh model dự đoán được hoặc có lợi nhuận sau chi phí. Decile thanh khoản không đồng nghĩa nhóm vốn hóa; không có shares outstanding/market cap thì không kết luận D10 là mega-cap. `stock_count=257` là số SID trong nhóm toàn kỳ, không phải trung bình 257 mã của một danh mục tại mỗi ngày.

## 4. Quy trình điều tra một ngoại lệ

1. Tìm đúng date/SID, raw OHLCV, adjusted OHLCV, factor và return của cả cửa sổ trước/sau.
2. Kiểm tra continuity/phiên thiếu, ticker reuse, alias và mapping đang dùng.
3. Kiểm tra corporate actions cùng ngày và những điều chỉnh được áp.
4. Đối chiếu nguồn độc lập: sự kiện, ngày hiệu lực, tỷ lệ, đúng loại chứng khoán và hai mức giá nếu có thể.
5. Phân loại: có bằng chứng sửa factor; nghi lỗi cần cách ly; biến động thật có bằng chứng; chưa xác minh.
6. Ghi quyết định và giới hạn; nếu sửa upstream, tái tạo phần downstream liên quan có chủ đích.

Không sửa giá chỉ vì return lớn và không coi return nhỏ sau sửa là bằng chứng đủ.

## 5. Các ca đã ghi nhận và mức bằng chứng

[Corrections/exceptions](../../Data%20report/market_data_audit/tables/market_data_corrections_and_exceptions.csv) có 13 ca can thiệp: 5 split overrides, 4 spin-off cách ly, 4 khoảng nghi dữ liệu lỗi. Chúng không phải 13 sự kiện cùng loại và không có cùng mức bằng chứng. Xem [corporate actions](step3_corporate_actions_report.md).

[Forensic ledger](../../Data%20report/market_data_audit/tables/extreme_returns_forensic_investigation.csv) giữ các nhóm CORR/HIST/UNVER. Nhãn HIST và mô tả SEC/FDIC trong ledger là kết quả ghi nhận trước đây, không phải lượt này đã truy tất cả văn bản. Ledger còn chuỗi giá bị mất ký tự và nguồn chưa có URL/accession; cần bổ sung trước khi trích dẫn như bằng chứng đầy đủ. Giữ nguyên CSV trong lượt sửa tài liệu để không ngầm thay đổi bằng chứng nguồn hoặc dữ liệu đầu vào của pipeline.

### CHK: ví dụ số học đã kiểm tra logic

Raw close trước/sau được ghi 0,1313 và 16,375. Raw return≈+12.371%; factor reverse split 200 đưa return về 16,375/(0,1313×200)−1≈−37,64%. Return sau split vẫn âm mạnh, không ép về 0. Đây là tính lại trên các giá được cung cấp; xác minh lịch sử giá là bước riêng.

### MFA: chưa coi câu chuyện là xác nhận mức giá

Mẫu ghi 25/03/2020 +227,87%. Diễn giải cũ gắn mức tăng với thỏa thuận hoãn nợ và TALF không đủ bằng chứng để xác nhận nguyên nhân hoặc hai mức giá. Không lặp lại như một kết luận đã xác minh.

Cần đối chiếu đúng SID, raw close 24/03 và 25/03, factor, phiên liên tiếp, ngày công bố sự kiện và nguồn giá độc lập. Hiện giữ kết quả quan sát và đánh dấu giới hạn; không xóa điểm này chỉ do lớn, cũng không chứng nhận là đúng chỉ vì xảy ra trong khủng hoảng.

### Các ca chưa xác minh

UNVER giữ nguyên theo chính sách hiện tại, kèm giới hạn và kế hoạch kiểm tra độ nhạy. Rank không làm giá lỗi trở thành dữ liệu đúng: một bar lỗi có thể thay thứ hạng của chính nó và các mã khác, đồng thời làm bẩn features rolling.

## 6. EDA ảnh hưởng lựa chọn model thế nào?

Tails lớn làm squared loss nhạy với sai số lớn. Với MSE, gradient theo prediction tỷ lệ tuyến tính residual; bình phương residual quyết định đóng góp loss, không phải gradient tăng theo bình phương như diễn giải cũ.

Kurtosis của return không tự cấm OLS/Ridge. OLS không yêu cầu phân phối biên của target phải chuẩn; giả định cho suy luận/thống kê và tính bền vững cần xét riêng. Có thể thử target rank, loss khác hoặc preprocessing theo thiết kế và kiểm thực trên Development.

Rank target bị chặn trong [0,1], giảm ảnh hưởng độ lớn cực đoan trong y. Nó không loại beta, không bảo đảm stationarity, không sửa X lỗi và không đồng nghĩa tối ưu MSE rank là tối ưu trực tiếp Spearman hay P&L. Ties và N hữu hạn cũng không tạo phân phối Uniform liên tục chính xác.

Target chính đã chốt tại [target/timing v1](../../specifications/target_and_timing_v1.md). Thực thi sau đóng cửa T cần lịch khớp lệnh riêng, không mặc nhiên thu được toàn bộ close-to-close.

## 7. Quyết định và giới hạn

Giữ EDA làm bằng chứng về mẫu hiện có, dùng ngoại lệ để hướng điều tra. Chưa có kết luận model/feature nào tốt, capacity giao dịch bao nhiêu hoặc toàn kho hoàn toàn đúng.

Bước tiếp theo là pilot tính đúng 16 features trên mẫu nhỏ theo [đặc tả](../../specifications/features_v1.md), sau đó mới đánh giá coverage/phân phối/tương quan/IC trên Development. Trước khi dùng báo cáo trong luận văn cần bổ sung nguồn truy được cho corrections và xử lý các giới hạn ngày snapshot đã ghi ở lineage.
