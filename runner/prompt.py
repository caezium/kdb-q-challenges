"""Prompt construction for LLM q-challenge evaluation."""

from pathlib import Path

# --- System prompts per strategy ---

SYSTEM_PROMPTS = {
    "zero-shot": {
        "q": """You are an expert kdb+/q developer.
You will be given a coding challenge. Respond with ONLY valid q code.
Your solution must define the function specified in the challenge stub.
No markdown fences. No explanation. No comments beyond what's necessary.
Pure q code only.""",
        "pykx": """You are an expert in both kdb+/q and PyKX (the Python interface to kdb+).
You will be given a coding challenge. Respond with ONLY valid Python code using PyKX.
Your solution must define the function specified in the challenge stub.
No markdown fences. No explanation. Pure Python code only.""",
    },
    "cot": {
        "q": """You are an expert kdb+/q developer.
You will be given a coding challenge. Think step by step about the q semantics,
type system, and evaluation model before writing your solution.
Reason carefully about:
- Right-to-left evaluation order
- Type promotion rules (e.g. boolean + long -> long)
- Adverb behavior (scan, over, each, prior)
- Performance implications of your approach

After your reasoning, provide your complete solution inside a ```q code block.
The solution must define the function specified in the challenge stub.""",
        "pykx": """You are an expert in both kdb+/q and PyKX (the Python interface to kdb+).
You will be given a coding challenge. Think step by step about the PyKX semantics,
type conversion rules, and q interop before writing your solution.

After your reasoning, provide your complete solution inside a ```python code block.
The solution must define the function specified in the challenge stub.""",
    },
    "few-shot": {
        "q": """You are an expert kdb+/q developer.
You will be given a coding challenge. Respond with ONLY valid q code.
Your solution must define the function specified in the challenge stub.

Here is an example of solving a q challenge:

Challenge: Implement `cummax` — cumulative maximum of a list.
  cummax:{[data] ...}

Solution:
  cummax:{[data] (|\\) data}

Now solve the challenge below. Output ONLY the code, no explanation.""",
        "pykx": """You are an expert in both kdb+/q and PyKX (the Python interface to kdb+).
You will be given a coding challenge. Respond with ONLY valid Python code using PyKX.

Here is an example of solving a PyKX challenge:

Challenge: Implement `qsum` — sum a Python list using q's sum function.
  def qsum(data: list) -> float:
      raise NotImplementedError

Solution:
  import pykx as kx
  def qsum(data: list) -> float:
      return float(kx.q('sum', kx.toq(data)))

Now solve the challenge below. Output ONLY the code, no explanation.""",
    },
}


def build_prompt(
    challenge_dir: Path, mode: str = "q", strategy: str = "zero-shot"
) -> dict:
    """Build a prompt from a challenge directory.

    Args:
        challenge_dir: Path to the challenge directory.
        mode: "q" for pure q challenges, "pykx" for PyKX challenges.
        strategy: "zero-shot", "cot", or "few-shot".

    Returns:
        Dict with "system" and "user" keys.
    """
    readme = (challenge_dir / "README.md").read_text()

    if mode == "pykx":
        stub = (challenge_dir / "challenge.py").read_text()
    else:
        stub = (challenge_dir / "challenge.q").read_text()

    system = SYSTEM_PROMPTS[strategy][mode]

    user = f"""## Challenge

{readme}

## Stub to fill in

```
{stub}
```

Write your complete solution. Output ONLY the code, nothing else."""

    return {"system": system, "user": user}


def build_retry_prompt(
    challenge_dir: Path,
    previous_code: str,
    error_output: str,
    mode: str = "q",
    strategy: str = "zero-shot",
) -> dict:
    """Build a retry prompt with error feedback from the previous attempt.

    Args:
        challenge_dir: Path to the challenge directory.
        previous_code: The code from the previous failed attempt.
        error_output: The test error output from the previous attempt.
        mode: "q" or "pykx".
        strategy: Prompt strategy.

    Returns:
        Dict with "system", "user", and "messages" keys.
        "messages" is the full conversation for multi-turn.
    """
    # Start with the original prompt
    original = build_prompt(challenge_dir, mode=mode, strategy=strategy)

    # Build conversation history
    messages = [
        {"role": "user", "content": original["user"]},
        {"role": "assistant", "content": previous_code},
        {
            "role": "user",
            "content": f"""Your solution failed the tests. Here is the error output:

```
{error_output[:3000]}
```

Analyze what went wrong and provide a corrected solution.
Output ONLY the corrected code, nothing else.""",
        },
    ]

    return {"system": original["system"], "messages": messages}
