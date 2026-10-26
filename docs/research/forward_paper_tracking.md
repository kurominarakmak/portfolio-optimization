# Forward paper tracking

The local infrastructure is implemented and fixture-checked. **Actual forward
tracking is NOT_STARTED:** no genuine holdings snapshot, approved historical
return panel, or subsequent verified market observation was supplied. The
[saved synthetic cohort](../../reports/synthetic_paper_status.json) has three
books, zero forward observations, `NO_TRADE`, and `NOT_STARTED`. Its snapshot
and journal are in `reports/synthetic_paper_cohort/` and are explicitly
engineering fixtures.

`portfolio-engine paper-start` takes the existing strict holdings CSV format
or an already normalized read-only Webull result through the Python API. The
snapshot freezes valuation, original positions, history available by the
decision date, model/config/data/proposal fingerprints, whole-share target
preview, expected costs, and the first decision. The independent books are:
original holdings held; a 90% equal-risky/10% cash target once then held; and
the optimized whole-share exploratory target once then held. If a preview is
infeasible, its failure is recorded and that book holds the original shares.
No book sends broker orders.

`paper-update` accepts a complete cumulative daily total-return panel. It
rejects changes to frozen or previously observed rows, newly inserted past
rows, future-dated observed retrieval/session times, and unreconciled NAV.
An explicit synthetic replay mode permits fixture dates only for synthetic
nongenuine cohorts and never starts live tracking. Updates carry quantities,
cash, drifted weights, modeled costs, NAV, forecast diagnostics, and a UTC
update timestamp. Initial modeled transaction costs are charged once. Future
return units include reinvested distributions and are **statistical units**;
they are not executable raw share prices or proof of fills.

The first snapshot is immutable by exclusive creation. Later events are
hash-chained, file locked, flushed, and compared to a separately committed
last sequence/hash. A missing or altered event, complete-record rollback, or
interrupted append/head update fails closed. This local integrity check is not
an adversarial signature or external timestamp. Full commands and input
contracts are in [README](../../README.md).

The fixture demonstration uses the synthetic AAA/BBB/CCC portfolio only.
Actual Webull eligibility, credentials, independent valuation timestamp,
licensed total returns, observed future prices, and long enough forward tails
remain unverified. The first frozen model is not retrained during updates, and
the first cohort uses one initial hypothetical allocation followed by holding;
it does not claim periodic forward rebalancing.
