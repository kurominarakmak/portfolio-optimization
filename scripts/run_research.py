"""Reproduce preregistered diagnostics on observed, non-investable academic proxies."""

import importlib.metadata
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from portfolio_engine.evaluation import evaluate
from portfolio_engine.models import black_litterman, covariance, scenarios
from portfolio_engine.optimize import Constraints, optimize


ROOT = Path(__file__).resolve().parents[1]


def save(name, value):
    (ROOT / "reports" / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sensitivity(frame, constraints):
    training = frame.iloc[-504:]
    initial = np.r_[np.full(frame.shape[1], .9 / frame.shape[1]), .1]
    base = {"alpha": .95, "risk_aversion": 1., "tau": .05, "covariance": "shrinkage", "family": "bootstrap"}
    trials = [("base", base)]
    for key, values in {
        "alpha": [.90], "risk_aversion": [.5, 2.], "tau": [.025, .1],
        "covariance": ["sample", "ewma"], "family": ["gaussian"],
    }.items():
        trials.extend((f"{key}={value}", {**base, key: value}) for value in values)
    results = []
    for label, config in trials:
        sigma = covariance(training, method=config["covariance"])
        posterior = black_litterman(sigma, prior=np.zeros(frame.shape[1]), tau=config["tau"])
        generated = scenarios(training, posterior["mean"], sigma, size=1000, seed=42, family=config["family"])
        result = optimize(np.column_stack([generated, np.zeros(len(generated))]),
                          np.r_[posterior["mean"], 0.], initial, np.pad(sigma, ((0, 1), (0, 1))),
                          constraints, alpha=config["alpha"], risk_aversion=config["risk_aversion"])
        results.append({"trial": label, "config": config,
                        "result": {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in result.items()}})
    for row in results:
        weights = np.asarray(row["result"]["weights"])
        assert np.isfinite(weights).all() and abs(weights.sum() - 1) < 1e-6
    return {
        "description": "One factor at a time; final 504 observations; conditional no-view zero prior. No performance selection.",
        "training_end": str(training.index[-1].date()), "seed": 42, "trials": results,
        "interpretation": "Tau cannot affect the conditional no-view mean; sample/EWMA covariance cannot change bootstrap residual scenarios. Gaussian comparison uses covariance. These degeneracies are expected, not evidence of robustness.",
    }


def pct(value):
    return "undefined" if value is None else f"{100 * value:.2f}%"


def write_report(report, unrestricted, sensitivities):
    strategies = report["strategies"]
    daily = strategies["bl_cvar"]["daily"]
    dates = [row["date"] for row in daily]
    assert all([row["date"] for row in strategy["daily"]] == dates for strategy in strategies.values())
    assert report["folds"][0]["train_end"] < dates[0]
    lines = [
        "# Observed academic proxy comparison", "",
        "Research diagnostic only. Five French industry portfolios are constructed research returns, **not investable equities/ETFs or the user's portfolio**. Current revised history does not establish historical tradability. No investment-performance superiority or production readiness is claimed.", "",
        f"Observed input: {report['provenance']['coverage_start']}–{report['provenance']['coverage_end']}; out of sample: {dates[0]}–{dates[-1]}, {len(dates)} daily observations, {len(report['folds'])} rolling folds.",
        "Training: 504 days; rebalancing: 63 observations; seed 42; 1,000 scenarios; daily ES confidence 95%; lambda 1; explicit zero prior; no views; daily cash interest 0. Initial hypothetical weights: 18% in each of five industries, 10% cash. Cost: 10bps per risky traded dollar.", "",
        "The primary common mandate caps cash at 10%, risky positions at 60%, risky traded notional at 200%, costs at 1% of pre-trade NAV. Buy-and-hold is explicitly exempt from rebalance constraint enforcement. No historical capitalization or actual investor holdings are inferred.", "",
        "Timing is idealized reallocation at the training/test boundary. Daily aggregate portfolio returns do not separate overnight from intraday returns, provide an executable next-open price, or establish latency/slippage feasibility. This is a past-data-only statistical experiment, not a verified execution backtest.", "",
        "## Seven benchmark allocations", "",
        "| Strategy | Net cumulative return | Annual volatility | Sharpe (zero rate) | Max drawdown | Daily ES95 loss | Gross risky turnover | Sum local cost fractions | Failed folds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ["buy_hold", "equal_weight", "min_variance", "risk_parity", "bl_mv", "min_cvar", "bl_cvar"]:
        row = strategies[name]
        sharpe = "undefined" if row["sharpe_zero_rate"] is None else f"{row['sharpe_zero_rate']:.3f}"
        lines.append(f"| {name} | {pct(row['net_total_return'])} | {pct(row['annualized_volatility'])} | {sharpe} | {pct(row['maximum_drawdown'])} | {pct(row['daily_realized_es'])} | {row['two_sided_risky_turnover']:.3f} | {pct(row['total_cost_fraction'])} | {len(row['failed_folds'])} |")
    lines += ["", "Net cumulative return compounds daily returns after actual modeled cost. Costs are sums of fractions of each rebalance's NAV, not dollar costs divided by original NAV. Volatility/Sharpe annualization uses 252 and weak-autocorrelation assumptions. ES is a one-day empirical loss statistic; drawdown is historical across the displayed evaluation period. Pure minimum variance uses a variance target followed by self-financing implementation; BL MV includes mean/variance utility and cost preference, so they need not coincide.", "",
              "## Ablations and conditional uncertainty", "",
              "| Comparator | Net cumulative return | Candidate minus comparator mean daily return (bps) | Paired block 95% interval (bps/day) | Failed folds |",
              "|---|---:|---:|---:|---:|"]
    for name, contrast in report["paired_uncertainty"].items():
        low, high = contrast["paired_stationary_block_95_ci"]
        lines.append(f"| {name} | {pct(strategies[name]['net_total_return'])} | {1e4 * contrast['daily_mean_difference']:.3f} | [{1e4 * low:.3f}, {1e4 * high:.3f}] | {len(strategies[name]['failed_folds'])} |")
    contrast = report["paired_uncertainty"]["equal_weight"]
    low, high = contrast["paired_stationary_block_95_ci"]
    lines += ["", f"Candidate minus equal weight: {1e4 * contrast['daily_mean_difference']:.3f} bps/day, descriptive interval [{1e4 * low:.3f}, {1e4 * high:.3f}]. This is a conditional sampling diagnostic, not a superiority test or an independent recommendation gate.",
              "Intervals: 500 paired stationary-block resamples, mean block 10, seed 42. No multiple-testing correction; stationarity and block choice may fail. No-view zero BL prior makes minimum CVaR and BL CVaR redundant. The no-BL contrast substitutes a training sample mean, not an evidence-backed signal. Shrinkage versus sample covariance must compare `gaussian` against `sample_covariance`: bootstrap residuals do not use fitted covariance. Variance and ES risk aversions are not economically calibrated to equal risk budgets.", "",
              "## Predeclared market-period slices", "",
              "| Period | Observations | Candidate compounded net return | Equal-weight compounded net return |", "|---|---:|---:|---:|"]
    for start, end in [("2017", "2019"), ("2020", "2021"), ("2022", "2022"), ("2023", "2025")]:
        mask = np.array([start <= day[:4] <= end for day in dates])
        values = []
        for name in ["bl_cvar", "equal_weight"]:
            returns = np.array([row["net_return"] for row in strategies[name]["daily"]])[mask]
            values.append(pct(np.prod(1 + returns) - 1))
        lines.append(f"| {start}–{end} | {mask.sum()} | {values[0]} | {values[1]} |")
    lines += ["", "Slices are descriptive; they were not used to choose parameters. Each rebalance test block has fewer than 20 expected tail observations, so fold-level ES is particularly uncertain.", "",
              "## Unrestricted-cash diagnostic", "",
              "Same settings except cash ceiling 100%. Equal weight/ERC retain their 10% cash rule; this is an explicitly different mandate. A zero-prior one-day risk objective can select cash. Do not interpret the result as market-timing skill.", "",
              "| Strategy | Net cumulative return | First target cash | Final target cash | Failed folds |", "|---|---:|---:|---:|---:|"]
    for name in ["bl_cvar", "equal_weight", "min_variance"]:
        first = unrestricted["folds"][0]["weights"].get(name)
        last = unrestricted["folds"][-1]["weights"].get(name)
        lines.append(f"| {name} | {pct(unrestricted['strategies'][name]['net_total_return'])} | {pct(first[-1]) if first else 'failed'} | {pct(last[-1]) if last else 'failed'} | {len(unrestricted['strategies'][name]['failed_folds'])} |")
    lines += ["", "## Sensitivity and failures", "",
              f"{len(sensitivities['trials'])} final-window one-factor sensitivity trials are in `sensitivity.json`. These are modeled allocations, not out-of-sample results. Tau changes are inert without views when conditioning on innovation covariance; bootstrap covariance-estimator changes are also inert by construction.", "",
              "The first exploratory run is preserved as `french_proxy_attempt1.json`: a solver boundary residue propagated into invalid-current-weight failures in the no-cost-control ablation. The implementation was corrected and regression-tested; failed folds were never silently discarded. The minimum-variance comparator was corrected to use a pure variance target rather than a cost-dominated utility. No return-based hyperparameters were changed.", ""]
    lines += ["The second run is preserved as `french_proxy_attempt2.json`. Independent review identified frozen within-fold VaR/ES exposures and inconsistent first-day cost treatment in those diagnostics. Final forecasts now use each day's start-of-day drifted exposure and cost-inclusive rebalance losses. This correction does not alter realized returns or the fitted allocations.", ""]
    failures = {name: row["failed_folds"] for name, row in strategies.items() if row["failed_folds"]}
    lines.append("Final primary-run failures: " + (json.dumps(failures) if failures else "none."))
    lines += ["", "## Reproduction and limits", "",
              "Run `uv sync --extra test`, `uv run --extra test pytest`, `uv run python scripts/prepare_french.py`, then `uv run --extra test python scripts/run_research.py`. Source archive and processed CSV hashes, provider attribution, download timestamp and usage limitations are in `data/research/french_5_industry_daily.json`. The archived source snapshot is retained so future provider revisions cannot silently change this run.", "",
              "Full per-day diagnostics, forecasts, fold weights and failures are in `french_proxy_comparison.json`; unrestricted diagnostics in `french_proxy_unrestricted.json`. Reference and assumptions ledgers are in `docs/research/`. Real account integration, licensed investable point-in-time validation, empirically calibrated views and independent recommendation evidence remain pending. No trades are executed.", ""]
    (ROOT / "reports/empirical_comparison.md").write_text("\n".join(lines))


def main():
    source = ROOT / "data/research/french_5_industry_daily.csv"
    frame = pd.read_csv(source, index_col="date", parse_dates=True)
    metadata = json.loads(source.with_suffix(".json").read_text())
    constraints = Constraints(max_cash=.1, cost_budget=.01)
    kwargs = dict(train=504, step=63, seed=42, scenario_count=1000, alpha=.95, risk_aversion=1., ci_samples=500)
    primary = evaluate(frame, metadata, constraints=constraints, **kwargs)
    save("french_proxy_comparison.json", primary)
    unrestricted = evaluate(frame, metadata, constraints=Constraints(max_cash=1., cost_budget=.01), **kwargs)
    save("french_proxy_unrestricted.json", unrestricted)
    sensitivities = sensitivity(frame, constraints)
    save("sensitivity.json", sensitivities)
    sources = sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py")) + [ROOT / "uv.lock"]
    save("environment.json", {
        "packages": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "scipy", "scikit-learn", "cvxpy", "PyPortfolioOpt"]},
        "python": platform.python_version(), "platform": platform.platform(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    })
    write_report(primary, unrestricted, sensitivities)
    print(ROOT / "reports/empirical_comparison.md")


if __name__ == "__main__":
    main()
