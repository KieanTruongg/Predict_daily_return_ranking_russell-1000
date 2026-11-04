"""
src.quality
===========
Data quality assurance, leakage prevention, and trading window enforcement.
"""

from src.quality.quality_window import (
    OOSFreezeViolationError,
    check_oos_access,
    filter_dev_window,
    validate_trading_calendar_partition,
    assert_causal_alignment,
)

__all__ = [
    "OOSFreezeViolationError",
    "check_oos_access",
    "filter_dev_window",
    "validate_trading_calendar_partition",
    "assert_causal_alignment",
]
