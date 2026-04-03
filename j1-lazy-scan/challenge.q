/ j1-lazy-scan
/ Implement scanz: a scan with early termination.
/
/ scanz[f;init;data]
/   f: binary, returns (continue;newValue) where continue is boolean
/   init: initial accumulator
/   data: list to scan
/   Returns: list of accumulator values, starting with init,
/            stopping when f first returns 0b for continue.
/
/ Example:
/   scanz[{(x+y<10;x+y)};0;1 2 3 4 5 6]  =>  0 1 3 6 10

scanz:{[f;init;data]
  'nyi}
