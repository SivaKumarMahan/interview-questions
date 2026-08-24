# Application Performance Monitoring Summary

## What APM Does

Application Performance Monitoring (APM) connects a user's request to everything that handled it: the service code, its dependencies, and the underlying infrastructure. It does this through request metrics, distributed traces, error tracking, logs, service topology maps, profiling, and sometimes real-user and synthetic monitoring.

## Common Tools

| Tool | Type |
| --- | --- |
| Dynatrace | Commercial, full-stack |
| Datadog | Commercial, full-stack |
| New Relic | Commercial, full-stack |
| Application Insights | Azure-native |
| OpenTelemetry | Vendor-neutral instrumentation and export standard |

Dynatrace, Datadog, and New Relic are commercial platforms that cover the full stack. Application Insights is Azure's native option. OpenTelemetry isn't a platform on its own — it's a standard way to instrument code and export the data, so you can send it to whichever backend you choose.

## Choosing a Tool

The right choice depends on: application and runtime coverage, whether instrumentation is automatic or manual, Kubernetes and cloud integration, topology mapping, query and retention needs, sampling behavior, data residency, access control, operational effort, and cost.

## Using APM Well

A tool by itself isn't observability. To get real value out of it:

- Define clear service and business indicators to track.
- Propagate trace context across service calls.
- Mark deployments so before/after comparisons are easy.
- Redact sensitive data from captured attributes.
- Assign clear ownership for dashboards and alerts.

## Diagnosing a Slow API

1. Compare P95/P99 latency and error rates before and after the change.
2. Pick a few representative slow traces to dig into.
3. Separate time spent in service code from time spent in dependencies.
4. Check database, cache, and external calls, and check whether the runtime is close to a resource limit.
5. Fix the proven bottleneck.
6. Re-verify the original slow user transaction to confirm it's resolved.