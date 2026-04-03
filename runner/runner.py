#!/usr/bin/env python3
"""Main runner: evaluate LLM models against kdb+/q challenges.

Usage:
    python -m runner.runner --models claude-sonnet-4-6,gpt-4o --challenges all
    python -m runner.runner --models claude-sonnet-4-6 --challenges j1-lazy-scan,h2-custom-adverb
    python -m runner.runner --models claude-sonnet-4-6 --challenges all --include-pykx
"""

import argparse
import os
import sys
from pathlib import Path

from runner.evaluator import (
    evaluate_pykx_challenge,
    evaluate_q_challenge,
    extract_python_code,
    extract_q_code,
)
from runner.prompt import build_prompt
from runner.results import aggregate_results, print_leaderboard, save_results

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Challenge discovery
Q_CHALLENGES = sorted(
    [
        d.name
        for d in ROOT.iterdir()
        if d.is_dir()
        and (d / "challenge.q").exists()
        and (d / "tests.q").exists()
    ]
)

PYKX_CHALLENGES = sorted(
    [
        d.name
        for d in ROOT.iterdir()
        if d.is_dir()
        and (d / "challenge.py").exists()
        and (d / "tests.py").exists()
    ]
)

# Model configurations
MODELS = {
    "claude-sonnet-4-6": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "claude-opus-4-6": {"provider": "anthropic", "model": "claude-opus-4-6"},
    "claude-haiku-4-5": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
    "gpt-4.1": {"provider": "openai", "model": "gpt-4.1"},
    "gpt-4.1-mini": {"provider": "openai", "model": "gpt-4.1-mini"},
    "o3": {"provider": "openai", "model": "o3"},
    "o4-mini": {"provider": "openai", "model": "o4-mini"},
}


def call_llm(model_key: str, prompt: dict) -> str:
    """Call an LLM API and return the response text."""
    config = MODELS[model_key]
    provider = config["provider"]
    model = config["model"]

    if provider == "anthropic":
        return _call_anthropic(model, prompt)
    elif provider == "openai":
        return _call_openai(model, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_anthropic(model: str, prompt: dict) -> str:
    """Call Anthropic API."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=prompt["system"],
        messages=[{"role": "user", "content": prompt["user"]}],
    )
    return response.content[0].text


def _call_openai(model: str, prompt: dict) -> str:
    """Call OpenAI API."""
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
    )
    return response.choices[0].message.content


def run_challenge(model_key: str, challenge_name: str) -> dict:
    """Run a single challenge against a single model.

    Returns:
        Result dict with model, challenge, status, score, etc.
    """
    challenge_dir = ROOT / challenge_name
    is_pykx = (challenge_dir / "challenge.py").exists() and not (
        challenge_dir / "challenge.q"
    ).exists()
    mode = "pykx" if is_pykx else "q"

    print(f"  [{model_key}] {challenge_name} ({mode})...", end=" ", flush=True)

    # Build prompt and call LLM
    prompt = build_prompt(challenge_dir, mode=mode)
    try:
        raw_response = call_llm(model_key, prompt)
    except Exception as e:
        print(f"API ERROR: {e}")
        return {
            "model": model_key,
            "challenge": challenge_name,
            "challenge_type": mode,
            "status": "error",
            "score": 0,
            "total": 0,
            "elapsed_ms": 0,
            "errors": [str(e)],
            "raw_response": "",
            "raw_code": "",
        }

    # Extract code
    if mode == "pykx":
        code = extract_python_code(raw_response)
        result = evaluate_pykx_challenge(challenge_dir, code)
    else:
        code = extract_q_code(raw_response)
        result = evaluate_q_challenge(challenge_dir, code)

    status = result["status"]
    icon = {"pass": "PASS", "fail": "FAIL", "timeout": "TIMEOUT", "error": "ERROR"}
    print(f"{icon.get(status, status)} ({result['elapsed_ms']}ms)")

    return {
        "model": model_key,
        "challenge": challenge_name,
        "challenge_type": mode,
        "status": result["status"],
        "score": result["score"],
        "total": result["total"],
        "elapsed_ms": result["elapsed_ms"],
        "errors": result["errors"],
        "raw_response": raw_response,
        "raw_code": code,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate LLM models against kdb+/q challenges"
    )
    parser.add_argument(
        "--models",
        type=str,
        default="claude-sonnet-4-6",
        help=f"Comma-separated model keys. Available: {', '.join(MODELS.keys())}",
    )
    parser.add_argument(
        "--challenges",
        type=str,
        default="all",
        help="Comma-separated challenge names, or 'all' for all q challenges",
    )
    parser.add_argument(
        "--include-pykx",
        action="store_true",
        help="Include PyKX challenges in the run",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(ROOT / "results"),
        help="Output directory for results",
    )
    args = parser.parse_args()

    # Parse models
    model_keys = [m.strip() for m in args.models.split(",")]
    for mk in model_keys:
        if mk not in MODELS:
            print(f"Unknown model: {mk}. Available: {', '.join(MODELS.keys())}")
            sys.exit(1)

    # Parse challenges
    if args.challenges == "all":
        challenges = list(Q_CHALLENGES)
        if args.include_pykx:
            challenges.extend(PYKX_CHALLENGES)
    else:
        challenges = [c.strip() for c in args.challenges.split(",")]
        for c in challenges:
            if not (ROOT / c).is_dir():
                print(f"Challenge directory not found: {c}")
                sys.exit(1)

    # Verify API keys
    for mk in model_keys:
        provider = MODELS[mk]["provider"]
        if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set")
            sys.exit(1)
        if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY not set")
            sys.exit(1)

    print(f"Models:     {', '.join(model_keys)}")
    print(f"Challenges: {', '.join(challenges)}")
    print(f"Output:     {args.output}")
    print()

    # Run all combinations
    all_results = []
    for model_key in model_keys:
        print(f"\n=== {model_key} ===")
        for challenge in challenges:
            result = run_challenge(model_key, challenge)
            all_results.append(result)

    # Aggregate and save
    summary = aggregate_results(all_results)
    output_dir = Path(args.output)
    json_path, csv_path = save_results(summary, output_dir)

    print(f"\nResults saved to:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    # Print leaderboard
    print_leaderboard(summary)


if __name__ == "__main__":
    main()
