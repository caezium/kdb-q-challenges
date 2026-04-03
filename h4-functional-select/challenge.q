/ h4-functional-select
/ Implement qbuild: construct a functional select parse tree from a spec dict.
/
/ qbuild[spec]
/   spec has keys: t (table sym), c (where strings), b (group-by syms), a (agg dict)
/   Returns: a list (the functional form) evaluable with eval
/
/ The result of eval[qbuild spec] must match the equivalent qSQL query.

qbuild:{[spec]
  'nyi}
