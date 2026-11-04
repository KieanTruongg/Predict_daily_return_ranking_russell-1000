"""Unit tests for long-short dollar neutrality and portfolio weight scaling."""
import numpy as np
import pandas as pd
from src.portfolio.neutralizer import neutralize_and_scale, verify_dollar_neutrality


def test_dollar_neutrality():
    # Synthetic random signals across 5 dates and 10 stocks
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    stocks = [f"STK_{i}" for i in range(10)]
    raw_signal = pd.DataFrame(np.random.randn(5, 10), index=dates, columns=stocks)

    weights = neutralize_and_scale(raw_signal, target_leverage=1.0)

    # 1. Net sum across all stocks must be zero (dollar-neutral long-short balance)
    assert verify_dollar_neutrality(weights), "Portfolio weights must sum to 0 across stocks!"

    # 2. Sum of absolute weights must equal target leverage
    l1_norm = weights.abs().sum(axis=1)
    assert np.allclose(l1_norm, 1.0), "Portfolio gross leverage must equal 1.0!"


def test_position_limit_clipping():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=3, freq="D")
    stocks = [f"STK_{i}" for i in range(100)]
    raw_signal = pd.DataFrame(np.random.randn(3, 100), index=dates, columns=stocks)

    # Impose 5% max cap per stock
    weights = neutralize_and_scale(raw_signal, target_leverage=1.0, max_stock_weight=0.05)

    assert (weights.abs() <= 0.05 + 1e-6).all().all(), "No stock position should exceed 5% cap"
    assert verify_dollar_neutrality(weights), "Neutrality must be maintained after clipping"
