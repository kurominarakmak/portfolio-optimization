# Randomized initial portfolio experiment

**Primary 250-account real-market sample: BLOCKED; 0 admitted.** The asset
admission gate in [the frozen protocol](random_portfolio_protocol.md) was not
met by the audited Alpaca or Tiingo lanes. No current survivor list was used
as a substitute. There are no historical initial weights, paired strategy
outcomes, or valid real-market robustness distributions to report.

The [machine-readable D3 status](../../reports/random_market_experiment_status.json)
records seed 42, the inventory digest, requested count 250, and zero admitted
accounts. It is an explicit blocked result, not a 250-account simulation.

The sampling code is exercised with explicitly synthetic eligibility fixtures
to check deterministic generation, weights, and dated membership logic. Such
fixtures are software tests, not the requested 250 investment research
accounts. A future admitted run must save all 250 definitions before observing
outer-test outcomes, including eligibility records and independent scenario
random streams.

The previous French proxy finding remains in
[the unchanged report](../../reports/empirical_comparison.md): BL-CVaR did not
establish superiority over equal weight on that research series. It cannot
answer the new per-stock randomized-holdings question.
