# kdb-q-challenges: Project Report

**Author:** Henry Zhang ([@caezium](https://github.com/caezium))
**Repository:** [github.com/caezium/kdb-q-challenges](https://github.com/caezium/kdb-q-challenges)
**Date:** April 4, 2026
**Status:** v1.0 — 10 challenges, LLM runner, fully documented

---

## 1. What This Is

An anti-cheat benchmark for testing how well large language models write kdb+/q code. 10 challenges designed so that pattern-matching, hardcoding, and other common LLM cheating strategies are structurally impossible — the tests themselves are the anti-cheat.

Inspired by [effectfully/haskell-challenges](https://github.com/effectfully/haskell-challenges), a project that went viral when the author demonstrated that no frontier model — including GPT-5.3 Codex — could solve his Haskell puzzles without cheating. This project applies the same philosophy to kdb+/q.

## 2. Why kdb+/q

kdb+/q is the ideal target for this kind of benchmark:

- **Tiny training corpus.** q has orders of magnitude less public code than Python or JavaScript. LLMs can't memorize their way through it.
- **Paradigm mismatch.** q is vector-first, right-to-left, and uses adverbs instead of loops. Solutions that "look right" in a Python mental model produce wrong or slow q.
- **Type strictness.** q's implicit type promotion creates subtle bugs. `(0b;10)` silently promotes `0b` to long `0` — a trap I fell into myself while building this project.
- **Financial industry relevance.** kdb+ is the dominant platform for time-series analytics at banks and trading firms. Knowing whether an LLM can write correct q has real-world implications for these teams.

## 3. Architecture

### 3.1 Design Principles

| Principle | Implementation |
|-----------|---------------|
| Each challenge is standalone | No shared framework. Test harness is 6 lines copied into each `tests.q`. |
| Tests ARE the anti-cheat | No separate anti-cheat engine. Randomized inputs, property checks, and performance bounds are baked into test design. |
| No easy challenges | Difficulty ranges from "genuinely tricky" to "hard." If an LLM can solve it by pattern-matching, it's not a good challenge. |
| q-specific | Every challenge exploits something unique to q: adverbs, type system, temporal primitives, vector paradigm, or functional select semantics. |
| Minimal infrastructure | Pure q challenges need only `q tests.q`. No Docker, no CI, no build system. |

### 3.2 Repository Structure

```
kdb-q-challenges/           40 files, 3,525 lines
├── 7 pure q challenges     (j1, h2–h7)    — run with: q tests.q
├── 3 PyKX challenges       (p1–p3)        — run with: pytest tests.py
├── LLM benchmark runner    (runner/)      — 669 lines of Python
├── README.md               (~300 lines)   — full setup/usage documentation
└── REPORT.md               (this file)
```

### 3.3 Anti-Cheat Techniques

| Technique | Catches | Used In |
|-----------|---------|---------|
| **Anti-constant detection** | Hardcoded return values — run fn with 3+ different inputs, assert distinct outputs | All challenges |
| **Anti-identity detection** | `{x}` passthrough — assert result differs from input | All challenges |
| **Type checking** | Type coercion cheats — assert exact q types (`7h`, `9h`, `98h`) | All challenges |
| **Randomized property tests** | Plausible-looking but incorrect implementations — 50–100 random seeds verify mathematical invariants | All challenges |
| **Performance bounds** | O(n) brute force where O(k) is required — wall-clock timing via `.z.P` | j1, h5, h6, h7 |
| **Source code inspection** | Forbidden keywords — parse function string via `-3!` to detect `each`/`do`/`while` | h6 |
| **Invocation counting** | O(n*w) brute force — inject counter into callback function | h7 |
| **Equivalence to built-in** | Partially correct implementations — result must match `msum`, `aj`, `sums` | j1, h3, h7 |
| **pykx import verification** | Pure-Python solutions bypassing q — check `sys.modules` for `pykx` | p1, p2, p3 |

## 4. The 10 Challenges

### Pure q (j/h series)

| ID | Name | Core Insight Required | Lines of Tests |
|----|------|----------------------|----------------|
| **j1** | lazy-scan | q's `\` (scan) processes every element. Must use convergence-over with state encoding to short-circuit. Boolean-to-long promotion in mixed lists is a trap. | 152 |
| **h2** | custom-adverb | Must return a *callable function*, not a value. Requires understanding projections and higher-order function composition in q. | 123 |
| **h3** | temporal-bridge | `aj` has no maxlag parameter. Must post-process the join result to null out stale quotes. Temporal arithmetic and null propagation are the hard parts. | 186 |
| **h4** | functional-select | Must build a parse tree (`?[t;c;b;a]`), not run a query. The `enlist` semantics for single where clauses trip up every LLM. | 154 |
| **h5** | tree-unfold | Trees are unnatural in q. Naive recursion hits the ~200-frame stack limit. Must build BFS iteratively with state accumulation. | 172 |
| **h6** | vector-partition | No `each`/`do`/`while` — fully vectorized. Source code is inspected at runtime. Forces understanding of `group` and compound key indexing. | 166 |
| **h7** | adverb-algebra | Incremental sliding window: `f` must be called ~n times, not n*w. An injected counter catches brute-force solutions. | 162 |

### PyKX (p series)

| ID | Name | Core Insight Required | Lines of Tests |
|----|------|----------------------|----------------|
| **p1** | pykx-roundtrip | `float('nan')` survival, `bool` vs `int` distinction (PyKX returns `numpy.bool_`), timestamp microsecond precision, single-element lists staying as lists not atoms. | 208 |
| **p2** | pykx-streaming | Data must be stored and computed in q via PyKX — not pure Python math. Rolling VWAP, max, and sum per-sym with correct window semantics. | 202 |
| **p3** | pykx-hybrid | VWAP/volatility MUST be computed in q; model_fn MUST be called in Python. Forces a true bridge: neither side can do everything alone. Volume-weighted average vs simple mean is the anti-cheat. | 233 |

## 5. LLM Benchmark Runner

A Python CLI that automates the full evaluation loop:

```
README → prompt → LLM API → extract code → write to stub → run tests → restore stub → collect results
```

**Supported models:** Claude Opus/Sonnet/Haiku 4.x, GPT-4o, GPT-4.1, GPT-4.1-mini, o3, o4-mini.

**Evaluation modes:**
1. **PyKX in-process** (preferred) — tests run via `kx.q()`, no subprocess overhead
2. **Subprocess fallback** — runs `q tests.q` when PyKX unavailable

**Output:** JSON + CSV results files, plus a stdout leaderboard with per-model pass rates and per-challenge breakdown.

## 6. Build Process

14 commits over a single session:

| # | Commit | What |
|---|--------|------|
| 1 | `a0a74df` | Project skeleton: README, LICENSE, .gitignore |
| 2 | `2b79c62` | j1-lazy-scan — establishes the test harness pattern |
| 3–8 | `92a716c`–`defcf65` | h2 through h7 — one commit per challenge |
| 9–11 | `03b5ba7`–`9f915e8` | p1 through p3 — PyKX challenges |
| 12 | `0e31897` | LLM benchmark runner (669 lines) |
| 13 | `80fa68e` | README rewrite — comprehensive documentation |
| 14 | `560a0f5` | Test bug fixes and reference solutions |

Design was planned upfront by studying the effectfully/haskell-challenges repo structure, then adapted for q's ecosystem (no build system needed, inline test harness, `'nyi` stubs instead of Haskell's `undefined`).

## 7. Lessons Learned Building This

### 7.1 q's Type Promotion Is the Real Anti-Cheat

The most surprising finding: q's type system is itself an anti-cheat mechanism. When `f` returns `(0b; 10)`, q promotes the boolean to a long because mixed lists get unified. This means `r 0` extracts `0` (long), not `0b` (boolean), and convergence conditions that check for `0b` never trigger. I spent 4 attempts debugging this in j1-lazy-scan before understanding the promotion rule.

If Claude (the model writing this report) struggles with q type promotion, other LLMs will too. This validates the benchmark design.

### 7.2 effectfully's Key Insight: Simplicity Is the Moat

effectfully's repo has zero framework code. No CI, no Docker, no leaderboard. The challenges are the product. Our initial design was overcomplicated — a full harness framework, Python runner, Docker containers, weekly GitHub Actions. Studying the actual repo structure led us to strip all of that from the MVP.

### 7.3 PyKX Bridge Challenges Are a Different Kind of Hard

Pure q challenges test language understanding. PyKX challenges test *integration* understanding — how types convert across the Python↔q boundary, when to use which language, and how to compose them in a pipeline. These are the challenges most relevant to real-world PyKX adoption.

## 8. What's Next

| Priority | Item | Effort |
|----------|------|--------|
| **High** | Run the benchmark against Claude Sonnet/Opus, GPT-4o, o3 and publish results | 1 day |
| **High** | Validate all reference solutions pass 100% of tests under kdb+ personal edition | 1 day |
| **Medium** | Add 3–5 more challenges targeting: nested dictionaries, IPC serialization, memory-mapped tables | 1 week |
| **Medium** | Community launch: post to KX Slack, Hacker News, X | 1 day |
| **Low** | GitHub Pages leaderboard with historical tracking | 2 days |
| **Low** | Integration with KDB-X MCP server (KX's official AI interface) | TBD |

## 9. How to Use

```bash
# Clone
git clone https://github.com/caezium/kdb-q-challenges.git
cd kdb-q-challenges

# Solve a challenge (human)
cd j1-lazy-scan
vim challenge.q
q tests.q

# Benchmark LLMs (automated)
pip install -r runner/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python -m runner.runner --models claude-sonnet-4-6,gpt-4o --challenges all
```

Full setup instructions in [README.md](README.md).

---

*Built with Claude Opus 4 in a single session. 40 files, 3,525 lines, 14 commits.*
