# Real-stock/ETF walk-forward

**BLOCKED before D4.** Alpaca data are historical US stock observations, but
the local normalized bars request IEX/raw and contain no dividend, split, or
adjusted-price fields. Tiingo data include captured vendor-adjusted history,
yet that series is not point-in-time and the source project's identity,
terminal-action, and licensing qualifications are not complete for this
protocol. See [asset audit](real_market_data_inventory.md).

No qualified 504-observation training panel and matched 63-session test window
was admitted. Thus this new experiment tested **zero years and zero sessions**,
and generated no forecasts, trades, daily NAV paths, tail-risk metrics,
environment splits, sensitivity estimates, paired uncertainty intervals, or
HTML performance plots. We did not substitute synthetic returns, French
portfolios, or raw-close price changes for observed equity total returns.

Once a qualified dataset exists, the [frozen protocol](random_portfolio_protocol.md)
governs the run. Daily returns alone can support at most a statistical return
replay until actual execution timestamps, tradable prices, dividends, and
whole-share conventions are independently reconciled. All 250 accounts share
market shocks, so account counts must not be treated as independent market
histories.
