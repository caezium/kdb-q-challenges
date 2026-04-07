"""Results aggregation, reporting, and artifact management."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd


def _comb(n: int, k: int) -> int:
    """Compute C(n, k) safely."""
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def compute_pass_at_k(n: int, c: int, k: int) -> float:
    """Compute pass@k metric.

    Args:
        n: Total number of attempts.
        c: Number of correct (passing) attempts.
        k: k value for pass@k.

    Returns:
        pass@k as a float in [0, 1].
    """
    if n < k:
        return float("nan")
    if c == 0:
        return 0.0
    if c >= n:
        return 1.0
    return 1.0 - _comb(n - c, k) / _comb(n, k)


def save_artifacts(
    output_dir: Path,
    model_key: str,
    challenge_name: str,
    attempt: int,
    raw_response: str,
    code: str,
    test_output: str,
) -> None:
    """Save raw LLM response, extracted code, and test output as artifacts."""
    artifact_dir = output_dir / "artifacts" / model_key / challenge_name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"_attempt{attempt}" if attempt > 1 else ""

    (artifact_dir / f"response{suffix}.txt").write_text(raw_response)
    (artifact_dir / f"code{suffix}.q").write_text(code)
    (artifact_dir / f"test_output{suffix}.txt").write_text(test_output)


def aggregate_results(all_results: list[dict], run_meta: Optional[dict] = None) -> dict:
    """Aggregate per-challenge results into a summary.

    Args:
        all_results: List of result dicts from run_challenge.
        run_meta: Optional reproducibility metadata.

    Returns:
        Summary dict with overall stats per model.
    """
    df = pd.DataFrame(all_results)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_config": run_meta or {},
        "models": [],
    }

    for model, group in df.groupby("model"):
        n_challenges = len(group)
        passed = int((group["status"] == "pass").sum())
        first_shot = int(group["first_shot_pass"].sum()) if "first_shot_pass" in group else passed

        model_summary = {
            "model": model,
            "total_challenges": n_challenges,
            "passed": passed,
            "failed": int((group["status"] == "fail").sum()),
            "timed_out": int((group["status"] == "timeout").sum()),
            "errored": int((group["status"] == "error").sum()),
            "pass_rate": float((group["status"] == "pass").mean()),
            "first_shot_pass_rate": first_shot / n_challenges if n_challenges else 0,
            "avg_elapsed_ms": int(group["elapsed_ms"].mean()),
            "avg_attempts": float(group["attempts_used"].mean()) if "attempts_used" in group else 1.0,
            "challenges": [],
        }

        # Compute pass@k if we have attempt history
        if "attempt_history" in group.columns:
            for k_val in [1, 3, 5]:
                pass_k_scores = []
                for _, row in group.iterrows():
                    history = row.get("attempt_history", [])
                    n = len(history)
                    c = sum(1 for a in history if a.get("status") == "pass")
                    score = compute_pass_at_k(n, c, k_val)
                    if not math.isnan(score):
                        pass_k_scores.append(score)
                if pass_k_scores:
                    model_summary[f"pass@{k_val}"] = round(
                        sum(pass_k_scores) / len(pass_k_scores), 3
                    )

        for _, row in group.iterrows():
            ch_data = {
                "id": row["challenge"],
                "type": row.get("challenge_type", "q"),
                "status": row["status"],
                "score": row["score"],
                "total": row["total"],
                "elapsed_ms": row["elapsed_ms"],
                "sections": row.get("sections", {}),
                "attempts_used": row.get("attempts_used", 1),
                "first_shot_pass": row.get("first_shot_pass", row["status"] == "pass"),
                "prompt_hash": row.get("prompt_hash", ""),
            }
            if "attempt_history" in row:
                ch_data["attempt_history"] = row["attempt_history"]
            model_summary["challenges"].append(ch_data)

        summary["models"].append(model_summary)

    return summary


def save_results(summary: dict, output_dir: Path) -> tuple[Path, Path]:
    """Save results as both JSON and CSV.

    Returns:
        Tuple of (json_path, csv_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"results_{timestamp}.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    # Flatten for CSV
    rows = []
    for model_data in summary["models"]:
        for ch in model_data["challenges"]:
            row = {
                "model": model_data["model"],
                "challenge": ch["id"],
                "type": ch["type"],
                "status": ch["status"],
                "score": ch["score"],
                "total": ch["total"],
                "elapsed_ms": ch["elapsed_ms"],
                "attempts_used": ch.get("attempts_used", 1),
                "first_shot_pass": ch.get("first_shot_pass", False),
            }
            # Add section pass rates as columns
            for sec_name, sec_data in ch.get("sections", {}).items():
                row[f"sec_{sec_name}_passed"] = sec_data["passed"]
                row[f"sec_{sec_name}_failed"] = sec_data["failed"]
            rows.append(row)

    csv_path = output_dir / f"results_{timestamp}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    return json_path, csv_path


def generate_report(
    summary: dict, output_dir: Path, compare_path: Optional[str] = None
) -> Path:
    """Generate a human-readable markdown report.

    Returns:
        Path to the generated REPORT.md.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"REPORT_{timestamp}.md"

    lines = []
    lines.append("# kdb-q-challenges Benchmark Report\n")
    lines.append(f"**Generated:** {summary['generated_at']}\n")

    # Run config
    rc = summary.get("run_config", {})
    if rc:
        lines.append("## Run Configuration\n")
        lines.append(f"| Setting | Value |")
        lines.append(f"|---------|-------|")
        lines.append(f"| Strategy | {rc.get('strategy', 'zero-shot')} |")
        lines.append(f"| Max Attempts | {rc.get('max_attempts', 1)} |")
        lines.append(f"| Git Commit | `{rc.get('git_commit', 'unknown')[:8]}` |")
        lines.append(f"| q Version | {rc.get('q_version', 'unknown')} |")
        lines.append("")

    # Leaderboard
    models = sorted(summary["models"], key=lambda m: m["pass_rate"], reverse=True)
    lines.append("## Leaderboard\n")

    header = "| Rank | Model | Pass Rate | First-Shot | Passed | Avg Attempts | Avg ms |"
    sep = "|------|-------|-----------|------------|--------|--------------|--------|"
    lines.append(header)
    lines.append(sep)
    for i, m in enumerate(models, 1):
        fsr = f"{m.get('first_shot_pass_rate', m['pass_rate']):.0%}"
        lines.append(
            f"| {i} | {m['model']} | {m['pass_rate']:.0%} | {fsr} | "
            f"{m['passed']}/{m['total_challenges']} | {m.get('avg_attempts', 1):.1f} | "
            f"{m['avg_elapsed_ms']} |"
        )
    lines.append("")

    # Pass@k table if available
    has_pass_k = any("pass@1" in m for m in models)
    if has_pass_k:
        lines.append("## Pass@k\n")
        lines.append("| Model | Pass@1 | Pass@3 | Pass@5 |")
        lines.append("|-------|--------|--------|--------|")
        for m in models:
            p1 = f"{m.get('pass@1', '-')}"
            p3 = f"{m.get('pass@3', '-')}"
            p5 = f"{m.get('pass@5', '-')}"
            lines.append(f"| {m['model']} | {p1} | {p3} | {p5} |")
        lines.append("")

    # Per-challenge breakdown
    lines.append("## Per-Challenge Results\n")

    all_challenges = []
    for m in models:
        for ch in m["challenges"]:
            if ch["id"] not in all_challenges:
                all_challenges.append(ch["id"])

    header = "| Challenge |" + "".join(f" {m['model'][:20]} |" for m in models)
    sep = "|-----------|" + "".join("-" * (min(len(m["model"]), 20) + 2) + "|" for m in models)
    lines.append(header)
    lines.append(sep)

    for ch_id in all_challenges:
        row = f"| {ch_id} |"
        for m in models:
            ch = next((c for c in m["challenges"] if c["id"] == ch_id), None)
            if ch:
                status = ch["status"].upper()
                attempts = ch.get("attempts_used", 1)
                cell = status if attempts <= 1 else f"{status} ({attempts})"
                row += f" {cell} |"
            else:
                row += " --- |"
        lines.append(row)
    lines.append("")

    # Section-level heatmap
    lines.append("## Section Breakdown\n")
    lines.append("Shows passed/total per test section for each model-challenge pair.\n")

    for m in models:
        lines.append(f"### {m['model']}\n")
        # Collect all section names
        all_secs = set()
        for ch in m["challenges"]:
            all_secs.update(ch.get("sections", {}).keys())
        all_secs = sorted(all_secs)

        if all_secs:
            header = "| Challenge |" + "".join(f" {s} |" for s in all_secs)
            sep = "|-----------|" + "".join("------|" for _ in all_secs)
            lines.append(header)
            lines.append(sep)
            for ch in m["challenges"]:
                row = f"| {ch['id']} |"
                for s in all_secs:
                    sd = ch.get("sections", {}).get(s, {})
                    p = sd.get("passed", 0)
                    t = p + sd.get("failed", 0)
                    row += f" {p}/{t} |" if t > 0 else " - |"
                lines.append(row)
            lines.append("")
        else:
            lines.append("No section data available.\n")

    # Comparison with previous run
    if compare_path:
        try:
            prev = json.loads(Path(compare_path).read_text())
            lines.append("## Comparison with Previous Run\n")
            lines.append(f"Previous run: {prev.get('generated_at', 'unknown')}\n")

            prev_models = {m["model"]: m for m in prev.get("models", [])}
            lines.append("| Model | Prev Pass Rate | Curr Pass Rate | Delta |")
            lines.append("|-------|---------------|---------------|-------|")
            for m in models:
                prev_m = prev_models.get(m["model"])
                if prev_m:
                    prev_rate = prev_m["pass_rate"]
                    delta = m["pass_rate"] - prev_rate
                    sign = "+" if delta >= 0 else ""
                    lines.append(
                        f"| {m['model']} | {prev_rate:.0%} | {m['pass_rate']:.0%} | {sign}{delta:.0%} |"
                    )
            lines.append("")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            lines.append(f"## Comparison\n\nCould not load previous results: {e}\n")

    report_path.write_text("\n".join(lines))
    return report_path


def print_leaderboard(summary: dict) -> None:
    """Print a leaderboard to stdout."""
    print("\n" + "=" * 70)
    print("kdb-q-challenges Leaderboard")
    print("=" * 70)
    print(f"Generated: {summary['generated_at']}")

    rc = summary.get("run_config", {})
    if rc:
        print(f"Strategy: {rc.get('strategy', 'zero-shot')}  |  "
              f"Max attempts: {rc.get('max_attempts', 1)}")
    print()

    models = sorted(summary["models"], key=lambda m: m["pass_rate"], reverse=True)

    print(
        f"{'Rank':<6}{'Model':<25}{'Pass%':<8}{'1st-Shot':<10}"
        f"{'Passed':<10}{'Avg Try':<9}{'Avg ms':<8}"
    )
    print("-" * 70)

    for i, m in enumerate(models, 1):
        fsr = m.get("first_shot_pass_rate", m["pass_rate"])
        print(
            f"{i:<6}"
            f"{m['model']:<25}"
            f"{m['pass_rate']:.0%}{'':<5}"
            f"{fsr:.0%}{'':<7}"
            f"{m['passed']}/{m['total_challenges']}{'':<6}"
            f"{m.get('avg_attempts', 1):.1f}{'':<6}"
            f"{m['avg_elapsed_ms']}"
        )

    # Pass@k if available
    has_pass_k = any("pass@1" in m for m in models)
    if has_pass_k:
        print()
        print("Pass@k:")
        for m in models:
            parts = [f"  {m['model']}:"]
            for k in [1, 3, 5]:
                key = f"pass@{k}"
                if key in m:
                    parts.append(f"  @{k}={m[key]:.3f}")
            print("".join(parts))

    print()

    # Per-challenge breakdown
    print("Per-Challenge Breakdown:")
    print("-" * 70)

    all_challenges = []
    for m in models:
        for ch in m["challenges"]:
            if ch["id"] not in all_challenges:
                all_challenges.append(ch["id"])

    header = f"{'Challenge':<25}" + "".join(f"{m['model'][:15]:<17}" for m in models)
    print(header)
    print("-" * len(header))

    for ch_id in all_challenges:
        row = f"{ch_id:<25}"
        for m in models:
            ch = next((c for c in m["challenges"] if c["id"] == ch_id), None)
            if ch:
                status = ch["status"]
                icon = {
                    "pass": "PASS",
                    "fail": "FAIL",
                    "timeout": "TIME",
                    "error": "ERR",
                }
                attempts = ch.get("attempts_used", 1)
                cell = icon.get(status, status)
                if attempts > 1:
                    cell += f"({attempts})"
                row += f"{cell:<17}"
            else:
                row += f"{'---':<17}"
        print(row)

    print()
