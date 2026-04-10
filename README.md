# kdb+/q Challenges

An anti-cheat benchmark for testing how well LLMs write kdb+/q code.

Inspired by [effectfully/haskell-challenges](https://github.com/effectfully/haskell-challenges) — hard, language-specific puzzles where the tests themselves are the anti-cheat.

**[→ See LEADERBOARD.md for frontier LLM benchmark results](LEADERBOARD.md)**

Top result: Gemini 3.1 Pro Preview at 6/7 (86%) best-of-3, followed by Claude Opus/Sonnet 4.6 tied at 4/7 (57%). h4-functional-select is unsolved by every model tested.

## Table of Contents

- [Philosophy](#philosophy)
- [Quick Start](#quick-start)
- [Setup](#setup)
  - [kdb+ (for q challenges)](#kdb-for-q-challenges)
  - [PyKX (for Python challenges)](#pykx-for-python-challenges)
- [Solving Challenges](#solving-challenges)
  - [Pure q (j/h series)](#pure-q-jh-series)
  - [PyKX (p series)](#pykx-p-series)
- [Challenge Reference](#challenge-reference)
- [LLM Benchmark Runner](#llm-benchmark-runner)
  - [Installation](#runner-installation)
  - [Configuration](#runner-configuration)
  - [Usage](#runner-usage)
  - [Output Format](#output-format)
  - [Supported Models](#supported-models)
- [Anti-Cheat Design](#anti-cheat-design)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Philosophy

1. **Difficulty: "genuinely tricky" to "hard."** There are no warm-ups.
2. **Solutions under ~20 lines of q.** High think-to-type ratio.
3. **Minimal corner cases.** The challenge is conceptual, not exhaustive edge handling.
4. **q-specific.** Each challenge exploits the vector paradigm, adverb system, type strictness, temporal primitives, or functional programming capabilities. Row-by-row solutions will fail performance tests.
5. **Clearly formulated.** The problem statement is unambiguous; the difficulty is in the solution, not the specification.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USER/kdb-q-challenges.git
cd kdb-q-challenges

# Pick a challenge, edit the stub, run the tests
cd j1-lazy-scan
vim challenge.q        # replace 'nyi with your solution
q tests.q              # all pass = done
```

---

## Setup

### kdb+ (for q challenges)

The 7 pure q challenges (j1, h2–h7) need only kdb+ personal edition. No build system, no package manager, no dependencies.

**1. Download kdb+ personal edition (free)**

Go to [code.kx.com/q/learn/install](https://code.kx.com/q/learn/install/) and follow the instructions for your OS.

**2. Install and configure**

macOS / Linux:
```bash
# Move the downloaded q directory to a permanent location
mv ~/Downloads/q /opt/q

# Add to your shell profile (~/.zshrc or ~/.bashrc)
export QHOME=/opt/q
export PATH="$PATH:$QHOME/m64"    # macOS Apple Silicon
# export PATH="$PATH:$QHOME/l64"  # Linux x86_64

# Reload
source ~/.zshrc
```

Windows:
```powershell
# Set environment variables
[Environment]::SetEnvironmentVariable("QHOME", "C:\q", "User")
$env:Path += ";C:\q\w64"
```

**3. Verify**

```bash
q -e "1+1"
# Should print: 2
```

If you see `'cores` or a license error, you may need to request a personal license at [kx.com](https://kx.com/kdb-insights-sdk-personal-edition-download/) and place the `kc.lic` file in `$QHOME`.

### PyKX (for Python challenges)

The 3 PyKX challenges (p1–p3) and the LLM runner need Python + PyKX.

**1. Get a kdb+ license**

PyKX requires a license file. The free personal edition works:
- Visit [kx.com/kdb-insights-sdk-personal-edition-download](https://kx.com/kdb-insights-sdk-personal-edition-download/)
- Fill in the form, download the license file (`kc.lic`)
- Save it somewhere permanent (e.g., `~/.kx/`)

**2. Set the license path**

```bash
# Add to your shell profile
export QLIC=~/.kx    # directory containing kc.lic
```

**3. Install PyKX**

```bash
pip install pykx
```

**4. Verify**

```bash
python -c "import pykx as kx; print(kx.q('1+1'))"
# Should print: 2
```

---

## Solving Challenges

### Pure q (j/h series)

Each challenge is a self-contained directory with three files:

| File | Purpose |
|------|---------|
| `README.md` | Problem statement, examples, constraints |
| `challenge.q` | Stub with `'nyi` — replace this with your solution |
| `tests.q` | Test suite — run this to check your solution |

**Workflow:**

```bash
cd j1-lazy-scan

# 1. Read the problem
cat README.md

# 2. Edit the stub
vim challenge.q
# Replace the 'nyi line with your implementation, e.g.:
#   scanz:{[f;init;data]
#     ... your code here ...
#   }

# 3. Run tests
q tests.q
```

**Output on success:**
```
--- basic correctness ---
  pass: running sum stops at 10
  pass: empty input
  ...
--- anti-cheat ---
  pass: not identity 1
  ...
--- property tests ---
  pass: len <= 1+n (seed 42)
  ...
--- performance ---
  big list early stop: 2ms, result length: 4
  pass: early stop is fast (<500ms)
  ...

=== Results ===
passed: 38
failed: 0
```

**Output on failure:**
```
  FAIL: running sum stops at 10 | expected: 0 1 3 6 10 got: 0 1 3 6
```

Exit code is 0 on all pass, 1 on any failure.

### PyKX (p series)

Same structure, but Python:

| File | Purpose |
|------|---------|
| `README.md` | Problem statement |
| `challenge.py` | Python stub with `raise NotImplementedError` |
| `tests.py` | pytest test suite |

**Workflow:**

```bash
cd p1-pykx-roundtrip

# 1. Read the problem
cat README.md

# 2. Edit the stub
vim challenge.py

# 3. Run tests
python -m pytest tests.py -v
```

---

## Challenge Reference

### Pure q Challenges

| ID | Name | What It Tests | Difficulty |
|----|------|--------------|------------|
| j1 | [lazy-scan](j1-lazy-scan/) | Short-circuit scan via convergence — q has no native early-exit scan | Medium-Hard |
| h2 | [custom-adverb](h2-custom-adverb/) | Higher-order iterator-wrapper composition — projections and adverb abstraction | Hard |
| h3 | [temporal-bridge](h3-temporal-bridge/) | As-of join with max staleness — aj has no native maxlag parameter | Hard |
| h4 | [functional-select](h4-functional-select/) | Build a `?[t;c;b;a]` parse tree — functional select enlist semantics | Medium-Hard |
| h5 | [tree-unfold](h5-tree-unfold/) | BFS tree as a table — recursion hits q's ~200-frame stack limit | Hard |
| h6 | [vector-partition](h6-vector-partition/) | Vectorized multi-key grouping — no `each`/`do`/`while` allowed | Medium-Hard |
| h7 | [adverb-algebra](h7-adverb-algebra/) | Incremental sliding-window scan — must be O(n) not O(n*w) | Hard |

### PyKX Challenges

| ID | Name | What It Tests | Difficulty |
|----|------|--------------|------------|
| p1 | [pykx-roundtrip](p1-pykx-roundtrip/) | Lossless Python->q->Python type conversion (NaN, bool, timestamps) | Medium-Hard |
| p2 | [pykx-streaming](p2-pykx-streaming/) | Real-time tick aggregation — data stored and computed in q via PyKX | Hard |
| p3 | [pykx-hybrid](p3-pykx-hybrid/) | Python model + q time-series math in one pipeline | Hard |

---

## LLM Benchmark Runner

Automatically evaluate how well LLMs solve the challenges. The runner prompts each model, extracts the code from its response, writes it into the challenge stub, runs the tests, and collects pass/fail results.

### Runner Installation

```bash
cd kdb-q-challenges

# Install Python dependencies
pip install -r runner/requirements.txt

# This installs: pykx, anthropic, openai, pandas
```

### Runner Configuration

**API keys** — set environment variables for the providers you want to test:

```bash
# Anthropic (Claude models)
export ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI (GPT, o-series models)
export OPENAI_API_KEY=sk-proj-...
```

The runner validates that the required key is set before calling any model. You only need keys for providers you actually use.

**kdb+ / PyKX** — the runner evaluates solutions in two ways:

1. **PyKX (preferred)** — if `pykx` is importable, tests run in-process via `kx.q()`. Faster, no subprocess overhead.
2. **Subprocess fallback** — if PyKX is unavailable, it runs `q tests.q` as a subprocess. Requires `q` on your `PATH`.

You need at least one of these working. For PyKX challenges (p series), PyKX is always required.

### Runner Usage

Run from the project root:

```bash
# Single model, all q challenges (zero-shot, 1 attempt)
python -m runner.runner --models claude-sonnet-4-6 --challenges all

# Compare multiple models with chain-of-thought prompting
python -m runner.runner --models claude-sonnet-4-6,gpt-4o,o3 --challenges all --strategy cot

# Multi-attempt with error feedback (agentic mode)
python -m runner.runner --models claude-sonnet-4-6 --challenges all --attempts 3

# Include PyKX challenges
python -m runner.runner --models claude-sonnet-4-6,gpt-4o --challenges all --include-pykx

# Few-shot prompting with 5 retries, compare against a previous run
python -m runner.runner --models gpt-4.1 --challenges all \
  --strategy few-shot --attempts 5 --compare ./results/results_20260403_120000.json

# Skip artifact saving for quick runs
python -m runner.runner --models claude-sonnet-4-6 --challenges j1-lazy-scan --no-artifacts
```

**CLI flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--models` | `claude-sonnet-4-6` | Comma-separated model keys (see table below) |
| `--challenges` | `all` | Comma-separated challenge names, or `all` for all q challenges |
| `--include-pykx` | off | Also run PyKX challenges (p series) |
| `--attempts` | `1` | Max attempts per challenge (1–5). On failure, error output is fed back to the model. |
| `--strategy` | `zero-shot` | Prompting strategy: `zero-shot`, `cot` (chain-of-thought), or `few-shot` |
| `--output` | `./results` | Directory for JSON/CSV/report output |
| `--no-artifacts` | off | Skip saving raw LLM responses and extracted code |
| `--compare` | none | Path to a previous results JSON for delta comparison in the report |

### Prompt Strategies

| Strategy | Behavior |
|----------|----------|
| `zero-shot` | "Pure code only" — the model gets the README + stub and must output just code |
| `cot` | Chain-of-thought — the model is asked to reason about q semantics step by step, then output code in a fenced block |
| `few-shot` | Includes a small solved example (not from the benchmark) to demonstrate expected format |

### Multi-Attempt Mode

When `--attempts N` is set (N > 1), the runner retries on failure:

1. **Attempt 1:** Standard prompt (README + stub)
2. **Attempt 2+:** The model sees its previous code and the test error output, and is asked to fix it

This simulates agentic coding workflows (Claude Code, Cursor, etc.) and measures "attempts to pass."

The runner tracks both **first-shot pass rate** and **best-of-N pass rate**, plus the standard **Pass@k** metric from the Codex/HumanEval paper.

### Output Format

Each run produces three files in the output directory:

**`results_YYYYMMDD_HHMMSS.json`** — full structured results with section-level scoring:
```json
{
  "generated_at": "2026-04-03T12:00:00+00:00",
  "run_config": {
    "strategy": "cot",
    "max_attempts": 3,
    "git_commit": "abc12345",
    "q_version": "4.1"
  },
  "models": [
    {
      "model": "claude-sonnet-4-6",
      "pass_rate": 0.714,
      "first_shot_pass_rate": 0.571,
      "pass@1": 0.571,
      "pass@3": 0.714,
      "avg_attempts": 1.8,
      "challenges": [
        {
          "id": "j1-lazy-scan",
          "status": "pass",
          "attempts_used": 2,
          "first_shot_pass": false,
          "sections": {
            "basic_correctness": {"passed": 10, "failed": 0},
            "anti-cheat": {"passed": 5, "failed": 0},
            "property_tests": {"passed": 20, "failed": 0},
            "performance": {"passed": 3, "failed": 0}
          },
          "prompt_hash": "a1b2c3d4"
        }
      ]
    }
  ]
}
```

**`results_YYYYMMDD_HHMMSS.csv`** — flat table with section columns:
```
model,challenge,status,attempts_used,first_shot_pass,sec_basic_correctness_passed,...
```

**`REPORT_YYYYMMDD_HHMMSS.md`** — human-readable markdown report with:
- Run configuration table
- Leaderboard with first-shot and best-of-N rates
- Pass@k table (when attempts > 1)
- Per-challenge status grid
- Section-level heatmap per model
- Delta comparison vs. previous run (if `--compare` used)

**Artifacts** (in `results/artifacts/<model>/<challenge>/`):
- `response.txt` — raw LLM response
- `code.q` — extracted q code
- `test_output.txt` — test suite output
- Suffixed `_attempt2`, `_attempt3` etc. for retries

### Supported Models

| Key | Provider | Model |
|-----|----------|-------|
| `claude-opus-4-6` | Anthropic | Claude Opus 4.6 |
| `claude-sonnet-4-6` | Anthropic | Claude Sonnet 4.6 |
| `claude-haiku-4-5` | Anthropic | Claude Haiku 4.5 |
| `gpt-4o` | OpenAI | GPT-4o |
| `gpt-4.1` | OpenAI | GPT-4.1 |
| `gpt-4.1-mini` | OpenAI | GPT-4.1 Mini |
| `o3` | OpenAI | o3 |
| `o4-mini` | OpenAI | o4-mini |

To add a new model, edit the `MODELS` dict in `runner/runner.py`.

---

## Anti-Cheat Design

Tests are the anti-cheat. Each challenge bakes detection into the test suite itself — no separate framework.

| Technique | How It Works | What It Catches |
|-----------|-------------|-----------------|
| **Anti-constant** | Run fn with 3+ structurally different inputs, assert distinct outputs | Hardcoded return values |
| **Anti-identity** | Assert result differs from input | `{x}` passthrough solutions |
| **Type checking** | Assert exact q types match (`7h`, `9h`, `98h`, etc.) | Type coercion cheats |
| **Property tests** | 50–100 random seeds verify mathematical invariants | Solutions that pass examples but fail in general |
| **Performance bounds** | Wall-clock timing via `.z.P` with ms precision | O(n) brute force where O(k) is required |
| **Source inspection** | Parse function string via `-3!` for forbidden keywords | `each`/`do`/`while` in h6 where vectorization is required |
| **Invocation counting** | Inject counter into callback function | O(n*w) brute force in h7 where O(n) is required |
| **Equivalence checks** | Result must match a known-correct q built-in (e.g., `msum`, `aj`) | Partially correct implementations |

The randomized property tests use `\S seed` / `system "S ",string seed` for deterministic randomness — same seed produces same test cases across runs.

---

## Project Structure

```
kdb-q-challenges/
├── README.md                   # This file
├── LICENSE                     # MIT
├── .gitignore
│
├── j1-lazy-scan/               # Pure q challenges
│   ├── README.md               #   Problem statement
│   ├── challenge.q             #   Stub ('nyi) — fill this in
│   └── tests.q                 #   Self-contained tests + anti-cheat
├── h2-custom-adverb/
│   └── ...
├── h3-temporal-bridge/
│   └── ...
├── h4-functional-select/
│   └── ...
├── h5-tree-unfold/
│   └── ...
├── h6-vector-partition/
│   └── ...
├── h7-adverb-algebra/
│   └── ...
│
├── p1-pykx-roundtrip/          # PyKX challenges
│   ├── README.md
│   ├── challenge.py            #   Python stub — fill this in
│   └── tests.py                #   pytest suite
├── p2-pykx-streaming/
│   └── ...
├── p3-pykx-hybrid/
│   └── ...
│
├── Dockerfile                   # Sandboxed execution (optional)
│
├── runner/                      # LLM benchmark automation
│   ├── requirements.txt         #   pykx, anthropic, openai, pandas
│   ├── runner.py                #   CLI entry point + retry loop
│   ├── evaluator.py             #   Test execution + section parsing
│   ├── prompt.py                #   Prompt strategies (zero-shot/cot/few-shot)
│   └── results.py               #   Pass@k, artifacts, markdown reports
│
└── results/                     # Benchmark output (gitignored)
    └── .gitkeep
```

**Naming convention:**
- `j1` — separate series (matching effectfully's j1-lazy-foldrM)
- `h2`–`h7` — hard series, no h1 (signals no beginner challenges)
- `p1`–`p3` — PyKX (Python↔q bridge) challenges

Each q challenge is fully standalone — no shared files, no imports between challenges. The test harness (~6 lines) is copied into each `tests.q`.

---

### Docker (Optional)

For sandboxed execution (recommended when running untrusted LLM-generated code):

```bash
# Place your kc.lic in the project root, then:
docker build -t kdb-q-challenges .

docker run --rm \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -v $(pwd)/results:/app/results \
  kdb-q-challenges \
  --models claude-sonnet-4-6 --challenges all --attempts 3
```

---

## How the Runner Works

```
                    ┌─────────────────────────────┐
                    │     runner.py (CLI)          │
                    │  --models  --challenges      │
                    └──────┬──────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼──────┐
    │ prompt.py  │   │ prompt.py  │   │  prompt.py   │
    │ Read README│   │ Read README│   │  Read README │
    │ Build msg  │   │ Build msg  │   │  Build msg   │
    └─────┬─────┘   └─────┬─────┘   └──────┬──────┘
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼──────┐
    │ Call LLM   │   │ Call LLM   │   │  Call LLM    │
    │ (Anthropic │   │ (OpenAI    │   │  (OpenAI     │
    │  or OpenAI)│   │  API)      │   │   API)       │
    └─────┬─────┘   └─────┬─────┘   └──────┬──────┘
          │                │                │
    ┌─────▼─────────────────▼────────────────▼──────┐
    │              evaluator.py                      │
    │  1. Extract code from LLM response             │
    │  2. Write code to challenge.q / challenge.py   │
    │  3. Run tests (PyKX in-process or subprocess)  │
    │  4. Parse pass/fail/score from output           │
    │  5. Restore original stub                       │
    └─────────────────────┬─────────────────────────┘
                          │
    ┌─────────────────────▼─────────────────────────┐
    │              results.py                        │
    │  Aggregate → JSON + CSV + stdout leaderboard   │
    └───────────────────────────────────────────────┘
```

---

## Contributing

This repo is author-controlled (matching effectfully's approach). If you find an ambiguity or bug in a test, open an issue. Share solutions as external links — not inline — to preserve the challenge for others.

## License

MIT
