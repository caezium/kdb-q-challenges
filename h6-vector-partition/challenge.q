/ h6-vector-partition
/ Implement vpart: partition data by compound keys, fully vectorized.
/
/ vpart[keys;data]
/   keys: list of key-lists (each same length as data)
/   data: list to partition
/   Returns: dictionary of (compound key) -> (grouped data values)
/
/ CONSTRAINT: No each, do, or while. Fully vectorized.

vpart:{[keys;data]
  'nyi}
