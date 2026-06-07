#!/usr/bin/env bash
# run-q-sandboxed.sh — run q under sandbox-q.sb with resource + time bounds.
# DRAFT wrapper for hardening the judge's untrusted-code execution.
#
# Usage:
#   QHOME=~/q ./run-q-sandboxed.sh <tests.q> <challenge_temp_dir> [timeout_s]
#
# Wires together: macOS sandbox-exec (filesystem + no-shell-out) + ulimit
# (cpu / file-size / memory bounds) + a hard wall-clock timeout. The challenge
# temp dir is the only writable path. See sandbox-q.sb for the threat model and
# the documented network limitation (license daemon egress can't be pinned).
set -euo pipefail

tests_q="${1:?usage: run-q-sandboxed.sh <tests.q> <temp_dir> [timeout_s]}"
tmpdir="${2:?need challenge temp dir}"
timeout_s="${3:-120}"
: "${QHOME:?set QHOME (e.g. ~/q)}"

qbin="$QHOME/m64/q"
[ -x "$qbin" ] || { echo "no q binary at $qbin"; exit 2; }

here="$(cd "$(dirname "$0")" && pwd)"
profile="$(mktemp -t sandbox-q).sb"
trap 'rm -f "$profile"' EXIT
sed -e "s#@TMPDIR@#${tmpdir}#g" -e "s#@QHOME@#${QHOME}#g" \
    "$here/sandbox-q.sb" > "$profile"

# Resource bounds (subshell so they don't leak to the caller):
#   -t CPU seconds, -f max file size (blocks), -v address space (KB; best-effort)
( ulimit -t "$timeout_s" -f 1048576 2>/dev/null || true
  cd "$tmpdir"
  # `timeout` from coreutils if present, else fall back to plain exec.
  if command -v gtimeout >/dev/null 2>&1; then TO=gtimeout
  elif command -v timeout  >/dev/null 2>&1; then TO=timeout
  else TO=""; fi
  QHOME="$QHOME" exec ${TO:+$TO "$timeout_s"} \
    /usr/bin/sandbox-exec -f "$profile" "$qbin" "$(basename "$tests_q")" )
