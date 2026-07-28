# AI-Assisted Kubernetes Upgrade Readiness Assessment

## Important Accuracy Note

The supplied project contains one detailed assessment prompt and an Apache 2.0 license. It does not contain an implemented application, cluster collector, AI integration, assessment output, automated tests, upgrade execution logs or production results.

In an interview, I should say **“I designed an AI-assisted Kubernetes upgrade assessment workflow”** unless I have separately implemented and validated it against real clusters. The prompt defines what the assessment must do; it is not evidence that a cluster was successfully upgraded.
---

## One-Line Project Explanation

I designed an AI-assisted readiness tool that combines live Kubernetes evidence, manifests, release notes and vendor compatibility matrices to decide whether a cluster upgrade is safe, what could break, what must be fixed first, and how to validate and roll back the change.
---

## 30-Second Interview Answer

> I designed an AI-assisted Kubernetes upgrade risk assessor. Before an upgrade, it gathers read-only evidence about cluster and node versions, workloads, APIs, CRDs, operators, admission webhooks, CNI, CSI, runtime and resource pressure. It then checks every intermediate Kubernetes release and verifies installed add-ons against official compatibility information. Predictable checks find removed APIs and unsafe settings, while AI compares the large evidence set, explains failure scenarios and produces a risk matrix, readiness score and ordered fix plan. Unknown compatibility is never treated as safe, and AI never performs the upgrade. A platform engineer reviews the evidence, tests the upgrade in a representative environment, follows the approved runbook and validates service health after each phase.

---

## Two-Minute Interview Explanation

A Kubernetes upgrade is not just changing the control-plane version. The API server may remove an API, an operator may not support the target version, a conversion webhook may stop working, a CSI driver may lose compatibility, or draining a node may expose missing capacity and PodDisruptionBudget problems.
I split the assessment into four parts:

1. A read-only collector inventories the cluster and supporting configuration.
2. A compatibility engine checks objective rules such as version skew, removed APIs, CRD storage versions and add-on support.
3. A retrieval layer obtains the official Kubernetes release notes and vendor compatibility documents for every version step.
4. An AI reasoning layer compares the verified facts, models failure scenarios and creates a simple executive and engineering report.

The report separates verified, probable, possible and unknown risks. For every issue it says what can break, during which upgrade phase, the impact, severity, supporting evidence and required fix.

It ends with an `APPROVED`, `CONDITIONAL` or `NOT RECOMMENDED` decision, but the decision is accepted only after predictable validation and human review.

The key principle is conservative reasoning: if compatibility cannot be verified, it reduces confidence and cannot silently become a pass.

---

## Problem, Goal and End Result

### Problem

- Kubernetes changes across every minor release, not only at the final target version.
- Cluster add-ons have their own Kubernetes compatibility ranges and upgrade ordering.
- Custom Resources may depend on conversion webhooks and controller behavior.
- Node drain can cause capacity, disruption-budget, local-storage or scheduling failures.
- Networking, DNS and storage problems may appear only after nodes or workloads restart.
- Manually checking many release notes and vendor matrices is slow and easy to miss.

### Goal

Create a repeatable pre-upgrade assessment that answers:

- Is the source-to-target path supported?
- What will break and when?
- What must be upgraded or migrated first?
- Is there enough capacity to drain and replace nodes safely?
- What is still unknown?
- What is the correct upgrade, validation and rollback order?

### Expected result

```text
Decision: CONDITIONAL
Source: 1.x
Target: 1.y
Readiness: 78/100
Confidence: 84%

Verified blocker:
  Component: example-controller
  Evidence: installed version does not support target Kubernetes version
  Break point: first reconciliation (making actual state match desired state) after control-plane upgrade
  Impact: custom resources stop reconciling
  Required action: upgrade controller and CRDs before cluster upgrade
```

Scores help summarize the assessment, but evidence and explicit blockers determine the decision. A high average score must never hide one critical incompatibility.

---

## High-Level Architecture

```text
┌──────────────────────────────────────────────┐
│ Assessment request                          │
│ Cluster + source version + target version   │
└─────────────────────┬────────────────────────┘
                      ▼
┌──────────────────────────────────────────────┐
│ Read-only evidence collector                 │
│ cluster | workloads | APIs | CRDs | add-ons  │
│ webhooks | CNI | CSI | runtime | capacity    │
└──────────────┬───────────────────────────────┘
               │ normalized evidence
               ▼
┌──────────────────────────────────────────────┐
│ Compatibility and source-verification layer  │
│ rules | release notes | vendor matrices      │
│ version skew | policy | manifest scanning    │
└──────────────┬───────────────────────────────┘
               │ cited facts and unknowns
               ▼
┌──────────────────────────────────────────────┐
│ AI reasoning and report generation           │
│ correlation | failure modeling | explanation │
└──────────────┬───────────────────────────────┘
               │ schema and policy validation
               ▼
┌──────────────────────────────────────────────┐
│ Human-reviewed readiness report              │
│ decision | risks | remediation | runbook      │
└──────────────────────────────────────────────┘
```

AI is not the source of truth. Live cluster evidence and official compatibility documentation are the source of truth; AI helps compare and explain them.

---

## Suggested Technology Stack

| Area | Technology | Purpose |
| --- | --- | --- |
| Collector | Python, Kubernetes Python client or controlled `kubectl` | Read cluster objects and status |
| API | FastAPI and Pydantic | Start assessments and validate structured results |
| Compatibility | Predictable Python rules | Version skew, API, CRD, capacity and policy checks |
| Manifest scanning | Pluto, kubent or equivalent plus repository scanning | Find deprecated/removed APIs in deployed and source manifests |
| Documentation retrieval | Official Kubernetes and vendor sources | Verify changes and add-on support |
| AI | Approved LLM with structured output | Compare evidence and explain risk |
| Persistence | PostgreSQL/object storage | Store evidence snapshot, citations, report and audit history |
| Execution | Background worker/queue | Run long assessments with retry and cancellation |
| Observability | Metrics, structured logs and traces | Audit duration, errors and evidence coverage |

The exact tools may vary. The important design choice is to separate evidence collection, compatibility rules and AI interpretation.

---

## End-to-End Assessment Flow

### Phase 1: Validate the requested upgrade path

I record:

- cluster type and provider
- source and target Kubernetes versions
- managed or self-managed control plane
- high-availability topology
- maintenance window and business criticality
- provider-specific supported upgrade path

I evaluate every intermediate minor version. If the platform supports only sequential minor upgrades, a multi-version request is converted into several gated steps.

```text
source -> next minor -> validation -> next minor -> validation -> target
```

### Phase 2: Capture a read-only cluster snapshot

Core commands from the design include:

```bash
kubectl version
kubectl cluster-info
kubectl get nodes -o wide
kubectl api-resources
kubectl get apiservices
kubectl get all -A
kubectl get crd -o yaml
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl top nodes
kubectl top pods -A
```

I additionally collect Deployments, StatefulSets, DaemonSets, Jobs, CronJobs, Services, Ingresses, NetworkPolicies, StorageClasses, PVs, PVCs, VolumeSnapshots, PodDisruptionBudgets, priority classes, events and relevant node conditions.

Every command has an allow-list, timeout, output limit, correlation ID and sanitized error handling. Collection uses a least-privilege (minimum required access) read-only identity and never fetches Secret values.

### Phase 3: Inventory controllers and operators

I identify standard, vendor and internal components using labels, images, Helm releases, namespaces and Custom Resource ownership. Examples include:

- ingress and DNS controllers
- metrics-server and autoscalers
- cert-manager
- Prometheus Operator
- Argo CD or Flux
- service meshes
- policy engines
- backup tools
- CNI and CSI drivers
- cloud-provider controllers

For each component, I record installed version, source of version evidence, current support, target support, known upgrade notes and whether it must be upgraded before or after Kubernetes.

Image tags are helpful but not always reliable; digests, Helm metadata, component endpoints and vendor-supported detection methods provide stronger evidence.

### Phase 4: Analyze all intermediate release changes

The retrieval layer reads official release notes, changelogs, deprecation guides, upgrade notes and provider documentation for every version transition. It extracts:

- API removals and deprecations
- feature-gate changes
- kubelet and runtime requirements
- security and admission behavior changes
- networking, DNS and proxy changes
- storage and CSI changes
- scheduler and eviction changes
- version-skew restrictions

Each claim in the final report should retain its source URL, document version and retrieval time. If official support cannot be found, the component becomes an unknown risk rather than a pass.

### Phase 5: Scan APIs and manifests

I check three places:

1. Objects currently exposed by the API server
2. Stored and requested API usage from metrics or audit evidence
3. Git, Helm and deployment manifests that may recreate an old API later

This distinction matters because `kubectl get -o yaml` normally shows the version currently served by the API server. The API server can convert objects, so scanning only live YAML may miss an old API still present in a Helm chart or CI repository.

I therefore scan source manifests and, where available, API request metrics/audit logs as well.

For each affected object the report states:

```text
Namespace and object
Current/source API
Removal or behavior-change version
Evidence location
Failure point
Required manifest migration
```

### Phase 6: Assess CRDs and conversion

For every CRD I verify:

- `apiextensions.k8s.io` compatibility
- served and storage versions
- `status.storedVersions`
- structural OpenAPI schema
- validation and defaulting behavior
- conversion strategy and webhook service
- webhook certificate, CA bundle and endpoint availability
- controller support for every stored/served version
- need for storage-version migration

A CRD definition being accepted does not prove that its controller can reconcile (make actual state match desired state) objects on the target Kubernetes version. CRD and controller compatibility are separate gates.

### Phase 7: Assess admission webhooks

I review validating and mutating webhooks for:

- service and endpoint health
- TLS certificate validity and CA configuration
- supported admission review versions
- namespace/object selectors
- timeout and `failurePolicy`
- side effects and reinvocation behavior
- controller compatibility

A failing webhook with `failurePolicy: Fail` can block Pod creation or other API writes, so it may be a critical pre-upgrade dependency.

### Phase 8: Assess networking, storage and runtime

Networking checks include CNI support, CoreDNS, kube-proxy or replacement, Services, Ingress controllers, NetworkPolicies and provider load-balancer controllers.

Storage checks include CSI driver versions, StorageClasses, reclaim policies, snapshots, attachment behavior, PV/PVC health and stateful workload disruption.

Node/runtime checks include OS image, kernel, container runtime, CRI, kubelet version, taints, allocatable resources and provider image support.

### Phase 9: Assess drain and capacity risk

Before upgrading a worker node, I determine whether its Pods can move elsewhere:

- enough spare CPU, memory, pod IPs and volume attachment capacity
- valid PodDisruptionBudgets
- replicas spread across nodes/zones
- no blocking local storage or unmanaged static Pods
- topology, affinity, anti-affinity, taint and selector constraints
- critical DaemonSets and priority/preemption behavior

Example dry-run preparation:

```bash
kubectl get pdb -A
kubectl get pods -A -o wide
kubectl describe node <node>
kubectl drain <node> --ignore-daemonsets --dry-run=server
```

The exact drain options depend on policy. I would never add `--delete-emptydir-data` or force eviction automatically without understanding data and availability impact.

### Phase 10: Generate and validate the report

The AI receives normalized, redacted evidence and retrieved compatibility facts. It returns a strict schema, for example:

```json
{
  "decision": "CONDITIONAL",
  "readiness_score": 78,
  "confidence": 84,
  "verified_issues": [],
  "probable_issues": [],
  "possible_issues": [],
  "unknown_risks": [],
  "required_actions": [],
  "upgrade_order": [],
  "post_upgrade_validations": []
}
```

The backend validates the schema, recalculates scores, checks citations and applies policy gates. The LLM cannot turn a predictable critical failure into `APPROVED`.

---

## Risk Classification

| Status | Meaning | Example action |
| --- | --- | --- |
| PASS | Verified compatible with strong evidence | Continue |
| GOOD | No issue found; normal validation still required | Continue with checks |
| WARNING | Non-blocking concern or migration approaching | Schedule fix |
| HIGH RISK | Likely outage or major decline without fix | Fix before upgrade |
| CRITICAL | Verified blocker, data risk or unsupported path | Do not upgrade |

Every finding uses the mandatory failure format:

```text
WHAT WILL BREAK:
WHEN IT WILL BREAK:
IMPACT:
SEVERITY:
EVIDENCE:
REMEDIATION:
VALIDATION:
```

---

## Readiness and Confidence Scoring

Readiness measures known technical risk. Confidence measures how complete and trustworthy the evidence is. They answer different questions.

Example readiness model:

```text
APIs             15 points
CRDs             15 points
Controllers      15 points
Webhooks         10 points
Networking       10 points
Storage          10 points
Security          8 points
Runtime/nodes    12 points
Control plane     5 points
Total           100 points
```

Predictable deductions are mapped to severity, with a critical blocker also forcing `NOT RECOMMENDED` regardless of the total. The weights must be versioned and agreed with the platform team rather than invented by the LLM.

Confidence is limited by evidence coverage:

```text
cluster inventory completeness
+ release-note coverage
+ verified controller matrices
+ verified CRD ownership
+ provider/runtime evidence
- unknown or inaccessible components
```

An assessment with readiness `95` and confidence `45%` is not safe to approve. It means few known problems were found but too much remains unverified.

---

## Upgrade Execution Plan After Approval

The assessment does not execute the upgrade. A reviewed runbook normally includes:

1. Back up etcd or confirm the managed-provider recovery mechanism.
2. Back up critical application data and verify restore procedures.
3. Freeze or coordinate risky platform changes.
4. Remediate removed APIs and incompatible CRDs/controllers.
5. Upgrade add-ons that must precede the control plane.
6. Validate the plan in a representative non-production cluster.
7. Upgrade one supported minor version at a time.
8. Upgrade the control plane according to provider procedure.
9. Run the control-plane validation gate.
10. Drain and replace/upgrade worker nodes in controlled batches.
11. Validate each node pool and availability zone before continuing.
12. Upgrade add-ons that must follow the cluster version.
13. Run application, networking, storage, policy and observability tests.
14. Observe the cluster through the agreed soak period.

Managed services such as AKS, EKS and GKE have provider-specific order, supported versions, node-image procedures and rollback limitations. The runbook must use the provider's current official process.

---

## Post-Upgrade Validation

I validate more than `kubectl get nodes`:

- all nodes Ready and on supported kubelet/runtime versions
- system Pods healthy with no new restart loops
- APIService and webhook availability
- Deployments, StatefulSets and DaemonSets at desired replicas
- operators reconciling and Custom Resources healthy
- DNS resolution and internal/external traffic
- Ingress, load balancer and NetworkPolicy behavior
- PVC mount, read/write and snapshot/restore checks
- autoscaling and scheduling
- admission, RBAC and Pod Security behavior
- monitoring, logging and alert delivery
- application synthetic tests and critical business transactions
- error rate, latency, saturation (how close a resource is to its limit) and event comparison with baseline

Example commands:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apiservices
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl rollout status deployment/<name> -n <namespace>
```

Command success alone is not sufficient; service-level and application-level validation are required.

---

## Rollback and Recovery Approach

Rollback must be designed before the change. I document:

- provider-supported control-plane recovery or limitations
- node-pool rollback/replacement method
- previous add-on, Helm chart and manifest versions
- etcd backup and tested restore process for self-managed clusters
- application-data backup and restore ownership
- traffic-shift or failover plan
- stop conditions and decision authority

Kubernetes downgrades are not generally something I assume is safe. On managed platforms, control-plane rollback may be unavailable. Therefore forward fix, replacement node pools, backup restore or cluster failover may be the real recovery method.

---

## How AI Is Used Safely

### Good uses of AI

- summarize changes across several release documents
- compare a removed API with affected manifests and workloads
- explain why a webhook or controller creates upgrade risk
- organize findings by failure phase and severity
- draft fix, validation and runbook steps
- highlight contradictions and missing evidence

### Tasks kept predictable

- cluster collection
- semantic version comparison
- API removal tables
- compatibility-matrix parsing and citations
- readiness/confidence calculation
- policy gates
- command allow-listing
- final approval and upgrade execution

### Controls

- Treat resource names, annotations, labels and CRD text as untrusted input.
- Redact Secret data, tokens, private URLs and sensitive configuration.
- Require citations for compatibility claims.
- Reject claims that are not supported by collected or retrieved evidence.
- Validate structured output and score calculations server-side.
- Keep collection read-only and separate from upgrade credentials.
- Require platform-owner approval for the report and change runbook.
- Record evidence hashes, prompt/model version and assessment time for audit.

---

## Error Handling and Unknowns

| Situation | Correct behavior |
| --- | --- |
| Namespace is inaccessible | Mark inventory incomplete and reduce confidence |
| Metrics Server unavailable | Do not infer capacity safety from missing metrics |
| Operator version unknown | Classify support as unknown/high risk based on criticality |
| Vendor matrix unavailable | Do not let the model assume compatibility |
| Release-note retrieval incomplete | Block final approval or lower confidence below policy threshold |
| CRD owner cannot be identified | Report unknown reconciliation (making actual state match desired state) risk |
| Webhook endpoint is unhealthy | Flag possible API-write/deployment failure |
| AI output is invalid | Fail report generation safely; preserve collected evidence |
| Cluster changes during scan | Record timestamps/resource versions and warn about snapshot inconsistency |

Unknown does not always mean the component will fail, but it means the assessor cannot prove that it is safe.

---

## Testing Strategy

### Unit tests

- version-range and version-skew calculations
- release-to-removal mapping
- CRD served/storage-version checks
- severity and policy-gate rules
- readiness and confidence calculations
- redaction and prompt-injection defenses
- structured AI response validation

### Integration tests

- collector behavior with RBAC denial, timeout and partial APIs
- clusters containing deprecated manifests and unhealthy APIService objects
- conversion and admission webhook failure scenarios
- fake vendor matrices and missing-source behavior
- database evidence/report ownership
- background job retry and cancellation

### Scenario evaluation

Create known test clusters or fixtures for:

- removed API in a Git manifest but not visible in live output
- old cert-manager or ingress controller
- CRD with conversion webhook failure
- blocking PodDisruptionBudget
- insufficient node-drain capacity
- incompatible CNI or CSI version
- expired webhook certificate
- privileged workload affected by security-policy change

Expected blockers and severities are reviewed by platform engineers and compared with the generated report.

### Upgrade rehearsal

The strongest validation is a representative staging or cloned environment. I run the exact upgrade sequence, failure tests and application checks, record differences, then update the production runbook.

---

## Measures of Success

- percentage of installed components with verified compatibility
- deprecated/removed APIs found before the maintenance window
- critical findings confirmed by engineers
- false-positive and unsupported-claim rate
- assessment duration compared with manual review
- fix completion before upgrade
- upgrade success without unplanned outage or data loss
- post-upgrade error, latency and reconciliation (making actual state match desired state) health
- number of rollbacks or emergency fixes
- repeatability of assessment results from the same evidence snapshot

I would not claim the AI “prevented an outage” without a confirmed finding and documented fix. A defensible outcome is that it identified a specific risk before the change and the team verified and fixed it.

---

## Main Challenges and Solutions

### Compatibility information changes

I retrieve and timestamp official version-specific sources for every assessment rather than relying on model memory.

### Live objects can hide old source APIs

I scan Git, Helm and CI manifests plus API-request evidence, not only `kubectl get` output.

### Internal controllers may have no public matrix

I require owner confirmation and test evidence. Until then, compatibility remains unknown and reduces confidence.

### Upgrade risk is phase-specific

Each finding states whether failure occurs during control-plane upgrade, node drain, node startup, first workload restart, first API write or first controller reconciliation (making actual state match desired state).

### A numeric score can create false confidence

Critical policy gates override the weighted score, and unknowns reduce confidence separately.

---

## Future Improvements

1. Build provider adapters for AKS, EKS, GKE and self-managed clusters.
2. Continuously inventory add-ons and warn before versions become unsupported.
3. Integrate GitOps and Helm repositories for source-manifest scanning.
4. Add Prometheus/audit-log API-usage detection.
5. Maintain a versioned compatibility knowledge base with source citations.
6. Generate a pull request for safe manifest migrations.
7. Add a staging rehearsal pipeline and automated conformance/smoke tests.
8. Model node drain using scheduler constraints and current capacity.
9. Compare pre/post-upgrade SLOs and automatically assemble evidence.
10. Add signed approvals, exceptions, expiry and assessment audit history.

---

## Common Interview Follow-Up Questions

### Why use AI for a Kubernetes upgrade?

An upgrade produces a large, cross-component evidence set. AI helps compare and explain it, but predictable rules and official documentation decide compatibility. This reduces manual reading without allowing the model to invent support.

### Can AI approve the upgrade automatically?

No. It can generate a recommendation. Predictable blockers, provider policy, staging evidence and a platform engineer's change approval determine whether execution proceeds.

### Why check every intermediate version?

APIs, defaults and supported version-skew can change at each minor release. A direct source-to-target comparison may miss a required migration or unsupported upgrade hop.

### How do you find deprecated APIs accurately?

I combine a versioned removal database, repository/Helm manifest scanning, live discovery and API-request metrics or audit logs. Live YAML alone can be misleading because the API server converts objects to a served version.

### What is the highest-risk area?

It depends on the cluster. Common high-risk areas are unsupported operators, admission webhooks that fail closed, CRD conversion, CNI/CSI incompatibility and workloads that cannot move during node drain.

The assessment uses evidence rather than assuming one universal answer.

### What if an operator has no compatibility matrix?

I contact the owner/vendor, inspect release and test evidence, and rehearse it against the target. Until verified, I report an unknown risk and reduce confidence; I do not mark it compatible.

### How would you upgrade with minimum downtime?

I ensure spare capacity and multiple replicas, correct PDBs and topology spread, upgrade the control plane first where required, then drain and replace nodes in small batches, validating service health after each batch. Stateful and singleton workloads receive specific runbooks.

### What is the difference between readiness and confidence?

Readiness describes the severity of risks discovered. Confidence describes how completely we checked the cluster. A cluster may have few known risks but low confidence because important controllers or namespaces were inaccessible.

### Would you automatically fix removed APIs?

I can generate a reviewed Git pull request, but I would not modify live production resources blindly. The migration needs schema validation, controller support, testing and normal GitOps/change approval.

### What happens if the upgrade fails?

I stop at the defined gate, preserve evidence, restore traffic or capacity using the prepared recovery method, and follow provider-specific recovery. I do not assume a control-plane downgrade is supported.

---

## Honest Closing Statement

> This project shows how I would use AI to improve a Kubernetes platform task without giving AI unsafe control. The system gathers read-only evidence, verifies compatibility against authoritative sources, uses predictable logic for technical gates, and uses AI to compare and explain risks. The supplied repository is an assessment design, so I would describe it as designed or prototyped until I have implemented the collector, evaluated it with known failure scenarios, rehearsed an upgrade and recorded real results.
