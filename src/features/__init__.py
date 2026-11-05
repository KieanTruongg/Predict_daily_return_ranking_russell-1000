"""
src.features
============
Feature engineering base abstractions and cross-sectional transforms.
"""

from src.features.base import (
    FeatureBase,
    TotalReturnMomentumFeature,
    RealizedVolatilityFeature,
)
from src.features.v1 import FeatureV1, features_v1
from src.features.transforms import (
    cross_sectional_rank,
    cross_sectional_demean,
    cross_sectional_zscore,
    cross_sectional_winsorize,
)

__all__ = [
    "FeatureBase",
    "TotalReturnMomentumFeature",
    "RealizedVolatilityFeature",
    "FeatureV1",
    "features_v1",
    "cross_sectional_rank",
    "cross_sectional_demean",
    "cross_sectional_zscore",
    "cross_sectional_winsorize",
]
