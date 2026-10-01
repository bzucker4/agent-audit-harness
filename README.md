# Agent Tool-Abuse Audit Suite

Automated security audit harness for tool-using LLM agents. It runs fixed-scope,
canary-based attack cases and renders an audit report.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set the environment variables used by `config/target_agent.yaml`:

```bash
export AUDIT_USER_A_TOKEN="user-a-token"
export AUDIT_USER_B_TOKEN="user-b-token"
```

## Running

```bash
pytest suites/
```

Or run only unit tests offline:

```bash
pytest tests/
```

Reports are written to `reports/output/audit_report.md` and
`reports/output/audit_report.html` by default. Override with:

```bash
pytest suites/ --audit-report-dir my-report-dir
```

## Scope and Authorization

This harness is intended **only** for systems you are explicitly authorized to
test. The configuration includes a fixed-scope guardrail using `allowed_hosts`.
Before every request, the harness verifies the target host is in that allow-list.
Do not expand the scope beyond the authorization granted for the engagement.
