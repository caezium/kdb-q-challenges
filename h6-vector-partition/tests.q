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

/ Single key
r1:vpart[enlist `a`b`a`b; 10 20 30 40];
assertEq["single key - a group"; 10 30; r1[enlist `a]];
assertEq["single key - b group"; 20 40; r1[enlist `b]];
assert["single key - 2 groups"; 2=count r1];

/ Two keys
r2:vpart[(`a`b`a`b`a; 1 1 2 1 2); 10 20 30 40 50];
assertEq["two keys - (a;1)"; enlist 10; r2[(`a;1)]];
assertEq["two keys - (b;1)"; 20 40; r2[(`b;1)]];
assertEq["two keys - (a;2)"; 30 50; r2[(`a;2)]];
assert["two keys - 3 groups"; 3=count r2];

/ Single-element groups
r3:vpart[enlist `x`y`z; 100 200 300];
assertEq["single-element groups - x"; enlist 100; r3[enlist `x]];
assertEq["single-element groups - y"; enlist 200; r3[enlist `y]];
assertEq["single-element groups - z"; enlist 300; r3[enlist `z]];

/ All same key
r4:vpart[enlist `a`a`a; 1 2 3];
assertEq["all same key"; 1 2 3; r4[enlist `a]];
assert["all same key - 1 group"; 1=count r4];

/ Three key columns
r5:vpart[(`a`a`b`b; 1 1 1 2; `x`y`x`x); 10 20 30 40];
assertEq["three keys - (a;1;x)"; enlist 10; r5[(`a;1;`x)]];
assertEq["three keys - (a;1;y)"; enlist 20; r5[(`a;1;`y)]];
assertEq["three keys - (b;1;x)"; enlist 30; r5[(`b;1;`x)]];
assertEq["three keys - (b;2;x)"; enlist 40; r5[(`b;2;`x)]];
assert["three keys - 4 groups"; 4=count r5];

/ Order preservation
r6:vpart[enlist `a`b`a`b`a`b; 1 2 3 4 5 6];
assertEq["order preserved - a"; 1 3 5; r6[enlist `a]];
assertEq["order preserved - b"; 2 4 6; r6[enlist `b]];

/ Numeric keys
r7:vpart[enlist 1 2 1 2 1; `p`q`r`s`t];
assertEq["numeric keys - 1"; `p`r`t; r7[enlist 1]];
assertEq["numeric keys - 2"; `q`s; r7[enlist 2]];

/ ============================================================
/ Section 2 - Anti-Cheat
/ ============================================================
-1 "\n--- Section 2: Anti-Cheat ---";

/ Source code inspection: no each, do, while
src:string vpart;
assert["no each in source"; not any src ss "each"];
/ Use careful patterns to avoid false positives with "do" inside words
/ Check for " do[" or " do " which are the loop forms
hasDo:(any src ss " do[[]") or (any src ss " do ") or (any src ss "\tdo[[]") or (any src ss "\tdo ");
assert["no do loop in source"; not hasDo];
assert["no while in source"; not any src ss "while"];

/ Anti-constant: different inputs produce different results
rc1:vpart[enlist `a`b`a; 10 20 30];
rc2:vpart[enlist `x`y`x; 40 50 60];
assert["anti-constant"; not rc1 ~ rc2];

/ Anti-identity: result is a dictionary, not the input data
ri:vpart[enlist `a`b`a; 10 20 30];
assert["anti-identity"; not ri ~ 10 20 30];

/ Type check: result is a dictionary
assert["result is dict"; 99h = type ri];

/ Keys are lists (compound keys)
assert["keys are lists"; all 0h = type key ri];

/ ============================================================
/ Section 3 - Property Tests (50 random seeds)
/ ============================================================
-1 "\n--- Section 3: Property Tests ---";

propPass:0; propTotal:0;
seeds:42 + til 50;
{[s]
  system "S ",string s;
  n:10 + s mod 50;
  syms:`a`b`c`d`e;
  k1:n ? syms;
  k2:n ? 1 2 3;
  d:n ? 100;

  r:vpart[(k1;k2); d];

  / Property 1: raze of values has same count as data
  allVals:raze value r;
  c1:(count allVals) = count d;

  / Property 2: sum of group counts = count data
  c2:(sum count'[value r]) = count d;

  / Property 3: all values in result come from data (same multiset)
  c3:(asc allVals) ~ asc d;

  / Property 4: result matches group-based indexing
  idx:group flip (k1;k2);
  c4:r ~ (key idx)!d idx key idx;

  / Property 5: result keys and group keys match in order
  c5:(key r) ~ key idx;

  propTotal+:5;
  if[c1; propPass+:1];
  if[c2; propPass+:1];
  if[c3; propPass+:1];
  if[c4; propPass+:1];
  if[c5; propPass+:1];
 } each seeds;

assert["property tests pass rate"; propPass = propTotal];

/ Simpler targeted property tests
-1 "  Running targeted property checks...";

/ For single key, verify against built-in group
\S 99
n2:100;
k:n2 ? `a`b`c`d;
d2:n2 ? 1000;
rSingle:vpart[enlist k; d2];
gBuiltin:group k;
/ Check that the grouping structure matches
expected:(enlist each key gBuiltin)!d2 value gBuiltin;
assert["single key matches group builtin"; expected ~ rSingle];

/ ============================================================
/ Section 4 - Performance
/ ============================================================
-1 "\n--- Section 4: Performance ---";

\S 123
N:1000000;
bigK1:N ? `sym1`sym2`sym3`sym4`sym5`sym6`sym7`sym8`sym9`sym10;
bigK2:N ? til 10;
bigK3:N ? til 10;
bigD:N ? 10000.0;

st:.z.p;
rPerf:vpart[(bigK1;bigK2;bigK3); bigD];
et:.z.p;
ms:(`long$(et - st)) % 1000000;
-1 "  performance: ",string[ms],"ms for 1M rows";
assert["performance < 3000ms"; ms < 3000];
assert["performance result is dict"; 99h = type rPerf];
assert["performance correct count"; N = sum count'[value rPerf]];

/ ============================================================
summary[]
