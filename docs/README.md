# Mục lục tài liệu

Đây là điểm bắt đầu để đọc tài liệu dự án. Không cần đọc toàn bộ CSV hoặc mọi báo cáo lịch sử trước khi phát triển features.

> [!IMPORTANT]
> **MỐC THỰC NGHIỆM v1 (MILESTONE v1 REVIEW)**
>
> Giảng viên chưa công bố bảng điểm (rubric) hoặc mẫu báo cáo chính thức, do đó toàn bộ trạng thái hiện tại được chuẩn hóa và đóng gói thành **Báo Cáo Thực Nghiệm v1** để nhóm sinh viên đọc, rà soát phương pháp luận và đối chiếu số liệu.
>
> - **Tài liệu thực nghiệm chính:** **[Báo Cáo Thực Nghiệm v1](reports/baseline/comprehensive_course_project_report.md)**.
> - [Bản nháp bố cục báo cáo](reports/baseline/course_project_submission_report.md) có trang bìa và mục tự kiểm tra để tham khảo.
> - **Mô hình & Kết quả cốt lõi v1:**
>   - **Ridge Baseline** ($\alpha=1.0$, `StandardScaler`): mốc tuyến tính chuẩn hóa.
>   - **HistGradientBoostingRegressor** (7 lá, không qua scaler): mô hình ứng viên phi tuyến.
>   - **ret_20d**: tín hiệu đối chứng động lượng đơn giản.
>   - **Kết quả chính trả lời đề bài:** Mean Spearman Rank IC trên 624 phiên ngoài mẫu (OOS) chính từ 03/01/2024 đến 30/06/2026 (Ridge: **+0,023050**, $t = +3,58, p = 0,00037$; GBDT: **+0,020403**, $t = +3,43, p = 0,00065$; ret_20d: **-0,004393**, $t = -0,64, p = 0,522$). Cả hai mô hình đạt $p < 0,001$ trong kiểm định hai phía so với giả thuyết không $\text{Mean IC} = 0$.
>   - **Backtest minh họa Top 20:** Được thiết kế sau khi xem kết quả Rank IC OOS, tái cân bằng 100% hàng ngày (Open-to-Close). Ridge đạt **+34,93%** trước chi phí (0 bps) và **-61,19%** ở mức chi phí giả định 20 bps round-trip trong khoảng 2,5 năm (624 phiên). Cả ba danh mục đều chịu thua lỗ nặng sau chi phí.
> - **Tài liệu tham khảo (`docs/refer_report.pdf`):** Đóng vai trò học tập cách trình bày học thuật và tham khảo ý tưởng bố cục đồ án của khóa trước; khi thảo luận về **Survivorship Bias (Thiên lệch sống sót)**, đồ án đã giải thích tại sao áp dụng danh sách hiện tại về quá khứ sẽ loại bỏ công ty phá sản/hủy niêm yết gây thổi phồng kết quả, và cách v1 dùng Universe Point-in-Time (PIT) tái tạo theo từng năm để giảm thiểu rủi ro này (đồng thời nêu rõ 3 giới hạn phương pháp luận PIT).

---

## Lộ Trình Đọc Báo Cáo Thực Nghiệm v1 (4 Chặng Khuyến Nghị)

Để nắm bắt trọn vẹn logic từ bài toán, kỹ thuật xử lý dữ liệu tới kết quả thực nghiệm mà không bị ngợp trước khối lượng thông tin lớn, nhóm khuyến nghị đọc [Báo Cáo Thực Nghiệm v1](reports/baseline/comprehensive_course_project_report.md) theo 4 chặng:

```mermaid
flowchart LR
    C1["Chặng 1: Dữ liệu & Phương pháp\n(PIT, Corporate Actions, Masks, Freeze)"] --> C2["Chặng 2: Features, Alpha & Trọng số\n(13 Features Close/Volume, Ridge Weights)"]
    C2 --> C3["Chặng 3: Kết quả Rank IC OOS\n(624 phiên, t-test vs 0, Phân rã năm)"]
    C3 --> C4["Chặng 4: Backtest & Ma sát chi phí\n(Top 20, 0 vs 20 bps, Phân rã NAV)"]
```

| Chặng | Chủ Đề Trọng Tâm | Mục Cần Đọc Trong Báo Cáo v1 | Câu Hỏi Cần Trả Lời Được Sau Khi Đọc |
| :--- | :--- | :--- | :--- |
| **Chặng 1** | **Dữ liệu và Phương pháp nghiên cứu** | Mục 1 và Mục 2.1 – 2.2 | • Tại sao không được áp dụng danh sách cổ phiếu hiện tại về quá khứ mà phải dựng Universe Point-in-Time (PIT)? Tránh survivorship bias ra sao?<br>• Dữ liệu giá thô được làm sạch và điều chỉnh chia tách/cổ tức (Corporate Actions) thế nào?<br>• Hệ thống 4 tầng mask kiểm soát tính hợp lệ dữ liệu ra sao?<br>• Ranh giới giữa Development (2000–2023) và OOS (2024–2026) được bảo vệ chống rò rỉ ranh giới (Causal Boundary Purge) và đóng băng mô hình như thế nào? |
| **Chặng 2** | **Feature, Alpha và Cách Mô hình Học Trọng số** | Mục 2.3 và Mục 2.4 (kèm Bảng 1) | • 13 đặc trưng kỹ thuật Close và Volume đại diện cho những nhóm tín hiệu kinh tế nào (động lượng, biến động, thanh khoản, dao động)?<br>• Tại sao hoãn 3 features cần giá Open/High/Low?<br>• Mô hình tuyến tính Ridge Baseline gán trọng số ra sao cho các yếu tố rủi ro và động lượng (phạt rủi ro giảm giá, ưu tiên cổ phiếu trong dải biến động Bollinger)? |
| **Chặng 3** | **Kết Quả Dự Báo Xếp Hạng Ngoài Mẫu (Rank IC)** | Mục 3 (Bảng 2, Bảng 3, Hình 1, Hình 2) | • Spearman Rank IC đo lường điều gì và được tính theo từng phiên ra sao?<br>• Tại sao Mean Rank IC của Ridge (+0,023050) và GBDT (+0,020403) đạt mức ý nghĩa thống kê $p < 0,001$ trong kiểm định hai phía so với giả thuyết không $\text{Mean IC} = 0$?<br>• Tín hiệu động lượng cổ điển `ret_20d` có hiệu quả không?<br>• Động thái suy giảm IC qua các năm 2024, 2025, 2026 phản ánh điều gì? |
| **Chặng 4** | **Backtest Minh Họa và Tác Động Ma Sát Chi Phí** | Mục 4, Mục 5 và Mục 6 (Bảng 4, Hình 3, Hình 4) | • Tại sao Rank IC dương trên toàn rổ nhưng danh mục Top 20 lại thua lỗ sau chi phí?<br>• Cơ chế phân kỳ giữa Close-to-Close và Open-to-Close (bỏ lỡ lợi suất qua đêm) ảnh hưởng ra sao?<br>• Tần suất giao dịch 100% hàng ngày nhân bội ma sát chi phí như thế nào (phân rã khoản chênh lệch NAV của Ridge)?<br>• Hai hướng nghiên cứu mở cho v2 để giải quyết bài toán alpha và thực thi là gì? |

---

## 1. Đọc theo thứ tự nào?

1. [README dự án](../README.md): mục tiêu, phạm vi, thiết lập và cách dùng.
2. [Context hiện hành](pipeline_migration_and_feature_readiness_context.md): quyết định, giả định và việc còn lại.
3. [Hành trình dữ liệu](reports/data_pipeline/data_lineage_report.md): nguồn → xử lý → artifact.
4. [Đặc tả target/timing](specifications/target_and_timing_v1.md), rồi [16 features v1](specifications/features_v1.md): hợp đồng thiết kế để triển khai.
5. [Đặc tả Dataset Baseline v1](specifications/baseline_dataset_v1.md): quy chuẩn cấu trúc bảng 13 features Close/Volume và target ranking cho Ridge baseline.
6. [Bản bàn giao v1](reports/handoff/handoff_v1_2026-11-05.md): phạm vi đã bàn giao, kiểm thử và giới hạn.
7. [Tài liệu Bàn giao Mốc Feature Store Ứng viên](reports/handoff/feature_store_milestone_handoff.md): tổng kết mốc bàn giao, giải trình 5.61M vs 6.31M ô, quy tắc return mới, đối chiếu 2 tọa độ kiểm chứng (LOW, CPTH) và đề xuất 13-feature baseline.
8. [Đặc tả Kế hoạch Backtest v1](specifications/backtest_plan_v1.md): đề xuất cấu hình kiểm thử danh mục Long-Only Top 20 Open-to-Close cho 3 mô hình trên OOS, quy tắc khớp lệnh, xử lý tiền mặt và chi phí giao dịch.
9. [Báo Cáo Kiểm Thử Giao Dịch OOS Backtest](reports/baseline/oos_backtest_primary_report.md): kết quả đối soát sổ lệnh 18 sự kiện ngừng giao dịch (M&A/Halt), phân rã chi phí và hiệu ứng suy giảm vốn tái đầu tư.
10. **[Báo Cáo Thực Nghiệm v1 (Tài liệu chính)](reports/baseline/comprehensive_course_project_report.md)**: toàn văn báo cáo đồ án tổng hợp mốc v1 chuẩn học thuật: Bài toán → Dữ liệu và phương pháp (Russell 1000 PIT, Corporate Actions, 13 features Close/Volume, Walk-Forward, Purge, Freeze) → Kết quả OOS Rank IC 624 phiên → Backtest minh họa Top 20 (0 vs 20 bps) → Giới hạn, Kết luận và Hai câu hỏi mở cho v2.
11. [Bản nháp bố cục báo cáo](reports/baseline/course_project_submission_report.md). Xem báo cáo thực nghiệm v1 để đọc nội dung đã rà.
12. [Báo Cáo Kết Quả Thực Nghiệm Toàn Diện (Primary Focus)](reports/baseline/comprehensive_experimental_results_report.md): báo cáo thực nghiệm tổng hợp góc nhìn kỹ thuật phân tích chi tiết dữ liệu và biểu đồ.

> [!TIP]
> **Lộ trình Đọc Khuyến nghị cho Mốc Feature Store (Review & Nghiệm thu):**
> 1. [Đặc tả 16 features candidate v1](specifications/features_v1.md) & [Đặc tả Target và Thời điểm Khớp lệnh v1](specifications/target_and_timing_v1.md): Hợp đồng toán học và thời điểm.
> 2. [Báo cáo Pilot 16 features](reports/feature_pilot_report.md): Thử nghiệm pilot trên mẫu đại diện, đối chiếu số học độc lập.
> 3. [Báo cáo EDA và Validation Feature Store Development](reports/feature_eda_report.md): Kiểm định 104 tiêu chí cấu trúc, 144 bài kiểm tra nhân quả mở rộng, phân rã NaN và thống kê phân phối trên 5.911 phiên.
> 4. [Tài liệu Bàn giao Mốc Feature Store Ứng viên](reports/handoff/feature_store_milestone_handoff.md): Bàn giao mốc, làm rõ 5.61M vs 6.31M ô, quy tắc return mới, đối chiếu 2 tọa độ kiểm chứng (LOW, CPTH) và đề xuất 13-feature baseline.
> 5. [Đặc tả Dataset Baseline v1](specifications/baseline_dataset_v1.md): Cấu trúc bảng 13 features Close/Volume, định nghĩa hai điều kiện eligibility, mẫu số xếp hạng target và ví dụ minh họa trực quan.

Tra [data dictionary](data_dictionary.md) khi cần hiểu cột/mask; tra [DAG](pipeline_dag.md) khi cần thứ tự chạy script.

Xem [kiểm thử local và CI](testing.md) để phân biệt tests chạy trên GitHub với integration cần kho dữ liệu thật.

## 2. Cấu trúc và vai trò

```text
docs/
├── README.md                           # Mục lục này
├── learning/                           # Hướng dẫn học từng chặng
├── data_dictionary.md                  # Tra cứu schema và ý nghĩa dữ liệu
├── pipeline_dag.md                     # Thứ tự thực thi và phụ thuộc
├── pipeline_migration_and_feature_readiness_context.md
├── specifications/                     # Hợp đồng thiết kế hiện hành
├── reports/
│   ├── data_pipeline/                  # Lineage, corporate actions, matrices, EDA
│   ├── library/                        # Sửa thư viện và tests
│   ├── migration/                      # Hồ sơ rà soát/tái cấu trúc theo thời điểm
│   ├── handoff/                        # Các mốc bàn giao
│   ├── feature_pilot_report.md         # Báo cáo pilot chung, cập nhật theo đợt
│   └── feature_pilot/                  # Bảng đối chiếu/coverage và figures của pilot
├── Data report/                        # Artifact audit/HTML hiện có; giữ đường dẫn pipeline
│   ├── market_data_audit/
│   │   ├── tables/                     # CSV bằng chứng/đối chiếu
│   │   └── figures/                    # Hình EDA/audit
│   └── raw_universe/                   # Bản nguồn tham khảo đã lưu trong docs
├── Teacher Resource/                   # Tài liệu của thầy
├── refer_report.pdf                    # Tài liệu tham khảo hiện có
└── archive/                            # Báo cáo và đề xuất lịch sử
    └── plans/                          # Kế hoạch bước 7 cũ đã được thay thế
```

`reports/` trả lời **đã làm gì, kết quả và giới hạn ra sao**. `specifications/` trả lời **phải tính và xử lý như thế nào**. CSV/figures hỗ trợ kết luận, không thay thế mô tả phương pháp.

## 3. Báo cáo theo chủ đề

### Dữ liệu

- [Lineage](reports/data_pipeline/data_lineage_report.md).
- [Bảng truy nguồn universe từng năm](reports/data_pipeline/universe_source_inventory.csv): ngày ứng viên và các điểm chưa xác minh.
- [Identity và corporate actions](reports/data_pipeline/step3_corporate_actions_report.md).
- [Matrices và masks](reports/data_pipeline/step4_matrices_masks_report.md).
- [EDA Development](reports/data_pipeline/step6_eda_report.md).
- [Audit coverage thị trường](Data%20report/market_data_audit/market_data_audit_report.md).

Các báo cáo dữ liệu ghi nhận kết quả tại thời điểm tạo, có thể còn diễn giải cần xác minh. Đọc kèm giới hạn trong context và bản bàn giao; không xem mọi nhãn VERIFIED hoặc thống kê hợp lý là bằng chứng độc lập về toàn bộ dữ liệu.

### Thư viện, pilot và features

- [Library edge cases và fixes](reports/library/library_edge_cases_and_fixes_report.md).
- [Báo cáo pilot 16 features](reports/feature_pilot_report.md): đối chiếu số học độc lập, ca biên và mẫu thực Development.
- [Báo cáo EDA và Validation Feature Store (Development)](reports/feature_eda_report.md): kiểm định 104 tiêu chí, phân tích phân phối, tương quan chéo lát cắt, chế độ thị trường và cơ cấu NaN cho 16 features v1 trên 5.911 phiên.
- [Thư mục dữ liệu và biểu đồ EDA Features](reports/feature_eda/): các bảng CSV phân phối/tương quan/NaN và 6 biểu đồ phân tích trực quan.
- [Tài liệu Bàn giao Mốc Feature Store Ứng viên](reports/handoff/feature_store_milestone_handoff.md): tổng kết mốc bàn giao, giải trình 5.61M vs 6.31M ô, quy tắc return mới, đối chiếu 2 tọa độ kiểm chứng (LOW, CPTH) và đề xuất 13-feature baseline.
- [Theo dõi pilot features](reports/feature_pilot/README.md): quy ước lưu bằng chứng và artifacts pilot.

### Baseline và Mô Hình

- [Báo cáo Ridge Baseline v1 (Train 2000–2018 / Val 2019–2023)](reports/baseline/ridge_v1_report.md): kết quả split đơn tĩnh đầu tiên.
- [Báo cáo Walk-Forward Ridge Baseline (alpha=1.0)](reports/baseline/walk_forward_ridge_alpha1.0_report.md): kiểm định mở rộng thời gian 5 fold (2019–2023).
- [Báo cáo Grid Search Ridge Alpha (1 đến 1.000.000)](reports/baseline/ridge_alpha_grid_search_report.md): rà soát mức co hệ số trên 5 fold.
- [Báo cáo So Sánh GBDT vs Ridge Baseline](reports/baseline/walk_forward_gbdt_vs_ridge_report.md): đánh giá mô hình phi tuyến HistGradientBoostingRegressor so với mốc tuyến tính.
- [Báo cáo Thử Nghiệm Số Lá GBDT (max_leaf_nodes = 7, 15, 31)](reports/baseline/gbdt_leaf_grid_report.md): khảo sát dung lượng cây quyết định, phân tích hiện tượng overfit của cây sâu và đề xuất chọn 7 lá.
- [Báo Cáo Kiểm Chứng Mở Rộng OOS Prediction Pipeline (600 phiên Development)](reports/baseline/prediction_pipeline_scale_report.md): xác nhận pipeline tính toán đặc trưng và suy luận có khả năng mở rộng liên tục qua 711 phiên ngoài mẫu, đối chiếu số học 13 features và kiểm thử cơ chế bảo vệ Guardrail.
- [Báo Cáo Đánh Giá Ngoài Mẫu Chính Thức OOS 2024–2026 (One-Shot)](reports/baseline/oos_evaluation_report.md): kiểm định ngoài mẫu chính thức 711 phiên cho Ridge Baseline (alpha=1.0) và GBDT Candidate (7 lá) cố định, phân tách phạm vi Primary (2024–2026H1) và Extended (2026Q3–Q4).
- [Đặc Tả Kế Hoạch Backtest v1 (Long-Only Top 20 Open-to-Close)](specifications/backtest_plan_v1.md): thiết kế kiểm thử danh mục đầu tư mô phỏng cho Ridge, GBDT và ret_20d trên OOS, quy tắc khớp lệnh, xử lý tiền mặt và chi phí giao dịch.
- [Báo Cáo Thử Nghiệm Lát Cắt OOS Backtest (Ridge vs GBDT vs ret_20d)](reports/baseline/backtest_trial_slice_report.md): kết quả kiểm thử lát cắt 5 phiên đầu OOS trên dữ liệu giá thực tế, đối chiếu Top 20, sổ lệnh, sổ cái, phí và cơ chế xử lý corporate actions cho vị thế qua đêm.
- [Báo Cáo Kiểm Thử Giao Dịch Ngoài Mẫu Chính Thức OOS Backtest (2024–2026H1)](reports/baseline/oos_backtest_primary_report.md): kết quả backtest chính thức trên 624 phiên của Phạm vi OOS Chính cho Ridge, GBDT và ret_20d ở 0 và 20 bps với 18 sự kiện ngừng giao dịch (M&A/Halt), phân tách rạch ròi giữa Rank IC OOS và hiệu năng danh mục Top 20 trước/sau chi phí, cùng đối chiếu trực tiếp sổ lệnh.
- **[Báo Cáo Kết Quả Thực Nghiệm Ngoài Mẫu Toàn Diện (OOS Experimental Results Report)](reports/baseline/comprehensive_experimental_results_report.md)**: báo cáo tổng hợp hoàn chỉnh bằng tiếng Việt phục vụ viết đồ án, phân tích toàn diện kiểm định Rank IC trên 624 phiên OOS chính, minh họa backtest Top 20 ở 0 và 20 bps, kèm 4 biểu đồ PNG trực quan hóa tại [reports/baseline/figures/](reports/baseline/figures/) và script tái hiện [33_generate_report_figures.py](../scripts/01_pipeline/33_generate_report_figures.py).
- **[Bản Nháp Mục Đồ Án: Kết Quả Dự Báo Xếp Hạng Lợi Suất Ngoài Mẫu](reports/baseline/draft_section_oos_rank_ic_results.md)**: bản thảo văn phong sư phạm tiếng Việt dành riêng cho phần trình bày kết quả Rank IC trong báo cáo đồ án môn học, có ví dụ ngày cụ thể, ví dụ 3 mã cổ phiếu, công thức chi tiết, bảng kiểm định ý nghĩa thống kê và trả lời đề tài.
- **[Bản Nháp Mục Đồ Án: Backtest Minh Họa Danh Mục Top 20](reports/baseline/draft_section_oos_backtest_results.md)**: bản thảo văn phong sư phạm tiếng Việt dành riêng cho phần trình bày kết quả mô phỏng danh mục Top 20 trong báo cáo đồ án, quy tắc khớp lệnh Open-to-Close, bảng 6 kịch bản 18 sự kiện, 2 biểu đồ PNG quỹ đạo NAV/chi phí và giải thích phân kỳ giữa Rank IC và PnL danh mục.
- **[Bản Nháp Mục Đồ Án: Tóm Tắt (Abstract) Và Kết Luận (Conclusion)](reports/baseline/draft_abstract_and_conclusion.md)**: bản thảo văn phong học thuật tiếng Việt cho phần Abstract và Conclusion toàn đồ án, đặt dự báo xếp hạng trên 624 phiên OOS làm kết quả chính, Top 20 làm backtest minh họa (Ridge +34,93% ở 0 bps và -61,19% ở 20 bps giả định), làm rõ cơ chế phân kỳ và ranh giới nghiên cứu.
- **[Báo Cáo Thực Nghiệm v1 (Tài Liệu Chính)](reports/baseline/comprehensive_course_project_report.md)**: toàn văn báo cáo đồ án tổng hợp mốc v1 chuẩn học thuật: Bài toán → Dữ liệu và phương pháp (Russell 1000 PIT, 13 features Close/Volume, Walk-Forward, Freeze) → Kết quả OOS Rank IC 624 phiên → Backtest minh họa Top 20 (0 vs 20 bps) → Giới hạn, Kết luận và Hai câu hỏi mở cho v2.
- [Bản nháp bố cục báo cáo](reports/baseline/course_project_submission_report.md). Bản đối chiếu lịch sử. Xem báo cáo thực nghiệm v1 để đọc nội dung đã rà.

### Hồ sơ tái cấu trúc

- [Rà và sửa nội dung cho người mới, 2026-11-05](reports/migration/documentation_review_2026-11-05.md).
- [Kiểm kê dự án](reports/migration/project_audit_inventory.md).
- [Code review](reports/migration/code_review_report.md).
- [Verification log](reports/migration/pipeline_verification_log.md).
- [Phase 2 verification log](reports/migration/phase2_pipeline_verification_log.md).

Đây là hồ sơ theo thời điểm; không dùng danh sách đường dẫn cũ trong các bản ghi này thay cho DAG/config hiện hành. Giữ hai log riêng để bảo toàn bằng chứng, không giả định chúng là một hướng dẫn chạy duy nhất.

## 4. Tài liệu hiện hành và tài liệu lịch sử

- Công thức features/target/dataset: dùng các đặc tả trong `specifications/` ([features_v1.md](specifications/features_v1.md), [target_and_timing_v1.md](specifications/target_and_timing_v1.md), [baseline_dataset_v1.md](specifications/baseline_dataset_v1.md), [walk_forward_schedule_v1.md](specifications/walk_forward_schedule_v1.md), [oos_evaluation_plan_v1.md](specifications/oos_evaluation_plan_v1.md), [backtest_plan_v1.md](specifications/backtest_plan_v1.md)).
- [Kế hoạch bước 7 cũ](archive/plans/step7_feature_engineering_plan.md) chỉ để truy lịch sử, không phải đặc tả hiện hành.
- [Archive](archive/README.md) giữ các báo cáo trước đây. HTML tổng hợp và báo cáo sinh tự động có thể chưa cập nhật theo quyết định mới nhất; dùng mục lục này và các đặc tả làm điểm tham chiếu.
- Khi code khác đặc tả, ghi rõ khác biệt; không âm thầm coi code hoặc văn bản là đã được kiểm chứng.

## 5. Khi thêm tài liệu mới

1. Đặc tả mới vào `specifications/`; báo cáo kết quả vào nhóm phù hợp trong `reports/`.
2. Pilot dùng một báo cáo chung cho 16 features, cập nhật theo đợt; không tạo một báo cáo cho mỗi feature/lần chạy nhỏ.
3. Ghi trạng thái, ngày, phạm vi dữ liệu, commit/lệnh chạy, bằng chứng và giới hạn. Chưa chạy thì ghi chưa chạy.
4. Không chép lại công thức vào nhiều nơi; dẫn link tới đặc tả. Cập nhật mục lục khi thêm tài liệu chính.
5. Không đổi vị trí `Data report/market_data_audit/` hoặc các đường dẫn mà script dùng nếu chưa cập nhật producer/consumer. Dữ liệu đầu vào parser vẫn là `data/raw/universe/raw_universe/`, không tự đọc bản tham khảo trong docs.
6. Không đưa ZIP/Parquet hoặc artifact lớn vào Git chỉ vì đặt dưới `docs/`. Xem README dự án về dữ liệu cần chuẩn bị ngoài Git.
