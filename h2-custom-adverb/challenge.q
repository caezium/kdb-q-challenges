/ h2-custom-adverb
/ Implement compose: compose two iterator-wrappers into a new one.
/ .
/ compose[outer;inner]
/   outer, inner: triadic iw[f;init;data] -> result
/   Returns: a new iterator-wrapper such that
/            compose[outer;inner][f;init;data] = outer[f;init;inner[f;init;] each data]

compose:{[outer;inner] 'nyi}
