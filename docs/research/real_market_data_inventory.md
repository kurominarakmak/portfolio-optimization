# Real market data audit (2026-10-26)

The requested real-stock/ETF walk-forward is **BLOCKED**. The available local
Alpaca lane contains observed US stock bars, but they are raw IEX prices, with
`div_cash`, `split_factor`, and adjusted close absent. Raw close-to-close changes
are not corporate-action-aware total returns. The source registry also marks
Alpaca licensing `REVIEW_REQUIRED` and `production_approved: false`. Alpaca's
[historical bars reference](https://docs.alpaca.markets/us/reference/stockbars)
confirms that `raw` means no adjustment and that `iex` is a single-exchange feed.

The local Tiingo lane contains 896 symbol files with raw and vendor-adjusted
prices plus split/dividend fields. Its adjusted series was captured in 2026 and
is explicitly marked non-point-in-time in the source project's
`docs/data/point-in-time-contract.md`; vendor and derived-data usage rights remain
unverified. The membership file carries local `SEC...` IDs, but its own field
audit says many historical identity and membership dates are inferred or only
supported by secondary references. These facts do not establish the complete
point-in-time tradable universe, delisting settlement, or executable historical
returns required by the new protocol. We have not silently promoted either lane.

The per-asset [inventory CSV](../../reports/real_market_asset_inventory.csv)
records provider, symbol, local security ID where available, date coverage,
observed rows or source-reported sessions, gaps, adjustment, currency, license,
corporate-action status, point-in-time status, and executable-research suitability.
It is metadata only; it does not copy price bars. Source paths and registry
status are recorded in the CSV. A missing value means unverified, not zero.

| Source | Observed inventory | Main limit | Decision |
| --- | ---: | --- | --- |
| Alpaca normalized `membership_pit` | 1,063 security files; 667 nonempty; 792,198 bars; 135 labeled full prototype coverage, 532 partial | IEX/raw, no dividends/splits, 9,991 reported missing cross-series sessions, unverified rights | Block total-return replay |
| Tiingo normalized `membership_pit` | 896 ticker files; 2,373,669 rows counted | 2026 back-adjusted values are not historical PIT observations; identity, terminal actions, and rights need qualification | Block requested PIT replay |
| French five-industry research portfolios | 5 observed academic series | Constructed portfolios, not individual tradable securities | Preserve previous proxy lane only |
| Synthetic demo | Fixture only | No observed market history | Tests only |

The Alpaca report's completeness grid is cross-series, not independently
exchange-certified. The project's separate XNYS calendar is present, but no
asset-by-asset total-return and corporate-action reconciliation against it was
completed here. The Alpaca feed's single-exchange close also cannot establish
executable consolidated closing prices. No genuine current holdings snapshot or
broker connection was supplied in this task.

Audit inputs: `/Users/manpao/Downloads/ai-us-equity-portfolio-consultant/alpaca_coverage_report.csv`,
`alpaca_security_mapping.csv`, `membership_pit_v1.csv`,
`config/data-sources.yaml`, `docs/data/alpaca-prototype.md`, and local normalized
Alpaca/Tiingo directories. The source project's reports have different review
dates; this inventory records what was accessible on 2026-10-26, without
asserting that earlier approval labels qualify this new experiment.
