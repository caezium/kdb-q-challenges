items:(
  (`j1; "10-2-3"); (`j1; "2+3*4"); (`j1; "5>3>1"); (`j1; "{x*2}/[3;1]"); (`j1; "(*/)1 2 3 4");
  (`h2; "(+/)1 2 3 4 5"); (`h2; "(+\\)1 2 3 4"); (`h2; "(*\\)1 2 3 4"); (`h2; "(|/)3 1 4 1 5");
  (`h3; "10:00:30 - 09:59:50"); (`h3; "2026.01.10 - 2026.01.01"); (`h3; "09:30:00 + 90");
  (`h4; "count select from ([]a:1 2 3 4) where a>2");
  (`h4; "count select by sym from ([]sym:`a`b`a`b`a;v:til 5)");
  (`h4; "?[([]a:1 2 3);();0b;()]~([]a:1 2 3)");
  (`h5; "{x,last[x]+1}/[3;enlist 0]"); (`h5; "til 5"); (`h5; "(#:) each (1 2;3 4 5;enlist 6)");
  (`h6; "group `a`b`a`c`b"); (`h6; "where 01011b"); (`h6; "count each group `a`a`b`a");
  (`h7; "3 msum 1 2 3 4 5"); (`h7; "2 xprev 10 20 30 40 50"); (`h7; "differ 1 1 2 2 3 1"); (`h7; "deltas 1 3 6 10") );
/ emit JSON lines so Python can ingest gold verbatim
-1 .j.j {[it] `tag`expr`gold!((string it 0); it 1; @[{-3!value x};it 1;{"ERR:",x}])} each items;
exit 0
