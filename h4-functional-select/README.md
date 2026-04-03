# h4-functional-select

## Problem

Implement `qbuild` — build a functional select expression from a specification dictionary.

```q
qbuild:{[spec] ... }
```

### Signature

- `spec` is a dictionary with keys:
  - `t` — table name (symbol)
  - `c` — where clauses: a list of strings, each a valid q where-expression (e.g., `"price>100"`)
  - `b` — group-by columns: a symbol list (e.g., `` `sym ``)
  - `a` — aggregations: a dictionary mapping output column names to expressions as strings (e.g., `` `avgPrice`cnt!("avg price";"count i") ``)
- Returns a list representing the functional form `(parse "?";t;c;b;a)` that can be evaluated with `eval` to produce the query result.

### Example

```q
t:([] sym:`AAPL`GOOG`AAPL`GOOG; price:150 200 155 210; vol:100 200 150 300)

spec:`t`c`b`a!(`t; enlist "price>100"; `sym; `avgPrice`totalVol!("avg price";"sum vol"))

r:qbuild spec
/ r is a parse tree: (parse "?"; `t; enlist (parse "price>100"); ...; ...)
eval r
/ => sym  | avgPrice totalVol
/ => -----| -----------------
/ => AAPL | 152.5    250
/ => GOOG | 205      500
```

### Constraints

- Output must be a list (the parse tree), NOT the result of running the query.
- Empty where clause (`()`) means no filter.
- Empty group-by (`` `$() ``) means no grouping.
- Empty aggregations means select all columns (the `a` parameter should be `0b`).
- Must handle enlist correctly for single where clauses (the parse tree needs `enlist` for single constraints).
- Solution should be under ~20 lines.

### Running
```bash
q tests.q
```
