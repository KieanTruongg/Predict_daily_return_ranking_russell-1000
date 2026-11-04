"""Meta-Alpha ensemble and combination models."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.portfolio.neutralizer import neutralize_and_scale


class MetaAlphaCombiner:
    """
    Combines multiple individual alpha signals into a robust meta-strategy portfolio.
    Addresses Hedge Fund practice of aggregating a diversified book of alphas.
    """
    def __init__(self, method: str = "equal_weight", target_leverage: float = 1.0):
        self.method = method
        self.target_leverage = target_leverage

    def combine_weights(
        self,
        alpha_weights_dict: Dict[str, pd.DataFrame],
        alpha_pnl_series: Optional[Dict[str, pd.Series]] = None,
        alpha_ic_series: Optional[Dict[str, pd.Series]] = None
    ) -> pd.DataFrame:
        """
        Combines individual alpha weight matrices into an aggregated meta-portfolio weight matrix.
        
        Supported methods:
        - 'equal_weight': simple average across all alpha weights
        - 'inv_vol': weighted inversely to each strategy's historical volatility
        - 'ic_weight': weighted proportionally to each strategy's trailing Rank IC
        """
        names = list(alpha_weights_dict.keys())
        first_df = next(iter(alpha_weights_dict.values()))
        meta_weights = pd.DataFrame(0.0, index=first_df.index, columns=first_df.columns)

        if self.method == "equal_weight" or alpha_pnl_series is None:
            # Simple equal-weight combination
            w_alpha = 1.0 / len(names)
            for name, w_df in alpha_weights_dict.items():
                meta_weights = meta_weights.add(w_df.fillna(0.0) * w_alpha, fill_value=0.0)

        elif self.method == "inv_vol":
            # Compute annualized volatility of each alpha's returns
            vols = {}
            for name, pnl in alpha_pnl_series.items():
                std = pnl.std()
                vols[name] = std if (std is not None and std > 1e-6) else 1e-6
            inv_vols = {name: 1.0 / v for name, v in vols.items()}
            sum_inv_vol = sum(inv_vols.values())
            weights_per_alpha = {name: inv_vols[name] / sum_inv_vol for name in names}

            for name, w_df in alpha_weights_dict.items():
                meta_weights = meta_weights.add(w_df.fillna(0.0) * weights_per_alpha[name], fill_value=0.0)

        elif self.method == "ic_weight" and alpha_ic_series is not None:
            # Weight proportionally to positive mean IC
            mean_ics = {name: max(0.001, alpha_ic_series[name].mean()) for name in names}
            sum_ic = sum(mean_ics.values())
            weights_per_alpha = {name: mean_ics[name] / sum_ic for name in names}

            for name, w_df in alpha_weights_dict.items():
                meta_weights = meta_weights.add(w_df.fillna(0.0) * weights_per_alpha[name], fill_value=0.0)

        # Enforce long-short dollar neutrality on final combined portfolio
        final_meta = neutralize_and_scale(meta_weights, target_leverage=self.target_leverage)
        return final_meta
