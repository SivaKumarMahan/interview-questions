# CI/CD: Runners and Pipeline Performance

> Managing shared and hybrid runners, and cutting slow pipelines down to minutes.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you prevent shared runners from blocking pipelines?</summary>

**Answer:**

I monitor queue time, executor utilization, job duration, disk space, and failure rate. Jobs get labels and resource classes so a heavy build doesn't starve a small test job. Runner pools autoscale with a max limit, and critical or protected jobs get their own isolated pool.

I set job timeouts, concurrency controls, fair scheduling, dependency caches, and ephemeral workspaces. A stuck job gets terminated safely, and retries are limited to failures known to be temporary.

Self-hosted runners get patched, capacity-tested, and cleaned between jobs.

If queue time spikes, I first check whether it's real demand, offline agents, slow image pulls, slow startup, or one runaway job — before just throwing more capacity at it.

</details>

<details><summary>Q2. [Advanced] How do you manage hybrid CI/CD runners (on-prem + cloud)? <em>(scenario)</em></summary>

**Answer:** Use self-hosted runners for sensitive or on-prem workloads, cloud runners for elastic builds, and route jobs by label or tag.
Mini-case: Database migrations ran on on-prem runners, while builds and tests ran on GCP runners. This kept both compliance and speed.

**Detailed interview approach:**
I classify each workload by data access, trust level, latency, and how elastic it needs to be. Builds that need private on-prem systems run on dedicated self-hosted pools, reached only through controlled network paths. Ordinary builds can use ephemeral cloud runners instead.

Labels map a job to an approved pool. Untrusted pull requests never run on privileged internal agents. All runners use versioned images, short-lived identity, isolated workspaces, restricted egress, and no persistent secrets.

I monitor queue time, provisioning failures, utilization, patch age, and network dependencies, and keep spare capacity in both locations. A hybrid design also needs a fallback rule, so a cloud outage doesn't accidentally send sensitive work to the wrong runner.

</details>

<details><summary>Q3. [Advanced] A CI/CD pipeline takes 30–60 minutes. How would you reduce it to under five minutes?</summary>

**Answer:**

I measure before optimizing. Stage timestamps, queue time, executor utilization, cache hit rate, artifact transfer time, Docker layer timings, test reports, and external API latency show whether the real bottleneck is waiting, checkout, installing dependencies, compiling, testing, scanning, building the image, or deploying.

I compare a fast run and a slow run from the same commit, and I don't just start cutting quality checks to save time.

Then I apply targeted fixes: shallow or sparse checkout, dependency caches keyed to the lockfile, BuildKit layer caching, a smaller build context, incremental compilation, parallel independent jobs, test splitting based on historical duration, and pre-warmed ephemeral agents close to the registry.

In a monorepo, services that didn't change can be skipped, as long as the dependency mapping is reliable.

Unit and static checks run first so failures show up fast. Integration and security suites run in parallel, with enough isolated capacity to support that.

Getting under five minutes may not be realistic for every full production qualification. Instead, I aim for a fast commit-feedback path, while still running the broader required tests before promotion — or continuously, against that same artifact.

I verify the cache is actually correct, run periodic clean builds, track p50/p95 duration and flakiness, and make sure speed improvements never weaken security or reproducibility.

</details>

<details><summary>Q4. [Intermediate] Your team's CI/CD pipeline has become slow, taking over an hour to complete. How would you approach optimizing it? <em>(scenario)</em></summary>

**Answer:** Instrument each stage to find the bottleneck. Add Docker layer caching and multi-stage builds. Parallelize and split tests. Cache dependencies. Use `terraform -target` for dev iterations. Use ArgoCD's selective sync and ephemeral environments.

**Detailed interview approach:**
First, I'd instrument the pipeline with timing metrics to see how long each stage in GitHub Actions actually takes. For builds, I'd add Docker layer caching and multi-stage builds to shrink image size and build time.

For tests, I'd parallelize unit tests and split them based on their historical run time.

For infrastructure, I'd use Terraform's `-target` flag to apply only changed resources during dev iterations, while still applying the full state for production. I'd add dependency caching for languages like Node.js and Java to avoid repeated downloads.

For Kubernetes deployments, I'd use ArgoCD's selective sync to update only the applications that changed, instead of doing a full sync every time. I'd also set up ephemeral environments that spin up only what a feature branch actually needs, instead of a full clone of the infrastructure.

Together, these changes can take a pipeline from around 65 minutes down to about 12 minutes for most changes.

</details>
