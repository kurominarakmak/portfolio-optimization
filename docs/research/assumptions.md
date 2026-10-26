# Assumptions register

Frozen before observing evaluation results, 2026-10-26.

| Item | Default / interpretation | Verification needed |
|---|---|---|
| Portfolio | Long-only USD equity/ETF units plus nonnegative USD cash | Real statement, simultaneous prices, settled/unsettled cash and corporate actions |
| CSV example | Invented positions and prices, explicitly synthetic | Never infer the user's holdings from examples |
| Valuation | One timezone-aware timestamp; configurable maximum age against analysis time | Market calendars, price freshness and corporate actions beyond schema checks |
| Returns | Daily decimal simple total returns, synchronized dates, no forward fill | Provider rights, split/dividend adjustment, delistings, universe history |
| Currency | USD only, including Thai account's US assets | THB conversion and Thailand-specific tax/accounting excluded |
| Covariance | sklearn scaled-identity Ledoit–Wolf | Out-of-sample forecast comparison; finite moments/stationarity |
| BL prior | Explicit user zero excess-return prior if no genuine market weights supplied | Economic usefulness unverified; no equilibrium interpretation for this fallback |
| BL views | No views unless dated evidence, P/Q and Omega supplied | Pre-decision forecast error calibration; correlated views may need nondiagonal Omega |
| Tau | .05 research sensitivity parameter | Not an estimated confidence or a universal best value |
| Cash | Daily deterministic zero return unless supplied | Actual cash interest, fees and credit risk |
| Tail | Alpha .95, at least 20 expected historical tail observations for decisions | Independent observations/effective sample size, tail dependence and regime stability |
| Scenarios | Seed 42, Gaussian and synchronized resampling | Neither adds new market information; Gaussian can generate impossible simple returns |
| Cost | Proportional 10bps per risky traded dollar in exploratory evaluation | Actual spreads, commission, taxes, market impact and available liquidity unknown |
| Risk aversion | Lambda 1, uncalibrated | Investor preferences; no inferred suitability |
| Decision | Proposal-bound independent evidence plus observed investable inputs and verified expected-session coverage; internal sensitivity max L1 distance <=.25 | Human-supplied evidence is not automatically statistically credible; threshold uncalibrated |
| Shares | Separate whole-share preview, no order execution | Lot rules, fractional entitlements, fees, tax lots, live tradability |
| Historical portfolio | Hypothetical initial allocation only | Dated actual historical allocations absent |
| Factor exposures | Only with aligned supplied factors | Factor definitions, excess returns, stability and identification |
| Broker | Official SDK, read-only account methods; TH host verified in SDK | App approval and actual account entitlements not supplied; no live connection tested |

Defaults are engineering choices. None is presented as empirically optimal. A conservative zero prior can make all-cash optimal; hiding this with invented alpha would invalidate the experiment.
