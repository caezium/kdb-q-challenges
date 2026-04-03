# h3-temporal-bridge

## Problem

Implement `tbridge` — an as-of join with a maximum staleness constraint.

```q
tbridge:{[trades;quotes;maxlag] ... }
```

### Signature

- `trades` is a table with columns `sym` (symbol), `time` (timestamp), `price` (float).
- `quotes` is a table with columns `sym` (symbol), `time` (timestamp), `bid` (float), `ask` (float).
- `maxlag` is a timespan — the maximum allowed age of a quote at trade time.
- Returns the trades table with `bid` and `ask` columns joined, but any quote older than `maxlag` from the trade time is replaced with null (`0Nf`).

### Example

```q
trades:([] sym:`AAPL`AAPL; time:10:00:00 10:00:30; price:150.0 151.0)
quotes:([] sym:`AAPL`AAPL; time:09:59:50 10:00:25; bid:149.5 150.5; ask:150.5 151.5)

tbridge[trades;quotes;0D00:00:15]
/ First trade at 10:00:00: nearest quote at 09:59:50 (10s ago, < 15s) => bid:149.5, ask:150.5
/ Second trade at 10:00:30: nearest quote at 10:00:25 (5s ago, < 15s) => bid:150.5, ask:151.5

tbridge[trades;quotes;0D00:00:05]
/ First trade at 10:00:00: nearest quote at 09:59:50 (10s ago, > 5s) => bid:0Nf, ask:0Nf
/ Second trade at 10:00:30: nearest quote at 10:00:25 (5s ago, <= 5s) => bid:150.5, ask:151.5
```

### Constraints

- Both tables must be sorted by sym,time (use `s#` or sort as needed).
- When `maxlag` is `0W` (positive infinity timespan), behavior must match standard `aj` exactly.
- Must handle multiple syms correctly.
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
