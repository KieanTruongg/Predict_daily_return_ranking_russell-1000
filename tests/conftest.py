"""Classify existing tests that require local datasets.

New data tests should use @pytest.mark.integration directly. There is no automatic
skip on missing data; pytest without -m continues to execute the full suite.
This manifest avoids editing tests shared with ongoing feature-pilot work.
"""
import pytest

LOCAL_DATA_TESTS = {
    "test_gbdt_baseline.py": {"test_gbdt_models_and_config_structure"},
    "test_gbdt_leaf_grid.py": {
        "test_gbdt_leaf_grid_config_and_models",
        "test_gbdt_leaf_grid_predictions_integrity",
        "test_gbdt_leaf_grid_daily_ic_and_summary",
    },
    "test_grid_search_ridge.py": {"test_grid_search_config_and_summary_structure"},
    "test_oos_refit_models.py": {
        "test_ridge_refit_model_integrity", "test_gbdt_refit_model_integrity",
    },
    "test_prediction_pipeline.py": {
        "test_trial_predictions_and_decoupling_integrity",
        "test_scale_verification_artifacts_and_parity",
    },
    "test_ridge_baseline.py": {"test_ridge_model_artifact_and_config"},
    "test_walk_forward_evaluation.py": {"test_walk_forward_run_config_and_models"},
    "test_library_fixes.py": {"test_03_get_active_constituents_dev_no_oos_error"},
    "test_pipeline_integrity.py": {
        "test_04_universe_extraction_output_contracts",
        "test_07_coordinate_grid_and_trading_sessions",
    },
    "test_matrix_loader.py": {
        "test_coordinate_indices", "test_trading_calendar_partition",
        "test_load_matrix_full", "test_load_matrix_dev_window",
        "test_load_matrix_dev_with_warmup", "test_oos_freeze_enforcement",
        "test_3_tier_mask_hierarchy", "test_masked_matrix_loading",
        "test_universe_mapping", "test_feature_computation_on_real_matrix",
        "test_oos_zero_memory_leakage_via_pushdown",
    },
}


def pytest_collection_modifyitems(items):
    for item in items:
        name = getattr(item, "originalname", None) or item.name
        if name in LOCAL_DATA_TESTS.get(item.path.name, set()):
            item.add_marker(pytest.mark.integration)
