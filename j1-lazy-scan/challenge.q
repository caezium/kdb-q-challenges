/ j1-lazy-scan
/ Implement scanz: a scan that supports early termination.
/ .
/ scanz[f;init;data]
/   f: binary f[acc;elem] -> (continue;newValue)
/   init: initial accumulator
/   data: list to scan
/   Returns: list of accumulator values from init up to first stop.

scanz:{[f;init;data] 'nyi}
