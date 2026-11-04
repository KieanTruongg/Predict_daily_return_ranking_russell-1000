"""
src.data
========
High-performance 2D matrix ingestion, PIT masks, and universe management.
"""

from src.data.matrix_loader import (
    load_matrix,
    load_matrices,
    load_masked_matrix,
    load_dates_index,
    load_columns_sids,
    get_matrix_path,
)
from src.data.masks import (
    load_layer1_mask,
    load_layer2_mask,
    load_layer3_mask,
    combine_masks,
    verify_mask_hierarchy,
)
from src.data.universe import (
    load_canonical_security_mapping,
    load_temporal_mapping,
    ticker_to_canonical_sids,
    canonical_sid_to_ticker,
    get_active_constituents,
    get_reconstitution_year,
)

__all__ = [
    "load_matrix",
    "load_matrices",
    "load_masked_matrix",
    "load_dates_index",
    "load_columns_sids",
    "get_matrix_path",
    "load_layer1_mask",
    "load_layer2_mask",
    "load_layer3_mask",
    "combine_masks",
    "verify_mask_hierarchy",
    "load_canonical_security_mapping",
    "load_temporal_mapping",
    "ticker_to_canonical_sids",
    "canonical_sid_to_ticker",
    "get_active_constituents",
    "get_reconstitution_year",
]
