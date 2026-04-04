/ h7-adverb-algebra
/ Implement slideScan: incremental sliding-window scan.
/ .
/ slideScan[f;w;data]
/   f: ternary f[prevResult;entering;exiting] - incremental update
/   w: window size (positive long)
/   data: list to scan
/   Returns: list of window results, one per data position
/ .
/ f is called ~n times (incremental), NOT n*w times (brute force).
/ For partial windows (first w-1 positions), exiting is 0N.

slideScan:{[f;w;data] exiting:w xprev data; {[f;x;y] f[x;y 0;y 1]}[f]\[0;flip(data;exiting)]}
