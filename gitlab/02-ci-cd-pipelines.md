# GitLab: CI/CD Pipelines

> GitLab CI/CD concepts: stages, jobs, runners, pipeline definitions, rules, artifacts, and cache.

## Interview Questions

<details><summary>Q1. [Basic] What is GitLab CI/CD?</summary>

**Answer:**

GitLab CI/CD runs automated workflows, defined mostly in `.gitlab-ci.yml`. A pipeline gets created by a commit, a merge request, a tag, a schedule, an API call, or a manual trigger. Each pipeline has stages and jobs, and GitLab Runners actually execute those jobs.

A production flow can look like this:

```text
commit → build/test → code and dependency scans → image build/scan
       → publish immutable (not changed after creation) artifact → deploy staging → smoke test
       → production approval → deploy → verify/rollback
```

I keep the pipeline definition in Git, use templates so I'm not repeating job configuration, protect production environments, use short-lived credentials, and make sure every artifact traces back to a commit. Monitoring and post-deployment checks are what actually confirm a deployment succeeded — a green pipeline on its own doesn't prove the application is healthy.

</details>

<details><summary>Q2. [Basic] What are stages, jobs, and runners in GitLab CI?</summary>

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

I tag runners by capability, keep protected runners isolated, patch them regularly, make sure they don't retain secrets between jobs, and autoscale where it makes sense. Using `needs`, a job can start as soon as its own dependencies finish, instead of waiting for the whole previous stage to complete.

</details>

<details><summary>Q3. [Basic] How do you define a simple GitLab CI pipeline?</summary>

**Answer:**

I define which events trigger a pipeline using `workflow: rules`, then create jobs with explicit images, scripts, artifacts, and failure behavior.

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

I lint the file with GitLab's CI Lint tool, pin tool images to specific versions, set timeouts, avoid plaintext secrets, and make sure merge-request pipelines can't deploy to production. A real production image job would also authenticate securely, scan the image, and only push it after the required gates pass.

</details>

<details><summary>Q4. [Basic] What is the difference between <code>only/except</code> and <code>rules</code>?</summary>

**Answer:**

`only/except` is the older way to include or exclude a job, based mainly on branch, tag, variable, or changed files. `rules` is more expressive: it evaluates ordered conditions using the pipeline source, variables, file changes, and file existence, and lets you set a specific `when` behavior for each one.

```yaml
deploy-prod:
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/'
      when: manual
    - when: never
```

I prefer `rules` for new pipelines and avoid mixing the two styles in the same job. I test the behavior across push, merge-request, tag, schedule, and API pipelines, since a mistake in the rules can create duplicate pipelines or accidentally expose a deployment job.

</details>

<details><summary>Q5. [Basic] How do artifacts and cache differ in GitLab CI?</summary>

**Answer:**

Artifacts are job outputs meant to be passed to later jobs or kept for people to download — binaries, test reports, plans, manifests. Cache exists purely for speed: it holds reusable dependencies like package-manager downloads.

A job has to work correctly even if the cache is completely empty.

```yaml
cache:
  key:
    files: [package-lock.json]
  paths: [.npm/]

artifacts:
  paths: [dist/]
  expire_in: 7 days
```

I never put secrets in either one. Artifacts use controlled retention and stay immutable once created.

Cache keys include the lock file, and sometimes the branch protection level, to prevent cache poisoning. Production deployment always uses the approved artifact — never whatever happens to be sitting in a cache.

</details>
