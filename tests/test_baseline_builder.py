"""
Tests for Baseline Dataset v1 Builder Logic and Target Ranking
============================================================
Xác thực:
1. Logic xếp hạng target rank chuẩn hóa [0, 1], xử lý ties, N=1 -> 0.5, N=0 -> NaN (Portable test).
2. 17 cột dữ liệu theo đúng schema và dtypes, toàn bộ hữu hạn, không trùng (date, canonical_sid) (@pytest.mark.integration).
3. Nguyên tắc No Re-ranking: target_rank của các mã đủ X giữ nguyên giá trị khi loại bỏ mã thiếu X (@pytest.mark.integration).
4. Phân biệt rõ Inference Eligibility tại T và Training Eligibility (ví dụ ca CCB và phiên purge 2023-12-29) (@pytest.mark.integration).
5. Cơ chế predicate pushdown từ chối ngày ngoài Development window (@pytest.mark.integration).
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Đảm bảo đường dẫn import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load module dynamically because directory and file start with numbers
script_path = PROJECT_ROOT / "scripts" / "01_pipeline" / "16_build_baseline_dataset_sample.py"
spec = importlib.util.spec_from_file_location("baseline_sample_builder", str(script_path))
builder_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder_mod)

BASELINE_13_FEATURES = builder_mod.BASELINE_13_FEATURES
SCHEMA_17_COLUMNS = builder_mod.SCHEMA_17_COLUMNS
build_baseline_sample = builder_mod.build_baseline_sample
compute_cross_sectional_target_rank = builder_mod.compute_cross_sectional_target_rank
demonstrate_rank_stability = builder_mod.demonstrate_rank_stability


def test_target_rank_math_properties():
    """Kiểm tra đặc tính toán học của hàm compute_cross_sectional_target_rank (Portable)."""
    # 1. Trường hợp bình thường 5 giá trị phân biệt
    s = pd.Series([-0.05, -0.01, 0.00, 0.02, 0.10], index=["A", "B", "C", "D", "E"])
    r = compute_cross_sectional_target_rank(s)
    assert r["A"] == pytest.approx(0.0)
    assert r["C"] == pytest.approx(0.5)
    assert r["E"] == pytest.approx(1.0)
    assert len(r) == 5

    # 2. Xử lý đồng hạng (ties) bằng method='average'
    s_ties = pd.Series([-0.02, 0.01, 0.01, 0.05], index=["W", "X", "Y", "Z"])
    # ranks: W=1, X=2.5, Y=2.5, Z=4. Normalized: (rank-1)/(4-1)
    # W -> 0/3 = 0.0, X,Y -> 1.5/3 = 0.5, Z -> 3/3 = 1.0
    r_ties = compute_cross_sectional_target_rank(s_ties)
    assert r_ties["W"] == pytest.approx(0.0)
    assert r_ties["X"] == pytest.approx(0.5)
    assert r_ties["Y"] == pytest.approx(0.5)
    assert r_ties["Z"] == pytest.approx(1.0)

    # 3. Biên N = 1 -> gán 0.5
    s_one = pd.Series([0.03], index=["SOLO"])
    r_one = compute_cross_sectional_target_rank(s_one)
    assert r_one["SOLO"] == pytest.approx(0.5)

    # 4. Biên N = 0 (hoặc toàn NaN) -> trả về Series rỗng / NaN
    s_empty = pd.Series([np.nan, np.nan], index=["N1", "N2"])
    r_empty = compute_cross_sectional_target_rank(s_empty)
    assert len(r_empty) == 0 or r_empty.isna().all()


@pytest.mark.integration
def test_schema_and_complete_case_integrity():
    """Kiểm tra cấu trúc schema 17 cột, không null, không trùng lặp và tính hữu hạn của complete-case training set."""
    test_dates = [pd.Timestamp("2000-07-03"), pd.Timestamp("2015-06-15")]
    df_train, stats = build_baseline_sample(test_dates, filter_training_only=True)

    # 1. Kiểm tra 17 cột
    assert list(df_train.columns) == SCHEMA_17_COLUMNS
    assert len(df_train.columns) == 17

    # 2. Kiểm tra không có bất kỳ ô NaN nào trong tập training
    assert df_train.isna().sum().sum() == 0

    # 3. Kiểm tra toàn bộ các cột số đều hữu hạn (np.isfinite)
    for col in BASELINE_13_FEATURES + ["target_return", "target_rank"]:
        assert np.isfinite(df_train[col]).all()

    # 4. Kiểm tra target_rank luôn thuộc [0.0, 1.0]
    assert (df_train["target_rank"] >= 0.0).all()
    assert (df_train["target_rank"] <= 1.0).all()

    # 5. Kiểm tra không trùng lặp cặp (date, canonical_sid)
    assert df_train.duplicated(subset=["date", "canonical_sid"]).sum() == 0

    # 6. Kiểm tra sắp xếp tăng dần theo date và canonical_sid
    is_sorted = df_train[["date", "canonical_sid"]].equals(
        df_train[["date", "canonical_sid"]].sort_values(["date", "canonical_sid"]).reset_index(drop=True)
    )
    assert is_sorted


@pytest.mark.integration
def test_rank_stability_empirical():
    """Kiểm tra thực nghiệm: rank của các mã đủ X không bị thay đổi khi loại mã thiếu X."""
    d = pd.Timestamp("2000-07-03")
    stability = demonstrate_rank_stability(d)

    assert stability["n_label"] == 931
    assert stability["n_train"] == 862
    assert stability["n_dropped_missing_x"] == 69

    # Nếu tính lại rank trên 862 mã, độ lệch tối đa là hơn 1% (> 0.01)
    assert stability["max_rank_distortion"] > 0.009
    assert stability["mean_rank_distortion"] > 0.003
    assert stability["sample_missing_stock"] == "A RPTMYV3VC57P"


@pytest.mark.integration
def test_purge_date_2023_12_29():
    """Kiểm tra ngày kết thúc Development 2023-12-29: Inference-eligible > 0 nhưng Training-eligible == 0."""
    d = pd.Timestamp("2023-12-29")
    df_audit, stats = build_baseline_sample([d], filter_training_only=False)

    day_stat = stats["2023-12-29"]
    assert day_stat["strict_membership_count"] == 984
    assert day_stat["label_ranked_count"] == 0
    assert day_stat["inference_eligible_count"] == 978
    assert day_stat["training_eligible_count"] == 0
    assert day_stat["inference_eligible_no_label_count"] == 978

    # Toàn bộ target_return và target_rank trong ngày này phải là NaN
    assert df_audit["target_return"].isna().all()
    assert df_audit["target_rank"].isna().all()


@pytest.mark.integration
def test_coordinate_cases_2000_07_03():
    """Kiểm tra chi tiết 3 ca tọa độ tiêu biểu tại ngày 2000-07-03."""
    d = pd.Timestamp("2000-07-03")
    df_audit, _ = build_baseline_sample([d], filter_training_only=False)

    # Ca 1: A RPTMYV3VC57P có nhãn nhưng thiếu mom_12m
    row_a = df_audit[df_audit["canonical_sid"] == "A RPTMYV3VC57P"].iloc[0]
    assert np.isnan(row_a["mom_12m_skip_1m"])
    assert np.isfinite(row_a["target_return"])
    assert np.isfinite(row_a["target_rank"])
    assert row_a["is_u_label"] == True
    assert row_a["is_inference_eligible"] == False
    assert row_a["is_training_eligible"] == False

    # Ca 2: CCB R735QTJ8XC9X đủ 13 X nhưng volume phiên kế tiếp bằng 0 nên nhãn bị loại theo chính sách hiện tại
    row_ccb = df_audit[df_audit["canonical_sid"] == "CCB R735QTJ8XC9X"].iloc[0]
    assert row_ccb["all_13_features_valid"] == True
    assert np.isnan(row_ccb["target_return"])
    assert np.isnan(row_ccb["target_rank"])
    assert row_ccb["is_inference_eligible"] == True
    assert row_ccb["is_training_eligible"] == False

    # Ca 3: AAPL R735QTJ8XC9X hoàn chỉnh
    row_aapl = df_audit[df_audit["canonical_sid"] == "AAPL R735QTJ8XC9X"].iloc[0]
    assert row_aapl["all_13_features_valid"] == True
    assert np.isfinite(row_aapl["target_return"])
    assert np.isfinite(row_aapl["target_rank"])
    assert row_aapl["is_inference_eligible"] == True
    assert row_aapl["is_training_eligible"] == True


@pytest.mark.integration
def test_out_of_development_date_rejection():
    """Kiểm tra builder từ chối các ngày ngoài Development window trước khi đọc disk."""
    oos_date = pd.Timestamp("2024-01-02")
    with pytest.raises((ValueError, Exception)):
        build_baseline_sample([oos_date])


@pytest.mark.integration
def test_full_baseline_dataset_production_parquet():
    """Kiểm tra file Parquet hoàn chỉnh của Dataset Baseline v1 trên đĩa."""
    import pyarrow.parquet as pq

    prod_file = PROJECT_ROOT / "data" / "processed" / "baseline_dataset_v1.parquet"
    if not prod_file.exists():
        pytest.skip("Chưa sinh file baseline_dataset_v1.parquet đầy đủ.")

    pfile = pq.ParquetFile(prod_file)
    schema = pfile.schema_arrow

    # 1. Đúng 17 cột
    assert schema.names == SCHEMA_17_COLUMNS
    assert len(schema.names) == 17

    # 2. Đúng 5.514.324 dòng
    assert pfile.metadata.num_rows == 5514324
