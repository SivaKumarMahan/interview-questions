# AI-Assisted Terraform Drift Detector

## Important Accuracy Note

Unlike the earlier design-only projects, the supplied reference folder contains an implemented Go application with a CLI, REST API, dashboard, scheduler, state readers, AWS collectors, drift engine, SQLite persistence and unit tests.

However, the current code is a **predictable Terraform drift detector**. It contains no LLM dependency, AI API call, prompt builder, retrieval system or AI-output validator. To describe it honestly in an interview:

- I can say **“I implemented/prototyped a Terraform drift detection engine in Go.”**
- I can say **“I designed an AI-assisted explanation and fix layer as the next stage.”**
- I should not say the supplied code already uses AI.
- I should call it production-ready only after resolving the limitations listed below and running security, scale and live-cloud tests.

The Go toolchain was unavailable in the current review environment, so the existing automated tests could not be executed here. The implementation and tests were reviewed statically.

---

## One-Line Project Explanation

I built a Go service that compares Terraform's expected state with live AWS resources, detects missing resources and configuration changes, stores scan history and supports CLI, API, dashboard and scheduled execution; I then designed an AI layer to explain verified drift and propose safe, reviewable fix.
---

## 30-Second Interview Answer

> I developed a Terraform drift detector in Go. It reads a local, HTTP or S3 Terraform state file, extracts managed AWS resources into a common resource model, fetches their live configuration through the AWS SDK and compares expected attributes and tags with actual values. It reports missing resources, changed attributes and tag differences through a CLI, REST API and dashboard, stores scan history in SQLite, and can run scans on a cron schedule. The predictable engine remains the source of truth. My AI extension consumes only verified findings to explain impact, rank risk and draft Terraform-based fix, but it cannot run `terraform apply` or make cloud changes. During review I also identified important gaps, including incomplete discovery of cloud-only resources and unsafe handling of partial provider failures, which I would fix before production use.

---

## Two-Minute Interview Explanation

Terraform drift occurs when real infrastructure no longer matches the state Terraform expects. For example, somebody may change an EC2 instance type in the AWS console, remove a security-group rule, delete a managed resource, or alter tags outside the normal pull-request workflow.
The application has two input paths:

1. The state reader loads raw Terraform state from a local file, HTTP endpoint or S3 object.
2. The AWS provider fetches the current configuration of supported resources through AWS SDK v2.

The extractor converts state objects into a canonical resource containing provider, type, cloud ID, selected attributes, tags and region. The live collector produces the same shape.

The comparison engine indexes resources by canonical ID, checks presence, compares normalized attributes, compares tags after applying ignore rules, and creates a structured report.

Users can run an ad-hoc scan with the Cobra CLI, call the REST API, view results in a small web dashboard, or configure cron scans. Workspaces, schedules and reports are stored in SQLite.

Exit codes make the CLI useful in CI: `0` means no drift, `1` means drift and `2` means an execution error.

The AI portion is intentionally downstream. It never decides whether raw values differ.

It takes predictable findings and supporting context, explains operational impact, groups related changes and drafts a fix plan. A human reviews the proposal and fixes the cause through Terraform and the normal change process.

---

## Problem, Goal and Value

### Problem

- Engineers can make emergency or accidental console changes outside Terraform.
- Cloud services can change through another automation system.
- A deleted resource may remain in state until the next Terraform operation.
- Running `terraform plan` continuously can require working configuration, providers, variables and credentials.
- Teams need history, ownership and alerting rather than discovering drift during deployment.

### Goal

Continuously compare the expected infrastructure recorded in Terraform state with live cloud configuration and produce a focused, auditable report without automatically changing infrastructure.

### Business and operational value

- Detect unauthorized or accidental infrastructure changes earlier.
- Prevent unexpected changes from appearing first during a deployment.
- Identify possible security and compliance deviations.
- Give the owning team clear evidence and a repeatable fix flow.
- Track drift frequency, age and recurrence across workspaces.

---

## Implemented Architecture

```text
Terraform state
 local | HTTP | S3
       │
       ▼
State Reader -> State Extractor -> Expected Resources ─┐
                                                       │
AWS SDK -> Resource Fetchers -> Actual Resources ──────┤
                                                       ▼
                                              Drift Engine
                                                       │
                                                       ▼
                                                Drift Report
                              ┌──────────────────┬──────┴───────┐
                              ▼                  ▼              ▼
                           CLI/table          REST API       SQLite
                                                               │
                                                               ▼
                                                  dashboard + scheduler
```

### Proposed AI extension

```text
Verified drift report + policy + ownership context
                         │
                         ▼
              redaction and evidence builder
                         │
                         ▼
               AI explanation/remediation
                         │
                         ▼
             schema, citation and command validator
                         │
                         ▼
                 human-reviewed recommendation
```

The AI extension does not replace the comparison engine and is not present in the reviewed source code.

---

## Technology Stack

| Area | Technology | Purpose |
| --- | --- | --- |
| Language | Go | Fast single-binary CLI/service and strong concurrency support |
| CLI | Cobra | `scan`, `report`, `workspace` and `schedule` commands |
| Cloud access | AWS SDK for Go v2 | Fetch EC2, VPC, subnet, security-group and S3 data |
| State backends | Filesystem, HTTP(S), AWS S3 | Load expected Terraform state |
| Configuration | YAML | Database, API, workspaces, regions and ignore rules |
| API | Go `net/http` | REST endpoints and static dashboard serving |
| Scheduler | robfig/cron | Periodic workspace scans |
| Persistence | SQLite | Workspaces, schedules and scan reports |
| Frontend | HTML, CSS and vanilla JavaScript | Simple workspace and report dashboard |
| IDs | Google UUID | Unique workspace and scan identifiers |
| Proposed AI | Approved LLM with structured output | Explain and prioritize verified findings |

---

## Repository Components and Responsibilities

```text
cmd/driftctl/                 CLI entry point
cmd/drift-server/            API/server entry point
internal/state/              State readers and Terraform-state extraction
internal/providers/aws/      AWS live-resource collectors
internal/drift/              Predictable comparison engine
internal/scan/               End-to-end scan orchestration
internal/store/              SQLite persistence interface/implementation
internal/scheduler/          Cron registration and scheduled scans
internal/api/                REST API, auth middleware and dashboard
internal/output/             JSON and table formatting
internal/model/              Canonical resources, findings and reports
web/                         Static dashboard
testdata/                    Sample Terraform state
```

The provider registry allows another cloud provider to implement a common `CloudProvider` interface and be registered without rewriting the scanner.

---

## End-to-End Scan Flow

### 1. Resolve the workspace

A scan can use a named YAML/SQLite workspace or ad-hoc flags:

```bash
driftctl scan \
  --state /path/to/terraform.tfstate \
  --provider aws \
  --region us-east-1 \
  --output json
```

The workspace defines the provider, state backend, regions, ignored tags/attributes and optional cron expression.

### 2. Create the scan record

The scanner generates a UUID, records the start time and saves a `running` report before external work begins. This provides an audit entry even if collection later fails.

### 3. Read Terraform state

The reader supports:

- local file through `os.ReadFile`
- HTTP(S) through an HTTP GET
- S3 through `GetObject`

The extractor parses version-4 Terraform state JSON and ignores data sources because it processes only resources with `mode: managed`.

### 4. Normalize expected resources

Each expected resource becomes:

```json
{
  "id": "aws/aws_instance/i-0123456789abcdef0",
  "provider": "aws",
  "type": "aws_instance",
  "cloud_id": "i-0123456789abcdef0",
  "name": "web-server",
  "region": "us-east-1",
  "source": "state",
  "attributes": {
    "instance_type": "t3.micro",
    "ami": "ami-...",
    "subnet_id": "subnet-...",
    "monitoring": false
  },
  "tags": {"Name": "web-server", "env": "prod"}
}
```

Comparison keys are resource-specific. This avoids comparing computed Terraform-only attributes that would create noise.

### 5. Fetch actual AWS configuration

The current provider supports:

- `aws_instance`
- `aws_vpc`
- `aws_subnet`
- `aws_security_group`
- `aws_s3_bucket`

It derives regions from configuration and state, loads AWS's default credential chain and fetches regions concurrently. Provider-specific functions translate AWS SDK responses into the same canonical resource shape.

### 6. Compare expected and actual state

The engine indexes both lists by canonical resource ID and detects:

| Finding | Meaning |
| --- | --- |
| `missing_in_cloud` | State expects the resource, but live collection did not return it |
| `extra_in_cloud` | Live collection returned a resource that state did not contain |
| `attribute_changed` | A selected expected value differs from live configuration |
| `tags_changed` | A non-ignored tag was added, removed or changed |

Values are JSON-normalized before comparison to reduce differences caused only by Go numeric types or nested representations.

### 7. Store and present the report

The report includes status, times, counts, findings and collection errors. It is persisted in SQLite and rendered as JSON or a terminal table. The web dashboard lists workspaces, starts scans, displays history and opens detailed reports.

### 8. Return CI-friendly exit status

```text
0 -> scan completed with no findings
1 -> drift findings exist
2 -> command or scan error
```

This allows a pipeline to warn, create a ticket or block a promotion according to team policy.

---

## Drift Detection Example

Assume state expects:

```text
EC2 i-123
instance_type = t3.micro
env tag = prod
```

Live AWS returns:

```text
EC2 i-123
instance_type = t3.small
env tag = staging
```

The predictable findings are conceptually:

```json
[
  {
    "kind": "attribute_changed",
    "field": "instance_type",
    "expected": "t3.micro",
    "actual": "t3.small",
    "severity": "warning"
  },
  {
    "kind": "tags_changed",
    "field": "tags.env",
    "expected": "prod",
    "actual": "staging",
    "severity": "info"
  }
]
```

The AI layer can then add context without changing the facts:

```text
The instance was resized outside Terraform. Confirm whether this was an
approved emergency change. If the larger size is required, update Terraform
code and review a plan. Otherwise, use Terraform to restore the expected size
during an approved window. The environment-tag change may affect cost,
ownership or policy reporting and should be confirmed with the resource owner.
```

---

## CLI, REST API and Scheduling

### CLI examples

```bash
driftctl scan --config configs/driftctl.yaml --workspace prod
driftctl report <scan-id> --output table
driftctl workspace list
driftctl schedule create --workspace prod --cron "0 6 * * *"
```

### REST endpoints

```text
GET    /health
GET    /api/v1/workspaces
POST   /api/v1/workspaces
GET    /api/v1/workspaces/{id}
DELETE /api/v1/workspaces/{id}
POST   /api/v1/workspaces/{id}/scans
GET    /api/v1/workspaces/{id}/scans
GET    /api/v1/scans
GET    /api/v1/scans/{id}
GET    /api/v1/scans/{id}/report
PUT    /api/v1/workspaces/{id}/schedules
DELETE /api/v1/workspaces/{id}/schedules
```

The reviewed API optionally protects endpoints with one configured API key. This is acceptable only for a limited prototype; production needs identity-based authentication, authorization by workspace, secret rotation and audit logging.

### Scheduled scans

At server startup, configured workspaces and schedules are stored, loaded into the cron scheduler and executed in the background. Scan history allows the team to see whether drift is new, recurring or unresolved.

---

## How AI Should Be Added

### AI input

Only a minimized, structured payload should be sent:

```json
{
  "workspace": "prod",
  "scan_id": "...",
  "findings": [],
  "resource_criticality": {},
  "change_policy": {},
  "recent_approved_changes": []
}
```

Terraform state must not be sent wholesale because it can contain credentials, passwords, private endpoints and other sensitive values.

### AI output contract

```json
{
  "summary": "...",
  "groups": [
    {
      "finding_ids": ["..."],
      "probable_cause": "...",
      "impact": "...",
      "priority": "high",
      "evidence": ["..."],
      "recommended_action": "...",
      "verification": ["..."],
      "confidence": 0.82
    }
  ]
}
```

Pydantic, JSON Schema or Go validation rejects unsupported priorities, unknown finding IDs and missing evidence.

### Appropriate AI responsibilities

- explain drift in simple language
- compare several related findings
- use ownership/change context to suggest a probable cause
- prioritize investigation based on resource criticality
- draft a ticket, incident note or pull-request description
- propose verification and rollback steps

### Predictable responsibilities

- read and parse state
- fetch live cloud values
- compare resource identity, values and tags
- determine whether collection was complete
- apply ignore rules
- enforce severity policy
- decide pipeline exit code
- authorize and execute any infrastructure change

### Human-controlled fix

The preferred fix is a reviewed Terraform change:

```text
Verified drift
  -> identify whether cloud or code is correct
  -> update Terraform configuration or import/state workflow if needed
  -> terraform fmt and validate
  -> review terraform plan
  -> peer/change approval
  -> terraform apply
  -> re-run drift scan
```

The model must never directly run `terraform apply`, edit state, delete a resource or accept a suggested command as safe without review.

---

## Important Findings from the Code Review

These limitations should be mentioned honestly if an interviewer asks what I would improve.

### 1. Cloud-only resources are not discovered in live scans

The current AWS fetchers receive expected resources and call APIs using only those resource IDs. Therefore a resource created manually in AWS but absent from Terraform state is never fetched.

Although the comparison engine supports `extra_in_cloud`, the live collector normally cannot produce that finding.

**Fix:** enumerate all supported resources in the configured account/region and then compare them with state. Add explicit scope, ownership tags and ignore rules to avoid treating every unrelated account resource as drift.

### 2. Partial collection failures can create false “missing” drift

The scanner records provider errors but can still mark the scan `completed` and compare an incomplete actual list. A permission, throttling or regional API failure can therefore make healthy resources appear deleted.

**Fix:** track collection completeness by provider/type/region. Never emit absence findings for a failed scope. Mark the report `partial` or `failed`, and distinguish `not found` from `not observed`.

### 3. Unsupported resource types can be reported incorrectly

State extraction can produce types that the AWS provider does not fetch. Such expected objects have no actual match and can look missing.

**Fix:** intersect state resources with `SupportedTypes`, report unsupported types separately, and exclude them from missing-resource comparison.

### 4. Some normalized attributes are not equivalent

The VPC fetcher sets DNS attributes to `nil` instead of querying them. S3 also uses `nil` for values such as ACL or `force_destroy`, and live/state shapes may differ. These can create false attribute changes.

**Fix:** implement complete provider-specific reads and canonical converters with golden fixtures for both Terraform-state and SDK response shapes.

### 5. State-only mode intentionally reports every resource missing

With `--skip-cloud`, actual resources are empty, so all state resources are classified as missing. This tests orchestration but should not be presented as a meaningful drift scan.

**Fix:** name it validation/test mode, skip comparison, or provide a fixture for actual cloud resources.

### 6. Missing-resource severity is always critical

The current helper returns critical whether or not the `env` tag is production.

**Fix:** use explicit, configurable severity policy based on environment, resource type, criticality and ownership rather than a hard-coded result.

### 7. State readers require stronger security controls

An API-created workspace can point to a local path or HTTP URL. Without validation this creates arbitrary-file-read and server-side request-forgery risk. State content itself may contain secrets.

**Fix:** allow-list backend types and paths/hosts, block private/metadata endpoints, enforce response-size and time limits, encrypt state access, avoid logging state, and use least-privilege (minimum required access) state credentials.

### 8. API authentication is prototype-level

One optional shared API key protects all resources. If no key is configured, all API routes are open; if a key is configured, the current browser JavaScript does not attach it.

**Fix:** add OIDC/JWT authentication, workspace RBAC, CSRF/CORS controls where relevant, secure headers, rate limits and a frontend login/session flow.

### 9. Scans and schedules need production controls

API-triggered scans are synchronous, scheduled scans use an unlimited background context, and overlapping schedules are not prevented.

**Fix:** use a durable job queue, per-scan timeout/cancellation, idempotency (safe repeat behavior), concurrency limits, distributed scheduling/locking, retry policy and progress/status APIs.

### 10. Persistence needs relational integrity and retention

SQLite is useful for a local prototype, but workspace deletion does not visibly enforce foreign keys/cascade behavior and report growth has no retention policy.

**Fix:** define migrations, foreign keys, indexes, retention, backup and multi-user storage such as PostgreSQL for a deployed service.

---

## Investigation and Fix Scenarios

### Scenario 1: Resource is missing in cloud

My approach:

1. Confirm the scan was complete and AWS returned an authoritative not-found result.
2. Check CloudTrail and approved change records to identify who or what deleted it.
3. Determine whether Terraform state is stale or the resource must exist.
4. Check dependencies, backups, data implications and recovery requirements.
5. Run `terraform plan` with the correct configuration and variables.
6. Review whether recreation is safe, especially for stateful resources.
7. Apply through normal approval and rescan.

### Scenario 2: Attribute changed outside Terraform

1. Compare expected and actual values.
2. Check whether the console change was an approved emergency action.
3. Decide which value represents desired state.
4. If cloud is correct, update Terraform code and review the plan.
5. If state/code is correct, use Terraform to restore the resource during an approved window.
6. Validate service health and rescan.

I do not blindly force the cloud back to state because the manual change may have been made to resolve an incident.

### Scenario 3: Security-group rule drift

This may be security-sensitive. I normalize rule ordering before comparison, confirm collection completeness, identify an overly broad or missing rule, check CloudTrail and ownership, assess exposure, and follow the incident/change process.

The fix belongs in Terraform so the desired security policy remains reproducible.

### Scenario 4: Recurring tag drift

I check whether another policy engine or automation owns tags. If so, Terraform and that automation have conflicting ownership.

I define a single source of truth or ignore only the explicitly externally managed tag, document the exception and avoid hiding unrelated tag drift.

### Scenario 5: Scan suddenly reports many missing resources

I first suspect collection failure rather than mass deletion. I inspect scan errors, credentials, AWS API throttling, region selection and permissions. Absence is trustworthy only when the collector successfully enumerated the relevant scope.

---

## Security and Safety Measures

- Use a read-only AWS role for detection.
- Separate state-read permissions from live-resource discovery.
- Encrypt Terraform state and scan history at rest and in transit.
- Never log or send raw state to AI.
- Redact sensitive attributes and hash identifiers where possible.
- Validate state backend locations and block SSRF/local-path abuse.
- Restrict AWS account, organization, regions and resource scope.
- Use OIDC/short-lived credentials instead of static keys.
- Authenticate users and authorize every workspace/report.
- Sign or version comparison policy and ignore rules.
- Record collection errors so missing evidence is not presented as drift.
- Keep AI and fix credentials separate; AI receives no cloud credentials.
- Require reviewed Terraform plans and approvals for changes.
- Retain an audit trail of scans, acknowledgements and exceptions.

---

## Testing Strategy

### Existing tests in the reference

The repository includes tests for:

- missing, extra, attribute and tag comparison
- critical missing-resource severity
- sample state extraction
- scan persistence/orchestration in skip-cloud mode

These are useful unit tests, but they do not prove live AWS correctness or production safety.

### Tests I would add

- golden tests for each Terraform/AWS canonical converter
- ordering and set normalization for security groups and lists
- partial collection versus confirmed not-found behavior
- unsupported resource-type handling
- real discovery of extra cloud resources
- multi-region S3 behavior and deduplication
- permission denied, throttling, pagination and retry cases
- HTTP backend SSRF, timeout and oversized response tests
- authentication, authorization and cross-workspace isolation
- scheduler overlap, cancellation and idempotency
- database migration, retention and recovery
- AI redaction, schema, hallucination and prompt-injection tests

### Live integration test

In an isolated AWS account:

1. Apply a small Terraform fixture.
2. Run a baseline scan and expect zero drift.
3. Change one attribute and tag through AWS APIs.
4. Delete one managed test resource.
5. Create one in-scope unmanaged resource.
6. Run a scan and verify exact findings.
7. Remove a permission and verify the result becomes incomplete, not false missing.
8. Restore through Terraform and confirm a clean scan.

The Go toolchain was not installed in the current workspace, so `go test ./...` could not be executed during this documentation task.

---

## CI/CD Integration

A pipeline can build and execute the scanner, then interpret the documented exit codes:

```yaml
- name: Run drift scan
  run: ./driftctl scan --config configs/driftctl.yaml --workspace prod --output json
```

Recommended policy:

- scheduled/nightly scans create reports and alerts
- pull-request plans remain the main change preview
- a scan error fails safely and is not interpreted as drift or no drift
- critical verified drift can block promotion
- informational tag drift may create a ticket instead
- reports are uploaded as artifacts without raw state or secrets

---

## Monitoring and Success Measures

### Service monitoring

- scan duration and completion rate
- AWS API latency, error and throttle rate
- number of resources by provider/type/region
- incomplete collection scopes
- scheduler delay and overlapping jobs
- database size and errors
- AI latency, cost, validation failures and unsupported claims

### Project outcomes

- time from drift creation to detection
- confirmed versus false-positive findings
- drift age and recurrence
- percentage remediated through reviewed Terraform changes
- number of unauthorized changes identified
- mean time to explain and assign drift
- percentage of resource types with verified collector coverage

I would not claim that drift detection alone prevented an outage. A defensible result connects a verified finding to a reviewed fix and measured reduction in recurrence or investigation time.

---

## Future Improvements

1. Correct collection completeness and false-missing behavior first.
2. Enumerate all in-scope supported cloud resources to detect extras.
3. Add pagination, retry/backoff (increasing wait between retries), rate limits and typed error classes.
4. Add Azure and GCP providers through the registry interface.
5. Support more AWS resources with tested canonical schemas.
6. Add remote-state locking/version metadata and snapshot hashes.
7. Move long scans to a durable queue with progress and cancellation.
8. Replace shared API key authentication with OIDC and RBAC.
9. Add notifications for Slack, email or incident/ticket systems.
10. Add the redacted AI explanation layer with structured output.
11. Generate reviewed Terraform pull requests, never direct applies.
12. Compare drift with CloudTrail and approved change records.
13. Add exception ownership, justification and expiry.
14. Use PostgreSQL/object storage for multi-user scale and retention.

---

## Common Interview Follow-Up Questions

### What is Terraform drift?

It is a difference between Terraform's expected managed state and the real infrastructure. It commonly happens through manual console changes, another automation tool, failed operations or changes outside the Terraform workflow.

### Why not just run `terraform plan`?

`terraform plan` is authoritative for a configured Terraform project and should remain part of the workflow. This detector focuses on continuous centralized scanning from state and cloud APIs, history and reporting without needing every working directory at scan time.

It complements rather than replaces plan.

### Is the Terraform state file the desired configuration?

It is the last recorded managed state, not always the full intended configuration. Current code, variables, provider behavior and pending changes may differ.

Therefore a finding is evidence for investigation, and fix is confirmed with the correct Terraform configuration and plan.

### How do you detect resources created manually in the cloud?

The collector must enumerate all in-scope resources of supported types and subtract the state index. The reviewed implementation does not yet do this because it fetches only expected IDs; I identified that as a required fix.

### How do you avoid false positives?

I use provider-specific canonical schemas, normalize unordered collections, ignore only documented computed/external fields, distinguish failed collection from confirmed absence, and test converters against real fixtures.

### Why use Go?

Go provides a single deployable binary, good concurrency for regional API calls, strong typing and mature cloud SDK support. It works well for both CLI and long-running service modes.

### Where exactly is AI used?

It is not in the supplied implementation. My proposed AI layer is downstream of predictable detection and explains impact, compares findings and drafts fix. It does not compare raw infrastructure or execute fixes.

### Would you automatically revert drift?

No. A manual change may be an approved incident action, and reverting it could cause an outage. I identify the correct desired state, review a Terraform plan and use the normal approval process.

### How do you secure Terraform state?

I use encrypted remote storage, least-privilege access, short-lived credentials, audit logging and no raw-state logging. Sensitive state is never sent wholesale to an LLM.

### What if AWS access fails during a scan?

The affected scope must be marked incomplete or failed. I do not interpret “not observed” as “deleted.” The reviewed code needs improvement in this area.

### How would you scale it?

I would use a job queue, horizontally scalable workers, account/region concurrency limits, distributed scheduling, PostgreSQL, object storage for evidence, pagination and cached provider metadata.

### What was the most important lesson from this project?

Drift accuracy depends more on collection completeness and canonical modeling than on the comparison loop. A simple equality check is easy; proving that two representations refer to the same resource and that missing data is authoritative is the difficult part.
---

## Honest Closing Statement

> I implemented a Go-based Terraform drift detector with state ingestion, AWS collection, normalized comparison, CLI/API/dashboard access, scheduling and scan history. The reviewed code is predictable, not yet AI-powered. My AI design adds evidence-based explanations and fix guidance after detection while keeping Terraform plans and human approvals in control. Before calling it production-ready, I would fix cloud-only discovery, incomplete-scan false positives, normalization gaps, state-backend security and production authentication, then validate it in an isolated live AWS environment.
