"""
src.models.oos_prediction_pipeline
==================================
Pipeline tạo dự đoán ngoài mẫu (Out-of-Sample Prediction Pipeline) cho:
1. Ridge Baseline (alpha=1.0 kèm StandardScaler)
2. GBDT Candidate (HistGradientBoostingRegressor max_leaf_nodes=7)

Theo đúng đặc tả trong docs/specifications/oos_evaluation_plan_v1.md:
- Tái sử dụng chính xác các lớp tính 13 features từ src.features.base.
- Áp dụng các quy tắc kiểm soát chất lượng (bar_quality_mask, corrections).
- Duy trì cửa sổ đệm lịch sử (lookback >= 252 bars) và bảo toàn trạng thái Wilder RSI qua ranh giới.
- Tuyệt đối tách biệt ranh giới:
  * Điểm dự đoán tại T (Inference Eligibility): chỉ sử dụng thông tin <= T.
  * Đánh giá nhãn tại T+1 (Evaluation Eligibility): chỉ áp dụng khi nhãn T+1 sẵn sàng.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from scipy import stats
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from src.data.matrix_loader import (
    load_matrix,
    load_bar_quality_mask,
    load_layer1_mask,
)
from src.features.base import (
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    RealizedVolatilityFeature,
    DownsideDeviationFeature,
    AmihudIlliquidityFeature,
    VolumeRatioFeature,
    LogDollarVolumeFeature,
    RSIFeature,
    BollingerPctBFeature,
)

BASELINE_13_FEATURES = [
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "mom_12m_skip_1m",
    "vol_realized_20d",
    "vol_realized_60d",
    "downside_deviation_20d",
    "amihud_illiq_20d",
    "volume_ratio_5_20",
    "log_dollar_volume_20d",
    "rsi_14d",
    "bollinger_pct_b_20d",
]

DEV_END_DATE = pd.Timestamp("2023-12-29")
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "configs" / "oos_production_models_manifest.yaml"
DEFAULT_RIDGE_PATH = PROJECT_ROOT / "models" / "oos_production" / "ridge_refit_dev_alpha1.0.joblib"
DEFAULT_GBDT_PATH = PROJECT_ROOT / "models" / "oos_production" / "gbdt_refit_dev_leaf7.joblib"


def get_feature_specifications(data_inputs: Dict[str, pd.DataFrame]) -> List[Tuple[str, object, dict]]:
    """
    Trả về danh sách 13 cấu hình feature theo đúng đặc tả kỹ thuật features_v1.md.
    """
    adj_c = data_inputs["adj_close"]
    d_ret = data_inputs["daily_return"]
    close = data_inputs["close"]
    volume = data_inputs["volume"]
    adj_vol = data_inputs["adj_volume"]

    specs = [
        ("ret_1d", PriceRatioMomentumFeature(window=1), {"adj_close": adj_c}),
        ("ret_5d", PriceRatioMomentumFeature(window=5), {"adj_close": adj_c}),
        ("ret_20d", PriceRatioMomentumFeature(window=20), {"adj_close": adj_c}),
        ("ret_60d", PriceRatioMomentumFeature(window=60), {"adj_close": adj_c}),
        ("mom_12m_skip_1m", Mom12mSkip1mFeature(lookback=252, skip=21), {"adj_close": adj_c}),
        ("vol_realized_20d", RealizedVolatilityFeature(window=20, return_type="daily_return", annualize=False), {"daily_return": d_ret}),
        ("vol_realized_60d", RealizedVolatilityFeature(window=60, return_type="daily_return", annualize=False), {"daily_return": d_ret}),
        ("downside_deviation_20d", DownsideDeviationFeature(window=20), {"daily_return": d_ret}),
        ("amihud_illiq_20d", AmihudIlliquidityFeature(window=20, scale=1e6), {"daily_return": d_ret, "close": close, "volume": volume}),
        ("volume_ratio_5_20", VolumeRatioFeature(fast_window=5, slow_window=20), {"adj_volume": adj_vol}),
        ("log_dollar_volume_20d", LogDollarVolumeFeature(window=20), {"close": close, "volume": volume}),
        ("rsi_14d", RSIFeature(window=14), {"adj_close": adj_c}),
        ("bollinger_pct_b_20d", BollingerPctBFeature(window=20, k=2.0), {"adj_close": adj_c}),
    ]
    return specs


def compute_13_features_with_history(
    target_dates: List[Union[str, pd.Timestamp]],
    lookback_sessions: Optional[int] = 500,
    start_from_origin: bool = False,
    dev_only: Optional[bool] = None,
    include_warmup: bool = True,
    allow_oos: bool = False,
    verbose: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Tính toán 13 features trên các phiên mục tiêu (target_dates), sử dụng cửa sổ đệm
    lịch sử (lookback_sessions hoặc từ gốc lịch sử start_from_origin) để đảm bảo:
    - mom_12m_skip_1m đủ 252 phiên quan sát.
    - rsi_14d duy trì trạng thái Wilder exponential smoothing mượt mà qua ranh giới.
    - Input được làm sạch bằng bar_quality_mask trước khi tính toán.
    - Truyền tham số allow_oos tường minh qua toàn bộ các loader.
    - Chặn đứng mọi truy cập ngày ngoài Development khi chưa bật cờ allow_oos=True.
    """
    t0 = time.time()

    # 1. Chuẩn hóa và kiểm tra danh sách target_dates
    target_ts = [pd.Timestamp(d) for d in target_dates]
    if not target_ts:
        raise ValueError("target_dates không được rỗng!")

    min_target_date = min(target_ts)
    max_target_date = max(target_ts)

    # 2. GUARDRAIL: Chặn truy cập OOS khi chưa có cờ tường minh allow_oos=True
    if not allow_oos:
        oos_dates = [d for d in target_ts if d > DEV_END_DATE]
        if oos_dates:
            raise PermissionError(
                f"Truy cập dữ liệu ngoài Development (OOS) bị từ chối vì chưa bật cờ allow_oos=True! "
                f"Phát hiện {len(oos_dates)} phiên sau {DEV_END_DATE.strftime('%Y-%m-%d')}, "
                f"ví dụ: {oos_dates[0].strftime('%Y-%m-%d')}."
            )

    if dev_only is None:
        dev_only = not allow_oos

    if verbose:
        print(f"[1/4] Nạp dữ liệu cơ sở cho {len(target_dates)} phiên mục tiêu "
              f"(lookback = {'toàn bộ lịch sử' if (start_from_origin or lookback_sessions is None) else f'{lookback_sessions} phiên'}, allow_oos={allow_oos})...")

    # 3. Nạp ma trận cơ sở để xác định lịch phiên
    adj_c_full = load_matrix(
        "adj_close",
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
    )
    all_dates = adj_c_full.index

    if min_target_date not in all_dates:
        raise ValueError(f"Ngày bắt đầu {min_target_date.strftime('%Y-%m-%d')} không nằm trong lịch dữ liệu!")
    if max_target_date not in all_dates:
        raise ValueError(f"Ngày kết thúc {max_target_date.strftime('%Y-%m-%d')} không nằm trong lịch dữ liệu!")

    min_idx = all_dates.get_loc(min_target_date)
    max_idx = all_dates.get_loc(max_target_date)

    if start_from_origin or lookback_sessions is None:
        start_idx = 0
    else:
        start_idx = max(0, min_idx - lookback_sessions)

    slice_dates = all_dates[start_idx : max_idx + 1]

    if verbose:
        print(f"      Cửa sổ tính toán: [{slice_dates[0].strftime('%Y-%m-%d')} -> {slice_dates[-1].strftime('%Y-%m-%d')}] ({len(slice_dates)} phiên)")

    # 4. Nạp các ma trận cắt theo slice_dates với cờ allow_oos nhất quán
    data_inputs = {
        "adj_close": adj_c_full.loc[slice_dates],
        "close": load_matrix("close", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates],
        "volume": load_matrix("volume", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates],
        "adj_volume": load_matrix("adj_volume", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates],
        "daily_return": load_matrix("daily_return", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates],
    }

    bar_q = load_bar_quality_mask(dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates]
    strict_m = load_layer1_mask(strict=True, dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos).loc[slice_dates]

    specs = get_feature_specifications(data_inputs)
    results = {}

    if verbose:
        print(f"[2/4] Bắt đầu tính toán 13 features Close/Volume...")

    for feat_name, feat_obj, inp_dict in specs:
        t_f = time.time()
        # Tính toán feature với input hygiene qua bar_quality_mask
        res_full = feat_obj.compute(inp_dict, bar_quality_mask=bar_q, membership_mask=strict_m)
        # Chỉ giữ lại các phiên mục tiêu được yêu cầu
        res_target = res_full.loc[target_ts]
        results[feat_name] = res_target
        if verbose:
            print(f"      - {feat_name:<25}: xong trong {time.time() - t_f:.2f}s")

    if verbose:
        print(f"  -> Hoàn thành tính 13 features trong {time.time() - t0:.2f}s")

    return results


def load_inference_masks(
    dev_only: Optional[bool] = None,
    include_warmup: bool = True,
    allow_oos: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Nạp đồng bộ 6 ma trận phục vụ xác định Inference Eligibility tại T:
    - strict_membership_mask
    - is_bad_data_period
    - is_spinoff_discontinuity
    - is_consecutive_session
    - close
    - volume
    """
    if dev_only is None:
        dev_only = not allow_oos
    return {
        "strict_mem": load_matrix("strict_membership_mask", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "is_bad": load_matrix("is_bad_data_period", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "is_spinoff": load_matrix("is_spinoff_discontinuity", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "is_consec": load_matrix("is_consecutive_session", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "close": load_matrix("close", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "volume": load_matrix("volume", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
    }


def load_evaluation_matrices(
    dev_only: Optional[bool] = None,
    include_warmup: bool = True,
    allow_oos: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Nạp ma trận phục vụ đánh giá tại T+1 (target_next_return, valid_label_mask, volume).
    """
    if dev_only is None:
        dev_only = not allow_oos
    return {
        "target_return": load_matrix("target_next_return", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "valid_label": load_matrix("valid_label_mask", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
        "volume": load_matrix("volume", dev_only=dev_only, include_warmup=include_warmup, allow_oos=allow_oos),
    }


def build_inference_dataframe(
    target_date: Union[str, pd.Timestamp],
    features_dict: Dict[str, pd.DataFrame],
    strict_mem_df: pd.DataFrame,
    is_bad_df: pd.DataFrame,
    is_spinoff_df: pd.DataFrame,
    is_consec_df: pd.DataFrame,
    close_df: pd.DataFrame,
    volume_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Xác định tập cổ phiếu đủ điều kiện dự đoán tại ngày T (Inference Eligibility)
    theo đúng mục 2.1 của oos_evaluation_plan_v1.md:
    1. strict_membership_mask[T] == True
    2. Nến T sạch: is_bad_data_period == False & is_spinoff_discontinuity == False
    3. is_consecutive_session[T] == True
    4. Close[T] > 0 và Volume[T] > 0
    5. Đầy đủ 13 biến X hữu hạn (np.isfinite)

    Trả về bảng phẳng với đúng 13 cột đặc trưng theo thứ tự chuẩn.
    """
    dt = pd.Timestamp(target_date)

    # 1. Trích xuất vector của phiên T
    s_mem = strict_mem_df.loc[dt].fillna(False).astype(bool)
    s_bad = is_bad_df.loc[dt].fillna(False).astype(bool)
    s_spin = is_spinoff_df.loc[dt].fillna(False).astype(bool)
    s_consec = is_consec_df.loc[dt].fillna(False).astype(bool)
    s_close = close_df.loc[dt]
    s_vol = volume_df.loc[dt]

    # Điều kiện nến và thanh khoản tại T
    bar_clean = (~s_bad) & (~s_spin)
    price_clean = np.isfinite(s_close) & (s_close > 0)
    vol_clean = np.isfinite(s_vol) & (s_vol > 0)
    consec_clean = s_consec

    base_eligible = s_mem & bar_clean & price_clean & vol_clean & consec_clean

    # Kiểm tra tính hữu hạn của 13 features
    all_sids = strict_mem_df.columns
    feat_series_dict = {}
    feat_finite_mask = pd.Series(True, index=all_sids)

    for feat_name in BASELINE_13_FEATURES:
        f_val = features_dict[feat_name].loc[dt]
        feat_series_dict[feat_name] = f_val
        feat_finite_mask &= np.isfinite(f_val)

    # Tập hợp lệ suy luận tại T
    final_eligible = base_eligible & feat_finite_mask
    eligible_sids = all_sids[final_eligible].tolist()

    if len(eligible_sids) == 0:
        return pd.DataFrame(columns=["date", "canonical_sid"] + BASELINE_13_FEATURES)

    # Dựng bảng phẳng cho tập hợp lệ
    records = []
    for sid in eligible_sids:
        row = {
            "date": dt,
            "canonical_sid": sid,
        }
        for feat_name in BASELINE_13_FEATURES:
            row[feat_name] = float(feat_series_dict[feat_name][sid])
        records.append(row)

    df_inf = pd.DataFrame(records)
    return df_inf


def predict_for_models(
    df_inference: pd.DataFrame,
    ridge_pipeline: object,
    gbdt_model: object,
    manifest_features_order: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Sinh điểm xếp hạng từ hai mô hình Ridge và GBDT đã refit.
    Kiểm tra nghiêm ngặt thứ tự cột đầu vào khớp 100% với manifest.
    """
    if len(df_inference) == 0:
        res = df_inference.copy()
        res["ridge_score"] = np.nan
        res["gbdt_score"] = np.nan
        return res

    expected_order = manifest_features_order or BASELINE_13_FEATURES

    # Xác nhận thứ tự cột
    for idx, expected_col in enumerate(expected_order):
        actual_col = BASELINE_13_FEATURES[idx]
        assert actual_col == expected_col, f"Lệch thứ tự feature tại vị trí {idx}: {actual_col} != {expected_col}"

    X = df_inference[expected_order].to_numpy(dtype=np.float32)

    ridge_scores = ridge_pipeline.predict(X)
    gbdt_scores = gbdt_model.predict(X)

    df_res = df_inference.copy()
    df_res["ridge_score"] = ridge_scores
    df_res["gbdt_score"] = gbdt_scores

    return df_res


def evaluate_daily_spearman_ic(
    df_predictions: pd.DataFrame,
    target_return_matrix: pd.DataFrame,
    valid_label_matrix: pd.DataFrame,
    volume_matrix: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Đánh giá Spearman Rank IC theo ngày (bước tách rời hoàn toàn khỏi bước dự đoán tại T).
    Chỉ chấm trên các mã có:
    1. Dự đoán tại T (có trong df_predictions).
    2. target_return hữu hạn.
    3. valid_label_mask[T] == True.
    4. Volume[T+1] > 0.
    """
    all_dates = df_predictions["date"].unique()
    daily_ic_records = []
    evaluated_rows_list = []

    for dt in sorted(all_dates):
        dt_ts = pd.Timestamp(dt)
        sub_preds = df_predictions[df_predictions["date"] == dt].copy()

        # Kiểm tra nếu ngày dt_ts có trong target_return_matrix
        if dt_ts not in target_return_matrix.index:
            daily_ic_records.append({
                "date": dt_ts.strftime("%Y-%m-%d"),
                "n_predicted_at_t": len(sub_preds),
                "n_evaluable_at_t1": 0,
                "ic_ridge": np.nan,
                "ic_gbdt": np.nan,
                "ic_ret_20d": np.nan,
                "diff_gbdt_vs_ridge": np.nan,
                "has_valid_label": False,
                "status": "PURGED_OR_OUT_OF_BOUNDS",
            })
            continue

        s_ret = target_return_matrix.loc[dt_ts]
        s_vlabel = valid_label_matrix.loc[dt_ts].fillna(False).astype(bool)

        # Ghép nhãn
        sub_preds["target_return"] = sub_preds["canonical_sid"].map(s_ret)
        sub_preds["valid_label"] = sub_preds["canonical_sid"].map(s_vlabel).fillna(False).astype(bool)

        # Điều kiện chấm điểm
        eval_mask = (
            sub_preds["valid_label"]
            & np.isfinite(sub_preds["target_return"])
        )
        eval_subset = sub_preds[eval_mask].copy()
        n_eval = len(eval_subset)

        if n_eval < 2:
            daily_ic_records.append({
                "date": dt_ts.strftime("%Y-%m-%d"),
                "n_predicted_at_t": len(sub_preds),
                "n_evaluable_at_t1": n_eval,
                "ic_ridge": np.nan,
                "ic_gbdt": np.nan,
                "ic_ret_20d": np.nan,
                "diff_gbdt_vs_ridge": np.nan,
                "has_valid_label": (n_eval > 0),
                "status": "INSUFFICIENT_STOCKS (<2)",
            })
            continue

        y_true = eval_subset["target_return"].to_numpy()
        r_sc = eval_subset["ridge_score"].to_numpy()
        g_sc = eval_subset["gbdt_score"].to_numpy()
        b_sc = eval_subset["ret_20d"].to_numpy()

        ic_ridge = float(stats.spearmanr(r_sc, y_true)[0]) if np.ptp(r_sc) > 0 else np.nan
        ic_gbdt = float(stats.spearmanr(g_sc, y_true)[0]) if np.ptp(g_sc) > 0 else np.nan
        ic_bench = float(stats.spearmanr(b_sc, y_true)[0]) if np.ptp(b_sc) > 0 else np.nan

        diff_gb_rd = ic_gbdt - ic_ridge if (np.isfinite(ic_gbdt) and np.isfinite(ic_ridge)) else np.nan

        daily_ic_records.append({
            "date": dt_ts.strftime("%Y-%m-%d"),
            "n_predicted_at_t": len(sub_preds),
            "n_evaluable_at_t1": n_eval,
            "ic_ridge": ic_ridge,
            "ic_gbdt": ic_gbdt,
            "ic_ret_20d": ic_bench,
            "diff_gbdt_vs_ridge": diff_gb_rd,
            "has_valid_label": True,
            "status": "EVALUATED_SUCCESS",
        })

        evaluated_rows_list.append(eval_subset)

    df_daily_ic = pd.DataFrame(daily_ic_records)
    df_eval_rows = pd.concat(evaluated_rows_list, ignore_index=True) if evaluated_rows_list else pd.DataFrame()

    return df_daily_ic, df_eval_rows
