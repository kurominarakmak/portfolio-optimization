# Portfolio research engine

Local Python decision support for daily USD long-only equities/ETFs plus cash. No order functions, service, database or live dashboard. Research decisions were frozen in [methodology](docs/research/methodology.md) before implementation; source access and uncertainty are in [references](docs/research/references.md).

```sh
uv sync --extra test
uv run pytest -q
uv run portfolio-engine demo --output reports/synthetic-demo
uv run portfolio-engine analyze --holdings examples/synthetic/holdings.csv --returns examples/synthetic/returns.csv --metadata examples/synthetic/returns.json --as-of 2026-10-24T00:00:00Z --output reports/offline-analysis
uv run portfolio-engine evaluate --returns data/research/french_5_industry_daily.csv --metadata data/research/french_5_industry_daily.json --train 504 --step 63 --max-cash .1 --output reports/proxy-cli
```

The lock file pins the environment; `uv sync` installs runtime and default development/test dependencies. `--extra test` is also supported. `demo` creates explicitly **SYNTHETIC** fixtures under `examples/synthetic`. JSON and static HTML outputs are written alongside each other. Analysis HTML presents current/continuous/rounded composition, cash/NAV, one-day scenario risk/cost comparisons and shared-bin net-loss histograms, with escaped expandable JSON details. No credentials or internet are needed for offline analysis. Reports can contain account information; put private inputs in `data/private` and reports in `reports/private` (ignored by Git).

## Inputs

Holdings CSV exact required columns: `symbol,quantity,price,currency,valuation_timestamp,nav`; optional `cost_basis` in USD per share. Each risky symbol appears once. Include exactly one `CASH` row with quantity equal to USD cash and price 1. All rows repeat the same timezone-aware snapshot timestamp and declared total NAV. NAV must reconcile to quantity times price including cash within one cent. No short positions, negative cash, mixed currencies, missing values or future/stale snapshots accepted. Snapshot and returns freshness default to four calendar days relative to explicit `as_of`; this is a screening assumption, not an exchange-calendar freshness guarantee.

Return CSV first column is `date`, other columns exactly match risky symbols. Values are synchronized daily decimal simple **total returns**. No fills, duplicate/unsorted dates, intraday timestamps, impossible returns below -1, constant series or six consecutive zero returns accepted. Require at least max(60,5N) rows; actionable ES requires at least 20 expected tail observations in history and simulation. Supply companion JSON with `provider`, `permitted_usage`, `adjustment: "total_return"`, `currency: "USD"`, `frequency: "daily"`, `units: "decimal"`, timezone-aware `retrieved_at`, `kind: "observed"|"synthetic"`, `coverage_start`, `coverage_end`. Provider permissions are declarations, not verified licenses. Optional `expected_sessions` must exactly equal the ordered return-date grid; any internal missing session fails validation. Actionable analysis additionally requires an independently attributed `calendar_source`, `session_coverage_verified: true`, `kind: "observed"`, and `investable: true`. Merely copying source return dates does not verify an exchange session calendar. Without an expected-session grid a conservative screen rejects gaps over seven calendar days or more than 20% of gaps over three days; passing this screen only permits descriptive analytics. No holiday calendar is invented. Explicit aligned factor data can be passed to `models.risk_metrics`; factor exposures are omitted without them. Sector caps require a sector label per risky asset.

Current holdings are never treated as historical holdings. Academic industry proxy returns are observed research series, not tradeable ETF returns or investor performance. Synthetic results only check engineering behavior.

## Python API

```python
from portfolio_engine.data import read_portfolio, read_returns
from portfolio_engine.cli import analyze, write_report
from portfolio_engine.evaluation import evaluate
from portfolio_engine.optimize import Constraints

# metadata is the attributed return JSON loaded as a dict.
# returns is an indexed DataFrame; analyze validates exact holdings universe.
report = evaluate(returns, metadata, train=504, step=63,
                  constraints=Constraints(max_cash=.1, cost_budget=.01), seed=42)
write_report(report, "reports/private/comparison")
```

`analyze(portfolio, returns, metadata, constraints=None, prior=None, views=None, evidence=None, as_of=...)` returns candidate risk, costs, continuous fractions, separate whole-share preview and decision. `prior` is explicitly supplied daily excess return; default is user-labelled zero, **not** market equilibrium. `views` contains `P,Q,omega,evidence` with dated source; Omega must be positive definite. `models.market_prior` requires dated genuine market-capitalization evidence. Investor weights and ETF AUM are never used as capitalization substitutes.

`evidence` is an externally supplied independent uncertainty assessment (`independent`, `source`, `lower_bound` in daily net utility units, `sensitivity_stable`, `proposal_id`). It must come from disjoint validation covering the exact rounded proposal. Analysis reports a deterministic SHA-256 `proposal_id` binding symbols, current allocation, rounded fractions, return-input digest, as-of timestamp and model/constraint configuration. A missing or mismatching ID gives **NO_TRADE**. Supplied evidence remains an unauthenticated attestation, not independently verified statistical proof.

Recommendations use the separately cash-reconciled **rounded** portfolio's expected net return, ES, costs, turnover and net utility improvement. Continuous candidates remain diagnostics. Unchanged rounded quantities cannot produce REBALANCE. HOLD requires feasible current weights and immaterial implemented improvement; REBALANCE also needs a matching independent positive lower bound above the frozen threshold. Synthetic inputs, noninvestable research proxies, unverified session coverage and known sensitivity failures always produce NO_TRADE, regardless of supplied evidence flags.

The four sensitivity fits are diagnostics, not independent proof. A frozen uncalibrated engineering stability screen requires no failed scenario/optimization fit and maximum L1 difference between alternate normalized weights and the continuous candidate no greater than 0.25. Reports expose the maximum difference, threshold and failures. No threshold is selected from performance results.

Cash returns are deterministic and explicit (default zero per day). Covariance and conditional scenario innovations are distinct from BL posterior mean uncertainty. Predictive Gaussian scenarios optionally add `mean_uncertainty` once; bootstrap scenarios do not. All primary losses and costs use one trading day. Only mean/volatility are annualized with 252; ES is never square-root-scaled.

## Constraints and accounting

`Constraints` supplies min/max risky weights, min/max cash, sector caps, gross two-sided risky turnover, proportional transaction cost and budget. Bounds apply to **post-cost normalized weights**. Optimization holds pre-trade-NAV fractions `x`, so `sum(x)+cost=1`. Cash is not counted as traded notional. The solver's actual absolute-trade costs and all residuals are independently checked. Tiny boundary noise is cleaned only after verification and cash/costs are reconciled and checked again. Infeasibility never relaxes constraints.

Whole-share quantities are a separate floor-rounded preview. Cash and actual costs are recomputed and every constraint rechecked; a failed preview gives NO_TRADE. Fractional current quantities are rejected for whole-share preview. Fixed fees, tax lots, slippage curves, liquidity, minimum ticket search, and mixed-integer optimization are not modeled. `preview_shares` can check a supplied minimum ticket. It does not submit orders.

## Walk-forward comparison

`evaluate` uses strictly past rolling (or expanding) training windows, next-day holding returns, synchronized universe/dates, drift between rebalances and charges initial transitions and all subsequent proportional costs. Every failed fit remains in the failure ledger; it holds previous weights that fold without relaxing constraints. Twelve strategies cover seven benchmarks and five requested ablations. Buy-and-hold is explicitly exempt from rebalance constraints. Equal weight/ERC retain 10% cash, while optimizers follow the supplied cash mandate. Pure minimum variance first finds a cost-free target and then realizes actual costs under common constraints; BL MV includes cost in its daily objective. No-cost-control omits optimization cost but still pays actual realized costs.

All folds disclose train/test dates, allocations and failures. Daily VaR/ES forecasts use each day’s actual start exposure after drift; first-day forecast losses include transition cost against pre-trade NAV, while later holding days do not repeat that cost. Realized losses and tail diagnostics use the same daily units. BL priors are excess means plus the explicit cash rate; the no-BL historical means are already total returns and receive no added cash rate. Metrics include net mean/return, annualized volatility, zero-rate Sharpe/Sortino, drawdown including initial wealth, fractional empirical ES, VaR hit rate, excess tail loss, covariance/variance forecast MSE, gross turnover, costs, HHI and weight drift. Conditional mean forecast errors are not equivalent to posterior mean calibration; VaR frequency alone does not establish conditional tail calibration. Paired stationary-block intervals compare daily net mean differences; stationarity, block choice and multiple trials limit interpretation. Per-fold tails can be too sparse even when pooled tails are sufficient. No automatic PBO or profitable-investment claim is made.

## Optional read-only Webull adapter

`uv sync --extra broker` installs the official SDK. `broker.read_webull(account_id, as_of, valuation_timestamp, eligible=True)` reads only `AccountV2.get_account_list/get_account_balance/get_account_position`. Set `WEBULL_APP_KEY` and `WEBULL_APP_SECRET` in the environment; never commit credentials. TH host `api.webull.co.th` was verified against official SDK `endpoints.json`. TH endpoint availability does not establish account eligibility: caller must explicitly confirm a supported CASH account and independently verify valuation freshness. The positions API omits quote timestamps; retrieval time cannot replace a quote timestamp. Unsupported envelopes/pagination, derivative positions, margin balances, locked cash and unreconciled NAV fail closed. Auth, rate-limit and connection errors are sanitized. No automatic retry loop or credential logging. No live credentials/account were supplied, so live auth, permissions and regional schema compatibility remain untested. See [official account API](https://developer.webull.com/apis/docs/trade-api/account/) and [official SDK](https://github.com/webull-inc/webull-openapi-python-sdk).

See [architecture](docs/architecture.md) for methods, checks and traceability. Passing tests establishes numerical/accounting behavior under tested cases, not empirical investment performance or production readiness.

## Frozen randomized holdings (D2 infrastructure)

The real 250-portfolio experiment is **BLOCKED** until an independently verified dated US stock/ETF universe passes admission. Existing French proxies and synthetic fixtures do not qualify. Unit tests generate 250 definitions from explicit test-only external-attestation fixtures; these are not 250 real-market accounts or independent market histories. This extension does not rerun or alter earlier French reports.

`sampling.sample_portfolios(universe, start_at, seed=42, max_attempts=1000)` accepts JSON-compatible metadata only: it never receives prices or returns. It returns all 250 valid definitions (50 per frozen group), or `status: "BLOCKED"` with no partial sample. Five to ten held names are sampled when available; two to four names are explicitly disclosed as an adaptation; fewer than two blocks the run. Dirichlet alpha is 3 diversified and 0.35 concentrated. Sector-heavy portfolios place 75% of risky wealth in the dated sector when other sectors are selected. Missing dated sector/ETF labels produce explicit concentrated-profile fallback labels. Cash stays 0–10%, risky weights at most 60%, and NAV is USD100,000. Cash/boundary samples use cash 0/10% and one 60% risky weight. Finite rejection limits are reported.

The `universe` contract has `provider`, `permitted_usage`, `source_hashes` (named 64-hex SHA256 digests), `verification`, and `assets`. Verification requires a named `source`, timezone-aware `available_at` no later than start, and explicit true flags for `identity`, `tradability`, `point_in_time`, `corporate_actions`, `delistings`, `session_calendar`, `adjustment_policy`, `usage_rights`, and `daily_usd_total_returns`. Each asset requires unique `symbol`/`permanent_id`, `currency: "USD"`, `market: "US"`, dated `known_at`, `eligible_from`, optional `eligible_until`, integer `history_observations_asof >= 504`, and `history_asof` no later than start. Optional dated `sector` and `asset_type: "STOCK"|"ETF"` enable those strata. Supplied derivative/non-USD identities are excluded. These are external verification attestations; the sampler cannot authenticate their truth or inspect provider licenses itself.

A recorded SeedSequence child stream samples holdings and a separate child stream produces `scenario_seed`. Save the initial definitions once with `sampling.save_definitions(result, path)`; exclusive-create refuses to replace an existing experiment. Definitions include symbols, permanent IDs, weights, cash, NAV, concentration, eligibility time, seed, attempts, prior coverage and a deterministic hash. Neither paper updates nor any existing rebalance code calls the sampler.

```sh
uv run portfolio-engine sample --universe data/private/verified-universe.json --start-at 2020-01-02T00:00:00Z --output data/private/frozen-definitions.json
```

A BLOCKED output is saved as such; it is not a completed D3–D5 result. No verified real universe has been supplied in this workspace.

## Forward paper tracking (D6 infrastructure)

`paper.start_paper(directory, portfolio, returns, metadata, holdings_provenance, as_of, ...)` accepts the existing `read_portfolio` output, rechecks its accounting and freezes its first decision, complete return snapshot, original positions, configuration, data/config/proposal fingerprints and three independent paper books. `holdings_provenance` requires a `source` and `kind: "observed"|"synthetic"`; genuine positions additionally require `genuine_holdings_verified: true`. Claims are supplied attestations, not authenticated account connections. Historical input retrieval must precede the decision, and fitted returns cannot postdate the holdings valuation. Existing synthetic/noninvestable/calendar/uncertainty NO_TRADE gates remain in force. Non-genuine holdings always remain NO_TRADE.

The books share identical **pre-trade** NAV and original holdings: hold; a predeclared one-time 90%-equal-risky/10%-cash benchmark, then hold; and the feasible rounded optimized allocation, then hold. The optimized book is always explicitly exploratory and may be hypothetically implemented even while the frozen recommendation remains NO_TRADE. Actual proportional initial trade costs are debited once. A failed benchmark/rounded preview records its failure and holds original quantities; constraints are never relaxed. No automatic periodic rebalance or fresh holdings draw occurs in this first forward cohort. A different decision needs a new directory/cohort, rather than overwriting a past decision.

**Accounting convention:** snapshots anchor total-return unit prices to the supplied valuation prices. Subsequent validated total returns compound those units while recorded quantities stay fixed; deterministic cash return uses the frozen configured rate (zero by default). This represents reinvested distributions through adjusted units. These later unit prices/quantities are **not actual raw share quotes or verified executable holdings**. Without a separate raw-price/corporate-action execution ledger, results are statistical return replay only. No brokerage connection or real order exists in this workflow.

`paper.update_paper(directory, returns, metadata, synthetic_replay=False)` requires a complete validated cumulative return snapshot. Every original and previously observed row must remain byte-equivalent numerically; revisions/removals are rejected. Only new sessions strictly after the frozen decision are appended. Updates use an actual UTC wall-clock cutoff and reject future retrieval/observation timestamps; accepted events record that actual update timestamp. Explicit `synthetic_replay=True` (CLI `--synthetic-replay`) permits fixture dates only for synthetic, nongenuine cohorts, records that mode and never grants live status. The full batch is checked before writing; repeated snapshots are idempotent. `snapshot.json` is never overwritten; `events.jsonl` is hash-chained, exclusively locked for local concurrent writers, flushed and fsynced. A separate `committed_head.json` records the last committed sequence/hash: reads take the same journal lock and reject even complete-record truncation. Journal data are fsynced before an atomic head replacement and directory fsync; interrupted or partial commits fail closed on a head mismatch. Older cohorts without a committed head are rejected rather than silently migrated. Stored data/config hashes detect ordinary tampering; these are not signatures, remote timestamps or proof against an operator who rewrites hashes. Do not manually edit the files. A damaged/truncated chain fails closed; no automatic repair is attempted.

`paper.read_paper(directory)` verifies the snapshot and journal and reports each book’s NAV, quantities, cash, total net return, one-time costs, drift, drawdown, forward volatility, tail ES only after 20 expected tail observations, and frozen-model forecast errors/VaR exceedances. Initial costs enter total return and drawdown; they are not repeated in later daily losses or treated as an extra trading day. Forecasts use only the first frozen fit and each book’s drifted exposure; a stale frozen forecast is not recalibrated by future observations. `live_forward_status` remains `NOT_STARTED` for synthetic infrastructure or unverified inputs, including after synthetic update tests. Genuine, attributed, verified observed sessions may mark `OBSERVING_PAPER_ONLY`; this does not authorize REBALANCE or establish sufficient forward investment evidence.

```sh
# Example holdings provenance file for engineering fixtures only:
# {"source":"explicit synthetic fixture", "kind":"synthetic"}
uv run portfolio-engine paper-start --directory data/private/paper-cohort-1 --holdings examples/synthetic/holdings.csv --holdings-metadata data/private/holdings-provenance.json --returns examples/synthetic/returns.csv --metadata examples/synthetic/returns.json --as-of 2026-10-24T00:00:00Z
uv run portfolio-engine paper-status --directory data/private/paper-cohort-1
# Run only after independently sourced future observations actually arrive:
uv run portfolio-engine paper-update --directory data/private/paper-cohort-1 --returns data/private/cumulative-returns.csv --metadata data/private/cumulative-returns.json
```

These commands print JSON and write only the selected cohort directory. Genuine user holdings are not connected and actual forward verification has not started; synthetic fixtures establish accounting/immutability behavior only.

## Separate frozen Alpaca/Tiingo exploratory replay

The local-data experiment in `docs/research/exploratory_market_protocol.md` has its own `EXPLORATORY_REAL_MARKET` / `HISTORICAL_RETURN_REPLAY` implementation. It does not call or relax the strict `VALIDATED` sampler, issue an actionable recommendation, relabel raw prices as total returns, or alter prior French results. `exploratory.load_matched_data(root)` reads the frozen 23-name cohort, local identity mapping and XNYS calendar for 2020-07-27–2025-12-31. Every selected feed/symbol must have all 1,366 positive price observations; Tiingo action fields must show zero dividends/unit splits, and same-day cross-source log-return discrepancy must stay below .05. Embedded source/symbol/security identities are checked. Missing prices are never filled. File hashes, runtime candidate counts, cohort exclusions and limitations are recorded; only the frozen 23 names are runtime quality screened, rather than reranking the entire universe.

Alpaca uses raw IEX close-to-close **price** returns; Tiingo uses vendor-adjusted-close ratios captured in 2026. The selected no-recorded-action window does not prove action completeness or PIT back-adjustment. These price series are never called verified executable fills. Full-window common coverage selection introduces survivorship and future-coverage bias, so this experiment measures allocations conditional on selected survivors, not historical stock-selection skill.

`exploratory.make_portfolios(alpaca_returns.iloc[:504])` creates one fixed 250-definition cohort: 50 each diversified, concentrated, training-correlated, cash-boundary, and 5/10-name breadth. Training-correlated selection uses only the first 504 Alpaca returns; both sources then reuse identical portfolio IDs, symbols and weights. Dirichlet profiles and caps follow the frozen protocol. Holdings and scenario RNG streams are distinct and recorded; no holdings redraw occurs at rebalances.

`exploratory.replay_account(returns, definition, scenario_seed, fit_cache=None, max_folds=None)` reuses existing BL/shrinkage/bootstrap/convex optimizer/risk-parity logic for seven independent books. Rolling 504/step63, S1000, ES95, lambda1, costs10bps, risky60%/cash10% caps and 1% cost budget are frozen in the runner. Initial NAV is USD100,000 for every strategy. Initial transitions and later proportional costs occur once, weights drift, and first-day scenario losses include the transition cost against pre-trade NAV. Later daily forecasts use drifted exposures. Buy-and-hold's cap exemption is explicit. Fit failure holds prior positions with all dates and the failure retained; it does not relax constraints. The input cache contains only data-keyed covariance/BL/scenario fits, never optimized solutions dependent on current weights. No per-account inferential bootstrap is run: 250 accounts share market shocks, so inference belongs to a date-block aggregate comparison.

```sh
# New directory required; saves all 250 initial definitions before evaluating outcomes.
# Smoke evaluates only the first two accounts and one fold per feed, clearly labelled.
uv run python scripts/run_exploratory.py --smoke --output-directory /tmp/exploratory-smoke
# Reproduce a full run in a new directory; no downloads are performed.
uv run python scripts/run_exploratory.py --output-directory reports/exploratory-full
```

The runner writes source/definition/config/environment hashes, separate provider JSON with every account's daily NAV/returns/risk forecasts and per-fold dollar trades/weights/costs/failures, and timing estimates. It exclusive-creates outputs to preserve earlier runs. Full output is `alpaca_randomized_250.json` and `tiingo_randomized_250.json`; smoke uses distinct `*_smoke.json` names and retains the requested count of 250 in configuration without claiming completion. Account-level failures remain explicit. BL uses zero excess prior/no views: it does not establish incremental BL value. The completed 2026-10-26 run is in `reports/exploratory_20261026/`; its aggregate reports are in `reports/`, with source provenance and exclusions in `reports/exploratory_20261026/data_manifest.json`.
