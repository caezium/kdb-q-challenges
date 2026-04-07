/ h6-vector-partition
/ Implement vpart: partition data by compound keys, fully vectorized.
/ .
/ vpart[ks;data]
/   ks: list of key-lists (same length as data)
/   data: list to partition
/   Returns: dictionary of (compound key) -> (grouped data values)
/ .
/ CONSTRAINT: No each, do, or while. Fully vectorized.

vpart:{[ks;data] 'nyi}
