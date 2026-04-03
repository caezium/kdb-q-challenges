# h2-custom-adverb

## Problem

Implement `compose` — compose two "iterator-wrappers" into a new one.

An iterator-wrapper is a triadic function `iw[f;init;data] -> result` with the same signature as how `over` and `scan` are used with initial values.

```q
compose:{[outer;inner] ... }
```

### Signature

- `outer` and `inner` are both iterator-wrappers (triadic: `iw[f;init;data] -> result`)
- Returns a new iterator-wrapper such that:
  `compose[outer;inner][f;init;data]` equals `outer[f;init;inner[f;init;] each data]`
  where `data` is a list of lists.

### Example

```q
myOver:{[f;init;data] f/[init;data]}
myScan:{[f;init;data] init,f\[init;data]}

compose[myOver;myOver][+;0;(1 2 3;4 5;6 7 8 9)]
/ => 45  (sum of everything)

compose[myScan;myOver][+;0;(1 2 3;4 5;6 7 8 9)]
/ => 0 6 15 45  (running totals of sublist sums: 6, 9, 30)
```

### Constraints

- Must return a callable triadic function, not a precomputed value.
- Must work with arbitrary iterator-wrappers, not just myOver/myScan.
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
