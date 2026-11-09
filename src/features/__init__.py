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
from src.features.nan_classifier import (
    classify_cell_nan,
    classify_feature_nans,
    FEATURE_WINDOW_SPECS,
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
    "classify_cell_nan",
    "classify_feature_nans",
    "FEATURE_WINDOW_SPECS",
]
