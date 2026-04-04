/ h5-tree-unfold
/ Implement unfold: build a BFS tree-table from a branching function and seed.
/ .
/ unfold[f;seed]
/   f: unary, returns list of child values (empty = leaf)
/   seed: root value
/   Returns: table with id, parent, value, depth columns
/            Nodes in breadth-first order with sequential ids.

unfold:{[f;seed]
  s0:(enlist(`long$0;0N;seed;`long$0); enlist(0;seed;0); 1);
  step:{[f;s]
    acc:(();();s 2);
    acc:{[f;acc;nd]
      cv:f nd 1;
      {[pid;dep;a;c]
        (a[0],enlist(`long$a 2;`long$pid;c;`long$dep+1);
         a[1],enlist(a 2;c;dep+1);
         1+a 2)
      }[nd 0;nd 2]/[acc;cv]
    }[f]/[acc;s 1];
    (s[0],acc 0; acc 1; acc 2)
  }[f];
  s:step/[{0<count x 1};s0];
  flip `id`parent`value`depth!flip s 0}
