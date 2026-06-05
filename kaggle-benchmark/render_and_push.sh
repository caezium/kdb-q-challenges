#!/usr/bin/env bash
# Render the code-gen task template with the live judge URL/token and push it.
# The values are baked into the task source because the task executes in Kaggle's
# sandbox, which has no access to your local environment.
#
# Usage:
#   JUDGE_URL=https://your-judge-host JUDGE_TOKEN=secret ./render_and_push.sh
#
# Requires: kaggle CLI authed (KGAT token), the judge running + reachable at JUDGE_URL.
set -euo pipefail

: "${JUDGE_URL:?set JUDGE_URL (e.g. your ngrok/cloudflared/loca.lt https URL)}"
: "${JUDGE_TOKEN:?set JUDGE_TOKEN (matches the judge's JUDGE_TOKEN env)}"

here="$(cd "$(dirname "$0")" && pwd)"
tmpl="$here/kdb_q_codegen.py"
rendered="$here/kdb_q_codegen.rendered.py"   # gitignored

sed -e "s#__JUDGE_URL__#${JUDGE_URL}#g" -e "s#__JUDGE_TOKEN__#${JUDGE_TOKEN}#g" "$tmpl" > "$rendered"

echo "Sanity: judge health at $JUDGE_URL ..."
curl -fsS --max-time 15 -H "bypass-tunnel-reminder: 1" "$JUDGE_URL/health" >/dev/null \
  && echo "  judge OK" || { echo "  judge NOT reachable — aborting"; exit 1; }

echo "Pushing kdb-q-code-gen ..."
kaggle benchmarks tasks push kdb-q-code-gen -f "$rendered" --wait
echo "Done. Run with: kaggle b t run kdb-q-code-gen -m <model> [...] --wait"
