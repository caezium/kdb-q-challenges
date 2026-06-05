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
import re
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


# Token budgets. Reasoning models spend tokens on hidden chain-of-thought
# before emitting the answer, so they need a far larger ceiling or the actual
# code gets truncated and the attempt fails for the wrong reason.
MAX_TOKENS_STANDARD = 8192
MAX_TOKENS_REASONING = 32768


def _is_openai_reasoning(model: str) -> bool:
    """True for OpenAI-family reasoning models (o-series, GPT-5+).

    These reject `max_tokens` (need `max_completion_tokens`) and reject any
    `temperature` other than the default. `model` may carry a provider prefix
    (e.g. "openai/gpt-5.4") when called via OpenRouter.
    """
    name = model.split("/")[-1]
    return bool(re.match(r"o\d", name)) or name.startswith("gpt-5")


def call_llm(model_key: str, prompt: dict, temperature: float = 0.0) -> str:
    """Call an LLM API and return the response text.

    Supports both single-turn (system + user) and multi-turn (system + messages).
    `temperature` is threaded through for reproducibility (0.0) or for drawing
    diverse independent samples (>0, needed for an honest pass@k).
    """
    config = MODELS[model_key]
    provider = config["provider"]
    model = config["model"]

    if provider == "anthropic":
        return _call_anthropic(model, prompt, temperature)
    elif provider in ("openai", "openrouter"):
        return _call_openai_compatible(model, prompt, temperature, provider)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _messages_for(prompt: dict, include_system_role: bool) -> list:
    """Build the message list from a prompt dict (single- or multi-turn)."""
    turns = prompt["messages"] if "messages" in prompt else [
        {"role": "user", "content": prompt["user"]}
    ]
    if include_system_role:
        return [{"role": "system", "content": prompt["system"]}] + turns
    return turns


def _call_anthropic(model: str, prompt: dict, temperature: float) -> str:
    """Call Anthropic API. Supports single-turn and multi-turn."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS_STANDARD,
        temperature=temperature,
        system=prompt["system"],
        messages=_messages_for(prompt, include_system_role=False),
    )
    # Concatenate text blocks; thinking blocks (if any) are not `.text`.
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text")


def _call_openai_compatible(
    model: str, prompt: dict, temperature: float, provider: str
) -> str:
    """Call OpenAI or any OpenAI-compatible endpoint (e.g. OpenRouter).

    Handles the reasoning-model API differences: `max_completion_tokens`
    instead of `max_tokens`, and no custom `temperature`.
    """
    import openai

    if provider == "openrouter":
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
    else:
        client = openai.OpenAI()

    messages = _messages_for(prompt, include_system_role=True)
    kwargs = {"model": model, "messages": messages}

    if _is_openai_reasoning(model):
        kwargs["max_completion_tokens"] = MAX_TOKENS_REASONING
        # temperature is intentionally omitted — reasoning models reject it.
    else:
        kwargs["max_tokens"] = MAX_TOKENS_STANDARD
        kwargs["temperature"] = temperature

    response = client.chat.completions.create(**kwargs)
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
    temperature: float = 0.0,
) -> dict:
    """Run a single challenge against a single model with optional retries.

    Retries here are *sequential with error feedback* (an agentic loop), not
    independent samples — so the resulting metric is best-of-N, not pass@k.
    Use ``run_challenge_samples`` for an honest pass@k.

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
    first_prompt_hash = ""

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

        # Compute prompt hash for reproducibility (record the first-attempt
        # prompt — that's the one that defines a run for comparison purposes).
        prompt_str = prompt["system"] + str(prompt.get("user", "")) + str(
            prompt.get("messages", "")
        )
        prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:16]
        if attempt == 0:
            first_prompt_hash = prompt_hash

        # Call LLM
        try:
            raw_response = call_llm(model_key, prompt, temperature=temperature)
        except Exception as e:
            attempt_history.append(
                {"attempt": attempt + 1, "status": "error", "error": str(e)}
            )
            last_error = str(e)
            continue

        # Extract code
        if mode == "pykx":
            code = extract_python_code(raw_response)
        else:
            code = extract_q_code(raw_response)

        # No extractable code is a harness/format failure, not a wrong answer.
        # Score it as "error" so it doesn't masquerade as a model that tried
        # and got the q semantics wrong.
        if not code.strip():
            result = {
                "status": "error",
                "score": 0,
                "total": 0,
                "errors": ["No code block found in model response"],
                "elapsed_ms": 0,
                "raw_output": raw_response[:3000],
                "sections": {},
            }
        elif mode == "pykx":
            result = evaluate_pykx_challenge(challenge_dir, code)
        else:
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
        "prompt_hash": first_prompt_hash,
    }


def run_challenge_samples(
    model_key: str,
    challenge_name: str,
    n_samples: int,
    strategy: str = "zero-shot",
    output_dir: Optional[Path] = None,
    temperature: float = 0.6,
) -> dict:
    """Draw N *independent* single-shot samples for an honest pass@k.

    No error feedback, no early stop — every sample sees the same fresh prompt.
    This is the sampling regime the HumanEval/Codex pass@k estimator assumes.
    Returns a result dict shaped like ``run_challenge`` plus ``n_samples`` and
    ``n_correct`` so the aggregator can compute the unbiased pass@k.
    """
    challenge_dir = ROOT / challenge_name
    is_pykx = (challenge_dir / "challenge.py").exists() and not (
        challenge_dir / "challenge.q"
    ).exists()
    mode = "pykx" if is_pykx else "q"

    print(
        f"  [{model_key}] {challenge_name} ({mode}) x{n_samples} @T={temperature}...",
        end=" ",
        flush=True,
    )

    prompt = build_prompt(challenge_dir, mode=mode, strategy=strategy)
    prompt_str = prompt["system"] + str(prompt.get("user", ""))
    prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:16]

    sample_history = []
    n_correct = 0
    best = None
    for i in range(n_samples):
        try:
            raw_response = call_llm(model_key, prompt, temperature=temperature)
        except Exception as e:
            sample_history.append({"sample": i + 1, "status": "error", "error": str(e)})
            continue

        code = extract_python_code(raw_response) if mode == "pykx" else extract_q_code(raw_response)
        if not code.strip():
            result = {"status": "error", "score": 0, "total": 0, "errors": [],
                      "elapsed_ms": 0, "raw_output": raw_response[:3000], "sections": {}}
        elif mode == "pykx":
            result = evaluate_pykx_challenge(challenge_dir, code)
        else:
            result = evaluate_q_challenge(challenge_dir, code)

        if output_dir is not None:
            save_artifacts(output_dir, model_key, challenge_name, i + 1,
                           raw_response, code, result.get("raw_output", ""))

        if result["status"] == "pass":
            n_correct += 1
        if best is None or result["status"] == "pass":
            best = result
        sample_history.append({
            "sample": i + 1, "status": result["status"],
            "score": result["score"], "total": result["total"],
            "sections": result.get("sections", {}),
        })

    best = best or {"status": "error", "score": 0, "total": 0,
                    "errors": ["all samples errored"], "elapsed_ms": 0, "sections": {}}
    passed = n_correct > 0
    print(f"{n_correct}/{n_samples} passed")

    return {
        "model": model_key,
        "challenge": challenge_name,
        "challenge_type": mode,
        "status": "pass" if passed else best["status"],
        "score": best["score"],
        "total": best["total"],
        "elapsed_ms": best.get("elapsed_ms", 0),
        "errors": best.get("errors", []),
        "sections": best.get("sections", {}),
        "n_samples": n_samples,
        "n_correct": n_correct,
        "sample_history": sample_history,
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
        help="Max sequential attempts per challenge (1-5). On failure, the error "
        "is fed back (agentic best-of-N — NOT pass@k). Mutually exclusive with --samples.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Draw N independent single-shot samples per challenge for an honest "
        "pass@k (no feedback, no early stop). Overrides --attempts when > 1.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature. Default 0.0 for reproducibility, or 0.6 when "
        "--samples > 1 (pass@k needs sample diversity). Ignored by reasoning models.",
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
    args.samples = max(1, args.samples)
    sampling_mode = args.samples > 1
    # Default temperature: deterministic unless we're drawing samples for pass@k.
    if args.temperature is None:
        args.temperature = 0.6 if sampling_mode else 0.0
    if sampling_mode and args.attempts > 1:
        print("[note] --samples > 1 overrides --attempts; using independent sampling.")

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
    if sampling_mode:
        print(f"Samples:    {args.samples} (independent, pass@k)")
    print(f"Temperature:{args.temperature}")
    print()

    # Collect metadata
    run_meta = _get_run_metadata(model_keys, args.strategy, args.attempts)
    run_meta["temperature"] = args.temperature
    run_meta["mode"] = "samples" if sampling_mode else "attempts"
    if sampling_mode:
        run_meta["samples"] = args.samples

    # Run all combinations — models in parallel, challenges sequential per model
    def _run_model(model_key):
        """Run all challenges for a single model sequentially."""
        results = []
        print(f"\n=== {model_key} ===")
        for challenge in challenges:
            if sampling_mode:
                result = run_challenge_samples(
                    model_key,
                    challenge,
                    n_samples=args.samples,
                    strategy=args.strategy,
                    output_dir=artifact_dir,
                    temperature=args.temperature,
                )
            else:
                result = run_challenge(
                    model_key,
                    challenge,
                    strategy=args.strategy,
                    max_attempts=args.attempts,
                    output_dir=artifact_dir,
                    temperature=args.temperature,
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
