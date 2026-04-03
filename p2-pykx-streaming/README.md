# p2-pykx-streaming

## Problem

Implement `stream_agg` — a real-time streaming aggregator that processes tick data through PyKX.

```python
def stream_agg(ticks: list[dict], windows: dict) -> dict:
    ...
```

### Signature

- `ticks` is a list of dicts, each with keys: `sym` (str), `time` (datetime), `price` (float), `size` (int). These arrive in time order.
- `windows` is a dict mapping aggregation names to window specs:
  - `{"vwap_5": {"type": "vwap", "n": 5}}` — volume-weighted average price over last 5 ticks per sym
  - `{"max_10": {"type": "max", "field": "price", "n": 10}}` — rolling max price over last 10 ticks per sym
  - `{"sum_size_3": {"type": "sum", "field": "size", "n": 3}}` — rolling sum of size over last 3 ticks per sym
- Returns a dict mapping each sym to a dict of aggregation results (the final value after all ticks processed).

### Example

```python
from datetime import datetime
ticks = [
    {"sym": "AAPL", "time": datetime(2024,1,1,10,0,0), "price": 150.0, "size": 100},
    {"sym": "AAPL", "time": datetime(2024,1,1,10,0,1), "price": 151.0, "size": 200},
    {"sym": "AAPL", "time": datetime(2024,1,1,10,0,2), "price": 149.0, "size": 150},
]
windows = {"vwap_3": {"type": "vwap", "n": 3}}

result = stream_agg(ticks, windows)
# result = {"AAPL": {"vwap_3": 150.111...}}
# VWAP = sum(price*size) / sum(size) = (150*100 + 151*200 + 149*150) / (100+200+150)
```

### Constraints

- **Must use PyKX** to store and compute aggregations in q. The tick data must be inserted into a q table and aggregations computed using q operations (not pure Python math).
- Must handle multiple syms independently.
- Rolling windows are per-sym: `n=5` means last 5 ticks for that specific sym.
- If fewer than `n` ticks have arrived for a sym, compute over available ticks.
- VWAP = sum(price * size) / sum(size) for the window.

### Running

```bash
python -m pytest tests.py -v
```
