# Báo Cáo Code Review Toàn Diện Pipeline (Milestone M2)
**Dự Án**: Russell 1000 Daily Return Rankings Overhaul  
**Mục Tiêu**: Thẩm định chuyên sâu mã nguồn toàn bộ 13 scripts hoạt động thuộc `scripts/01_pipeline/`, kiểm tra tính toàn vẹn hệ thống (schema contract, data lineage, đường dẫn tuyệt đối, dead code) và xác nhận tuyệt đối không có rò rỉ dữ liệu ngoài mẫu (Zero Out-Of-Sample Data Leakage).  
**Ngày Thực Hiện**: 04/11/2026  
**Trạng Thái Tổng Thể**: ✅ **ĐÃ THẨM ĐỊNH TOÀN DIỆN (13/13 SCRIPTS)** — Phát hiện một số cảnh báo về hardcoded absolute path và thứ tự thực thi dependency giữa các scripts phụ trợ.

---

## 1. Tổng Quan Kiến Trúc Pipeline & Bảng Tổng Kết 13 Scripts

Pipeline xử lý dữ liệu được thiết kế theo mô hình nhiều tầng (Multi-tier Quantitative Warehouse), chuyển hóa từ dữ liệu thô (raw universe PDF/XLS/JSON và nến QuantConnect LEAN) thành kho dữ liệu chuẩn hóa danh tính (Tier 2 Adjusted Warehouse) và lưới ma trận 2D tối ưu hóa cho mô hình học máy (Machine Learning Grid):

```
[Raw Universe PDF/CSV/JSON] ──> Script 01 (Parse PIT Universe)
                                       │
                                       ▼ (russell1000_pit_by_year.json)
[QuantConnect Cloud] ──────────> Script 02 (Availability Scan) & Export Batches
                                       │
                                       ▼ (10 ZIP Batches)
[Batch Consolidation] ─────────> Script 03 (Process Batches to Parquet)
                                       │
                                       ▼ (Raw Master OHLCV Parquet)
[Identity Audit & Mapping] ────> Script 04 (Audit Identity & Canonical SIDs)
                                       │
                                       ├──────────────────────────┐
                                       ▼                          ▼
[Corporate Actions & Pricing] ─> Script 06 (Searchsorted Adj)   Script 04b, 05_rigorous
                                       │                        (Specialized Step 3 Audits)
                                       ▼ (Adjusted Parquet)
[2D Matrices & PIT Masks] ─────> Script 07 (Build Matrices & 3-Tier Masks)
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
Script 08 (Sanity Checks)     Script 09 (Dev EDA 2000-23)    Script 10 (Forensic Outliers)
```

### Bảng Thống Kê Tổng Quan 13 Scripts

| STT | Tên Script | Mục Đích Chính | Input Chính | Output Chính | Trạng Thái |
|:---:|:---|:---|:---|:---|:---:|
| **01** | `01_parse_all_universe.py` | Trích xuất universe Russell 1000 từ PDF/CSV/XLS 2000–2026 | Raw PDF/CSV/XLS, QC Parquet | `russell1000_pit_by_year.json` | ⚠️ Cần chú ý |
| **02** | `02_quantconnect_availability_scan.py` | Quét độ sẵn sàng của 26,919 ticker-years trên QC | B64 PIT universe, QC API | `russell1000_scan_all.csv` | ⚠️ Cần chú ý |
| **03** | `02_quantconnect_export_10_batches.py` | Xuất 10 batches OHLCV thô từ QC Research | B64 PIT universe, QC API | 10 ZIP files OHLCV | ⚠️ Cần chú ý |
| **04** | `03_process_10_batches_to_parquet.py` | Hợp nhất 10 ZIP thành Parquet theo năm & Master | 10 ZIP files | `russell1000_constituents_daily_ohlcv_1998_2026.parquet` | ✅ OK |
| **05** | `04_audit_identity_and_build_canonical_mapping.py` | Khử trùng bit-for-bit, stitch 2T, phân lập ticker reuse | Raw Master Parquet | Canonical Parquet, Mapping CSVs | ⚠️ Cần chú ý |
| **06** | `04b_generate_comprehensive_step3_audits.py` | Tạo báo cáo đối soát 3,711 SIDs, 26,919 constituent-years | Mapping CSV, Adjusted Parquet | 6 file CSV audit chuyên sâu | ⚠️ Cần chú ý |
| **07** | `05_quantconnect_export_corporate_actions.py` | Xuất toàn bộ Stock Splits & Dividends từ LEAN Factor | B64 universe, QC API | ZIP chứa Splits & Dividends CSV | ⚠️ Cần chú ý |
| **08** | `05_rigorous_pit_membership_reconstruction.py` | Chuẩn hóa membership 6 cấp, phân tích dual coverage | Mapping CSV, PIT JSON, Adj Parquet | 4 file CSV audit membership | ⚠️ Cần chú ý |
| **09** | `06_process_corporate_actions_and_adjusted_prices.py` | Tính CF searchsorted, điều chỉnh split/div, return float64 | Canonical Parquet, Splits/Divs | Tier 2 Adjusted Warehouse (484 MB) | ⚠️ Cần chú ý |
| **10** | `07_build_2d_matrices_and_masks.py` | Lưới 2D 7252x3711, 17 ma trận, 3 lớp PIT masks, purge OOS | Tier 2 Adjusted Parquet | 17 ma trận Parquet, 3 Masks, Targets | ⚠️ Cần chú ý |
| **11** | `08_validate_matrices_and_sanity_checks.py` | Kiểm thử ma trận, mask hierarchy, 50k cell round-trip | Matrices, Masks, Adjusted Parquet | 3 file CSV sanity summary | ⚠️ Cần chú ý |
| **12** | `09_run_development_eda.py` | EDA tập Development (2000-07-01 đến 2023-12-29) | Matrices & Masks | 4 bảng EDA, 4 biểu đồ PNG | ⚠️ Cần chú ý |
| **13** | `10_investigate_extreme_returns.py` | Điều tra pháp y Top 50 +/- return, đồng bộ corrections | Matrices & Masks, Corrections CSV | Top 50 +/- CSV, 34 forensic cases | ⚠️ Cần chú ý |

*(Ghi chú: Đa số các script bị xếp trạng thái "⚠️ Cần chú ý" do sử dụng đường dẫn tuyệt đối hardcoded `D:\A_Learning\...` hoặc là notebook script của QuantConnect; logic thuật toán định lượng đều đạt chuẩn xác cao).*

---

## 2. Chi Tiết Code Review Từng Script (13/13 Active Scripts)

### Script 01: `01_parse_all_universe.py`

**Mục đích:**  
Trích xuất danh sách mã chứng khoán (Point-in-Time constituents) của chỉ số Russell 1000 theo từng năm từ tài liệu thô PDF/CSV/JSON/XLS giai đoạn 2000–2026, loại bỏ stopwords/nhiễu và đối chiếu kiểm tra độ phủ (coverage) với kho dữ liệu thị trường QuantConnect.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/raw/universe/raw_universe/*` | PDF, CSV, JSON, XLS/XLSX | Tùy theo era: text cột, XML rows, JSON `aaData` | Dữ liệu công bố hằng năm từ iShares / FTSE Russell |
| `data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet` | Parquet | `ticker` (str), `year` (int) | Dùng để validate độ phủ đối chiếu |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `data/raw/universe/russell1000_pit_by_year.json` | JSON | Dictionary `{"<year>": ["<ticker>", ...]}` | 426 KB |
| `data/raw/universe/russell1000_constituents.csv` | CSV | `Ticker` (str), `InQC` (bool) | ~45 KB |
| `data/raw/universe/extraction_quality_report.csv` | CSV | `year`, `source_type`, `pit_tickers`, `qc_tickers`, `matched`, `coverage_pct` | 1.06 KB |

**Kỹ thuật Data Engineering:**
- **Multi-era Layout Regex Parsing**: Tách biệt logic phân tích cú pháp theo 3 thời kỳ tài liệu:
  - Era-1 (2000–2007): Regex bắt đầu dòng `^([A-Z][A-Z0-9\-]{0,5})\s{1,4}[A-Z0-9&]`.
  - Era-2 (2009–2015): Regex cuối dòng bắt ticker ở token cuối cùng.
  - Era-3 (2016–2022): Pair-based alternating lines (dòng lẻ tên công ty, dòng chẵn mã chứng khoán).
- **Domain Noise Exclusions**: Bộ lọc từ khóa dừng tài chính (`NOISE_WORDS` gồm 65 từ: THE, CORP, HOLDINGS, REBALANCING...) để triệt tiêu các từ viết hoa gây nhầm lẫn thành ticker.
- **Fast Set Intersection Validation**: Nhóm dữ liệu QC thành dict of sets theo năm `QC_BY_YEAR` để đo lường độ phủ cục bộ từng năm và độ phủ toàn cục.
- **Relative Path Resolution**: Sử dụng `Path(__file__).resolve().parent.parent.parent` độc lập với môi trường chạy.

**Dependencies:**
- Libraries: `pandas`, `pypdf`, `json`, `re`, `glob`, `os`, `sys`, `io`
- Scripts upstream: Không có (Script khởi đầu). Cần có folder `data/raw/universe/raw_universe/`.

**Potential Issues:**
- ⚠️ Script phụ thuộc vào file `data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet` để validate độ phủ. Nếu chạy từ scratch mà chưa có file parquet này, script sẽ bị `FileNotFoundError`.
- ⚠️ Parser Era-3 giả định thứ tự dòng lẻ/chẵn luôn chuẩn. Nếu file PDF bị lỗi ngắt trang (page break header lọt giữa pair), parser có thể bỏ qua một số ticker.

**Trạng thái:** ⚠️ Cần chú ý (Phụ thuộc vòng vào file parquet kiểm tra độ phủ).

---

### Script 02: `02_quantconnect_availability_scan.py`

**Mục đích:**  
Thực thi trên môi trường đám mây QuantConnect Research Notebook để quét tính khả dụng lịch sử của 26,919 lượt ticker-năm (2,884 mã PIT duy nhất qua 27 năm), xác định mã nào có nến thị trường (`MATCH`) hoặc không có dữ liệu (`EMPTY`) trong cửa sổ tái cân bằng (30/06 đến 30/06 năm sau).

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| Base64 string `_B64_DATA` | In-code String | Zlib compressed JSON of PIT universe | Nhúng trực tiếp trong code để chạy trên QC cloud |
| QuantConnect Data Feed | QC Cloud Engine | `qb.History(symbols, start, end, Resolution.Daily)` | Dữ liệu giá vốn từ QC LEAN |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `russell1000_scan/russell1000_scan_{year}.csv` | CSV | `year`, `ticker`, `status`, `rows`, `reason` | ~27 files, mỗi file ~15 KB |
| `russell1000_scan/russell1000_scan_all.csv` | CSV | `year`, `ticker`, `status`, `rows`, `reason` | ~650 KB (26,919 dòng) |

**Kỹ thuật Data Engineering:**
- **In-Memory Payload Decompression**: Giải nén Base64 + zlib trực tiếp thành JSON struct, không cần phụ thuộc đường dẫn file ngoài khi chạy trên cloud notebook.
- **Micro-Batching Memory Management**: Chia nhỏ danh sách 40 symbols/batch kết hợp tường minh `del history` và `gc.collect()` nhằm tránh lỗi Out-Of-Memory (OOM) trong môi trường cấp phát tài nguyên hạn chế của QC Research.
- **Point-in-Time Identity Resolution**: Sử dụng `SecurityIdentifier.GenerateEquity(ticker, Market.USA, mappingResolveDate=start)` để giải quyết chính xác mã cổ phiếu tại đúng thời điểm tái cơ cấu.

**Dependencies:**
- Libraries: `AlgorithmImports` (QuantConnect), `pandas`, `base64`, `zlib`, `json`, `os`, `gc`, `datetime`
- Scripts upstream: Script 01 (Cung cấp payload danh sách PIT universe).

**Potential Issues:**
- ⚠️ Script được thiết kế chạy chuyên biệt trên QuantConnect Notebook (`QuantBook()`, `display()`), không thể thực thi trực tiếp trên local shell nếu không cài đặt QuantConnect Lean engine cục bộ.
- ⚠️ Sử dụng `datetime.utcnow().date()` (đã bị deprecated từ Python 3.12+).

**Trạng thái:** ⚠️ Cần chú ý (Môi trường QuantConnect Notebook-only).

---

### Script 03: `02_quantconnect_export_10_batches.py`

**Mục đích:**  
Thực thi trên QuantConnect Research Notebook để trích xuất dữ liệu giá nến thô (OHLCV Unadjusted - `DataNormalizationMode.Raw`) cho 2,871 mã chứng khoán thành viên Russell 1000 chia thành 10 batch độc lập từ 1998 đến 2026, đóng gói tự động thành file ZIP nén chứa audit danh tính và link tải trực tiếp.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| Base64 string `_B64_DATA` | In-code String | Zlib compressed list of 2,871 valid unique tickers | Nhúng trong code |
| QuantConnect Data Feed | QC Cloud Engine | `qb.History([sym], start, end, Resolution.Daily)` | Chế độ `DataNormalizationMode.Raw` |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `russell_market_batch_{XX}_of_10.zip` | ZIP Archive | Chứa `raw/year={year}/*.csv`, `audit/*_status.csv`, `audit/*_identity.csv` | 10 files ZIP, mỗi file ~15–25 MB |

**Kỹ thuật Data Engineering:**
- **Two-Tier Resilient Ingestion Batching**: Phân chia 10 batch xuất lớn, mỗi batch chia nhỏ thành các sub-groups 20 symbols. Nếu một sub-group bị lỗi, hệ thống tự động fallback truy vấn từng symbol riêng lẻ để không làm gián đoạn toàn bộ batch.
- **Format Aliasing & Disambiguation Control**: Tự động thử nghiệm các định dạng alias phổ biến (`BF-B` -> `BF.B`), nhưng áp dụng danh sách chặn cứng `BLOCK_AUTOMATIC_ALIAS` (`{'ENR','PL','BTU','CR','MOS','XTSLA'}`) để ngăn chặn việc tự động ghép nhầm công ty khác có cùng tên viết tắt.
- **In-Memory ZIP Packaging & HTML Download Injector**: Toàn bộ các file CSV theo năm và file audit được nén trực tiếp vào `zipfile.ZipFile` trong RAM và inject thành thẻ HTML `<a download="..." href="data:application/zip;base64,...">` để tải nhanh về máy cục bộ.

**Dependencies:**
- Libraries: `AlgorithmImports` (QuantConnect), `pandas`, `json`, `zlib`, `base64`, `io`, `zipfile`, `time`, `datetime`, `IPython.display`
- Scripts upstream: Script 01, Script 02.

**Potential Issues:**
- ⚠️ Môi trường QuantConnect Notebook-only.
- ⚠️ Biến `BATCH_INDEX = 0` được hardcode cấu hình (người dùng phải đổi thủ công từ 0 đến 9 cho 10 lượt chạy).

**Trạng thái:** ⚠️ Cần chú ý (Môi trường QuantConnect Notebook-only).

---

### Script 04: `03_process_10_batches_to_parquet.py`

**Mục đích:**  
Giải nén trực tiếp trong bộ nhớ 10 file ZIP xuất từ QuantConnect, khử trùng lặp và hợp nhất toàn bộ dữ liệu giá nến thô thành các tệp Parquet phân vùng theo năm (`by_year/`) cùng một kho dữ liệu Master Parquet hợp nhất duy nhất (`russell_daily_ohlcv_1998_2026.parquet`), đồng thời tổng hợp các bảng audit status và identity.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/raw/market_data/russell_market_batch_*.zip` | ZIP Files | 10 ZIP files chứa CSVs theo năm và audit CSVs | Tải về từ QC Research Notebook |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `data/processed/market_data/by_year/russell_ohlcv_{year}.parquet` | Parquet | `date`, `original_ticker`, `qc_ticker`, `sid`, `open`, `high`, `low`, `close`, `volume` | 29 files, ~5–12 MB/file |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` | Parquet | Tương tự trên, `date` (datetime64[ns]) | ~200–250 MB |
| `data/processed/market_data/master_batch_status.csv` | CSV | `year`, `original_ticker`, `status`, `bars`, `error` | 1.80 MB |
| `data/processed/market_data/master_batch_identity.csv` | CSV | `year`, `original_ticker`, `candidate`, `sid`, `anchor_date`, `mapping_type` | 4.64 MB |

**Kỹ thuật Data Engineering:**
- **Direct Stream Extraction**: Đọc trực tiếp từng file CSV từ stream của ZIP thông qua `zipfile.ZipFile.open()` mà không cần giải nén bung toàn bộ dữ liệu ra ổ cứng, tiết kiệm hơn 10 GB dung lượng đĩa tạm.
- **Partitioned & Columnar Optimization**: Chuyển đổi định dạng CSV sang Apache Parquet nén `snappy`, phân vùng theo từng năm phục vụ truy vấn phân tán và kết hợp tạo Master dataset.
- **Deterministic Deduplication**: Khử trùng lặp trên cặp khóa `['date', 'original_ticker']` đảm bảo tính duy nhất.

**Dependencies:**
- Libraries: `pandas`, `pyarrow`, `pathlib.Path`, `glob`, `zipfile`, `os`
- Scripts upstream: Script 02/03 (Xuất 10 file ZIP).

**Potential Issues:**
- ✅ **Schema/Path Unification**: Script 03 lưu master parquet trực tiếp tại `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet`, hoàn toàn đồng bộ với đường dẫn đọc của Script 04.
- ⚠️ Comment đầu file ghi "split-adjusted Parquet dataset" nhưng thực chất dữ liệu ở bước này vẫn là Raw OHLCV (chưa split-adjusted).

**Trạng thái:** ✅ OK.

---

### Script 05: `04_audit_identity_and_build_canonical_mapping.py`

**Mục đích:**  
Thẩm định danh tính chứng khoán toàn diện (Identity Audit): loại bỏ 1.57 triệu dòng trùng lặp bit-for-bit từ các cặp alias, nối mượt (stitch) 752 mã tạm thời dạng placeholder `' 2T'` của QuantConnect sang mã vĩnh viễn (Permanent SID) với ngưỡng khoảng cách <= 10 ngày, phân lập tuyệt đối 1,281 ticker có hiện tượng Ticker Reuse qua các năm thành các `canonical_sid` độc lập, và tạo kho dữ liệu Tier 2 Canonical có khóa chính `(date, canonical_sid)` duy nhất 100%.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` | Parquet | `date`, `original_ticker`, `qc_ticker`, `sid`, `open`, `high`, `low`, `close`, `volume` | 13,147,389 dòng |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/transient_2t_resolution_audit.csv` | CSV | `original_ticker`, `raw_sid`, `canonical_sid`, `resolution_type`, `gap_calendar_days` | 79.28 KB (846 dòng) |
| `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | CSV | `original_ticker`, `raw_sid`, `canonical_sid`, `resolution_type`, `min_date`, `max_date` | 392.51 KB (4,463 dòng) |
| `docs/Data report/market_data_audit/tables/ticker_reuse_audit.csv` | CSV | `original_ticker`, `raw_sid`, `canonical_sid`, `min_date`, `max_date` | 195.55 KB |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet` | Parquet | `date`, `canonical_sid`, `original_ticker`, `qc_ticker`, `open`, `high`, `low`, `close`, `volume` | 155.76 MB (12,247,081 dòng) |

**Kỹ thuật Data Engineering:**
- **Bit-for-Bit Duplicate Verification**: Nhóm các dòng trùng lặp `(date, sid)` và kiểm tra `max_close_diff == 0.0` qua lệnh `assert`. Xác nhận 100% các bản ghi trùng khớp từng bit nhị phân trước khi khử trùng lặp.
- **Temporal Heuristic 2T Stitching**: Phân tích vòng đời (min date, max date), nối các mã kết thúc bằng `' 2T'` với mã vĩnh viễn liền kề trước hoặc sau nếu khoảng cách thời gian `gap_calendar_days <= 10`, đồng thời cô lập các mã gián đoạn lớn (`STANDALONE_2T_DISCONTINUOUS`).
- **Ticker Reuse Disambiguation**: Phân lập dứt khoát 1,281 ticker được tái sử dụng thành 3,711 canonical entities duy nhất.
- **High-Compression ZSTD Parquet Storage**: Sử dụng engine `pyarrow` với thuật toán nén `zstd` (level 7), giảm dung lượng từ 198 MB xuống 155 MB dù giữ nguyên 12.25 triệu dòng.

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `time`, `sys`
- Scripts upstream: Script 03/04 (`russell1000_constituents_daily_ohlcv_1998_2026.parquet`).

**Potential Issues:**
- ⚠️ Dòng 28 hardcode đường dẫn tuyệt đối: `BASE_DIR = Path(r"D:\A_Learning\HK1_2026-2027\CO3101 - Đồ án tổng hợp - ttnt\Predict_daily_return_rankings")`. Sẽ quăng lỗi nếu chạy trên máy tính khác hoặc thư mục khác.
- Thư viện `numpy` được import nhưng không dùng trực tiếp.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

### Script 06: `04b_generate_comprehensive_step3_audits.py`

**Mục đích:**  
Tạo hệ thống 6 báo cáo kiểm toán chuyên sâu phục vụ Bước 3: đối soát toàn bộ 3,711 Canonical SIDs (phân loại thành `CONFIRMED` vs `ASSUMED_UNVERIFIED`), tái thiết lập membership thời gian thực cho 26,919 constituent-years theo chu kỳ thường niên [01/07 năm Y đến 30/06 năm Y+1], thẩm định 162 ca đổi mã (aliases), đối soát Ticker Reuse và đo lường độ biến động (churn rate) cùng độ sẵn sàng dữ liệu lịch sử (warmup readiness >= 20 ngày) tại ranh giới tái cân bằng 30/06 -> 01/07.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | CSV | `original_ticker`, `raw_sid`, `canonical_sid`, `resolution_type`, `min_date`, `max_date` | 4,463 dòng |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | Parquet | `date`, `original_ticker`, `canonical_sid` | Kho dữ liệu giá nến |
| `data/raw/universe/russell1000_pit_by_year.json` | JSON | Annual constituent list | 27 snapshots |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/canonical_sid_reconciliation_audit.csv` | CSV | `canonical_sid`, `original_tickers`, `mapping_evidence`, `verification_status` | 693.62 KB (3,711 dòng) |
| `docs/Data report/market_data_audit/tables/temporal_mapping_heuristic_audit.csv` | CSV | `period_year`, `source_ticker`, `assigned_canonical_sids`, `resolution_category` | 4.38 MB (26,919 dòng) |
| `docs/Data report/market_data_audit/tables/period_reconciliation_summary.csv` | CSV | `snapshot_year`, `official_tickers`, `resolved_confirmed`, `coverage_with_bars_pct` | 1.14 KB (27 dòng) |
| `docs/Data report/market_data_audit/tables/ticker_changes_audit.csv` | CSV | `canonical_sid`, `tickers_involved`, `lifecycle_details`, `verification_status` | 46.38 KB (162 dòng) |
| `docs/Data report/market_data_audit/tables/ticker_reuse_temporal_audit.csv` | CSV | `reused_ticker`, `distinct_entities_count`, `canonical_sids`, `temporal_separation_details` | 223.68 KB |
| `docs/Data report/market_data_audit/tables/june_july_boundary_transition_audit.csv` | CSV | `transition`, `boundary_date`, `entering_constituents`, `warmup_readiness_pct`, `churn_rate_pct` | 2.77 KB (26 dòng) |

**Kỹ thuật Data Engineering:**
- **Vectorized Reconstitution Period Indexing**: Gán chu kỳ tái cân bằng chuẩn xác bằng đại số vector numpy: `np.where(dt.month >= 7, dt.year, dt.year - 1)`.
- **Pre-Indexed Triplet Inversion**: Gom nhóm và lập từ điển băm `triplets_dict[(period_year, ticker)]` giúp ánh xạ 26,919 mã nguồn chỉ trong vài giây.
- **Lookback Warmup Continuity Verification**: Truy vấn nến lịch sử trước ngày 01/07 cho các mã mới gia nhập rổ để chứng minh tính khả thi của các tính toán rolling lookback 20 ngày.

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `json`, `time`, `sys`, `os`
- Scripts upstream: Script 04 (`canonical_security_mapping.csv`), Script 01 (`russell1000_pit_by_year.json`), và Script 06 (`russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet`).

**Potential Issues:**
- ⚠️ Dòng 32 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.
- ⚠️ **Execution Order Anomaly**: Script có tiền tố `04b_` nhưng lại đọc file `..._adjusted_1998_2026.parquet` vốn được sinh ra bởi Script 06 (`06_process_corporate_actions_and_adjusted_prices.py`). Nếu chạy pipeline theo thứ tự số thứ tự file (04 -> 04b -> 05 -> 06), script này sẽ bị lỗi thiếu file.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded path & Phụ thuộc dữ liệu output từ Script 06).

---

### Script 07: `05_quantconnect_export_corporate_actions.py`

**Mục đích:**  
Thực thi trên QuantConnect Research Notebook để trích xuất toàn bộ dữ liệu sự kiện chia tách cổ phiếu (Stock Splits) và chi trả cổ tức tiền mặt (Cash Dividends) từ cơ sở dữ liệu LEAN Factor Files cho 2,871 mã cổ phiếu Russell 1000 từ 1998 đến 2026, đóng gói thành file ZIP nén để tải về phục vụ xử lý local.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| Base64 string `_B64_DATA` | In-code String | Zlib compressed universe (2,871 tickers) | Nhúng trực tiếp trong code |
| QuantConnect Data Feed | QC Cloud Engine | `qb.History[Split]` & `qb.History[Dividend]` | C# generic history query |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `russell1000_corporate_actions_1998_2026.zip` | ZIP Archive | Chứa `russell1000_splits_1998_2026.csv` và `russell1000_dividends_1998_2026.csv` | ~1.5–2.5 MB |

**Kỹ thuật Data Engineering:**
- **Generic Class Enumeration**: Sử dụng interface typed `History[Split]` và `History[Dividend]` của QuantConnect để truy xuất chuẩn xác các sự kiện doanh nghiệp.
- **Multi-variant C# Duck-Typing Extractor**: Hàm `extract_items` linh hoạt thích ứng với cả dictionary items, `.Keys` và `.KeyValuePair` của .NET CLR.
- **Chunked Query Resiliency**: Gom nhóm 100 symbols/chunk và tự động fallback sang từng symbol riêng lẻ khi gặp lỗi.

**Dependencies:**
- Libraries: `AlgorithmImports` (QuantConnect), `pandas`, `json`, `zlib`, `base64`, `io`, `zipfile`, `time`, `datetime`, `IPython.display`
- Scripts upstream: Script 01, Script 02.

**Potential Issues:**
- ⚠️ Môi trường QuantConnect Notebook-only.
- ⚠️ **Dead Code / Copy-paste Duplication**: Dòng 275–280 có 2 khối lệnh `if (i // CHUNK_SIZE + 1) % 5 == 0 ... print(...)` giống hệt nhau liên tiếp.

**Trạng thái:** ⚠️ Cần chú ý (QC cloud notebook tool; duplicate print statement).

---

### Script 08: `05_rigorous_pit_membership_reconstruction.py`

**Mục đích:**  
Chuẩn hóa học thuật về tái thiết lập Point-In-Time membership: đối soát 2,884 unique tickers sang 3,711 Canonical SIDs (hiện tượng Ticker Reuse), phân loại bằng chứng thành 6 cấp độ (LEVEL_1 đến LEVEL_6), giải trình hiện tượng xung đột đa SID (`AMBIGUOUS_DATE_CONFLICT` vs `AMBIGUOUS_DISCONTINUOUS_GAP`), và phân biệt rạch ròi 2 thước đo: Ticker-Period Coverage (Độ phủ vĩ mô theo kỳ) vs Daily Stock-Day Coverage (Độ phủ vi mô nến cổ phiếu-ngày).

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/raw/universe/russell1000_pit_by_year.json` | JSON | Annual constituent list | 27 snapshots |
| `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | CSV | `original_ticker`, `raw_sid`, `canonical_sid`, `min_date`, `max_date` | Bảng ánh xạ danh tính |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | Parquet | `date`, `original_ticker`, `canonical_sid` | Kho nến đã điều chỉnh |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv` | CSV | `period_year`, `source_ticker`, `evidence_level`, `verification_status` | 4.38 MB (26,919 dòng) |
| `docs/Data report/market_data_audit/tables/ambiguous_multi_sid_audit.csv` | CSV | `period_year`, `ticker`, `ambiguity_type`, `canonical_sids`, `details` | ~15 KB |
| `docs/Data report/market_data_audit/tables/coverage_ticker_period_vs_daily_stock_days.csv` | CSV | `snapshot_year`, `ticker_period_coverage_pct`, `daily_stock_day_coverage_pct` | 1.89 KB (27 dòng) |
| `docs/Data report/market_data_audit/tables/ticker_to_canonical_sid_reuse_breakdown.csv` | CSV | `ticker`, `entity_count`, `canonical_sids`, `entity_lifecycles` | 300.82 KB (2,884 dòng) |

**Kỹ thuật Data Engineering:**
- **Interval Overlap Arithmetic**: Xác định sự hiện diện của chứng khoán trong kỳ thông qua bất đẳng thức khoảng giao: `r.min_date <= p_end and r.max_date >= p_start`.
- **Multi-SID Conflict Isolation**: Phát hiện xung đột ngày hoạt động của 2 SIDs có cùng ticker (`max_date >= min_date` của entity kế tiếp), phân loại vào `AMBIGUOUS_DATE_CONFLICT` để loại khỏi universe giao dịch.
- **Dual Coverage Metric Formulation**: Tách bạch rõ giữa tỷ lệ % mã hiện diện trong năm (trung bình ~99.0%) và tỷ lệ % số nến thực tế giao dịch so với lý thuyết (trung bình ~87.4% do delisting, sáp nhập, IPO giữa năm).

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `collections.defaultdict`, `json`, `time`, `sys`, `os`
- Scripts upstream: Script 01, Script 04, và Script 06.

**Potential Issues:**
- ⚠️ Dòng 36 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.
- ⚠️ **Execution Order Anomaly**: Tên script mang số thứ tự `05_` nhưng đọc `russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` từ Script 06.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded path & Phụ thuộc output từ Script 06).

---

### Script 09: `06_process_corporate_actions_and_adjusted_prices.py`

**Mục đích:**  
Tính toán hệ số chia tách dồn tích liên tục (Cumulative Split Factor $CF_{i,t}$) theo thời gian bằng phương pháp tìm kiếm nhị phân `np.searchsorted` lùi (backward adjustment), tích hợp bảng corrections có bằng chứng (Reverse Splits, Spinoffs, Quality Flags), tính toán chuỗi giá điều chỉnh và lợi suất ngày (`daily_return`, `total_return`) ở độ chính xác nguyên bản `float64` (loại bỏ làm tròn), đo lường khoảng trống phiên giao dịch theo lịch NYSE (`trading_session_gap`, `is_consecutive_session`), và ghi kho dữ liệu Tier 2 Adjusted Warehouse (484 MB).

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet` | Parquet | `date`, `original_ticker`, `sid`, `close`, `volume` | Dữ liệu nến thô |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet` | Parquet | `date`, `canonical_sid`, `open`, `high`, `low`, `close`, `volume` | Dữ liệu nến canonical |
| `data/processed/constituents_market_data/corporate_actions/russell1000_splits_1998_2026.csv` | CSV | `date`, `sid`, `split_factor`, `reference_price` | Dữ liệu chia tách |
| `data/processed/constituents_market_data/corporate_actions/russell1000_dividends_1998_2026.csv` | CSV | `date`, `sid`, `dividend_amount`, `reference_price` | Dữ liệu cổ tức |
| `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | CSV | `raw_sid`, `canonical_sid` | Bảng ánh xạ SID |
| `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv` | CSV | `event_id`, `correction_layer`, `parameter_value` | Bảng hiệu chỉnh CORR_001..013 |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/2t_stitching_conflict_audit.csv` | CSV | `date`, `canonical_sid`, `close_diff`, `vol_diff` | 59.84 MB |
| `docs/Data report/market_data_audit/tables/splits_matched_unmatched_audit.csv` | CSV | `date`, `canonical_sid`, `split_factor`, `match_status` | 156.10 KB |
| `docs/Data report/market_data_audit/tables/dividends_matched_unmatched_audit.csv` | CSV | `date`, `canonical_sid`, `dividend_amount`, `match_status` | 5.75 MB |
| `docs/Data report/market_data_audit/tables/corporate_actions_match_summary.csv` | CSV | `event_type`, `total_events`, `matched_exact_bar`, `match_rate` | 0.13 KB |
| `docs/Data report/market_data_audit/tables/split_formula_mathematical_audit.csv` | CSV | `event`, `ticker`, `observed_cf_ratio`, `return_formula_error` | 3.23 KB |
| `docs/Data report/market_data_audit/tables/dividend_identity_mathematical_audit.csv` | CSV | `ticker`, `adj_dividend`, `dividend_yield`, `identity_error` | 1.06 KB |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | Parquet | 25 cột (xem chi tiết schema bên dưới), nén `zstd` level 7 | 484.32 MB (12,247,081 dòng) |

**Kỹ thuật Data Engineering:**
- **Searchsorted Backward Cumulative Factor**:
  - Tính toán mảng hệ số tích lũy: `cf_lookup = np.cumprod(s_factors[::-1])[::-1]` với mốc neo ngày hiện tại bằng 1.0.
  - Ánh xạ vector tốc độ cao: `pos = np.searchsorted(s_dates, t_dates, side='right')` cho phép gán hệ số điều chỉnh chuẩn xác với độ phức tạp $O(\log M)$, hoàn toàn không bị ảnh hưởng nếu ngày thực hiện chia tách rơi vào ngày nghỉ hoặc không có nến.
- **Institutional Float64 Precision**: Giữ nguyên độ chính xác 64-bit float cho `adj_close` và `adj_volume`, bỏ triệt để các lệnh làm tròn số thập phân trước khi tính return, ngăn ngừa tích lũy sai số vi mô (micro-rounding bias).
- **Trading Session Gap Tracking**: Xây dựng mảng lịch giao dịch chính thức của NYSE (`nyse_trading_dates`), đo lường khoảng cách phiên thực tế `session_gap = curr_session_idx - prev_session_idx` để xác định chính xác các phiên liên tục chuẩn (`is_consecutive_session == True` khi gap = 1).
- **Forensic Corrections Injection**: Tích hợp trực tiếp 13 ca hiệu chỉnh có bằng chứng từ `market_data_corrections_and_exceptions.csv`:
  - 5 ca Reverse Splits (CHK 1:200, CRC 1:10, ADCT 1:7, AA 1:3, DYN 1:5) được đưa vào tầng tính Cumulative Factor.
  - 4 ca Spin-offs (KSU, SSP, COMS, PENN) và 4 ca Bad Ticks/Collisions (MKL, SABR, LOW, CPTH) được cách ly trong `is_bad_data_period` / `is_spinoff_discontinuity` và gán return = NaN cùng phiên phục hồi kế tiếp.
- **Mathematical Equivalence Assertions**: Kiểm tra đẳng thức toán học khắt khe `assert max_div_error < 1e-12` và kiểm thử 26 sự kiện chia tách kinh điển.

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `time`, `sys`, `os`
- Scripts upstream: Script 04 (`canonical_parquet`), Script 05/07 (`corporate_actions CSVs`).

**Potential Issues:**
- ⚠️ Dòng 26 hardcode đường dẫn tuyệt đối: `BASE_DIR = Path(r"D:\A_Learning\...")`.
- Thư viện `os` được import nhưng không dùng.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

### Script 10: `07_build_2d_matrices_and_masks.py`

**Mục đích:**  
Thiết lập lưới tọa độ chính quy 2D đồng bộ thời gian (7,252 phiên NYSE x 3,711 Canonical SIDs), tái cấu trúc 17 ma trận giá/khối lượng/return dạng wide-format Parquet, xuất bảng phân đoạn hiệu lực Segment Mapping, và thiết lập hệ thống 3 lớp mask Point-In-Time (Membership Mask, Tradability Mask, Training Label Mask) cùng các ma trận mục tiêu tương lai (`target_next_return`, `target_next_total_return`) với cơ chế purge triệt để ranh giới Out-of-Sample.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | Parquet | 25 cột (Tier 2 Warehouse) | 12,247,081 dòng |
| `data/raw/universe/russell1000_pit_by_year.json` | JSON | Annual constituent list | 27 snapshots |
| `docs/Data report/market_data_audit/tables/canonical_security_mapping.csv` | CSV | Mapping SIDs | 4,463 dòng |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `data/processed/matrices/matrix_dates_index.parquet` | Parquet | `date` (datetime64[ns]) | 7,252 dòng (~60 KB) |
| `data/processed/matrices/matrix_columns_sids.parquet` | Parquet | `canonical_sid` (str) | 3,711 dòng (~40 KB) |
| 17 ma trận 2D (`adj_close.parquet`, `daily_return.parquet`, `volume.parquet`, ...) | Parquet | Index: dates (7,252), Columns: SIDs (3,711), Values: float64/bool | Mỗi file ~50–110 MB (Tổng ~1 GB) |
| `data/processed/matrices/membership_mask.parquet` | Parquet | Index: dates, Columns: SIDs, Values: bool | 2.10 MB |
| `data/processed/matrices/valid_data_mask.parquet` | Parquet | Index: dates, Columns: SIDs, Values: bool | 2.10 MB |
| `data/processed/matrices/valid_label_mask.parquet` | Parquet | Index: dates, Columns: SIDs, Values: bool | 2.11 MB |
| `data/processed/matrices/target_next_return.parquet` | Parquet | Index: dates, Columns: SIDs, Values: float64 (NaN outside mask) | 58.90 MB |
| `data/processed/matrices/target_next_total_return.parquet` | Parquet | Index: dates, Columns: SIDs, Values: float64 | 58.90 MB |
| `docs/Data report/market_data_audit/tables/universe_constituent_segments_mapping.csv` | CSV | Segment-level mapping (1 SID - 1 validity range per row) | 4.55 MB (27,477 dòng) |
| `docs/Data report/market_data_audit/tables/matrix_and_mask_coverage_by_period.csv` | CSV | Coverage stats per reconstitution period | 4.20 KB |

**Kỹ thuật Data Engineering:**
- **Canonical Coordinate Grid Synchronization**: Khởi tạo khung tọa độ chuẩn xác 7,252 ngày giao dịch x 3,711 mã chứng khoán chính quy = 26,942,172 ô. Chuyển đổi dữ liệu từ dạng bảng dài (long-form) sang dạng bảng rộng (wide 2D matrix) cho phép vector hóa các phép tính cross-sectional ranking và time-series rolling trong mô hình ML.
- **Segment-Level Validity Mapping**: Mỗi dòng trong `universe_constituent_segments_mapping.csv` đại diện cho một phân đoạn duy nhất gồm 1 SID và 1 khoảng hiệu lực `[effective_start_date, effective_end_date]`. Các ca đa SID hoặc gián đoạn lớn (>10 ngày) được đánh dấu loại trừ tường minh (`is_included_in_mask = False`).
- **3-Tier Layered PIT Masks Architecture**:
  1. *Membership Mask (Layer 1)*: Kích hoạt strictly trong khoảng ngày hiệu lực từ hồ sơ rổ chỉ số. Toàn bộ giai đoạn warm-up 1998–1999 là `False`.
  2. *Tradability / Valid Data Mask (Layer 2)*: Giao của 6 điều kiện đồng thời: `Member & Price > 0 & Vol > 0 & is_consecutive_session & cum_bars >= 20 & ~is_bad_data_period & ~is_spinoff_discontinuity`.
  3. *Training Label Mask (Layer 3)*: Đảm bảo nến hiện tại hợp lệ VÀ nến tương lai T+1 hợp lệ (`Close_{T+1} > 0, Vol_{T+1} > 0, is_consecutive_{T+1}`).
- **Temporal Boundary Purging (Anti-Leakage Mechanism)**:
  - Dòng 387–390: `purge_dates = [unique_dates[-1], pd.Timestamp("2023-12-29")]`.
  - Ép buộc toàn bộ nhãn tương lai tại phiên cuối cùng của tập Development (`2023-12-29`) thành `NaN`. Cơ chế này ngăn chặn 100% rò rỉ thông tin từ ngày giao dịch đầu tiên của OOS (`2024-01-02`) vào mô hình huấn luyện!

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `collections.defaultdict`, `json`, `time`, `sys`, `os`
- Scripts upstream: Script 06 (`russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet`).

**Potential Issues:**
- ⚠️ Dòng 38 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

### Script 11: `08_validate_matrices_and_sanity_checks.py`

**Mục đích:**  
Thực thi bộ kiểm thử hậu chuyển đổi (Post-Transformation Sanity Checks) trên 17 ma trận 2D và 3 lớp PIT masks: kiểm tra tính phân cấp nghiêm ngặt của masks (`valid_label <= valid_data <= membership`), kiểm định dịch chuyển nhãn nhân quả ($target\_next\_return_T = daily\_return_{T+1}$), đối soát round-trip 50,000 ô dữ liệu với kho gốc với sai số tuyệt đối < 1e-12, và thẩm định tính liên tục tại biên các đợt chia tách cổ phiếu.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/matrices/*.parquet` | Parquet | 17 ma trận, 3 masks, target | 7252 x 3711 |
| `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` | Parquet | Tier 2 Adjusted Warehouse | Dùng đối soát round-trip |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/matrix_reconciliation_audit.csv` | CSV | `field`, `sampled_cells`, `max_absolute_error`, `status` | 0.31 KB |
| `docs/Data report/market_data_audit/tables/matrix_split_boundary_audit.csv` | CSV | `ticker`, `ex_date`, `raw_close_prev`, `adj_close_ex`, `status` | 1.39 KB |
| `docs/Data report/market_data_audit/tables/matrix_sanity_check_summary.csv` | CSV | `Metric`, `Value`, `Status` (Toàn bộ PASSED) | 0.82 KB |

**Kỹ thuật Data Engineering:**
- **Strict Mask Hierarchy Assertion**: Sử dụng đại số boolean `(l_arr & ~d_arr).sum() == 0` và `(d_arr & ~m_arr).sum() == 0` xác nhận không có bất kỳ cell nào vi phạm cấu trúc hình nón của mask.
- **Target Shift Discrepancy & Leakage Verification**: Đo lường độ lệch tuyệt đối giữa target và `daily_return.shift(-1)` trên toàn bộ valid cells, kiểm tra `assert max_label_diff < 1e-14`, đồng thời kiểm tra `non_nan_invalid_targets == 0` (mọi ô ngoài mask đều là NaN).
- **Randomized Multi-Field Round-Trip Reconciliation**: Lấy mẫu ngẫu nhiên 50,000 dòng từ kho nến gốc, tra cứu chỉ mục tọa độ ma trận tương ứng, đối soát 5 trường dữ liệu chính (`adj_close`, `adj_volume`, `daily_return`, `total_return`, `cumulative_split_factor`), khẳng định sai số số học = 0.00.

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `time`, `sys`, `os`
- Scripts upstream: Script 06 và Script 07.

**Potential Issues:**
- ⚠️ Dòng 31 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.
- Thư viện `os` và `json` được import nhưng không dùng.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

### Script 12: `09_run_development_eda.py`

**Mục đích:**  
Thực hiện phân tích khám phá dữ liệu (Exploratory Data Analysis - EDA) độc quyền trên tập Development (2000-07-01 đến 2023-12-29, gồm 5,913 phiên), tuân thủ nguyên tắc định lượng "Zero Data Snooping" (tập Out-Of-Sample 2024–2026 hoàn toàn đóng băng không bị đọc), phân tích 4 moments thống kê (Kurtosis 66.88, Skewness +0.563, Vol 2.65%), phân tích hiện tượng đuôi béo (fat-tails), biến động churn rổ chỉ số hằng năm, độ phân tán chéo (cross-sectional dispersion) qua các cuộc khủng hoảng, và phân vị thanh khoản (Liquidity Deciles D1–D10).

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/matrices/*.parquet` | Parquet | Lưới ma trận, masks, prices, returns | Cắt lát vùng Development |
| `data/raw/universe/russell1000_pit_by_year.json` | JSON | PIT constituent list 2000–2023 | Dùng tính churn |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/eda_daily_return_moments.csv` | CSV | `mean`, `daily_vol`, `skewness`, `excess_kurtosis`, `p01`..`p99_9` | 0.69 KB |
| `docs/Data report/market_data_audit/tables/eda_universe_dynamics_by_year.csv` | CSV | `snapshot_year`, `entering_stocks`, `annual_churn_pct` | 1.08 KB |
| `docs/Data report/market_data_audit/tables/eda_cross_sectional_dispersion.csv` | CSV | `year`, `avg_dispersion`, `max_dispersion`, `min_dispersion` | 2.13 KB |
| `docs/Data report/market_data_audit/tables/eda_liquidity_deciles.csv` | CSV | `liquidity_decile`, `median_daily_dollar_vol_mil`, `avg_annual_volatility` | 0.55 KB |
| `docs/Data report/market_data_audit/figures/eda_*.png` | PNG Figures | 4 biểu đồ độ phân giải cao 300 DPI | ~4 files, 150–250 KB/file |

**Kỹ thuật Data Engineering:**
- **Strict OOS Temporal Isolation**:
  - Khai báo hằng số cứng: `DEV_START = pd.Timestamp("2000-07-01")`, `DEV_END = pd.Timestamp("2023-12-29")`.
  - Toàn bộ ma trận được cắt lát thông qua `.loc[dev_dates]`. Dữ liệu giai đoạn 2024–2026 hoàn toàn không bị nạp vào bộ nhớ tính toán hay vẽ biểu đồ.
- **High-Moment Robust Estimation**: Tính toán chính xác 4 moments thống kê trên 5,610,691 quan sát nến hợp lệ (`valid_data_mask`). Xác nhận Kurtosis thực nghiệm là **66.88** (sửa chữa hoàn toàn sai số 3.4 triệu của pipeline cũ do chia tách chưa điều chỉnh).
- **Cross-Sectional Daily Volatility Vectorization**: Tính toán độ phân tán chéo $\sigma_t^{CS} = \text{std}_{i \in \text{valid}}(r_{i,t})$ theo từng phiên, phân tích các cú sốc thị trường (Dot-com 2000-2002, GFC 2008, COVID-19 2020, Fed Hikes 2022).
- **Dollar Volume Quantile Segmentation**: Sử dụng `pd.qcut` chia 10 nhóm thanh khoản D1–D10 để khảo sát mối tương quan nghịch giữa thanh khoản và biến động.

**Dependencies:**
- Libraries: `pandas`, `numpy`, `scipy.stats`, `matplotlib`, `pyarrow`, `pathlib.Path`, `json`, `time`, `sys`, `os`
- Scripts upstream: Script 07 (`matrices` và `masks`).

**Potential Issues:**
- ⚠️ Dòng 34 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.
- Thư viện `os` được import nhưng không dùng.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

### Script 13: `10_investigate_extreme_returns.py`

**Mục đích:**  
Điều tra pháp y định lượng (Forensic Investigation) đối với các biến động lợi suất cực đoan (Top 50 dương và Top 50 âm) trên tập Development (2000–2023), đồng bộ các can thiệp từ bảng corrections (13 sự kiện CORR_001..CORR_013), đối soát tài liệu quy định chính thức (SEC Form 8-K, FDIC, FHFA, Bankruptcy Court) cho các biến cố sụp đổ lịch sử (Lehman Brothers, WorldCom, Washington Mutual, Enron, Bear Stearns, Fannie Mae, Freddie Mac, MFA Financial), và phân loại minh bạch các ca chưa có nguồn kiểm chứng độc lập thành `UNVERIFIED_PRICE_SHOCK`.

**Input:**
| File | Format | Schema cột chính | Ghi chú |
|---|---|---|---|
| `data/processed/matrices/*.parquet` | Parquet | `daily_return`, `valid_data_mask`, `adj_close`, `close`, `cumulative_split_factor` | Lưới ma trận |
| `docs/Data report/market_data_audit/tables/universe_constituent_segments_mapping.csv` | CSV | Segment mapping | Tra cứu ticker |
| `docs/Data report/market_data_audit/tables/market_data_corrections_and_exceptions.csv` | CSV | 13 sự kiện corrections có bằng chứng | Bảng hiệu chỉnh |

**Output:**
| File | Format | Schema cột chính | Kích thước ước tính |
|---|---|---|---|
| `docs/Data report/market_data_audit/tables/top_50_positive_returns_audit.csv` | CSV | `rank`, `date`, `source_ticker`, `clean_daily_return_pct`, `cumulative_split_factor_curr` | 6.23 KB (50 dòng) |
| `docs/Data report/market_data_audit/tables/top_50_negative_returns_audit.csv` | CSV | `rank`, `date`, `source_ticker`, `clean_daily_return_pct`, `raw_close_curr` | 6.38 KB (50 dòng) |
| `docs/Data report/market_data_audit/tables/extreme_returns_forensic_investigation.csv` | CSV | `investigation_id`, `event_type`, `date`, `source_ticker`, `classification`, `primary_evidence_source` | 16.70 KB (34 ca chi tiết) |

**Kỹ thuật Data Engineering:**
- **Flat-to-2D Coordinate Projection**: Tối ưu hóa truy vết tọa độ phẳng `(r, c) = (idx // n_cols, idx % n_cols)` để trích xuất tức thời thông tin ngày và mã chứng khoán trong $O(1)$ mà không cần duyệt lặp toàn ma trận.
- **Three-Dimensional Forensic Triangulation**: Đối chiếu tam giác giữa giá nến thô (`raw_close`), hệ số điều chỉnh dồn tích (`cumulative_split_factor`), và giá nến điều chỉnh (`adj_close`), phân tích nguyên nhân gốc rễ của từng ngoại lai.
- **Academic Classification Discipline**: Phân định rạch ròi 5 danh mục học thuật:
  1. `CORRECTED_REVERSE_SPLIT` (Đã xử lý ở tầng Corporate Actions: CHK, CRC, ADCT, AA, DYN)
  2. `SPECIAL_CORPORATE_SPINOFF` (Đã cách ly gián đoạn: KSU, SSP, COMS, PENN)
  3. `CORRECTED_QUALITY_FLAG` (Đã cách ly nến lỗi/ticker collision: MKL, SABR, LOW, CPTH)
  4. `VERIFIED_HISTORICAL_CRASH` (Biến cố thị trường thật có hồ sơ SEC/FDIC: LEH, WCOME, WM, FNM, FRE, ENE, BSC, WB, MFA)
  5. `UNVERIFIED_PRICE_SHOCK` (Chưa có hồ sơ kiểm chứng độc lập, tuân thủ nguyên tắc không phỏng đoán, giữ nguyên và chế ngự bằng uniform rank).

**Dependencies:**
- Libraries: `pandas`, `numpy`, `pyarrow`, `pathlib.Path`, `time`, `sys`, `os`
- Scripts upstream: Script 07 (`matrices`), Script 06 (`corrections CSV`).

**Potential Issues:**
- ⚠️ Dòng 27 hardcode đường dẫn tuyệt đối `BASE_DIR = Path("D:/A_Learning/...")`.
- Thư viện `os` và `json` được import nhưng không dùng.

**Trạng thái:** ⚠️ Cần chú ý (Hardcoded absolute path).

---

## 3. Kiểm Tra Chéo Hệ Thống (Cross-Script Systemic Checks)

### 3.1. Tính Tương Thích Schema Giữa Các Bước (Schema Contract Alignment)

Đã đối soát chi tiết schema đầu ra của Script $N$ với schema đầu vào của Script $N+1$ trên toàn bộ chuỗi pipeline:

```
[Script 03 Output]
russell1000_constituents_daily_ohlcv_1998_2026.parquet
Schema: date (datetime64), original_ticker (str), qc_ticker (str), sid (str), 
        open (f64), high (f64), low (f64), close (f64), volume (f64)
  │
  ├──► [ĐÃ THỐNG NHẤT]:
  │    - Script 03 ghi ra: data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet
  │    - Script 04 đọc từ: data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet
  │    (Đường dẫn và tên tệp đã được chuẩn hóa đồng bộ 100%).
  │
  ▼
[Script 04 Output]
russell1000_constituents_daily_ohlcv_canonical_1998_2026.parquet
Schema: date (datetime64), canonical_sid (str), original_ticker (str), qc_ticker (str),
        open (f64), high (f64), low (f64), close (f64), volume (f64)
  │
  ├──► [KHỚP 100%]: Script 06 đọc chính xác các cột trên từ CANONICAL_PARQUET.
  │
  ▼
[Script 06 Output]
russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet (Tier 2 Warehouse)
Schema: 25 cột hoàn chỉnh:
  - Khóa: date (datetime64[us]), canonical_sid (str), original_ticker (str), qc_ticker (str)
  - Giá thô: open, high, low, close, volume (f64)
  - Điều chỉnh: cumulative_split_factor, adj_open, adj_high, adj_low, adj_close, adj_volume (f64)
  - Cổ tức: dividend_amount, adj_dividend (f64)
  - Lợi suất: daily_return, total_return (f64)
  - Phiên & Lịch: trading_session_gap, calendar_day_gap (f64), is_consecutive_session (bool)
  - Quality Flags: is_bad_data_period (bool), is_spinoff_discontinuity (bool), quality_flag (str)
  │
  ├──► [KHỚP 100%]: Script 07 đọc trực tiếp 17 cột giá trị và pivot thành 17 ma trận 2D.
  │
  ▼
[Script 07 Output]
17 Ma trận 2D Parquet (7,252 dates x 3,711 canonical SIDs) + 3 PIT Masks + 2 Target Matrices
  │
  ├──► [KHỚP 100%]: Script 08, Script 09, Script 10 đều nạp chính xác các ma trận này.
```

### 3.2. Rà Soát Đường Dẫn Tuyệt Đối (Hardcoded Absolute Paths)

Phát hiện **8 trên 13 script** đang sử dụng đường dẫn tuyệt đối dạng hardcoded tới ổ cứng `D:\A_Learning\...`:
- `04_audit_identity_and_build_canonical_mapping.py` (Line 28)
- `04b_generate_comprehensive_step3_audits.py` (Line 32)
- `05_rigorous_pit_membership_reconstruction.py` (Line 36)
- `06_process_corporate_actions_and_adjusted_prices.py` (Line 26)
- `07_build_2d_matrices_and_masks.py` (Line 38)
- `08_validate_matrices_and_sanity_checks.py` (Line 31)
- `09_run_development_eda.py` (Line 34)
- `10_investigate_extreme_returns.py` (Line 27)

**Mức độ nghiêm trọng**: ⚠️ **Cao đối với tính di động (Portability)**.  
Nếu dự án được clone sang một thư mục khác (như `D:\Learning\...` hoặc máy Linux/macOS/Docker container), cả 8 script trên sẽ đồng loạt vấp lỗi `FileNotFoundError`.  
**Khuyến nghị giải pháp**: Chuẩn hóa toàn bộ về mô hình định vị tương đối như Script 03 đã thực hiện xuất sắc:
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
```

### 3.3. Rà Soát Unused Imports và Dead Code

- **Imports dư thừa**:
  - `04_audit_identity_and_build_canonical_mapping.py`: `numpy` không dùng trực tiếp.
  - `04b_generate_comprehensive_step3_audits.py`: `os` không dùng.
  - `05_rigorous_pit_membership_reconstruction.py`: `os` và `numpy` không dùng.
  - `06_process_corporate_actions_and_adjusted_prices.py`: `os` không dùng.
  - `07_build_2d_matrices_and_masks.py`: `os` không dùng.
  - `08_validate_matrices_and_sanity_checks.py`: `os`, `json` không dùng.
  - `09_run_development_eda.py`: `os` không dùng.
  - `10_investigate_extreme_returns.py`: `os`, `json` không dùng.
- **Đoạn mã trùng lặp (Dead Code / Duplication)**:
  - `05_quantconnect_export_corporate_actions.py`: Dòng 275–280 có 2 câu lệnh `if (i // CHUNK_SIZE + 1) % 5 == 0 ... print(...)` bị copy lặp lại 2 lần liên tiếp.

### 3.4. Thẩm Định Tuyệt Đối Không Rò Rỉ Dữ Liệu OOS (Zero OOS Leakage Verification)

Đây là tiêu chí kiểm định quan trọng bậc nhất của hệ thống định lượng (Quantitative Rigor). Đã kiểm chứng chi tiết các cơ chế cô lập thời gian:

1. **Ranh giới Development được bảo vệ tuyệt đối**:
   - Trong `09_run_development_eda.py`: Khai báo cứng `DEV_START = 2000-07-01` và `DEV_END = 2023-12-29`. Toàn bộ dữ liệu tính toán moments, phân vị, dispersion, liquidity deciles đều được cắt lát bởi `unique_dates[(unique_dates >= DEV_START) & (unique_dates <= DEV_END)]`. Giai đoạn OOS 2024–2026 hoàn toàn không bị chạm vào.
   - Trong `10_investigate_extreme_returns.py`: Outlier filtering strictly áp dụng `index[(index >= "2000-07-01") & (index <= "2023-12-29")]`.
2. **Cơ chế Purge ranh giới chống rò rỉ nhãn (Anti-Lookahead Purge)**:
   - Trong `07_build_2d_matrices_and_masks.py`:
     ```python
     purge_dates = [unique_dates[-1], pd.Timestamp("2023-12-29")]
     purge_mask_1d = np.isin(unique_dates, purge_dates)
     not_purged = (~purge_mask_1d)[:, None]
     valid_label_arr = (valid_data_arr & ... & not_purged)
     ```
   - Tại ngày `2023-12-29` (phiên cuối của Development), nhãn tương lai T+1 rơi vào ngày `2024-01-02` (phiên đầu của OOS). Bằng cách ép `not_purged = False`, toàn bộ nhãn tương lai tại `2023-12-29` đều bị biến thành `NaN`.
   - Trong `08_validate_matrices_and_sanity_checks.py`: Kiểm thử `assert boundary_valid_labels == 0` tại ngày 2023-12-29 đã được xác minh thành công 100%.
3. **Kết luận về rò rỉ**:  
   ✅ **100% AIRTIGHT (Kín khít tuyệt đối)**. Không có bất kỳ hiện tượng rò rỉ thông tin nào từ giai đoạn 2024–2026 vào giai đoạn phát triển và huấn luyện mô hình.

### 3.5. Bất Cập Về Thứ Tự Thực Thi File (Pipeline Ordering Anomaly)

- Các file `04b_generate_comprehensive_step3_audits.py` và `05_rigorous_pit_membership_reconstruction.py` mang tiền tố tên gọi của Bước 2 / Bước 3, nhưng bên trong lại nạp file `russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet` (vốn chỉ được tạo ra sau khi Script `06_process_corporate_actions_and_adjusted_prices.py` chạy xong).
- Nếu người vận hành chạy tuần tự theo thứ tự chữ cái/số thứ tự file (`01 -> 02 -> 03 -> 04 -> 04b -> 05 -> 06`), script `04b` và `05_rigorous` sẽ lập tức báo lỗi do thiếu file đầu vào từ bước 06.
- **Khuyến nghị**: Đổi tên các script audit chuyên biệt này để thể hiện rõ chúng thuộc tầng hậu kiểm toán của Bước 3B/Bước 4 (ví dụ: `06b_audit_step3_comprehensive.py`).

---

## 4. Đề Xuất Cải Tiến Kỹ Thuật (Recommendations for Phase 2)

1. **Refactor Đường Dẫn Tương Đối Toàn Diện**:
   Thay thế toàn bộ các khai báo `BASE_DIR = Path("D:/A_Learning/...")` bằng:
   ```python
   BASE_DIR = Path(__file__).resolve().parents[2]
   ```
2. **Đồng Bộ Schema Naming Giữa Script 03 và Script 04**:
   Chuẩn hóa đường dẫn output của Script 03 và input của Script 04 cùng trỏ về:
   `data/processed/constituents_market_data/russell1000_constituents_daily_ohlcv_1998_2026.parquet`.
3. **Dọn Dẹp Unused Imports & Dead Code**:
   Xóa bỏ các imports thừa (`os`, `json`, `numpy`) và xóa khối lệnh print bị duplicate ở dòng 275–280 của `05_quantconnect_export_corporate_actions.py`.
4. **Tách Biệt Mã Chạy Cloud và Local CLI**:
   Các script 02, 02_export, 05_export là công cụ nạp dữ liệu chạy trên đám mây QuantConnect Research Notebook. Nên gắn cờ hoặc đặt vào thư mục riêng `scripts/00_ingestion_qc/` để phân biệt rõ ràng với pipeline xử lý tự động local (scripts 03 đến 10).

---

## 5. Kết Luận Đánh Giá (Final Sign-Off)

Toàn bộ 13 script hoạt động trong `scripts/01_pipeline/` đã được đọc thực tế, phân tích từng dòng mã và đối soát với kho dữ liệu Parquet cùng bảng kiểm toán thực tế trên đĩa:
- **Độ tin cậy toán học & định lượng**: **RẤT CAO**. Các thuật toán nén `searchsorted`, khử trùng bit-for-bit, cô lập Ticker Reuse, kiểm thử đẳng thức số học sai số < 1e-12 và cấu trúc 3 lớp mask PIT đều được triển khai xuất sắc, đạt chuẩn Institutional Quant Grade.
- **Tính toàn vẹn Out-of-Sample**: **HOÀN HẢO (100% Kín)**. Ranh giới 2023-12-29 được purge nhãn triệt để, ngăn chặn hoàn toàn hiện tượng Look-ahead Bias.
- **Các điểm cần lưu ý trước khi triển khai sản xuất**: Sửa đổi các đường dẫn hardcoded thành đường dẫn tương đối và đồng bộ thứ tự thực thi của các script audit `04b` và `05_rigorous`.

**Đánh giá tổng kết**: Đạt yêu cầu nghiệm thu Mục R2 của Milestone M2.
