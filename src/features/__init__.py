"""
src.features
============
Feature engineering base abstractions and cross-sectional transforms.
All 16 features specified in docs/specifications/features_v1.md.
"""

from src.features.base import (
    FeatureBase,
    TotalReturnMomentumFeature,
    PriceRatioMomentumFeature,
    Mom12mSkip1mFeature,
    RealizedVolatilityFeature,
    ParkinsonVolatilityFeature,
    DownsideDeviationFeature,
    AmihudIlliquidityFeature,
    VolumeRatioFeature,
    LogDollarVolumeFeature,
    IntradayReturnFeature,
    OvernightReturnFeature,
    RSIFeature,
    BollingerPctBFeature,
)
from src.features.transforms import (
    cross_sectional_rank,
    cross_sectional_demean,
    cross_sectional_zscore,
    cross_sectional_winsorize,
)

__all__ = [
    "FeatureBase",
    "TotalReturnMomentumFeature",
    "PriceRatioMomentumFeature",
    "Mom12mSkip1mFeature",
    "RealizedVolatilityFeature",
    "ParkinsonVolatilityFeature",
    "DownsideDeviationFeature",
    "AmihudIlliquidityFeature",
    "VolumeRatioFeature",
    "LogDollarVolumeFeature",
    "IntradayReturnFeature",
    "OvernightReturnFeature",
    "RSIFeature",
    "BollingerPctBFeature",
    "cross_sectional_rank",
    "cross_sectional_demean",
    "cross_sectional_zscore",
    "cross_sectional_winsorize",
]
