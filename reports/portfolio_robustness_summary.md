# Portfolio robustness summary

**EXPLORATORY_REAL_MARKET / HISTORICAL_RETURN_REPLAY — NO_TRADE, not VALIDATED.**

Completed input directory: `/Users/manpao/Downloads/dongchain/optimizatiom/reports/exploratory_20261026`.

Smoke-only structural report: False. Both feeds use identical initial definitions and aligned dates; no independent-account inference.

| Provider | Attempted | Valid | Account failures | Fit failures | BL-CVaR minus buy-and-hold mean / median net return | Fraction higher net return | Fraction lower ES |
|---|---:|---:|---:|---:|---|---:|---:|
| alpaca | 250 | 250 | 0 | 0 | -0.17328366 / -0.15894551 | 0.276 | 0.952 |
| tiingo | 250 | 250 | 0 | 0 | -0.17279955 / -0.1605537 | 0.256 | 0.956 |

Read all strategy distributions, paired intervals, initial-group/year slices and the complete failure ledgers in the provider reports. Zero-prior/no-view BL does not identify incremental Bayesian signal; compare minimum CVaR explicitly. No favorable statistic is selected as proof. All reported results are conditional on full-window common-survivor selection, differing close definitions, unresolved action/PIT/rights/execution limitations, and unadjusted multiple comparisons. Actual user holdings/forward evaluation are not established by this replay.

## What the experiments show

Both providers completed 250 hypothetical accounts, each starting from one frozen random 5–10-stock holding set, across 861 out-of-sample trading returns from 2022-07-28 through 2025-12-31. The first 504 returns trained each rolling decision; there were 14 rebalance folds. These are simulated starting holdings, not the user's current brokerage positions. Seven strategies began with the same USD 100,000 and initial holdings within each account. The frozen protocol and exact local file paths, hashes, exclusions, and return definitions are in [the data manifest](exploratory_20261026/data_manifest.json), [portfolio definitions](exploratory_20261026/portfolio_definitions.json), and [run configuration](exploratory_20261026/run_configuration.json).

BL–CVaR reduced mean realized one-day ES95 from 3.408% to 2.684% on Alpaca and from 3.411% to 2.685% on Tiingo versus buy-and-hold. It had lower ES in 95.2% and 95.6% of accounts, respectively. This supports mechanical tail-risk reduction within this restricted sample; it does not establish superior forecasts. Mean net cumulative returns were 19.766% versus 37.094% on Alpaca and 19.758% versus 37.038% on Tiingo. BL–CVaR beat buy-and-hold in only 27.6% and 25.6% of accounts, so it hurt net return in 72.4% and 74.4%. Its mean zero-rate Sharpe was 0.351 on both sources, below buy-and-hold (0.468/0.467) and equal weight (0.537/0.536). Relative to equal weight, it won on net return in only 16.4%/16.8% of accounts; its lower ES occurred in 78.0%/78.8%.

The mean BL–CVaR modeled trading cost was USD 387.41/390.63 per USD 100,000 initial account, versus zero for buy-and-hold and USD 221.96/221.80 for equal weight. Those costs are already included in net returns. Minimum CVaR and BL–CVaR were numerically equivalent: the apparent 0.4%/0.8% BL win rates arise from floating-point solver differences, not an incremental BL benefit. The experiment supplied zero excess prior and no investment views, so it cannot answer whether informative BL priors would add value.

Initial holdings mattered. Alpaca mean BL–CVaR minus buy-and-hold net return ranged from -11.35 percentage points for concentrated profiles to -29.73 points for cash-boundary profiles; Tiingo ranged from -11.47 to -29.45 points. All five prespecified profile means were negative on both feeds. Provider-wide findings were similar, but individual minimum-CVaR outcomes differed by as much as 6.00 percentage points across feeds; source choice is therefore not immaterial to an individual account. The matched comparison shows return, ES, forecast-risk, allocation, and ranking differences for all seven books.

These accounts share one market history. The paired date-block intervals in the provider reports are conditional descriptive uncertainty, not 250 independent trials; the Alpaca BL–CVaR versus buy-and-hold mean daily-return interval spans zero [-0.000465, 0.000132], as does Tiingo's [-0.000466, 0.000133]. Full-window common-survivor selection uses future coverage and limits external validity. The replay uses Alpaca raw IEX price returns and Tiingo vendor-adjusted-close ratios, with no verified executable fills, complete point-in-time corporate-action certification, or actual user holdings. The strict `NO_TRADE` gate remains in force; forward paper tracking is still `NOT_STARTED` until dated genuine holdings and subsequent observed prices are available.
