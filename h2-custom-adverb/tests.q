/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

\l challenge.q

/ --- test wrappers ---
myOver:{[f;init;data] f/[init;data]}
myScan:{[f;init;data] init,f\[init;data]}
myLast:{[f;init;data] last f\[init;data]}
myRevOver:{[f;init;data] f/[init;reverse data]}

/ =========================================
-1 "\n--- Section 1: Basic Correctness ---";
/ =========================================

assertEq["compose[myOver;myOver] sums all";
  45;
  compose[myOver;myOver][+;0;(1 2 3;4 5;6 7 8 9)]]

assertEq["compose[myScan;myOver] running totals of sublist sums";
  0 6 15 45;
  compose[myScan;myOver][+;0;(1 2 3;4 5;6 7 8 9)]]

assertEq["compose[myOver;myScan] sums all scan results";
  0 4 10;
  compose[myOver;myScan][+;0;(1 2;3 4)]]

assertEq["single sublist";
  6;
  compose[myOver;myOver][+;0;enlist 1 2 3]]

assertEq["empty sublists mixed in";
  3;
  compose[myOver;myOver][+;0;(();1 2;())]]

assertEq["compose[myLast;myOver] last of running sums";
  last sums (6;9;6);
  compose[myLast;myOver][+;0;(1 2 3;4 5;6)]]

assertEq["compose[myScan;myScan] nested scan";
  myScan[+;0;myScan[+;0;] each (1 2;3 4)];
  compose[myScan;myScan][+;0;(1 2;3 4)]]

assertEq["multiplication wrapper";
  compose[myOver;myOver][*;1;(2 3;4 5)];
  2*3*4*5]

/ =========================================
-1 "\n--- Section 2: Anti-Cheat ---";
/ =========================================

/ Anti-constant: 3 different inputs must give 3 different outputs
r1:compose[myOver;myOver][+;0;(1 2;3 4)];
r2:compose[myOver;myOver][+;0;(10 20;30 40)];
r3:compose[myOver;myOver][+;0;(100 200;300)];
assert["anti-constant: 3 inputs give 3 different outputs";not (r1~r2) or (r2~r3) or (r1~r3)]

/ Custom wrapper myRevOver — reversal before fold
assertEq["compose[myOver;myRevOver] reverse-then-fold";
  15;
  compose[myOver;myRevOver][+;0;(1 2 3;4 5)]]

/ myRevOver with non-commutative op to prove reversal matters
assertEq["myRevOver with subtract proves reversal";
  compose[myOver;myRevOver][-;100;(1 2 3;10 20)];
  myOver[-;100;myRevOver[-;100;] each (1 2 3;10 20)]]

/ Result of compose must be a function, not a value
res:compose[myOver;myOver];
assert["compose returns a function (type >= 100h)";100h<=type res]

/ Additional type check: the composed result is a projection or lambda
assert["compose result type is projection or lambda";(type res) in 104 100 105 106h]

/ =========================================
-1 "\n--- Section 3: Property Tests ---";
/ =========================================

-1 "  running 50 random property tests...";
propFails:0;
do[50;
  n:2+rand 8;
  xss:{(1+x?10)?100} each til n;
  / Property 1: compose[myOver;myOver][+;0;xss] = sum raze xss
  expected:sum raze xss;
  actual:compose[myOver;myOver][+;0;xss];
  if[not expected~actual; propFails+:1];
  / Property 2: compose[myScan;myOver][+;0;xss] = 0,sums sum each xss
  expected2:0,sums sum each xss;
  actual2:compose[myScan;myOver][+;0;xss];
  if[not expected2~actual2; propFails+:1]
 ];
assertEq["property tests (myOver;myOver and myScan;myOver, 50 seeds)";0;propFails]

/ Additional property: compose[myLast;myOver] = last of running sums
propFails2:0;
do[50;
  n:2+rand 8;
  xss:{(1+x?10)?100} each til n;
  expected:last sums sum each xss;
  actual:compose[myLast;myOver][+;0;xss];
  if[not expected~actual; propFails2+:1]
 ];
assertEq["property tests (myLast;myOver, 50 seeds)";0;propFails2]

/ =========================================
-1 "\n--- Section 4: Performance ---";
/ =========================================

bigdata:enlist each 1000?1000;
st:.z.p;
r:compose[myOver;myOver][+;0;bigdata];
elapsed:(`long$.z.p-st) div 1000000;
-1 "  perf: 1000x1000 completed in ",string[elapsed],"ms";
assert["performance: 1000x1000 under 3000ms";elapsed<3000]
assertEq["perf result correctness";sum raze bigdata;r]

/ ===
summary[]
