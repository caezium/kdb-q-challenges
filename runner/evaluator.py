"""Evaluate LLM-generated solutions against challenge test suites using PyKX."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Optional


def extract_q_code(llm_response: str) -> str:
    """Extract q code from an LLM response, stripping markdown fences."""
    # Try to extract from code fences first
    fence_match = re.search(r"```(?:q|kdb)?\s*\n(.*?)```", llm_response, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # If no fences, assume the whole response is code
    # Strip any leading/trailing whitespace and common non-code prefixes
    code = llm_response.strip()
    for prefix in ["Here is", "Here's", "Solution:", "Answer:"]:
        if code.lower().startswith(prefix.lower()):
            code = code[len(prefix) :].strip()
            if code.startswith(":"):
                code = code[1:].strip()
    return code


def extract_python_code(llm_response: str) -> str:
    """Extract Python code from an LLM response."""
    fence_match = re.search(
        r"```(?:python|py)?\s*\n(.*?)```", llm_response, re.DOTALL
    )
    if fence_match:
        return fence_match.group(1).strip()
    return llm_response.strip()


def evaluate_q_challenge(challenge_dir: Path, solution_code: str) -> dict:
    """Evaluate a pure q solution by writing it and running tests.

    Tries PyKX first (import pykx), falls back to subprocess q.

    Args:
        challenge_dir: Path to the challenge directory.
        solution_code: The q code to evaluate.

    Returns:
        Dict with keys: status, score, total, errors, elapsed_ms, raw_output.
    """
    challenge_file = challenge_dir / "challenge.q"
    tests_file = challenge_dir / "tests.q"

    # Back up original stub
    original = challenge_file.read_text()

    try:
        # Write solution
        challenge_file.write_text(solution_code)

        # Try PyKX evaluation first
        result = _evaluate_via_pykx(tests_file)
        if result is not None:
            return result

        # Fall back to subprocess
        return _evaluate_via_subprocess(tests_file, challenge_dir)

    finally:
        # Restore original stub
        challenge_file.write_text(original)


def _evaluate_via_pykx(tests_file: Path) -> Optional[dict]:
    """Try to evaluate using PyKX. Returns None if PyKX unavailable."""
    try:
        import pykx as kx
    except ImportError:
        return None

    start = time.time()
    try:
        import io
        import sys

        # Capture stdout to get test output for section parsing
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()
        try:
            kx.q("\\l " + str(tests_file))
        finally:
            sys.stdout = old_stdout
        raw_output = captured.getvalue()
        elapsed = int((time.time() - start) * 1000)
        sections = parse_sections(raw_output)
        total = sum(s["passed"] + s["failed"] for s in sections.values())
        passed = sum(s["passed"] for s in sections.values())
        return {
            "status": "pass",
            "score": passed if total > 0 else "all",
            "total": total if total > 0 else "all",
            "errors": [],
            "elapsed_ms": elapsed,
            "raw_output": raw_output,
            "sections": sections,
        }
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        error_str = str(e)
        sections = parse_sections(error_str)
        return {
            "status": "fail",
            "score": _extract_score(error_str),
            "total": _extract_total(error_str),
            "errors": [error_str],
            "elapsed_ms": elapsed,
            "raw_output": error_str,
            "sections": sections,
        }


def _evaluate_via_subprocess(tests_file: Path, challenge_dir: Path) -> dict:
    """Evaluate by running q as a subprocess."""
    start = time.time()
    try:
        result = subprocess.run(
            ["q", str(tests_file)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(challenge_dir),
        )
        elapsed = int((time.time() - start) * 1000)

        output = result.stdout + result.stderr
        passed = result.returncode == 0
        sections = parse_sections(output)

        return {
            "status": "pass" if passed else "fail",
            "score": _extract_score(output),
            "total": _extract_total(output),
            "errors": [output] if not passed else [],
            "elapsed_ms": elapsed,
            "raw_output": output,
            "sections": sections,
        }
    except subprocess.TimeoutExpired:
        elapsed = int((time.time() - start) * 1000)
        return {
            "status": "timeout",
            "score": 0,
            "total": 0,
            "errors": ["Execution timed out after 120s"],
            "elapsed_ms": elapsed,
            "raw_output": "",
            "sections": {},
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "score": 0,
            "total": 0,
            "errors": ["q executable not found. Install kdb+ and ensure q is on PATH."],
            "elapsed_ms": 0,
            "raw_output": "",
            "sections": {},
        }


def evaluate_pykx_challenge(challenge_dir: Path, solution_code: str) -> dict:
    """Evaluate a PyKX (Python) solution by writing it and running pytest.

    Args:
        challenge_dir: Path to the challenge directory.
        solution_code: The Python code to evaluate.

    Returns:
        Dict with keys: status, score, total, errors, elapsed_ms, raw_output.
    """
    challenge_file = challenge_dir / "challenge.py"
    tests_file = challenge_dir / "tests.py"

    original = challenge_file.read_text()

    try:
        challenge_file.write_text(solution_code)

        start = time.time()
        result = subprocess.run(
            ["python", "-m", "pytest", str(tests_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(challenge_dir),
        )
        elapsed = int((time.time() - start) * 1000)

        output = result.stdout + result.stderr
        passed = result.returncode == 0

        return {
            "status": "pass" if passed else "fail",
            "score": _extract_pytest_score(output),
            "total": _extract_pytest_total(output),
            "errors": [output] if not passed else [],
            "elapsed_ms": elapsed,
            "raw_output": output,
            "sections": {},  # pytest doesn't use our section format
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "score": 0,
            "total": 0,
            "errors": ["Execution timed out after 120s"],
            "elapsed_ms": int((time.time() - start) * 1000),
            "raw_output": "",
            "sections": {},
        }
    finally:
        challenge_file.write_text(original)


def parse_sections(output: str) -> dict:
    """Parse test output into per-section pass/fail counts.

    Handles both formats:
      --- Section 1: Basic Correctness ---
      --- basic correctness ---

    Returns:
        Dict mapping section name -> {"passed": int, "failed": int}
    """
    sections = {}
    current_section = None

    for line in output.splitlines():
        stripped = line.strip()

        # Detect section headers
        sec_match = re.match(
            r"---\s*(?:Section\s*\d+:\s*)?(.+?)\s*---", stripped
        )
        if sec_match:
            # Normalize: lowercase, underscores
            name = sec_match.group(1).strip().lower().replace(" ", "_")
            current_section = name
            sections[current_section] = {"passed": 0, "failed": 0}
            continue

        if current_section is None:
            continue

        # Count pass/fail lines
        if re.match(r"pass:", stripped):
            sections[current_section]["passed"] += 1
        elif re.match(r"FAIL:", stripped):
            sections[current_section]["failed"] += 1

    return sections


def _extract_score(output: str) -> int:
    """Extract pass count from q test output."""
    match = re.search(r"passed:\s*(\d+)", output)
    return int(match.group(1)) if match else 0


def _extract_total(output: str) -> int:
    """Extract total test count from q test output."""
    passed = _extract_score(output)
    fail_match = re.search(r"failed:\s*(\d+)", output)
    failed = int(fail_match.group(1)) if fail_match else 0
    return passed + failed


def _extract_pytest_score(output: str) -> int:
    """Extract pass count from pytest output."""
    match = re.search(r"(\d+) passed", output)
    return int(match.group(1)) if match else 0


def _extract_pytest_total(output: str) -> int:
    """Extract total test count from pytest output."""
    passed = _extract_pytest_score(output)
    fail_match = re.search(r"(\d+) failed", output)
    failed = int(fail_match.group(1)) if fail_match else 0
    return passed + failed
