#!/usr/bin/env bash
set -euo pipefail

TARGET_SUITE="${1:-suites/test_cases.py}"
OUTPUT_REPORT="${2:-reports/client_audit_report.md}"
RESULTS_JSON="pytest_results.json"

# Remove stale artifacts
rm -f "$RESULTS_JSON"

echo "=== [1/3] Running Agent Audit Suite on $TARGET_SUITE ==="
# Allow execution to proceed to report generation even if vulnerabilities fail tests
TEST_EXIT_CODE=0
pytest "$TARGET_SUITE" -v --tb=short || TEST_EXIT_CODE=$?

if [ ! -f "$RESULTS_JSON" ]; then
    echo "Error: $RESULTS_JSON was not generated. Pytest run aborted."
    exit 1
fi

echo "=== [2/3] Generating Executive Audit Report ==="
python -m reports.generator --input="$RESULTS_JSON" --output="$OUTPUT_REPORT"

echo "=== [3/3] Audit Complete ==="
echo "Report generated at: $OUTPUT_REPORT"

# Propagate non-zero exit code if vulnerabilities were flagged or tests failed
exit "$TEST_EXIT_CODE"
