/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

\l challenge.q

/ Incremental sum function used throughout tests
fsum:{[prev;enter;exit] prev + enter - $[null exit;0;exit]}

/ ============================================================
/ Section 1 - Basic Correctness
/ ============================================================
-1 "\n--- Section 1: Basic Correctness ---";

/ Incremental sum example from README
assertEq["sum w=3, 1 2 3 4 5"; 1 3 6 9 12; slideScan[fsum;3;1 2 3 4 5]];

/ Window size 1: each element is its own window
/ f[0;x;0N] = x for each element, since no exiting
assertEq["w=1, each elem standalone"; 1 2 3 4 5; slideScan[fsum;1;1 2 3 4 5]];

/ Window size = data length: one full window at the end
/ w=5, data=1 2 3 4 5 => cumulative sums: 1 3 6 10 15
assertEq["w=data length"; 1 3 6 10 15; slideScan[fsum;5;1 2 3 4 5]];

/ Window size > data length: all partial windows, no exiting ever
/ w=10, data=1 2 3 4 5 => same as cumsum: 1 3 6 10 15
assertEq["w > data length"; 1 3 6 10 15; slideScan[fsum;10;1 2 3 4 5]];

/ Single element
assertEq["single element"; enlist 5; slideScan[fsum;3;enlist 5]];

/ Window size 2
assertEq["w=2"; 1 3 5 7 9; slideScan[fsum;2;1 2 3 4 5]];

/ All zeros
assertEq["all zeros"; 0 0 0 0 0; slideScan[fsum;3;0 0 0 0 0]];

/ Negative numbers
assertEq["negative numbers"; -1 -3 -6 -9 -12; slideScan[fsum;3;-1 -2 -3 -4 -5]];

/ Two elements, window 2
assertEq["two elems w=2"; 10 30; slideScan[fsum;2;10 20]];

/ Longer sequence with w=4
/ data: 1 2 3 4 5 6 7 8
/ msum 4: 1 3 6 10 14 18 22 26
assertEq["w=4, longer seq"; 1 3 6 10 14 18 22 26; slideScan[fsum;4;1 2 3 4 5 6 7 8]];

/ ============================================================
/ Section 2 - Anti-Cheat
/ ============================================================
-1 "\n--- Section 2: Anti-Cheat ---";

/ Invocation counting: verify incremental (n calls, not n*w)
CNT:0;
fCounted:{[prev;enter;exit] CNT+:1; prev + enter - $[null exit;0;exit]};
slideScan[fCounted;10;til 1000];
-1 "  invocation count: ",string[CNT]," (expect ~1000)";
assert["incremental: n calls not n*w"; CNT < 1500];
assert["incremental: at least n calls"; CNT >= 999];

/ Invocation counting with larger window
CNT2:0;
fCounted2:{[prev;enter;exit] CNT2+:1; prev + enter - $[null exit;0;exit]};
slideScan[fCounted2;100;til 5000];
-1 "  invocation count (w=100,n=5000): ",string[CNT2]," (expect ~5000)";
assert["incremental large w: n calls not n*w"; CNT2 < 7500];
assert["incremental large w: at least n calls"; CNT2 >= 4999];

/ Anti-constant: different data produces different results
r1:slideScan[fsum;3;1 2 3 4 5];
r2:slideScan[fsum;3;10 20 30 40 50];
assert["anti-constant"; not r1 ~ r2];

/ Anti-identity: result differs from input
r3:slideScan[fsum;3;1 2 3 4 5];
assert["anti-identity"; not r3 ~ 1 2 3 4 5];

/ Result length = data length
assert["result length = data length (5)"; 5 = count slideScan[fsum;3;1 2 3 4 5]];
assert["result length = data length (1)"; 1 = count slideScan[fsum;3;enlist 7]];
assert["result length = data length (10)"; 10 = count slideScan[fsum;2;til 10]];

/ ============================================================
/ Section 3 - Property Tests (50 random seeds)
/ ============================================================
-1 "\n--- Section 3: Property Tests ---";

propPass:0; propTotal:0;
seeds:42 + til 50;
{[s]
  \S s;
  n:5 + s mod 100;
  w:1 + s mod 20;
  d:n ? 100;

  r:slideScan[fsum;w;d];
  expected:w msum d;

  / Property 1: slideScan matches msum for incremental sum
  c1:r ~ expected;

  / Property 2: result length = data length
  c2:(count r) = count d;

  / Property 3: first element = first data element (for sum: f[0;d[0];0N] = d[0])
  c3:r[0] = d[0];

  propTotal+:3;
  if[c1; propPass+:1];
  if[c2; propPass+:1];
  if[c3; propPass+:1];
 }[seeds];

-1 "  property tests: ",string[propPass]," / ",string[propTotal]," passed";
assert["property tests all pass"; propPass = propTotal];

/ Additional property: window w=1 always returns the data itself (for sum)
\S 200;
dProp:50 ? 1000;
assertEq["w=1 returns data"; dProp; slideScan[fsum;1;dProp]];

/ Additional property: w >= n gives cumulative sum
\S 201;
dProp2:20 ? 100;
assertEq["w>=n gives cumsum"; sums dProp2; slideScan[fsum;1000;dProp2]];

/ ============================================================
/ Section 4 - Performance
/ ============================================================
-1 "\n--- Section 4: Performance ---";

N:1000000;
bigData:N ? 10000.0;

/ Performance: 1M data points, window size 100
st:.z.p;
rPerf:slideScan[fsum;100;bigData];
et:.z.p;
ms:(`long$(et - st)) % 1000000;
-1 "  performance: ",string[ms],"ms for 1M rows, w=100";
assert["performance < 3000ms"; ms < 3000];
assert["performance result length"; N = count rPerf];

/ Verify invocation count is ~n, not n*w
CNTPERF:0;
fCountPerf:{[prev;enter;exit] CNTPERF+:1; prev + enter - $[null exit;0;exit]};
perfData:100000 ? 1000;
slideScan[fCountPerf;100;perfData];
-1 "  perf invocation count (n=100000,w=100): ",string[CNTPERF];
assert["perf: invocation count ~n (within 2x)"; CNTPERF < 200000];
assert["perf: invocation count >= n"; CNTPERF >= 99999];

/ Verify correctness of performance run against msum
assertEq["perf result matches msum"; 100 msum bigData; rPerf];

/ ============================================================
summary[]
