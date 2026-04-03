# j1-lazy-scan

## Problem

Implement `scanz` — a scan that supports early termination.

```q
scanz:{[f;init;data] ... }
```

### Signature

- `f` is a binary function `f[accumulator;element]` that returns a two-element list `(continue;newValue)` where `continue` is a boolean.
- `init` is the initial accumulator value.
- `data` is a list of elements to scan over.
- Returns the list of accumulator values, starting with `init`, up to and including the value at which `f` first returns `0b` for `continue`.

### Example

```q
/ Running sum, stop when total >= 10
scanz[{(x+y<10; x+y)}; 0; 1 2 3 4 5 6]
/ => 0 1 3 6 10
/    ^init   ^stopped here (6+4=10, 10<10 is 0b)
```

### Constraints

- Must actually short-circuit: if `f` returns `0b` on the 3rd element of a 10-million-element list, your function must return in microseconds, not seconds.
- Empty data returns `enlist init`.
- Must work with any accumulator type (longs, floats, symbols, etc.).
- Solution should be under ~20 lines of q.

### Running

```bash
q tests.q
```
