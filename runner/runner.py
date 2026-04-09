#!/usr/bin/env python3
"""Main runner: evaluate LLM models against kdb+/q challenges.

Usage:
    python -m runner.runner --models claude-sonnet-4-6,gpt-4o --challenges all
    python -m runner.runner --models claude-sonnet-4-6 --challenges all --attempts 3 --strategy cot
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from runner.evaluator import (
    evaluate_pykx_challenge,
    evaluate_q_challenge,
    extract_python_code,
    extract_q_code,
)
from runner.prompt import build_prompt, build_retry_prompt
from runner.results import (
    aggregate_results,
    generate_report,
    print_leaderboard,
    save_artifacts,
    save_results,
)

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
    # Direct API providers
    "claude-sonnet-4-6": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "claude-opus-4-6": {"provider": "anthropic", "model": "claude-opus-4-6"},
    "claude-haiku-4-5": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
    "gpt-4.1": {"provider": "openai", "model": "gpt-4.1"},
    "gpt-4.1-mini": {"provider": "openai", "model": "gpt-4.1-mini"},
    "o3": {"provider": "openai", "model": "o3"},
    "o4-mini": {"provider": "openai", "model": "o4-mini"},
    # OpenRouter models
    "or-opus-4.6": {"provider": "openrouter", "model": "anthropic/claude-opus-4.6"},
    "or-sonnet-4.6": {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6"},
    "or-gpt-5.4": {"provider": "openrouter", "model": "openai/gpt-5.4"},
    "or-kimi-k2.5": {"provider": "openrouter", "model": "moonshotai/kimi-k2.5"},
    "or-gemini-3.1-pro": {"provider": "openrouter", "model": "google/gemini-3.1-pro-preview"},
    "or-gemini-3.1-flash": {"provider": "openrouter", "model": "google/gemini-3.1-flash-lite-preview"},
}


def call_llm(model_key: str, prompt: dict) -> str:
    """Call an LLM API and return the response text.

    Supports both single-turn (system + user) and multi-turn (system + messages).
    """
    config = MODELS[model_key]
    provider = config["provider"]
    model = config["model"]

    if provider == "anthropic":
        return _call_anthropic(model, prompt)
    elif provider == "openai":
        return _call_openai(model, prompt)
    elif provider == "openrouter":
        return _call_openrouter(model, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_anthropic(model: str, prompt: dict) -> str:
    """Call Anthropic API. Supports single-turn and multi-turn."""
    import anthropic

    client = anthropic.Anthropic()

    if "messages" in prompt:
        messages = prompt["messages"]
    else:
        messages = [{"role": "user", "content": prompt["user"]}]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=prompt["system"],
        messages=messages,
    )
    return response.content[0].text


def _call_openai(model: str, prompt: dict) -> str:
    """Call OpenAI API. Supports single-turn and multi-turn."""
    import openai

    client = openai.OpenAI()

    if "messages" in prompt:
        messages = [{"role": "system", "content": prompt["system"]}] + prompt[
            "messages"
        ]
    else:
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=messages,
    )
    return response.choices[0].message.content


def _call_openrouter(model: str, prompt: dict) -> str:
    """Call OpenRouter API (OpenAI-compatible with different base URL)."""
    import openai

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    )

    if "messages" in prompt:
        messages = [{"role": "system", "content": prompt["system"]}] + prompt[
            "messages"
        ]
    else:
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def _get_run_metadata(model_keys: list, strategy: str, max_attempts: int) -> dict:
    """Collect reproducibility metadata for the run."""
    meta = {
        "models": {k: MODELS[k] for k in model_keys},
        "strategy": strategy,
        "max_attempts": max_attempts,
    }

    # Git commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        meta["git_commit"] = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        meta["git_commit"] = None

    # q version
    try:
        result = subprocess.run(
            ["q", "-e", ".z.K"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        meta["q_version"] = result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        meta["q_version"] = None

    return meta


def run_challenge(
    model_key: str,
    challenge_name: str,
    strategy: str = "zero-shot",
    max_attempts: int = 1,
    output_dir: Optional[Path] = None,
) -> dict:
    """Run a single challenge against a single model with optional retries.

    Returns:
        Result dict with model, challenge, status, score, sections, attempt_history, etc.
    """
    challenge_dir = ROOT / challenge_name
    is_pykx = (challenge_dir / "challenge.py").exists() and not (
        challenge_dir / "challenge.q"
    ).exists()
    mode = "pykx" if is_pykx else "q"

    print(f"  [{model_key}] {challenge_name} ({mode})...", end=" ", flush=True)

    attempt_history = []
    last_code = ""
    last_error = ""
    last_result = None

    for attempt in range(max_attempts):
        if attempt > 0:
            print(f"retry {attempt}...", end=" ", flush=True)

        # Build prompt
        if attempt == 0:
            prompt = build_prompt(challenge_dir, mode=mode, strategy=strategy)
        else:
            prompt = build_retry_prompt(
                challenge_dir,
                previous_code=last_code,
                error_output=last_error,
                mode=mode,
                strategy=strategy,
            )

        # Compute prompt hash for reproducibility
        prompt_str = prompt["system"] + str(prompt.get("user", "")) + str(
            prompt.get("messages", "")
        )
        prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:16]

        # Call LLM
        try:
            raw_response = call_llm(model_key, prompt)
        except Exception as e:
            attempt_history.append(
                {"attempt": attempt + 1, "status": "error", "error": str(e)}
            )
            last_error = str(e)
            continue

        # Extract code
        if mode == "pykx":
            code = extract_python_code(raw_response)
            result = evaluate_pykx_challenge(challenge_dir, code)
        else:
            code = extract_q_code(raw_response)
            result = evaluate_q_challenge(challenge_dir, code)

        last_code = code
        last_result = result
        last_error = result.get("raw_output", "")

        attempt_history.append(
            {
                "attempt": attempt + 1,
                "status": result["status"],
                "score": result["score"],
                "total": result["total"],
                "elapsed_ms": result["elapsed_ms"],
                "sections": result.get("sections", {}),
            }
        )

        # Save artifacts if output dir given
        if output_dir is not None:
            save_artifacts(
                output_dir,
                model_key,
                challenge_name,
                attempt + 1,
                raw_response,
                code,
                result.get("raw_output", ""),
            )

        # Stop retrying on success
        if result["status"] == "pass":
            break

    # Determine final status
    final_status = last_result["status"] if last_result else "error"
    final_score = last_result["score"] if last_result else 0
    final_total = last_result["total"] if last_result else 0
    final_sections = last_result.get("sections", {}) if last_result else {}

    status_icon = {
        "pass": "PASS",
        "fail": "FAIL",
        "timeout": "TIMEOUT",
        "error": "ERROR",
    }
    attempts_str = f" ({len(attempt_history)} attempts)" if max_attempts > 1 else ""
    print(f"{status_icon.get(final_status, final_status)}{attempts_str}")

    return {
        "model": model_key,
        "challenge": challenge_name,
        "challenge_type": mode,
        "status": final_status,
        "score": final_score,
        "total": final_total,
        "elapsed_ms": last_result["elapsed_ms"] if last_result else 0,
        "errors": last_result["errors"] if last_result else [last_error],
        "sections": final_sections,
        "attempts_used": len(attempt_history),
        "first_shot_pass": (
            attempt_history[0]["status"] == "pass" if attempt_history else False
        ),
        "attempt_history": attempt_history,
        "prompt_hash": prompt_hash,
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
        "--attempts",
        type=int,
        default=1,
        help="Max attempts per challenge (1-5). On failure, error is fed back.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="zero-shot",
        choices=["zero-shot", "cot", "few-shot"],
        help="Prompting strategy",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(ROOT / "results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Don't save raw responses and code artifacts",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run models in parallel (faster, but interleaved output)",
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="Path to a previous results JSON for comparison in the report",
    )
    args = parser.parse_args()

    # Validate
    args.attempts = max(1, min(5, args.attempts))

    model_keys = [m.strip() for m in args.models.split(",")]
    for mk in model_keys:
        if mk not in MODELS:
            print(f"Unknown model: {mk}. Available: {', '.join(MODELS.keys())}")
            sys.exit(1)

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
        if provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
            print("OPENROUTER_API_KEY not set")
            sys.exit(1)

    output_dir = Path(args.output)
    artifact_dir = output_dir if not args.no_artifacts else None

    print(f"Models:     {', '.join(model_keys)}")
    print(f"Challenges: {', '.join(challenges)}")
    print(f"Strategy:   {args.strategy}")
    print(f"Attempts:   {args.attempts}")
    print(f"Output:     {args.output}")
    print()

    # Collect metadata
    run_meta = _get_run_metadata(model_keys, args.strategy, args.attempts)

    # Run all combinations — models in parallel, challenges sequential per model
    def _run_model(model_key):
        """Run all challenges for a single model sequentially."""
        results = []
        print(f"\n=== {model_key} ===")
        for challenge in challenges:
            result = run_challenge(
                model_key,
                challenge,
                strategy=args.strategy,
                max_attempts=args.attempts,
                output_dir=artifact_dir,
            )
            results.append(result)
        return results

    all_results = []
    if args.parallel and len(model_keys) > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        print(f"[parallel mode: {len(model_keys)} models concurrently]")
        with ThreadPoolExecutor(max_workers=len(model_keys)) as pool:
            futures = {
                pool.submit(_run_model, mk): mk for mk in model_keys
            }
            for future in as_completed(futures):
                mk = futures[future]
                try:
                    all_results.extend(future.result())
                except Exception as e:
                    print(f"\nERROR running {mk}: {e}")
    else:
        for model_key in model_keys:
            all_results.extend(_run_model(model_key))

    # Aggregate and save
    summary = aggregate_results(all_results, run_meta)
    json_path, csv_path = save_results(summary, output_dir)

    print(f"\nResults saved to:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    # Generate markdown report
    report_path = generate_report(summary, output_dir, compare_path=args.compare)
    print(f"  Report: {report_path}")

    # Print leaderboard
    print_leaderboard(summary)


if __name__ == "__main__":
    main()
