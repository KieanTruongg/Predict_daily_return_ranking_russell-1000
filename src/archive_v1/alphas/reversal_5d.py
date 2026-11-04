"""Benchmark 5-Day Reversal Alpha as specified in the instructor prompt."""
import pandas as pd
from src.alphas.base import AlphaStrategy
from src.data.preprocessor import CrossSectionalDataContainer
from src.alphas.operators import cs_demean, cs_scale


class Reversal5D(AlphaStrategy):
    """
    Classic 5-day Mean Reversal Strategy.
    
    Formula:
        alpha_i = (price[i, t-5] - price[i, t-1]) / 5
        mean = mean(alpha_i)
        alpha_i = alpha_i - mean   (so sum(alpha_i) == 0, dollar-neutral long-short)
    
    Economic intuition:
        Stocks that lost relative value over the last 5 days (price[t-5] > price[t-1])
        tend to rebound (reversal motif), so we buy them (positive alpha).
        Stocks that gained over the last 5 days tend to pull back, so we short them.
    """
    def __init__(self, lookback: int = 5):
        super().__init__(name="Alpha_01_Reversal_5D", category="short_term_reversal")
        self.lookback = lookback

    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        """
        Computes alpha_i = (P_{t - lookback} - P_{t - 1}) / lookback.
        Uses Adjusted Close to account for dividends and stock splits.
        """
        price = data.adj_close
        price_t_minus_5 = price.shift(self.lookback)
        price_t_minus_1 = price.shift(1)

        raw_alpha = (price_t_minus_5 - price_t_minus_1) / self.lookback
        return raw_alpha

    def compute_instructor_positions(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        """
        Computes the exact positions following the instructor's formula:
        alpha_i = (price[i, -5] - price[i, -1]) / 5
        mean = mean(alpha_i)
        alpha_i = alpha_i - mean
        -> sum(alpha_i) == 0
        """
        raw_alpha = self.compute_raw_signal(data)
        demeaned_alpha = cs_demean(raw_alpha)
        # Scaled to L1 = 1.0 for risk-managed portfolio execution
        scaled_alpha = cs_scale(demeaned_alpha, target_leverage=1.0)
        return scaled_alpha
