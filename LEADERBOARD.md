# kdb-q-challenges Leaderboard

Official results from running the benchmark against frontier LLMs via OpenRouter.

**Last updated:** 2026-04-10
**Strategy:** zero-shot
**Max attempts:** 3 (with error feedback on retries)
**Evaluator:** user's kdb+ personal edition via subprocess
**Seed:** benchmark randomness is seeded; model stochasticity is not controlled

## Overall Leaderboard

| Rank | Model | Provider | First-Shot | Best-of-3 | Passed |
|------|-------|----------|------------|-----------|--------|
| 1 | **Gemini 3.1 Pro Preview** | Google | 57% | **86%** | 6/7 |
| 2 | Claude Opus 4.6 | Anthropic | 29% | 57% | 4/7 |
| 2 | Claude Sonnet 4.6 | Anthropic | 43% | 57% | 4/7 |
| 4 | Gemini 3.1 Flash Lite Preview | Google | 43% | 43% | 3/7 |
| 5 | GPT-5.4 | OpenAI | 29% | 29% | 2/7 |
| 5 | Kimi K2.5 | MoonshotAI | 14% | 29% | 2/7 |

## Per-Challenge Matrix

Status legend: `PASS(N)` = passed on attempt N, `FAIL(3)` = failed all 3 attempts, `ERROR` = code extraction/execution crash.

| Challenge | Gemini Pro | Opus 4.6 | Sonnet 4.6 | Gemini Flash | GPT-5.4 | Kimi K2.5 | Pass Rate |
|-----------|-----------|----------|------------|--------------|---------|-----------|-----------|
| j1 lazy-scan | PASS(1) | PASS(1) | PASS(1) | PASS(1) | PASS(1) | PASS(1) | 6/6 (100%) |
| h2 custom-adverb | PASS(1) | PASS(1) | PASS(1) | PASS(1) | PASS(1) | FAIL(3) | 5/6 (83%) |
| h6 vector-partition | PASS(1) | PASS(2) | PASS(2) | PASS(1) | FAIL(3) | FAIL(3) | 4/6 (67%) |
| h5 tree-unfold | PASS(2) | PASS(2) | PASS(1) | FAIL(3) | FAIL(3) | FAIL(3) | 3/6 (50%) |
| h7 adverb-algebra | PASS(1) | FAIL(3) | FAIL(3) | FAIL(3) | FAIL(3) | PASS(3) | 2/6 (33%) |
| h3 temporal-bridge | PASS(2) | FAIL(3) | FAIL(3) | FAIL(3) | FAIL(3) | FAIL(3) | 1/6 (17%) |
| h4 functional-select | FAIL(3) | FAIL(3) | FAIL(3) | FAIL(3) | FAIL(3) | ERROR(3) | **0/6 (0%)** |

## First-Shot vs Best-of-3 Improvement

Retries with error feedback help some models more than others.

| Model | First-Shot | Best-of-3 | Δ (percentage points) |
|-------|-----------|-----------|----------------------|
| Claude Opus 4.6 | 2/7 (29%) | 4/7 (57%) | **+28** |
| Gemini 3.1 Pro | 4/7 (57%) | 6/7 (86%) | **+29** |
| Claude Sonnet 4.6 | 3/7 (43%) | 4/7 (57%) | +14 |
| Kimi K2.5 | 1/7 (14%) | 2/7 (29%) | +14 |
| Gemini 3.1 Flash | 3/7 (43%) | 3/7 (43%) | 0 |
| GPT-5.4 | 2/7 (29%) | 2/7 (29%) | 0 |

**Weaker models can't act on error feedback for q** — they keep producing the same category of mistakes across retries. Frontier models (Opus, Sonnet, Gemini Pro) convert retries into actual fixes.

## Per-Challenge Difficulty Ranking

| Rank | Challenge | Solved By | Verdict |
|------|-----------|-----------|---------|
| 1 | j1 lazy-scan | 6/6 (100%) | Tractable — all models got it first shot in this run |
| 2 | h2 custom-adverb | 5/6 (83%) | Functional composition transfers from other languages |
| 3 | h6 vector-partition | 4/6 (67%) | Easy if you know `group flip`; no-loops constraint is the filter |
| 4 | h5 tree-unfold | 3/6 (50%) | BFS without stack overflow — known algorithm, subtle state threading |
| 5 | h7 adverb-algebra | 2/6 (33%) | Incremental sliding window — invocation counting catches brute force |
| 6 | h3 temporal-bridge | 1/6 (17%) | `aj` + post-processing staleness — only Gemini Pro solved it |
| 7 | **h4 functional-select** | **0/6 (0%)** | **Unsolved.** Parse tree `enlist` semantics defeat every model tested |

## Key Findings

### 1. Gemini 3.1 Pro is the clear winner at rare-language coding
86% best-of-3 — the only model to pass 6/7 challenges, and the only model to solve h3 (temporal-bridge). This is surprising given Gemini's mixed reputation on general coding benchmarks.

### 2. h4 is a hard floor that no model can clear
0/6 models solved h4-functional-select. The challenge tests knowledge of q's functional select parse tree `(?;table;where;by;agg)` with the notoriously confusing `enlist` semantics for single-where clauses. This pattern is rare in training data and models can't derive it from first principles.

### 3. h3 is surprisingly hard
Only Gemini Pro solved h3-temporal-bridge (`aj` + staleness post-processing). Both Claude models failed it — suggesting this specific kdb+ pattern isn't in their training data despite being a classic financial time-series use case.

### 4. Kimi's "solved" h7 is a curious result
Kimi K2.5 solved h7 (adverb-algebra) on attempt 3 despite failing every other non-trivial challenge. The h7 anti-cheat (invocation counting) is one of the strictest in the suite. Without inspecting the response, it's unclear whether this is a genuine solve or a lucky copy of a memorized pattern.

### 5. Non-determinism affects ~1 challenge per model per run
Repeated runs show ±1 challenge variation even with the same model and prompt. A serious benchmark run should use N=5+ samples and report variance, not point estimates.

## Pass@k Notes

The `--attempts 3` mode terminates on the first passing attempt, so Pass@k values in the saved JSON use `n = attempts_used` rather than a fixed `n = 3`. This makes the reported Pass@3 values misleading (often 0.0 because passing challenges have n=1 < k=3). To compute meaningful Pass@k, set `--attempts` equal to your target k and don't terminate early — a future runner flag could support this.

## Run Configuration

```
Provider:   OpenRouter
Strategy:   zero-shot
Attempts:   3 (with error feedback on retries)
Evaluator:  subprocess q (user's kdb+ personal edition)
Challenges: all 7 pure-q challenges (j1, h2-h7)
```

Source JSON files (in local `results/` directory, gitignored):
- `results_20260410_131354.json` — Opus 4.6, Sonnet 4.6, GPT-5.4 (parallel)
- `results_20260409_144543.json` — Gemini Pro, Gemini Flash (parallel)
- `results_20260408_135619.json` — Kimi K2.5 h2-h7
- `results_20260410_112712.json` — Kimi K2.5 j1 (rerun after earlier run crashed on h4)

## How to Reproduce

```bash
export OPENROUTER_API_KEY=sk-or-v1-...

python -m runner.runner \
  --models or-opus-4.6,or-sonnet-4.6,or-gpt-5.4,or-gemini-3.1-pro,or-gemini-3.1-flash \
  --challenges all \
  --strategy zero-shot \
  --attempts 3 \
  --parallel \
  --output ./results

# Run Kimi separately — it's ~5x slower than other models and can hang
python -m runner.runner \
  --models or-kimi-k2.5 \
  --challenges all \
  --strategy zero-shot \
  --attempts 3 \
  --output ./results
```
