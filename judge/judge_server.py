#!/usr/bin/env python3
"""Remote q judge for the code-generation benchmark.

A thin HTTP service that runs untrusted, model-generated q through the real
`tests.q` anti-cheat suites (reusing runner/evaluator.py) and returns a verdict.
The Kaggle Benchmarks sandbox can't run licensed q, so the task POSTs generated
code here and we grade it with a real kdb+.

  GET  /health                      -> {ok, challenges}
  POST /grade {challenge, response} -> {passed, score, total, sections}
        Authorization: Bearer <JUDGE_TOKEN>

PROTOTYPE SECURITY NOTE: this runs untrusted q in a temp dir with a timeout, but
network is ON (the kc.lic cloud license needs it) and the license is readable by
the executed code. Acceptable for a controlled demo with frontier models on a
known coding task; NOT for a public benchmark. Production: dedicated isolated
host + its own disposable license.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from runner.evaluator import evaluate_q_challenge, extract_q_code  # noqa: E402

TOKEN = os.environ.get("JUDGE_TOKEN", "")
CHALLENGES = sorted(
    d.name for d in ROOT.iterdir()
    if d.is_dir() and (d / "tests.q").exists() and (d / "challenge.q").exists()
)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "challenges": CHALLENGES})
        elif self.path.startswith("/challenge/"):
            name = self.path[len("/challenge/"):]
            if name not in CHALLENGES:
                return self._send(404, {"error": f"unknown challenge {name!r}",
                                        "challenges": CHALLENGES})
            d = ROOT / name
            self._send(200, {
                "challenge": name,
                "readme": (d / "README.md").read_text(),
                "stub": (d / "challenge.q").read_text(),
            })
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/grade":
            return self._send(404, {"error": "not found"})
        if TOKEN and self.headers.get("authorization") != f"Bearer {TOKEN}":
            return self._send(401, {"error": "unauthorized"})
        try:
            n = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": f"bad request: {e}"})

        challenge = body.get("challenge")
        if challenge not in CHALLENGES:
            return self._send(400, {"error": f"unknown challenge {challenge!r}",
                                    "challenges": CHALLENGES})
        # Accept either a raw LLM response or already-extracted code.
        raw = body.get("response", body.get("code", ""))
        code = extract_q_code(raw)
        if not code.strip():
            return self._send(200, {"challenge": challenge, "passed": False,
                                    "status": "error", "score": 0, "total": 0,
                                    "sections": {}, "note": "no q code found"})
        try:
            res = evaluate_q_challenge(ROOT / challenge, code)
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": str(e)})
        out = {
            "challenge": challenge,
            "passed": res["status"] == "pass",
            "status": res["status"],
            "score": res["score"],
            "total": res["total"],
            "sections": res.get("sections", {}),
        }
        # On failure, return a bounded error excerpt so best-of-N clients can
        # feed the real q error back to the model. Truncated to avoid leaking
        # the full harness / large outputs.
        if res["status"] != "pass":
            errs = res.get("errors") or []
            excerpt = (errs[0] if errs else res.get("raw_output", "")) or ""
            out["error"] = excerpt[-800:]
        self._send(200, out)

    def log_message(self, *args):  # silence default logging
        pass


if __name__ == "__main__":
    port = int(os.environ.get("JUDGE_PORT", "8787"))
    host = os.environ.get("JUDGE_HOST", "127.0.0.1")
    print(f"q judge on {host}:{port}  challenges={CHALLENGES}  "
          f"token={'set' if TOKEN else 'NONE (open!)'}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
