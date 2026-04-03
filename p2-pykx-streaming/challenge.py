"""p2-pykx-streaming

Implement stream_agg: real-time streaming aggregator using PyKX.

stream_agg(ticks, windows) -> dict
    ticks: list of dicts with sym, time, price, size
    windows: dict of aggregation specs (vwap, max, sum with window size n)
    Returns: dict[sym -> dict[agg_name -> final_value]]

You MUST use PyKX to store data in q tables and compute aggregations
using q operations. Pure Python math will fail anti-cheat checks.
"""


def stream_agg(ticks: list[dict], windows: dict) -> dict:
    raise NotImplementedError("Fill in your solution")
