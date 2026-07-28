# CI/CD Monitoring Summary

**Pipeline monitoring data** should cover queue time, stage duration, success/failure/retry rate, flaky tests, agent saturation (how close a resource is to its limit), artifact size/time, deployment frequency, lead time, change-failure rate and recovery time.

Jenkins can expose metrics through a maintained Prometheus integration; Azure DevOps metrics and APIs can feed the selected observability backend.

Grafana or another dashboard shows trends by pipeline, branch, agent pool and environment.

Tag application dashboards with commit, artifact digest and deployment time. A **post-deployment gate** checks error rate, latency, saturation (how close a resource is to its limit) and a real smoke/business transaction before promotion.

Automatic rollback must be limited, authorized, recorded and verified; it must not conceal a recurring root cause.

**Alerts** should identify environment, commit, failed stage, owner and runbook. Page only for urgent production impact or a blocked critical delivery path; ordinary build failures normally notify the responsible team without waking on-call staff.

Never expose credentials through pipeline logs or high-cardinality (number of unique label combinations) labels.
