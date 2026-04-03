"""Evaluate LLM-generated solutions against challenge test suites using PyKX."""

import re
import subprocess
import time
from pathlib import Path


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


def _evaluate_via_pykx(tests_file: Path) -> dict | None:
    """Try to evaluate using PyKX. Returns None if PyKX unavailable."""
    try:
        import pykx as kx
    except ImportError:
        return None

    start = time.time()
    try:
        # Run tests in a fresh q context
        kx.q("\\l " + str(tests_file))
        elapsed = int((time.time() - start) * 1000)
        return {
            "status": "pass",
            "score": "all",
            "total": "all",
            "errors": [],
            "elapsed_ms": elapsed,
            "raw_output": "PyKX evaluation passed",
        }
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        error_str = str(e)
        # Parse pass/fail from error output if available
        return {
            "status": "fail",
            "score": _extract_score(error_str),
            "total": _extract_total(error_str),
            "errors": [error_str],
            "elapsed_ms": elapsed,
            "raw_output": error_str,
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

        return {
            "status": "pass" if passed else "fail",
            "score": _extract_score(output),
            "total": _extract_total(output),
            "errors": [output] if not passed else [],
            "elapsed_ms": elapsed,
            "raw_output": output,
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
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "score": 0,
            "total": 0,
            "errors": ["q executable not found. Install kdb+ and ensure q is on PATH."],
            "elapsed_ms": 0,
            "raw_output": "",
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
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "score": 0,
            "total": 0,
            "errors": ["Execution timed out after 120s"],
            "elapsed_ms": int((time.time() - start) * 1000),
            "raw_output": "",
        }
    finally:
        challenge_file.write_text(original)


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
