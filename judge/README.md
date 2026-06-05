# Remote q judge (executable code-generation benchmark)

The companion [output-prediction task](../kaggle-benchmark/) measures q *comprehension*
without running q. This judge measures actual q **code-generation ability**: the
model writes a solution, and a real licensed kdb+ runs it through the genuine
anti-cheat `tests.q` suites.

Kaggle Benchmarks runs each task in a sandbox with **no licensed q**, so grading
can't happen there. Instead the Kaggle task is a thin client that calls this
judge over HTTP:

```
Kaggle sandbox (no q)                       your host (licensed q)
  GET  /challenge/<name> ───────────────►   serves README + stub
  llm.prompt -> q code                       judge_server.py
  POST /grade {challenge, response} ─────►   evaluate_q_challenge -> real tests.q
  ◄──────────── {passed, score, sections} ◄──  (e.g. h2 -> 16/16)
  return float score (fraction of suites fully passed)
```

Proven end-to-end: gemini-3.1-pro scored 0.429 (j1, h2, h6 fully pass; h3 33/35;
h4/h5/h7 fail) — cross-validating the comprehension leaderboard, with the model's
exact q captured for inspection (h3 sorted `trades` and lost row order; h4 fumbled
the enlist-wrapping — the precise traps).

## Run it

```bash
# 1. Judge (reuses runner/evaluator.py + the 7 tests.q). Needs licensed q on PATH/~/q.
JUDGE_TOKEN=$(openssl rand -hex 16) JUDGE_PORT=8787 python3 judge/judge_server.py

# 2. Expose it (pick one — see "Exposure" below), get a public https URL.

# 3. Render the task with that URL/token and push:
JUDGE_URL=https://your-judge-host JUDGE_TOKEN=<same> ./kaggle-benchmark/render_and_push.sh

# 4. Run models:
kaggle b t run kdb-q-code-gen -m gemini-3.1-pro-preview -m gpt-5.5-2026-04-23 --wait
```

Endpoints: `GET /health`, `GET /challenge/<name>` (README + stub),
`POST /grade {challenge, response}` (Bearer `JUDGE_TOKEN`).

## Exposure (Kaggle egress is open — confirmed: HTTPS/DNS/raw-TCP all work)

| Option | Notes |
|---|---|
| **ngrok** | Rides :443, stable. `ngrok http 8787`. Best for multi-model runs. |
| **cloudflared named tunnel** | Most robust, but uses UDP/QUIC + TCP 7844 — blocked behind some VPNs (e.g. WARP remaps to `198.18.x.x`). Turn the VPN off if so. |
| **localtunnel** | `npx localtunnel --port 8787` (:443). Zero-setup but FLAKY — fine for one run, struggles under concurrent multi-model load; the task's retries help. |
| **reverse-SSH to a box you own** | `ssh -R` + a forwarder on a Kaggle-allowed port. No third party, but needs an open inbound port. |

## ⚠️ Security — this executes untrusted model code

`evaluate_q_challenge` runs model-generated q in a temp dir with a timeout, but
**not in a hard sandbox**, and:

- the **`kc.lic` cloud license requires network at startup** (deny-all-network
  kills q), and the license is a credential sharing the process with the
  executed code — a malicious solution could read/exfiltrate it;
- the offline `k4.lic` is host-bound (often invalid), so you can't trivially run
  q air-gapped.

**Do NOT run this on your primary machine with your primary license for a public
benchmark.** Production: a dedicated, disposable host with its own kdb+ license,
egress-allowlisted to the license daemon only, q under a real sandbox
(`sandbox-exec` / container / VM), per-request resource + time limits. The
prototype here trades that hardening for a one-session demo with frontier models
on a known coding task (low, but nonzero, risk).
