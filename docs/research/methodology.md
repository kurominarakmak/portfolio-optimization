# Methodology decision — 2026-10-26

Status: specification frozen before implementation. This is decision support, with no order API. Mathematical tests do not establish investment performance. See [references](references.md) for access limitations.

## Research decision matrix

| Approach | Coherence and data | Assumptions and sensitivity | Cost / explanation | Validation and decision |
|---|---|---|---|---|
| A: classical mean–variance, shrinkage covariance | Convex quadratic; synchronized adjusted returns and explicit expected returns | Finite second moments; unstable sample means; covariance and risk-aversion sensitive | Small QP; variance is easy to explain but symmetric | Equal weight and minimum variance are baselines; sample-mean MV is an ablation, not an alpha model |
| B: BL plus mean–variance | Gaussian Bayesian mean update then constrained QP; supplied prior or dated genuine market weights, risk aversion, optional P/Q/Omega | Prior, tau, view errors matter; no views preserves prior mean; constraints invalidate unconstrained market-recovery claims | Small linear solves plus QP; views and prior auditable | Candidate comparator; reference-test posterior; perturb prior/tau/views |
| C: BL mean plus scenario CVaR and costs | Bayesian mean update plus finite-scenario convex program; same data plus costs/constraints | Tail estimates unstable; Gaussian misses tail dependence; bootstrap assumes local stationarity; scenario mean shift is an adaptation | LP for CVaR; scenarios dominate runtime; explicit tail losses/costs | Primary research candidate, not a proven improvement; must survive cost/uncertainty gates and walk-forward comparisons |

Choose Ledoit–Wolf **scaled-identity** shrinkage (2004 JMA, as implemented by sklearn) as the reproducible default. This is different from the constant-correlation target in *Honey*. Sample covariance and exponentially weighted covariance are comparators; do not average estimators without evidence. EWMA responds faster but adds decay sensitivity; robust/nonlinear estimators are deferred absent demonstrated need.

## Conventions and mathematical specification

Initial engine: USD, long-only US equities/ETFs plus cash, simple total returns, one trading day risk/decision horizon. Cash has an explicitly supplied daily deterministic rate (default 0, a scenario assumption). Annualized arithmetic mean = 252 daily mean; annualized volatility = sqrt(252) daily volatility under the usual no-autocorrelation approximation. Never scale ES by sqrt(time). No missing-value filling, duplicate dates/symbols, unsorted dates, mixed currencies, negative positions or unadjusted prices accepted. Reject inadequate samples and stale snapshots; freshness is relative to an explicit analysis timestamp.

Covariance: fit risky assets only, append a zero cash row/column. Reject material non-PSD input, symmetrize roundoff only. Require at least max(60, 5N) observations; this is a screening rule, not a statistical guarantee. Constant returns/stale consecutive quotes require explicit failure or warning; sample variance alone is not evidence of quote freshness.

BL uses excess-return prior pi. If genuine market weights exist, pi = delta Sigma w_market; ETFs' AUM must not be confused with constituent market capitalization. Investor holdings are never market weights. With unavailable market weights use an explicitly labeled user prior (offline default zero excess return), which changes the equilibrium interpretation. Optional views require dated evidence and explicit positive-definite Omega; do not invent confidence percentages. Empirical calibration would use pre-decision forecast errors and disjoint calibration data; not implemented without such evidence.

Let T=tau Sigma, A=P T P' + Omega. Solve linear systems:

    mu = pi + T P' solve(A, Q-P pi)
    M = T - T P' solve(A, P T)
    predictive covariance = Sigma + M

No views: mu=pi, M=T. Cash is appended after the risky update. Return innovation covariance and mean uncertainty M are distinct. Primary scenarios condition on mu and innovation covariance Sigma; optional Gaussian predictive scenarios add M exactly once. Historical/stationary-bootstrap scenarios resample synchronized rows; residuals are centered on training means and shifted to mu. This preserves empirical residual cross-dependence but not shrinkage covariance exactly, and does not integrate posterior mean uncertainty. Do not relabel bootstrap tails as Gaussian predictive tails. One-day stationary bootstrap does not improve its marginal over row resampling; blocks matter for path/statistic uncertainty. Reject impossible simple returns below -100%, including generated Gaussian extremes; do not clip silently. Historical stress windows are descriptive, not assigned invented probabilities.

## Convex accounting and risk

Optimize dollar fractions x of **pre-trade** NAV, including cash. Current fractions w0 sum to one. Risky turnover is sum |x_i-w0_i| (two-sided gross traded notional; cash transfer excluded); quoted one-way turnover is half this only if explicitly labeled. Linear cost k=c'|x_risky-w0_risky|. Self-financing: sum x + k=1. Use trade epigraph variables t>=abs(trade), k=c't, an affine budget and objective that charges cost; independently reconcile actual absolute trades and reject non-tight epigraph solutions. Report post-cost weights x/(1-k) separately. All weight/sector/cash bounds apply to these normalized weights and remain affine through 1-k. A cash-only solution is allowed; no hidden required risky allocation.

For scenario returns R, net one-day losses are L_s=k-R_s x. RU ES:

    ES_alpha = min_z z + sum_s max(L_s-z,0)/[S(1-alpha)]
    objective = -mu_total' x + k + lambda * ES_alpha

Charging k in expected loss and in tail loss reflects mean and risk preferences, not two debits to NAV. Linear extra turnover regularization, if used, is separate from actual cash cost. Use alpha=.95, lambda=1 as documented uncalibrated research defaults. Require expected tail count >=20 in history and scenarios for actionable decisions; increasing simulations does not increase historical information. Exact empirical ES handles fractional probability mass at VaR. Costs are charged once to wealth, not once every holding day. Accept only optimal solver status and independently checked residuals <=1e-6; infeasibility never triggers silent relaxation. Fixed fees, minimum tickets and integer shares are nonconvex: a separate preview must reconcile cash and recheck all constraints after rounding or return NO_TRADE. No order transmission exists.

## Decision policy and uncertainty

NO_TRADE takes precedence for invalid/stale inputs, unsupported broker response, insufficient tail data, solver failure, infeasibility, failed rounding, missing uncertainty assessment, or unstable sensitivity. HOLD means current constraints are satisfied and estimated net utility improvement does not exceed the configured materiality threshold. REBALANCE requires feasibility, improvement above threshold, and positive lower uncertainty bound across documented model sensitivities. Current constraint violations cannot produce HOLD. Utility is mu'x-k-lambda ES; uncertainty from paired synchronized block resampling is conditional on model assumptions, not proof of superior expected returns. Avoid using optimization scenarios as independent validation evidence. Parameter grid and decision thresholds are frozen before evaluation. If no independent evidence is supplied, recommendation stays NO_TRADE while candidate analytics remain visible.

Implementation review refinement: only explicitly observed, investable data with attributed, verified expected-session coverage may support an actionable decision. Synthetic inputs and academic proxies always give NO_TRADE. Evaluate net utility for the **actual whole-share preview**, not merely the continuous target; unchanged quantities cannot justify REBALANCE. Bind supplied independent evidence to that exact proposal and its input/configuration fingerprint. An external evidence assertion cannot override an internal diagnostic failure. Internal sensitivity acceptance uses a conservative, uncalibrated engineering threshold: maximum L1 normalized-weight distance from the continuous candidate across scenario-family/lambda perturbations <=.25, with no failed fit. This threshold was introduced to close a safety gap, not selected on proxy performance; it does not establish statistical calibration.

## Evaluation protocol

Rolling training windows, next-day execution at the documented boundary, disjoint nonoverlapping test periods; drift positions between rebalances. Initial allocation is explicitly hypothetical unless historical allocations are provided. Start all strategies from identical initial wealth/weights, charge initial transitions, use common universe/dates, constraints and proportional execution costs. Buy-and-hold may be labeled exempt from rebalance constraints, never silently made comparable. Compare buy-and-hold, equal weight, minimum variance, equal risk contribution where feasible, BL MV, minimum CVaR, BL CVaR cost-aware. Include no-BL, variance, sample covariance, Gaussian/bootstrap, no-cost-control ablations; even no-cost-control pays realized costs. Historical views/priors must be available before each decision. No today's capitalization fed into historical windows.

Report net returns, Sharpe/Sortino (zero-rate assumption labeled), drawdown including initial wealth, fractional empirical ES, VaR exceedance frequency, tail-loss diagnostic, covariance forecast MSE, turnover/costs, concentration and weight changes. Paired stationary-block bootstrap intervals for mean net return differences preserve dates across strategies; dependence/stationarity and multiple-comparison limitations remain. No automatic PBO claim: CSCV requires a declared family of trials and its exchangeability assumptions; it is not a cure for regime change. Report folds and failures, not only successful strategies. Stress/regime slices are descriptive and fixed before evaluating results.

Daily forecast verification: within each holding block, reuse only the training-estimated scenario model while recomputing portfolio losses with each day's start-of-day drifted holdings. On a rebalance date, compare cost-inclusive loss k-Rx to realized net loss; on subsequent dates use -Rw without recurring costs. Training window total-return means are already total returns; add cash yield only when converting the BL **excess** mean to total mean.

## Claims and boundaries

Literature supports BL Bayesian blending, shrinkage, RU ES, convex linear costs and the need for simple benchmarks. Their composition, defaults, evidence gates and bootstrap recentering are engineering decisions. Better out-of-sample utility, stable tail forecasts and calibrated confidence are untested hypotheses until observed investable data support them. No API/UI before core checks; minimal local HTML report is sufficient after checks. Factors/sectors require supplied aligned metadata. No live account access or actual historical holdings were supplied.
