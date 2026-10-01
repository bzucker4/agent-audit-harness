#!/usr/bin/env bash
set -euo pipefail

OUTPUT_REPORT="${1:-reports/client_audit_report.md}"
RESULTS_JSON="pytest_results.json"

echo "=== [1/3] Running Agent Audit Test Suite ==="
pytest -v --tb=short || true

if [ ! -f "$RESULTS_JSON" ]; then
    echo "Error: $RESULTS_JSON was not generated."
    exit 1
fi

echo "=== [2/3] Generating Executive Audit Report ==="
python -m reports.generator --input="$RESULTS_JSON" --output="$OUTPUT_REPORT"

echo "=== [3/3] Audit Complete ==="
echo "Report generated at: $OUTPUT_REPORT"
