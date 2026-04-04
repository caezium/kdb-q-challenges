/ j1-lazy-scan tests
/ Run: q tests.q

/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

/ === load solution ===
\l challenge.q

/ ============================================================
/ Section 1: Basic Correctness
/ ============================================================
-1 "\n--- basic correctness ---";

/ running sum, stop at >= 10
assertEq["running sum stops at 10";
  0 1 3 6 10;
  scanz[{((x+y)<10;x+y)};0;1 2 3 4 5 6]]

/ empty input
assertEq["empty input";
  enlist 0;
  scanz[{(1b;x+y)};0;`long$()]]

/ single element, continues (but no more data)
assertEq["single element continues";
  0 5;
  scanz[{(1b;x+y)};0;enlist 5]]

/ single element, stops immediately
assertEq["single element stops";
  0 5;
  scanz[{(0b;x+y)};0;enlist 5]]

/ all elements processed (never stops)
assertEq["never stops";
  0 1 3 6 10 15;
  scanz[{(1b;x+y)};0;1 2 3 4 5]]

/ stops on first element
assertEq["stops on first";
  0 1;
  scanz[{(0b;x+y)};0;1 2 3 4 5]]

/ float accumulator
assertEq["float accumulator";
  0.0 1.5 4.0 104.0;
  scanz[{((x+y)<10;x+y)};0.0;1.5 2.5 100.0 200.0]]

/ symbol accumulator — track state as symbol, stop when reaching target
assertEq["symbol accumulator";
  `start`a`b`c;
  scanz[{$[y=`c;(0b;y);(1b;y)]};`start;`a`b`c`d`e]]

/ ============================================================
/ Section 2: Anti-Cheat
/ ============================================================
-1 "\n--- anti-cheat ---";

/ anti-identity: result must not be the input
r1:scanz[{((x+y)<10;x+y)};0;1 2 3 4 5 6];
assert["not identity 1"; not r1~(1 2 3 4 5 6)]
assert["not identity 2"; not r1~0]

/ anti-constant: different inputs must give different outputs
r2:scanz[{((x+y)<100;x+y)};0;1 2 3];
r3:scanz[{((x+y)<100;x+y)};0;10 20 30];
r4:scanz[{((x+y)<100;x+y)};0;50 60 70];
assert["not constant"; 3=count distinct (r2;r3;r4)]

/ output always starts with init
assert["starts with init 0"; 0=first scanz[{(1b;x+y)};0;1 2 3]]
assert["starts with init 42"; 42=first scanz[{(1b;x+y)};42;1 2 3]]

/ output type matches accumulator type
assert["long type"; 7h=type scanz[{(1b;x+y)};0;1 2 3]]
assert["float type"; 9h=type scanz[{(1b;x+y)};0.0;1.0 2.0 3.0]]

/ ============================================================
/ Section 3: Property Tests (randomized)
/ ============================================================
-1 "\n--- property tests ---";

/ Property: output length <= 1 + input length
{[seed]
  system "S ",string seed;
  data:10+10?90;
  r:scanz[{((x+y)<500;x+y)};0;data];
  assert["len <= 1+n (seed ",string[seed],")"; (count r)<= 1+count data]
 } each 100?1000;

/ Property: always-continue scan matches 0,sums
{[seed]
  system "S ",string seed;
  data:5?100;
  r:scanz[{(1b;x+y)};0;data];
  assertEq["matches sums (seed ",string[seed],")"; 0,sums data; r]
 } each 100?1000;

/ Property: first element is always init
{[seed]
  system "S ",string seed;
  data:3+3?50;
  init:seed mod 100;
  r:scanz[{(1b;x+y)};init;data];
  assert["first=init (seed ",string[seed],")"; init=first r]
 } each 50?1000;

/ Property: if stopped early, last value triggered stop; if not, length = 1+n
{[seed]
  system "S ",string seed;
  data:5+5?50;
  threshold:50+seed mod 200;
  f:{[t;a;e] ((a+e)<t; a+e)}[threshold];
  r:scanz[f;0;data];
  $[(count r)<1+count data;
    / stopped early — last val must have crossed threshold
    assert["early stop correct (seed ",string[seed],")"; threshold<=last r];
    / didn't stop — length must be 1+n
    assert["full scan length (seed ",string[seed],")"; (count r)=1+count data]
  ]
 } each 100?1000;

/ ============================================================
/ Section 4: Performance
/ ============================================================
-1 "\n--- performance ---";

/ 10M elements, stops at element 3 — must be fast
bigdata:10000000?100;
t0:.z.P;
r:scanz[{((x+y)<50;x+y)};0;bigdata];
elapsed:(`long$.z.P-t0) div 1000000;  / ms
-1 "  big list early stop: ",string[elapsed],"ms, result length: ",string count r;
assert["early stop is fast (<500ms)"; elapsed<500]
assert["early stop result is short"; (count r)<100]

/ 100K elements, never stops — must still be reasonable
meddata:100000?10;
t0:.z.P;
r:scanz[{(1b;x+y)};0;meddata];
elapsed:(`long$.z.P-t0) div 1000000;
-1 "  full scan 100K: ",string[elapsed],"ms";
assert["full scan completes (<5000ms)"; elapsed<5000]
assertEq["full scan correct"; 0,sums meddata; r]

/ ============================================================
summary[]
