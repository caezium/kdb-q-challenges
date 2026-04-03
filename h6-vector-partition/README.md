# h6-vector-partition

## Problem

Implement `vpart` -- partition data into groups by compound keys, fully vectorized.

```q
vpart:{[keys;data] ... }
```

### Signature

- `keys` is a list of key-lists (each the same length as `data`). Think of it as the columns of a compound key.
- `data` is a list of values to partition.
- Returns a dictionary mapping each unique compound key (as a list) to the corresponding data values, **preserving order** within each group.

### Example

```q
vpart[(`a`b`a`b`a; 1 1 2 1 2); 10 20 30 40 50]
/ => (`a;1) | ,10
/ => (`b;1) | 20 40
/ => (`a;2) | 30 50
```

### Constraints

- **No `each`, `do`, or `while` in your solution.** Fully vectorized.
- This constraint is verified by source code inspection.
- Must handle 1 to N key columns.
- Must preserve original order within each group.
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
