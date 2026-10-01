# Statement of Work: Fixed-Scope Agent Tool-Abuse Audit

**Client:** [CLIENT NAME]  
**Auditor:** [SECURITY CONSULTANCY NAME]  
**SOW Number:** [SOW NUMBER]  
**Date:** [DATE]  

## 1. Engagement Overview

This fixed-fee, fixed-scope engagement audits **one deployed or staging tool-using agent** for tool-abuse risk. The engagement is designed to produce ticket-ready findings, raw tool-invocation trace evidence, and an executive-facing report suitable for security leadership.

The audit focuses on the agent’s security boundary: how it selects, calls, and sequences tools based on user, document, webhook, or tool-response input. The approach is canary-only, controlled, and limited to the agreed staging environment.

## 2. Pricing and Complexity Tiers

The fixed fee is selected from the tier table below based on tool count, role levels, and multi-step/agent-complexity risk.

| Tier | Scope Characteristics | Fixed Fee |
|---|---|---|
| Tier 1 | Up to 5 tools, 1 role level, standard chat/document ingress | $8,500 |
| Tier 2 | 6–10 tools, up to 2 role levels, moderate tool sensitivity | $10,500 |
| Tier 3 | 11–15 tools, 2 role levels, multi-step chaining or sensitive tool risk | $14,500 |

The selected tier is confirmed during Day 1 Tool Mapping. Changes to tool count, role levels, ingress paths, or agent behavior after Day 1 may require change control and may adjust the fee.

## 3. In-Scope

- **Target:** 1 agent.
- **Ingress paths:** Staging document upload, chat, and webhook/tool-response ingress.
- **Tooling:** Up to 15 declared tools.
- **Role levels:** Up to 2 role levels, referenced as User A vs User B.
- **Attack classes (4):**
  1. **Indirect Prompt Injection (document and ingress vectors):** ingested files (PDF, Markdown, raw text chunks), plus upstream data sources and ingress channels (synthetic email bodies, calendar event descriptions, and downstream tool responses) crafted to force unauthorized tool invocation (Tool Force / Tool Result Poisoning).
  2. **Confused Deputy and Cross-Tenant Boundary Violations.**
  3. **Tool-Argument Injection and Smuggling.**
  4. **Multi-Step Exfiltration Chains.**
- **Trace extraction:** Raw tool-invocation traces collected as evidence for each finding.
- **Remediation tickets:** Ticket-ready findings with severity, priority, remediation guidance, acceptance criteria, and OWASP LLM Top 10 mapping.

## 4. Out-of-Scope

- Model training, fine-tuning, weights, or embedding systems.
- Infrastructure or network penetration testing.
- Code remediation or patch development.
- Production traffic load testing or denial-of-service testing.
- Auditing third-party vendors or model providers.

## 5. Timeline

| Day | Activity |
|---|---|
| Day 1 | Tool Mapping, authorization verification, environment access confirmation |
| Days 2–4 | Test Execution, Trace Triage, Manual Edge Chaining |
| Day 5 | Report Generation, Executive Readout, Deliverable Handover |
| Days 6–8 | Buffer only for rate limits, access delays, or client-deferred test windows |

## 6. Deliverables

- Executive report in Markdown and HTML format.
- Raw tool-invocation traces supporting all Vulnerable findings.
- Remediation ticket suite with OWASP LLM Top 10 mapping.
- 30-minute executive readout.

## 7. Client Responsibilities

The client will provide:

- Staging access to the target agent.
- Two test accounts per role level: User A and User B.
- Source IP allow-listing for auditor test traffic.
- Access to raw tool-invocation traces or trace API/trace files.
- A named technical contact available during the engagement.
- Written authorization and internal approval before testing begins.

## 8. Authorization and Rules of Engagement

Testing will begin only after written authorization is received. The engagement will follow:

- Fixed scope limited to the agreed staging target.
- Canary-only payloads; no real data exfiltration or real PII movement.
- No production testing.
- Stop conditions if target instability, real data exposure, scope ambiguity, or authorization changes occur.

## 9. Assumptions and Change Control

This SOW assumes the agent APIs, tool schemas, and roles are stable during the test window. Any change to scope, tools, roles, endpoints, or environment is handled through written change control and may affect fee or timeline.

## 10. Payment Terms

- 50% due on signing.
- 50% due on delivery and acceptance.

## 11. Confidentiality

Both parties will treat engagement data, findings, and communications as confidential under the governing agreement.

## 12. Limitation Statement

This is a point-in-time assessment. Findings are based on the tested configuration and observed behavior and do not constitute a guarantee that the agent is free from all security vulnerabilities.

## 13. Acceptance

The client will review deliverables and provide written acceptance or exceptions within 5 business days of the readout.

## 14. Retainer Clause

After delivery, the client may subscribe to a recurring regression scan at **$2,500/month**. The retainer re-runs the established audit suite after model, prompt, or tool modifications and provides a short delta report.

**Trigger/notification process:** Client notifies [SECURITY CONSULTANCY NAME] within 5 business days of a model, prompt, or tool change. Auditor runs the regression within 5 business days of access confirmation.

**Cancellation:** Either party may cancel with 30 days written notice.

## 15. Template Note

This SOW is a template and should be reviewed by qualified counsel before use.

**Signatories**

[CLIENT NAME]  
By: ___________________________  
Title: ___________________________  
Date: ___________________________

[SECURITY CONSULTANCY NAME]  
By: ___________________________  
Title: ___________________________  
Date: ___________________________

