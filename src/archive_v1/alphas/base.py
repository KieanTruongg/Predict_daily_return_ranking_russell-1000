"""Base Alpha class and portfolio weight generation interface."""
from abc import ABC, abstractmethod
import pandas as pd
from src.data.preprocessor import CrossSectionalDataContainer
from src.alphas.operators import cs_demean, cs_scale, cs_rank


class AlphaStrategy(ABC):
    """
    Abstract base class for quantitative alpha strategies.
    Ensures long-short dollar neutrality and consistent portfolio weighting.
    """
    def __init__(self, name: str, category: str = "general"):
        self.name = name
        self.category = category

    @abstractmethod
    def compute_raw_signal(self, data: CrossSectionalDataContainer) -> pd.DataFrame:
        """
        Computes unnormalized alpha signal for each stock and timestamp.
        Higher value indicates higher expected cross-sectional return.
        """
        pass

    def generate_weights(
        self,
        data: CrossSectionalDataContainer,
        use_rank: bool = False,
        target_leverage: float = 1.0
    ) -> pd.DataFrame:
        """
        Converts raw alpha signal into dollar-neutral, long-short balanced portfolio weights:
        1. (Optional) Cross-sectional ranking: uniform distribution in [0, 1]
        2. Demeaning: ensures sum(weights_i) == 0
        3. L1 Scaling: ensures sum(|weights_i|) == target_leverage (e.g. 50% long, 50% short)
        """
        signal = self.compute_raw_signal(data)

        if use_rank:
            signal = cs_rank(signal)

        # Demean to ensure dollar neutrality (long-short balanced)
        demeaned = cs_demean(signal)

        # Scale weights to target leverage (default: 1.0)
        weights = cs_scale(demeaned, target_leverage=target_leverage)

        return weights
