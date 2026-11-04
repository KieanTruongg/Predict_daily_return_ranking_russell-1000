"""Unit tests for Sharpe ratio, PnL computation, and Information Coefficient."""
import numpy as np
import pandas as pd
from src.metrics.performance import calculate_performance_metrics, compute_pnl_series
from src.metrics.information import compute_daily_ic_series, calculate_ic_summary


def test_performance_metrics():
    # Constant positive return series
    daily_ret = pd.Series([0.001] * 252)
    metrics = calculate_performance_metrics(daily_ret, annualization_factor=252)

    assert np.isclose(metrics["annualized_return"], 0.252)
    assert np.isclose(metrics["annualized_volatility"], 0.0, atol=1e-6)
    assert metrics["win_rate"] == 1.0


def test_daily_ic():
    dates = pd.date_range("2023-01-01", periods=2, freq="D")
    tickers = [f"T{i}" for i in range(20)]

    # Perfectly correlated signals and returns
    signals = pd.DataFrame([range(20), range(20)], index=dates, columns=tickers, dtype=float)
    forward_returns = pd.DataFrame([range(20), range(20)], index=dates, columns=tickers, dtype=float)

    ic = compute_daily_ic_series(signals, forward_returns, method="spearman")
    assert np.allclose(ic.values, 1.0)
