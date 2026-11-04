"""Performance evaluation metrics: Annualized Return, Sharpe Ratio, Drawdown, and Turnover."""
from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_pnl_series(
    weights: pd.DataFrame,
    forward_returns: pd.DataFrame,
    transaction_cost_bps: float = 5.0
) -> pd.DataFrame:
    """
    Computes daily portfolio returns, turnover, and transaction costs.
    
    Formula:
      Gross Daily Return: R_t = sum_i(w_{i, t} * r_{i, t+1})
      Turnover: Turnover_t = sum_i |w_{i, t} - w_{i, t-1}|
      Cost_t = Turnover_t * (transaction_cost_bps / 10,000)
      Net Daily Return: Net_t = R_t - Cost_t
    """
    # Align dates
    common_dates = weights.index.intersection(forward_returns.index)
    w = weights.loc[common_dates]
    r = forward_returns.loc[common_dates]

    # Gross return: sum over cross-section
    gross_returns = (w * r).sum(axis=1)

    # Turnover
    w_prev = w.shift(1).fillna(0.0)
    turnover = (w - w_prev).abs().sum(axis=1)

    # Transaction cost in return percentage
    cost = turnover * (transaction_cost_bps / 10000.0)
    net_returns = gross_returns - cost

    result = pd.DataFrame({
        "gross_return": gross_returns,
        "turnover": turnover,
        "cost": cost,
        "net_return": net_returns,
        "cum_net_return": (1.0 + net_returns).cumprod() - 1.0
    }, index=common_dates)

    return result


def calculate_performance_metrics(
    daily_returns: pd.Series,
    annualization_factor: int = 252
) -> Dict[str, float]:
    """
    Calculates key performance metrics per instructor requirements:
    - Annualized Return
    - Sharpe Ratio (return / volatility * sqrt(252))
    - Annualized Volatility
    - Maximum Drawdown (MDD)
    - Win Rate
    """
    clean_ret = daily_returns.dropna()
    if len(clean_ret) < 2:
        return {
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trading_days": len(clean_ret)
        }

    mean_daily = clean_ret.mean()
    std_daily = clean_ret.std()

    ann_return = mean_daily * annualization_factor
    ann_vol = std_daily * np.sqrt(annualization_factor)

    sharpe = (ann_return / ann_vol) if ann_vol > 1e-8 else 0.0

    # Drawdown
    cum_returns = (1.0 + clean_ret).cumprod()
    peak = cum_returns.cummax()
    drawdown = (cum_returns - peak) / peak
    max_drawdown = float(drawdown.min())

    # Win rate
    win_rate = float((clean_ret > 0).mean())

    return {
        "annualized_return": float(ann_return),
        "annualized_volatility": float(ann_vol),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "win_rate": float(win_rate),
        "total_trading_days": int(len(clean_ret))
    }
