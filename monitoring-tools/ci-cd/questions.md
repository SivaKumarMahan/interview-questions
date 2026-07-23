## 1. How do you monitor Jenkins or Azure DevOps pipelines?

**Answer:**

I export supported platform/plugin/API metrics to Prometheus or the chosen backend and graph queue time, stage duration, result, retries, flaky tests, agent capacity, artifact transfer, deployment frequency, lead time, change-failure rate and recovery time. Labels are bounded; commit hashes belong in deployment annotations/logs rather than long-lived metric labels.

An alert includes pipeline, environment, failed stage, owner and runbook. Normal build failure notifies the team; production deployment failure or a blocked critical path may page. I correlate trends with agent image/tool changes and fix the flaky or constrained stage rather than adding unlimited retries.

## 2. How do you integrate observability into deployment gates?

**Answer:**

I deploy one immutable artifact, annotate dashboards with its digest/commit, route a controlled traffic amount, and query error rate, latency, saturation plus a smoke/business transaction. The gate uses a defined observation window and minimum traffic so empty or insufficient data cannot pass silently.

If thresholds fail, promotion stops and a controlled rollback or traffic shift runs, followed by the same verification. The action is authorized, bounded and logged. Teams can override only through an audited approval path because automatic health checks can themselves be incomplete.
