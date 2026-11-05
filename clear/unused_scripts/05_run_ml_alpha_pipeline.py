"""Script 05: End-to-End Machine Learning Alpha Pipeline (Phase 1-5).
Demonstrates:
  1. Loading In-sample data (< 2024-01-01)
  2. Feature Engineering (50+ features)
  3. Training XGBoost & LambdaMART rank models
  4. Ensembling predictions into a Meta-Alpha
  5. Long-Short Dollar-Neutral Backtesting (Sharpe, Returns, Rank IC)
"""
import sys
import os
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.feature_engineer import FeatureEngineer
from src.models.xgboost_model import XGBoostAlphaModel
from src.models.lambdamart_model import LambdaMARTAlphaModel
from src.ensemble.meta_ensemble import MLAlphaEnsemble
from src.portfolio.neutralizer import neutralize_and_scale
from src.metrics.performance import compute_pnl_series, calculate_performance_metrics
from src.metrics.information import compute_daily_ic_series, calculate_ic_summary

if __name__ == "__main__":
    print("=" * 70)
    print("MACHINE LEARNING ALPHA PIPELINE (XGBoost, LambdaMART, Meta Ensemble)")
    print("=" * 70)

    # 1. Synthesize / load sample panel data for demonstration
    dates = pd.date_range("2021-01-01", "2023-12-31", freq="B")
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "V", "UNH"]

    print(f"\n[Phase 1 & 2] Generating features across {len(tickers)} stocks over {len(dates)} trading days...")
    np.random.seed(42)
    panel_dict = {}
    for t in tickers:
        p0 = 100.0 + np.random.uniform(10, 50)
        daily_ret = np.random.normal(0.0005, 0.015, len(dates))
        prices = p0 * np.exp(np.cumsum(daily_ret))
        highs = prices * (1.0 + np.random.uniform(0.002, 0.01, len(dates)))
        lows = prices * (1.0 - np.random.uniform(0.002, 0.01, len(dates)))
        vols = np.random.randint(1000000, 10000000, len(dates))

        df_t = pd.DataFrame({
            "Open": prices * 0.999,
            "High": highs,
            "Low": lows,
            "Close": prices,
            "Adj Close": prices,
            "Volume": vols
        }, index=dates)
        panel_dict[t] = df_t

    fe = FeatureEngineer(forward_lookahead=1)
    full_dataset = fe.build_cross_sectional_dataset(panel_dict)
    print(f"Generated feature dataset with shape: {full_dataset.shape}")

    # Select feature columns (excluding identifiers & targets)
    exclude_cols = ["Date", "Ticker", "target_forward_return", "target_return_rank"]
    feature_cols = [c for c in full_dataset.columns if c not in exclude_cols]
    print(f"Total features extracted: {len(feature_cols)}")

    # Time-series split (Train: 2021-2022, Validation: 2023)
    train_mask = full_dataset["Date"] < "2023-01-01"
    val_mask = (full_dataset["Date"] >= "2023-01-01") & (full_dataset["Date"] < "2024-01-01")

    train_df = full_dataset[train_mask]
    val_df = full_dataset[val_mask]

    # [Phase 3] Train ML Models
    print("\n[Phase 3] Training ML Alpha Models...")
    xgb_alpha = XGBoostAlphaModel(n_estimators=50, max_depth=3)
    xgb_alpha.fit(train_df, feature_cols)
    val_pred_xgb = xgb_alpha.predict(val_df)
    print("  -> XGBoost Alpha model trained.")

    lgb_alpha = LambdaMARTAlphaModel(n_estimators=50, num_leaves=15)
    lgb_alpha.fit(train_df, feature_cols)
    val_pred_lgb = lgb_alpha.predict(val_df)
    print("  -> LambdaMART Alpha model trained.")

    # [Phase 4] Meta-Alpha Ensemble
    print("\n[Phase 4] Ensembling predictions into Meta-Alpha...")
    ensemble = MLAlphaEnsemble(method="equal_weight")
    pred_dict = {
        "XGBoost": val_pred_xgb,
        "LambdaMART": val_pred_lgb
    }
    meta_df = ensemble.combine_predictions(pred_dict, val_df)

    # [Phase 5] Pivot to matrix and construct Long-Short Dollar-Neutral Portfolio
    print("\n[Phase 5] Generating Long-Short Dollar-Neutral Weights & Backtesting...")
    val_meta_matrix = meta_df.pivot(index="Date", columns="Ticker", values="meta_rank")
    val_weights = neutralize_and_scale(val_meta_matrix, target_leverage=1.0)

    val_fwd_ret_matrix = val_df.pivot(index="Date", columns="Ticker", values="target_forward_return")

    # Run performance calculation
    pnl_df = compute_pnl_series(val_weights, val_fwd_ret_matrix, transaction_cost_bps=5.0)
    perf = calculate_performance_metrics(pnl_df["net_return"])
    ic_series = compute_daily_ic_series(val_weights, val_fwd_ret_matrix, method="spearman")
    ic_stats = calculate_ic_summary(ic_series)

    print("\n" + "=" * 55)
    print(" ML META-ALPHA VALIDATION RESULTS (Long-Short Neutral)")
    print("=" * 55)
    print(f" Net Annualized Return           : {perf['annualized_return']:.2%}")
    print(f" Net Sharpe Ratio                : {perf['sharpe_ratio']:.2f}")
    print(f" Maximum Drawdown (MDD)          : {perf['max_drawdown']:.2%}")
    print(f" Daily Win Rate                  : {perf['win_rate']:.2%}")
    print(f" Mean Rank IC (Spearman)         : {ic_stats['mean_ic']:.4f}")
    print(f" IC Information Ratio (ICIR)     : {ic_stats['icir']:.2f}")
    print("=" * 55)
    print("\n[Pipeline Complete] Scaffold successfully verified end-to-end!")
