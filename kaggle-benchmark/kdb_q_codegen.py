# %% [markdown]
# # kdb+/q code generation (executable, remote-judged)
#
# The model writes q solutions to the 7 kdb-q-challenges; a remote licensed-q
# **judge** (judge/judge_server.py) runs each through the real anti-cheat test
# suites and returns pass/fail. The Kaggle sandbox has no licensed q, so grading
# happens out-of-band over HTTP. Score = fraction of challenges whose FULL suite
# passes.
#
# This is a TEMPLATE. `JUDGE_URL` / `JUDGE_TOKEN` below are placeholders that get
# baked in at push time (the task runs in Kaggle's sandbox, which has no access
# to your local env). Render + push with:
#
#     JUDGE_URL=https://your-judge-host JUDGE_TOKEN=... ./kaggle-benchmark/render_and_push.sh
#
# (Never commit the rendered copy — see .gitignore.)

# %%
import json
import time
import urllib.request
import urllib.error
import kaggle_benchmarks as kbench

JUDGE_URL = "__JUDGE_URL__"      # rendered at push time
JUDGE_TOKEN = "__JUDGE_TOKEN__"  # rendered at push time
# Best-of-N: number of attempts per challenge. Each failed attempt feeds the
# real q error from the judge back into the next prompt (sequential retries).
# Baked at push time; defaults to 1 (zero-shot) when unrendered.
try:
    ATTEMPTS = max(1, int("__ATTEMPTS__"))
except ValueError:
    ATTEMPTS = 1
HEADERS = {"content-type": "application/json", "authorization": f"Bearer {JUDGE_TOKEN}",
           "bypass-tunnel-reminder": "1", "user-agent": "kbench-judge-client"}
CHALLENGES = ["j1-lazy-scan", "h2-custom-adverb", "h3-temporal-bridge",
              "h4-functional-select", "h5-tree-unfold", "h6-vector-partition",
              "h7-adverb-algebra"]
SYSTEM = (
    "You are an expert kdb+/q developer. You will be given a coding challenge "
    "and a function stub. Respond with ONLY valid q code that defines the "
    "function from the stub (replace the 'nyi placeholder). No explanation."
)


def _req(path, payload=None, tries=4):
    """Call the judge, retrying transient tunnel errors (502/503/EOF/timeout)."""
    data = json.dumps(payload).encode() if payload is not None else None
    method = "POST" if payload is not None else "GET"
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(JUDGE_URL + path, data=data, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (502, 503, 504, 522, 524):
                break
        except Exception as e:  # noqa: BLE001  (connection closed, timeout, etc.)
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"judge unreachable after {tries} tries: {last}")


# %%
@kbench.task(
    name="kdb-q-code-gen",
    description=("Write q solutions to 7 hard kdb+/q challenges; a remote "
                "licensed-q judge runs the real anti-cheat tests. Score = "
                "fraction of challenges whose full suite passes."),
)
def _solve_challenge(llm, ch):
    """Best-of-N: up to ATTEMPTS tries, feeding the judge's q error back each
    time. Returns (ok, detail). Stops early on the first full pass."""
    spec = _req("/challenge/" + ch)
    base = (f"{SYSTEM}\n\n## Challenge\n{spec['readme']}\n\n"
            f"## Stub to implement\n```q\n{spec['stub']}\n```\n\n"
            "Write the complete solution now.")
    last = ""
    for attempt in range(1, ATTEMPTS + 1):
        prompt = base if attempt == 1 else (
            f"{base}\n\n## Your previous attempt FAILED the test suite\n"
            f"```q\n{last}\n```\n\n## Judge feedback (attempt {attempt - 1})\n"
            f"{prev_fb}\n\nFix the bug and return the COMPLETE corrected q "
            "solution. ONLY q code, no explanation.")
        resp = llm.prompt(prompt)
        last = resp
        verdict = _req("/grade", {"challenge": ch, "response": resp})
        ok = bool(verdict.get("passed"))
        detail = (f"{verdict.get('score')}/{verdict.get('total')} tests, "
                  f"status={verdict.get('status')} (attempt {attempt}/{ATTEMPTS})")
        if ok:
            return True, detail
        prev_fb = (f"status={verdict.get('status')} "
                   f"score={verdict.get('score')}/{verdict.get('total')}\n"
                   f"sections={verdict.get('sections')}\n"
                   f"error: {verdict.get('error', '')}")
    return False, detail


def kdb_q_code_gen(llm) -> float:
    passed = 0
    for ch in CHALLENGES:
        try:
            ok, detail = _solve_challenge(llm, ch)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"JUDGE ERROR: {e}"
        passed += int(ok)
        kbench.assertions.assert_true(ok, expectation=f"{ch}: {'PASS' if ok else 'FAIL'} ({detail})")
    score = passed / len(CHALLENGES)
    print(f"code-gen (best-of-{ATTEMPTS}): {passed}/{len(CHALLENGES)} "
          f"challenges fully passed -> {score:.3f}")
    return round(score, 3)


# %%
kdb_q_code_gen.run(kbench.llm)
