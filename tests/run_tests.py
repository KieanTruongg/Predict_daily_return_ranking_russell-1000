"""Standalone test runner to verify core components."""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_neutralization import test_dollar_neutrality, test_position_limit_clipping
from tests.test_operators import test_delta_and_delay, test_cross_sectional_rank_and_demean
from tests.test_metrics import test_performance_metrics, test_daily_ic

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    try:
        print("[1/3] Testing Long-Short Neutralization and Leverage Scaling...")
        test_dollar_neutrality()
        test_position_limit_clipping()
        print("  -> PASSED: Portfolio weights strictly sum to 0 (Dollar-neutral)!")

        print("[2/3] Testing Alpha Operators (Delta, Delay, CS Rank, CS Demean)...")
        test_delta_and_delay()
        test_cross_sectional_rank_and_demean()
        print("  -> PASSED: Mathematical operators functioning as expected!")

        print("[3/3] Testing Performance Metrics and Information Coefficient...")
        test_performance_metrics()
        test_daily_ic()
        print("  -> PASSED: Sharpe, Returns, and Rank IC formulas validated!")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY (3/3)")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)
