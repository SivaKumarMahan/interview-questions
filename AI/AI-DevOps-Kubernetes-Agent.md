# AI DevOps Kubernetes Agent

## Important Accuracy Note

The supplied project folder contains a high-level design and five staged implementation prompts. It does not contain the generated backend/frontend source code, deployment manifests, automated test results, screenshots, or production metrics.

In an interview, I should therefore say **“I designed and prototyped this workflow”** unless I have separately built, executed, and validated the application. I should claim that it is fully implemented or production-deployed only when I can show the working code, test evidence, security review, deployment and measured results.

---

## One-Line Project Explanation

I designed an on-demand AI assistant that collects Kubernetes evidence such as Pod status, logs, Events, Deployment health and Service networking, sends structured evidence to an LLM, and returns a simple root cause, supporting explanation, suggested fix, commands, prevention advice and confidence score.

The objective is to help an engineer investigate faster. The AI recommends actions; it does not automatically run destructive changes.

---

## 30-Second Interview Answer

> I designed an AI-powered Kubernetes troubleshooting assistant for common incidents such as CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending Pods and Service selector problems. A user selects a cluster from the local kubeconfig and starts an investigation from a dashboard. The FastAPI backend safely runs read-only `kubectl` commands, collects Pod state, recent logs, Events, Deployment status, Services and endpoints, and converts everything into structured JSON. The AI layer sends only the relevant evidence to an LLM through OpenRouter and asks it to return a structured diagnosis, suggested fix, commands, prevention steps and confidence. InsForge is used for authentication, realtime progress and investigation history, while Next.js provides the UI. The goal is to reduce investigation time and give junior engineers a clear starting point, without allowing the LLM to make uncontrolled cluster changes.

---

## Two-Minute Interview Explanation

### What problem were we solving?

Kubernetes troubleshooting normally requires an engineer to check several places:

- Pod state and container termination reason
- Current and previous container logs
- Kubernetes Events
- Deployment replica and rollout status
- Service selectors and endpoints
- DNS and connectivity evidence

The information is spread across multiple commands. A junior engineer may see `CrashLoopBackOff`, but that is only a symptom. The real cause could be a missing environment variable, failed mount, incorrect probe, invalid image, OOM kill or dependency failure.

### What did we build?

We separated the solution into two responsibilities:

1. A deterministic investigation layer gathers reliable Kubernetes evidence.
2. An AI reasoning layer correlates that evidence and explains the probable cause in simple language.

The backend remains the orchestrator. The LLM never receives direct cluster credentials and should not be allowed to execute commands.

### What is the end-to-end flow?

```text
User logs in
    -> selects a kubeconfig cluster/context
    -> clicks Investigate
    -> FastAPI validates user, cluster and request
    -> read-only Kubernetes evidence is collected
    -> evidence is normalized into JSON
    -> prompt builder sends relevant evidence to the LLM
    -> structured diagnosis is validated
    -> result and progress are saved
    -> dashboard shows root cause, fix and confidence
```

### What was the end goal?

The end goal was not to replace the DevOps or SRE engineer. It was to reduce mean time to understand an incident, standardize the initial investigation, preserve a useful history and help engineers move from a Kubernetes symptom to an evidence-backed next action.

---

## High-Level Architecture

```text
┌───────────────────────────────────────────────┐
│ Next.js Dashboard                             │
│ Login | Cluster selection | Progress | Result │
└──────────────────────┬────────────────────────┘
                       │ HTTP API / realtime status
                       ▼
┌───────────────────────────────────────────────┐
│ FastAPI Backend                               │
│ Authentication, validation and orchestration  │
└──────────────┬─────────────────┬──────────────┘
               │                 │
               ▼                 ▼
┌─────────────────────────┐   ┌──────────────────┐
│ Kubernetes Investigation│   │ InsForge         │
│ Read-only kubectl        │   │ Auth, history,   │
│ Pods/logs/events/deploy  │   │ realtime updates│
│ Services/endpoints/DNS   │   └──────────────────┘
└──────────────┬──────────┘
               │ structured and redacted evidence
               ▼
┌───────────────────────────────────────────────┐
│ AI Kubernetes Agent                           │
│ Prompt builder -> OpenRouter LLM -> validator │
│ Root cause | fix | commands | confidence      │
└───────────────────────────────────────────────┘
```

This is an **on-demand troubleshooting application**, not a Kubernetes controller or operator. It investigates only when a user or API triggers it; it does not continuously reconcile cluster state.

---

## Technology Stack and Why We Used It

| Area | Technology | Purpose |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS | Simple typed dashboard and clear investigation experience |
| Frontend data | Axios and React Query | API calls, loading/error state and result caching |
| Backend | Python, FastAPI, Uvicorn, Pydantic | API orchestration, validation and structured response models |
| Backend utilities | Loguru and HTTPX | Structured application logs and outbound LLM calls |
| Kubernetes access | `kubectl` through controlled subprocess execution | Collect cluster evidence using familiar commands |
| AI gateway | OpenRouter | Access a configured LLM such as GPT, Claude or DeepSeek through one API |
| Backend platform | InsForge | Authentication, investigation history, realtime progress and secret/key integration described by the design |
| Packaging | Docker and Docker Compose | Repeatable local frontend/backend startup |
| Configuration | Environment variables | Keep API keys, model name, kubeconfig path and API base URL outside code |

We deliberately used `kubectl` rather than the Kubernetes Python SDK for the initial prototype because it kept the investigation steps easy to understand and demonstrate. For a larger production system, I would evaluate the SDK because it provides typed APIs, watches, cancellation and avoids some command-construction risk.

---

## How We Implemented It in Five Stages

## Stage 1: Project Foundation

We first created a monorepo with separate backend and frontend areas:

```text
ai-kubernetes-agent/
├── backend/
│   ├── api/
│   ├── core/
│   ├── kubernetes/
│   ├── ai/
│   ├── services/
│   └── models/
├── frontend/
│   ├── components/
│   ├── services/
│   ├── hooks/
│   └── types/
├── docker-compose.yml
└── README.md
```

The first milestone implemented only:

- FastAPI application
- `GET /health`
- Minimal Next.js screen
- CORS, logging and environment loading
- Backend and frontend Dockerfiles
- Docker Compose on ports 8000 and 3000

Example health response:

```json
{
  "status": "healthy",
  "service": "ai-kubernetes-agent"
}
```

We intentionally avoided Kubernetes and AI logic at this stage. This incremental approach made it easier to test each layer independently and prevented many integration problems from appearing at once.

## Stage 2: Kubernetes Investigation Engine

The investigation engine behaves like a junior DevOps engineer gathering evidence before reaching a conclusion.

### Kubectl executor

A reusable executor runs an allow-listed command with `subprocess`, captures stdout/stderr, enforces a timeout, records exit code and returns a structured result.

```python
{
    "command": ["kubectl", "get", "pods", "-A", "-o", "json"],
    "success": True,
    "exit_code": 0,
    "stdout": "...",
    "stderr": ""
}
```

The safe design uses an argument list rather than `shell=True`, never accepts arbitrary command text from the user, fixes the selected context explicitly, limits output and redacts secrets.

### Pod inspector

It reads Pod and container status and identifies conditions such as:

- CrashLoopBackOff
- ImagePullBackOff or ErrImagePull
- Pending
- Error
- OOMKilled
- ContainerCreating for an abnormal duration

It records namespace, Pod, container, reason, restart count, readiness and owning workload.

### Logs collector

It fetches a bounded amount of current and, when relevant, previous container logs. It looks for startup exceptions, missing configuration, connection failures and termination clues. The goal is not to send thousands of log lines to the LLM.

### Events analyzer

It groups recent relevant Events such as:

- FailedScheduling
- BackOff
- FailedMount
- FailedPull or ErrImagePull
- Unhealthy probe results

Events are filtered by involved object and time so old unrelated warnings do not become the apparent root cause.

### Deployment inspector

It checks desired, ready, available and unavailable replicas, observed generation, rollout Conditions and the relationship between Deployment, ReplicaSet and Pods.

### Network inspector

It checks Service existence, selector-to-Pod-label matching, endpoints or EndpointSlices and relevant DNS/connectivity evidence. A Service with no endpoints is treated differently from a DNS failure or an application that is not listening.

### Unified evidence payload

The investigation service returns one normalized payload:

```json
{
  "cluster": "development",
  "collected_at": "timestamp",
  "pods": {},
  "logs": {},
  "events": {},
  "deployments": {},
  "network": {},
  "collection_errors": []
}
```

At this stage there is deliberately no AI conclusion. The output can be tested deterministically.

## Stage 3: AI Reasoning Engine

The AI layer consumes the evidence payload and behaves like a senior Kubernetes SRE assistant.

### Prompt builder

The prompt contains:

- Exact scope and selected cluster
- Pod/container state
- Relevant bounded logs
- Recent related Events
- Deployment health
- Service/network findings
- A strict output schema

The model is instructed to distinguish evidence, inference and missing information and to avoid inventing commands or resources.

Expected output:

```json
{
  "root_cause": "DATABASE_URL is missing from the application configuration",
  "explanation": "The container exits during startup and then Kubernetes restarts it.",
  "suggested_fix": "Add the expected secret reference to the Deployment.",
  "commands": ["kubectl -n payments describe deployment payment-service"],
  "prevention": "Validate required configuration during deployment and startup.",
  "confidence": 92,
  "evidence": [
    "Pod is in CrashLoopBackOff",
    "Previous log reports DATABASE_URL missing"
  ]
}
```

### LLM client

The backend uses HTTPX to call OpenRouter. The API key and selected model come from environment/secret configuration, never source control. The client adds connection/read timeout, bounded retry for transient failures, safe error messages and correlation logging without prompts containing secrets.

### Root-cause and recommendation handling

The LLM output is parsed through a strict Pydantic response model. The system rejects invalid or incomplete output instead of displaying free-form text as a trusted diagnosis. Suggested commands are treated as guidance and displayed for human review; the application does not execute them.

### Confidence

Confidence must reflect evidence quality, not the model's writing style. A high score is reasonable only when independent signals agree—for example termination state, previous log and Event all indicate the same cause. Missing logs, collection errors or conflicting evidence must lower confidence and produce explicit next investigation steps.

## Stage 4: Application Experience with InsForge

The fourth stage converts the backend into a usable application:

- User login and session
- Protected investigation API/dashboard
- Realtime progress events
- Persisted investigation history
- Root-cause result card

Progress states are simple and meaningful:

```text
Checking Pods
Reading Logs
Analyzing Events
Inspecting Deployments
Checking Networking
Running AI Reasoning
Validating Diagnosis
Completed
```

History stores metadata such as investigation ID, user, selected cluster/context, namespace/scope, timestamp, status, root cause and confidence. Raw sensitive logs should not be retained automatically; retention and access need an explicit policy.

## Stage 5: End-to-End Integration and Failure Testing

The final stage joins the entire workflow and tests known failure cases:

1. CrashLoopBackOff caused by a missing environment variable
2. ImagePullBackOff caused by an invalid image tag
3. OOMKilled caused by an insufficient memory limit or application memory behavior
4. Service selector mismatch causing no endpoints

It also handles:

- Missing kubeconfig
- Cluster unreachable
- Invalid or unauthorized context
- `kubectl` failure or timeout
- LLM/API timeout or invalid response
- Authentication failure
- No unhealthy resources found
- Partial evidence collection

The dashboard shows useful failure messages without exposing a stack trace or secret.

---

## Multi-Cluster Selection

The integration requirement includes showing clusters/contexts from the local kubeconfig and allowing the user to select one.

A safer flow is:

1. Backend reads allowed kubeconfig contexts.
2. API returns display names and a stable internal identifier.
3. User selects one context.
4. Backend validates that the user may access it.
5. Every command supplies that exact context and optional namespace.
6. History records which context was investigated.

The frontend must never send an arbitrary shell fragment as a context name. In production, server-side service-account/workload identity and explicit cluster registration are generally safer than exposing a developer's local kubeconfig.

---

## Example Incident: CrashLoopBackOff

### User symptom

The payment service is unavailable.

### Evidence collected

```text
Pod: payment-service-7d9f
State: Waiting / CrashLoopBackOff
Restarts: 8
Previous exit code: 1
Previous log: "DATABASE_URL environment variable is required"
Deployment: 0 of 3 replicas available
Service: selector matches Pods, but no Ready endpoints
```

### AI-assisted conclusion

```text
Root cause:
The application exits during startup because DATABASE_URL is missing.

Why:
The previous container log contains the explicit configuration error.
CrashLoopBackOff and repeated exit code 1 confirm a startup failure.

Suggested fix:
Add the correct Secret reference to the Deployment and roll out a new revision.

Prevention:
Validate required variables in CI and use a startup check with a clear message.
```

### Human-controlled investigation/fix flow

```bash
kubectl -n payments describe pod payment-service-7d9f
kubectl -n payments logs payment-service-7d9f --previous
kubectl -n payments get deployment payment-service -o yaml
kubectl -n payments rollout status deployment/payment-service
```

I would not recommend `kubectl edit` as the permanent source of truth when GitOps or reviewed manifests are used. The lasting fix should be committed to the deployment repository, reviewed and reconciled through the normal pipeline.

---

## How AI Was Used in Day-to-Day DevOps

The useful AI part is not “ask a chatbot why Kubernetes is broken.” We first gather deterministic evidence and give the model a narrow reasoning task.

AI helps with:

- Correlating Pod state, Events, logs and rollout health
- Translating technical evidence into a simple explanation
- Ranking likely causes
- Suggesting the next safe diagnostic command
- Generating prevention recommendations
- Summarizing an investigation for history and handover

Deterministic code still handles:

- Authentication and authorization
- Cluster selection
- Command execution
- Evidence collection
- Output limits and redaction
- Response-schema validation
- History and progress state
- Approval and execution of changes

This separation makes the system easier to trust and test.

---

## Security and Safety Controls

The supplied design prompts describe the functional flow, but a production implementation also needs these controls:

### Kubernetes access

- Use read-only, least-privilege RBAC for investigation.
- Scope access by allowed cluster and namespace.
- Do not expose a general-purpose shell endpoint.
- Use an argument array, command allow-list, timeout and output limit.
- Audit user, cluster, scope and command category.

### Secrets and sensitive evidence

- Store OpenRouter/InsForge credentials outside Git.
- Prefer workload identity or a secret manager over long-lived environment secrets.
- Redact Secret values, tokens, authorization headers and personal data from logs/prompts/history.
- Encrypt retained investigation data and define access and deletion policy.

### LLM safety

- Treat Kubernetes logs and annotations as untrusted input; they can contain prompt-injection text.
- Delimit evidence and instruct the model that evidence is data, not instructions.
- Use a strict response schema and reject extra executable content.
- Never automatically run LLM-generated commands.
- Allow only human-reviewed or pre-approved bounded runbooks.
- Record model, prompt version, evidence references and result for audit.

### Operational safety

- Use correlation IDs and bounded retries.
- Apply rate limits and investigation concurrency limits.
- Cancel timed-out investigations.
- Make progress/history updates idempotent.
- Provide a non-AI fallback that returns collected evidence when the LLM is unavailable.

---

## Testing Strategy

### Unit tests

- Parse Pod/container states correctly.
- Select current versus previous logs.
- Group Events by object and time.
- Detect Service selector/endpoints mismatch.
- Build a redacted prompt.
- Validate accepted and rejected LLM responses.
- Calculate or constrain confidence consistently.

### Integration tests

- Mock `kubectl` exit codes, malformed JSON, stderr and timeout.
- Mock OpenRouter success, 429, timeout, server error and invalid JSON.
- Test authentication, history ownership and realtime updates.
- Verify one user's result is not visible to another user.

### Controlled cluster tests

Use a local disposable cluster and versioned test manifests to create:

- Missing environment variable
- Invalid image tag
- Memory-limit failure
- Pending Pod from impossible request/constraint
- Failed mount
- Probe failure
- Service with no endpoints

For each scenario, define expected evidence, acceptable diagnosis, unsafe suggestions that must be rejected and recovery checks.

### End-to-end acceptance

```text
select test cluster -> trigger investigation -> observe progress
-> receive valid diagnosis -> inspect supporting evidence
-> apply reviewed fixture fix -> rerun -> healthy/no-critical-issue result
```

---

## How We Measure Whether It Achieved the Goal

The supplied project does not include measured results, so I should not invent percentages. I would measure:

- Time from investigation start to useful diagnosis
- Root cause top-1 and top-3 accuracy on labeled scenarios
- Percentage of diagnoses supported by cited evidence
- False-positive and low-confidence rate
- Unsafe or invalid command recommendation rate
- Evidence-collection success and latency
- LLM timeout/error and fallback success
- Engineer acceptance/correction rate
- Reduction in repeated manual investigation steps
- User-visible mean time to acknowledge and restore

The success condition is not simply “the LLM answered.” The answer must be correct enough, evidence-backed, safe, understandable and faster than the normal first investigation.

---

## Challenges and How We Addressed Them

### Too much noisy data

Sending every log and Event increases cost and confuses the model. We limit logs, filter by affected object/time and summarize structured status before reasoning.

### Hallucinated fixes

We require a strict output structure, evidence list and human review. Low or conflicting evidence produces next diagnostic steps rather than a confident fix.

### Command injection

The backend builds allow-listed argument arrays. User input is validated as a context, namespace or object name and never concatenated into a shell command.

### LLM or network failure

The deterministic investigation result is still returned. The UI explains that AI analysis is temporarily unavailable and gives the evidence to the engineer.

### Confidence can be misleading

The model's self-reported number is not enough. Confidence should be constrained by evidence coverage, agreement, collection errors and scenario validation.

### Cluster credentials are high risk

Use read-only RBAC, explicit scope, short-lived identity, audit and separate credentials per cluster/environment. A public application must never receive unrestricted admin kubeconfig access.

---

## What I Would Improve Next

1. Replace or complement subprocess calls with the Kubernetes client for typed API access and watches.
2. Add deterministic rule checks for obvious failures before invoking the LLM.
3. Retrieve relevant approved runbooks and Kubernetes documentation rather than asking the model from memory alone.
4. Add OpenTelemetry traces and service metrics for the agent itself.
5. Use queued background jobs for long investigations and enforce per-cluster concurrency.
6. Add prompt/model evaluation with a versioned incident test dataset.
7. Support namespace/workload-scoped investigation rather than scanning every cluster resource.
8. Add an approval workflow for a small set of reversible runbooks, with dry run and post-action verification.
9. Deploy inside a private management environment with workload identity instead of relying on local kubeconfig.
10. Add cost controls, token budgets and evidence caching without reusing stale cluster state.

---

## Likely Interview Follow-Up Questions

### Why use AI when scripts and alerts already exist?

Scripts are excellent for deterministic checks, but incidents often contain several related signals. AI helps correlate and explain them. I keep evidence collection and safety deterministic and use AI only for reasoning and explanation.

### Why did you use FastAPI?

It gives simple typed APIs, async support for the LLM call, Pydantic validation and automatic API documentation. It also keeps orchestration separate from the UI.

### Why use `kubectl` instead of the Kubernetes SDK?

For the prototype it was simple, familiar and easy to demonstrate. The trade-off is process overhead, parsing and command-safety work. For production scale and watches, I would consider the typed SDK.

### Is this a Kubernetes operator?

No. An operator continuously watches desired state and reconciles it. This system runs only when an authenticated user requests an investigation and primarily reads evidence.

### How do you prevent hallucination?

I provide narrow structured evidence, require evidence citations and a strict response schema, lower confidence when data is missing, validate output and never automatically execute generated commands.

### What happens if the LLM is unavailable?

The evidence collector still works. The API returns the structured investigation with a message that AI analysis is unavailable, and the engineer continues manually.

### How do you secure Kubernetes access?

Read-only least-privilege RBAC, allowed cluster/namespace scope, short-lived identity, command allow-list, no shell execution, timeouts, audit logs and no Secret-value collection.

### How do you validate the confidence score?

I compare diagnoses with labeled failure scenarios and human-confirmed incidents. Confidence is constrained by the number and independence of supporting signals, collection errors and contradictory evidence; it is not accepted solely because the LLM prints a percentage.

### Would you let AI automatically fix production?

Not directly. I would begin with recommendations only. Later, a small catalog of reversible and well-tested runbooks could run with preconditions, dry run, approval, limited scope, rollback, audit and post-change SLO verification.

### How is investigation history useful?

It supports audit, handover, repeated-incident detection and evaluation of model quality. It must store appropriate metadata and redacted evidence with access and retention controls.

### What result can you confidently claim from the supplied repository?

I can confidently claim a complete staged design and implementation plan for an AI-assisted Kubernetes troubleshooting product. I cannot claim a working production deployment or measured MTTR improvement from this supplied folder alone because it contains prompts/HLD rather than application source and test evidence.

---

## Final Interview Closing Statement

> This project showed me that useful AI in DevOps is not about giving an LLM cluster-admin access. The reliable approach is to collect evidence deterministically, give AI a narrow reasoning task, validate its structured answer, and keep execution under human or tightly controlled runbook approval. The end result is a faster and more consistent first investigation, while Kubernetes access, secrets and production changes remain governed by normal DevOps and SRE controls.

---

## Source Project Reviewed

This explanation was prepared from all files supplied in `AI-DevOps-Kubernetes-Agent-main`:

- High-level architecture README
- Project-foundation prompt
- Kubernetes investigation-engine prompt
- AI reasoning-engine prompt
- InsForge authentication/dashboard/history prompt
- End-to-end integration and failure-testing prompt
- `.gitignore`
- Apache License 2.0

The Apache License permits use and modification under its terms; attribution/license obligations still apply if project material is redistributed.
