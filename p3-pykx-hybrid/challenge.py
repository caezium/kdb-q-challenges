"""p3-pykx-hybrid

Implement hybrid_pipeline: a data pipeline combining q (time-series ops)
and Python (model inference).

hybrid_pipeline(trades, model_fn, lookback) -> list[dict]
    trades: list of dicts with sym, time, price, size
    model_fn: Python callable (features dict -> float signal)
    lookback: int, number of prior trades for feature window

VWAP and volatility MUST be computed in q via PyKX.
model_fn MUST be called in Python.
"""


def hybrid_pipeline(
    trades: list[dict], model_fn, lookback: int
) -> list[dict]:
    raise NotImplementedError("Fill in your solution")
