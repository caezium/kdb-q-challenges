#!/usr/bin/env python3
"""Re-grade captured code-gen runs with the FIXED evaluator (multi-line load bug).

Reads every kaggle-benchmark/codegen_results/**/*.run.json, extracts each model's
generated q per challenge from the stored conversations, and re-runs the real
tests.q suites locally via runner.evaluator. Emits a corrected per-model board.

Run from the repo root with the licensed q reachable (QHOME=~/q).
"""
from __future__ import annotations
import glob, json, os, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from runner.evaluator import evaluate_q_challenge, extract_q_code  # noqa: E402

CHALLENGES = ["j1-lazy-scan", "h2-custom-adverb", "h3-temporal-bridge",
              "h4-functional-select", "h5-tree-unfold", "h6-vector-partition",
              "h7-adverb-algebra"]


def challenge_of(text: str):
    m = re.search(r"##\s*Challenge\s*\n#\s*([a-z0-9-]+)", text)
    return m.group(1) if m else None


def collect():
    """-> {model: {challenge: set(raw_response)}}"""
    out = defaultdict(lambda: defaultdict(set))
    for f in glob.glob(str(ROOT / "kaggle-benchmark/codegen_results/**/*.run.json"),
                       recursive=True):
        d = json.load(open(f))
        model = d["modelVersion"]["slug"]
        for conv in d.get("conversations", []):
            for r in conv.get("requests", []):
                user = "".join(p.get("text", "") for m in r["contents"]
                               if m.get("role") == "CONTENT_ROLE_USER"
                               for p in m.get("parts", []))
                asst = "".join(p.get("text", "") for m in r["contents"]
                               if m.get("role") == "CONTENT_ROLE_ASSISTANT"
                               for p in m.get("parts", []))
                ch = challenge_of(user)
                if ch and asst.strip():
                    out[model][ch].add(asst)
    return out


def main():
    data = collect()
    # board[model][challenge] = (passed_bool, "score/total")
    board = defaultdict(dict)
    cache = {}  # (challenge, code) -> result, to avoid re-running identical q
    for model in sorted(data):
        for ch in CHALLENGES:
            responses = data[model].get(ch)
            if not responses:
                board[model][ch] = (None, "n/a")
                continue
            best = (False, "0/?")
            for raw in responses:
                code = extract_q_code(raw)
                key = (ch, code)
                if key not in cache:
                    try:
                        cache[key] = evaluate_q_challenge(ROOT / ch, code)
                    except Exception as e:  # noqa: BLE001
                        cache[key] = {"status": "error", "score": 0,
                                      "total": 0, "errors": [str(e)]}
                res = cache[key]
                tag = f"{res['score']}/{res['total']}"
                if res["status"] == "pass":
                    best = (True, tag)
                    break
                if not best[0]:
                    best = (False, tag)
            board[model][ch] = best
            mark = "PASS" if best[0] else "fail"
            print(f"  {model:48s} {ch:22s} {mark} ({best[1]})", flush=True)

    print("\n=== CORRECTED BOARD (local re-grade, fixed evaluator) ===")
    rows = []
    for model in sorted(board):
        total = sum(1 for ch in CHALLENGES if board[model][ch][0])
        solved = [ch for ch in CHALLENGES if board[model][ch][0]]
        rows.append((total, model, solved))
    for total, model, solved in sorted(rows, reverse=True):
        print(f"  {model:48s} {total}/7  {solved}")

    # per-challenge solve rate
    print("\n=== per-challenge solve count ===")
    for ch in CHALLENGES:
        n = sum(1 for m in board if board[m][ch][0])
        print(f"  {ch:22s} {n}/{len(board)} models")

    json.dump({m: {c: list(v) for c, v in board[m].items()} for m in board},
              open(ROOT / "kaggle-benchmark/codegen_results/regrade_board.json", "w"),
              indent=2)
    print("\nwrote codegen_results/regrade_board.json")


if __name__ == "__main__":
    main()
