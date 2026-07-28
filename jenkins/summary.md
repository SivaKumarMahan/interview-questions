# Jenkins Summary

## Jenkins and Jenkinsfile

**Jenkins** is an extensible automation server commonly used for CI/CD. The controller schedules jobs, stores configuration and coordinates agents; agents execute builds.

A `Jenkinsfile` is version-controlled Groovy pipeline-as-code, normally stored at the repository root so pipeline changes follow review and history.

**Declarative Pipeline** is structured and preferred for most use cases; **Scripted Pipeline** is more flexible but easier to make complex. Important Declarative sections include `pipeline`, `agent`, `environment`, `options`, `parameters`, `triggers`, `stages`, `stage`, `steps`, `when`, `tools`, and `post`.

Common steps include `checkout`/`git`, `sh`/`bat`, `withCredentials`, `junit`, `archiveArtifacts`, `stash`/`unstash`, and notifications.

## End-to-End Pipeline

A controlled pipeline checks out the commit, installs locked dependencies, builds, runs unit/integration tests, publishes reports, runs code/dependency/image scans and quality gates, builds and signs an immutable (not changed after creation) artifact, pushes it to a registry, and promotes the same digest.

Lower environments deploy automatically; production can require protected approval, health/SLO verification, and rollback.

Shared libraries hold reviewed reusable behavior while the `Jenkinsfile` keeps application intent visible.

A CI job can build/test/scan/publish. A separate CD/GitOps flow updates the desired image version in Git; **Argo CD** deploys it to Kubernetes. **Prometheus** and **Grafana** monitor the result and alerts route through the approved notification system.

## Operations and Troubleshooting

Useful concepts include jobs, stages, steps, agents/nodes, workspace, credentials, artifacts, plugins, triggers, webhooks, Poll SCM, cron, post-build actions, backups, and Blue Ocean/other UIs.

Treat plugins and shared libraries as privileged code: pin/test upgrades, restrict administration, use least privilege (only the permissions needed), and back up/configure the controller through code.
For a failure, inspect the first failed stage and logs, agent health/label, workspace, dependency/tool version, credentials scope, network/registry access, disk/memory/executors, and recent plugin or `Jenkinsfile` change. Use timestamps and preserve test/scan results.

Cleanup belongs in `post { always { ... } }`; do not expose passwords in Groovy interpolation or logs.
