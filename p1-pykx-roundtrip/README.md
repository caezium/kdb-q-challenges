# p1-pykx-roundtrip

## Problem

Implement `roundtrip` — lossless Python-to-q-to-Python type conversion for edge-case types.

```python
def roundtrip(data: dict) -> dict:
    ...
```

### Signature

- `data` is a Python dictionary with string keys and values of various types:
  - `"longs"`: list of Python ints
  - `"floats"`: list of Python floats, possibly containing `float('nan')` and `float('inf')`
  - `"symbols"`: list of Python strings to be treated as q symbols
  - `"timestamps"`: list of `datetime.datetime` objects
  - `"booleans"`: list of Python bools
  - `"nested"`: a list of lists of ints (nested structure)
  - `"mixed"`: a general list with mixed types

- Your function must:
  1. Convert each value to its appropriate q/kdb+ type using PyKX
  2. Perform a round-trip: Python → q → Python
  3. Return a dictionary with the same keys, where each value has been converted back to a Python-native type that matches the original

### Constraints

- `float('nan')` must survive the round-trip (nan == nan is False, use `math.isnan`)
- `float('inf')` must survive as infinity
- Booleans must come back as Python `bool`, not `int` (PyKX can mangle this)
- Timestamps must preserve microsecond precision
- Nested lists must maintain their structure
- Empty lists must preserve their type hint (an empty long list stays typed, not generic)
- You MUST use `pykx` for the conversion — no passthrough/identity tricks

### Running

```bash
python -m pytest tests.py -v
```
