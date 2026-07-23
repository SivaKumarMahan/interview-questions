# Application Performance Monitoring Summary

**APM** connects user transactions to service code, dependencies and infrastructure through request metrics, distributed traces, errors, logs, topology, profiling and sometimes real-user/synthetic monitoring. Dynatrace, Datadog and New Relic provide commercial full-stack platforms; Application Insights is Azure-native; OpenTelemetry offers vendor-neutral instrumentation and export.

**Selection** depends on application/runtime coverage, automatic versus manual instrumentation, Kubernetes/cloud integration, topology, query and retention needs, sampling, data residency, access control, operational effort and cost. A tool is not observability by itself: define service/business indicators, propagate trace context, mark deployments, redact sensitive attributes and assign dashboard/alert ownership.

For a **slow API**, compare P95/P99 and errors before/after a change, choose representative traces, separate service processing from dependency time, inspect database/cache/external calls and runtime saturation, mitigate the proven bottleneck, then verify the same user transaction.
