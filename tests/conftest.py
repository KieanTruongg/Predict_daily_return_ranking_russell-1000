"""Classify existing tests that require local datasets.

New data tests should use @pytest.mark.integration directly. There is no automatic
skip on missing data; pytest without -m continues to execute the full suite.
This manifest avoids editing tests shared with ongoing feature-pilot work.
"""
import pytest

LOCAL_DATA_TESTS = {
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
        "test_feature_computation_on_real_matrix",
    },
}


def pytest_collection_modifyitems(items):
    for item in items:
        name = getattr(item, "originalname", None) or item.name
        if name in LOCAL_DATA_TESTS.get(item.path.name, set()):
            item.add_marker(pytest.mark.integration)
