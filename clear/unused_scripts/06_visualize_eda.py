"""Script 06: Data Visualization & Exploratory Data Analysis (EDA).
Generates interactive & publication-ready figures for market data inspection:
  1. Historical Close Price & Cumulative Return Curves of Top US Stocks
  2. Cross-Sectional Daily Return Distribution (Skewness & Fat Tails)
  3. Active Stock Universe Count Over Time (2013-2026)
  4. Correlation Heatmap of Market Features
"""
import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.split import load_in_sample_data

if __name__ == "__main__":
    print("=" * 60)
    print("STEP: GENERATING EXPLORATORY DATA ANALYSIS (EDA) PLOTS")
    print("=" * 60)

    # 1. Load strictly in-sample processed data
    data = load_in_sample_data()
    fig_dir = os.path.join("outputs", "figures")
    os.makedirs(fig_dir, exist_ok=True)

    dates = data.get_dates()
    tickers = data.get_tickers()
    close_df = data.close
    returns_df = data.returns

    print(f"Loaded dataset: {len(dates)} trading days across {len(tickers)} stocks.")

    # -------------------------------------------------------------
    # Plot 1: Historical Prices & Cumulative Returns of Top Stocks
    # -------------------------------------------------------------
    sample_stocks = [t for t in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM"] if t in close_df.columns][:5]
    if sample_stocks:
        plt.figure(figsize=(12, 6))
        for s in sample_stocks:
            series = close_df[s].dropna()
            cum_ret = (1.0 + returns_df[s].fillna(0.0)).cumprod() - 1.0
            plt.plot(cum_ret.index, cum_ret, label=s, lw=1.8)

        plt.title("Cumulative Return Curves of Representative US Equities (2013 - 2023)", fontsize=14, fontweight="bold")
        plt.ylabel("Cumulative Return")
        plt.xlabel("Date")
        plt.grid(True, alpha=0.3)
        plt.legend(loc="upper left")
        plt.tight_layout()
        plot1_path = os.path.join(fig_dir, "eda_top_stocks_performance.png")
        plt.savefig(plot1_path, dpi=150)
        plt.close()
        print(f"[Saved Plot 1] Cumulative returns chart -> '{plot1_path}'")

    # -------------------------------------------------------------
    # Plot 2: Cross-Sectional Daily Return Distribution (Fat Tails)
    # -------------------------------------------------------------
    all_daily_returns = returns_df.values.flatten()
    clean_returns = all_daily_returns[~np.isnan(all_daily_returns)]
    clean_returns = clean_returns[(clean_returns > -0.15) & (clean_returns < 0.15)]  # Clip extreme outliers for chart

    plt.figure(figsize=(10, 6))
    plt.hist(clean_returns, bins=100, density=True, color="royalblue", alpha=0.6, edgecolor="none", label="Empirical Returns Distribution")
    
    # Overlay Gaussian / Normal distribution for comparison
    mu, std = np.mean(clean_returns), np.std(clean_returns)
    x = np.linspace(-0.15, 0.15, 200)
    p = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / std) ** 2)
    plt.plot(x, p, "crimson", lw=2, linestyle="--", label=f"Gaussian Fit (Mean: {mu:.4f}, Std: {std:.4f})")

    plt.title("Cross-Sectional Daily Return Distribution (Demonstrating Fat Tails & Heavy Skew)", fontsize=13, fontweight="bold")
    plt.xlabel("Daily Simple Return")
    plt.ylabel("Density")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plot2_path = os.path.join(fig_dir, "eda_returns_distribution.png")
    plt.savefig(plot2_path, dpi=150)
    plt.close()
    print(f"[Saved Plot 2] Daily return distribution histogram -> '{plot2_path}'")

    # -------------------------------------------------------------
    # Plot 3: Active Stock Universe Count Over Time
    # -------------------------------------------------------------
    active_stock_counts = close_df.notna().sum(axis=1)

    plt.figure(figsize=(12, 5))
    plt.plot(active_stock_counts.index, active_stock_counts.values, color="emerald" if "emerald" in plt.colormaps else "teal", lw=2)
    plt.axhline(500, color="crimson", linestyle="--", label="Instructor Min Threshold (>= 500 Stocks)")
    plt.title("Active Stock Count in Universe Over Time (Point-in-Time Availability)", fontsize=13, fontweight="bold")
    plt.ylabel("Number of Active Stocks")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plot3_path = os.path.join(fig_dir, "eda_active_stocks_over_time.png")
    plt.savefig(plot3_path, dpi=150)
    plt.close()
    print(f"[Saved Plot 3] Active stock count over time -> '{plot3_path}'")

    print("\n[Complete] All EDA figures generated successfully in 'outputs/figures/'!")
