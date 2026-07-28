# GitLab Interview Questions

---

### 1. What is GitLab?

**Answer:**

GitLab is a DevSecOps platform centered on Git repository hosting. It includes merge requests, issues, access control, CI/CD, runners, package and container registries, releases, and security capabilities.

It can be consumed as GitLab.com or self-managed when an organization needs control over network placement, upgrades, or data residency.

A typical flow is: developer pushes a branch, opens a merge request, pipeline runs tests and scans, reviewers approve, the commit merges, an immutable (not changed after creation) artifact is published, and a protected environment job deploys it.

I would still evaluate runner security, backup/restore, identity integration, licensing, availability, and operational ownership before selecting it.
---

### 2. What is a merge request in GitLab?

**Answer:**

A merge request proposes integrating a source branch into a target branch. It combines code review, discussion, automated pipeline results, approvals, issue links, and the final merge decision.

I include a clear problem statement, solution, risk, test evidence, deployment impact, and rollback notes. GitLab rules can require Code Owner approval, successful pipelines, resolved discussions, and no merge conflicts.

I keep changes small enough to review and use draft status while work is incomplete.

Before merging, I review the generated artifact or infrastructure plan where relevant. After merging, I verify the deployment and link the release back to the merge request for auditability.

---

### 3. How do you protect branches in GitLab?

**Answer:**

I mark `main` and release branches as protected, restrict who can push and merge, disallow force pushes, and require merge requests. Approval rules require appropriate reviewers or Code Owners, while pipelines enforce tests, security scans, and policy checks.

I also protect tags and deployment environments because a user who can create a production tag or run a deployment may bypass branch controls. Emergency access is limited, audited, and reviewed afterward.

I validate the control with a normal developer account: direct push, force push, unauthorized merge, and protected-variable access should fail. Periodic access review removes stale users and tokens.

---

### 4. How do GitLab groups and projects help access management?

**Answer:**

Groups organize related projects and can contain subgroups. Membership and settings can be inherited, which makes it easier to manage teams consistently. Projects contain repositories, pipelines, registries, issues, and project-specific permissions.

I grant access through groups rather than individual users, use the least suitable role, separate platform and application administration, and create subgroups for different trust boundaries. Sensitive production projects and runners should not inherit overly broad access from a general parent group.
I review inherited permissions, deploy tokens, access tokens, runner scope, protected environments, and external collaborators regularly. Ownership is documented so access requests and removals have an accountable approver.

---

### 5. How do you manage GitLab repository secrets?

**Answer:**

I store CI secrets as protected and masked CI/CD variables or retrieve them at runtime from Vault or a cloud secret manager. Production secrets are restricted to protected branches/tags and protected environments.

File-type variables are useful when a tool needs a temporary credential file.

I prefer OIDC or workload identity for cloud access so jobs receive short-lived credentials. I never echo variables, enable shell tracing around secrets, or pass secrets through artifacts and caches.

Masking is a safety feature, not the primary security boundary.

I test that unprotected branches and fork pipelines cannot access production variables. If a value leaks, I revoke it first, inspect job logs and audit events, rotate affected credentials, and remove retained artifacts where possible.

---

### 6. What are GitLab tags and releases used for?

**Answer:**

A Git tag marks a specific commit, commonly a version such as `v1.4.0`. A GitLab Release adds release notes, evidence, links, and assets around that tag.

My pipeline builds an immutable (not changed after creation) artifact once, records the commit SHA and checksum, and promotes that same artifact. Protected tags restrict who can trigger a release.

I do not move an existing published tag; a correction gets a new version.

Release notes contain user-visible changes, migrations, known issues, deployment steps, and rollback information. After deployment I verify application health and retain enough artifact and pipeline evidence to reproduce what reached production.

---

### 7. How do you handle code review quality in GitLab?

**Answer:**

I combine process and automation:

- Small merge requests with clear acceptance criteria
- Code Owners for security-sensitive or specialized areas
- Required approvals without allowing the author to self-approve
- Successful unit, integration, lint, security, and policy checks
- Resolved discussions and tested migrations
- Review checklists covering security, failure handling, observability, and rollback

I encourage reviewers to explain risk rather than only style preferences. Repeated style issues are moved into linters. I monitor review time, defect escape rate, and oversized requests; adding approvals without improving review quality only slows delivery.

---

### 8. How do you migrate a repository to GitLab?

**Answer:**

I inventory branches, tags, large files, submodules, issues, pull requests, webhooks, deploy keys, CI secrets, branch policies, packages, and integrations. For Git history I can mirror all references:

```bash
git clone --mirror <old-url> project.git
cd project.git
git push --mirror <gitlab-url>
```

I recreate permissions, protected branches/tags, runners, variables, and webhooks without copying plaintext secrets. I migrate issues and review history with supported import tools when required.

Before cutover I freeze writes briefly, run a final sync, compare branch/tag counts and important SHAs, test clone/push/merge/pipeline/release operations, then switch DNS or repository URLs. The old repository becomes read-only for an agreed period, with a documented rollback plan.
---

### 9. What is GitLab CI/CD?

**Answer:**

GitLab CI/CD runs automated workflows defined mainly in `.gitlab-ci.yml`. A commit, merge request, tag, schedule, API call, or manual action creates a pipeline. The pipeline contains stages and jobs, and GitLab Runners execute those jobs.

A production flow can be:

```text
commit → build/test → code and dependency scans → image build/scan
       → publish immutable (not changed after creation) artifact → deploy staging → smoke test
       → production approval → deploy → verify/rollback
```

I keep the pipeline definition in Git, use templates for repeated jobs, protect production environments, use short-lived credentials, and make artifacts traceable to a commit. Monitoring and post-deployment checks decide whether a deployment succeeded; a green pipeline alone does not prove the application is healthy.
---

### 10. What are stages, jobs, and runners in GitLab CI?

**Answer:**

- A **job** is a unit of work, such as test or deploy, with a script, image, variables, and rules.
- A **stage** groups jobs by logical order. Jobs in the same stage can run in parallel; later stages normally wait for earlier ones.
- A **runner** is the agent that executes jobs using a shell, Docker, Kubernetes, or another executor.

```yaml
stages: [test, build]

unit-test:
  stage: test
  image: node:20-alpine
  script: ["npm ci", "npm test"]

build-image:
  stage: build
  script: ["docker build -t app:$CI_COMMIT_SHA ."]
```

I tag runners by capability, isolate protected runners, patch them, prevent secret persistence, and autoscale where appropriate. `needs` can create a DAG so a job starts as soon as its dependencies finish instead of waiting for the entire prior stage.

---

### 11. How do you define a simple GitLab CI pipeline?

**Answer:**

I define events with `workflow: rules`, then create jobs with explicit images, scripts, artifacts, and failure behavior.

```yaml
stages: [test, package]

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

test:
  stage: test
  image: python:3.12-slim
  script:
    - pip install -r requirements.txt
    - pytest --junitxml=report.xml
  artifacts:
    when: always
    reports:
      junit: report.xml

package:
  stage: package
  image: docker:27
  services: ["docker:27-dind"]
  script:
    - docker build -t "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" .
```

I lint the file in GitLab CI Lint, pin tool images, set timeouts, avoid plaintext secrets, and ensure merge-request pipelines cannot deploy production. A real production image job would authenticate securely, scan the image, and push only after required gates pass.
---

### 12. What is the difference between `only/except` and `rules`?

**Answer:**

`only/except` is the older way to include or exclude jobs based mainly on branches, tags, variables, or changes. `rules` is more expressive and evaluates ordered conditions using pipeline source, variables, file changes, existence, and a selected `when` behavior.
```yaml
deploy-prod:
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/'
      when: manual
    - when: never
```

I prefer `rules` for new pipelines and avoid mixing both styles in one job. I test behavior for push, merge-request, tag, schedule, and API pipelines because incorrect rules can create duplicate pipelines or accidentally expose a deployment job.

---

### 13. How do artifacts and cache differ in GitLab CI?

**Answer:**

Artifacts are job outputs intentionally passed to later jobs or retained for users, such as binaries, test reports, plans, or manifests. Cache is a performance optimization for reusable dependencies such as package-manager downloads.

A job must remain correct if the cache is empty.

```yaml
cache:
  key:
    files: [package-lock.json]
  paths: [.npm/]

artifacts:
  paths: [dist/]
  expire_in: 7 days
```

I do not store secrets in either. Artifacts use controlled retention and immutable (not changed after creation) versioning.

Cache keys include the lock file and sometimes branch protection level to prevent cache poisoning. Production deployment consumes the approved artifact, not whatever happens to be in a cache.

---

### 14. How do you manage secrets in GitLab CI?

**Answer:**

I use protected, masked CI/CD variables or retrieve secrets from Vault/cloud secret managers during the job. For cloud authentication I prefer GitLab OIDC identity federation so the job exchanges its identity token for short-lived credentials.

Controls include:

1. Production variables are available only to protected refs and environments.
2. Runners for untrusted merge requests cannot access production secrets.
3. Shell tracing is disabled around secret operations.
4. Secrets are never placed in artifacts, cache, Docker layers, or command-line arguments that appear in process lists.
5. Access, owner, expiry, and rotation are audited.

If a secret appears in a job log, I revoke it immediately, review who could read the log, rotate related credentials, remove retained output where possible, and correct the pipeline before rerunning it.

---

### 15. How do you deploy to Kubernetes from GitLab CI?

**Answer:**

The pipeline builds and scans an image, pushes it with an immutable (not changed after creation) SHA tag, and updates the Kubernetes release through Helm, manifests, or GitOps. I prefer GitOps when possible so the cluster pulls desired state and CI does not hold broad cluster credentials.
For a direct deployment:

```yaml
deploy-staging:
  stage: deploy
  environment:
    name: staging
  script:
    - helm upgrade --install api ./chart
      --namespace api --create-namespace
      --set image.tag="$CI_COMMIT_SHA"
      --atomic --wait --timeout 5m
    - kubectl rollout status deployment/api -n api --timeout=5m
```

I use a dedicated least-privilege (minimum required access) ServiceAccount or workload identity, protected environments, readiness probes, smoke tests, deployment metrics, and rollback. I save the image digest and Helm revision so the exact release is traceable.

---

### 16. What are manual jobs and environments in GitLab CI?

**Answer:**

A manual job waits for an authorized user to start it using `when: manual`. An environment represents a deployment target such as staging or production and records deployment history, URLs, and protection rules.

```yaml
deploy-production:
  when: manual
  allow_failure: false
  environment:
    name: production
    url: https://app.example.com
  rules:
    - if: $CI_COMMIT_TAG
```

I protect the production environment so only the release group can run it, and I require that the artifact already passed lower-environment checks. The manual click is not the complete control: I also need separation of duties, traceable change approval, health gates, rollback, and audit logs.
---

### 17. How do you optimize GitLab CI pipeline speed?

**Answer:**

I measure queue time and job duration first, then optimize the actual bottleneck:

- Use `needs` to run independent jobs as a DAG.
- Cache dependencies using lock-file keys.
- Build only affected services in a monorepo using `rules:changes`.
- Parallelize tests while keeping predictable results.
- Use prebuilt tool images and nearby registries.
- Autoscale runners and separate heavy workloads.
- Reuse one immutable (not changed after creation) build artifact instead of rebuilding per environment.

I do not skip required tests merely to make the pipeline green faster. After changes I compare median and high-percentile duration, queue time, cache hit rate, flakiness, and infrastructure cost.

---

### 18. How do you troubleshoot GitLab CI failures?

**Answer:**

I identify whether the problem is pipeline creation, scheduling, runner execution, job commands, artifacts, or deployment.

1. Read the first meaningful error, not only the final exit code.
2. Check recent `.gitlab-ci.yml`, variable, runner, image, and dependency changes.
3. Confirm the runner is online, correctly tagged, and allowed to run the job.
4. Verify protected variables and environment permissions.
5. Check artifact paths, cache behavior, disk space, network/DNS, and external service status.
6. Reproduce the job with the same container image and commands using safe test credentials.

I fix the root cause, rerun only when the job is safe and idempotent (safe to run more than once), validate downstream outputs, and add a preventive change such as pinning a version, improving an error message, setting a timeout, or monitoring runner capacity.