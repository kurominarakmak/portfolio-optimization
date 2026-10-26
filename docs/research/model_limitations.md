# Limitations of the extension

The requested 250-account empirical conclusion is unavailable because the
historical asset admission gate failed. The local Alpaca bars are raw prices
from IEX. The separate Tiingo adjusted values were retrieved after the
historical dates and are not point-in-time observations. Local security IDs and
historical membership contain inferred boundaries. Licensing status is review
required. Delisting and complex corporate actions lack full terminal-return
proof. These gaps may bias asset selection, returns, turnover, and apparent
tail-risk reductions.

The model's default Black–Litterman prior is explicitly zero excess return
with no historical views. Under those settings it cannot demonstrate
incremental BL information over minimum CVaR. No parameters were tuned using
the new final test period, and the existing French results remain negative or
inconclusive for investment advantage.

Paper results based on synthetic fixtures only validate accounting and state
transitions. Actual holdings, live broker access, current prices, and forward
outcomes have not been supplied. A `NO_TRADE` decision must remain distinct
from an exploratory simulated target. Neither software test success nor a
future statistical return replay establishes executable fills, investor
suitability, or real-money readiness.
