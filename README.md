# kdb+/q Challenges

Curated programming challenges for kdb+/q — for fun, not for hiring.

Inspired by [effectfully/haskell-challenges](https://github.com/effectfully/haskell-challenges).

## Philosophy

1. **Difficulty ranges from "genuinely tricky" to "hard."** There are no warm-ups.
2. **Solutions should be under ~20 lines of q.** High think-to-type ratio.
3. **Minimal corner cases.** The challenge is conceptual, not exhaustive edge handling.
4. **q-specific.** Each challenge exploits the vector paradigm, adverb system, type strictness, temporal primitives, or functional programming capabilities. Row-by-row solutions will fail performance tests.
5. **Clearly formulated.** The problem statement is unambiguous; the difficulty is in the solution, not the specification.

## Anti-Cheat

Tests include randomized property checks, constant-function detection, identity-function detection, type validation, and performance bounds. These are structural — baked into the test design, not a separate framework.

## Requirements

**Pure q challenges (j/h series):**
- [kdb+ personal edition](https://code.kx.com/q/learn/install/) (free)
- That's it. No build system, no dependencies.

**PyKX challenges (p series):**
- Python 3.8+
- [PyKX](https://github.com/KxSystems/pykx) (`pip install pykx`)
- A kdb+ license (personal edition works — see [PyKX setup](https://code.kx.com/pykx/getting-started/installing.html))

## Running a Challenge

```bash
cd j1-lazy-scan
q tests.q
```

Fill in `challenge.q` with your solution. Run `q tests.q`. All tests pass = challenge complete.

## Challenges

| ID | Name | Core Concept | Difficulty |
|----|------|-------------|------------|
| j1 | [lazy-scan](j1-lazy-scan/) | Short-circuit scan with early termination | Medium-Hard |
| h2 | [custom-adverb](h2-custom-adverb/) | Higher-order adverb composition | Hard |
| h3 | [temporal-bridge](h3-temporal-bridge/) | Constrained temporal join without aj | Hard |
| h4 | [functional-select](h4-functional-select/) | Programmatic query construction | Medium-Hard |
| h5 | [tree-unfold](h5-tree-unfold/) | Recursive tree in a columnar language | Hard |
| h6 | [vector-partition](h6-vector-partition/) | Stable multi-key partitioning without each | Medium-Hard |
| h7 | [adverb-algebra](h7-adverb-algebra/) | Incremental sliding-window scan | Hard |

### PyKX Challenges

These test LLM fluency with the Python↔q bridge — type conversion, embedded q expressions, and hybrid pipelines.

| ID | Name | Core Concept | Difficulty |
|----|------|-------------|------------|
| p1 | [pykx-roundtrip](p1-pykx-roundtrip/) | Lossless Python→q→Python type conversion | Medium-Hard |
| p2 | [pykx-streaming](p2-pykx-streaming/) | Real-time aggregation via PyKX | Hard |
| p3 | [pykx-hybrid](p3-pykx-hybrid/) | Python model + q time-series in one pipeline | Hard |

```bash
cd p1-pykx-roundtrip
python -m pytest tests.py -v
```

## LLM Benchmark Runner

Automatically evaluate LLMs against all challenges:

```bash
cd runner
pip install -r requirements.txt
python -m runner.runner --models claude-sonnet-4-6,gpt-4o --challenges all
python -m runner.runner --models claude-sonnet-4-6 --challenges all --include-pykx
```

Results are saved to `results/` as JSON and CSV.

## Guidelines

- Solutions are guaranteed to exist and pass all tests.
- Tests run in under 10 seconds on commodity hardware.
- If you find an ambiguity, open an issue.
- Share solutions as external links, not inline — preserve the challenge for others.

## License

MIT
