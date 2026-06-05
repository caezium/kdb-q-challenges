# %% [markdown]
# # kdb+/q output prediction
#
# A Kaggle Benchmarks task that probes a model's grasp of q's *evaluation model*
# — the exact gap the kdb-q-challenges anti-cheat benchmark targets (right-to-left
# parsing, adverbs, temporal arithmetic, functional select, grouping, sliding
# windows). Each item is a self-contained q expression; the model must predict the
# exact value q produces.
#
# Why prediction (not code-gen)? The Kaggle sandbox has no licensed kdb+/q, so the
# executable anti-cheat tests can't run here. The gold answers below were computed
# locally with a licensed q (`-3!` flat-text form) and embedded, so grading needs
# no q at run time. This is the license-clean companion to the local benchmark.
#
# Items are derived from the 7 pure-q challenges (tags j1, h2..h7).

# %%
import re

import kaggle_benchmarks as kbench

# %%
# Items: (tag=source challenge, expr=q expression, gold=`-3!` of its value).
# Gold strings are produced by a licensed q — do not hand-edit.
ITEMS = [
    {'tag': 'j1', 'expr': '10-2-3', 'gold': '11'},
    {'tag': 'j1', 'expr': '2+3*4', 'gold': '14'},
    {'tag': 'j1', 'expr': '5>3>1', 'gold': '1b'},
    {'tag': 'j1', 'expr': '{x*2}/[3;1]', 'gold': '8'},
    {'tag': 'j1', 'expr': '(*/)1 2 3 4', 'gold': '24'},
    {'tag': 'h2', 'expr': '(+/)1 2 3 4 5', 'gold': '15'},
    {'tag': 'h2', 'expr': '(+\\)1 2 3 4', 'gold': '1 3 6 10'},
    {'tag': 'h2', 'expr': '(*\\)1 2 3 4', 'gold': '1 2 6 24'},
    {'tag': 'h2', 'expr': '(|/)3 1 4 1 5', 'gold': '5'},
    {'tag': 'h3', 'expr': '10:00:30 - 09:59:50', 'gold': '00:00:40'},
    {'tag': 'h3', 'expr': '2026.01.10 - 2026.01.01', 'gold': '9i'},
    {'tag': 'h3', 'expr': '09:30:00 + 90', 'gold': '09:31:30'},
    {'tag': 'h4', 'expr': 'count select from ([]a:1 2 3 4) where a>2', 'gold': '2'},
    {'tag': 'h4', 'expr': 'count select by sym from ([]sym:`a`b`a`b`a;v:til 5)', 'gold': '2'},
    {'tag': 'h4', 'expr': '?[([]a:1 2 3);();0b;()]~([]a:1 2 3)', 'gold': '1b'},
    {'tag': 'h5', 'expr': '{x,last[x]+1}/[3;enlist 0]', 'gold': '0 1 2 3'},
    {'tag': 'h5', 'expr': 'til 5', 'gold': '0 1 2 3 4'},
    {'tag': 'h5', 'expr': '(#:) each (1 2;3 4 5;enlist 6)', 'gold': '2 3 1'},
    {'tag': 'h6', 'expr': 'group `a`b`a`c`b', 'gold': '`a`b`c!(0 2;1 4;,3)'},
    {'tag': 'h6', 'expr': 'where 01011b', 'gold': '1 3 4'},
    {'tag': 'h6', 'expr': 'count each group `a`a`b`a', 'gold': '`a`b!3 1'},
    {'tag': 'h7', 'expr': '3 msum 1 2 3 4 5', 'gold': '1 3 6 9 12'},
    {'tag': 'h7', 'expr': '2 xprev 10 20 30 40 50', 'gold': '0N 0N 10 20 30'},
    {'tag': 'h7', 'expr': 'differ 1 1 2 2 3 1', 'gold': '101011b'},
    {'tag': 'h7', 'expr': 'deltas 1 3 6 10', 'gold': '1 2 3 4'},
]

PROMPT_TEMPLATE = """You are a kdb+/q expert. Evaluate the q expression EXACTLY as the \
q interpreter would (remember: q parses right-to-left, with no operator precedence).

Return ONLY the resulting value in q's flat text form — the form `-3!` prints — on a \
single line. No explanation, no quotes, no code fences.

Format examples:
  expression:  1+1                 answer:  2
  expression:  (+\\)1 2 3           answer:  1 3 6
  expression:  2 xprev 1 2 3 4     answer:  0N 0N 1 2
  expression:  `a`b!1 2            answer:  `a`b!1 2
  expression:  3<2                 answer:  0b

expression:  {expr}
answer:"""


def build_prompt(expr: str) -> str:
    return PROMPT_TEMPLATE.format(expr=expr)


def normalize(s: str) -> str:
    """Canonicalize a predicted/gold answer for comparison.

    Strips reasoning/labels/fences and collapses whitespace, but preserves q
    syntax (notably leading backticks of symbols and the spaces that separate
    vector items — so we never strip ALL whitespace).
    """
    if not s:
        return ""
    t = s.strip()
    fenced = re.findall(r"```[a-zA-Z+]*\n?(.*?)```", t, re.DOTALL)
    if fenced:
        t = fenced[-1].strip()
    lines = [ln for ln in t.splitlines() if ln.strip()]
    if lines:
        t = lines[-1]
    t = re.sub(r"^\s*(answer|result|output|=>)\s*[:=]?\s*", "", t.strip(), flags=re.I)
    if len(t) >= 2 and t[0] in "\"'" and t[-1] == t[0]:
        t = t[1:-1]
    return re.sub(r"\s+", " ", t).strip()


def grade(predict):
    """Run `predict(expr)->str` over every item; return (accuracy, by_tag, details).

    `predict` is injected so the grading logic is testable without a live model.
    """
    details = []
    tag_tot, tag_ok = {}, {}
    for it in ITEMS:
        tag = it["tag"]
        tag_tot[tag] = tag_tot.get(tag, 0) + 1
        try:
            got = predict(it["expr"])
        except Exception as e:  # a failed model call is a wrong answer, not a crash
            got = f"<error: {e}>"
        ok = normalize(got) == normalize(it["gold"])
        if ok:
            tag_ok[tag] = tag_ok.get(tag, 0) + 1
        details.append({"tag": tag, "expr": it["expr"], "gold": it["gold"],
                        "got": got, "ok": ok})
    n = len(ITEMS)
    accuracy = (sum(d["ok"] for d in details) / n) if n else 0.0
    by_tag = {t: round(tag_ok.get(t, 0) / tag_tot[t], 3) for t in sorted(tag_tot)}
    return accuracy, by_tag, details


# %%
@kbench.task(name="kdb-q-output-prediction")
def kdb_q_output_prediction(llm) -> dict:
    """Predict the exact output of q expressions; score = fraction correct."""
    accuracy, by_tag, details = grade(lambda e: llm.prompt(build_prompt(e)))
    for d in details:
        kbench.assertions.assert_true(
            d["ok"],
            expectation=f"{d['expr']}  =>  {d['gold']!r}   (got {d['got']!r})",
        )
    return {"accuracy": round(accuracy, 3), "by_challenge": by_tag, "n": len(ITEMS)}


# %%
kdb_q_output_prediction.run(kbench.llm)
