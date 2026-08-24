# CI/CD Monitoring Summary

Pipeline monitoring should cover the full delivery path, not just whether a build passed.

## What to Track

| Area | Signals |
| --- | --- |
| Pipeline health | Queue time, stage duration, success/failure/retry rate, flaky tests |
| Agent capacity | Agent saturation — how close agents are to running out of capacity |
| Artifacts | Artifact size and transfer time |
| Delivery performance | Deployment frequency, lead time, change-failure rate, recovery time |

Jenkins can expose metrics through a maintained Prometheus integration. Azure DevOps has its own metrics and APIs that can feed whatever observability backend you use.

Grafana, or another dashboard tool, should show these trends broken down by pipeline, branch, agent pool, and environment.

## Tagging and Correlation

Tag application dashboards with the commit, artifact digest, and deployment time. This lets you trace a production issue back to the exact build that caused it.

## Deployment Gates

A post-deployment gate should check error rate, latency, saturation, and a real smoke or business transaction before allowing promotion to continue.

Automatic rollback must be:

- Limited in scope
- Authorized
- Recorded
- Verified afterward

A rollback that fires automatically should never hide a recurring root cause — someone still needs to investigate why it triggered.

## Alerting

Alerts should identify the environment, commit, failed stage, owner, and runbook.

Page someone only for urgent production impact or a blocked critical delivery path. Ordinary build failures should just notify the responsible team, not wake up on-call.

## Security Note

Never expose credentials in pipeline logs. Also avoid high-cardinality labels — labels with too many unique values, like raw usernames or request IDs, that make metrics expensive to store and slow to query.
