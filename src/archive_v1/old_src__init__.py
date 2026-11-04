"""Quantitative Equity Research System - Predicting Daily Return Rankings."""
__version__ = "0.2.0"

# ─── Module Map (Phase 1/2 status) ───────────────────────────────────────────
#
# ✅ ACTIVE — Phase 1/2:
#   src/alphas/      operators.py, reversal_5d.py, base.py — CS alpha computation
#   src/features/    feature_engineer.py (v4, lowercase schema) — feature store
#   src/metrics/     information.py (Rank IC), performance.py
#
# ⚠️ OUTDATED SCHEMA (v3) — NOT used in Phase 1/2:
#   src/data/        loader.py, preprocessor.py, split.py, universe.py
#                    → Uses OLD capitalized columns (Close, Adj Close, Volume)
#                    → Phase 1/2 reads directly from in_sample/*.parquet matrices
#                    → Reserved for Phase 3 refactoring
#
# 🔒 PHASE 3 ONLY — Not yet needed:
#   src/portfolio/   combiner.py, neutralizer.py — portfolio construction
#
# ─────────────────────────────────────────────────────────────────────────────
