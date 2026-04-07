/ h5-tree-unfold
/ Implement unfold: build a BFS tree-table from a branching function and seed.
/ .
/ unfold[f;seed]
/   f: unary, returns list of child values (empty = leaf)
/   seed: root value
/   Returns: table with id, parent, value, depth columns
/            Nodes in breadth-first order with sequential ids.

unfold:{[f;seed] 'nyi}
