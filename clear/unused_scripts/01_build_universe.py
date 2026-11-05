"""Script 01: Build and cache the Russell 1000 constituent universe."""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.universe import build_or_load_universe

if __name__ == "__main__":
    print("=" * 60)
    print("STEP 1: BUILDING RUSSELL 1000 UNIVERSE (TARGET >= 500 STOCKS)")
    print("=" * 60)

    universe_path = os.path.join("data", "raw", "universe", "russell1000_constituents.csv")
    tickers = build_or_load_universe(output_csv=universe_path, min_stocks=500)

    print(f"\n[Success] Universe ready: {len(tickers)} stocks saved to '{universe_path}'")
    print(f"Sample tickers: {tickers[:15]} ... {tickers[-5:]}")
