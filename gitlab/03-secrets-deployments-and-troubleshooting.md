# GitLab: Secrets, Deployments, and Troubleshooting

> Managing secrets, deploying to Kubernetes with environments and manual jobs, speeding up pipelines, and troubleshooting CI failures.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you manage GitLab repository secrets?</summary>

**Answer:**

I store CI secrets as protected and masked CI/CD variables, or I fetch them at runtime from Vault or a cloud secret manager. Production secrets are limited to protected branches and tags, and to protected environments.

File-type variables are useful when a tool needs a temporary credential file on disk.

For cloud access, I prefer OIDC or workload identity so jobs get short-lived credentials instead of long-lived keys. I never echo variables to the log, turn on shell tracing around secret operations, or let secrets end up in artifacts or cache.

Masking hides a value in the log output, but it's not the real security boundary — access control is.

I test that unprotected branches and fork pipelines cannot reach production variables. If a value does leak, I revoke it first, check job logs and audit events, rotate the affected credentials, and remove any retained artifacts that might contain it.

</details>

<details><summary>Q2. [Intermediate] How do you manage secrets in GitLab CI?</summary>

**Answer:**

I use protected, masked CI/CD variables, or fetch secrets from Vault or a cloud secret manager during the job. For cloud authentication, I prefer GitLab's OIDC identity federation, so the job trades its identity token for short-lived credentials instead of holding a long-lived key.

Controls I rely on:

1. Production variables are only available to protected branches/tags and protected environments.
2. Runners handling untrusted merge requests cannot reach production secrets.
3. Shell tracing is turned off around any secret operation.
4. Secrets never go into artifacts, cache, Docker image layers, or command-line arguments that would show up in a process list.
5. Access, ownership, expiry, and rotation are all audited.

If a secret shows up in a job log, I revoke it right away, check who could have read that log, rotate the related credentials, remove the retained output where I can, and fix the pipeline before running it again.

</details>

<details><summary>Q3. [Intermediate] How do you deploy to Kubernetes from GitLab CI?</summary>

**Answer:**

The pipeline builds and scans an image, pushes it tagged with an immutable commit SHA, and updates the Kubernetes release through Helm, plain manifests, or GitOps. I prefer GitOps when I can use it, because then the cluster pulls its own desired state and CI never needs to hold broad cluster credentials.

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

I use a dedicated ServiceAccount or workload identity with only the access it actually needs, plus protected environments, readiness probes, smoke tests, deployment metrics, and a rollback path. I save the image digest and the Helm revision so the exact release stays traceable.

</details>

<details><summary>Q4. [Basic] What are manual jobs and environments in GitLab CI?</summary>

**Answer:**

A manual job, set with `when: manual`, waits for an authorized person to start it. An environment represents a deployment target like staging or production, and GitLab records its deployment history, URLs, and protection rules.

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

I protect the production environment so only the release group can run it, and I require that the artifact already passed the checks in lower environments first. Clicking the manual button isn't the whole control by itself — I also need separation of duties, traceable change approval, health checks, rollback, and audit logs.

</details>

<details><summary>Q5. [Intermediate] How do you optimize GitLab CI pipeline speed?</summary>

**Answer:**

I measure queue time and job duration first, then fix the actual bottleneck instead of guessing:

- Use `needs` so independent jobs run as a DAG instead of one stage at a time.
- Cache dependencies keyed off the lock file.
- In a monorepo, build only the affected services using `rules:changes`.
- Parallelize tests while keeping results predictable.
- Use prebuilt tool images and registries close to the runners.
- Autoscale runners and separate heavy workloads from fast ones.
- Build the artifact once and reuse that same immutable artifact across environments, instead of rebuilding it each time.

I never skip required tests just to make the pipeline finish faster. After making changes, I compare median and high-percentile duration, queue time, cache hit rate, flakiness, and infrastructure cost.

</details>

<details><summary>Q6. [Intermediate] How do you troubleshoot GitLab CI failures?</summary>

**Answer:**

First I narrow down where the problem actually is: pipeline creation, scheduling, runner execution, the job's own commands, artifacts, or deployment.

1. Read the first meaningful error, not just the final exit code.
2. Check what changed recently in `.gitlab-ci.yml`, variables, runners, images, or dependencies.
3. Confirm the runner is online, correctly tagged, and allowed to pick up the job.
4. Check protected variables and environment permissions.
5. Check artifact paths, cache behavior, disk space, network/DNS, and the status of external services.
6. Reproduce the job locally with the same container image and commands, using safe test credentials.

I fix the root cause, and only rerun the job once I know it's safe to run again — a job is idempotent if running it twice causes no harm. I validate the downstream outputs, and add something to prevent a repeat: pinning a version, improving an error message, setting a timeout, or monitoring runner capacity.

</details>
