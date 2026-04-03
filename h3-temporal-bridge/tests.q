/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

\l challenge.q

/ =========================================
-1 "\n--- Section 1: Basic Correctness ---";
/ =========================================

/ Simple 2-trade, 2-quote AAPL example with 15s maxlag (both match)
trades1:([] sym:`AAPL`AAPL; time:10:00:00 10:00:30; price:150.0 151.0);
quotes1:([] sym:`AAPL`AAPL; time:09:59:50 10:00:25; bid:149.5 150.5; ask:150.5 151.5);

r1:tbridge[trades1;quotes1;0D00:00:15];
assertEq["15s maxlag: first trade bid";149.5;r1[`bid][0]]
assertEq["15s maxlag: first trade ask";150.5;r1[`ask][0]]
assertEq["15s maxlag: second trade bid";150.5;r1[`bid][1]]
assertEq["15s maxlag: second trade ask";151.5;r1[`ask][1]]

/ Same data with 5s maxlag (first trade stale, second fresh)
r2:tbridge[trades1;quotes1;0D00:00:05];
assertEq["5s maxlag: first trade bid is null (10s stale)";0Nf;r2[`bid][0]]
assertEq["5s maxlag: first trade ask is null (10s stale)";0Nf;r2[`ask][0]]
assertEq["5s maxlag: second trade bid (5s fresh)";150.5;r2[`bid][1]]
assertEq["5s maxlag: second trade ask (5s fresh)";151.5;r2[`ask][1]]

/ Zero maxlag — only exact time matches
trades3:([] sym:`AAPL`AAPL; time:10:00:00 10:00:25; price:150.0 151.0);
quotes3:([] sym:`AAPL`AAPL; time:10:00:00 10:00:20; bid:149.0 150.0; ask:150.0 151.0);
r3:tbridge[trades3;quotes3;0D00:00:00];
assertEq["zero maxlag: exact match trade gets bid";149.0;r3[`bid][0]]
assertEq["zero maxlag: exact match trade gets ask";150.0;r3[`ask][0]]
assertEq["zero maxlag: non-exact trade bid is null";0Nf;r3[`bid][1]]
assertEq["zero maxlag: non-exact trade ask is null";0Nf;r3[`ask][1]]

/ Multiple syms (AAPL and GOOG, quotes interleaved)
trades4:([] sym:`AAPL`GOOG`AAPL`GOOG; time:10:00:00 10:00:00 10:00:30 10:00:30; price:150.0 2800.0 151.0 2810.0);
quotes4:([] sym:`AAPL`AAPL`GOOG`GOOG; time:09:59:50 10:00:25 09:59:55 10:00:28; bid:149.5 150.5 2795.0 2805.0; ask:150.5 151.5 2805.0 2815.0);
r4:tbridge[trades4;quotes4;0D00:00:15];
/ AAPL at 10:00:00 -> quote at 09:59:50 (10s lag, within 15s)
assertEq["multi-sym: AAPL first trade bid";149.5;r4[`bid][0]]
/ GOOG at 10:00:00 -> quote at 09:59:55 (5s lag, within 15s)
assertEq["multi-sym: GOOG first trade bid";2795.0;r4[`bid][1]]
/ AAPL at 10:00:30 -> quote at 10:00:25 (5s lag)
assertEq["multi-sym: AAPL second trade bid";150.5;r4[`bid][2]]
/ GOOG at 10:00:30 -> quote at 10:00:28 (2s lag)
assertEq["multi-sym: GOOG second trade bid";2805.0;r4[`bid][3]]

/ Trade with no quote at all for its sym -> null bid/ask
trades5:([] sym:`MSFT; time:enlist 10:00:00; price:enlist 300.0);
quotes5:([] sym:`AAPL; time:enlist 09:59:50; bid:enlist 149.5; ask:enlist 150.5);
r5:tbridge[trades5;quotes5;0D00:01:00];
assertEq["no quote for sym: bid is null";0Nf;r5[`bid][0]]
assertEq["no quote for sym: ask is null";0Nf;r5[`ask][0]]

/ Quote exactly at maxlag boundary (lag = maxlag means NOT stale, should include)
trades6:([] sym:`AAPL; time:enlist 10:00:10; price:enlist 150.0);
quotes6:([] sym:`AAPL; time:enlist 10:00:00; bid:enlist 149.0; ask:enlist 150.0);
r6:tbridge[trades6;quotes6;0D00:00:10];
assertEq["boundary: lag exactly equals maxlag, bid included";149.0;r6[`bid][0]]
assertEq["boundary: lag exactly equals maxlag, ask included";150.0;r6[`ask][0]]

/ One tick beyond boundary
r6b:tbridge[trades6;quotes6;0D00:00:09];
assertEq["boundary+1: lag exceeds maxlag by 1s, bid null";0Nf;r6b[`bid][0]]
assertEq["boundary+1: lag exceeds maxlag by 1s, ask null";0Nf;r6b[`ask][0]]

/ =========================================
-1 "\n--- Section 2: Anti-Cheat ---";
/ =========================================

/ Anti-identity: result is not the trades table unchanged
assert["anti-identity: result differs from input trades";not trades1~tbridge[trades1;quotes1;0D00:00:15]]

/ Anti-constant: different maxlags produce different results
rc1:tbridge[trades1;quotes1;0D00:00:15];
rc2:tbridge[trades1;quotes1;0D00:00:05];
assert["anti-constant: different maxlags give different results";not rc1~rc2]

/ Output has bid and ask columns
assert["output has bid column";`bid in cols r1]
assert["output has ask column";`ask in cols r1]

/ bid/ask are float type (9h)
assert["bid column is float type";9h=type r1`bid]
assert["ask column is float type";9h=type r1`ask]

/ Result preserves original trade columns
assertEq["result sym matches trades";trades1`sym;r1`sym]
assertEq["result time matches trades";trades1`time;r1`time]
assertEq["result price matches trades";trades1`price;r1`price]

/ =========================================
-1 "\n--- Section 3: Property Tests ---";
/ =========================================

-1 "  running 50 random property tests...";
propFails:0;
do[50;
  \S
  syms:3?`4;
  n:10+first 1?90;
  m:20+first 1?180;
  / generate random trades
  tSym:n?syms;
  tTime:asc 09:30:00+n?23400000;
  tPrice:n?100.0;
  trds:`sym`time xcols `sym xasc ([] sym:tSym; time:tTime; price:tPrice);
  / generate random quotes
  qSym:m?syms;
  qTime:asc 09:30:00+m?23400000;
  qBid:m?100.0;
  qAsk:qBid+m?5.0;
  qts:`sym`time xcols `sym xasc ([] sym:qSym; time:qTime; bid:qBid; ask:qAsk);

  / Property 1: when maxlag=0W, result matches aj exactly
  rInf:tbridge[trds;qts;0W];
  rAj:aj[`sym`time;trds;qts];
  if[not rInf~rAj; propFails+:1];

  / Property 2: all returned bid values are either null or exist in quotes table
  bids:rInf`bid;
  validBids:all (bids where not null bids) in qts`bid;
  if[not validBids; propFails+:1];

  / Property 3: result has same count as trades
  if[not (count rInf)=count trds; propFails+:1];

  / Property 4: result has same sym and time columns as trades
  if[not (rInf`sym)~trds`sym; propFails+:1];
  if[not (rInf`time)~trds`time; propFails+:1]
 ];
assertEq["property tests (50 seeds: aj match, valid bids, count, cols)";0;propFails]

/ Additional property: with very small maxlag, at least some nulls appear in large random data
\S 99
propFails2:0;
do[20;
  \S
  syms:`A`B`C;
  n:50; m:50;
  tSym:n?syms;
  tTime:asc 09:30:00+n?23400000;
  trds:`sym`time xcols `sym xasc ([] sym:tSym; time:tTime; price:n?100.0);
  qSym:m?syms;
  qTime:asc 09:30:00+m?23400000;
  qBid:m?100.0;
  qts:`sym`time xcols `sym xasc ([] sym:qSym; time:qTime; bid:qBid; ask:qBid+m?5.0);
  rTiny:tbridge[trds;qts;0D00:00:00.001];
  rBig:tbridge[trds;qts;0W];
  / With near-zero maxlag, we should get at least as many nulls as with 0W
  nullsTiny:sum null rTiny`bid;
  nullsBig:sum null rBig`bid;
  if[not nullsTiny>=nullsBig; propFails2+:1]
 ];
assertEq["property: smaller maxlag produces >= nulls vs 0W";0;propFails2]

/ =========================================
-1 "\n--- Section 4: Performance ---";
/ =========================================

-1 "  generating 100K trades, 200K quotes, 5 syms...";
\S 123
symsPerf:`AAPL`GOOG`MSFT`AMZN`META;
nT:100000; nQ:200000;
tSymP:nT?symsPerf;
tTimeP:asc 09:30:00.000+nT?23400000;
trdsPerf:`sym`time xcols `sym xasc ([] sym:tSymP; time:tTimeP; price:nT?500.0);
qSymP:nQ?symsPerf;
qTimeP:asc 09:30:00.000+nQ?23400000;
qBidP:nQ?500.0;
qtsPerf:`sym`time xcols `sym xasc ([] sym:qSymP; time:qTimeP; bid:qBidP; ask:qBidP+nQ?10.0);

st:.z.p;
rPerf:tbridge[trdsPerf;qtsPerf;0D00:00:30];
elapsed:(`long$.z.p-st) div 1000000;
-1 "  perf: 100K trades x 200K quotes completed in ",string[elapsed],"ms";
assert["performance: 100K x 200K under 5000ms";elapsed<5000]
assertEq["perf: result count matches trades";count trdsPerf;count rPerf]

/ ===
summary[]
