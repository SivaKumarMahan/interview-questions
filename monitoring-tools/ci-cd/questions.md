## 1. How do you monitor Jenkins or Azure DevOps pipelines?

**Answer:**

I export whatever platform, plugin, or API metrics are available to Prometheus or the chosen backend. Then I graph queue time, stage duration, result, retries, flaky tests, agent capacity, artifact transfer time, deployment frequency, lead time, change-failure rate, and recovery time.

I keep labels limited. Commit hashes belong in deployment annotations or logs, not in long-lived metric labels.

An alert should include the pipeline, environment, failed stage, owner, and runbook. A normal build failure notifies the team; a production deployment failure, or a blocked critical path, may page someone.

I compare trends against agent image or tool changes, and fix the flaky or constrained stage instead of just adding more retries.

## 2. How do you integrate observability into deployment gates?

**Answer:**

I deploy one immutable artifact — meaning it's never changed after it's built — and annotate dashboards with its digest and commit. I route a controlled amount of traffic to it, then check error rate, latency, saturation (how close the system is to its limit), and a smoke or business transaction.

The gate uses a fixed observation window and a minimum amount of traffic, so an empty or thin sample can't pass silently.

If the thresholds fail, promotion stops. A controlled rollback or traffic shift runs, followed by the same verification. That action is authorized, limited in scope, and logged.

Teams can only override the gate through an audited approval path, because automated health checks can be wrong too.
