/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

\l challenge.q

/ ============================================================
/ Section 1 - Basic Correctness
/ ============================================================
-1 "\n--- Section 1: Basic Correctness ---";

/ Leaf only: f always returns empty list
r1:unfold[{`long$()};42]
assertEq["leaf only: single row count"; 1; count r1]
assertEq["leaf only: id"; enlist 0; r1`id]
assertEq["leaf only: parent is null"; enlist 0N; r1`parent]
assertEq["leaf only: value"; enlist 42; r1`value]
assertEq["leaf only: depth"; enlist 0; r1`depth]

/ Simple binary split: f:{$[x>1;(x div 2;x-1);`long$()]}
bfn:{$[x>1;(x div 2;x-1);`long$()]}
r2:unfold[bfn;5]

/ Verify column names
assertEq["columns"; `id`parent`value`depth; cols r2]

/ Verify root
assertEq["root id"; 0; r2[`id] 0]
assertEq["root parent null"; 0N; r2[`parent] 0]
assertEq["root value"; 5; r2[`value] 0]
assertEq["root depth"; 0; r2[`depth] 0]

/ Verify first children of root (value 5 => children 2, 4)
assertEq["child 1 value"; 2; r2[`value] 1]
assertEq["child 1 parent"; 0; r2[`parent] 1]
assertEq["child 1 depth"; 1; r2[`depth] 1]
assertEq["child 2 value"; 4; r2[`value] 2]
assertEq["child 2 parent"; 0; r2[`parent] 2]
assertEq["child 2 depth"; 1; r2[`depth] 2]

/ Verify ids are sequential
assertEq["ids sequential"; til count r2; r2`id]

/ Total node count for seed=5 with bfn: 13 nodes
assertEq["binary tree node count"; 13; count r2]

/ Chain function: each value decrements by 1 until 0
cfn:{$[x>0;enlist x-1;`long$()]}
r3:unfold[cfn;3]
assertEq["chain: 4 nodes"; 4; count r3]
assertEq["chain: depths"; 0 1 2 3; r3`depth]
assertEq["chain: values"; 3 2 1 0; r3`value]
assertEq["chain: parents"; 0N 0 1 2; r3`parent]

/ Ternary branching: each value produces 3 children (x-1) until x<=0
tfn:{$[x>0; 3#enlist x-1; `long$()]}
r4:unfold[tfn;2]
/ depth 0: 1 node (val=2), depth 1: 3 nodes (val=1 each), depth 2: 9 nodes (val=0 each) = 13 total
assertEq["ternary: node count"; 13; count r4]
assertEq["ternary: root value"; 2; r4[`value] 0]
assertEq["ternary: depth-1 values"; 1 1 1; r4[`value] 1 2 3]

/ ============================================================
/ Section 2 - Anti-Cheat
/ ============================================================
-1 "\n--- Section 2: Anti-Cheat ---";

/ Anti-identity: result is a table, not the seed value
r_ac1:unfold[{`long$()};99]
assert["result is a table not seed"; not 99~r_ac1]
assert["result type is table (98h)"; 98h = type r_ac1]

/ Anti-constant: different seeds produce different trees
r_ac2a:unfold[cfn;3]
r_ac2b:unfold[cfn;5]
assert["anti-constant: different seeds => different trees"; not r_ac2a ~ r_ac2b]

/ Different functions produce different trees
r_ac3a:unfold[bfn;5]
r_ac3b:unfold[cfn;5]
assert["anti-constant: different functions => different trees"; not r_ac3a ~ r_ac3b]

/ Type checks
r_tc:unfold[bfn;5]
assert["type: result is table"; 98h = type r_tc]
assert["type: id is long"; 7h = type r_tc`id]
assert["type: parent is long"; 7h = type r_tc`parent]
assert["type: depth is long"; 7h = type r_tc`depth]

/ BFS order: depths must be non-decreasing
assert["BFS order: depths non-decreasing"; (asc r_tc`depth) ~ r_tc`depth]

/ ============================================================
/ Section 3 - Property Tests
/ ============================================================
-1 "\n--- Section 3: Property Tests ---";

/ Property tests with 30 random seeds using the binary-split function
seeds:2 + 30?20;
{[s]
  r:unfold[bfn;s];
  n:count r;
  nm:"seed=",string s;

  / ids are sequential 0..n-1
  assert["prop ids sequential (",nm,")"; (til n) ~ r`id];

  / root checks
  assert["prop root parent null (",nm,")"; 0N = r[`parent] 0];
  assert["prop root depth 0 (",nm,")"; 0 = r[`depth] 0];

  / Every non-root node's parent has smaller id
  if[n>1;
    nonroot:1 _ r;
    assert["prop parent < id (",nm,")"; all {x[`parent] < x`id} each nonroot];
  ];

  / Depth of child = 1 + depth of parent
  if[n>1;
    pids:r[`parent] 1 + til n-1;
    pdepths:r[`depth] pids;
    cdepths:r[`depth] 1 + til n-1;
    assert["prop depth = parent depth + 1 (",nm,")"; all cdepths = pdepths + 1];
  ];

  / Every parent id exists in the id column
  if[n>1;
    parentIds:distinct r[`parent] where not null r`parent;
    assert["prop all parents exist (",nm,")"; all parentIds in r`id];
  ];

  / Number of children of each node matches count f[value]
  {[r;bfn;nm;pid]
    childrenInTree:r[`value] where r[`parent] = pid;
    expectedChildren:bfn r[`value] pid;
    assert["prop child count matches f (",nm,", id=",string[pid],")"; expectedChildren ~ childrenInTree];
  }[r;bfn;nm] each til n;

  } each seeds;

/ ============================================================
/ Section 4 - Performance
/ ============================================================
-1 "\n--- Section 4: Performance ---";

/ Deep chain: seed 500 => 501 nodes, must not stack overflow
st1:.z.P;
r_deep:unfold[{$[x>0;enlist x-1;`long$()]};500];
elapsed1:(`long$.z.P - st1) div 1000000;
assertEq["deep chain: node count"; 501; count r_deep]
assertEq["deep chain: max depth"; 500; max r_deep`depth]
-1 "  perf: deep chain (501 nodes) in ",string[elapsed1],"ms";
assert["deep chain < 3000ms"; elapsed1 < 3000]

/ Wide binary tree: seed 14, f produces two children (x-1,x-1) until x<=0
/ This gives 2^15 - 1 = 32767 nodes
widefn:{$[x>0;(x-1;x-1);`long$()]}
st2:.z.P;
r_wide:unfold[widefn;14];
elapsed2:(`long$.z.P - st2) div 1000000;
assertEq["wide tree: node count"; 32767; count r_wide]
-1 "  perf: wide tree (32767 nodes) in ",string[elapsed2],"ms";
assert["wide tree < 5000ms"; elapsed2 < 5000]

/ Verify BFS property on wide tree: depths non-decreasing
assert["wide tree BFS order"; (asc r_wide`depth) ~ r_wide`depth]

/ ============================================================
summary[]
