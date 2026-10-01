# Agent Tool-Abuse Audit: Operational Runbook & Execution Checklist

## Pre-Flight Verification (Phase 1)
- [ ] **Ingress & Target Surface:** Verify target interaction method (REST/JSON, WebSocket, or SDK runner) in `config/target_agent.yaml`.
- [ ] **Authentication:** Confirm session tokens/API keys load via environment variables (`TARGET_AGENT_API_KEY`, `TARGET_USER_TOKEN`).
- [ ] **Observability Pipeline:** Confirm whether tool invocations return synchronously in chat responses or require polling an external trace collector (e.g., Langfuse, OpenTelemetry).
- [ ] **Sink Isolation:** Ensure write tools (`send_email`, `export_file`) point to staging mock sinks (e.g., MailHog, test buckets) to prevent data pollution.

---

## Live Audit Execution (Phase 2)
1. **Smoke Test Baseline:**
   ```bash
   pytest -k "test_baseline_smoke" -v
