# Frozen randomized-holdings protocol (2026-10-26, before outcomes)

Status: **implementation may be tested with fixtures; the 250 real-market
portfolios cannot be admitted until a verified asset universe exists.** No
portfolio may be sampled from today's surviving names and relabeled
historically eligible.

The primary start date will be the first date after at least 504 aligned,
qualified daily total-return observations for each sampled asset. At each start
date the sampler must use an asset's dated existence, identity, tradability,
corporate-action, and licensed-usage evidence available then. It samples held
assets only; optimization may retain/reweight these assets and cash, without
adding names. Save a single initial state for each hypothetical account and
carry it forward through all rebalance dates. Every benchmark starts from that
same state and NAV. Do not draw a fresh account at each rebalance.

Primary seed: 42. A separate stream with a recorded seed generates return
scenarios from training data only. Freeze 50 portfolios each for diversified,
concentrated, sector-heavy, stock/ETF mix, and cash/boundary groups. If dated
sector or ETF identity is unavailable, mark those strata unavailable and use
explicit concentration alternatives, while retaining 250 total valid samples
only if the full verified universe permits. Sample 5–10 held risky assets when
possible, use fixed Dirichlet profiles (`alpha=3` diversified, `alpha=0.35`
concentrated), cash in [0, 0.10], risky weight <=0.60, long only, total 1.0,
and initial NAV 100,000 USD. Rejection sampling has a recorded finite limit;
failure yields `BLOCKED`, never a reduced or silently invalid sample.

Frozen walk-forward settings: rolling 504 observations, nonoverlapping 63-day
test windows, 1,000 training-based scenarios, ES confidence 95%, risk aversion
1, risky traded-dollar cost 10 bps, risky cap 60%, cash 0–10%, turnover cap
2, cost budget 1%. The zero-prior/no-view BL lane is the baseline. Dated market
prior and historical views are separate lanes only when genuine evidence exists.
Run buy-and-hold, equal weight, minimum variance, equal risk contribution where
feasible, BL mean variance, minimum CVaR, and BL-CVaR using the same observed
dates, holdings set, cost conventions, and start NAV. Buy-and-hold's rebalance
bounds exemption must be explicit. Record every solver failure and all account
state transitions. Without independently verified execution timing and prices,
label output `statistical return replay`.

Compare every initial account pairwise on aligned dates, report distributions
and failures, and resample date blocks across the shared market history rather
than treating 250 accounts as independent market experiments. Freeze sensitivity
checks before the final data run: holdings seeds 7/42/101, cash cap variants
0/10%, concentration profiles above, bootstrap/Gaussian scenario families,
ES 90/95%, risk aversion 0.5/1/2, and costs 0/10/25 bps. These are diagnostics,
not a search for the best final Sharpe. The earlier French period has already
influenced development and is no untouched holdout.

Admission gate: attributable USD daily total returns; independently checked
session calendar and adjustment policy; security identity, delisting, and
corporate actions through the full holding period; dated eligibility; usage
rights; source hashes; and enough aligned observations. If any mandatory input
is absent, D3–D5 report `BLOCKED` and never compute proxy price performance as
if it were valid. Invalid and out-of-mandate initial holdings form a separate
negative-control lane.
