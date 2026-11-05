# Mục lục tài liệu

Đây là điểm bắt đầu để đọc tài liệu dự án. Không cần đọc toàn bộ CSV hoặc mọi báo cáo lịch sử trước khi phát triển features.

**Người mới muốn hiểu từ đầu:** đọc [hướng dẫn theo 9 chặng](learning/README.md). Mỗi chặng giải thích khái niệm, vấn đề, input/output, ví dụ, kiểm tra, quyết định và giới hạn, rồi dẫn tới báo cáo tương ứng.

**Để hiểu bài đang làm:** trong mỗi chặng, đọc mục “Từ vấn đề đến phương pháp”. Phần này nối bias/lỗi dữ liệu với kỹ thuật đã chọn, bằng chứng kiểm tra và giới hạn; không chỉ liệt kê các bước chạy. Các lựa chọn ML chưa thực hiện được ghi là kế hoạch.

## 1. Đọc theo thứ tự nào?

1. [README dự án](../README.md): mục tiêu, phạm vi, thiết lập và cách dùng.
2. [Context hiện hành](pipeline_migration_and_feature_readiness_context.md): quyết định, giả định và việc còn lại.
3. [Hành trình dữ liệu](reports/data_pipeline/data_lineage_report.md): nguồn → xử lý → artifact.
4. [Đặc tả target/timing](specifications/target_and_timing_v1.md), rồi [16 features v1](specifications/features_v1.md): hợp đồng thiết kế để triển khai.
5. [Bản bàn giao v1](reports/handoff/handoff_v1_2026-11-05.md): phạm vi đã bàn giao, kiểm thử và giới hạn.

Tra [data dictionary](data_dictionary.md) khi cần hiểu cột/mask; tra [DAG](pipeline_dag.md) khi cần thứ tự chạy script.

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

### Thư viện và pilot

- [Library edge cases và fixes](reports/library/library_edge_cases_and_fixes_report.md).
- [Theo dõi pilot features](reports/feature_pilot/README.md): quy ước lưu bằng chứng; báo cáo kết quả chi tiết đang được rà soát riêng, chưa nằm trong commit docs.
- [Quy ước artifact pilot](reports/feature_pilot/README.md).

### Hồ sơ tái cấu trúc

- [Rà và sửa nội dung cho người mới, 2026-11-05](reports/migration/documentation_review_2026-11-05.md).
- [Kiểm kê dự án](reports/migration/project_audit_inventory.md).
- [Code review](reports/migration/code_review_report.md).
- [Verification log](reports/migration/pipeline_verification_log.md).
- [Phase 2 verification log](reports/migration/phase2_pipeline_verification_log.md).

Đây là hồ sơ theo thời điểm; không dùng danh sách đường dẫn cũ trong các bản ghi này thay cho DAG/config hiện hành. Giữ hai log riêng để bảo toàn bằng chứng, không giả định chúng là một hướng dẫn chạy duy nhất.

## 4. Tài liệu hiện hành và tài liệu lịch sử

- Công thức features/target: dùng hai file trong `specifications/`.
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
