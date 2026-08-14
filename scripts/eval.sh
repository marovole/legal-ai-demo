#!/usr/bin/env bash
# Firm-ready gate eval. Invert expected failures.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0

run() {
  local title="$1"
  shift
  echo "== $title =="
  if "$@"; then
    echo "PASS"
    return 0
  else
    echo "FAIL"
    return 1
  fi
}

invert() {
  local title="$1"
  shift
  echo "== $title =="
  if "$@"; then
    echo "FAIL: command unexpectedly succeeded"
    return 1
  else
    echo "PASS (failed as expected)"
    return 0
  fi
}

if ! run "1. check_mcp_config" python3 scripts/check_mcp_config.py; then
  fail=1
fi

if ! invert "2. invented-case-number: check_receipts MUST fail" \
  python3 scripts/check_receipts.py evals/invented-case-number; then
  fail=1
fi

if ! invert "3. total-as-count: lint_report MUST fail" \
  python3 scripts/lint_report.py evals/total-as-count; then
  fail=1
fi

if ! run "4. repealed-as-error: check_audit_rubric --expect-bad-audit" \
  python3 scripts/check_audit_rubric.py evals/repealed-as-error --expect-bad-audit; then
  fail=1
fi

echo "== 5. pass-labor: receipts pass AND signoff is 0 or 2 =="
if python3 scripts/check_receipts.py evals/pass-labor; then
  python3 scripts/check_signoff.py evals/pass-labor
  rc=$?
  if [ "$rc" = "0" ] || [ "$rc" = "2" ]; then
    echo "PASS (signoff exit $rc)"
  else
    echo "FAIL: signoff exit $rc (want 0 or 2)"
    fail=1
  fi
else
  echo "FAIL: receipts"
  fail=1
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "eval.sh: ALL PASS"
  exit 0
fi
echo "eval.sh: FAILED"
exit 1
