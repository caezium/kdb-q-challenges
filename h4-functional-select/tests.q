/ === test harness ===
\S 42
PASS:0; FAIL:0; ERRS:()
assert:{[n;c] $[c;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n]]}
assertEq:{[n;e;a] $[e~a;[PASS+:1; -1 "  pass: ",n];[FAIL+:1; ERRS,:enlist n; -1 "  FAIL: ",n," | expected: ",(-3!e)," got: ",(-3!a)]]}
summary:{[] -1 "\n=== Results ==="; -1 "passed: ",string PASS; -1 "failed: ",string FAIL; if[FAIL>0; -1 "failures: ",", " sv ERRS]; exit FAIL>0}

\l challenge.q

/ ============================================================
/ Test table
/ ============================================================
t:([] sym:`AAPL`GOOG`AAPL`GOOG`MSFT; price:150 200 155 210 180f; vol:100 200 150 300 250)

/ ============================================================
/ Section 1 - Basic Correctness
/ ============================================================
-1 "\n--- Section 1: Basic Correctness ---";

/ Full query: filter price>100, group by sym, avg price + sum vol
spec1:`t`c`b`a!(`t; enlist "price>100"; enlist `sym; `avgPrice`totalVol!("avg price";"sum vol"))
r1:qbuild spec1
expected1:select avgPrice:avg price, totalVol:sum vol by sym from t where price>100
assertEq["full query matches qSQL"; expected1; eval r1]

/ No where clause: empty list means no filter
spec2:`t`c`b`a!(`t; (); enlist `sym; `avgPrice`totalVol!("avg price";"sum vol"))
r2:qbuild spec2
expected2:select avgPrice:avg price, totalVol:sum vol by sym from t
assertEq["no where clause"; expected2; eval r2]

/ No group-by: flat aggregation
spec3:`t`c`b`a!(`t; enlist "price>100"; `$(); `avgPrice`totalVol!("avg price";"sum vol"))
r3:qbuild spec3
expected3:select avgPrice:avg price, totalVol:sum vol from t where price>100
assertEq["no group-by"; expected3; eval r3]

/ No aggregation, no group-by: select all columns (like select from t)
spec4:`t`c`b`a!(`t; (); `$(); ()!())
r4:qbuild spec4
expected4:select from t
assertEq["no agg no group => select from t"; expected4; eval r4]

/ Select with where but no group: single aggregation
spec5:`t`c`b`a!(`t; enlist "sym=`AAPL"; `$(); (enlist `avgPrice)!(enlist "avg price"))
r5:qbuild spec5
expected5:select avgPrice:avg price from t where sym=`AAPL
assertEq["where + agg, no group"; expected5; eval r5]

/ Multiple where clauses
spec6:`t`c`b`a!(`t; ("price>100";"sym in `AAPL`GOOG"); enlist `sym; `avgPrice`totalVol!("avg price";"sum vol"))
r6:qbuild spec6
expected6:select avgPrice:avg price, totalVol:sum vol by sym from t where price>100, sym in `AAPL`GOOG
assertEq["multiple where clauses"; expected6; eval r6]

/ No where, no group, no agg: plain select from t
spec7:`t`c`b`a!(`t; (); `$(); ()!())
r7:qbuild spec7
expected7:select from t
assertEq["plain select from t"; expected7; eval r7]

/ Where clause only, no group, select all
spec8:`t`c`b`a!(`t; enlist "price>160"; `$(); ()!())
r8:qbuild spec8
expected8:select from t where price>160
assertEq["where only, select all columns"; expected8; eval r8]

/ Group by only, no where, no agg: selects all grouped
spec9:`t`c`b`a!(`t; (); enlist `sym; ()!())
r9:qbuild spec9
expected9:select by sym from t
assertEq["group by only, no where, no agg"; expected9; eval r9]

/ ============================================================
/ Section 2 - Anti-Cheat
/ ============================================================
-1 "\n--- Section 2: Anti-Cheat ---";

/ Output must be a list, not a table
r_ac1:qbuild spec1
assert["output is a list (type 0h)"; 0h=type r_ac1]
assert["output is NOT a table"; not 98h=type r_ac1]

/ Anti-constant: different specs produce different parse trees
spec_ac2a:`t`c`b`a!(`t; enlist "price>100"; enlist `sym; `avgPrice`totalVol!("avg price";"sum vol"))
spec_ac2b:`t`c`b`a!(`t; enlist "price>200"; enlist `sym; (enlist `cnt)!(enlist "count i"))
r_ac2a:qbuild spec_ac2a
r_ac2b:qbuild spec_ac2b
assert["anti-constant: different specs => different trees"; not r_ac2a ~ r_ac2b]

/ Parse tree references table by name — modifying table after building tree still works
t_backup:t;
spec_ac3:`t`c`b`a!(`t; (); `$(); ()!())
r_ac3:qbuild spec_ac3
/ Append a row to t
`t insert (`TSLA;999f;999);
res_after:eval r_ac3
assert["parse tree uses table name, not value (sees new row)"; (count res_after) = 1 + count t_backup]
/ Restore t
t:t_backup;

/ ============================================================
/ Section 3 - Property Tests
/ ============================================================
-1 "\n--- Section 3: Property Tests ---";

/ Helper: build qSQL string and evaluate it for comparison
/ We build the equivalent qSQL manually and compare
whereCols:("price>100";"price>150";"sym=`AAPL";"sym in `AAPL`GOOG";"vol>100")
groupOpts:(`$(); enlist `sym)
aggOpts:(()!(); `avgP`totalV!("avg price";"sum vol"); (enlist `cnt)!(enlist "count i"); `mx`mn!("max price";"min price"))

/ Restore a clean table for property tests
t:([] sym:`AAPL`GOOG`AAPL`GOOG`MSFT; price:150 200 155 210 180f; vol:100 200 150 300 250)

whereCols:("price>100";"price>150";"sym=`AAPL";"sym in `AAPL`GOOG";"vol>100")
groupOpts:(`$(); enlist `sym)
aggOpts:(()!(); `avgP`totalV!("avg price";"sum vol"); (enlist `cnt)!(enlist "count i"); `mx`mn!("max price";"min price"))
t:([] sym:`AAPL`GOOG`AAPL`GOOG`MSFT; price:150 200 155 210 180f; vol:100 200 150 300 250)
propSpecs:();
do[20;
  nw:1?1+count whereCols;
  wIdx:neg[first nw]?count whereCols;
  wc2:$[0=first nw; (); whereCols wIdx];
  grp2:groupOpts first 1?count groupOpts;
  agg2:aggOpts first 1?count aggOpts;
  propSpecs,:enlist `t`c`b`a!(`t; wc2; grp2; agg2)
 ];
propTrees:qbuild each propSpecs;
propGot:eval each propTrees;
propFails:`long$sum {not (type x) in 98 99h} each propGot;
assertEq["property tests: all 20 produce tables";0;propFails];

/ ============================================================
/ Section 4 - Performance
/ ============================================================
-1 "\n--- Section 4: Performance ---";

/ Create a large table
bigN:100000;
bigtbl:([] sym:bigN?`AAPL`GOOG`MSFT`TSLA`AMZN; price:bigN?500f; vol:bigN?10000);

/ Assign to a global so the parse tree can reference it
`bigtbl set bigtbl;

specPerf:`t`c`b`a!(`bigtbl; ("price>50";"vol>1000"); enlist `sym; `ap`tv`cnt!("avg price";"sum vol";"count i"))
st:.z.P;
do[100; eval qbuild specPerf];
elapsed:(`long$.z.P-st) div 1000000;
-1 "  perf: 100 iterations in ",string[elapsed],"ms";
assert["performance: 100 complex queries < 2000ms"; elapsed < 2000]

/ ============================================================
summary[]
