## 1. Compare Dynatrace, Datadog, New Relic and OpenTelemetry.

**Answer:**

Dynatrace, Datadog and New Relic are commercial observability platforms offering varying combinations of agents, APM, infrastructure, logs, traces, topology, user experience and automated analysis. OpenTelemetry is an open instrumentation and collection standard, not a complete storage/analysis UI by itself.
I select from runtime/cloud/Kubernetes coverage, trace quality, profiling and RUM/synthetics, integrations, data residency, access, sampling/retention, operational effort and cost. A pilot uses a real service and incident query.

Vendor automation assists investigation but changes require evidence and safe approval controls.

## 2. How do you use APM to find a latency regression?

**Answer:**

I mark the deployment, compare request percentiles and errors by version, select representative slow traces, and split time among gateway, service code, database/cache/queue/external dependencies.

I inspect runtime saturation (how close a resource is to its limit) and logs for the same trace ID, compare healthy traffic, and mitigate the proven bottleneck through rollback, capacity or a targeted fix.

I validate the original user transaction and add a regression test or SLO alert.
