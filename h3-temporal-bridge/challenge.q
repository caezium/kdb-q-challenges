/ h3-temporal-bridge
/ Implement tbridge: as-of join with maximum staleness constraint.

tbridge:{[trades;quotes;maxlag] qq:`sym`time xasc `sym`time xcols update qtime:time from quotes; tt:`sym`time xasc update i0:i from trades; r:aj[`sym`time;tt;qq]; r:`i0 xasc r; stale:(r[`time]-r[`qtime])>maxlag; r:update bid:?[stale;0Nf;bid], ask:?[stale;0Nf;ask] from r; delete i0, qtime from r}
