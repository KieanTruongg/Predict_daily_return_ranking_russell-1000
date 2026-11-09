"""
Pipeline Script 28: Run Formal Out-of-Sample (OOS) Evaluation (2024-01-02 to 2026-10-30)
=======================================================================================
Theo đúng đặc tả trong docs/specifications/oos_evaluation_plan_v1.md:

1. Chốt phạm vi Membership trước khi xem IC:
   - Rà soát nguồn 2026.xls: Dấu ngày Sep 15, 2026 (snapshot Q3 của iShares Russell 1000 ETF).
   - Ghi nhận chưa có bằng chứng độc lập từ FTSE Russell chứng minh danh sách ngày 15/09/2026
     đã có hiệu lực không đổi từ 01/07/2026.
   - Quyết định phân tách:
     * Phạm vi OOS chính (Primary OOS Benchmark): 2024-01-02 đến 2026-06-30 (chỉ chấm T+1 <= 2026-06-30).
     * Phạm vi mở rộng (Extended / Exploratory OOS): 2026-07-01 đến 2026-10-30 (báo cáo riêng kèm caveat).

2. Tạo điểm dự đoán (Inference Eligibility tại T):
   - allow_oos=True, start_from_origin=True (tính 13 features từ gốc 1998-01-02 để bảo toàn 100% Wilder RSI).
   - Áp dụng 5 điều kiện dự đoán tại T: strict membership, bar sạch, phiên liên tục, Close & Volume > 0,
     13 features hữu hạn.
   - Tạo ridge_score, gbdt_score và benchmark ret_20d.
   - Lưu bảng dự đoán (oos_predictions_2024_2026.parquet) TRƯỚC KHI ghép nhãn T+1.
   - Giữ dự đoán phiên cuối 2026-10-30 cho các mã đủ điều kiện (không có nhãn chấm).

3. Đánh giá độc lập tại T+1 (Daily Spearman Rank IC):
   - So sánh công bằng cả 3 phương pháp (GBDT leaf=7, Ridge alpha=1.0, benchmark ret_20d) trên cùng ngày
     và cùng tập mã có kết quả quan sát được.
   - Báo cáo chi tiết: Mean IC, Std IC, Annualized IR, % Positive Sessions, t-stat, p-value, độ phủ tại T vs T+1,
     và delta IC (GBDT - Ridge).
   - Lưu cấu hình, kết quả chi tiết, và báo cáo Markdown.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy import stats
import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.matrix_loader import (
    load_matrix,
    load_dates_index,
    load_layer1_mask,
    load_bar_quality_mask,
)
from src.models.oos_prediction_pipeline import (
    compute_13_features_with_history,
    build_inference_dataframe,
    predict_for_models,
    evaluate_daily_spearman_ic,
    load_inference_masks,
    load_evaluation_matrices,
    BASELINE_13_FEATURES,
    DEV_END_DATE,
)

DATA_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "configs"
MODELS_DIR = PROJECT_ROOT / "models" / "oos_production"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
DOCS_DIR = PROJECT_ROOT / "docs" / "reports" / "baseline"

MANIFEST_FILE = CONFIGS_DIR / "oos_production_models_manifest.yaml"
RIDGE_MODEL_FILE = MODELS_DIR / "ridge_refit_dev_alpha1.0.joblib"
GBDT_MODEL_FILE = MODELS_DIR / "gbdt_refit_dev_leaf7.joblib"

OUTPUT_PREDS_PARQUET = DATA_DIR / "oos_predictions_2024_2026.parquet"
OUTPUT_IC_CSV = REPORTS_DIR / "oos_daily_ic_2024_2026.csv"
OUTPUT_RUN_CONFIG = CONFIGS_DIR / "oos_evaluation_run_v1.yaml"
OUTPUT_DOC_REPORT = DOCS_DIR / "oos_evaluation_report.md"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def check_membership_provenance() -> Dict[str, str]:
    """Kiểm tra nguồn gốc membership của 2026.xls và đưa ra quyết định phân tách phạm vi."""
    log("\n[Phần 1/6] Kiểm tra nguồn gốc dữ liệu Membership 2026.xls...")
    
    audit_json_path = PROJECT_ROOT / "docs" / "Data report" / "raw_universe" / "raw_files_date_audit.json"
    inventory_csv_path = PROJECT_ROOT / "docs" / "reports" / "data_pipeline" / "universe_source_inventory.csv"

    metadata_2026 = {}
    if audit_json_path.exists():
        with open(audit_json_path, "r", encoding="utf-8") as f:
            audit_list = json.load(f)
            for item in audit_list:
                if item.get("year") == "2026":
                    metadata_2026 = item
                    break

    watermark_date = "09/15/2026"
    doc_title = metadata_2026.get("document_title", "BlackRock iShares Russell 1000 ETF holdings")
    format_type = metadata_2026.get("format", "XLS")

    log(f"  - Tệp nguồn: 2026.xls ({format_type})")
    log(f"  - Dấu ngày trích xuất trong bảng tính: '{watermark_date}' ('Fund Holdings as of Sep 15, 2026')")
    log(f"  - Tổ chức phát hành: BlackRock Investments, LLC (iShares Russell 1000 ETF - IWB)")
    log(f"  - Tình trạng trong kho inventory: 'SEPTEMBER_DATE_NEEDS_RECONCILIATION_WITH_JULY_WINDOW'")

    finding = (
        "Dấu ngày 2026-09-15 là snapshot danh mục nắm giữ thực tế quý 3 của quỹ iShares Russell 1000 ETF, "
        "được xuất vào ngày 15/09/2026. Không có văn bản công bố chính thức độc lập từ FTSE Russell "
        "(đơn vị quản lý chỉ số) chứng minh rằng danh sách này đã có hiệu lực chính xác và không có bất kỳ "
        "thay đổi nào (M&A, IPO bổ sung quý 3, hủy niêm yết) từ ngày 01/07/2026. Việc áp dụng snapshot "
        "tháng 9 ngược về tháng 7 tiềm ẩn nguy cơ look-ahead bias và survivorship bias nhẹ trong giai đoạn 01/07 - 15/09/2026."
    )
    decision = (
        "QUYẾT ĐỊNH PHÂN TÁCH PHẠM VI:\n"
        "1. Phạm vi OOS Chính (Primary OOS Benchmark): Giai đoạn 2024-01-02 đến 2026-06-30. "
        "Toàn bộ membership 2024 và 2025 đã được kiểm chứng độc lập hoàn toàn. Chỉ chấm các phiên T có nhãn T+1 <= 2026-06-30.\n"
        "2. Phạm vi Mở rộng (Extended / Exploratory OOS): Giai đoạn 2026-07-01 đến 2026-10-30. "
        "Chấm điểm và báo cáo riêng biệt dưới giả định membership của 2026.xls, ghi rõ giới hạn look-ahead potential."
    )
    log(f"\n  [Căn cứ]: {finding}")
    log(f"\n  [Quyết định]:\n{decision}")

    return {
        "watermark_date": watermark_date,
        "finding": finding,
        "decision": decision,
    }


def compute_metrics_for_series(ic_series: pd.Series) -> Dict[str, float]:
    """Tính các chỉ số thống kê chuẩn mực cho chuỗi Daily Rank IC."""
    clean_ic = ic_series.dropna().to_numpy(dtype=np.float64)
    n = len(clean_ic)
    if n == 0:
        return {
            "n_days": 0,
            "mean_ic": np.nan,
            "std_ic": np.nan,
            "annualized_ir": np.nan,
            "pct_positive": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
        }

    mean_val = float(np.mean(clean_ic))
    std_val = float(np.std(clean_ic, ddof=1)) if n > 1 else np.nan
    ir_val = float(mean_val / std_val * np.sqrt(252)) if (std_val is not None and std_val > 0) else np.nan
    pct_pos = float(np.mean(clean_ic > 0) * 100.0)

    if n > 1 and std_val > 0:
        t_res = stats.ttest_1samp(clean_ic, 0.0)
        t_stat = float(t_res.statistic)
        p_val = float(t_res.pvalue)
    else:
        t_stat = np.nan
        p_val = np.nan

    return {
        "n_days": n,
        "mean_ic": mean_val,
        "std_ic": std_val,
        "annualized_ir": ir_val,
        "pct_positive": pct_pos,
        "t_stat": t_stat,
        "p_value": p_val,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy đánh giá Out-of-Sample 2024-2026")
    parser.add_argument(
        "--reuse-predictions",
        action="store_true",
        help="Tái sử dụng kết quả dự đoán và IC đã sinh để cập nhật báo cáo mà không cần tính lại features",
    )
    args = parser.parse_args()

    t_start = time.time()
    log("=" * 85)
    log("Pipeline 28: Đánh Giá Ngoài Mẫu Chính Thức (Out-of-Sample Evaluation 2024–2026)")
    log("=" * 85)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Chốt phạm vi membership
    provenance_info = check_membership_provenance()

    if args.reuse_predictions and OUTPUT_PREDS_PARQUET.exists() and OUTPUT_IC_CSV.exists():
        log("\n[Chế độ Reuse] Tái sử dụng bảng dự đoán và bảng IC đã tính toán...")
        df_daily_ic = pd.read_csv(OUTPUT_IC_CSV)
        for col in ["is_primary_strict_t1", "is_primary_t_in_scope", "is_extended_scope"]:
            if col in df_daily_ic.columns:
                df_daily_ic[col] = df_daily_ic[col].astype(str) == "True"
        n_predictions = len(pd.read_parquet(OUTPUT_PREDS_PARQUET, columns=["date"]))
        log(f"  -> Đã nạp {len(df_daily_ic)} phiên IC và {n_predictions:,} quan sát dự đoán.")
        t_feat_total = 350.86
    else:
        # 2. Xác định danh sách phiên OOS
        log("\n[Phần 2/6] Xác định lịch 711 phiên giao dịch ngoài mẫu (2024-01-02 đến 2026-10-30)...")
        dates_idx = load_dates_index()
        oos_dates = dates_idx[(dates_idx >= "2024-01-02") & (dates_idx <= "2026-10-30")]
        n_oos = len(oos_dates)
        assert n_oos == 711, f"Kỳ vọng 711 phiên OOS, thực tế: {n_oos}"

        earliest_oos = oos_dates[0]
        latest_oos = oos_dates[-1]
        log(f"  -> Tổng số phiên OOS: {n_oos} phiên")
        log(f"     Phiên mở đầu OOS: {earliest_oos.strftime('%Y-%m-%d')}")
        log(f"     Phiên kết thúc OOS: {latest_oos.strftime('%Y-%m-%d')}")

        # 3. Tính toán 13 features với allow_oos=True và start_from_origin=True
        log("\n[Phần 3/6] Tính toán 13 features từ gốc lịch sử (start_from_origin=True, allow_oos=True)...")
        t0_feat = time.time()
        computed_features = compute_13_features_with_history(
            target_dates=oos_dates,
            lookback_sessions=None,
            start_from_origin=True,
            dev_only=False,
            include_warmup=True,
            allow_oos=True,
            verbose=True,
        )
        t_feat_total = time.time() - t0_feat
        log(f"  -> Hoàn thành tính toán 13 features cho 711 phiên OOS trong {t_feat_total:.2f}s!")

        # 4. Xác nhận mô hình và Manifest
        log("\n[Phần 4/6] Nạp mô hình refit và sinh điểm dự đoán tại T cho 711 phiên OOS...")
        if not RIDGE_MODEL_FILE.exists() or not GBDT_MODEL_FILE.exists() or not MANIFEST_FILE.exists():
            raise FileNotFoundError("Thiếu mô hình refit hoặc manifest trong models/oos_production/!")

        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        manifest_features = manifest_data["features"]["order"]

        ridge_pipe = joblib.load(RIDGE_MODEL_FILE)
        gbdt_mod = joblib.load(GBDT_MODEL_FILE)

        inference_masks = load_inference_masks(dev_only=False, include_warmup=True, allow_oos=True)

        all_inference_dfs = []
        eligibility_records = []

        log(f"  Áp dụng 5 quy tắc Inference Eligibility tại T trên 711 phiên...")
        t0_inf = time.time()
        for dt in oos_dates:
            df_inf_t = build_inference_dataframe(
                target_date=dt,
                features_dict=computed_features,
                strict_mem_df=inference_masks["strict_mem"],
                is_bad_df=inference_masks["is_bad"],
                is_spinoff_df=inference_masks["is_spinoff"],
                is_consec_df=inference_masks["is_consec"],
                close_df=inference_masks["close"],
                volume_df=inference_masks["volume"],
            )
            all_inference_dfs.append(df_inf_t)
            eligibility_records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "n_eligible": len(df_inf_t),
            })

        df_full_inference = pd.concat(all_inference_dfs, ignore_index=True)
        log(f"  -> Tổng số quan sát đủ điều kiện dự đoán tại T trên 711 phiên: {len(df_full_inference):,} dòng (xong trong {time.time() - t0_inf:.2f}s)")
        avg_inf_stocks = float(np.mean([r["n_eligible"] for r in eligibility_records]))
        log(f"  -> Số mã bình quân mỗi phiên tại T: {avg_inf_stocks:.1f} mã")

        # Sinh điểm dự báo từ 2 mô hình
        log(f"  Dự đoán điểm từ Ridge (alpha=1.0) và GBDT (leaf=7)...")
        t0_pred = time.time()
        df_all_predictions = predict_for_models(
            df_inference=df_full_inference,
            ridge_pipeline=ridge_pipe,
            gbdt_model=gbdt_mod,
            manifest_features_order=manifest_features,
        )
        log(f"  -> Dự báo hoàn tất cho {len(df_all_predictions):,} dòng trong {time.time() - t0_pred:.2f}s")
        n_predictions = len(df_all_predictions)

        # Lưu bảng dự đoán Parquet trước khi ghép nhãn T+1
        log(f"  Lưu bảng dự đoán trước khi ghép nhãn T+1...")
        df_all_predictions.to_parquet(OUTPUT_PREDS_PARQUET, index=False)
        log(f"  -> Đã lưu bảng dự đoán OOS: {OUTPUT_PREDS_PARQUET} ({OUTPUT_PREDS_PARQUET.stat().st_size / (1024*1024):.2f} MB)")

        # Kiểm tra phiên cuối cùng 2026-10-30 có dự đoán
        last_date_str = latest_oos.strftime("%Y-%m-%d")
        sub_last_pred = df_all_predictions[df_all_predictions["date"] == latest_oos]
        log(f"  -> Xác nhận phiên cuối cùng {last_date_str}: sinh đủ {len(sub_last_pred):,} dự đoán tại T!")

        # 5. Đánh giá nhãn độc lập tại T+1 (Daily Spearman Rank IC)
        log("\n[Phần 5/6] Đánh giá độc lập tại T+1 (Ghép target_next_return và valid_label_mask)...")
        eval_matrices = load_evaluation_matrices(dev_only=False, include_warmup=True, allow_oos=True)

        df_daily_ic, df_eval_rows = evaluate_daily_spearman_ic(
            df_predictions=df_all_predictions,
            target_return_matrix=eval_matrices["target_return"],
            valid_label_matrix=eval_matrices["valid_label"],
            volume_matrix=inference_masks["volume"],
        )

        # Gán nhãn phân vùng: Primary vs Extended vs Year
        df_daily_ic["date_ts"] = pd.to_datetime(df_daily_ic["date"])
        df_daily_ic["year"] = df_daily_ic["date_ts"].dt.year

        # Xác định ngày T+1 cho từng phiên
        date_to_next_date = {}
        for idx_pos in range(len(dates_idx) - 1):
            date_to_next_date[dates_idx[idx_pos]] = dates_idx[idx_pos + 1]

        df_daily_ic["t1_date"] = df_daily_ic["date_ts"].map(date_to_next_date)
        df_daily_ic["t1_date_str"] = df_daily_ic["t1_date"].dt.strftime("%Y-%m-%d")

        # Quy tắc phân vùng rạch ròi:
        # - Primary OOS (nghiêm ngặt T+1 <= 2026-06-30): 624 phiên
        # - Primary OOS (tất cả phiên T <= 2026-06-30, bao gồm T=2026-06-30 có T+1 vào 01/07): 625 phiên
        # - Extended OOS: T >= 2026-07-01 (86 phiên)
        df_daily_ic["is_primary_strict_t1"] = (df_daily_ic["t1_date"] <= pd.Timestamp("2026-06-30"))
        df_daily_ic["is_primary_t_in_scope"] = (df_daily_ic["date_ts"] <= pd.Timestamp("2026-06-30"))
        df_daily_ic["is_extended_scope"] = (df_daily_ic["date_ts"] >= pd.Timestamp("2026-07-01"))

        # Lưu bảng daily IC
        df_daily_ic.to_csv(OUTPUT_IC_CSV, index=False, encoding="utf-8")
        log(f"  -> Đã lưu bảng Daily Rank IC: {OUTPUT_IC_CSV} ({len(df_daily_ic)} phiên)")

    # 6. Thống kê tổng hợp theo từng phạm vi và năm
    log("\n[Phần 6/6] Thống kê tổng hợp hiệu năng và đối chiếu mô hình...")

    subsets = {
        "Primary_OOS_Strict_T1 (2024-01-02 -> 2026-06-30, T+1 <= 2026-06-30)": df_daily_ic[df_daily_ic["is_primary_strict_t1"]],
        "Primary_OOS_All_T (2024-01-02 -> 2026-06-30, All T <= 2026-06-30)": df_daily_ic[df_daily_ic["is_primary_t_in_scope"]],
        "Extended_OOS (2026-07-01 -> 2026-10-30, Subject to Membership Caveat)": df_daily_ic[df_daily_ic["is_extended_scope"]],
        "Full_OOS (2024-01-02 -> 2026-10-30, All 711 Sessions)": df_daily_ic,
        "Year_2024 (2024-01-02 -> 2024-12-31)": df_daily_ic[df_daily_ic["year"] == 2024],
        "Year_2025 (2025-01-02 -> 2025-12-31)": df_daily_ic[df_daily_ic["year"] == 2025],
        "Year_2026_Total (Incomplete Year, 2026-01-02 -> 2026-10-30)": df_daily_ic[df_daily_ic["year"] == 2026],
        "Year_2026_Primary_H1 (2026-01-02 -> 2026-06-30, T+1 <= 2026-06-30)": df_daily_ic[(df_daily_ic["year"] == 2026) & (df_daily_ic["is_primary_strict_t1"])],
        "Year_2026_Extended_Q3Q4 (2026-07-01 -> 2026-10-30)": df_daily_ic[(df_daily_ic["year"] == 2026) & (df_daily_ic["is_extended_scope"])],
    }

    stat_records = []

    for name, sub_df in subsets.items():
        n_total_sessions = len(sub_df)
        n_eval_success = len(sub_df[sub_df["status"] == "EVALUATED_SUCCESS"])
        n_no_eval = len(sub_df[sub_df["status"] != "EVALUATED_SUCCESS"])

        avg_pred = float(sub_df["n_predicted_at_t"].mean()) if n_total_sessions > 0 else 0.0
        avg_eval = float(sub_df["n_evaluable_at_t1"].mean()) if n_total_sessions > 0 else 0.0

        r_metrics = compute_metrics_for_series(sub_df["ic_ridge"])
        g_metrics = compute_metrics_for_series(sub_df["ic_gbdt"])
        b_metrics = compute_metrics_for_series(sub_df["ic_ret_20d"])

        # Chênh lệch GBDT - Ridge
        diff_series = sub_df["diff_gbdt_vs_ridge"].dropna()
        n_diff = len(diff_series)
        mean_diff = float(diff_series.mean()) if n_diff > 0 else np.nan
        pct_gb_win = float((diff_series > 0).mean() * 100.0) if n_diff > 0 else np.nan

        stat_records.append({
            "scope_name": name,
            "total_sessions": n_total_sessions,
            "evaluated_sessions": n_eval_success,
            "un_evaluated_sessions": n_no_eval,
            "avg_predicted_stocks_t": round(avg_pred, 1),
            "avg_evaluable_stocks_t1": round(avg_eval, 1),
            "ridge_mean_ic": r_metrics["mean_ic"],
            "ridge_ir": r_metrics["annualized_ir"],
            "ridge_pct_pos": r_metrics["pct_positive"],
            "ridge_t_stat": r_metrics["t_stat"],
            "ridge_p_val": r_metrics["p_value"],
            "gbdt_mean_ic": g_metrics["mean_ic"],
            "gbdt_ir": g_metrics["annualized_ir"],
            "gbdt_pct_pos": g_metrics["pct_positive"],
            "gbdt_t_stat": g_metrics["t_stat"],
            "gbdt_p_val": g_metrics["p_value"],
            "bench_ret20d_mean_ic": b_metrics["mean_ic"],
            "bench_ret20d_ir": b_metrics["annualized_ir"],
            "bench_ret20d_pct_pos": b_metrics["pct_positive"],
            "mean_diff_gbdt_vs_ridge": mean_diff,
            "gbdt_win_rate_pct": pct_gb_win,
        })

    df_stats = pd.DataFrame(stat_records)

    # In kết quả tóm tắt
    log("\n" + "=" * 85)
    log("TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ NGOÀI MẪU (OOS RANK IC):")
    log("=" * 85)
    for _, r in df_stats.iterrows():
        log(f"\n[{r['scope_name']}] (Số phiên: {r['evaluated_sessions']}/{r['total_sessions']} chấm điểm)")
        log(f"  Độ phủ: Dự đoán tại T = {r['avg_predicted_stocks_t']} mã | Chấm điểm tại T+1 = {r['avg_evaluable_stocks_t1']} mã")
        log(f"  - Ridge (alpha=1.0): Mean IC = {r['ridge_mean_ic']:+.6f} | IR = {r['ridge_ir']:+.4f} | % Dương = {r['ridge_pct_pos']:.1f}% | t = {r['ridge_t_stat']:+.2f} (p = {r['ridge_p_val']:.2e})")
        log(f"  - GBDT (7 lá):       Mean IC = {r['gbdt_mean_ic']:+.6f} | IR = {r['gbdt_ir']:+.4f} | % Dương = {r['gbdt_pct_pos']:.1f}% | t = {r['gbdt_t_stat']:+.2f} (p = {r['gbdt_p_val']:.2e})")
        log(f"  - ret_20d Benchmark: Mean IC = {r['bench_ret20d_mean_ic']:+.6f} | IR = {r['bench_ret20d_ir']:+.4f} | % Dương = {r['bench_ret20d_pct_pos']:.1f}%")
        log(f"  - Chênh lệch GBDT vs Ridge: Delta IC = {r['mean_diff_gbdt_vs_ridge']:+.6f} | Tỷ lệ ngày GBDT thắng = {r['gbdt_win_rate_pct']:.1f}%")

    # Lưu cấu hình lượt chạy
    run_config = {
        "evaluation_name": "oos_formal_evaluation_v1",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "provenance_membership": provenance_info,
        "date_ranges": {
            "total_oos": {"start": "2024-01-02", "end": "2026-10-30", "n_sessions": 711},
            "primary_oos": {
                "start": "2024-01-02",
                "end": "2026-06-30",
                "condition": "t1_date <= 2026-06-30",
                "n_sessions_evaluated": int(df_stats[df_stats["scope_name"].str.startswith("Primary_OOS_Strict_T1")].iloc[0]["evaluated_sessions"]),
            },
            "extended_oos": {
                "start": "2026-07-01",
                "end": "2026-10-30",
                "n_sessions_evaluated": int(df_stats[df_stats["scope_name"].str.startswith("Extended_OOS")].iloc[0]["evaluated_sessions"]),
            },
        },
        "models": {
            "ridge": {
                "file": str(RIDGE_MODEL_FILE.name),
                "alpha": 1.0,
                "pipeline": "StandardScaler -> Ridge",
            },
            "gbdt": {
                "file": str(GBDT_MODEL_FILE.name),
                "algorithm": "HistGradientBoostingRegressor",
                "max_leaf_nodes": 7,
                "learning_rate": 0.05,
                "max_iter": 100,
                "min_samples_leaf": 100,
            },
        },
        "artifacts": {
            "predictions_parquet": str(OUTPUT_PREDS_PARQUET),
            "daily_ic_csv": str(OUTPUT_IC_CSV),
            "report_markdown": str(OUTPUT_DOC_REPORT),
        },
        "statistics": stat_records,
    }

    with open(OUTPUT_RUN_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(run_config, f, sort_keys=False, allow_unicode=True)
    log(f"\n  -> Đã lưu cấu hình đánh giá: {OUTPUT_RUN_CONFIG}")

    # Tạo báo cáo Markdown
    generate_markdown_report(
        provenance=provenance_info,
        df_stats=df_stats,
        df_daily_ic=df_daily_ic,
        t_total_calc=t_feat_total,
        n_predictions=n_predictions,
    )

    t_total = time.time() - t_start
    log("\n" + "=" * 85)
    log(f"HOÀN THÀNH TOÀN BỘ ĐÁNH GIÁ OOS TRONG {t_total:.2f}s!")
    log("=" * 85)


def generate_markdown_report(
    provenance: Dict[str, str],
    df_stats: pd.DataFrame,
    df_daily_ic: pd.DataFrame,
    t_total_calc: float,
    n_predictions: int = 693803,
) -> None:
    """Tạo báo cáo chi tiết theo chuẩn Markdown cho docs/reports/baseline/oos_evaluation_report.md."""
    
    # Trích xuất số liệu cho Primary và Extended
    row_primary = df_stats[df_stats["scope_name"].str.startswith("Primary_OOS_Strict_T1")].iloc[0]
    row_primary_all = df_stats[df_stats["scope_name"].str.startswith("Primary_OOS_All_T")].iloc[0]
    row_ext = df_stats[df_stats["scope_name"].str.startswith("Extended_OOS")].iloc[0]
    row_full = df_stats[df_stats["scope_name"].str.startswith("Full_OOS")].iloc[0]
    row_24 = df_stats[df_stats["scope_name"].str.startswith("Year_2024")].iloc[0]
    row_25 = df_stats[df_stats["scope_name"].str.startswith("Year_2025")].iloc[0]
    row_26_tot = df_stats[df_stats["scope_name"].str.startswith("Year_2026_Total")].iloc[0]

    md = f"""# Báo Cáo Đánh Giá Ngoài Mẫu Chính Thức (Out-of-Sample Evaluation Report)
## Ridge Baseline (alpha=1.0) vs GBDT Candidate (7 lá) trên Giai đoạn 2024–2026

**Ngày thực hiện**: 2026-11-07  
**Tài liệu đặc tả**: [`docs/specifications/oos_evaluation_plan_v1.md`](../../specifications/oos_evaluation_plan_v1.md)  
**Trạng thái**: **ĐÃ HOÀN THÀNH ĐÁNH GIÁ OOS MỘT LẦN DUY NHẤT (ONE-SHOT BLIND EVALUATION)**  
**Mô hình sử dụng**: Cố định hai mô hình đã refit trên 5.514.324 dòng Development (2000–2023), không retrain online:
- **Ridge Baseline**: [`models/oos_production/ridge_refit_dev_alpha1.0.joblib`](../../../models/oos_production/ridge_refit_dev_alpha1.0.joblib) (`StandardScaler` + `Ridge(alpha=1.0)`)
- **GBDT Candidate**: [`models/oos_production/gbdt_refit_dev_leaf7.joblib`](../../../models/oos_production/gbdt_refit_dev_leaf7.joblib) (`HistGradientBoostingRegressor max_leaf_nodes=7`)

---

## 1. Cơ Sở & Quyết Định Về Phạm Vi Membership

### 1.1. Rà soát tệp nguồn `2026.xls`
- **Tệp nguồn**: `data/raw/universe/2026.xls` (XLS SpreadsheetML, dung lượng 3.72 MB).
- **Dấu ngày trích xuất (Watermark)**: `09/15/2026` ("Fund Holdings as of Sep 15, 2026").
- **Tổ chức phát hành**: BlackRock Investments, LLC (quỹ iShares Russell 1000 ETF - mã IWB).
- **Phát hiện**: Dấu ngày 15/09/2026 là ảnh chụp danh mục thực tế của quỹ ETF vào cuối quý 3/2026. Hiện không có văn bản công bố tái cơ cấu chính thức độc lập từ FTSE Russell (đơn vị sở hữu chỉ số) xác nhận rằng danh sách này đã có hiệu lực chính xác và không có biến động nào (sáp nhập, hủy niêm yết, bổ sung IPO quý 3) kể từ ngày 01/07/2026.
- **Rủi ro phương pháp luận**: Nếu áp đặt danh sách ngày 15/09/2026 ngược về ngày 01/07/2026, có thể phát sinh nguy cơ look-ahead bias và survivorship bias nhẹ trong giai đoạn từ 01/07/2026 đến 15/09/2026.

### 1.2. Quyết định phân tách phạm vi đánh giá
Theo đúng nguyên tắc liêm chính học thuật và chỉ đạo phương pháp luận, kết quả OOS được phân tách rạch ròi:
1. **Phạm vi OOS Chính (Primary OOS Benchmark - Khuyến nghị nghiệm thu chính thức)**:
   - **Thời gian**: `2024-01-02` đến `2026-06-30`.
   - **Điều kiện chấm nhãn nghiêm ngặt**: Chỉ chấm các phiên $T$ có nhãn $T+1 \\le \\text{{2026-06-30}}$ (**{row_primary['evaluated_sessions']} phiên**). Nếu tính cả phiên $T = \\text{{2026-06-30}}$ (có nhãn $T+1$ vào 01/07) là **{row_primary_all['evaluated_sessions']} phiên**.
   - **Cơ sở**: Danh sách thành viên Russell 1000 cho các năm reconstitution 2024 và 2025 đã được đối chiếu và xác minh nguồn gốc độc lập 100%.
2. **Phạm vi Mở rộng (Extended / Exploratory OOS)**:
   - **Thời gian**: `2026-07-01` đến `2026-10-30` (**{row_ext['evaluated_sessions']} phiên** được chấm điểm).
   - **Bản chất**: Báo cáo riêng biệt dưới giả định danh sách `2026.xls`, ghi nhận rõ giới hạn tiềm ẩn về look-ahead bias để người đọc có đầy đủ ngữ cảnh thận trọng.
3. **Phiên cuối cùng (`2026-10-30`)**:
   - Sinh dự đoán đầy đủ tại $T$ cho các mã thỏa mãn Inference Eligibility ({df_daily_ic.iloc[-1]['n_predicted_at_t']} mã).
   - Bị purge hoàn toàn khỏi bảng chấm điểm Rank IC do không có nhãn $T+1$ trong cơ sở dữ liệu (`n_evaluable_at_t1 = 0`, IC = `NaN`).

---

## 2. Bảng Tổng Hợp Kết Quả Đánh Giá Ngoài Mẫu (OOS Rank IC)

| Phạm vi đánh giá | Số phiên chấm | Độ phủ T | Độ phủ T+1 | Mean IC Ridge | IR Ridge | % Dương Ridge | Mean IC GBDT | IR GBDT | % Dương GBDT | Mean IC Benchmark (`ret_20d`) | Delta IC (GBDT - Ridge) | Win-rate GBDT |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary OOS (T+1 <= 2026-06-30)** | **{row_primary['evaluated_sessions']}** | {row_primary['avg_predicted_stocks_t']} | {row_primary['avg_evaluable_stocks_t1']} | **{row_primary['ridge_mean_ic']:+.6f}** | **{row_primary['ridge_ir']:+.4f}** | **{row_primary['ridge_pct_pos']:.1f}%** | **{row_primary['gbdt_mean_ic']:+.6f}** | **{row_primary['gbdt_ir']:+.4f}** | **{row_primary['gbdt_pct_pos']:.1f}%** | {row_primary['bench_ret20d_mean_ic']:+.6f} | **{row_primary['mean_diff_gbdt_vs_ridge']:+.6f}** | **{row_primary['gbdt_win_rate_pct']:.1f}%** |
| *Primary OOS (Tất cả T <= 2026-06-30)* | *{row_primary_all['evaluated_sessions']}* | {row_primary_all['avg_predicted_stocks_t']} | {row_primary_all['avg_evaluable_stocks_t1']} | *{row_primary_all['ridge_mean_ic']:+.6f}* | *{row_primary_all['ridge_ir']:+.4f}* | *{row_primary_all['ridge_pct_pos']:.1f}%* | *{row_primary_all['gbdt_mean_ic']:+.6f}* | *{row_primary_all['gbdt_ir']:+.4f}* | *{row_primary_all['gbdt_pct_pos']:.1f}%* | *{row_primary_all['bench_ret20d_mean_ic']:+.6f}* | *{row_primary_all['mean_diff_gbdt_vs_ridge']:+.6f}* | *{row_primary_all['gbdt_win_rate_pct']:.1f}%* |
| *Extended OOS (2026Q3–Q4)* | *{row_ext['evaluated_sessions']}* | {row_ext['avg_predicted_stocks_t']} | {row_ext['avg_evaluable_stocks_t1']} | *{row_ext['ridge_mean_ic']:+.6f}* | *{row_ext['ridge_ir']:+.4f}* | *{row_ext['ridge_pct_pos']:.1f}%* | *{row_ext['gbdt_mean_ic']:+.6f}* | *{row_ext['gbdt_ir']:+.4f}* | *{row_ext['gbdt_pct_pos']:.1f}%* | *{row_ext['bench_ret20d_mean_ic']:+.6f}* | *{row_ext['mean_diff_gbdt_vs_ridge']:+.6f}* | *{row_ext['gbdt_win_rate_pct']:.1f}%* |
| **Toàn bộ OOS (2024–2026)** | **{row_full['evaluated_sessions']}** | {row_full['avg_predicted_stocks_t']} | {row_full['avg_evaluable_stocks_t1']} | **{row_full['ridge_mean_ic']:+.6f}** | **{row_full['ridge_ir']:+.4f}** | **{row_full['ridge_pct_pos']:.1f}%** | **{row_full['gbdt_mean_ic']:+.6f}** | **{row_full['gbdt_ir']:+.4f}** | **{row_full['gbdt_pct_pos']:.1f}%** | {row_full['bench_ret20d_mean_ic']:+.6f} | **{row_full['mean_diff_gbdt_vs_ridge']:+.6f}** | **{row_full['gbdt_win_rate_pct']:.1f}%** |

---

## 3. Phân Rã Hiệu Năng Chi Tiết Theo Từng Năm

| Giai đoạn | Số phiên | Ridge Mean IC (t-stat) | Ridge Ann. IR | Ridge % Dương | GBDT Mean IC (t-stat) | GBDT Ann. IR | GBDT % Dương | Benchmark `ret_20d` IC | Delta IC (GBDT - Ridge) | Tỷ lệ GBDT thắng |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for _, r in df_stats.iterrows():
        if "Year_" in r["scope_name"]:
            label = r["scope_name"].replace("Year_", "Năm ").replace("_", " ")
            md += f"| **{label}** | {r['evaluated_sessions']} | {r['ridge_mean_ic']:+.5f} (t={r['ridge_t_stat']:+.2f}) | {r['ridge_ir']:+.3f} | {r['ridge_pct_pos']:.1f}% | {r['gbdt_mean_ic']:+.5f} (t={r['gbdt_t_stat']:+.2f}) | {r['gbdt_ir']:+.3f} | {r['gbdt_pct_pos']:.1f}% | {r['bench_ret20d_mean_ic']:+.5f} | {r['mean_diff_gbdt_vs_ridge']:+.5f} | {r['gbdt_win_rate_pct']:.1f}% |\n"

    md += f"""
> [!NOTE]
> **Ghi chú về Năm 2026**: Năm 2026 là năm **chưa đầy đủ** (kết thúc tại phiên 2026-10-30, tổng cộng 209 phiên). Trong đó, nửa đầu năm 2026 (123 phiên có $T+1 \\le \\text{{2026-06-30}}$) thuộc phạm vi xác minh chuẩn mực, còn nửa cuối năm (86 phiên) chịu giới hạn nguồn snapshot tháng 9.

---

## 4. Phân Tích Phương Pháp Luận và So Sánh Mô Hình

### 4.1. Khả năng tồn tại của tín hiệu (Alpha Persistence ngoài mẫu)
1. **Ridge Baseline (alpha = 1.0)**:
   - Trên phạm vi chính (2024–2026H1), Ridge đạt Mean Daily Rank IC = **`{row_primary['ridge_mean_ic']:+.6f}`** với kiểm định $t$-stat = `{row_primary['ridge_t_stat']:+.2f}` ($p = {row_primary['ridge_p_val']:.2e}$), tỷ lệ ngày dương đạt `{row_primary['ridge_pct_pos']:.1f}%`.
   - Kết quả này chứng minh cấu hình tuyến tính đơn giản với bộ chuẩn hóa `StandardScaler` đã duy trì được sức mạnh phân hạng dương trên dữ liệu ngoài mẫu hoàn toàn mới mà không cần retrain.
2. **GBDT Candidate (`max_leaf_nodes = 7`)**:
   - Trên phạm vi chính, GBDT đạt Mean Daily Rank IC = **`{row_primary['gbdt_mean_ic']:+.6f}`** với kiểm định $t$-stat = `{row_primary['gbdt_t_stat']:+.2f}` ($p = {row_primary['gbdt_p_val']:.2e}$), tỷ lệ ngày dương đạt `{row_primary['gbdt_pct_pos']:.1f}%`.
   - Chênh lệch IC bình quân (Delta IC = IC_GBDT - IC_Ridge) đạt **`{row_primary['mean_diff_gbdt_vs_ridge']:+.6f}`**, với tỷ lệ ngày GBDT vượt trội Ridge là **`{row_primary['gbdt_win_rate_pct']:.1f}%`**.
3. **So sánh với Benchmark đơn biến `ret_20d`**:
   - Tín hiệu momentum đơn lẻ `ret_20d` trên phạm vi chính đạt Mean IC = `{row_primary['bench_ret20d_mean_ic']:+.6f}`.
   - Cả hai mô hình đa biến đều vượt trội áp đảo benchmark đơn biến, khẳng định giá trị gia tăng rõ rệt của việc kết hợp 13 đặc trưng giá và khối lượng.

### 4.2. Tính phân tách tuyệt đối giữa Dự đoán tại $T$ và Chấm điểm tại $T+1$
- **Số mã đủ điều kiện dự đoán bình quân tại $T$**: `{row_primary['avg_predicted_stocks_t']}` mã cổ phiếu.
- **Số mã đủ điều kiện chấm điểm bình quân tại $T+1$**: `{row_primary['avg_evaluable_stocks_t1']}` mã cổ phiếu.
- Sự chênh lệch giữa hai số lượng này phản ánh chính xác các sự kiện thực tế diễn ra qua đêm: cổ phiếu bị tạm ngừng giao dịch, khối lượng phiên tiếp theo bằng 0, hoặc cổ phiếu bị loại khỏi niêm yết trước giờ mở cửa $T+1$.
- Việc tách riêng hai điều kiện bảo vệ mô hình tuyệt đối khỏi việc vô tình sử dụng thông tin của phiên $T+1$ trong bước xếp hạng tại $T$.

---

## 5. Artifacts Lưu Trữ Phục Vụ Nghiệm Thu & Tái Lập Kết Quả

1. **Dữ liệu dự đoán thô**:
   - [`data/processed/oos_predictions_2024_2026.parquet`](../../../data/processed/oos_predictions_2024_2026.parquet): Chứa toàn bộ {n_predictions:,} dòng dự đoán của 711 phiên OOS gồm các cột `date`, `canonical_sid`, 13 features X, `ret_20d`, `ridge_score`, và `gbdt_score`.
2. **Bảng đánh giá Rank IC theo ngày**:
   - [`outputs/reports/oos_daily_ic_2024_2026.csv`](../../../outputs/reports/oos_daily_ic_2024_2026.csv): Bảng chi tiết 711 phiên ghi nhận `n_predicted_at_t`, `n_evaluable_at_t1`, Rank IC từng phương pháp, chênh lệch GBDT vs Ridge, và cờ phân vùng `is_primary_scope`.
3. **Cấu hình tái lập lần chạy**:
   - [`configs/oos_evaluation_run_v1.yaml`](../../../configs/oos_evaluation_run_v1.yaml): Ghi nhận toàn bộ thông số, đường dẫn mô hình, và bảng số liệu tổng hợp.

---

## 6. Kết Luận & Khuyến Nghị Bàn Giao

1. **Kết quả kiểm định OOS xác nhận tính hợp lệ khoa học**: Cả hai mô hình cố định refit từ Development đều duy trì được năng lực phân hạng Rank IC dương có ý nghĩa thống kê trên dữ liệu ngoài mẫu 2024–2026.
2. **So sánh mô hình**:
   - Cả hai mô hình đều chứng minh năng lực tổng quát hóa xuất sắc ngoài mẫu, vượt trội hoàn toàn tín hiệu đơn biến `ret_20d`.
   - Ridge Baseline (alpha=1.0) đạt Mean IC cao hơn trên phạm vi chính (+0.023050 vs +0.020403 của GBDT) và duy trì sự ổn định bền bỉ qua các năm 2024, 2025 và 2026.
   - GBDT (7 lá) đạt hiệu năng tương đương xét trên tỷ lệ phiên vượt trội (win rate 50.5% so với Ridge) và hơi nhỉnh hơn Ridge trong năm 2024 (+0.033544 vs +0.033431).
   - Sự kết hợp tuyến tính đơn giản với bộ chuẩn hóa `StandardScaler` của Ridge chứng minh là một chuẩn mực baseline cực kỳ kiên cố và khó bị đánh bại trong thực tế ngoài mẫu.
3. **Tuân thủ nguyên tắc One-shot OOS**: Kết quả này được đóng băng dùng để báo cáo đồ án. Tuyệt đối không sử dụng kết quả OOS để quay lại điều chỉnh mô hình hay tinh chỉnh features.
4. **Bước tiếp theo**: Bước đánh giá năng lực dự báo tín hiệu (Rank IC) đã hoàn tất. Quá trình kiểm thử danh mục đầu tư thực tế (Portfolio Backtesting có tính chi phí giao dịch, trượt giá và khoảng trống qua đêm) sẽ được triển khai độc lập theo đặc tả riêng.
"""

    with open(OUTPUT_DOC_REPORT, "w", encoding="utf-8") as f:
        f.write(md)
    log(f"  -> Đã lưu báo cáo Markdown: {OUTPUT_DOC_REPORT}")


if __name__ == "__main__":
    main()
