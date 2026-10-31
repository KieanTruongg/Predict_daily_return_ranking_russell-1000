"""Standalone test runner to verify core components."""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_neutralization import test_dollar_neutrality, test_position_limit_clipping
from tests.test_operators import test_delta_and_delay, test_cross_sectional_rank_and_demean
from tests.test_metrics import test_performance_metrics, test_daily_ic
from tests.test_pit_universe import (
    test_reconstitution_date_is_last_friday_of_june,
    test_mask_switches_after_reconstitution,
    test_no_look_ahead_on_real_lists,
    test_feature_engineer_respects_mask,
    test_2026_list_overlaps_iwb_holdings,
)

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    try:
        print("[1/4] Testing Long-Short Neutralization and Leverage Scaling...")
        test_dollar_neutrality()
        test_position_limit_clipping()
        print("  -> PASSED: Portfolio weights strictly sum to 0 (Dollar-neutral)!")

        print("[2/4] Testing Alpha Operators (Delta, Delay, CS Rank, CS Demean)...")
        test_delta_and_delay()
        test_cross_sectional_rank_and_demean()
        print("  -> PASSED: Mathematical operators functioning as expected!")

        print("[3/4] Testing Performance Metrics and Information Coefficient...")
        test_performance_metrics()
        test_daily_ic()
        print("  -> PASSED: Sharpe, Returns, and Rank IC formulas validated!")

        print("[4/4] Testing PIT Universe Mask (reconstitution timing, no look-ahead)...")
        test_reconstitution_date_is_last_friday_of_june()
        test_mask_switches_after_reconstitution()
        test_no_look_ahead_on_real_lists()
        test_feature_engineer_respects_mask()
        test_2026_list_overlaps_iwb_holdings()
        print("  -> PASSED: Membership only effective after late-June reconstitution!")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY (4/4)")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)
