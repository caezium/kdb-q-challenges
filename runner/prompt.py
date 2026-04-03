"""Prompt construction for LLM q-challenge evaluation."""

from pathlib import Path

SYSTEM_PROMPT = """You are an expert kdb+/q developer.
You will be given a coding challenge. Respond with ONLY valid q code.
Your solution must define the function specified in the challenge stub.
No markdown fences. No explanation. No comments beyond what's necessary.
Pure q code only."""

PYKX_SYSTEM_PROMPT = """You are an expert in both kdb+/q and PyKX (the Python interface to kdb+).
You will be given a coding challenge. Respond with ONLY valid Python code using PyKX.
Your solution must define the function specified in the challenge stub.
No markdown fences. No explanation. Pure Python code only."""


def build_prompt(challenge_dir: Path, mode: str = "q") -> dict:
    """Build a prompt from a challenge directory.

    Args:
        challenge_dir: Path to the challenge directory.
        mode: "q" for pure q challenges, "pykx" for PyKX challenges.

    Returns:
        Dict with "system" and "user" keys.
    """
    readme = (challenge_dir / "README.md").read_text()

    if mode == "pykx":
        stub = (challenge_dir / "challenge.py").read_text()
        system = PYKX_SYSTEM_PROMPT
    else:
        stub = (challenge_dir / "challenge.q").read_text()
        system = SYSTEM_PROMPT

    user = f"""## Challenge

{readme}

## Stub to fill in

```
{stub}
```

Write your complete solution. Output ONLY the code, nothing else."""

    return {"system": system, "user": user}
