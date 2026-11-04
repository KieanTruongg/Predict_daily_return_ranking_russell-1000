# Archive v1: Phase 1 Legacy Codebase (Deprecated)

This directory contains the legacy code from Phase 1 of the **Predict Daily Return Rankings** project.
It is preserved strictly for historical reference, audit compliance, and retrospective comparison.

**WARNING: DO NOT IMPORT OR USE THIS CODE IN STEP 7 (FEATURE ENGINEERING) OR SUBSEQUENT PRODUCTION MODULES.**

---

## 1. Archival Overview

- **Archive Date**: 2026-11-04
- **Original Source Location**: `src/` (`alphas/`, `data/`, `features/`, `metrics/`, `portfolio/`)
- **Archival Destination**: `src/archive_v1/`
- **Superseded By**: Clean modular architecture in `src/` operating on Tier 2 Adjusted Warehouses and 2D Matrices (`data/processed/matrices/`).

---

## 2. Core Reasons for Deprecation

The Phase 1 implementation contained several critical quantitative and data engineering flaws that necessitated complete architectural retirement prior to Step 7:

### A. Zero-Fill Artifact in `feature_engineer.py` (`fillna(0)`)
- **Location**: `src/archive_v1/features/feature_engineer.py` (Line 132: `log_ret = np.log1p(ret_w.fillna(0))`).
- **Defect**: Filling missing returns with `0.0` creates artificial price stability for non-trading, suspended, or unlisted stocks.
- **Consequence**: This artificially depresses realized volatility, distorts cross-sectional rankings, induces forward-looking look-ahead artifacts during zero-return imputation, and biases momentum and reversal features.
- **Resolution in Step 7**: Missing values outside the active tradable universe are strictly preserved as `np.nan` throughout all matrix operations and cross-sectional rankings.

### B. Flawed Reconstitution Date in `pit_universe.py`
- **Location**: `src/archive_v1/data/pit_universe.py` (Lines 11–12, 38–44: `d -= timedelta(days=(d.weekday() - 4) % 7)`).
- **Defect**: Calculated universe reconstitution as "the last Friday of June" dynamically using calendar days.
- **Consequence**: Inconsistent with the institutional Russell 1000 reconstitution convention where constituent membership is effective strictly across the annual cycle `[01/07/Y to 30/06/Y+1]`. It created temporal mismatch against corporate actions and point-in-time security identifiers.
- **Resolution in Step 7**: Fixed reconstitution window `[01/07/Y to 30/06/Y+1]` uniformly enforced in `universe_constituent_temporal_mapping.csv`, `strict_membership_mask.parquet`, and `src.data.universe`.

### C. Stale Data Paths & Unadjusted Split Assumptions in `loader.py`
- **Location**: `src/archive_v1/data/loader.py` (Lines 1–5, 23–24).
- **Defect**: Referenced non-existent Phase 1 files (such as `data/processed/daily_ohlcv/russell1000_daily_2000_2026.parquet`) and assumed SplitAdjusted data where `Close == Adj Close`.
- **Consequence**: Throws immediate `FileNotFoundError` on current pipeline data structures and fails to account for cash dividend adjustments, total return calculations, and corporate actions.
- **Resolution in Step 7**: Direct ingestion via `src.data.matrix_loader` reading 26 2D matrices $(7,252 \times 3,711)$ from `data/processed/matrices/` and Tier 2 adjusted warehouse `russell1000_constituents_daily_ohlcv_adjusted_1998_2026.parquet`.

---

## 3. Contents of Archive

- `alphas/`: Phase 1 alpha definitions and basic operators.
- `data/`: Phase 1 data loaders (`loader.py`, `pit_universe.py`, `preprocessor.py`, `split.py`, `universe.py`).
- `features/`: Phase 1 `feature_engineer.py` with `fillna(0)` defect.
- `metrics/`: Phase 1 performance and IC calculators (`information.py`, `performance.py`).
- `portfolio/`: Phase 1 long-short combiners and dollar-neutralizers (`combiner.py`, `neutralizer.py`).
- `old_src__init__.py`: Original Phase 1 package initialization.
