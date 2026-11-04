"""
src.data.masks
==============
3-Tier Point-In-Time Mask hierarchy and filter combiners:
  - Layer 1: PIT Membership Mask (strict_membership_mask / membership_mask)
  - Layer 2: Tradable & Valid Data Mask (valid_data_mask)
  - Layer 3: Training & Evaluation Label Mask (valid_label_mask)

Strict Hierarchy Constraint:
  Layer 3 (valid_label) <= Layer 2 (valid_data) <= Layer 1 (membership)
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

from src.data.matrix_loader import load_matrix
from src.utils.config import Config


def load_layer1_mask(
    strict: bool = True,
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Loads Layer 1 PIT Membership Mask.
    If strict=True: loads strict_membership_mask ([01/07/Y to 30/06/Y+1] cycle).
    If strict=False: loads membership_mask.
    """
    matrix_name = "strict_membership_mask" if strict else "membership_mask"
    df = load_matrix(
        matrix_name,
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
        config=config,
    )
    return df.astype(bool)


def load_layer2_mask(
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Loads Layer 2 Tradable / Valid Data Mask.
    Ensures active constituent, price > 0, volume > 0, not in bad data period,
    and consecutive trading session.
    """
    df = load_matrix(
        "valid_data_mask",
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
        config=config,
    )
    return df.astype(bool)


def load_layer3_mask(
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Loads Layer 3 Training & Evaluation Label Mask.
    Ensures valid data at T and T+1, target return non-NaN, and split boundary purged.
    """
    df = load_matrix(
        "valid_label_mask",
        dev_only=dev_only,
        include_warmup=include_warmup,
        allow_oos=allow_oos,
        config=config,
    )
    return df.astype(bool)


def combine_masks(
    layer1: bool = True,
    layer2: bool = True,
    layer3: bool = False,
    strict_layer1: bool = True,
    dev_only: bool = False,
    include_warmup: bool = False,
    allow_oos: bool = False,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Combines selected mask layers using element-wise logical AND (&).

    Parameters:
        layer1: Include Layer 1 (PIT membership).
        layer2: Include Layer 2 (Tradable / valid data).
        layer3: Include Layer 3 (Valid label).
        strict_layer1: Use strict reconstitution [01/07 to 30/06] for Layer 1.
        dev_only: Slice to development dates.
        include_warmup: Include warmup window if dev_only=True.
        allow_oos: Explicitly permit OOS if dev_only=False.

    Returns:
        pd.DataFrame of boolean values (True = valid, False = masked out).
    """
    combined: Optional[pd.DataFrame] = None

    if layer1:
        m1 = load_layer1_mask(
            strict=strict_layer1,
            dev_only=dev_only,
            include_warmup=include_warmup,
            allow_oos=allow_oos,
            config=config,
        )
        combined = m1 if combined is None else (combined & m1)

    if layer2:
        m2 = load_layer2_mask(
            dev_only=dev_only,
            include_warmup=include_warmup,
            allow_oos=allow_oos,
            config=config,
        )
        combined = m2 if combined is None else (combined & m2)

    if layer3:
        m3 = load_layer3_mask(
            dev_only=dev_only,
            include_warmup=include_warmup,
            allow_oos=allow_oos,
            config=config,
        )
        combined = m3 if combined is None else (combined & m3)

    if combined is None:
        raise ValueError("At least one mask layer must be enabled.")

    return combined


def verify_mask_hierarchy(
    m_mask: pd.DataFrame,
    d_mask: pd.DataFrame,
    l_mask: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Mathematically verifies the strict 3-tier hierarchy:
    valid_label_mask <= valid_data_mask <= membership_mask

    Returns:
        Dict detailing violations and hierarchical integrity status.
    """
    # Align shapes
    common_idx = m_mask.index.intersection(d_mask.index).intersection(l_mask.index)
    common_cols = m_mask.columns.intersection(d_mask.columns).intersection(l_mask.columns)

    m = m_mask.loc[common_idx, common_cols].values.astype(bool)
    d = d_mask.loc[common_idx, common_cols].values.astype(bool)
    l = l_mask.loc[common_idx, common_cols].values.astype(bool)

    # Violations:
    # 1. Label True but Data False
    label_without_data = int((l & ~d).sum())
    # 2. Data True but Membership False
    data_without_member = int((d & ~m).sum())

    is_strictly_hierarchical = (label_without_data == 0) and (data_without_member == 0)

    return {
        "is_strictly_hierarchical": is_strictly_hierarchical,
        "label_without_data_violations": label_without_data,
        "data_without_member_violations": data_without_member,
        "total_member_points": int(m.sum()),
        "total_data_points": int(d.sum()),
        "total_label_points": int(l.sum()),
        "evaluated_cells": int(m.size),
    }
