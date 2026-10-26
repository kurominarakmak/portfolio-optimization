# Experiment registry

Preregistered 2026-10-26 before any optimizer evaluation. No test-period parameter tuning.

## E0 — deterministic engineering verification

Synthetic correlated return fixtures, known loss vectors, accounting identities and independent reference libraries. Outcomes measure software/mathematical correctness only. Run `uv run --extra test pytest`. Require BL reference agreement, ES fractional-tail/sign agreement, PSD and alignment checks, self-financing costs, infeasible constraints, reproducibility, conservative decision policy and read-only broker mocks.

## E1 — observed academic proxy diagnostic

Use Kenneth French five-industry daily **value-weighted** returns including distributions, 2015-01-01 through 2025-12-31, taken from the first block of the official ZIP. Download snapshot, SHA256, original source headers and conversion retained. Convert percent to decimal once. Missing sentinel values fail; never substitute fabricated returns. Cutoff chosen as a completed calendar year rather than the most favorable endpoint.

These are constructed research portfolios, not executable equities/ETFs. Their current revised history does not reconstruct information actually available historically. No account history, ETF mapping, historical market capitalizations, execution rights, or revision-free universe provided. This diagnostic does NOT satisfy final investable strategy validation.

Primary comparison: rolling 504-day training, rebalance every 63 observations, seed 42, alpha .95, lambda 1, costs .001 of risky notional. Same universe and dates for all; initial hypothetical 18% per risky series and 10% cash. Long-only max risky weight .6, cash capped at .1 for the primary common-mandate comparison, turnover <=2, cost budget .01, no sector caps (industry portfolios already aggregate sectors; holdings metadata unavailable). Daily interest 0. No views, explicit zero prior. Use 1,000 scenarios or more, fixed before results. Parameter choices uncalibrated.

Compare hypothetical buy-and-hold, equal weight, minimum variance, equal risk contribution where feasible, BL mean–variance, minimum CVaR, cost-aware BL CVaR. Cash treatment for equal weight/ERC must be declared: keep common initial 10% cash target for those allocation rules; optimizer strategies have the same .1 cash ceiling (may hold less). A separately labeled unrestricted-cash diagnostic uses max_cash=1 and discloses its mandate differences. This refinement was frozen before any observed-data optimizer evaluation; default user analysis remains unrestricted cash.

Ablations: sample covariance instead of shrinkage, Gaussian instead of bootstrap, no-BL training sample mean instead of zero prior, variance instead of CVaR, remove optimization cost control but still pay realized costs. No-view/no-alpha degeneracies and redundant ablations must be reported. No alpha manufactured to make BL interesting.

Rolling windows end strictly before the next test block. Training-close data imply next-boundary hypothetical execution, without an overnight timing claim; aggregate daily total-return proxies do not contain intraday prices. Cost is paid at rebalance; drift weights thereafter. Confidence intervals: paired stationary bootstrap of **out-of-sample daily net-return differences**, mean block 10, 500 draws, seed 42, descriptive 95% interval; not corrected for familywise comparisons and not an independent decision gate.

Predeclared regimes: 2017–2019, 2020–2021, 2022, 2023–2025 (first interval may start later after training). Include all observations; no optimization on regime results. Minimum evaluation tail count warning where fewer than 20 expected exceedances. Forecast diagnostics concern one-day next-return forecasts; never compare daily VaR to a 63-day compounded return.

## E2 — sensitivity

Document alpha {.90,.95}, lambda {.5,1,2}, tau {.025,.05,.1}, covariance {shrinkage,sample,EWMA}, scenarios {Gaussian,bootstrap}. These are robustness diagnostics, not a grid search to select best test return. Under zero views and conditional innovation scenarios, tau does not affect the posterior mean or scenarios; record that fact. Changes in cash allocation and forecast utility do not establish statistical superiority.

## E3 — investable out-of-sample validation (pending)

Requires licensed point-in-time equity/ETF total returns with delistings, historical membership/capitalizations or a defensible nonmarket prior, dated views if any, actual cost estimates, documented historical allocations, and a held-out period not used in development. Compare identical investment/cash mandates. Calibrate forecast coverage and tail losses; examine exceedance clustering. Use nested training-only parameter selection if added. A PBO/CSCV result is not reported without a declared strategy-trial family and an assessment of exchangeability assumptions.

Reports must preserve failures and negative/inconclusive results. Passing E0 or completing E1 cannot mark E3 complete.
