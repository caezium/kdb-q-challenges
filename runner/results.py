"""Results aggregation and reporting."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def aggregate_results(all_results: list[dict]) -> dict:
    """Aggregate per-challenge results into a summary.

    Args:
        all_results: List of dicts with keys: model, challenge, challenge_type,
                     status, score, total, elapsed_ms, errors.

    Returns:
        Summary dict with overall stats per model.
    """
    df = pd.DataFrame(all_results)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": [],
    }

    for model, group in df.groupby("model"):
        model_summary = {
            "model": model,
            "total_challenges": len(group),
            "passed": int((group["status"] == "pass").sum()),
            "failed": int((group["status"] == "fail").sum()),
            "timed_out": int((group["status"] == "timeout").sum()),
            "errored": int((group["status"] == "error").sum()),
            "pass_rate": float((group["status"] == "pass").mean()),
            "avg_elapsed_ms": int(group["elapsed_ms"].mean()),
            "challenges": [],
        }

        for _, row in group.iterrows():
            model_summary["challenges"].append(
                {
                    "id": row["challenge"],
                    "type": row.get("challenge_type", "q"),
                    "status": row["status"],
                    "score": row["score"],
                    "total": row["total"],
                    "elapsed_ms": row["elapsed_ms"],
                }
            )

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
    json_path.write_text(json.dumps(summary, indent=2))

    # Flatten for CSV
    rows = []
    for model_data in summary["models"]:
        for ch in model_data["challenges"]:
            rows.append(
                {
                    "model": model_data["model"],
                    "challenge": ch["id"],
                    "type": ch["type"],
                    "status": ch["status"],
                    "score": ch["score"],
                    "total": ch["total"],
                    "elapsed_ms": ch["elapsed_ms"],
                }
            )

    csv_path = output_dir / f"results_{timestamp}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    return json_path, csv_path


def print_leaderboard(summary: dict) -> None:
    """Print a simple leaderboard to stdout."""
    print("\n" + "=" * 60)
    print("kdb-q-challenges Leaderboard")
    print("=" * 60)
    print(f"Generated: {summary['generated_at']}\n")

    # Sort by pass rate descending
    models = sorted(summary["models"], key=lambda m: m["pass_rate"], reverse=True)

    print(f"{'Rank':<6}{'Model':<30}{'Pass Rate':<12}{'Passed':<10}{'Avg ms':<10}")
    print("-" * 60)

    for i, m in enumerate(models, 1):
        print(
            f"{i:<6}"
            f"{m['model']:<30}"
            f"{m['pass_rate']:.0%}{'':<8}"
            f"{m['passed']}/{m['total_challenges']}{'':<6}"
            f"{m['avg_elapsed_ms']}"
        )

    print()

    # Per-challenge breakdown
    print("Per-Challenge Breakdown:")
    print("-" * 60)

    # Collect all challenge IDs
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
            ch_result = next(
                (c for c in m["challenges"] if c["id"] == ch_id), None
            )
            if ch_result:
                status = ch_result["status"]
                icon = {"pass": "PASS", "fail": "FAIL", "timeout": "TIME", "error": "ERR"}
                row += f"{icon.get(status, status):<17}"
            else:
                row += f"{'---':<17}"
        print(row)

    print()
