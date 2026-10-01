# Agent Tool-Abuse Audit: Operational Runbook & Execution Checklist

## Pre-Flight Verification (Phase 1)
- [ ] **Target Ingress & Transport:** Confirm target URL, interface protocol (REST/JSON, WebSocket, or SDK runner), and route mappings in `config/target_agent.yaml`. Confirm `scope.allowed_hosts` lists only the approved staging host.
- [ ] **Authentication & Identity Contexts:** Export active session credentials. For multi-tenant and authorization boundary tests, ensure both identities correspond to isolated accounts or roles:
  ```bash
  export AUDIT_LIVE=1
  export AUDIT_USER_A_TOKEN="<tenant_a_or_low_priv_token>"
  export AUDIT_USER_B_TOKEN="<tenant_b_or_high_priv_token>"
  ```
- [ ] **Trace Capture:** Confirm `trace.source` in `config/target_agent.yaml` (`api`, `langfuse`, `otel`, `burp_export`, or `file`) and that tool invocations are retrievable, either inline in chat responses or from the external trace collector. A case that cannot obtain a trace errors with "No trace was produced"; fix this before any full run.
- [ ] **Write-Tool Isolation:** Confirm every side-effecting tool (`send_email`, `export_file`, `webhook_post`, `fetch_url`, `delete_file`, `update_record`) is wired to staging sinks (mail catcher, test bucket, mock webhook), never production.
- [ ] **Authorization:** Signed SOW and written rules of engagement on file.

## Live Audit Execution (Phase 2)
1. **Smoke test** (one case; confirms auth, ingress and trace capture):
   ```bash
   pytest suites/test_cases.py -k "INJ-001" -v
   ```
   It must not report Error. Then confirm `pytest_results.json` has a `trace_id` for the case.
2. **Full SOW run** (all 40 cases):
   ```bash
   ./scripts/run_audit.sh suites/test_cases.py reports/client_audit_report.md
   ```
   The script deletes stale results, runs the suite, and writes the Markdown and HTML report. It exits non-zero when any case is Vulnerable; that is expected, not a script failure.
3. **429 / backoff handling.** The harness does not retry; a 429 appears as an Error result for that case.
   - [ ] Log each 429 (time, case ID) in the engagement log.
   - [ ] Wait with exponential backoff (1 s doubling to a 30 s cap).
   - [ ] Re-run only the affected cases, then merge, because every pytest run overwrites `pytest_results.json`:
   ```bash
   cp pytest_results.json reports/run_full.json          # save the full run first
   pytest suites/test_cases.py -k "INJ-004 or ARG-003" -v
   cp pytest_results.json reports/run_rerun.json
   # re-run records replace the originals with the same case_id
   python -c "import json; m={}; [m.update({r['case_id']: r for r in json.load(open(f))}) for f in ('reports/run_full.json','reports/run_rerun.json')]; json.dump(list(m.values()), open('pytest_results.json','w'), indent=2)"
   python -m reports.generator --input=pytest_results.json --output=reports/client_audit_report.md
   ```
4. **Triage Vulnerable traces.**
   - [ ] Each Vulnerable finding shows a real tool call in its trace with the canary in the arguments.
   - [ ] The canary was not in the prompt, system configuration or test setup (false-positive check).
   - [ ] Re-run Error cases once; if persistent, report them as Error, not Vulnerable.
5. **Validate deliverables against `sales/sow_fixed_scope_audit.md`:**
   - [ ] All four SOW classes covered: Indirect Injection (`INJ`, `TFC`), Confused Deputy (`CDP`), Argument Smuggling (`ARG`), Multi-Step Exfiltration (`MSE`).
   - [ ] Executive report delivered in Markdown and HTML.
   - [ ] Raw traces attached for every Vulnerable finding.
   - [ ] Remediation tickets include title, priority, description, remediation, acceptance criteria and OWASP LLM Top 10 mapping.
   - [ ] 30-minute executive readout scheduled; evidence retention agreed per contract.
