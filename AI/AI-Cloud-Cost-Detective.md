# AI Cloud Cost Detective

## Important Accuracy Note

The supplied project contains a README, architecture and request-flow documents, and five staged implementation prompts. It does not contain the generated backend or frontend source code, automated test evidence, deployment files, screenshots, measured savings, or production results.

In an interview, I should therefore say **“I designed and prototyped this solution”** unless I have separately implemented and tested it. I should not claim that an AI recommendation saved a specific amount of money without billing data, utilization metrics, approval records, and measured before-and-after results.

---

## One-Line Project Explanation

I designed an AI-assisted FinOps application that inventories resources in an Azure Resource Group, detects possible waste and configuration problems, explains the findings in simple language, and presents reviewable optimization commands while keeping a history of every analysis.

---

## 30-Second Interview Answer

> I designed an AI Cloud Cost Detective using React, FastAPI, Azure CLI, OpenAI, WebSockets and Azure Database for PostgreSQL. An authenticated user selects an Azure Resource Group. The FastAPI backend executes controlled, read-only Azure CLI commands and converts the resource inventory into structured JSON. A rule-based validation layer identifies obvious facts, and the AI correlates those facts into possible cost issues such as idle resources, oversized SKUs, missing lifecycle controls or inappropriate pricing tiers. The UI receives live progress, then displays evidence, severity, estimated savings assumptions and suggested Azure CLI fixes. Results are saved for audit and comparison. The important safety decision is that AI only recommends changes; a human reviews the evidence and command before anything is modified.

---

## Two-Minute Interview Explanation

Cloud bills are difficult to investigate because resource inventory, billing data, utilization, ownership tags and configuration are normally checked in different places. Engineers may also know that cost increased without knowing which resource caused it or what action is safe.

I divided the solution into five layers:

1. React provides login, Resource Group selection, progress, reports and history.
2. FastAPI authenticates requests and orchestrates the investigation.
3. Azure CLI gathers read-only resource information from the selected scope.
4. A deterministic layer validates and enriches the facts, and the OpenAI layer converts the evidence into a structured explanation and recommendations.
5. Azure PostgreSQL stores users and analysis history, while WebSockets send progress to the browser.

The end-to-end flow is:

```text
User logs in
    -> selects an Azure Resource Group
    -> backend validates user and scope
    -> Azure inventory and supporting cost/metric evidence are collected
    -> sensitive fields are removed and data is normalized
    -> deterministic rules calculate facts
    -> AI explains and prioritizes possible savings
    -> output schema and commands are validated
    -> report is stored and displayed for human review
```

The goal is not to let an LLM control Azure. It is to shorten the investigation, show why each item was flagged, and give a FinOps or DevOps engineer a safe starting point.

---

## Problem, Goal and Outcome

### Problem

- Unused resources can remain after projects or tests finish.
- A resource may use a larger or more expensive SKU than its workload needs.
- Missing tags make ownership and cost allocation difficult.
- Long log retention and missing storage lifecycle policies increase cost.
- A raw bill shows expenditure but does not always explain the operational cause.
- Manual investigation is repetitive and knowledge varies between engineers.

### Goal

Create one application that collects evidence, identifies possible waste, explains the reasoning, suggests a safe next action and retains an audit history.

### Intended outcome

The useful outcome is a prioritized report such as:

```text
Resource: dev-vm-03
Finding: Possible oversized development VM
Severity: Medium
Evidence: Low CPU during the selected 14-day window; non-production tag
Recommendation: Validate memory and business schedule, then consider downsizing
Estimated saving: Range based on current and candidate SKU prices
Action: Review-only command or Portal steps
Confidence: Medium, because memory evidence is incomplete
```

This is more convincing than saying “AI found an expensive VM,” because it includes evidence, assumptions, confidence and a verification step.

---

## High-Level Architecture

```text
┌─────────────────────────────────────────────┐
│ React + TypeScript                          │
│ Auth | Resource Group | Progress | Reports  │
└─────────────────────┬───────────────────────┘
                      │ HTTPS / WebSocket
                      ▼
┌─────────────────────────────────────────────┐
│ FastAPI                                    │
│ JWT | validation | orchestration | policy  │
└──────────────┬──────────────┬───────────────┘
               │              │
               ▼              ▼
┌────────────────────────┐  ┌────────────────────────┐
│ Azure evidence         │  │ Analysis pipeline      │
│ CLI/resource inventory │  │ rules -> AI -> schema  │
│ billing/metrics (next) │  │ validation             │
└──────────────┬─────────┘  └────────────┬───────────┘
               │                         │
               └────────────┬────────────┘
                            ▼
                  ┌────────────────────┐
                  │ Azure PostgreSQL   │
                  │ users + analyses   │
                  └────────────────────┘
```

The original design uses `az resource list` for inventory. For a production-grade cost detector, I would add Azure Cost Management data, Azure Monitor metrics, Azure Advisor recommendations and current retail/rate-card data. Inventory alone cannot prove that a resource is idle or calculate reliable savings.

---

## Technology Stack and Purpose

| Area | Technology | Why it is used |
| --- | --- | --- |
| Frontend | React, Vite, TypeScript, Tailwind CSS | Fast, typed dashboard with reusable report components |
| Backend | Python, FastAPI, Uvicorn | Validation, async APIs and orchestration |
| Authentication | bcrypt, PyJWT | Password hashing and signed access tokens |
| Azure collection | Azure CLI through Python `subprocess` | Simple prototype access to authenticated Azure inventory |
| AI analysis | OpenAI API | Correlate evidence and explain findings in plain language |
| Database | Azure Database for PostgreSQL | Users, JSON reports, status and analysis history |
| Live progress | FastAPI WebSocket | Show long-running analysis stages without browser polling |
| Configuration | Environment variables | Keep database URL, JWT secret and AI key outside source code |

For production I would normally prefer Azure SDK clients with a managed identity over shelling out to Azure CLI. SDKs provide typed responses, clearer retry behavior, cancellation and safer authentication without relying on a developer's local CLI session.

---

## How We Implemented It in Five Stages

### Stage 1: FastAPI and Azure inventory

The first stage provides:

- `GET /api/resource-groups`
- `POST /api/analyze`
- an Azure scanner module
- structured handling for missing CLI, expired login and invalid Resource Group
- development CORS for `http://localhost:5173`

Conceptual scanner:

```python
import json
import subprocess

def run_az(arguments: list[str]) -> list[dict]:
    command = ["az", *arguments, "--output", "json", "--only-show-errors"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Azure inventory command failed")
    return json.loads(result.stdout)

def list_resources(resource_group: str) -> list[dict]:
    return run_az(["resource", "list", "--resource-group", resource_group])
```

The Resource Group is passed as a separate argument, not concatenated into a shell string. I would also validate it against the Resource Groups available to the authenticated identity, set a timeout, limit output size, avoid `shell=True`, log a correlation ID, and return a sanitized error rather than CLI credentials or raw stderr.

The inventory is normalized so the AI does not need to understand many different Azure response shapes:

```json
{
  "id": "/subscriptions/.../resourceGroups/dev-rg/providers/...",
  "name": "dev-vm-03",
  "type": "Microsoft.Compute/virtualMachines",
  "location": "eastus",
  "sku": "Standard_D4s_v5",
  "tags": {"environment": "dev", "owner": "platform"}
}
```

One limitation is that a generic resource-list response may not contain all resource-specific configuration or utilization. The scanner needs provider-specific enrichment for VMs, disks, databases, App Services, storage and monitoring settings.

### Stage 2: AI cost analysis

The analyzer receives normalized evidence, not Azure credentials. It asks for a strict result containing:

- summary
- affected resource
- issue type
- severity
- evidence and assumptions
- estimated saving or an explicit “insufficient data” value
- recommendation and verification steps
- suggested command
- confidence

Example response model:

```python
from typing import Literal
from pydantic import BaseModel

class Finding(BaseModel):
    resource_id: str
    category: Literal["over_provisioned", "unused", "misconfigured", "governance"]
    severity: Literal["high", "medium", "low"]
    evidence: list[str]
    recommendation: str
    estimated_savings: str | None
    confidence: float
    command: str | None

class AnalysisReport(BaseModel):
    summary: str
    findings: list[Finding]
```

The response is parsed and validated with Pydantic. If it fails validation, the service retries once with the schema error or returns a controlled failure. Invalid commands are never presented as approved actions.

I would not let the model invent prices. The application should calculate cost and saving ranges deterministically from billing and pricing evidence. AI should explain the result and prioritize it.

### Stage 3: PostgreSQL and live progress

The design stores:

```text
users
  id, email, password_hash, created_at

analyses
  id, user_id, resource_group, resources_scanned,
  issues_found, estimated_savings, analysis_result JSONB,
  status, created_at
```

`GET /api/history` returns only the logged-in user's records. Database queries must be parameterized and migrations should be used instead of silently creating production tables at startup.

Progress messages are sent at major stages:

```text
Scanning resources in dev-rg...
Collecting supporting evidence...
Analyzing cost opportunities...
Validating recommendations...
Storing results...
Analysis complete
```

In a robust design, `POST /api/analyze` first creates an analysis record and immediately returns `202 Accepted` with an `analysis_id`. A background worker performs the job while the browser subscribes to `/ws/progress/{analysis_id}`. This avoids the race in which analysis finishes before the frontend learns which WebSocket to open.

WebSocket access must also be authenticated, checked against ownership of the analysis, rate-limited, and closed cleanly. For multi-instance deployment, I would use a job queue and Redis or a managed message service rather than an in-memory connection map.

### Stage 4: React dashboard and authentication

The frontend contains:

- Login and signup pages
- Resource Group selection and Run Analysis button
- Progress tracker
- Analysis report
- Previous-analysis history

Passwords are hashed with bcrypt and never stored in plain text. JWTs include a user identifier, expiry, issuer and audience. The backend validates the token on every protected API.

The initial prompt stores JWTs in `localStorage`. That is easy for a prototype but exposes the token if an XSS vulnerability occurs. For production I would prefer short-lived access tokens, refresh-token rotation, and `HttpOnly`, `Secure`, `SameSite` cookies where the architecture permits. I would also enforce TLS, strong password policy, login throttling and secret rotation.

### Stage 5: End-to-end integration

The final stage connects every component:

```text
signup/login
    -> load permitted Resource Groups
    -> submit an analysis
    -> receive analysis ID
    -> subscribe to authenticated progress
    -> collect and analyze evidence
    -> validate and store result
    -> display report
    -> revisit it from history
```

The UI shows total resources scanned, issue count and estimated saving, followed by individual findings with severity badges, explanation and copyable commands. A copy button does not mean a command is safe: the report must show prerequisites, scope, expected impact, verification and rollback guidance.

---

## How the Cost Investigation Works

### 1. Establish the scope and time window

I first record subscription, Resource Group, currency and analysis window. Cost comparisons are meaningless if the time period or scope changes between reports.

### 2. Collect deterministic evidence

I collect four evidence groups:

- Inventory: type, SKU, region, tags, state and relationships
- Billing: actual and amortized cost grouped by resource and service
- Utilization: CPU, memory where available, requests, storage, transactions and network
- Governance: Azure Advisor, budgets, reservations, lifecycle and shutdown policies

### 3. Apply rules before AI

Examples:

```text
Unattached managed disk for more than 7 days -> candidate waste
Public IP with no association -> candidate waste
Development VM running outside agreed hours -> scheduling opportunity
Very low CPU alone -> investigation, not automatic downsizing
Missing owner/cost-center tag -> governance issue
```

### 4. Use AI for correlation and explanation

AI can combine the evidence into an understandable hypothesis: “This development VM has low CPU and no activity outside office hours, but memory is unavailable, so confirm memory before moving from D4s to D2s.”

### 5. Validate the output

The backend verifies that every resource exists, severity follows policy, savings uses supplied numbers, and commands match an allow-list. Unsupported claims are marked as assumptions.

### 6. Human review and measurement

An owner approves the change, executes it through the normal IaC/change process, monitors performance, and compares cost after a suitable period. Only then is saving recorded as realized.

---

## Example Investigation: Sudden Azure Cost Increase

If an interviewer asks how I would investigate a spike, I would say:

1. Confirm scope, time window, currency and whether the chart uses actual or amortized cost.
2. Group cost by resource, resource type, service, location, meter and tag.
3. Compare with the previous equivalent period and find the largest contributors to the delta.
4. Check whether usage increased, SKU changed, a new resource was created, egress grew, reservation coverage changed, or a discount expired.
5. Correlate deployment/activity logs and ownership tags with the spike time.
6. Check utilization and business need before proposing rightsizing or deletion.
7. Produce recommendations with evidence, expected saving range, risk, owner and verification plan.
8. Apply approved changes through Terraform or the normal change process, then monitor service health and realized cost.

The AI helps summarize and correlate the data, but the numerical delta and saving are calculated from trusted billing inputs.

---

## Safety and Security Controls

- Use a read-only managed identity for discovery; do not use a developer's broad personal login in production.
- Scope Azure RBAC to allowed subscriptions or Resource Groups.
- Never send access tokens, secrets, connection strings or sensitive tag values to the model.
- Treat Azure names, tags and metadata as untrusted input because prompt injection can be hidden in text fields.
- Place evidence in a clearly delimited data section and prohibit it from changing system instructions.
- Use structured output and server-side schema validation.
- Calculate savings outside the LLM and reject unsupported amounts.
- Allow-list commands and block destructive verbs such as delete unless an explicit, separately approved workflow exists.
- Prefer showing Terraform/IaC changes so they are reviewed and auditable.
- Encrypt database connections and stored reports; define retention and deletion policies.
- Hash passwords, rotate JWT/API secrets, expire sessions and rate-limit authentication and analysis endpoints.
- Record who requested, reviewed and acted on every recommendation.
- Use private networking and approved model/data-residency controls where organizational policy requires them.

---

## Error Handling and Reliability

| Failure | Handling approach |
| --- | --- |
| Azure CLI missing | Fail health/readiness check with installation guidance |
| Azure session expired | Return an authentication-specific error; do not expose raw tokens |
| Invalid or unauthorized Resource Group | Return 404/403 without leaking other scopes |
| CLI timeout or throttling | Bounded retry with backoff and correlation ID |
| Partial provider data | Store partial status and show which evidence is missing |
| OpenAI timeout/rate limit | Retry with limits, then preserve inventory and mark analysis incomplete |
| Invalid AI JSON | Schema validation, one repair attempt, then controlled failure |
| Database unavailable | Do not claim completion; retry or queue persistence safely |
| WebSocket disconnect | Analysis continues; client reconnects and fetches current status |
| Duplicate request | Idempotency key prevents duplicate analyses and model cost |

---

## Testing Strategy

### Unit tests

- Azure JSON normalization and provider-specific enrichment
- CLI argument construction without shell injection
- billing calculations and rule thresholds
- AI response schema validation
- password hashing and JWT expiry
- report authorization by user ID

### Integration tests

- Mock Azure CLI success, invalid login, timeout and malformed JSON
- Mock the model API for valid, invalid, empty and rate-limited responses
- Test PostgreSQL JSONB persistence and user isolation
- Test authenticated WebSocket ownership and reconnection
- Test `202` job creation through final report retrieval

### AI evaluation

Maintain a fixed set of known scenarios and measure:

- finding precision and recall
- unsupported-claim rate
- command validity
- severity consistency
- saving-calculation accuracy
- explanation usefulness reviewed by engineers

### End-to-end test

```text
signup -> login -> select authorized RG -> start analysis
-> see progress -> view evidence-backed report -> open history
```

I would also test empty Resource Groups, thousands of resources, repeated clicks, expired tokens, cross-user history access, malicious tag text and browser reconnection.

---

## Measures of Success

I would measure rather than invent the following:

- time to produce the initial cost investigation
- percentage of findings accepted by owners
- false-positive and unsupported-claim rates
- proposed versus approved versus realized monthly savings
- time from finding to approved action
- number of unowned or untagged resources reduced
- model/API cost per analysis
- analysis completion and failure rates
- user feedback on whether evidence and actions were understandable

Realized saving should be measured after change against an agreed baseline and adjusted for workload changes.

---

## Main Challenges and How I Addressed Them

### Inventory is not utilization

`az resource list` tells us that a resource exists, but not whether it is idle. I treat inventory-only results as candidates and add metrics and billing evidence before making a confident recommendation.

### AI can hallucinate prices or commands

Prices and savings are computed deterministically. The AI uses structured output, and commands are checked against resource state and an allow-list before display.

### Recommendations can affect availability

Downsizing or stopping a resource may save money but cause an outage. Each finding includes owner validation, risk, observation window, change plan, rollback and post-change monitoring.

### Long-running requests and realtime progress

The API creates a background job and returns an analysis ID first. WebSocket progress is resumable, while the database remains the source of truth for current status.

### Multi-user security

Authentication alone is insufficient. Every Resource Group, history row and WebSocket subscription is authorized against the current user and permitted Azure scope.

---

## What I Would Improve Next

1. Replace production CLI subprocess calls with Azure SDK and managed identity.
2. Add Cost Management exports/query data, Azure Monitor metrics and Azure Advisor evidence.
3. Add deterministic price and reservation/savings-plan calculations.
4. Add provider-specific scanners for compute, disks, databases, storage, App Service and Log Analytics.
5. Use a durable job queue for horizontal scaling, retries and cancellation.
6. Add prompt/version tracking and a regression evaluation set.
7. Generate pull requests for Terraform changes instead of direct CLI mutation.
8. Add approval, exception and suppression workflows with owner and expiry.
9. Add budgets, anomaly alerts and scheduled analysis across subscriptions.
10. Compare forecast, proposed saving and realized saving on a FinOps dashboard.

---

## Common Interview Follow-Up Questions

### Why did you need AI if rules can detect waste?

Rules are best for facts and calculations. AI is useful for correlating many signals, ranking them and explaining the result in plain language. I use a hybrid approach: deterministic collection and calculation, AI explanation, then deterministic validation.

### Can the tool really detect an oversized VM from the original data?

Not reliably from inventory alone. It needs CPU, memory if available, I/O, workload patterns, availability requirements and a meaningful observation window. Without these, the report must label it as a low-confidence candidate.

### How do you calculate estimated savings?

I compare the trusted current-cost baseline with the candidate configuration price for the same region and usage window, include reservation/licensing effects where relevant, and present a range. The LLM does not perform or invent the calculation.

### Would you let AI delete an unused resource?

No. “Unused” may still mean disaster-recovery, compliance or seasonal use. I verify ownership, dependencies, activity, backup and retention requirements. The normal IaC/change approval performs the action and includes rollback.

### Why use PostgreSQL?

It stores users, status and searchable analysis metadata while JSONB preserves the structured report. It also supports ownership checks, history, audit fields and later reporting.

### Why use WebSockets?

Inventory, metrics and AI analysis can take time. WebSockets give stage updates without frequent polling. The database still stores authoritative status so disconnecting the browser does not lose the job.

### How do you protect the model from sensitive Azure data?

I minimize and redact the payload, remove credentials and sensitive tag values, use approved endpoints and retention settings, delimit untrusted metadata, and log only hashes or identifiers needed for audit.

### What happens if OpenAI is unavailable?

The deterministic inventory and rule findings remain available. I mark the explanation stage incomplete, retry within a fixed policy, and allow a later re-analysis rather than losing the collected evidence.

### How is this different from Azure Advisor?

Advisor is a valuable source of platform recommendations. This application can combine Advisor with organization-specific rules, ownership tags, billing history, operational metrics, approval workflow and a simple cross-signal explanation. It should complement, not pretend to replace, native Azure capabilities.

### How would you prove business value?

I would track accepted recommendations and compare verified cost after an approved change with an agreed baseline, while checking that latency, availability and capacity objectives remained healthy. Proposed savings alone are not business value.

---

## Honest Closing Statement

> This project demonstrates how I would apply AI in day-to-day DevOps and FinOps work: automate repetitive evidence collection, use deterministic logic for facts and money, use AI to correlate and explain the evidence, and keep a human in control of changes. The supplied material is a staged design rather than proof of a production deployment, so my next step would be to implement it, validate it with known Azure scenarios, and measure accepted and realized savings.
