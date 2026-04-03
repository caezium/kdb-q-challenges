"""p1-pykx-roundtrip

Implement roundtrip: lossless Python -> q -> Python type conversion.

roundtrip(data: dict) -> dict
    data: dict with string keys and various Python-typed values
    Returns: dict with same keys, values round-tripped through q via PyKX

You MUST use pykx for the conversion. The challenge is handling
edge cases: NaN, Inf, booleans vs ints, timestamp precision,
nested lists, empty typed lists.
"""


def roundtrip(data: dict) -> dict:
    raise NotImplementedError("Fill in your solution")
