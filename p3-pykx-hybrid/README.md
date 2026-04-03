# p3-pykx-hybrid

## Problem

Implement `hybrid_pipeline` — a data pipeline that requires both Python (feature engineering) and q (time-series operations) to solve correctly.

```python
def hybrid_pipeline(trades: list[dict], model_fn, lookback: int) -> list[dict]:
    ...
```

### Signature

- `trades` is a list of dicts with keys: `sym` (str), `time` (datetime), `price` (float), `size` (int). Sorted by time.
- `model_fn` is a Python callable `model_fn(features: dict) -> float` that takes a feature dict and returns a signal score (float). This is a "black box" — you cannot reimplement it in q.
- `lookback` is an int — the number of prior trades to use for feature computation.
- Returns a list of dicts, one per trade (from index `lookback` onward), with keys:
  - `sym`, `time`, `price` — from the original trade
  - `signal` — the output of `model_fn` for that trade's features
  - `vwap` — volume-weighted average price over the lookback window (must be computed in q via PyKX)
  - `volatility` — standard deviation of prices in the lookback window (must be computed in q via PyKX)
  - `spread` — `price - vwap` for that trade

### Feature Dict (input to model_fn)

For each trade at index `i` (where `i >= lookback`), the feature dict is:

```python
{
    "vwap": <vwap over trades[i-lookback:i]>,         # computed in q
    "volatility": <sdev of prices in trades[i-lookback:i]>,  # computed in q
    "price": <current trade price>,
    "size": <current trade size>,
    "spread": <price - vwap>,
}
```

### Constraints

- **VWAP and volatility MUST be computed in q via PyKX** — not in Python.
- **model_fn MUST be called in Python** — it cannot be expressed in q.
- This forces a true hybrid pipeline: q for time-series math, Python for the model.
- Output starts from index `lookback` (first `lookback` trades are the warmup).
- Solution should be under ~30 lines.

### Running

```bash
python -m pytest tests.py -v
```
