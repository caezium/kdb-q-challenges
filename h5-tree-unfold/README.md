# h5-tree-unfold

## Problem

Implement `unfold` — build a tree represented as a table from a seed value and a branching function.

```q
unfold:{[f;seed] ... }
```

### Signature

- `f` is a unary function `f[value]` that returns a list of child values. An empty list means the node is a leaf.
- `seed` is the initial root value.
- Returns a table with columns:
  - `id` — sequential long, starting at 0 for root
  - `parent` — long, parent's id (`0N` for root)
  - `value` — the node's value
  - `depth` — long, 0 for root

Nodes are assigned ids in **breadth-first order**.

### Example

```q
/ Binary split: each value splits into (value div 2) and (value - 1), stopping at <=1
f:{$[x>1; (x div 2; x-1); `long$()]}

unfold[f;5]
/ id parent value depth
/ -----------------------
/ 0  0N     5     0
/ 1  0      2     1
/ 2  0      4     1
/ 3  1      1     2
/ 4  1      1     2
/ 5  2      2     2
/ 6  2      3     2
/ 7  5      1     3
/ 8  5      1     3
/ 9  6      1     3
/ 10 6      2     3
/ 11 10     1     4
/ 12 10     1     4
```

### Constraints

- Must handle deep trees: a chain function `{$[x>0;enlist x-1;`long$()]}` with seed 500 produces depth 500. Naive recursion will stack overflow.
- Leaf-only input (f always returns empty) produces a single-row table.
- Must be breadth-first, not depth-first.
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
