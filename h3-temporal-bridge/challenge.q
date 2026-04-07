/ h3-temporal-bridge
/ Implement tbridge: as-of join with maximum staleness constraint.
/ .
/ tbridge[trades;quotes;maxlag]
/   trades: table (sym, time, price)
/   quotes: table (sym, time, bid, ask)
/   maxlag: timespan — max allowed age of quote at trade time
/   Returns: trades with bid/ask joined; stale quotes nulled to 0Nf.

tbridge:{[trades;quotes;maxlag] 'nyi}
