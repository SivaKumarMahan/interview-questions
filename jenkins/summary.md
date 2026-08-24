# Jenkins Summary

## What Jenkins Is

Jenkins is an automation server used to build CI/CD pipelines. It has two parts:

- **The controller** schedules jobs, stores configuration, and coordinates agents.
- **Agents** are the machines or containers that actually run the build steps.

A `Jenkinsfile` holds the pipeline as code, written in Groovy. It's version-controlled and normally kept at the root of the application repository, so pipeline changes go through the same review and history as any other code change.

There are two pipeline styles:

| Style | When to use it |
| --- | --- |
| Declarative Pipeline | The default choice. Structured, easier to read, has built-in validation. |
| Scripted Pipeline | More flexible, but easier to turn into a mess. Use only when Declarative can't do what you need. |

The main sections in a Declarative Pipeline are `pipeline`, `agent`, `environment`, `options`, `parameters`, `triggers`, `stages`, `stage`, `steps`, `when`, `tools`, and `post`.

Common steps you'll see in almost every pipeline: `checkout`/`git` to pull code, `sh`/`bat` to run shell commands, `withCredentials` to use secrets safely, `junit` to publish test results, `archiveArtifacts` to save build output, `stash`/`unstash` to pass files between stages, and various notification steps.

## A Typical End-to-End Pipeline

A well-built pipeline usually does this, in order:

1. Checks out the exact commit.
2. Installs dependencies from a lock file, so builds are repeatable.
3. Builds the application and runs unit and integration tests.
4. Publishes the test reports.
5. Runs code quality, dependency, and image scans, and enforces a quality gate.
6. Builds and signs one artifact. That artifact never changes after it's built — it's built once and reused everywhere.
7. Pushes it to a registry.
8. Promotes that exact same artifact through each environment.

Lower environments like dev and staging usually deploy automatically. Production usually needs a protected approval step, health or SLO checks after deploy, and a rollback plan if something goes wrong.

Shared libraries hold reusable, reviewed pipeline logic, so the `Jenkinsfile` itself stays short and easy to read — it shows what the application does, not how every shared step works internally.

A CI job typically builds, tests, scans, and publishes. A separate CD or GitOps flow then updates the desired image version in Git, and Argo CD deploys it to Kubernetes from there. Prometheus and Grafana watch the result, and alerts go out through whatever notification system the team has approved (Slack, email, etc.).

## Operations and Troubleshooting

Concepts worth knowing: jobs, stages, steps, agents/nodes, workspace, credentials, artifacts, plugins, triggers, webhooks, Poll SCM, cron, post-build actions, backups, and UIs like Blue Ocean.

Treat plugins and shared libraries as privileged code, because they can touch credentials and run on every build. Pin versions, test upgrades before rolling them out, restrict who can administer Jenkins, give every identity only the access it actually needs, and keep the controller's configuration in code so it can be restored.

When something fails, work through this order: find the first stage that failed and read its logs, check the agent's health and label, check the workspace, check dependency and tool versions, check what the credentials are scoped to, check network and registry access, check disk/memory/executor capacity, and look at whatever plugin or `Jenkinsfile` changed most recently. Turn on timestamps in the logs, and keep the test and scan results around for comparison.

Cleanup steps belong in `post { always { ... } }`. Never let a password show up in a Groovy string or in the console log.
