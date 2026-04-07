"""Helper script: run q tests via pykx in a subprocess.

Usage: python _eval_helper.py /path/to/challenge/dir

Exit code: 0 if all tests pass, 1 otherwise.
Prints test results summary to stdout.
"""
import os
import sys

challenge_dir = sys.argv[1]
os.chdir(challenge_dir)

import pykx as kx

try:
    kx.q(chr(92) + "l tests.q")
except SystemExit:
    pass
except Exception:
    pass

# Read test results from q globals
try:
    passed = int(kx.q("PASS"))
    failed = int(kx.q("FAIL"))
    errs = kx.q("ERRS").py()
    print(f"passed: {passed}")
    print(f"failed: {failed}")
    if failed > 0 and errs:
        print("failures: " + ", ".join(str(e) for e in errs))
    sys.exit(0 if failed == 0 else 1)
except Exception as e:
    print(f"error: could not read test results: {e}", file=sys.stderr)
    sys.exit(1)
