/ h3-temporal-bridge
/ Implement tbridge: as-of join with maximum staleness constraint.
/
/ tbridge[trades;quotes;maxlag]
/   trades: table with sym, time, price
/   quotes: table with sym, time, bid, ask
/   maxlag: timespan — max allowed age of quote at trade time
/   Returns: trades with bid, ask joined; stale quotes replaced with 0Nf
/
/ When maxlag=0W, must match standard aj exactly.

tbridge:{[trades;quotes;maxlag]
  'nyi}
