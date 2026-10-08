"""Vectorized cross-sectional daily long-short backtesting engine."""
from typing import Dict, Any, Optional
import os
import pandas as pd
import matplotlib.pyplot as plt

from src.alphas.base import AlphaStrategy
from src.data.preprocessor import CrossSectionalDataContainer
from src.metrics.performance import compute_pnl_series, calculate_performance_metrics
from src.metrics.information import compute_daily_ic_series, calculate_ic_summary
from src.portfolio.neutralizer import verify_dollar_neutrality


class BacktestEngine:
    """
    Simulates a daily cross-sectional long-short balanced equity strategy.
    
    Evaluates:
    - PnL (Gross & Net after transaction costs)
    - Annualized Return
    - Sharpe Ratio (Return / Volatility)
    - Information Coefficient (Rank IC & ICIR)
    - Max Drawdown & Turnover
    """
    def __init__(
        self,
        transaction_cost_bps: float = 5.0,
        target_leverage: float = 1.0,
        annualization_factor: int = 252
    ):
        self.transaction_cost_bps = transaction_cost_bps
        self.target_leverage = target_leverage
        self.annualization_factor = annualization_factor

    def run(
        self,
        strategy_or_weights: Any,
        data: CrossSectionalDataContainer,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs backtest on provided data container (typically in-sample container).
        """
        if isinstance(strategy_or_weights, AlphaStrategy):
            strategy_name = strategy_or_weights.name
            weights = strategy_or_weights.generate_weights(
                data,
                target_leverage=self.target_leverage
            )
        elif isinstance(strategy_or_weights, pd.DataFrame):
            strategy_name = name or "Custom_Weights"
            weights = strategy_or_weights
        else:
            raise TypeError("Expected AlphaStrategy instance or pd.DataFrame of weights")

        # Verify dollar neutrality
        is_dollar_neutral = verify_dollar_neutrality(weights)

        # Compute PnL and turnover
        pnl_df = compute_pnl_series(
            weights=weights,
            forward_returns=data.forward_returns,
            transaction_cost_bps=self.transaction_cost_bps
        )

        # Performance metrics
        gross_metrics = calculate_performance_metrics(pnl_df["gross_return"], self.annualization_factor)
        net_metrics = calculate_performance_metrics(pnl_df["net_return"], self.annualization_factor)

        # Information coefficient
        ic_series = compute_daily_ic_series(weights, data.forward_returns, method="spearman")
        ic_summary = calculate_ic_summary(ic_series)

        avg_turnover = float(pnl_df["turnover"].mean())

        report = {
            "strategy_name": strategy_name,
            "dollar_neutral": is_dollar_neutral,
            "net_annualized_return": net_metrics["annualized_return"],
            "net_sharpe_ratio": net_metrics["sharpe_ratio"],
            "net_annualized_volatility": net_metrics["annualized_volatility"],
            "gross_sharpe_ratio": gross_metrics["sharpe_ratio"],
            "max_drawdown": net_metrics["max_drawdown"],
            "win_rate": net_metrics["win_rate"],
            "average_daily_turnover": avg_turnover,
            "rank_ic_mean": ic_summary["mean_ic"],
            "icir": ic_summary["icir"],
            "trading_days": net_metrics["total_trading_days"],
            "pnl_series": pnl_df,
            "ic_series": ic_series,
            "weights": weights
        }

        return report

    def save_summary_plot(self, report: Dict[str, Any], output_path: str):
        """Generates and saves cumulative PnL & Drawdown curve."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pnl = report["pnl_series"]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})

        # Cumulative PnL
        ax1.plot(pnl.index, (1.0 + pnl["gross_return"]).cumprod() - 1.0, label="Gross Return", color="gray", alpha=0.7)
        ax1.plot(pnl.index, pnl["cum_net_return"], label=f"Net Return (Sharpe: {report['net_sharpe_ratio']:.2f})", color="royalblue", lw=2)
        ax1.set_title(f"Backtest Performance: {report['strategy_name']} (Long-Short Balanced)", fontsize=14, fontweight="bold")
        ax1.set_ylabel("Cumulative Return")
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left")

        # Drawdown
        cum = (1.0 + pnl["net_return"]).cumprod()
        dd = (cum - cum.cummax()) / cum.cummax()
        ax2.fill_between(dd.index, dd, 0, color="crimson", alpha=0.4, label=f"Max Drawdown: {report['max_drawdown']:.1%}")
        ax2.set_ylabel("Drawdown")
        ax2.set_xlabel("Date")
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="lower left")

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
