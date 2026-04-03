/ h2-custom-adverb
/ Implement compose: compose two iterator-wrappers into a new one.
/
/ An iterator-wrapper is triadic: iw[f;init;data] -> result
/ compose[outer;inner][f;init;data] = outer[f;init;inner[f;init;] each data]
/ where data is a list of lists.
/
/ Example:
/   myOver:{[f;init;data] f/[init;data]}
/   compose[myOver;myOver][+;0;(1 2 3;4 5;6)] => 21

compose:{[outer;inner]
  'nyi}
