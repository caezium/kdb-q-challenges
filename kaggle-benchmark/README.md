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

## Live task
https://www.kaggle.com/benchmarks/tasks/caesium137/kdb-q-output-prediction/3

> The task returns `-> float` (accuracy) so the Kaggle leaderboard renders a
> **numerical score**. (A `-> dict` return is not rankable and the board shows
> every run as PASS/FAIL — that was the v1 bug.) Note: the Model-Proxy applies a
> per-request **cost cap**, so the pricier models (Opus/Sonnet) can 403 with
> "max estimated cost"; those runs score artificially low (the errors count as
> wrong). The cheaper models run clean.

### First run (June 2026, 25 items, temperature default)
| Model | Acc | weak spot |
|---|---|---|
| gemini-3.1-pro-preview | 1.00 | — |
| gemini-3-flash-preview | 0.96 | h3 |
| claude-opus-4-8 | 0.92 | h3, h7 |
| gpt-5.5 | 0.92 | h3 |
| claude-sonnet-4-6 | 0.84 | j1, h3, h6, h7 |

**h3 (temporal arithmetic) is the universal weak spot** — only gemini-3.1-pro gets
it (models miss that `date-date` is `9i` not `9`, or that a `second` subtraction is
`00:00:40` not `00:00:40.000`). This cross-validates the code-gen benchmark, where
Gemini 3.1 Pro was likewise the only model to solve `h3-temporal-bridge`.

Note: the top model already saturates at 1.0, so the battery should be expanded /
hardened (more temporal + parsing traps, deeper functional-select forms) before
this is a discriminating frontier benchmark.

## Scope note
This measures q **comprehension**, not code **generation**. It is a companion to,
not a replacement for, the executable anti-cheat benchmark in the repo root, which
remains the gold standard (run locally with a licensed q).
