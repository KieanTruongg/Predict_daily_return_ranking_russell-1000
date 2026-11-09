"""Loader behavior on tiny temporary Parquet fixtures, without market data."""
from copy import deepcopy

import pandas as pd
import pytest

from src.data.matrix_loader import load_bar_quality_mask, load_matrices, load_matrix
from src.data.universe import get_active_constituents
from src.quality.quality_window import OOSFreezeViolationError
from src.utils.config import Config, load_config


@pytest.fixture
def tiny_store(tmp_path):
    raw = deepcopy(load_config().raw)
    raw["data"]["matrices_dir"] = str(tmp_path)
    config = Config(raw, tmp_path / "config.yaml")
    dates = pd.to_datetime([
        "1998-01-02", "2000-07-03", "2023-12-28", "2023-12-29", "2024-01-02",
    ])
    prices = pd.DataFrame({"SYNTHETIC_SID": [100., 101., 102., 103., 104.]}, index=dates)
    prices.to_parquet(tmp_path / "adj_close.parquet")
    return config, prices, tmp_path


@pytest.mark.parametrize("warmup,expected_rows", [(False, 3), (True, 4)])
def test_development_slice_from_temporary_parquet(tiny_store, warmup, expected_rows):
    config, prices, _ = tiny_store
    loaded = load_matrix("adj_close", dev_only=True, include_warmup=warmup, config=config)
    assert len(loaded) == expected_rows
    assert loaded.index[-1] == pd.Timestamp("2023-12-29")
    assert loaded.iloc[-1, 0] == prices.loc["2023-12-29"].iloc[0]
    assert loaded.index[0] == pd.Timestamp("1998-01-02" if warmup else "2000-07-03")


def test_oos_access_requires_explicit_authorization(tiny_store):
    config, prices, _ = tiny_store
    with pytest.raises(OOSFreezeViolationError):
        load_matrix("adj_close", config=config)
    allowed = load_matrix("adj_close", allow_oos=True, config=config)
    assert allowed.index.equals(prices.index)


def test_multi_matrix_loading_rejects_misaligned_dates(tiny_store):
    config, prices, directory = tiny_store
    prices.iloc[:-1].to_parquet(directory / "adj_volume.parquet")
    with pytest.raises(ValueError, match="index mismatch"):
        load_matrices(["adj_close", "adj_volume"], allow_oos=True, config=config)


def test_bar_quality_preserves_pre_membership_history(tiny_store):
    config, prices, directory = tiny_store
    bad = pd.DataFrame(False, index=prices.index, columns=prices.columns)
    bad.loc["2023-12-28"] = True
    bad.to_parquet(directory / "is_bad_data_period.parquet")
    pd.DataFrame(False, index=prices.index, columns=prices.columns).to_parquet(
        directory / "is_spinoff_discontinuity.parquet"
    )
    # No membership file exists; quality construction must not require it.
    quality = load_bar_quality_mask(dev_only=True, include_warmup=True, config=config)
    assert bool(quality.loc["1998-01-02"].iloc[0])
    assert not bool(quality.loc["2023-12-28"].iloc[0])
    assert bool(quality.loc["2023-12-29"].iloc[0])


def test_development_membership_query_uses_safe_slice(tiny_store):
    config, prices, directory = tiny_store
    pd.DataFrame(True, index=prices.index, columns=prices.columns).to_parquet(
        directory / "strict_membership_mask.parquet"
    )
    assert get_active_constituents("2023-12-29", config=config) == ["SYNTHETIC_SID"]
    with pytest.raises(OOSFreezeViolationError):
        get_active_constituents("2024-01-02", config=config)



def test_pushdown_passes_filters_to_read_parquet(tiny_store, monkeypatch):
    """Verify load_matrix passes date filters to pd.read_parquet when dev_only=True."""
    config, prices, _ = tiny_store

    recorded_calls = []
    orig_read_parquet = pd.read_parquet

    def spy_read_parquet(*args, **kwargs):
        recorded_calls.append({"args": args, "kwargs": kwargs})
        return orig_read_parquet(*args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", spy_read_parquet)

    # Call with dev_only=True, include_warmup=False
    load_matrix("adj_close", dev_only=True, include_warmup=False, config=config)

    assert len(recorded_calls) >= 1
    call_kwargs = recorded_calls[0]["kwargs"]
    assert "filters" in call_kwargs, "filters keyword argument must be passed to read_parquet"
    filters = call_kwargs["filters"]
    assert filters is not None
    # Check that upper bound 2023-12-29 is in filters
    upper_bounds = [f[2] for f in filters if f[1] == "<="]
    assert pd.Timestamp("2023-12-29") in upper_bounds
    # Check that lower bound 2000-07-01 is in filters
    lower_bounds = [f[2] for f in filters if f[1] == ">="]
    assert pd.Timestamp("2000-07-01") in lower_bounds


def test_pushdown_failure_raises_explicit_runtime_error_without_fallback(tiny_store, monkeypatch):
    """
    CRITICAL OOS DEFENSE:
    When predicate pushdown fails, load_matrix must raise an explicit RuntimeError.
    It must NEVER silently fall back to an unbounded full read.
    """
    config, prices, _ = tiny_store

    full_read_attempted = []

    def mock_read_parquet(*args, **kwargs):
        filters = kwargs.get("filters")
        if filters is not None:
            raise ValueError("Simulated PyArrow pushdown scanner failure")
        else:
            full_read_attempted.append(True)
            return prices

    monkeypatch.setattr(pd, "read_parquet", mock_read_parquet)

    with pytest.raises(RuntimeError) as exc_info:
        load_matrix("adj_close", dev_only=True, config=config)

    assert "Predicate pushdown failed for dev_only read" in str(exc_info.value)
    assert "Unbounded fallback read is strictly blocked" in str(exc_info.value)
    assert len(full_read_attempted) == 0, "Security violation: load_matrix attempted silent unbounded fallback read!"


def test_pushdown_missing_date_column_raises_explicit_error(tmp_path):
    """Verify load_matrix raises RuntimeError if date index column cannot be determined."""
    raw = deepcopy(load_config().raw)
    raw["data"]["matrices_dir"] = str(tmp_path)
    config = Config(raw, tmp_path / "config.yaml")

    # Create parquet without datetime index or 'date' column
    df_nodate = pd.DataFrame({"col_A": [1, 2, 3], "col_B": [4, 5, 6]})
    df_nodate.to_parquet(tmp_path / "no_date_matrix.parquet", index=False)

    with pytest.raises(RuntimeError) as exc_info:
        load_matrix("no_date_matrix", dev_only=True, config=config)

    assert "Cannot determine date index column in Parquet file" in str(exc_info.value)
