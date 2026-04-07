/ h4-functional-select
/ Implement qbuild: construct a functional select parse tree from a spec dict.
/ .
/ qbuild[spec]
/   spec: dict with keys `t (table name), `c (where strings),
/         `b (group-by symbols), `a (agg dict: col!expr-string)
/   Returns: a list (parse tree) that eval can execute as a functional select.

qbuild:{[spec] 'nyi}
