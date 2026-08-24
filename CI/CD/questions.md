## 1. Explain your CI/CD pipeline design. Why did you choose those tools?

**Answer:**

I walk through the whole value stream, end to end:

```text
pull request → build/unit test → quality/security gates → immutable artifact
             → staging deploy → integration/smoke test → approval
             → progressive production deploy → SLO verification → rollback
```

Source code and pipeline definitions both live in Git. CI produces one signed, versioned artifact and stores it in a registry. "Immutable" here means that artifact never changes once it's built — every environment gets the exact same bits.

CD promotes that same artifact through each environment. It never rebuilds per environment. Secrets come from workload identity or a secret manager, not from config files.

Production runs behind protected environments with a deployment identity that has least privilege — only the access it actually needs — plus health gates and rollback.

I pick the tool based on the situation: GitHub Actions for GitHub-native teams, Azure Pipelines when the team is already in Azure DevOps, Jenkins when there's a real reason for heavy customization or legacy support, and Argo CD or Flux for pull-based Kubernetes delivery. I compare security, network access for runners, governance, availability, cost, team skills, and ongoing maintenance — not just popularity.

## 2. What CI/CD tools have you used?

**Answer:**

I explain where each tool fits and what I personally did with it.

For example: GitHub or Azure Repos for source control, Jenkins, GitHub Actions, or Azure Pipelines for CI orchestration, Maven or npm for builds, SonarQube for quality, Trivy and Checkov for security, Docker plus a registry for artifacts, Terraform for infrastructure, Helm for packaging Kubernetes apps, Argo CD for GitOps, and Prometheus and Grafana for verifying a deployment worked.

I don't claim expert-level with every tool. A convincing answer covers scale, environments, authentication, one pipeline I designed, one failure I investigated, how rollback worked, and a measurable improvement — like a shorter deployment time or a lower change-failure rate.

## 3. How do you build a Jenkins pipeline for multi-environment deployment?

**Answer:**

I build the artifact once, publish it, and keep it immutable. Environment configuration lives outside the artifact and gets parameterized in. Stages are: checkout, test, scan, publish, deploy and test to dev, approve and test in staging, then approve and deploy to production.

Environment credentials and values stay separate from each other and are protected. Shared pipeline libraries hold the common logic, while each application repo just supplies its own version and config. Production deploys the exact same digest that was already tested in staging.

I use environment locks, concurrency limits, timeouts, smoke tests, monitoring, and rollback to the previous artifact. Database changes follow the expand/migrate/contract pattern so they stay backward compatible.

If one environment fails, promotion to the next stops, and I keep the evidence and artifacts around for investigation.

## 4. What happens when a pipeline fails? Give a real example.

**Answer:**

The pipeline stops any dependent stages, records logs and reports, marks the commit status, and notifies the owner. I figure out whether the failure is in the code, the test, the scanner, the runner, the credentials, the artifact, the network, or the target environment.

I don't just rerun it blindly — that hides flaky behavior instead of fixing it.

One real example: Trivy blocked an image because of a critical OpenSSL vulnerability in the base image. I confirmed the CVE and which version fixed it, updated the pinned base image, rebuilt from a clean cache, rescanned, ran regression tests, and published a new immutable digest.

Production was never reached.

Afterward, we scheduled regular base-image updates, assigned ownership for vulnerability exceptions, started retaining SBOMs, and built a dashboard to track aging critical findings.

## 5. How do you integrate code-quality tools like SonarQube?

**Answer:**

I run unit tests and coverage first, then send the source and coverage data to SonarQube. The pipeline waits for the quality gate and blocks publication if the agreed thresholds aren't met.

The gate checks new-code bugs, vulnerabilities, coverage, duplication, and maintainability. I focus the gate on new code so legacy debt doesn't block adoption, and I set up a separate fix plan for older issues.

Tokens are stored securely, and I make sure the scanner and server versions are compatible.

I keep the report link on the pull request. If something's a false positive, it gets a reviewed exception with a reason and an expiry — developers don't just disable the rule. I also test the gate against a known failing branch to make sure it actually blocks.

## 6. What security tools and scans do you use in pipelines?

**Answer:**

I use layered controls:

- Secret scanning before or at commit
- SAST for source code
- Software composition analysis and license checks
- IaC and Kubernetes policy scanning
- Container image and SBOM scanning
- DAST against a deployed test environment
- Artifact and image signing, with verification at admission

Findings get prioritized by severity, exploitability, exposure, and environment. High-risk failures block promotion, and any exception needs an owner and an expiry date. Tools run with least privilege — only the access they need — and reports are checked to avoid leaking secrets.

Scanning alone isn't complete security. Protected branches, isolated runners, pinned dependencies and actions, workload identity, runtime monitoring, patching, and an incident response plan are all still necessary.

## 7. How do you manage code vulnerabilities?

**Answer:**

The flow is: discover, validate, prioritize, assign an owner and SLA, remediate or formally accept, rescan, then monitor. I confirm the package, version, and whether the vulnerable code path is actually reachable and used.

The fix might mean updating a library or base image, removing a package, adding a compensating control, or fixing the code directly.

I test for regressions, rebuild the artifact — keeping it immutable — and deploy it progressively. Any exception has to document the business reason, the compensating control, the approver, and an expiry date.

I track metrics like the age of open critical findings, time to fix, recurrence, and false-positive rate.

For an actively exploited issue, I identify which releases are affected, block new deployments, patch and rebuild, rotate any exposed secrets, watch for indicators of compromise, and keep people updated on status.

## 8. How do you prevent shared runners from blocking pipelines?

**Answer:**

I monitor queue time, executor utilization, job duration, disk space, and failure rate. Jobs get labels and resource classes so a heavy build doesn't starve a small test job. Runner pools autoscale with a max limit, and critical or protected jobs get their own isolated pool.

I set job timeouts, concurrency controls, fair scheduling, dependency caches, and ephemeral workspaces. A stuck job gets terminated safely, and retries are limited to failures known to be temporary.

Self-hosted runners get patched, capacity-tested, and cleaned between jobs.

If queue time spikes, I first check whether it's real demand, offline agents, slow image pulls, slow startup, or one runaway job — before just throwing more capacity at it.

## 9. How do matrix builds, caching, and concurrency limits help pipelines?

**Answer:**

Matrix builds test every supported combination of OS, runtime, and version in parallel. Caching avoids re-downloading the same dependencies every run. Concurrency limits stop unsafe parallel deployments or duplicate workflow runs on the same branch.

Cache keys include the dependency lock file and platform details. A build still has to work correctly with an empty cache, and untrusted branches shouldn't be able to poison a protected cache.

Artifacts and caches are different things: artifacts are versioned deliverables, caches are disposable speed optimizations.

For deployment, I only let one job be active per environment at a time, and I cancel outdated non-production runs. I track speed improvement, cache hit rate, runner cost, and flakiness, so optimizing for speed doesn't quietly reduce test coverage or reliability.

## 10. Explain a complete CD process.

**Answer:**

CD starts from an approved, versioned artifact. The system deploys it to a lower environment, runs schema and policy checks plus integration and smoke tests, then promotes that same digest through each protected environment.

Production uses rolling, canary, or blue-green delivery depending on the risk.

Health gates watch readiness, error rate, latency, saturation — meaning how close a resource is to its limit — and key business transactions. Every deployment record includes the artifact digest, configuration version, approver, and a link to the change. If any limit is exceeded, traffic stops or rolls back.

Database changes stay backward compatible and are kept separate from any destructive cleanup step. After deploying, I watch a defined observation window, complete the audit trail, and keep a tested failback path ready.

## 11. How do you roll back a faulty deployment?

**Answer:**

First I stop the rollout and decide whether rolling back is actually safer than fixing forward. For a stateless application, rollback just points traffic or the deployment controller back at the previous artifact, which stays immutable the whole time.

I check that the old configuration is still compatible, then run smoke tests and watch monitoring.

For canary or blue-green, I shift traffic back quickly. On Kubernetes, I might use a Helm revision or a Deployment rollback. Database and schema changes need their own recovery plan — rolling back the application can't undo a destructive migration.

I preserve the logs and the failed version, communicate status, confirm users have actually recovered, and run a root-cause analysis. Prevention might mean better probes, tighter canary thresholds, backward-compatible schemas, or an integration test we were missing.

## 12. How do you securely store secrets in CI/CD pipelines?

**Answer:**

I prefer OIDC or workload identity, so jobs get short-lived cloud credentials instead of long-lived keys. Other secrets live in Vault or a platform secret store, and only the protected job or environment that needs them can see them.

I make sure secrets never end up in Git, YAML, artifacts, cache, Docker layers, command arguments, or logs. Runners are isolated and ephemeral, permissions follow least privilege, and access and rotation get audited. Masking log output is a backup control, not the actual security boundary.

I test that forked or unprotected pipelines can't reach production secrets. If a secret does leak, I revoke and rotate it first, check audit logs and downstream access, remove any retained output, and fix the pipeline.

## 13. How do you migrate pipelines from one CI/CD tool to another?

**Answer:**

I inventory triggers, stages, runners, plugins, variables, secrets, artifacts, approvals, schedules, retention rules, and integrations. I separate the portable scripts from tool-specific syntax and map each control to the target platform.

I build one representative pipeline first, migrate secrets securely, recreate the protected environments and identities, then run the old and new pipelines in parallel — without letting both deploy to production. I compare artifact checksums, test results, duration, permissions, and audit evidence between them.

Cutover happens in a freeze or change window, with owner communication, a rollback plan to the old pipeline, and monitoring. I only decommission the old credentials and runners after things have run stably and any retention requirements are met.

## 14. How do you secure pipelines against supply-chain attacks?

**Answer:**

I protect source and pipeline changes with code review and branch policy. I pin third-party actions, images, and dependencies to specific versions. I restrict runner egress and permissions, isolate untrusted builds, use short-lived identity, and block secrets from reaching fork jobs.

Builds generate SBOMs, scan dependencies, images, and IaC, and sign artifacts using a protected identity. Deployment checks the signature and provenance — meaning where the artifact came from and how it was built — and only deploys artifacts by their fixed digest. Registries are protected and audited.

I review transitive dependencies, runner images, who owns each plugin or action, and the artifact promotion path. My incident plan covers revoking signing credentials, blocking compromised artifacts, identifying which versions are deployed, rebuilding from trusted sources, and rotating any affected secrets.

## 15. How do you manage parallel builds and artifacts?

**Answer:**

Independent tests and services run in parallel with explicit dependencies between them. Each job writes to its own workspace and uses fixed version identifiers, so outputs can't overwrite each other.

A fan-in job collects the reports and decides whether publication is allowed.

Artifacts carry checksums, a version or commit reference, a retention policy, and access controls. I publish once and promote that same artifact — I don't rebuild it per environment. Cache is kept separate and disposable.

Concurrency limits protect shared test systems and deployment environments. I test partial job failure, missing artifacts, retries, and cancellation. Monitoring queue time and duration shows whether parallelism is actually helping, or just moving the bottleneck downstream.

## 16. How do you implement zero-downtime deployments in Jenkins or GitHub Actions?

**Answer:**

The pipeline picks rolling, blue-green, or canary delivery. The workload needs multiple replicas spread across failure domains — groups of resources that could fail together — realistic readiness and startup probes, enough spare capacity, graceful shutdown, and connection draining.

New versions need backward-compatible APIs, config, and database schema.

The pipeline deploys to a small slice first, runs smoke and synthetic tests, and watches error rate, latency, saturation, and business metrics. Traffic only increases once those checks pass. If they decline, it stops and routes back to the previous version.

I load-test the strategy itself and simulate a failed readiness check and a rollback. "Zero downtime" is an availability goal that the architecture has to support — adding a deploy command alone doesn't guarantee it.

## 17. What SAST and DAST tools do you prefer?

**Answer:**

SonarQube, CodeQL, Checkmarx, and Semgrep are common SAST tools. OWASP ZAP and Burp Suite Enterprise are common DAST tools. The right choice depends on languages, framework support, accuracy, CI integration, compliance needs, and who owns the tool.

SAST runs early against source code. DAST tests a running, authorized, non-production target, and needs its rate and scope controlled. I combine both with dependency, secret, IaC, container, and runtime controls.

I tune the rules, keep evidence, set severity gates with expiring exceptions, and track the true-positive and fix rate. No single scanner proves an application is secure.

## 18. How do you manage a ServiceNow task assigned to you?

**Answer:**

I read the category, impact, urgency, SLA, requester, evidence, dependencies, and any approval requirements. I restate the expected outcome and ask focused questions if something's unclear. I prioritize by user and business impact and the SLA — not just the order tickets arrived in.

I document investigation timestamps, the commands and results I ran (without secrets), the changes made, validation steps, and communication. Risky changes go through change control with a rollback plan.

If I'm blocked, I update the ticket with the owner, the reason, the next action, and an expected time — I don't leave it silent.

I only close a ticket once the requester or a defined test confirms success. I link related incident, problem, or change records, and write a knowledge article or automation if the issue is likely to repeat.

## 19. How do you make CI/CD pipelines auditable for compliance?

**Answer:**

Pipeline definitions and infrastructure code are version-controlled and reviewed. Protected branches and environments, identities with least privilege, separation of duties, and immutable artifacts all build in traceability.

For every release I retain the commit, the pull request and its reviewers, test/scan/policy results, the artifact's digest/signature/SBOM, approvals, deployment logs, the environment and config version, and the verification or rollback result. Logs follow a defined retention period and sit in tamper-resistant storage with restricted access.

I map this evidence to the actual control requirements, and I test that emergency or bypass paths are still audited. Good compliance automation makes the approved path the easy path — manual screenshots are fragile and easy to miss things with.

## 20. A CI/CD pipeline takes 30–60 minutes. How would you reduce it to under five minutes?

**Answer:**

I measure before optimizing. Stage timestamps, queue time, executor utilization, cache hit rate, artifact transfer time, Docker layer timings, test reports, and external API latency show whether the real bottleneck is waiting, checkout, installing dependencies, compiling, testing, scanning, building the image, or deploying.

I compare a fast run and a slow run from the same commit, and I don't just start cutting quality checks to save time.

Then I apply targeted fixes: shallow or sparse checkout, dependency caches keyed to the lockfile, BuildKit layer caching, a smaller build context, incremental compilation, parallel independent jobs, test splitting based on historical duration, and pre-warmed ephemeral agents close to the registry.

In a monorepo, services that didn't change can be skipped, as long as the dependency mapping is reliable.

Unit and static checks run first so failures show up fast. Integration and security suites run in parallel, with enough isolated capacity to support that.

Getting under five minutes may not be realistic for every full production qualification. Instead, I aim for a fast commit-feedback path, while still running the broader required tests before promotion — or continuously, against that same artifact.

I verify the cache is actually correct, run periodic clean builds, track p50/p95 duration and flakiness, and make sure speed improvements never weaken security or reproducibility.

## 21. How do you design rollback so it still works when the deployment stage itself fails?

**Answer:**

I design rollback before deployment even happens, and it runs from a separate, protected recovery path — not just as the next command in a job that already failed. I store the last known-good artifact — image, chart, or config version — and its deployment metadata outside the agent's own workspace.

The deployment system uses timeouts and `post`/`finally` handling, but an operator or an automated health controller can also trigger a dedicated rollback job with its own independent credentials.

On Kubernetes I use a Git revert, a Helm rollback, or a progressive-delivery controller. For VM deployments, I keep the previous package or image around and rotate traffic back to it. Database changes use the expand-and-contract pattern, because rolling back application code can't undo an incompatible, destructive schema change.

The recovery workflow is idempotent, meaning it's safe to run more than once. It's also scoped to one environment, audited, and gated by approval for production.

I test failure at checkout, artifact download, partial rollout, health check, and notification stages. After a rollback, I verify the real customer transaction, error and latency metrics, the version running on every instance, database compatibility, and any queue or background workers.

Then I preserve the evidence and fix the failed release properly, rather than just retrying it over and over.

## 22. How do you implement multi-environment CI/CD while preventing configuration drift?

**Answer:**

I build one artifact and promote that same digest through Dev, QA, UAT, and Production. Environment differences are explicit, schema-validated values stored in version control or an approved config/secret service — never copied pipeline logic or manually edited servers.

Reusable pipeline templates and infrastructure modules give everyone one shared process, and protected environment files hold only the justified differences.

Infrastructure and application config both go through plan/diff checks, GitOps reconciliation where it fits — meaning the actual state is automatically brought back in line with the desired state — and scheduled drift detection. Production gets stronger approval and credentials, but it never runs a different, untested script.

Secrets are referenced by identity and path, never copied between environments. Database and feature changes stay backward compatible throughout the promotion.

Before deploying, I compare desired state against live state. Afterward, I record the artifact, config commit, infrastructure version, and policy results, and run smoke tests. Break-glass changes expire and have to be reconciled back into code.

This makes drift visible, without pretending every environment has identical capacity or integrations.

## 23. A team deploys 50 times per day. How do you maintain stability without slowing releases?

**Answer:**

I make every change small, independently testable, observable, and reversible. Trunk-based development or short-lived branches, required automated tests, static and security policy checks, immutable artifacts, and reliable ephemeral test environments all give fast feedback.

High-risk code gets separated from the release itself using feature flags, with clear ownership and an expiry date.

Deployment uses canary or progressive rollout, with automated analysis of error rate, latency, saturation, and business metrics, and automatic pause or rollback. Changes keep backward-compatible APIs and expand-and-contract database migrations.

Service ownership, SLOs, error budgets, runbooks, and on-call readiness decide when the release rate is actually safe. A depleted error budget can mean pausing for reliability work — but that shouldn't become a permanent manual gate.

I track change failure rate, lead time, deployment frequency, recovery time, flaky tests, and rollback success. Delivery is fast and stable when the pipeline catches bad changes early and production limits the blast radius — not when reviews or tests get skipped.

## 24. Is it acceptable to deploy a critical banking application directly to production without automated testing because the developer is confident and time is limited? (True or False)

**Answer:**

False. Confidence isn't evidence, and time pressure actually increases the need for controlled risk, not less.

A critical banking change needs traceability, separation of duties, security and regulatory controls, repeatable tests, an approved artifact, a rollback plan, and post-deployment verification. Deploying untested code directly can cause financial loss, data-integrity problems, security exposure, and a change nobody can audit afterward.

For a genuine emergency, I'd use an approved break-glass process instead: define the incident and the smallest safe change, get it peer-reviewed, run the fastest relevant automated checks, back up affected state, deploy it as a canary or in a tightly scoped way, prepare the rollback, record who authorized it, and monitor real business transactions.

Any lower-priority tests that got skipped run immediately afterward, and the emergency path itself gets reviewed.

Emergency governance can move faster — but it's still governance, not the absence of it.

## 25. A deployment works in staging but fails in production. What differences do you compare?

**Answer:**

I compare the exact artifact digest and configuration commit first — rebuilding between environments would make this investigation unreliable.

Then I check identity and permissions, secret names and versions, network routes and firewall policy, DNS and certificates, database schema and data volume, feature flags, external endpoints, quotas, resource limits, replica counts, region or zone, runtime versions, admission policies, and any production-only proxy or service mesh.

I preserve the production error, deployment events, logs, metrics, traces, and an audit of what changed, then reproduce the issue with production-like configuration while keeping sensitive values protected. I avoid making random manual changes while investigating.

If the impact is still active, I pause or roll back and confirm recovery before testing any fix.

The long-term fix is environment parity where it's practical, explicit versioned differences where it isn't, promoting one immutable artifact everywhere, testing with production-like load and policy, validating the config schema, running preflight dependency checks, and detecting drift.

## 26. A deployment succeeded, but traffic still reaches the old version. Where do you start?

**Answer:**

First I verify the actual deployed artifact digest, the workload revision, and the real Pod or container image — I don't just trust a "success" message.

Then I trace the request path: DNS and CDN cache, the load balancer or ingress routing, the service selector and EndpointSlices, readiness, the rollout strategy and its traffic weights, service-mesh routing, and client or browser cache.

Common causes are a mutable tag resolving to something unexpected, a deployment template that never actually changed, old endpoints still marked ready, canary or blue-green routing still weighted toward the old revision, cache TTL, or a deploy that went to the wrong cluster or namespace.

I capture evidence, make the smallest reversible fix to routing or rollout, and confirm live requests are hitting the new version — using version headers or metrics — before closing the incident.
