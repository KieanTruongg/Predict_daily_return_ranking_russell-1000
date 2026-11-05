"""
src.models
==========
Phase 3 — walk-forward CV, panel builder và các model xếp hạng.
"""

from src.models.walk_forward import (
    Fold,
    WalkForwardResult,
    daily_decile_spread,
    daily_rank_ic,
    ic_summary,
    make_folds,
    run_walk_forward,
)
from src.models.panel import build_panel, target_next_rank
from src.models.feature_sets import FEATURES_V1, available_features, load_feature_matrices, reversal_5d
from src.models.baselines import ICSignEqualWeightModel, RidgeModel, SingleFactorModel, get_model_factory

__all__ = [
    "Fold",
    "WalkForwardResult",
    "daily_decile_spread",
    "daily_rank_ic",
    "ic_summary",
    "make_folds",
    "run_walk_forward",
    "build_panel",
    "target_next_rank",
    "FEATURES_V1",
    "available_features",
    "load_feature_matrices",
    "reversal_5d",
    "ICSignEqualWeightModel",
    "RidgeModel",
    "SingleFactorModel",
    "get_model_factory",
]
