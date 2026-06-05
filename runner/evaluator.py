"""Evaluate LLM-generated solutions against challenge test suites using PyKX."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Optional


def _fenced_blocks(text: str) -> list[tuple[str, str]]:
    """Return all fenced code blocks as (lang, body), in document order.

    `lang` is the lowercased fence info-string (may be "").
    """
    blocks = []
    for m in re.finditer(r"```([^\n`]*)\n(.*?)```", text, re.DOTALL):
        lang = m.group(1).strip().lower()
        blocks.append((lang, m.group(2).strip()))
    return blocks


def _extract_code(llm_response: str, preferred_langs: set[str]) -> str:
    """Extract a code block from an LLM response.

    Reasoning models routinely emit prose (and sometimes throwaway example
    blocks) before the real answer, so we take the LAST block whose language
    tag matches `preferred_langs`. Falling back: the last language-tagged block,
    then the last untagged block, then the whole response with prose prefixes
    stripped. Returns "" when nothing usable is found, so the caller can score
    the attempt as an error rather than feeding garbage to the interpreter.
    """
    if not llm_response or not llm_response.strip():
        return ""

    blocks = _fenced_blocks(llm_response)
    if blocks:
        preferred = [b for lang, b in blocks if lang in preferred_langs]
        if preferred:
            return preferred[-1]
        tagged = [b for lang, b in blocks if lang]
        if tagged:
            return tagged[-1]
        return blocks[-1][1]

    # No fences: the prompt asked for bare code, but models still add a line of
    # preamble. Drop leading prose-looking lines until the first code-looking one.
    code = llm_response.strip()
    for prefix in ["Here is", "Here's", "Sure", "Solution:", "Answer:", "Certainly"]:
        if code.lower().startswith(prefix.lower()):
            code = code.split("\n", 1)[-1].strip() if "\n" in code else ""
    return code.strip()


def extract_q_code(llm_response: str) -> str:
    """Extract q code from an LLM response, stripping markdown fences."""
    return _extract_code(llm_response, {"q", "kdb", "kdb+", "k"})


def extract_python_code(llm_response: str) -> str:
    """Extract Python code from an LLM response."""
    return _extract_code(llm_response, {"python", "py"})


def _script_safe_q(code: str) -> str:
    """Indent continuation lines so multi-line q loads correctly under ``\\l``.

    q's script loader starts a NEW statement on any line that begins at column 0,
    so a multi-line function whose closing ``}`` sits at column 0 (how Claude/Qwen
    and most humans format q) fails to load — the function never closes. Without
    this, the benchmark silently favors models that emit one-liners and zeroes
    everyone else. We indent any line that begins while a ``(){}[]`` bracket is
    still open, leaving genuine top-level statements at column 0 untouched.

    (Naive bracket count: does not parse q string/char/comment literals. The
    challenge solutions don't contain bracket characters inside those, so this is
    safe here; revisit if a solution needs e.g. ``"}"`` inside a string.)
    """
    out, depth = [], 0
    for idx, line in enumerate(code.split("\n")):
        if idx > 0 and depth > 0 and line[:1] not in (" ", "\t", ""):
            line = " " + line
        for ch in line:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
        out.append(line)
    return "\n".join(out)


def evaluate_q_challenge(challenge_dir: Path, solution_code: str) -> dict:
    """Evaluate a pure q solution by writing it and running tests.

    Copies the challenge dir to a temp directory so multiple models can
    evaluate the same challenge concurrently without file conflicts.

    Tries PyKX's bundled q first, falls back to system q.

    Args:
        challenge_dir: Path to the challenge directory.
        solution_code: The q code to evaluate.

    Returns:
        Dict with keys: status, score, total, errors, elapsed_ms, raw_output.
    """
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp) / challenge_dir.name
        shutil.copytree(challenge_dir, tmp_dir)

        # Write solution into the temp copy (normalized so multi-line q loads).
        (tmp_dir / "challenge.q").write_text(_script_safe_q(solution_code))
        tests_file = tmp_dir / "tests.q"

        # Try PyKX's bundled q first
        result = _evaluate_via_pykx(tests_file, tmp_dir)
        if result is not None:
            return result

        # Fall back to system q
        return _evaluate_via_subprocess(tests_file, tmp_dir)


def _find_q_binary() -> Optional[tuple]:
    """Find a working q binary, trying multiple sources.

    Returns (q_binary_path, env_dict) or None if no q found.
    Priority:
      1. User's q from ~/q (common personal edition location)
      2. q on PATH
      3. PyKX's bundled q binary
    """
    import importlib.util
    import os
    import shutil

    # 1. User's q at ~/q
    home_q = Path.home() / "q"
    for arch in ["m64", "l64", "m32", "l32"]:
        candidate = home_q / arch / "q"
        if candidate.exists():
            env = os.environ.copy()
            env["QHOME"] = str(home_q)
            return (str(candidate), env)

    # 2. q on PATH
    q_on_path = shutil.which("q")
    if q_on_path:
        return (q_on_path, None)  # None = use default env

    # 3. PyKX's bundled q
    spec = importlib.util.find_spec("pykx")
    if spec and spec.submodule_search_locations:
        pykx_dir = Path(list(spec.submodule_search_locations)[0])
        for arch in ["m64", "l64", "m32", "l32"]:
            candidate = pykx_dir / "lib" / arch / "q"
            if candidate.exists():
                env = os.environ.copy()
                env["QHOME"] = str(pykx_dir / "lib")
                return (str(candidate), env)

    return None


def _evaluate_via_pykx(tests_file: Path, challenge_dir: Path) -> Optional[dict]:
    """Try to evaluate using a discovered q binary as a subprocess.

    Searches for q in ~/q, PATH, and PyKX's bundled binary (in that order).
    Runs q directly so we get full stdout with section headers and pass/fail.

    Returns None if no q binary found.
    """
    found = _find_q_binary()
    if found is None:
        return None

    q_bin, env = found
    return _evaluate_via_subprocess_with_q(
        q_bin, tests_file, challenge_dir, env=env
    )


def _evaluate_via_subprocess_with_q(
    q_bin: str, tests_file: Path, challenge_dir: Path,
    env: Optional[dict] = None,
) -> dict:
    """Evaluate by running a specific q binary as a subprocess."""
    import os

    if env is None:
        env = os.environ.copy()
        # Ensure QHOME is set for the subprocess
        if "QHOME" not in env:
            env["QHOME"] = str(Path(q_bin).parent.parent)

    start = time.time()
    try:
        result = subprocess.run(
            [q_bin, str(tests_file.name)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(challenge_dir),
            env=env,
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
            "errors": [f"q binary not found at {q_bin}"],
            "elapsed_ms": 0,
            "raw_output": "",
            "sections": {},
        }


def _evaluate_via_subprocess(tests_file: Path, challenge_dir: Path) -> dict:
    """Evaluate by running system q as a subprocess."""
    return _evaluate_via_subprocess_with_q("q", tests_file, challenge_dir)


def evaluate_pykx_challenge(challenge_dir: Path, solution_code: str) -> dict:
    """Evaluate a PyKX (Python) solution by writing it and running pytest.

    Copies the challenge dir to a temp directory for concurrency safety.

    Args:
        challenge_dir: Path to the challenge directory.
        solution_code: The Python code to evaluate.

    Returns:
        Dict with keys: status, score, total, errors, elapsed_ms, raw_output.
    """
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp) / challenge_dir.name
        shutil.copytree(challenge_dir, tmp_dir)

        (tmp_dir / "challenge.py").write_text(solution_code)
        tests_file = tmp_dir / "tests.py"

        start = time.time()
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(tests_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(tmp_dir),
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
                "sections": {},
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
