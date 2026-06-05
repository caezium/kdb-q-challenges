#!/usr/bin/env python3
"""Run author-held reference solutions through the test suites.

This is the *reproducible* counterpart to LEADERBOARD.md: instead of trusting
hand-recorded model numbers, it proves that a known-correct solution passes
every section of every hardened test suite on this machine.

Solutions live in ``solutions/<challenge>/challenge.q`` (or ``.py`` for PyKX)
and are gitignored — committing them would leak the benchmark. Drop your own
solutions there and run::

    python verify_reference.py
    python verify_reference.py --challenges h6-vector-partition,j1-lazy-scan

Exit code is 0 only if every available reference solution passes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from runner.evaluator import evaluate_pykx_challenge, evaluate_q_challenge

ROOT = Path(__file__).resolve().parent
SOLUTIONS = ROOT / "solutions"


def _solution_for(challenge: str) -> tuple[str, str] | None:
    """Return (mode, code) for a challenge's reference solution, or None."""
    base = SOLUTIONS / challenge
    q_file = base / "challenge.q"
    py_file = base / "challenge.py"
    if q_file.exists():
        return "q", q_file.read_text()
    if py_file.exists():
        return "pykx", py_file.read_text()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--challenges",
        default="all",
        help="Comma-separated challenge names, or 'all' (default).",
    )
    args = parser.parse_args()

    if not SOLUTIONS.is_dir():
        print(f"No solutions/ directory at {SOLUTIONS}. Nothing to verify.")
        return 0

    if args.challenges == "all":
        challenges = sorted(d.name for d in SOLUTIONS.iterdir() if d.is_dir())
    else:
        challenges = [c.strip() for c in args.challenges.split(",")]

    if not challenges:
        print("No reference solutions found in solutions/.")
        return 0

    print(f"Verifying {len(challenges)} reference solution(s)\n")
    all_ok = True
    width = max(len(c) for c in challenges)
    for challenge in challenges:
        found = _solution_for(challenge)
        if found is None:
            print(f"  {challenge:<{width}}  SKIP  (no solutions/{challenge}/challenge.*)")
            continue
        mode, code = found
        challenge_dir = ROOT / challenge
        if not challenge_dir.is_dir():
            print(f"  {challenge:<{width}}  SKIP  (no challenge dir)")
            continue

        if mode == "pykx":
            result = evaluate_pykx_challenge(challenge_dir, code)
        else:
            result = evaluate_q_challenge(challenge_dir, code)

        status = result["status"]
        score, total = result.get("score", 0), result.get("total", 0)
        ok = status == "pass"
        all_ok = all_ok and ok
        mark = "PASS" if ok else status.upper()
        print(f"  {challenge:<{width}}  {mark}  ({score}/{total} checks)")
        if not ok:
            tail = (result.get("raw_output") or "\n".join(result.get("errors", [])))[-800:]
            print("    " + tail.replace("\n", "\n    "))

    print()
    print("ALL REFERENCE SOLUTIONS PASS" if all_ok else "SOME REFERENCE SOLUTIONS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
