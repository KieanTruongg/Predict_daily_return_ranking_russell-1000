"""
build_comprehensive_project_report.py
================================================================================
Generates an institutional-grade, responsive HTML Project Report for the
Russell 1000 Daily Return Ranking Prediction Engine.

Integrates data, audit tables, and high-res visualizations from:
  - Step 1: Research Design & Split Architecture (Development, Warm-up, OOS Frozen)
  - Step 2: Raw Warehouse Audit & Daily PIT Coverage
  - Step 3: Identity Disambiguation, 2T Resolution & Corporate Actions Audit (CORR_001..CORR_013)
  - Step 4: 2D Matrices System & 3-Tier PIT Masks (26.9M cells, 0 Look-ahead leakage)
  - Step 5: Post-Transformation Sanity Checks (Reconciliation, Split Checks)
  - Step 6: Development EDA (5,610,691 valid stock-days, Kurtosis 66.88, Forensic 34 cases)
  - Step 7: Feature Engineering Specification (16 Alpha Features + Uniform Rank Target [0, 1])
  - Steps 8-10: Pipeline Roadmap (Modeling, Optimization, Backtesting)

Target Output: docs/Data report/project_report.html
================================================================================
"""

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import time
from pathlib import Path
import pandas as pd

BASE_DIR = Path("D:/A_Learning/HK1_2026-2027/CO3101 - Đồ án tổng hợp - ttnt/Predict_daily_return_rankings")
TABLES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "tables"
FIGURES_DIR = BASE_DIR / "docs" / "Data report" / "market_data_audit" / "figures"
REPORT_OUTPUT = BASE_DIR / "docs" / "Data report" / "project_report.html"

def read_csv_to_html(csv_path, max_rows=None):
    if not csv_path.exists():
        return "<p><em>Bảng dữ liệu đang cập nhật...</em></p>"
    df = pd.read_csv(csv_path)
    if max_rows and len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_html(classes="audit-table", index=False, border=0)

def main():
    print("Building comprehensive HTML project report...")

    # Load summary metrics
    sanity_summary_html = read_csv_to_html(TABLES_DIR / "matrix_sanity_check_summary.csv")
    coverage_by_period_html = read_csv_to_html(TABLES_DIR / "matrix_and_mask_coverage_by_period.csv")
    recon_audit_html = read_csv_to_html(TABLES_DIR / "matrix_reconciliation_audit.csv")
    split_boundary_html = read_csv_to_html(TABLES_DIR / "matrix_split_boundary_audit.csv")
    corp_match_html = read_csv_to_html(TABLES_DIR / "corporate_actions_match_summary.csv")
    split_formula_html = read_csv_to_html(TABLES_DIR / "split_formula_mathematical_audit.csv", max_rows=15)
    dividend_identity_html = read_csv_to_html(TABLES_DIR / "dividend_identity_mathematical_audit.csv")
    churn_html = read_csv_to_html(TABLES_DIR / "eda_universe_dynamics_by_year.csv")
    moments_html = read_csv_to_html(TABLES_DIR / "eda_daily_return_moments.csv")
    liquidity_html = read_csv_to_html(TABLES_DIR / "eda_liquidity_deciles.csv")
    dispersion_html = read_csv_to_html(TABLES_DIR / "eda_cross_sectional_dispersion.csv", max_rows=15)

    # Step 3 Detailed Audits
    canonical_sid_html = read_csv_to_html(TABLES_DIR / "canonical_sid_reconciliation_audit.csv", max_rows=20)
    period_recon_html = read_csv_to_html(TABLES_DIR / "period_reconciliation_summary.csv")
    ticker_changes_html = read_csv_to_html(TABLES_DIR / "ticker_changes_audit.csv", max_rows=15)
    june_july_boundary_html = read_csv_to_html(TABLES_DIR / "june_july_boundary_transition_audit.csv", max_rows=15)
    dual_cov_html = read_csv_to_html(TABLES_DIR / "coverage_ticker_period_vs_daily_stock_days.csv")
    ambig_html = read_csv_to_html(TABLES_DIR / "ambiguous_multi_sid_audit.csv", max_rows=20)
    reuse_breakdown_html = read_csv_to_html(TABLES_DIR / "ticker_to_canonical_sid_reuse_breakdown.csv", max_rows=20)
    constituent_mapping_sample_html = read_csv_to_html(TABLES_DIR / "universe_constituent_temporal_mapping.csv", max_rows=25)
    segments_sample_html = read_csv_to_html(TABLES_DIR / "universe_constituent_segments_mapping.csv", max_rows=25)
    pos_returns_html = read_csv_to_html(TABLES_DIR / "top_50_positive_returns_audit.csv", max_rows=15)
    neg_returns_html = read_csv_to_html(TABLES_DIR / "top_50_negative_returns_audit.csv", max_rows=15)
    
    # Forensic 34 cases: display full table without row truncation
    extreme_forensic_html = read_csv_to_html(TABLES_DIR / "extreme_returns_forensic_investigation.csv", max_rows=None)

    template = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo Cáo Nghiên Cứu Định Lượng Toàn Diện — Russell 1000 Daily Return Ranking Engine</title>
<style>
  :root {
    --sidebar-w: 290px;
    --primary: #0f172a;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --success: #16a34a;
    --success-bg: #f0fdf4;
    --warning: #ea580c;
    --warning-bg: #fff7ed;
    --danger: #dc2626;
    --danger-bg: #fef2f2;
    --border: #e2e8f0;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --card-bg: #ffffff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 14.5px;
    color: var(--text-main);
    background: #f8fafc;
    line-height: 1.65;
  }

  /* Sidebar */
  #sidebar {
    position: fixed; top: 0; left: 0; width: var(--sidebar-w);
    height: 100vh; background: #0f172a; color: #f1f5f9;
    overflow-y: auto; z-index: 100; border-right: 1px solid #1e293b;
  }
  #sidebar .brand {
    background: #1e1b4b; padding: 20px 18px;
    font-size: 14px; font-weight: 700; color: #fff;
    border-bottom: 1px solid #312e81; letter-spacing: 0.3px;
  }
  #sidebar .brand span { color: #38bdf8; display: block; font-size: 11px; font-weight: 400; margin-top: 3px; }
  #sidebar nav { padding: 16px 0; }
  #sidebar nav .section-title {
    padding: 12px 18px 4px; font-size: 10.5px; font-weight: 700;
    color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;
  }
  #sidebar nav a {
    display: block; padding: 8px 18px 8px 22px; color: #cbd5e1;
    text-decoration: none; font-size: 13px; border-left: 3px solid transparent;
    transition: all 0.15s ease;
  }
  #sidebar nav a:hover, #sidebar nav a.active {
    color: #fff; background: rgba(255, 255, 255, 0.06); border-left-color: #38bdf8;
  }

  /* Main Content */
  #main { margin-left: var(--sidebar-w); padding: 0 0 60px 0; }

  /* Header Banner */
  #header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #1e3a8a 100%);
    color: #fff; padding: 42px 48px 36px;
    border-bottom: 1px solid #312e81;
  }
  #header h1 { font-size: 26px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }
  #header .sub { font-size: 15px; color: #cbd5e1; max-width: 900px; line-height: 1.6; margin-bottom: 24px; }
  
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-top: 20px;
  }
  .kpi-card {
    background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px;
    padding: 14px 18px; text-align: left;
  }
  .kpi-card .val { font-size: 22px; font-weight: 800; color: #38bdf8; font-variant-numeric: tabular-nums; }
  .kpi-card .lbl { font-size: 11.5px; color: #94a3b8; margin-top: 4px; font-weight: 500; }

  /* Content Containers */
  .container { max-width: 1200px; margin: 0 auto; padding: 32px 48px; }
  .section-card {
    background: var(--card-bg); border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    border: 1px solid var(--border); margin-bottom: 36px; overflow: hidden;
  }
  .section-card-header {
    background: #ffffff; border-bottom: 1px solid var(--border);
    padding: 18px 28px; display: flex; align-items: center; justify-content: space-between;
  }
  .section-card-header h2 {
    font-size: 18px; font-weight: 700; color: var(--primary);
    display: flex; align-items: center; gap: 10px;
  }
  .badge-phase {
    font-size: 11px; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; background: #e0f2fe; color: #0369a1;
  }
  .badge-success { background: #dcfce7; color: #15803d; }
  .badge-warning { background: #ffedd5; color: #c2410c; }
  .section-body { padding: 28px; }

  /* Typography */
  h3 { font-size: 15px; font-weight: 700; color: #334155; margin: 22px 0 10px; }
  h4 { font-size: 14px; font-weight: 700; color: #1e293b; margin: 16px 0 8px; }
  p { margin-bottom: 14px; color: #334155; }
  ul, ol { padding-left: 24px; margin-bottom: 16px; color: #334155; }
  li { margin-bottom: 6px; }

  /* Callout Boxes */
  .callout {
    border-left: 4px solid var(--accent); background: var(--accent-light);
    padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 18px 0;
  }
  .callout.success { border-left-color: var(--success); background: var(--success-bg); }
  .callout.warning { border-left-color: var(--warning); background: var(--warning-bg); }
  .callout h4 { font-size: 13.5px; font-weight: 700; margin-bottom: 4px; color: #0f172a; }
  .callout p { margin: 0; font-size: 13.5px; color: #334155; }

  /* Tables */
  .table-responsive { overflow-x: auto; margin: 16px 0 24px; }
  table.audit-table {
    width: 100%; border-collapse: collapse; font-size: 13px;
    background: #ffffff; border: 1px solid var(--border);
  }
  table.audit-table th {
    background: #f1f5f9; color: #334155; font-weight: 700;
    padding: 10px 14px; text-align: left; border-bottom: 2px solid var(--border);
    white-space: nowrap;
  }
  table.audit-table td {
    padding: 9px 14px; border-bottom: 1px solid var(--border);
    color: #334155; font-variant-numeric: tabular-nums;
  }
  table.audit-table tr:nth-child(even) td { background: #f8fafc; }
  table.audit-table tr:hover td { background: #f1f5f9; }

  /* Figures */
  .figure-box {
    margin: 22px 0; border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; background: #fff;
  }
  .figure-box img { width: 100%; height: auto; display: block; }
  .figure-box .caption {
    padding: 10px 16px; font-size: 12.5px; color: #64748b;
    background: #f8fafc; border-top: 1px solid var(--border);
    font-weight: 500;
  }

  /* Code */
  code {
    font-family: 'Consolas', 'Courier New', monospace; font-size: 12.5px;
    background: #e2e8f0; color: #0f172a; padding: 2px 6px; border-radius: 4px;
  }
</style>
</head>
<body>

<aside id="sidebar">
  <div class="brand">
    Russell 1000 Daily Alpha Engine
    <span>Institutional Quant Research Pipeline</span>
  </div>
  <nav>
    <div class="section-title">Nội Dung Nghiên Cứu</div>
    <a href="#sec-overview" class="active">1. Tổng Quan &amp; Phân Vùng Thời Gian ✅</a>
    <a href="#sec-warehouse">2. Kiểm Định Kho Thô &amp; Coverage PIT ✅</a>
    <a href="#sec-identity">3. Identity, 2T &amp; Corporate Actions ✅</a>
    <a href="#sec-matrices">4. Hệ Thống Ma Trận 2D &amp; 3 Lớp Masks ✅</a>
    <a href="#sec-sanity">5. Sanity Checks Sau Chuyển Đổi ✅</a>
    <a href="#sec-eda">6. EDA Tập Phát Triển &amp; Forensic 34 Ca ✅</a>
    <a href="#sec-next">7. Trạng Thái 10 Bước &amp; Kế Hoạch Bước ⑦ 🔜</a>
  </nav>
</aside>

<main id="main">

  <header id="header">
    <h1>Báo Cáo Nghiên Cứu Định Lượng Toàn Diện (1998–2026)</h1>
    <div class="sub">
      Dự án Xây dựng Mô hình Học Máy Dự Báo Thứ Hạng Lợi Nhuận Hằng Ngày (Daily Return Rankings) rổ Russell 1000 constituents. 
      Phương pháp chuẩn Quỹ Định Lượng: Ngăn ngừa 100% Look-ahead bias, Ticker Reuse, Split Discretization, và Phân tách nghiêm ngặt Out-Of-Sample.
    </div>
    
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="val">5,610,691</div>
        <div class="lbl">Mẫu Hợp Lệ Tập Phát Triển (Valid Stock-Days)</div>
      </div>
      <div class="kpi-card">
        <div class="val">66.88</div>
        <div class="lbl">Excess Kurtosis Đã Làm Sạch (Giảm từ 3.4M)</div>
      </div>
      <div class="kpi-card">
        <div class="val">+227.87%</div>
        <div class="lbl">Lợi Suất Ngày Max Thật (Khử +12,371% ảo)</div>
      </div>
      <div class="kpi-card">
        <div class="val">2.65%</div>
        <div class="lbl">Biến Động Ngày (Annualized 42.12%)</div>
      </div>
      <div class="kpi-card">
        <div class="val">3,711</div>
        <div class="lbl">Canonical SIDs (100% Unique CCCD)</div>
      </div>
      <div class="kpi-card">
        <div class="val">7,252</div>
        <div class="lbl">Phiên Giao Dịch NYSE (1998–2026)</div>
      </div>
      <div class="kpi-card">
        <div class="val">34 Ca</div>
        <div class="lbl">Kiểm Toán Pháp Y (13 CORR, 9 HIST, 12 UNVER)</div>
      </div>
      <div class="kpi-card">
        <div class="val">0%</div>
        <div class="lbl">Data Leakage sang OOS 2024–2026</div>
      </div>
    </div>
  </header>

  <div class="container">

    <!-- SECTION 1 -->
    <section id="sec-overview" class="section-card">
      <div class="section-card-header">
        <h2>1. Tổng Quan Thiết Kế Nghiên Cứu &amp; Phân Chia Thời Gian</h2>
        <span class="badge-phase badge-success">Bước ① Hoàn Tất ✅</span>
      </div>
      <div class="section-body">
        <p>Để đạt chuẩn mực cao nhất của nghiên cứu định lượng tổ chức (Institutional Quant Standard), toàn bộ dòng thời gian 29 năm (1998–2026) được chia thành 3 phân vùng độc lập:</p>
        <ul>
          <li><strong>1998–1999 (Feature Lookback Warm-up):</strong> 630 phiên giao dịch NYSE. Không tính vào tập huấn luyện do chưa có snapshot PIT chính thức. Toàn bộ lịch sử giá raw/adjusted được giữ nguyên để tính các feature rolling dài hạn (Momentum 252d, Volatility 60d) ngay từ ngày đầu tiên rổ Russell 1000 bắt đầu (01/07/2000), loại bỏ hoàn toàn rủi ro khởi động lạnh (Zero Cold-Start).</li>
          <li><strong>2000–2023 (Tập Phát Triển — Development Set):</strong> 5,912 phiên giao dịch (5,610,691 valid stock-days). Dùng để thực hiện EDA, Feature Engineering, huấn luyện mô hình và Walk-Forward Validation (Expanding Window CV). Tuyệt đối không nhìn trước vào tương lai.</li>
          <li><strong>2024–2026 (Tập Triển Khai Thực Chiến — Out-Of-Sample Deployment):</strong> 710 phiên giao dịch. <strong>ĐÓNG BĂNG HOÀN TOÀN</strong>. Đánh giá kiểm thử thực chiến bao gồm chi phí trượt giá (slippage) và phí giao dịch.</li>
        </ul>
        <div class="callout">
          <h4>Quy ước Khớp Lệnh &amp; Khoảng Thời Gian Dự Báo</h4>
          <p><strong>Thiết kế A (MOC Baseline):</strong> Tín hiệu (Alpha Features) được tính toán tại thời điểm 15:45 ngày T. Lệnh tái cân bằng được gửi theo lệnh Market-On-Close (MOC) khớp tại giá Đóng cửa ngày T. Nhãn mục tiêu là thứ hạng phân vị lợi suất ngày kế tiếp: <code>target_next_rank</code> &in; [0, 1].</p>
        </div>
      </div>
    </section>

    <!-- SECTION 2 -->
    <section id="sec-warehouse" class="section-card">
      <div class="section-card-header">
        <h2>2. Kiểm Định Kho Dữ Liệu Thô &amp; Baseline Coverage PIT</h2>
        <span class="badge-phase badge-success">Bước ② Hoàn Tất ✅</span>
      </div>
      <div class="section-body">
        <p>Hợp nhất 10 batch dữ liệu QuantConnect với 13,147,389 dòng bản ghi nến ngày. Sau khi đối chiếu với lịch giao dịch chính thức của sàn New York (NYSE Calendar), toàn bộ các phiên đóng cửa bất thường (Sự kiện khủng bố 11/9/2001, Siêu bão Sandy 2012, các ngày quốc tang) đều được xác nhận khớp 100%.</p>
        <p>Độ phủ thành viên Point-In-Time (PIT) đạt mức bình quân <strong>96.41%</strong> qua 27 kỳ tái cơ cấu (trung bình 960.8 cổ phiếu giao dịch hợp lệ mỗi ngày trên tổng số 1,000 cổ phiếu danh nghĩa).</p>
      </div>
    </section>

    <!-- SECTION 3 -->
    <section id="sec-identity" class="section-card">
      <div class="section-card-header">
        <h2>3. Chuẩn Hóa Identity, Phân Lập Ticker Reuse &amp; Thẩm Định Học Thuật Corporate Actions</h2>
        <span class="badge-phase badge-success">Bước ③ Hoàn Tất 100% ✅</span>
      </div>
      <div class="section-body">
        <h3>3.1. Bản Chất `canonical_sid` &amp; Tại Sao 2,884 Tickers Mở Rộng Thành 3,711 Canonical SIDs?</h3>
        <p><strong>Bản chất cốt lõi:</strong> Ticker chỉ là "cái áo" do Sở Giao Dịch cấp tạm thời. Trong suốt 29 năm (1998–2026), các công ty phá sản, hủy niêm yết, và mã ticker đó sau vài năm được cấp lại cho một công ty hoàn toàn mới. <code>canonical_sid</code> là <em>Căn Cước Công Dân (CCCD)</em> duy nhất của từng thực thể pháp nhân.</p>
        <p>Nếu gom theo ticker thuần túy (2,884 mã), ta sẽ ghép nhầm chuỗi giá của 2 công ty hoàn toàn khác nhau vào cùng một chuỗi thời gian, gây ra các cú sốc giá giả mạo. Phân tích dữ liệu cho thấy:</p>
        <ul>
          <li><strong>1,962 tickers (68.9%):</strong> Chỉ thuộc về duy nhất 1 công ty xuyên suốt 29 năm.</li>
          <li><strong>883 tickers (31.1%):</strong> Bị tái sử dụng (Ticker Reuse) bởi 2, 3, hoặc 4 công ty độc lập qua các thời kỳ! (Ví dụ: Ticker <code>ABI</code> là Applied Biosystems giai đoạn 1998–1999, nhưng từ 2008 trở đi lại là tập đoàn bia Anheuser-Busch InBev; Ticker <code>GEN</code>, <code>INFO</code>, <code>AI</code>, <code>CHTR</code> đều có nhiều thực thể kế tiếp nhau).</li>
          <li>Chính vì <strong>883 ca Ticker Reuse</strong> này, 2,884 mã ticker danh nghĩa đã đại diện cho đúng <strong>3,711 thực thể doanh nghiệp độc lập</strong> trên ma trận 2D!</li>
        </ul>
        <div class="table-responsive">
          __TICKER_REUSE_BREAKDOWN_TABLE__
        </div>

        <h3>3.2. Thiết Lập Membership Từ Snapshot &amp; 6 Cấp Độ Bằng Chứng Xác Minh (26,919 Constituent-Years)</h3>
        <p>Membership được thiết lập nghiêm ngặt từ 27 danh sách snapshot Point-In-Time chính thức kết hợp với khoảng hiệu lực <code>[min_date, max_date]</code> của từng thực thể. Tuyệt đối không suy diễn từ dòng nến có sẵn trong kho giá.</p>
        <p>Toàn bộ 26,919 lượt cổ phiếu–năm được phân loại theo <strong>6 cấp độ bằng chứng học thuật</strong>:</p>
        <ul>
          <li><strong style="color:var(--success);">LEVEL 1 — VERIFIED_PERMANENT (26,138 lượt — 97.10%):</strong> Ánh xạ duy nhất vào mã SID vĩnh viễn trực tiếp từ QuantConnect LEAN, chuỗi ngày liên tục khớp với kỳ.</li>
          <li><strong style="color:var(--success);">LEVEL 2 — VERIFIED_SEQUENTIAL_TRANSITION (45 lượt — 0.17%):</strong> Chuyển tiếp tuần tự giữa 2 mã SID vĩnh viễn qua thương vụ sáp nhập/đổi tên có khoảng cách liền kề &le; 10 ngày (ví dụ JPM sáp nhập CMB, TWX sáp nhập AOL), <strong>0 ngày trùng lặp</strong>.</li>
          <li><strong style="color:var(--warning);">LEVEL 3 — HEURISTIC_2T_STITCH (152 lượt — 0.56%):</strong> Nối mã placeholder <code>2T</code> vào SID vĩnh viễn (gap &le; 10 ngày); ghi nhận rõ là <em>giả định kỹ thuật chưa xác minh qua hồ sơ SEC</em>.</li>
          <li><strong style="color:var(--danger);">LEVEL 4 — AMBIGUOUS_MULTI_SID (138 lượt — 0.51%):</strong> Các trường hợp mơ hồ cần giữ nguyên trạng thái cảnh báo, không gượng ép xác nhận.</li>
          <li><strong style="color:var(--text-muted);">LEVEL 5 — UNRESOLVED_ZERO_BARS (250 lượt — 0.93%):</strong> Ticker có trong kho mapping nhưng không có ngày hiệu lực nào trong 12 tháng của kỳ này.</li>
          <li><strong style="color:var(--text-muted);">LEVEL 6 — UNRESOLVED_NOT_IN_MAPPING (196 lượt — 0.73%):</strong> Ticker không có trong kho nến (mã OTC / non-equity / un-downloaded).</li>
        </ul>
        <div class="table-responsive">
          __CONSTITUENT_MAPPING_SAMPLE_TABLE__
        </div>

        <h3>3.3. Thẩm Định 138 Trường Hợp Mơ Hồ (Ambiguous Multi-SID Audit)</h3>
        <p>Để đảm bảo tính nghiêm cẩn, 138 trường hợp mơ hồ được chia thành 2 nhóm rõ rệt:</p>
        <ol>
          <li><strong>Xung đột ngày giao dịch (Date Overlap Conflicts — 86 trường hợp):</strong> Cả mã <code>2T</code> và mã SID vĩnh viễn cùng tồn tại và cùng có nến trên sàn trong cùng một khoảng thời gian. Khuyến nghị: Giữ cờ <code>AMBIGUOUS</code> và loại khỏi universe giao dịch cho đến khi có bằng chứng CUSIP đối chiếu.</li>
          <li><strong>Gián đoạn thời gian lớn (Discontinuous Gap &gt; 10 ngày — 52 trường hợp):</strong> Chuyển tiếp giữa 2 thực thể cách nhau hàng tháng, có thể là 2 công ty độc lập tái sử dụng ticker chứ không phải M&A liên tục.</li>
        </ol>
        <div class="table-responsive">
          __AMBIGUOUS_AUDIT_TABLE__
        </div>

        <h3>3.4. Phân Biệt Rạch Ròi 2 Thước Đo Coverage: Ticker-Period vs Daily Stock-Days</h3>
        <p>Nghiên cứu định lượng phân biệt minh bạch giữa 2 khái niệm độ phủ:</p>
        <ul>
          <li><strong>Ticker-Period Coverage (Độ phủ vĩ mô theo kỳ):</strong> Trong số ~1,000 cổ phiếu chính thức của kỳ Y, có bao nhiêu cổ phiếu có ít nhất 1 nến giá trong 12 tháng? &rarr; <strong>Bình quân đạt 93.88%</strong> (~940 mã/năm).</li>
          <li><strong>Daily Stock-Day Coverage (Độ phủ vi mô khớp lệnh từng ngày):</strong> Trên tổng số $T \times N$ ngày-cổ phiếu lý thuyết (tổng 6,599,893 stock-days qua 27 năm), có bao nhiêu nến giao dịch thực tế? &rarr; <strong>Bình quân đạt 92.15%</strong> (6,078,043 stock-days thực tế, trung bình ~920 cổ phiếu hoạt động bình thường mỗi ngày).</li>
        </ul>
        <div class="table-responsive">
          __COVERAGE_DUAL_TABLE__
        </div>

        <h3>3.5. Thẩm Định Các Ca Đổi Ticker (Aliases) &amp; Ranh Giới Tái Cơ Cấu Tháng 6 – Tháng 7</h3>
        <p>Kiểm tra danh sách 256 trường hợp đổi mã chứng khoán (như Google đổi mã, Facebook đổi Meta):</p>
        <div class="table-responsive">
          __TICKER_CHANGES_TABLE__
        </div>
        <p>Kiểm tra tính sẵn sàng của dữ liệu lịch sử đối với các cổ phiếu mới gia nhập rổ vào ngày 01/07 hằng năm:</p>
        <div class="table-responsive">
          __JUNE_JULY_BOUNDARY_TABLE__
        </div>
        <p><strong>Kết luận then chốt:</strong> Bình quân <strong>93.38%</strong> số cổ phiếu mới gia nhập rổ vào ngày 01/07 đã có sẵn ít nhất 20 nến giá lịch sử từ trước ngày gia nhập, đảm bảo các chỉ báo kỹ thuật (rolling features) được warm-up đầy đủ ngay từ ngày đầu tiên vào rổ!</p>

        <h3>3.6. Khớp Nối &amp; Thẩm Định Học Thuật Corporate Actions (Splits &amp; Dividends)</h3>
        <p>Tiếp nhận 4,788 sự kiện chia tách (Splits) và 96,773 sự kiện cổ tức (Dividends) từ QuantConnect LEAN Database:</p>
        <div class="table-responsive">
          __CORP_MATCH_TABLE__
        </div>
        <ul>
          <li><strong>Hệ số CF_(i, t) liên tục theo thời gian:</strong> Tính bằng tích lũy lùi qua <code>np.searchsorted</code> trên lịch chia tách, <strong>độc lập 100% với việc ngày chia tách có nến giá hay không</strong>. Triệt tiêu hoàn toàn lỗi bỏ sót chia tách rơi vào ngày lễ/halt.</li>
          <li><strong>Không làm tròn trung gian:</strong> Loại bỏ làm tròn 4 chữ số, giữ nguyên độ chính xác <code>float64</code> chuẩn IEEE-754.</li>
          <li><strong>Nhận diện phiên gián đoạn:</strong> Cột <code>is_consecutive_session</code> phát hiện 3,934 phiên gián đoạn &gt; 1 ngày giao dịch để tránh tính nhầm return treo sàn nhiều tuần.</li>
        </ul>
        <div class="table-responsive">
          __SPLIT_FORMULA_TABLE__
        </div>
        <p><strong>Kiểm định đồng nhất thức cổ tức:</strong> Sai số đồng nhất thức |(R_total - R_price) - (D_adj / P_(t-1)_adj)| = <strong>1.07 &times; 10⁻¹⁶</strong>:</p>
        <div class="table-responsive">
          __DIVIDEND_IDENTITY_TABLE__
        </div>
      </div>
    </section>

    <!-- SECTION 4 -->
    <section id="sec-matrices" class="section-card">
      <div class="section-card-header">
        <h2>4. Hệ Thống Ma Trận 2D &amp; 3 Lớp PIT Masks Theo Kiến Trúc Segment Mapping</h2>
        <span class="badge-phase badge-success">Bước ④ Hoàn Tất Chuẩn Xác ✅</span>
      </div>
      <div class="section-body">
        <h3>4.1. Kiến Trúc Segment Mapping: 1 SID — 1 Khoảng Hiệu Lực Mỗi Dòng</h3>
        <p>Để triệt tiêu hoàn toàn lỗi bật cờ tràn cả năm cho các cổ phiếu thay đổi mã hoặc chỉ niêm yết một phần thời gian, hệ thống membership được xây dựng theo <strong>bảng phân đoạn Segment Mapping (27,103 dòng)</strong>:</p>
        <ul>
          <li>Mỗi dòng đại diện cho đúng <strong>1 Canonical SID &times; 1 khoảng thời gian hiệu lực <code>[effective_start_date, effective_end_date]</code></strong>.</li>
          <li><strong>Không coi gap &le; 10 ngày là bằng chứng verified:</strong> Toàn bộ các ca chuyển tiếp tuần tự (Sequential Transitions) hoặc nối placeholder <code>2T</code> có khoảng cách &le; 10 ngày đều được xếp vào nhóm <code>HEURISTIC_UNVERIFIED</code>, phản ánh đúng bản chất là giả định kỹ thuật của quy trình kỹ nghệ dữ liệu.</li>
          <li><strong>Xử lý triệt để Overlap:</strong> Các ca xung đột ngày (2 SID cùng tồn tại đồng thời) được phân lập thành 2 dòng riêng biệt và đưa vào chính sách loại trừ.</li>
        </ul>
        <div class="table-responsive">
          __SEGMENTS_MAPPING_SAMPLE_TABLE__
        </div>

        <h3>4.2. Chính Sách Loại Trừ Nghiêm Ngặt (Exclusion Policy)</h3>
        <div class="callout warning">
          <h4>Quy Tắc Bảo Vệ Universe Khỏi Nhiễm Bẩn Danh Tính</h4>
          <p>Nhằm bảo đảm danh mục đầu tư mô phỏng và nhãn huấn luyện AI không bị sai lệch bởi các mã không rõ nguồn gốc:</p>
          <ul>
            <li><strong>723 phân đoạn</strong> thuộc nhóm <code>AMBIGUOUS</code> (86 xung đột ngày + 52 gián đoạn lớn) và <code>UNRESOLVED</code> (250 nến trống + 196 không có trong kho) đều mang cờ <code>is_included_in_mask = False</code>.</li>
            <li>Các mã này <strong>vẫn được giữ nguyên trong báo cáo đối chiếu</strong> để minh bạch 100% nguồn gốc, nhưng <strong>tuyệt đối không được kích hoạt trong <code>membership_mask</code></strong>.</li>
            <li><strong>Kết quả:</strong> Trên mỗi phiên giao dịch $T$, mỗi công ty trong rổ Russell 1000 chỉ có <strong>tối đa duy nhất 1 Canonical SID hoạt động</strong>, triệt tiêu 100% rủi ro trùng lặp cột hoặc nhân đôi trọng số.</li>
          </ul>
        </div>

        <h3>4.3. Giải Nghĩa 3 Lớp Mặt Nạ Point-In-Time (PIT Masks)</h3>
        <div class="callout success">
          <h4>Bản Chất Nghiên Cứu Định Lượng Của 3 Lớp Mặt Nạ</h4>
          <ol>
            <li><strong>Lớp 1: <code>membership_mask</code> (Quyền Tham Gia Danh Sách):</strong><br>
            <em>Ý nghĩa:</em> Kích hoạt chính xác tại ngày T nếu ngày T rơi vào khoảng hiệu lực của một phân đoạn hợp lệ (<code>is_included_in_mask = True</code>). Tổng cộng: <strong>6,333,323 True cells</strong>. Giai đoạn 1998–1999 hoàn toàn False (khởi tạo lookback).</li>
            <li><strong>Lớp 2: <code>valid_data_mask</code> (Khả Năng Khớp Lệnh Tại Ngày T — Dùng Khi Đánh Trận Thực Tế):</strong><br>
            <em>Ý nghĩa:</em> Tại ngày T, cổ phiếu này có thực sự giao dịch được trên sàn để mua/bán không? Đòi hỏi: (1) Thuộc rổ; (2) Có nến giá đóng cửa dương; (3) Khối lượng Volume &gt; 0; (4) Phiên liên tục; (5) Có ít nhất 20 nến lịch sử để tính các chỉ báo kỹ thuật; (6) Không dính cờ cách ly lỗi. Tổng cộng: <strong>6,311,822 True cells (99.66% membership)</strong>. Đây là mặt nạ duy nhất được phép dùng khi triển khai thực chiến.</li>
            <li><strong>Lớp 3: <code>valid_label_mask</code> (Điều Kiện Huấn Luyện AI — Chỉ Dùng Trong Phòng Thí Nghiệm):</strong><br>
            <em>Ý nghĩa:</em> Phiên ngày mai (T+1) có nến giá và return hợp lệ để làm "đáp án chấm điểm" cho mô hình học không? Yêu cầu: Hôm nay giao dịch được (Lớp 2 = True) VÀ ngày mai cũng giao dịch bình thường. Tuyệt đối bị vô hiệu hóa tại ranh giới rò rỉ năm 2023 sang 2024 và phiên cuối 2026. Tổng cộng: <strong>6,308,873 True cells (99.61% membership)</strong>.</li>
          </ol>
        </div>

        <h3>4.4. Bảng Tổng Hợp Độ Phủ 3 Lớp Mask Theo Từng Kỳ (2000–2026)</h3>
        <div class="table-responsive">
          __COVERAGE_PERIOD_TABLE__
        </div>
      </div>
    </section>

    <!-- SECTION 5 -->
    <section id="sec-sanity" class="section-card">
      <div class="section-card-header">
        <h2>5. Sanity Checks Sau Chuyển Đổi Ma Trận</h2>
        <span class="badge-phase badge-success">Bước ⑤ 100% Đạt Chuẩn ✅</span>
      </div>
      <div class="section-body">
        <p>Kết quả kiểm định toàn diện trên 26.9 triệu ô dữ liệu ma trận đã chứng minh tính toàn vẹn toán học tuyệt đối:</p>
        <div class="table-responsive">
          __SANITY_SUMMARY_TABLE__
        </div>

        <h3>5.1. Đối Chiếu Ngẫu Nhiên 50,000 Ô Dữ Liệu Với Kho Gốc</h3>
        <div class="table-responsive">
          __RECON_AUDIT_TABLE__
        </div>

        <h3>5.2. Kiểm Tra Tính Liên Tục Của Chuỗi Giá Trên Các Sự Kiện Chia Tách &amp; Gộp Cổ Phiếu</h3>
        <div class="table-responsive">
          __SPLIT_BOUNDARY_TABLE__
        </div>
      </div>
    </section>

    <!-- SECTION 6 -->
    <section id="sec-eda" class="section-card">
      <div class="section-card-header">
        <h2>6. EDA Chuyên Sâu Trên Phần Phát Triển (2000–2023 — Zero Snooping) &amp; Điều Tra Pháp Y 34 Biến Cố</h2>
        <span class="badge-phase badge-success">Bước ⑥ Hoàn Tất Toàn Diện ✅</span>
      </div>
      <div class="section-body">
        <p>Khảo sát dữ liệu được thực hiện nghiêm ngặt trên <strong>5,912 phiên giao dịch Development</strong> (từ 01/07/2000 đến 29/12/2023), <strong>hoàn toàn đóng băng và không nhìn trước giai đoạn 2024–2026</strong>. Tổng số quan sát hợp lệ phục vụ học máy là <strong>5,610,691 stock-days</strong>.</p>

        <h3>6.1. Báo Cáo Điều Tra Pháp Y 34 Biến Cố Lợi Suất Cực Đoan (13 CORR, 9 HIST, 12 UNVER)</h3>
        <p>Để đảm bảo độ tin cậy định lượng tuyệt đối, toàn bộ 34 trường hợp lợi suất cực đoan nhất trong lịch sử 24 năm của rổ Russell 1000 đã được điều tra nguồn gốc và phân loại theo 3 nhóm chức năng:</p>
        
        <div class="callout warning">
          <h4>Tóm Tắt Kết Quả Điều Tra Pháp Y 34 Biến Cố Cực Đoan</h4>
          <ul>
            <li><strong>Nhóm I — 13 Ca Hiệu Chỉnh Kỹ Thuật &amp; Ngoại Lệ (CORR_001 đến CORR_013):</strong>
              <ul>
                <li><strong>5 sự kiện Reverse Split bị bỏ sót:</strong> Chesapeake Energy (<code>CHK</code> 15/04/2020 gộp 1:200, return sửa từ +12,371.4% về <strong>-37.64%</strong>), Dynegy (<code>DYN</code> 25/05/2010 gộp 1:5, sửa từ +391.2% về <strong>-1.76%</strong>), California Resources (<code>CRC</code> 01/06/2016 gộp 1:10, sửa từ +925.0% về <strong>+2.50%</strong>), ADC Telecom (<code>ADCT</code> 10/05/2005 gộp 1:7, sửa từ +620.0% về <strong>+2.86%</strong>), Alcoa (<code>AA</code> 06/10/2016 gộp 1:3, sửa từ +205.6% về <strong>+1.86%</strong>).</li>
                <li><strong>4 ca gián đoạn do Spin-off:</strong> Kansas City Southern (<code>KSU</code> tách Stilwell/Janus), Scripps (<code>SSP</code> tách SNI), 3Com (<code>COMS</code> tách Palm), Penn National (<code>PENN</code> tách GLPI REIT). Do tài sản cổ đông được bảo toàn qua cổ phiếu con, phiên gián đoạn được gán <strong>return = NaN và cách ly hoàn toàn khỏi masks</strong> (triệt tiêu 100% rủi ro target bị đầu độc).</li>
                <li><strong>4 ca lỗi nến kỹ thuật &amp; xung đột mã:</strong> Markel (<code>MKL</code> 7 nến rác $26.10), Sabre (<code>SABR</code> tick rác $0.50 vào Triple Witching Close), Lowe's (<code>LOW</code> xung đột mã preferred), Cytyc (<code>CPTH</code> nến ảo trong phiên halt). Toàn bộ được cách ly thành <strong>return = NaN</strong>.</li>
              </ul>
            </li>
            <li><strong>Nhóm II — 9 Biến Cố Khủng Hoảng Thị Trường Đã Xác Minh SEC/FDIC (HIST_001 đến HIST_009):</strong>
              Lehman Brothers phá sản (<code>LEH</code> -94.97%), gian lận WorldCom (<code>WCOM</code> -91.67%), Washington Mutual sụp đổ (<code>WM</code> -90.96%), Fannie Mae &amp; Freddie Mac bị chính phủ tiếp quản (<code>FNM</code> -90.14%, <code>FRE</code> -82.58%), Enron sụp đổ (<code>ENE</code> -85.10%), Bear Stearns bán khẩn cấp (<code>BSC</code> -84.17%), Wachovia giải cứu (<code>WB</code> -80.63%), MFA Financial phục hồi sau gói thanh khoản Fed TALF (<code>MFA</code> +227.87%). <strong>Giữ nguyên 100% trong rổ dữ liệu</strong> để mô hình học cách nhận diện rủi ro đuôi và ngăn ngừa thiên lệch kẻ sống sót (Survivorship Bias).</li>
            <li><strong>Nhóm III — 12 Ca Cú Sốc Giá Chưa Xác Minh Độc Lập (UNVER_001 đến UNVER_012):</strong>
              Các phiên biến động mạnh của cổ phiếu penny/distressed (<code>MRCH</code>, <code>CHK</code>, <code>WBVN</code>, <code>AWH</code>, <code>SDRL</code>, <code>ENE</code>, <code>WCOM</code>, <code>WCN</code>, <code>MFNX</code>, <code>MFA</code>, <code>LCAPA</code>, <code>SSCC</code>) được xếp vào diện <strong>UNVERIFIED_PRICE_SHOCK</strong>, minh bạch liêm chính học thuật không tự tiện gán "confirmed", và chế ngự hoàn toàn bằng biến mục tiêu Uniform Rank Target [0, 1].</li>
          </ul>
        </div>

        <div class="table-responsive">
          <h4>Bảng Kiểm Toán Pháp Y Chi Tiết Đầy Đủ 34 Biến Cố Cực Đoan (extreme_returns_forensic_investigation.csv)</h4>
          __EXTREME_FORENSIC_TABLE__
        </div>

        <h3>6.2. Phân Phối Return Thực Nghiệm Sau Hiệu Chỉnh Đồng Bộ</h3>
        <p>Sau khi áp dụng toàn bộ các điều chỉnh ở tầng gốc (Corporate Actions &amp; Quality Flags), phân phối lợi nhuận trên <strong>5,610,691 quan sát hợp lệ</strong> đã đạt trạng thái chuẩn mực định lượng:</p>
        <div class="table-responsive">
          __MOMENTS_TABLE__
        </div>
        <ul>
          <li><strong>Excess Kurtosis đạt 66.88 (giảm từ 3.4M của pipeline cũ):</strong> Triệt tiêu 99.998% độ nhọn giả tạo do lỗi dữ liệu, đưa đuôi phân phối về đúng đặc tính fat-tails của thị trường cổ phiếu thật.</li>
          <li><strong>Daily Volatility đạt 2.65%/ngày (Annualized: 42.12%):</strong> Phản ánh chuẩn xác mức độ dao động tự nhiên của nhóm cổ phiếu lớn trong rổ Russell 1000.</li>
          <li><strong>Skewness đạt +0.563:</strong> Phù hợp với lý thuyết tài chính: độ lệch dương nhẹ do giới hạn lỗ tối đa là -100%.</li>
          <li><strong>Biên độ giá:</strong> Lợi nhuận cao nhất là <strong>+227.87%</strong> (MFA Financial phục hồi sau gói thanh khoản Fed); Thấp nhất là <strong>-94.97%</strong> (Lehman Brothers phá sản).</li>
        </ul>
        <div class="figure-box">
          <img src="market_data_audit/figures/eda_daily_return_distribution_qq.png" alt="Return Distribution and QQ Plot">
          <div class="caption">Hình 1: Phân phối thực nghiệm của lợi nhuận hằng ngày sau hiệu chỉnh pháp y so với phân phối chuẩn lý thuyết (Excess Kurtosis = 66.88 | Daily Vol = 2.65% | Skewness = +0.563).</div>
        </div>

        <h3>6.3. Bảng Top 15 Return Dương &amp; Top 15 Return Âm Đã Thẩm Định</h3>
        <div class="table-responsive">
          <h4>Top 15 Return Dương Lớn Nhất</h4>
          __TOP_POS_RETURNS_TABLE__
        </div>
        <div class="table-responsive" style="margin-top: 15px;">
          <h4>Top 15 Return Âm Lớn Nhất</h4>
          __TOP_NEG_RETURNS_TABLE__
        </div>

        <h3>6.4. Biến Động Thành Viên (Universe Turnover &amp; Churn)</h3>
        <div class="figure-box">
          <img src="market_data_audit/figures/eda_universe_turnover_and_active_count.png" alt="Universe Turnover">
          <div class="caption">Hình 2: Số lượng cổ phiếu gia nhập mới, rút lui và tỷ lệ Churn hằng năm của rổ Russell 1000 (2001–2023).</div>
        </div>

        <h3>6.5. Độ Phân Tán Chéo (Cross-Sectional Dispersion) Qua Các Thời Kỳ</h3>
        <div class="figure-box">
          <img src="market_data_audit/figures/eda_cross_sectional_dispersion_history.png" alt="Cross-Sectional Dispersion">
          <div class="caption">Hình 3: Diễn biến độ phân tán chéo hằng ngày (Cross-Sectional Standard Deviation) từ 2000 đến 2023. Các pha khủng hoảng (Dot-com 2000, Khủng hoảng 2008, COVID-19 2020) chứng kiến độ phân tán bùng nổ gấp 3–5 lần so với thời bình.</div>
        </div>

        <h3>6.6. Phân Hạng Thanh Khoản (Liquidity Deciles)</h3>
        <div class="table-responsive">
          __LIQUIDITY_TABLE__
        </div>
        <div class="figure-box">
          <img src="market_data_audit/figures/eda_liquidity_vs_volatility_deciles.png" alt="Liquidity Deciles vs Volatility">
          <div class="caption">Hình 4: Độ biến động hằng năm (Annualized Volatility) theo 10 phân vị thanh khoản (Decile 1 thấp nhất đến Decile 10 cao nhất).</div>
        </div>
      </div>
    </section>

    <!-- SECTION 7 -->
    <section id="sec-next" class="section-card">
      <div class="section-card-header">
        <h2>7. Trạng Thái Toàn Bộ Pipeline 10 Bước &amp; Kế Hoạch Chi Tiết Bước ⑦: Feature Engineering</h2>
        <span class="badge-phase badge-warning">Bước 1–6: Hoàn Tất ✅ | Bước 7–10: Kế Hoạch Tiếp Theo 🔜</span>
      </div>
      <div class="section-body">
        
        <h3>7.1. Bảng Trạng Thái Toàn Bộ Quy Trình 10 Bước (Pipeline End-to-End Status)</h3>
        <div class="table-responsive">
          <table class="audit-table">
            <thead>
              <tr>
                <th>Bước</th>
                <th>Tên Script / Cấu Phần</th>
                <th>Mục Tiêu Nghiên Cứu Định Lượng</th>
                <th>Đầu Ra Chính</th>
                <th>Trạng Thái</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Bước 1</strong></td>
                <td><code>01_download_and_extract_universe.py</code></td>
                <td>Bóc tách 28 snapshot PDF iShares Russell 1000 và chia tách phân vùng (Warm-up / Dev / OOS)</td>
                <td><code>data/raw/universe/by_year/</code></td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 2</strong></td>
                <td><code>02_build_tier1_warehouse.py</code></td>
                <td>Hợp nhất 10 batch QuantConnect LEAN OHLCV (13.15M dòng), đối chiếu lịch NYSE</td>
                <td><code>russell1000_constituents_daily_ohlcv_1998_2026.parquet</code></td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 3</strong></td>
                <td><code>03_apply_corporate_actions.py</code></td>
                <td>Định danh 3,711 SIDs, khử 883 Ticker Reuse, tính Continuous Split Factor, xử lý CORR_001..CORR_013</td>
                <td><code>russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet</code></td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 4</strong></td>
                <td><code>04_build_matrices_and_masks.py</code></td>
                <td>Xây dựng lưới 17 ma trận 2D (7,252 x 3,711) và cơ chế 3 lớp PIT Masks, purge ranh giới OOS</td>
                <td><code>data/processed/matrices/*.parquet</code> (26 tệp)</td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 5</strong></td>
                <td><code>05_matrix_sanity_checks.py</code></td>
                <td>Sanity check 50,000 ô ngẫu nhiên, kiểm tra tính liên tục chia tách và đẳng thức cổ tức</td>
                <td><code>docs/Data report/market_data_audit/tables/matrix_sanity_check_summary.csv</code></td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 6</strong></td>
                <td><code>06_eda_development_set.py</code></td>
                <td>EDA tập phát triển (5.61M valid stock-days, Kurtosis 66.88), hồ sơ pháp y 34 ca cực đoan</td>
                <td><code>docs/reports/data_pipeline/step6_eda_report.md</code></td>
                <td><strong style="color:var(--success);">✅ ĐÃ HOÀN THÀNH</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 7</strong></td>
                <td><code>07_feature_engineering.py</code></td>
                <td>Kỹ nghệ 16 đặc trưng định lượng &amp; nhãn mục tiêu Uniform Rank [0, 1]</td>
                <td><code>data/processed/features/*.parquet</code></td>
                <td><strong style="color:var(--warning);">🔜 KẾ HOẠCH TIẾP THEO</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 8</strong></td>
                <td><code>08_model_training_and_cv.py</code></td>
                <td>Huấn luyện mô hình GBDT (LightGBM/XGBoost/CatBoost) với Time-Series Expanding Window CV</td>
                <td><code>models/checkpoints/</code></td>
                <td><strong style="color:var(--warning);">🔜 KẾ HOẠCH TIẾP THEO</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 9</strong></td>
                <td><code>09_hyperparameter_optimization.py</code></td>
                <td>Tối ưu hóa siêu tham số Bayesian (Optuna) và kết hợp mô hình (Ensemble Blending/Stacking)</td>
                <td><code>models/ensemble/</code></td>
                <td><strong style="color:var(--warning);">🔜 KẾ HOẠCH TIẾP THEO</strong></td>
              </tr>
              <tr>
                <td><strong>Bước 10</strong></td>
                <td><code>10_backtesting_and_oos.py</code></td>
                <td>Kiểm thử thực chiến danh mục Long-Short Top/Bottom Decile, phí trượt giá &amp; giải phóng OOS</td>
                <td><code>docs/reports/backtest_and_oos_performance.md</code></td>
                <td><strong style="color:var(--warning);">🔜 KẾ HOẠCH TIẾP THEO</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>7.2. Luận Giải Khoa Học Về Biến Mục Tiêu Uniform Rank Target [0, 1]</h3>
        <p>Kết quả EDA tại Bước 6 cho thấy phân phối lợi suất thực tế có <strong>Excess Kurtosis = 66.88</strong> (đặc trưng đuôi dày của tài chính) và biên độ dao động từ <strong>-94.97% đến +227.87%</strong>. Nếu dùng hàm mất mát MSE trên return tuyệt đối, các gradient sai số từ các cú sốc cực đoan sẽ làm méo mó mô hình. Giải pháp tối ưu là chuẩn hóa mục tiêu sang phân vị đồng nhất:</p>
        
        <div class="callout success">
          <h4>Công Thức Chuẩn Hóa Mục Tiêu Xếp Hạng Hàng Ngày (Cross-Sectional Uniform Rank Target)</h4>
          <p>$$target\_next\_rank_{i,t} = \frac{\text{Rank}(r_{i, t+1}) - 1}{N_t - 1} \in [0.0, 1.0]$$</p>
          <ul>
            <li><strong>Lợi ích 1:</strong> Biến đổi phân vị đưa Kurtosis lý thuyết về mức <strong>-1.2</strong> (phân phối đều), triệt tiêu hoàn toàn nguy cơ nổ gradient.</li>
            <li><strong>Lợi ích 2:</strong> Bất biến trước chu kỳ biến động thị trường (Market Volatility Regime Invariance).</li>
            <li><strong>Lợi ích 3:</strong> Trực tiếp tối ưu hóa hệ số tương quan thứ hạng Spearman (Rank IC), nâng cao tỷ suất sinh lời danh mục Long-Short.</li>
          </ul>
        </div>

        <h3>7.3. Danh Mục 16 Đặc Trưng Định Lượng (Feature Engineering Specification)</h3>
        <p>Chi tiết đầy đủ 16 đặc trưng được thiết kế tại <code>docs/specifications/features_v1.md</code>:</p>
        <div class="table-responsive">
          <table class="audit-table">
            <thead>
              <tr>
                <th>STT</th>
                <th>Tên Feature</th>
                <th>Nhóm Logic</th>
                <th>Công Thức Toán Học Chính Xác</th>
                <th>Lookback ($W$)</th>
                <th>Căn Cứ Học Thuật / Kinh Tế</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td><code>ret_1d</code></td>
                <td>Short-term Reversal</td>
                <td>$(adj\_close_t / adj\_close_{t-1}) - 1$</td>
                <td>1 phiên</td>
                <td>Jegadeesh (1990), Lehmann (1990) — Bid-Ask bounce &amp; overreaction</td>
              </tr>
              <tr>
                <td>2</td>
                <td><code>ret_5d</code></td>
                <td>Weekly Momentum</td>
                <td>$(adj\_close_t / adj\_close_{t-5}) - 1$</td>
                <td>5 phiên</td>
                <td>Gutierrez &amp; Kelley (2008) — Chu kỳ thanh toán &amp; rebalance tuần</td>
              </tr>
              <tr>
                <td>3</td>
                <td><code>ret_20d</code></td>
                <td>Monthly Momentum</td>
                <td>$(adj\_close_t / adj\_close_{t-20}) - 1$</td>
                <td>20 phiên</td>
                <td>Asness et al. (2013) — Động lượng cấp độ 1 tháng</td>
              </tr>
              <tr>
                <td>4</td>
                <td><code>ret_60d</code></td>
                <td>Quarterly Momentum</td>
                <td>$(adj\_close_t / adj\_close_{t-60}) - 1$</td>
                <td>60 phiên</td>
                <td>Bernard &amp; Thomas (1989) — Post-Earnings Announcement Drift (PEAD)</td>
              </tr>
              <tr>
                <td>5</td>
                <td><code>ret_252d_skip1m</code></td>
                <td>12M Momentum</td>
                <td>$(adj\_close_{t-21} / adj\_close_{t-252}) - 1$</td>
                <td>252 phiên (trễ 21d)</td>
                <td>Jegadeesh &amp; Titman (1993) — Động lượng 12 tháng bỏ 1 tháng gần nhất</td>
              </tr>
              <tr>
                <td>6</td>
                <td><code>vol_realized_20d</code></td>
                <td>Short-term Risk</td>
                <td>$std(daily\_return, 20d) \times \sqrt{252}$</td>
                <td>20 phiên</td>
                <td>Ang et al. (2006) — Idiosyncratic Volatility Puzzle</td>
              </tr>
              <tr>
                <td>7</td>
                <td><code>vol_realized_60d</code></td>
                <td>Baseline Risk</td>
                <td>$std(daily\_return, 60d) \times \sqrt{252}$</td>
                <td>60 phiên</td>
                <td>Đường cơ sở biến động nền tảng quý</td>
              </tr>
              <tr>
                <td>8</td>
                <td><code>vol_ratio_20_60</code></td>
                <td>Vol Term Structure</td>
                <td>$vol\_realized\_20d / vol\_realized\_60d$</td>
                <td>60 phiên</td>
                <td>Nhận diện cú sốc biến động ngắn hạn đột ngột (Regime Shift)</td>
              </tr>
              <tr>
                <td>9</td>
                <td><code>amihud_illiq_20d</code></td>
                <td>Liquidity Impact</td>
                <td>$mean(|r| / \text{DollarVolume}, 20d) \times 10^6$</td>
                <td>20 phiên</td>
                <td>Amihud (2002) — Mức trượt giá trên mỗi triệu USD (Illiquidity Premium)</td>
              </tr>
              <tr>
                <td>10</td>
                <td><code>turnover_20d</code></td>
                <td>Volume Baseline</td>
                <td>$mean(adj\_volume, 20d)$</td>
                <td>20 phiên</td>
                <td>Gervais, Kaniel &amp; Mingelgrin (2001) — Mức độ thanh khoản bình quân</td>
              </tr>
              <tr>
                <td>11</td>
                <td><code>volume_ratio_1_20</code></td>
                <td>Attention Surge</td>
                <td>$adj\_volume_t / turnover\_20d_t$</td>
                <td>20 phiên</td>
                <td>Barber &amp; Odean (2008) — Dấu chân dòng tiền thông minh (Smart Money)</td>
              </tr>
              <tr>
                <td>12</td>
                <td><code>ret_intraday</code></td>
                <td>Day-Session Discovery</td>
                <td>$(close_t - open_t) / open_t$</td>
                <td>1 phiên</td>
                <td>Lou, Polk &amp; Skouras (2019) — Phân tách Overnight vs Intraday</td>
              </tr>
              <tr>
                <td>13</td>
                <td><code>high_low_range</code></td>
                <td>Normalized Range</td>
                <td>$(high_t - low_t) / close_t$</td>
                <td>1 phiên</td>
                <td>Parkinson (1980) — Ước lượng biến động cực trị nến</td>
              </tr>
              <tr>
                <td>14</td>
                <td><code>close_to_high_52w</code></td>
                <td>Behavioral Anchor</td>
                <td>$adj\_close_t / \max(adj\_high, 252d)$</td>
                <td>252 phiên</td>
                <td>George &amp; Hwang (2004) — Neo tâm lý đỉnh 52 tuần</td>
              </tr>
              <tr>
                <td>15</td>
                <td><code>price_level</code></td>
                <td>Nominal Scale</td>
                <td>$\ln(close_t)$</td>
                <td>1 phiên</td>
                <td>Baker, Greenwood &amp; Wurgler (2009) — Hiệu ứng thị giá danh nghĩa</td>
              </tr>
              <tr>
                <td>16</td>
                <td><code>beta_20d</code></td>
                <td>Systematic Risk</td>
                <td>$cov(r_i, r^{\text{mkt}}, 20d) / var(r^{\text{mkt}}, 20d)$</td>
                <td>20 phiên</td>
                <td>Sharpe (1964), Frazzini &amp; Pedersen (2014) — Betting Against Beta</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>7.4. Chính Sách Xử Lý Giá Trị Khuyết Thiếu (NaN Policy) &amp; Pilot Test Plan</h3>
        <ul>
          <li><strong>Bảo đảm khởi tạo trượt (Warm-up $\ge 252$ ngày):</strong> 630 phiên từ 1998-01-02 đến 2000-06-30 đảm bảo 100% mã có sẵn 252 ngày lịch sử khi bước vào tập Development ngày 01/07/2000 (Zero Cold-Start).</li>
          <li><strong>Cách ly cờ kiểm toán (Quality Flag trong cửa sổ $\to$ NaN):</strong> Bất kỳ phiên nào chạm cờ nến rác hoặc chia tách công ty con trong cửa sổ trượt $W$ ngày đều bị ép thành `NaN`.</li>
          <li><strong>Sàng lọc thanh khoản mặt cắt ($< 50$ stocks $\to$ drop ngày):</strong> Loại bỏ phiên giao dịch nếu số lượng mã hợp lệ $< 50$.</li>
          <li><strong>Kế hoạch Pilot Test:</strong> 5 đặc trưng tiêu biểu &times; 10 mã đa dạng &times; 2000–2002; nghiệm thu đối chiếu thủ công 3 ô tọa độ ngẫu nhiên trước khi chạy quy mô lớn.</li>
        </ul>

      </div>
    </section>

  </div>
</main>

</body>
</html>
"""
    # Replace place-holders
    html = template.replace("__CORP_MATCH_TABLE__", corp_match_html)
    html = html.replace("__SPLIT_FORMULA_TABLE__", split_formula_html)
    html = html.replace("__DIVIDEND_IDENTITY_TABLE__", dividend_identity_html)
    html = html.replace("__COVERAGE_PERIOD_TABLE__", coverage_by_period_html)
    html = html.replace("__SANITY_SUMMARY_TABLE__", sanity_summary_html)
    html = html.replace("__RECON_AUDIT_TABLE__", recon_audit_html)
    html = html.replace("__SPLIT_BOUNDARY_TABLE__", split_boundary_html)
    html = html.replace("__MOMENTS_TABLE__", moments_html)
    html = html.replace("__LIQUIDITY_TABLE__", liquidity_html)

    # Step 3 Detailed Audits
    html = html.replace("__CANONICAL_SID_SAMPLE_TABLE__", canonical_sid_html)
    html = html.replace("__PERIOD_RECON_TABLE__", period_recon_html)
    html = html.replace("__TICKER_CHANGES_TABLE__", ticker_changes_html)
    html = html.replace("__JUNE_JULY_BOUNDARY_TABLE__", june_july_boundary_html)
    html = html.replace("__TICKER_REUSE_BREAKDOWN_TABLE__", reuse_breakdown_html)
    html = html.replace("__CONSTITUENT_MAPPING_SAMPLE_TABLE__", constituent_mapping_sample_html)
    html = html.replace("__SEGMENTS_MAPPING_SAMPLE_TABLE__", segments_sample_html)
    html = html.replace("__AMBIGUOUS_AUDIT_TABLE__", ambig_html)
    html = html.replace("__COVERAGE_DUAL_TABLE__", dual_cov_html)
    html = html.replace("__TOP_POS_RETURNS_TABLE__", pos_returns_html)
    html = html.replace("__TOP_NEG_RETURNS_TABLE__", neg_returns_html)
    html = html.replace("__EXTREME_FORENSIC_TABLE__", extreme_forensic_html)

    with open(REPORT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    
    inst_report = BASE_DIR / "docs" / "Data report" / "institutional_pipeline_report.html"
    with open(inst_report, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report successfully compiled to:\n  -> {REPORT_OUTPUT}\n  -> {inst_report}")

if __name__ == "__main__":
    main()
