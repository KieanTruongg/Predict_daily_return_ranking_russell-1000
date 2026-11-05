"""Script 04: Evaluate 10 diversified alphas and combine into a robust Meta-Alpha portfolio."""
import sys
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.split import load_in_sample_data
from src.alphas.alpha_library import get_all_alphas
from src.portfolio.combiner import MetaAlphaCombiner
from src.backtest.engine import BacktestEngine

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Alpha Combination & Meta-Portfolio.")
    parser.add_argument("--cost-bps", type=float, default=5.0, help="Transaction cost in bps")
    args = parser.parse_args()

    print("=" * 70)
    print("STEP 4: MULTI-ALPHA ENSEMBLE & META-PORTFOLIO OPTIMIZATION")
    print("Evaluating 10 diversified alpha signals on In-Sample data")
    print("=" * 70)

    # 1. Load in-sample data
    data = load_in_sample_data()
    engine = BacktestEngine(transaction_cost_bps=args.cost_bps, target_leverage=1.0)

    # 2. Run all individual alphas
    alphas = get_all_alphas()
    individual_reports = {}
    alpha_weights_dict = {}
    alpha_pnl_dict = {}
    alpha_ic_dict = {}

    summary_rows = []

    print(f"\nEvaluating {len(alphas)} candidate alpha strategies...")
    for alpha in alphas:
        report = engine.run(alpha, data)
        individual_reports[alpha.name] = report
        alpha_weights_dict[alpha.name] = report["weights"]
        alpha_pnl_dict[alpha.name] = report["pnl_series"]["net_return"]
        alpha_ic_dict[alpha.name] = report["ic_series"]

        summary_rows.append({
            "Alpha": alpha.name,
            "Category": alpha.category,
            "Ann Return": f"{report['net_annualized_return']:.2%}",
            "Sharpe (Net)": f"{report['net_sharpe_ratio']:.2f}",
            "Max DD": f"{report['max_drawdown']:.2%}",
            "Turnover": f"{report['average_daily_turnover']:.2%}",
            "Rank IC": f"{report['rank_ic_mean']:.4f}",
            "ICIR": f"{report['icir']:.2f}"
        })

    # Print summary table
    df_summary = pd.DataFrame(summary_rows)
    print("\n--- INDIVIDUAL ALPHA PERFORMANCE (IN-SAMPLE) ---")
    print(df_summary.to_string(index=False))

    # 3. Combine alphas into Meta-Alpha
    print("\nSynthesizing Meta-Alpha combinations...")
    combiner_eq = MetaAlphaCombiner(method="equal_weight", target_leverage=1.0)
    meta_weights_eq = combiner_eq.combine_weights(alpha_weights_dict)
    report_meta_eq = engine.run(meta_weights_eq, data, name="Meta_Alpha_EqualWeight")

    combiner_iv = MetaAlphaCombiner(method="inv_vol", target_leverage=1.0)
    meta_weights_iv = combiner_iv.combine_weights(alpha_weights_dict, alpha_pnl_series=alpha_pnl_dict)
    report_meta_iv = engine.run(meta_weights_iv, data, name="Meta_Alpha_InvVol")

    print("\n" + "=" * 55)
    print(" META-ALPHA ENSEMBLE RESULTS")
    print("=" * 55)
    print(f" [Meta Equal-Weight] Sharpe: {report_meta_eq['net_sharpe_ratio']:.2f} | Ann Ret: {report_meta_eq['net_annualized_return']:.2%} | MDD: {report_meta_eq['max_drawdown']:.2%}")
    print(f" [Meta Inv-Vol]      Sharpe: {report_meta_iv['net_sharpe_ratio']:.2f} | Ann Ret: {report_meta_iv['net_annualized_return']:.2%} | MDD: {report_meta_iv['max_drawdown']:.2%}")
    print("=" * 55)

    # 4. Save comparison figure
    os.makedirs(os.path.join("outputs", "figures"), exist_ok=True)
    fig_path = os.path.join("outputs", "figures", "meta_alpha_comparison.png")

    plt.figure(figsize=(12, 7))
    for name, rep in individual_reports.items():
        plt.plot(rep["pnl_series"].index, rep["pnl_series"]["cum_net_return"], alpha=0.3, lw=1, label=f"{name} (SR: {rep['net_sharpe_ratio']:.1f})")

    plt.plot(report_meta_eq["pnl_series"].index, report_meta_eq["pnl_series"]["cum_net_return"], color="crimson", lw=2.5, label=f"META (Equal-Weight) (SR: {report_meta_eq['net_sharpe_ratio']:.2f})")
    plt.plot(report_meta_iv["pnl_series"].index, report_meta_iv["pnl_series"]["cum_net_return"], color="navy", lw=2.5, linestyle="--", label=f"META (Inv-Vol) (SR: {report_meta_iv['net_sharpe_ratio']:.2f})")

    plt.title("Diversified Multi-Alpha vs Combined Meta-Alpha Portfolio (In-Sample)", fontsize=14, fontweight="bold")
    plt.ylabel("Cumulative Net Return")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"\n[Saved] Multi-alpha comparison figure saved to '{fig_path}'")
