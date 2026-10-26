# Implementation and validation record

2026-10-26. Local research engine; no trade execution. The implementation worker and independent reviewer ran in sequence as required by the parent repository instructions. Unit tests and research proxies do not prove investment performance.

| Phase | Delivered | Validation evidence | Uncertain, failed, or blocked |
|---|---|---|---|
| 0 — methodology | Three-way decision matrix, equations, reference/access ledger, assumptions and preregistered experiments | Primary/author sources checked; exact access limitations retained; scaled-identity vs constant-correlation distinction explicit | Several full texts inaccessible; empirical view confidence and superiority unestablished |
| 1 — ingestion | Strict CSV/NAV/cash normalization; official read-only TH Webull adapter; provider/session metadata | Offline integration and sanitized-failure mocks, cash reconciliation, raw duplicate-header and missing-session tests | No account credentials or eligibility proof; no live authentication or statement reconciliation |
| 2 — risk | Shrinkage/sample/EWMA covariance; historical risk/concentration; optional aligned factor OLS; Gaussian and synchronized bootstrap | PSD/date/unit/sample checks, known-tail signs/mass, pinned seeds, scenario dependence and mean checks | Statistical estimator choice not established as best for the user's unavailable assets; constant-volatility/stationarity assumptions remain |
| 3 — optimization | BL posterior and optional dated views/market prior; mean–CVaR, variance, linear costs, normalized constraints; rounded share preview | PyPortfolioOpt BL reference; deterministic ES checks, feasibility/cost/constraint checks, repeated-rebalance numerical-boundary regression | Fixed fees, taxes, market impact and integer optimality absent; continuous optimality does not establish optimal executable trades |
| 4 — decisions | Explicit HOLD/REBALANCE/NO_TRADE; rounded utility; input/config/proposal-bound evidence; internal sensitivity and investability gates | Independent review reproduced synthetic evidence override and rounded-no-op defects before correction; regression tests now prevent both | Independent evidence is a supplied, unauthenticated attestation; numerical thresholds uncalibrated; synthetic/proxy inputs never actionable |
| 5 — evaluation | Seven benchmarks, five ablations, rolling/expanding evaluator, drift and cost accounting, paired block intervals, regime/sensitivity reporting | 36 rolling folds and 2,262 OOS daily observations on observed academic proxies; final primary run has no failed strategy folds; complete daily/fold ledgers retained | Investable point-in-time evaluation pending. Current revised industry portfolios and idealized boundary timing cannot establish executable equity/ETF performance |
| 6 — interface | Offline CLI plus static composition/risk tables, current/proposed shared-bin loss histogram, escaped expandable JSON | Demo/analyze/evaluate smoke checks; histogram mass, escaping and table tests | Browser security policy blocked local `file:` preview; visual rendering was not inspected. Real portfolio display requires actual supplied holdings |

## Test record

`uv sync` and `uv run --extra test pytest -q`: **45 passed** after bounded review corrections. Tests were added red before implementing the core and the seven review regressions. The reference/test dependencies and solver environment are pinned in `uv.lock`; actual source/lock SHA256 and installed package versions are in `reports/environment.json`.

Relevant suites: `tests/test_data.py`, `test_models.py`, `test_optimize.py`, `test_broker.py`, `test_evaluation.py`, `test_validation.py`, `test_review_regressions.py`, and the coordinator's `test_french.py`. Tests cover the tested inputs and numerical reference cases, not universal numerical correctness.

## Review and experiment corrections

The first independent review returned FAIL despite all then-existing tests passing. Findings were: continuous versus rounded decision mismatch; synthetic/failed-sensitivity overrides; frozen within-fold risk exposures; nonzero cash-rate mean inconsistency; silently empty sector caps; insufficient session/duplicate-header validation; and a JSON-only interface. These were corrected with regressions before the final experiment rerun. Additional nonfinite market-prior and missing evidence-date guards were added.

`reports/french_proxy_attempt1.json` preserves the first run, including propagated boundary-residue failures. `french_proxy_attempt2.json` preserves the pre-review diagnostic run. Neither is the final accepted experiment. Changes corrected software and benchmark labeling; no test-period return tuning was used. The final report is `reports/empirical_comparison.md` with detailed machine-readable outputs alongside it.

The final independent review returned **PASS**: all prior blocking findings corrected, no remaining actionable blocker identified. The reviewer independently reproduced synthetic override → NO_TRADE and rounded no-op → HOLD with zero implemented improvement. Regenerated VaR, ES, net returns and exceedance flags were independently recomputed for buy-and-hold, equal weight and BL–CVaR over 2,262 observations each, with zero mismatches. This review did not test live authentication, licensed investable data or browser rendering.

## Claims supported and unsupported

Supported: reproducible formula/accounting behavior under the test cases; a documented, repeatable exploratory proxy comparison; visibility of negative/inconclusive results; conservative default NO_TRADE without qualified data/evidence; no order API in this engine.

Unsupported: improved expected investment performance, statistical superiority over naive allocations, genuinely calibrated posterior confidence, real broker/account compatibility for this user, executable point-in-time equity/ETF backtest accuracy, investor suitability, or production readiness. The empirical report does not recommend trades.
