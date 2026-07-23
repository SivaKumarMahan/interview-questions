## 1. Explain your CI/CD pipeline design. Why did you choose those tools?

**Answer:**

I explain the complete value stream:

```text
pull request → build/unit test → quality/security gates → immutable artifact
             → staging deploy → integration/smoke test → approval
             → progressive production deploy → SLO verification → rollback
```

Source and pipeline definitions live in Git. CI produces one signed/versioned artifact and stores it in a registry. CD promotes that same artifact; it does not rebuild per environment. Secrets come from workload identity or a secret manager. Production uses protected environments, least-privilege deployment identity, health gates, and rollback.

I choose GitHub Actions for GitHub-native teams, Azure Pipelines for Azure DevOps integration, Jenkins for justified customization/legacy, and Argo CD/Flux for pull-based Kubernetes delivery. I compare security, runner network, governance, availability, cost, skills, and maintenance—not popularity.

## 2. What CI/CD tools have you used?

**Answer:**

I describe where each tool fits and what I personally did. Example: GitHub/Azure Repos for source, Jenkins/GitHub Actions/Azure Pipelines for CI orchestration, Maven/npm for build, SonarQube for quality, Trivy/Checkov for security, Docker and a registry for artifacts, Terraform for infrastructure, Helm for Kubernetes packaging, Argo CD for GitOps, and Prometheus/Grafana for verification.

I avoid claiming every tool as expert-level. A convincing answer includes scale, environments, authentication, one pipeline design, one failure investigation, rollback, and measurable improvement such as reducing deployment time or change-failure rate.

## 3. How do you build a Jenkins pipeline for multi-environment deployment?

**Answer:**

I build once, publish one immutable artifact, and parameterize environment configuration outside the artifact. Stages include checkout, test, scan, publish, dev deploy/test, staging approval/test, and production approval/deploy.

Environment credentials and values are separate and protected. Shared pipeline libraries implement standard logic; application repositories provide version and configuration. Production deployment consumes the same digest tested in staging.

I use environment locks/concurrency, timeouts, smoke tests, monitoring, and rollback to the previous artifact. Database changes follow backward-compatible expand/migrate/contract steps. If an environment fails, later promotion stops and evidence/artifacts are retained for investigation.

## 4. What happens when a pipeline fails? Give a real example.

**Answer:**

The pipeline stops dependent stages, records logs/reports, marks the commit status, and notifies the owner. I identify whether failure is code, test, scanner, runner, credentials, artifact, network, or target environment. I do not rerun blindly because that hides flaky behavior.

Example: Trivy blocked an image for a critical OpenSSL vulnerability in the base image. I confirmed the CVE and fixed version, updated the pinned base image, rebuilt from a clean cache, rescanned, ran regression tests, and published a new immutable digest. Production was never reached.

Preventive actions were scheduled base-image updates, ownership for vulnerability exceptions, SBOM retention, and a dashboard for aging critical findings.

## 5. How do you integrate code-quality tools like SonarQube?

**Answer:**

I run unit tests and coverage first, then send source/coverage to SonarQube. The pipeline waits for the quality gate and blocks publication if agreed thresholds fail.

The gate covers new-code bugs, vulnerabilities, coverage, duplication, and maintainability. I focus on new code so legacy debt does not make adoption impossible, while older issues have a remediation plan. Tokens are stored securely and scanner/server versions are compatible.

I retain the report link in the pull request. False positives use a reviewed exception with reason and expiry; developers do not simply disable the rule. I test the gate with a known failing branch.

## 6. What security tools and scans do you use in pipelines?

**Answer:**

I use layered controls:

- Secret scanning before/at commit
- SAST for source code
- Software composition analysis and license checks
- IaC/Kubernetes policy scanning
- Container image and SBOM scanning
- DAST against a deployed test environment
- Artifact/image signing and admission verification

Findings are prioritized by severity, exploitability, exposure, and environment. High-risk failures block promotion; exceptions require owner and expiry. Tools run with least privilege and reports avoid secret leakage.

Scanning is not complete security: protected branches, isolated runners, pinned dependencies/actions, workload identity, runtime monitoring, patching, and incident response remain necessary.

## 7. How do you manage code vulnerabilities?

**Answer:**

The flow is discover → validate → prioritize → assign owner/SLA → remediate or formally accept → rescan → monitor. I confirm package/version/reachability and whether the vulnerable path is used. The fix may update a library/base image, remove a package, add a compensating control, or correct code.

I test for regression, rebuild an immutable artifact, and deploy progressively. Exceptions document business reason, compensating controls, approver, and expiry. Metrics include open critical age, remediation time, recurrence, and false positives.

For an actively exploited issue I identify affected releases, block new deployments, patch/rebuild, rotate exposed secrets if relevant, monitor indicators, and communicate status.

## 8. How do you prevent shared runners from blocking pipelines?

**Answer:**

I monitor queue time, executor utilization, job duration, disk, and failure rate. Jobs use labels/tags and resource classes so heavy builds do not starve small tests. Runner pools autoscale with maximum limits; critical/protected jobs use isolated pools.

I set job timeouts, concurrency controls, fair scheduling, dependency caches, and ephemeral workspaces. Stuck jobs are terminated safely, and retry is limited to known transient failures. Self-hosted runners are patched, capacity-tested, and cleaned between jobs.

If queue time spikes, I inspect whether demand, offline agents, image pull, startup time, or one runaway job is responsible before simply adding capacity.

## 9. How do matrix builds, caching, and concurrency limits help pipelines?

**Answer:**

Matrix builds test supported OS/runtime/version combinations in parallel. Caching avoids repeated dependency downloads, while concurrency limits prevent unsafe parallel deployments or duplicate branch workflows.

Cache keys include dependency lock files and platform details. A build remains correct with an empty cache, and untrusted branches cannot poison protected caches. Artifacts are not caches: artifacts are versioned deliverables; caches are disposable optimization.

For deployment I allow only one active job per environment and cancel outdated non-production runs. I measure speed improvement, cache hit rate, runner cost, and flakiness so optimization does not reduce coverage or reliability.

## 10. Explain a complete CD process.

**Answer:**

CD begins with an approved, versioned artifact. The system deploys it to a lower environment, runs schema/policy checks, integration and smoke tests, then promotes the same digest through protected environments. Production uses rolling, canary, or blue-green delivery based on risk.

Health gates watch readiness, error rate, latency, saturation, and business transactions. Deployment records artifact digest, configuration version, approver, and change link. If limits are exceeded, traffic stops or rolls back.

Database changes are backward compatible and separated from destructive cleanup. After deployment I monitor through a defined observation window, complete audit evidence, and keep a tested failback path.

## 11. How do you roll back a faulty deployment?

**Answer:**

I first stop further rollout and determine whether rollback is safer than forward-fix. Stateless application rollback points traffic or the deployment controller to the previous immutable artifact. I validate configuration compatibility and run smoke tests plus monitoring.

For canary/blue-green I shift traffic back quickly. For Kubernetes I may use Helm revision or Deployment rollback. Database/schema/data changes need their own recovery; application rollback cannot undo destructive migration.

I preserve logs and the failed version, communicate status, verify user recovery, and perform RCA. Prevention may include better probes, canary thresholds, backward-compatible schemas, or a missing integration test.

## 12. How do you securely store secrets in CI/CD pipelines?

**Answer:**

I prefer OIDC/workload identity so jobs receive short-lived cloud credentials. Other secrets live in Vault or platform secret stores and are exposed only to the protected job/environment that requires them.

I prevent secrets in Git, YAML, artifacts, cache, Docker layers, command arguments, and logs. Runners are isolated and ephemeral, permissions are least privilege, and access/rotation are audited. Masking is a backup control, not the security boundary.

I test that fork/unprotected pipelines cannot access production secrets. On exposure I revoke/rotate first, inspect audit logs and downstream access, remove retained output, and correct the pipeline.

## 13. How do you migrate pipelines from one CI/CD tool to another?

**Answer:**

I inventory triggers, stages, runners, plugins, variables, secrets, artifacts, approvals, schedules, retention, and integrations. I separate portable scripts from tool-specific syntax and map each control to the target platform.

I implement a representative pipeline, migrate secrets securely, recreate protected environments and identities, and run old/new pipelines in parallel without both deploying production. I compare artifact checksums, tests, duration, permissions, and audit evidence.

Cutover uses a freeze/change window, owner communication, rollback to the old pipeline, and monitoring. I decommission old credentials/runners only after stable operation and retained evidence requirements are met.

## 14. How do you secure pipelines against supply-chain attacks?

**Answer:**

I protect source and pipeline changes with review/branch policy, pin third-party actions/images/dependencies, restrict runner egress and permissions, isolate untrusted builds, use short-lived identity, and prevent secrets from fork jobs.

Builds generate SBOMs, scan dependencies/images/IaC, and sign artifacts with a protected identity. Deployment verifies signature/provenance and uses immutable digests. Registries are protected and audited.

I review transitive dependencies, runner images, plugin/action ownership, and artifact promotion path. An incident plan covers revoking signing credentials, blocking compromised artifacts, identifying deployed versions, rebuilding from trusted sources, and rotating affected secrets.

## 15. How do you manage parallel builds and artifacts?

**Answer:**

Independent tests/services run in parallel with explicit dependencies. Each job writes to a unique workspace and uses immutable version identifiers so outputs cannot overwrite each other. A fan-in job collects reports and decides whether publication is allowed.

Artifacts include checksums, version/commit, retention, and access controls. I publish once and promote; I do not rebuild in every environment. Cache is separate and disposable.

Concurrency limits protect shared test systems and deployment environments. I test partial job failure, artifact absence, retry, and cancellation. Monitoring queue and duration shows whether parallelism helps or only moves contention downstream.

## 16. How do you implement zero-downtime deployments in Jenkins or GitHub Actions?

**Answer:**

The pipeline selects rolling, blue-green, or canary delivery. The workload needs multiple replicas across failure domains, realistic readiness/startup probes, resource capacity, graceful shutdown, and connection draining. New versions use backward-compatible APIs/config/database schema.

The pipeline deploys a small portion, runs smoke/synthetic tests, and monitors error, latency, saturation, and business metrics. Traffic increases only when gates pass. On degradation it stops and routes to the previous version.

I load-test the strategy and simulate failed readiness and rollback. “Zero downtime” is an availability objective supported by architecture; adding a deploy command alone cannot guarantee it.

## 17. What SAST and DAST tools do you prefer?

**Answer:**

Examples of SAST are SonarQube, CodeQL, Checkmarx, and Semgrep; DAST examples include OWASP ZAP and Burp Suite Enterprise. Tool selection depends on languages, framework support, accuracy, CI integration, compliance, and ownership.

SAST runs early on source; DAST tests a running, authorized non-production target and must be rate/scope controlled. I combine them with dependency, secret, IaC, container, and runtime controls.

I tune rules, preserve evidence, define severity gates and expiring exceptions, and measure true-positive/remediation rates. No single scanner proves the application is secure.

## 18. How do you manage a ServiceNow task assigned to you?

**Answer:**

I read category, impact, urgency, SLA, requester, evidence, dependencies, and approval requirements. I restate the expected outcome and ask focused questions if requirements are unclear. I prioritize by user/business impact and SLA, not arrival order alone.

I document investigation timestamps, commands/results without secrets, changes, validation, and communication. Risky changes follow change control and rollback. If blocked, I update owner, reason, next action, and expected time rather than leaving the ticket silent.

I close only after the requester or defined test confirms success, link related incident/problem/change records, and create a knowledge article or automation for repeat issues.

## 19. How do you make CI/CD pipelines auditable for compliance?

**Answer:**

Pipeline definitions and infrastructure code are version-controlled and reviewed. Protected branches/environments, least-privilege identities, separation of duties, and immutable artifacts create traceability.

For each release I retain commit, pull request/reviewers, test/scan/policy results, artifact digest/signature/SBOM, approvals, deployment logs, environment/config version, and verification/rollback result. Logs use defined retention and tamper-resistant storage with restricted access.

I map evidence to control requirements and test that bypass/emergency paths are audited. Compliance automation should make the approved path easier; manual screenshots are fragile and incomplete.

## 20. A CI/CD pipeline takes 30–60 minutes. How would you reduce it to under five minutes?

**Answer:**

I measure before optimizing. Stage timestamps, queue time, executor utilization, cache hit rate, artifact transfer, Docker layer timings, test reports, and external API latency show whether the bottleneck is waiting, checkout, dependency installation, compilation, tests, scanning, image build, or deployment. I compare a fast and slow run from the same commit and do not simply remove quality controls.

I then apply the appropriate changes: shallow or sparse checkout, lockfile-keyed dependency caches, BuildKit layer caching, smaller build context, incremental compilation, parallel independent jobs, test splitting based on historical duration, and pre-warmed ephemeral agents near the registry. Unchanged services in a monorepo can be skipped through reliable dependency mapping. Unit and static checks run first for fast failure; integration/security suites run in parallel with enough isolated capacity.

Under five minutes may be unrealistic for every full production qualification. I define a fast commit-feedback path and keep required broader tests before promotion or continuously against the same immutable artifact. I verify cache correctness, run periodic clean builds, track p50/p95 duration and flakiness, and ensure speed changes do not weaken security or reproducibility.

## 21. How do you design rollback so it still works when the deployment stage itself fails?

**Answer:**

Rollback is designed before deployment and runs from a separate protected recovery path, not only as the next command in the failed job. I store the last known-good immutable image/chart/config version and deployment metadata outside the agent workspace. The deployment system uses timeouts and `post`/`finally` handling, but an operator or automated health controller can also invoke a dedicated rollback job with independent credentials.

For Kubernetes I use a Git revert, Helm rollback, or progressive-delivery controller; for VM deployments I retain the previous package or image and rotate traffic back. Database changes use expand-and-contract migrations because restoring application code cannot undo an incompatible destructive schema change. The recovery workflow is idempotent, environment-scoped, audited, and protected by approval for production.

I test failure at checkout, artifact download, partial rollout, health check, and notification stages. After rollback I verify the real customer transaction, error/latency metrics, version on every instance, database compatibility, and queue/background workers. Then I preserve evidence and correct the failed release rather than repeatedly retrying it.

## 22. How do you implement multi-environment CI/CD while preventing configuration drift?

**Answer:**

I build an artifact once and promote the same digest through Dev, QA, UAT, and Production. Environment differences are explicit, schema-validated values stored in version control or an approved configuration/secret service—not copied pipeline logic or manually edited servers. Reusable pipeline templates and infrastructure modules provide one process, while protected environment files contain only justified differences.

Infrastructure and application configuration use plan/diff checks, GitOps reconciliation where suitable, and scheduled drift detection. Production has stronger approval and credentials but does not run a different untested script. Secrets are referenced by identity and path, never copied between environments. Database and feature changes remain backward compatible during promotion.

Before deployment I compare desired and live state; afterward I record the artifact, config commit, infrastructure version, and policy results and run smoke tests. Break-glass changes expire and must be reconciled into code. This makes drift visible without pretending all environments have identical capacity or integrations.

## 23. A team deploys 50 times per day. How do you maintain stability without slowing releases?

**Answer:**

I make each change small, independently testable, observable, and reversible. Trunk-based development or short-lived branches, required automated tests, static/security policy, immutable artifacts, and reliable ephemeral test environments provide fast feedback. High-risk code is separated from release through feature flags with ownership and expiry.

Deployment uses canary or progressive rollout, automated analysis of error rate, latency, saturation, and business metrics, and automatic pause/rollback. Changes have backward-compatible APIs and expand-and-contract database migrations. Service ownership, SLOs, error budgets, runbooks, and on-call readiness determine when the release rate is safe; a depleted error budget can require reliability work without becoming a permanent manual gate.

I measure change failure rate, lead time, deployment frequency, recovery time, flaky tests, and rollback success. Faster delivery is stable when the pipeline detects bad changes early and production limits blast radius—not when reviews or tests are skipped.

## 24. Is it acceptable to deploy a critical banking application directly to production without automated testing because the developer is confident and time is limited? (True or False)

**Answer:**

False. Confidence is not evidence, and a time constraint increases the need for controlled risk. A critical banking change requires traceability, separation of duties, security and regulatory controls, repeatable tests, an approved artifact, rollback, and post-deployment verification. Direct untested deployment can cause financial loss, data-integrity issues, security exposure, and an unauditable change.

For an emergency, I use an approved break-glass process: define the incident and smallest safe change, peer-review it, run the fastest relevant automated checks, back up affected state, use canary or tightly scoped deployment, prepare rollback, record authorization, and monitor business transactions. Missing lower-priority tests run immediately afterward, and the emergency path is reviewed. Emergency governance can be faster, but it is not the absence of governance.

## 25. A deployment works in staging but fails in production. What differences do you compare?

**Answer:**

I compare the exact artifact digest and configuration commit first; rebuilding between environments makes investigation unreliable. Then I check identity and permissions, secret names/versions, network routes and firewall policy, DNS and certificates, database schema/data volume, feature flags, external endpoints, quotas, resource limits, replicas, region/zone, runtime versions, admission policies, and production-only proxies or service mesh.

I preserve the production error, deployment events, logs, metrics, traces, and audit changes, then reproduce using production-like configuration with sensitive values protected. I avoid making random manual changes. If impact is active, I pause or roll back and verify recovery before testing a fix.

The preventive action is environment parity where practical, explicit versioned differences where not, promotion of one immutable artifact, production-like load and policy testing, configuration schema validation, preflight dependency checks, and drift detection.
