# Benchmark Hardening — findings & fixes

A skeptical audit of the runner and test suites, and what was changed in response.
Grouped by whether a fix shipped or the issue is documented for follow-up.

## Fixed

### 1. Reasoning-model API calls were broken (scores were garbage for them)
`_call_openai` sent `max_tokens=4096` via `chat.completions` to `o3`/`o4-mini`
(and would to GPT-5). Current OpenAI reasoning models **reject `max_tokens`**
(need `max_completion_tokens`), **reject a custom `temperature`**, and spend the
token budget on hidden reasoning — so the real answer was truncated or the call
errored, and the result was scored as a *wrong answer* rather than a harness
failure. Any o-series / GPT-5 number in the old leaderboard is therefore suspect.

**Fix:** `runner.py` now detects OpenAI-family reasoning models
(`_is_openai_reasoning`) and uses `max_completion_tokens`, omits `temperature`,
and raises the budget to 32k. Non-reasoning models get `max_tokens` + an explicit
temperature. (`runner/runner.py`)

### 2. "Pass@k" was mislabeled best-of-N
The estimator in `results.py` was the correct HumanEval formula, but it was fed
`n = attempts_used` from **sequential, error-feedback** retries with **early
stop** — not k i.i.d. samples. Reporting that as "Pass@3" invites false
comparison with published numbers (LEADERBOARD.md even noted the values came out
"often 0.0").

**Fix:** retry mode now reports `best_of_n_pass_rate` and never emits `pass@k`.
A new `--samples N` mode draws **independent** single-shot samples (no feedback,
no early stop, non-zero temperature) and computes the unbiased pass@k from those.
(`runner/runner.py`, `runner/results.py`)

### 3. Correctness was gated on wall-clock time (non-reproducible)
Every suite had `assert elapsed < <const ms>`. A correct O(n) solution could FAIL
on a slow/loaded box and a wrong one PASS on a fast one — directly contradicting
the repo's reproducibility claims. **Fixed across all 7 pure-q challenges**, each
with the right per-challenge signal and verified against a reference solution:
- **h6** — relative to the vectorized `group` primitive (within 25×), so
  element-wise cheats blow up regardless of hardware. (observed ~1.2×)
- **h7** — wall-clock assert removed; the **invocation-count** checks (O(n) not
  O(n·w)) are exact and machine-independent and already encode the property.
- **j1** — early-stop asserted relative to a full O(n) pass (a short-circuiting
  solution is far faster than scanning everything). (observed ~0× vs 8ms)
- **h2** — wall-clock assert removed; there is no perf-based anti-cheat (a
  precompute cheat is caught by the "returns a function" type checks), so timing
  only added flakiness. Correctness on 1000 sublists proves end-to-end run.
- **h3** — relative to the `aj` primitive (within 10×); tbridge is `aj` + two
  vector updates. (observed ~0.8×)
- **h4** — relative to the equivalent native qSQL `select` (within 5×); qbuild
  adds only cheap parse-tree construction. (observed ~0.7×)
- **h5** — both wall-clock asserts removed; "no stack overflow at depth 500" is
  structural — a naive-recursive solution crashes and never reaches the
  node-count asserts (501 / 32767) that are the real signal.

### 4. The "no iteration" anti-cheat (h6) was bypassable
It banned the *word* `each` by substring but missed q's each **adverb glyph** `'`
(`f'[x]` — the most direct bypass), and used a cryptic `" do[[]"` pattern.

**Fix:** h6 now also forbids a `'` that isn't forming each-prior (`':`), keeps the
keyword/`peach`/`do[`/`while` checks, and is commented. Verified: the vectorized
`group flip` solution passes; a correct-but-`'`-looping solution is now rejected.
(`h6-vector-partition/tests.q`)

### 5. Format failures were scored as wrong answers
Empty/unextractable responses fell through to the q interpreter and scored as
FAIL. The extractor also took the *first* fenced block (grabbing a throwaway
example before the real answer) and was coupled to a "no fences" prompt.

**Fix:** `extract_q_code`/`extract_python_code` now take the **last** language-
matching block (reasoning models emit prose then a final block), fall back
sensibly, and return "" when nothing is usable — which `run_challenge` scores as
`error`, not `fail`. (`runner/evaluator.py`, `runner/runner.py`)

### 6. Misc correctness
- `prompt_hash` returned the *last* retry's hash; now records the first-attempt
  prompt that defines the run.
- `generate_report` crashed (`None[:8]`) when `git_commit` was unavailable; now
  guarded, and the config table records mode/temperature/samples.

### 7. h7 spec was wider than the tests
`slideScan` is advertised as a general windowed scan, but the `f[prev;entering;
exiting]` contract only supports **invertible** aggregations and every test uses
windowed sum. README corrected so a sum-specific solution isn't mistaken for a
general one.

### Reproducibility: `verify_reference.py`
New harness runs author-held reference solutions (in gitignored `solutions/`)
through the hardened suites and asserts every section passes — the auditable
counterpart to the hand-recorded leaderboard. Current status on the author's
machine: **all 7 pure-q challenges (j1, h2–h7) → every section passes.**

## Documented (follow-up)

- **Untrusted model code runs on the host by default.** `_evaluate_via_subprocess`
  executes model-written q, and the PyKX path runs model-written Python via
  `pytest`, directly — Docker is only "optional". The temp-dir copy is for
  concurrency, not isolation. Treat sandboxing as required, not optional.
- **Single-sample rankings are within noise.** The author already notes ±1
  challenge variation per run; use `--samples N` and report variance before
  ranking models that sit within a challenge of each other.
- **`/:` and `\:` (each-right/left) are not source-banned in h6.** They are caught
  today only by the machine-independent perf gate. If you want strict "no
  element-wise iteration", extend the source check — at the cost of possibly
  rejecting some legitimate vectorized solutions.
