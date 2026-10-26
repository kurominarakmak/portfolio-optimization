# Frozen Alpaca/Tiingo exploratory replay protocol

Frozen on 2026-10-26 after checking file readability, XNYS dates, recorded
split/dividend fields, and cross-source price-return discrepancies, **before
strategy outcomes**. This is a separate `EXPLORATORY_REAL_MARKET` lane; the
existing strict `VALIDATED` admission and `NO_TRADE` rules remain unchanged.

## Cohort and return definitions

Use local Alpaca `data/normalized/alpaca/membership_pit/SEC*.jsonl` and Tiingo
`data/normalized/membership_pit/TICKER.jsonl` in
`/Users/manpao/Downloads/ai-us-equity-portfolio-consultant`. Use the local
XNYS calendar in `data/verification/`. Fixed price window:
**2020-07-27 through 2025-12-31**, inclusive, 1,366 calendar sessions.
One historical ticker must map to one local security ID at the start. Admit
only symbols with a positive price on every session in both sources and zero
Tiingo `div_cash` and unit `split_factor` throughout this window; screen
same-day Alpaca/Tiingo log-return discrepancy above 5 percentage points as
an unresolved corporate-action/identity distortion. No missing values are
filled. This full-window quality filter creates survivorship and future
coverage selection bias; the sample is conditional on these names, not a
point-in-time stock-selection test. Unrecorded spin-offs or vendor errors
remain possible.

The frozen matched cohort is: **CHTR, ADBE, ADSK, AKAM, ALGN, AMD, CDNS,
DLTR, FFIV, HOLX, HSIC, IDXX, INCY, LULU, MELI, MRNA, SNPS, TTWO, UAL,
ULTA, VRTX, WDAY, ZBRA** (23 stocks). Exactly 23 passed the zero-gap,
zero-recorded-action filter; each has 1,366 price observations in both lanes.
As a cross-source check, each symbol's maximum absolute daily log-return
difference was under 2.3 percentage points, below the frozen 5-point quality
threshold. Record exact file hashes and all candidate/exclusion counts in the
run manifest.

Alpaca uses **raw IEX close-to-close price returns**; do not call them total
returns. Because the selected names have no recorded split/dividend event in
Tiingo during this window, they are a useful restricted price-only comparison,
but Alpaca's corporate-action completeness is not established. Tiingo uses
`vendor_adjusted_close` ratios, a vendor split/dividend adjusted research
series captured in 2026. Its back-adjustment is not a historical point-in-time
observation. We do not combine the two feeds or represent their closes as
executable fills. Report differences between their return definitions.

## Sampling and walk-forward

Generate **one fixed set of 250 initial portfolios**, then replay the same
portfolio IDs, tickers, weights, USD 100,000 initial NAV and decision dates
separately on Alpaca and Tiingo. This yields 250 accounts per provider and an
exact matched cross-source cohort. Seed 42; 50 each of diversified
(`Dirichlet(3)`), concentrated (`Dirichlet(0.35)`), correlated (high
correlation chosen using only the pretest 504 returns), cash-boundary, and
5-versus-10-name breadth profiles. Hold 5–10 distinct stocks, cash 0–10%,
single risky cap 60%, long only, weights plus cash 1. Save all definitions,
selection basis, and independent scenario RNG seed before evaluating outcomes.
Use only held symbols plus cash throughout an account. No resampling at
rebalance. Correlation is a training-period statistic, never a test-period
ranking.

Compute 1,365 dated simple returns from the 1,366 prices. The first 504
returns train; every later return is out of sample. Rolling 504, rebalance
every 63 returns, last fold shorter if needed; 1,000 bootstrap scenarios,
CVaR 95%, uncalibrated lambda 1, zero excess BL prior and no fabricated views,
cash daily return 0, cost 10 bps per risky traded dollar, max risky weight
60%, cash 0–10%, turnover cap 2, cost budget 1%. Run original buy-and-hold,
equal-weight, minimum variance, equal risk contribution, BL mean–variance,
minimum CVaR, and BL-CVaR. All seven begin from the same account state.
Buy-and-hold is exempt from rebalance caps but pays no trades; all others use
the same feasible mandate and costs. Reject failures explicitly rather than
relaxing constraints. Label every result `HISTORICAL_RETURN_REPLAY`.

Report per-account net NAV, return, volatility, Sharpe/Sortino, drawdown,
realized daily ES95, VaR calibration, turnover/cost, constraint and solver
failures, and paired BL-CVaR differences. Report complete portfolio
distributions; do not select winners. A date-block paired bootstrap treats
market dates as shared shocks across accounts, not 250 independent histories.
No parameter search on these outcomes. Do not alter the prior French reports.
