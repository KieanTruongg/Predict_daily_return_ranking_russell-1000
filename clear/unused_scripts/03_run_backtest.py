"""Script 03: Run In-Sample Backtest on Candidate Alphas (e.g. 5-Day Reversal)."""
import sys
import os
import argparse
import json
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.split import load_in_sample_data
from src.alphas.reversal_5d import Reversal5D
from src.backtest.engine import BacktestEngine

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run In-Sample Alpha Backtest.")
    parser.add_argument("--cost-bps", type=float, default=5.0, help="Transaction cost in basis points (5 bps = 0.05%)")
    args = parser.parse_args()

    print("=" * 60)
    print("STEP 3: RUNNING IN-SAMPLE BACKTEST (BENCHMARK: 5-DAY REVERSAL)")
    print("Note: Evaluating strictly on In-Sample data (< 2024-01-01)")
    print("=" * 60)

    # 1. Load strictly in-sample data
    data = load_in_sample_data()
    print(f"Loaded in-sample data: {len(data.get_dates())} trading days across {len(data.get_tickers())} stocks.")

    # 2. Initialize strategy (Benchmark 5-Day Reversal)
    strategy = Reversal5D(lookback=5)

    # 3. Run backtest engine
    engine = BacktestEngine(transaction_cost_bps=args.cost_bps, target_leverage=1.0)
    report = engine.run(strategy, data)

    # 4. Display results
    print("\n" + "=" * 45)
    print(f" STRATEGY PERFORMANCE: {report['strategy_name']}")
    print("=" * 45)
    print(f" Dollar Neutral (Sum weights == 0) : {report['dollar_neutral']}")
    print(f" Total In-Sample Trading Days       : {report['trading_days']}")
    print(f" Net Annualized Return              : {report['net_annualized_return']:.2%}")
    print(f" Net Annualized Volatility          : {report['net_annualized_volatility']:.2%}")
    print(f" Net Sharpe Ratio (Return / Vol)    : {report['net_sharpe_ratio']:.3f}")
    print(f" Gross Sharpe Ratio (before fees)   : {report['gross_sharpe_ratio']:.3f}")
    print(f" Maximum Drawdown (MDD)             : {report['max_drawdown']:.2%}")
    print(f" Average Daily Turnover             : {report['average_daily_turnover']:.2%}")
    print(f" Daily Win Rate                     : {report['win_rate']:.2%}")
    print(f" Mean Rank IC (Spearman)            : {report['rank_ic_mean']:.4f}")
    print(f" IC Information Ratio (ICIR)        : {report['icir']:.3f}")
    print("=" * 45)

    # 5. Save report and plot
    fig_path = os.path.join("outputs", "figures", f"{strategy.name}_insample_pnl.png")
    engine.save_summary_plot(report, fig_path)
    print(f"\n[Saved] Performance chart saved to '{fig_path}'")

    summary_path = os.path.join("outputs", "reports", f"{strategy.name}_metrics.json")
    clean_summary = {k: v for k, v in report.items() if not isinstance(v, (pd.DataFrame, pd.Series))}
    with open(summary_path, "w") as f:
        json.dump(clean_summary, f, indent=4)
    print(f"[Saved] Metrics summary saved to '{summary_path}'")
