# Research → implementation → evidence

This matrix distinguishes implementation checks from investment evidence. Reference IDs resolve in [references.md](references.md). Concrete run results are recorded in [experiments.md](experiments.md) and the generated comparison report.

| Method / requirement | Basis | Implementation boundary | Required validation / remaining evidence |
|---|---|---|---|
| Holdings, cash, weights | Accounting identity, engineering schema | `src/portfolio_engine/data.py` | USD-only, nonnegative finite quantity/cash, unique instruments, NAV reconciliation, timestamp, no fabricated user holdings |
| Read-only broker | Official Webull Python SDK and TH regional docs | Broker adapter, account list/balance/position only | Offline mocks: failure/auth/rate/unsupported payload; live entitlements and snapshot reconciliation pending |
| Adjusted returns and provenance | Provider conventions, not an estimator | Data validator; `scripts/prepare_french.py` | Dates/coverage/units, missing data, source and hashes; true point-in-time tradable dataset pending |
| Covariance | LW-I default; LW-H target comparison | `src/portfolio_engine/models.py` | PSD, finite alignment/sufficiency, sample/EWMA comparators; forecast error reported, no blanket superiority |
| BL mean and uncertainty | BL92, IDZ | `src/portfolio_engine/models.py` | No-view identities, independent reference posterior, valid Omega, prior/view provenance; market prior never inferred from investor holdings |
| Scenarios | PR94; Gaussian conditioning | `src/portfolio_engine/models.py` | Pinned seed, synchronized sampling, mean/covariance tests, innovation vs mean uncertainty; recentering is an adaptation |
| Discrete ES | RU00 and RU02 | Risk utility and optimizer | Fractional tail mass, signs, alpha, known sample and independently solved reference |
| Convex mean–CVaR | RU00; PK18 only related context | `src/portfolio_engine/optimize.py` | Feasible bounds, self-financing costs, solver/residual checks; no claim of equivalence to elliptical closed form |
| Linear transaction costs | LFB07 | Continuous optimizer and separate share preview | Cost charged once; normalized post-cost weights and residuals; fixed costs/minimum tickets not convex and must not be silently ignored |
| Decisions | Engineering policy; DN90 motivation only | HOLD / REBALANCE / NO_TRADE | Failure precedence, no unsupported improvement claim; independent forecast calibration still needed |
| Baselines / out-of-sample | DGU09; BBLZ | Walk-forward evaluator | Past-only training, same universe, drift/costs, benchmark failures explicit; current revised proxy history limits inference |
| Uncertainty and sensitivity | PR94, GI03 motivation, CKP18 | Block intervals / model comparisons | Conditional on stationarity; multiple tests not corrected; no unsupported PBO or statistical-superiority label |
| Forecast diagnostics | C98 | Coverage and tail diagnostics | One-day horizon, exceedance clustering matters; coverage frequency alone does not validate ES |
| Minimal local interface | Engineering delivery choice | CLI → JSON/HTML | No network write/order execution; actual portfolio unavailable until supplied |

## Acceptance boundaries

E0 mathematical/accounting tests and numerical references can establish that specified formulas were implemented consistently. E1 observed academic proxy evaluation can expose failure modes and hypothesis weaknesses. Neither establishes a profitable, suitable or production-ready investment system. E3 remains contingent on investable point-in-time data and genuinely independent validation.
