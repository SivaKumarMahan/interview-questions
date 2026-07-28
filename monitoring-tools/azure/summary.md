# Azure Monitoring Summary

**Azure Monitor** is the umbrella platform for Azure metrics, logs, traces, alerts, workbooks and integrations. Platform metrics provide numeric time series.

Diagnostic settings route supported resource logs and metrics to Log Analytics, Storage, Event Hubs or partner destinations. **Application Insights** provides application requests, dependencies, exceptions, traces, availability tests and distributed correlation, commonly through workspace-based storage and OpenTelemetry.
**Log Analytics** workspaces store and query data with **KQL**. Workspace boundaries should reflect access, residency, retention, ownership and cost.

Data Collection Rules and diagnostic settings must be deployed consistently through IaC or Policy, then verified by generating a known event. An enabled setting without confirmed ingestion is not complete monitoring.

A **production alert** has a user-relevant signal, threshold or dynamic condition, evaluation window, severity, owner, action group and runbook. Test firing and resolved delivery.

During an incident, start with the affected transaction, compare Application Insights requests/dependencies with resource metrics, Log Analytics data, deployment markers and Azure Activity Log changes, then prove recovery using the same transaction.

For **multiple AKS clusters**, use Azure Monitor managed/container monitoring data as required, Azure Managed Prometheus or self-managed Prometheus for Kubernetes metrics, Azure Managed Grafana or Grafana for shared views, and centralized but access-controlled Log Analytics workspaces.

Include cluster, subscription, region and environment labels without creating high-cardinality (number of unique label combinations) dimensions.
