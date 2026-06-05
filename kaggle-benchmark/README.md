# kdb+/q output-prediction — Kaggle Benchmarks task

A companion to the local executable benchmark, designed to run on
[Kaggle Benchmarks](https://www.kaggle.com/benchmarks). The Kaggle sandbox has no
licensed kdb+/q, so the anti-cheat *code-execution* suites can't run there. This
task instead probes the same skill — a model's grasp of q's **evaluation model** —
by asking it to **predict the exact output** of q expressions drawn from the 7
challenges (right-to-left parsing, adverbs, temporal arithmetic, functional
select, grouping, sliding windows). Gold answers are precomputed locally with a
licensed q (`-3!` flat-text form) and embedded, so grading needs no q at run time.

## Files
- `kdb_q_prediction.py` — the self-contained `@kbench.task`. Prompts the model per
  item, grades by normalized exact match, returns `{accuracy, by_challenge, n}`.
- `gen_items.q` — regenerates the item battery + gold from a licensed q.
- `items.gold.json` — the generated items (tag, expr, gold), for review/diff.

## Regenerate the gold (needs a licensed q)
```bash
QHOME=~/q ~/q/m64/q gen_items.q > items.gold.json
# then re-embed the ITEMS list in kdb_q_prediction.py
```

## Push to Kaggle (needs auth)
The new Benchmarks flow rejects the legacy `~/.kaggle/kaggle.json`. Authenticate
first, then push + run:
```bash
# one-time auth (OAuth in browser) — or: export KAGGLE_API_TOKEN=...
kaggle auth login

# scaffold creds/.env (writes MODEL_PROXY_* + LLM_DEFAULT/LLMS_AVAILABLE)
kaggle benchmarks init -y

# create the task on Kaggle (returns the task page URL)
kaggle benchmarks tasks push kdb-q-output-prediction -f kdb_q_prediction.py --wait

# run it against models
kaggle benchmarks tasks run kdb-q-output-prediction \
  -m gemini-3.1-pro-preview -m claude-opus-4-8-default -m gpt-5.5-2026-04-23 --wait

# pull results
kaggle benchmarks tasks download kdb-q-output-prediction -o ./results
```
A *benchmark* (the public collection that wraps this task) is created in the
Kaggle web UI — the CLI manages individual tasks only.

## Scope note
This measures q **comprehension**, not code **generation**. It is a companion to,
not a replacement for, the executable anti-cheat benchmark in the repo root, which
remains the gold standard (run locally with a licensed q).
