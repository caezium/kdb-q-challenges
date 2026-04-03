# h7-adverb-algebra

## Problem

Implement `slideScan` -- an incremental sliding-window scan.

```q
slideScan:{[f;w;data] ... }
```

### Signature

- `f` is a ternary function `f[prevResult;entering;exiting]` that incrementally updates the window result when one element enters and one exits.
- `w` is the window size (positive long).
- `data` is a list of values.
- Returns a list of window results, one per position in `data`, where position `i` covers elements `max(0,i-w+1)` through `i`.

For the first `w-1` positions (partial windows), `exiting` is `0N` (null of the data type) -- meaning no element is leaving the window yet.

### Example

```q
/ Incremental sum: add entering, subtract exiting
f:{[prev;enter;exit] prev + enter - $[null exit;0;exit]}

slideScan[f;3;1 2 3 4 5]
/ Position 0: window=[1],        f[0;1;0N]  = 1
/ Position 1: window=[1,2],      f[1;2;0N]  = 3
/ Position 2: window=[1,2,3],    f[3;3;0N]  = 6
/ Position 3: window=[2,3,4],    f[6;4;1]   = 9
/ Position 4: window=[3,4,5],    f[9;5;2]   = 12
/ => 1 3 6 9 12
```

### Constraints

- Must be incremental: `f` should be called approximately `n` times, not `n*w` times.
- This is verified by counting function invocations.
- The initial "prevResult" for position 0 is `0` (long zero) -- the identity for common operations.
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
