# Azure Monitoring Summary

Azure Monitor is the umbrella platform for Azure metrics, logs, traces, alerts, workbooks, and integrations. Platform metrics give you numeric time series for each resource.

## Core Building Blocks

| Component | What it does |
| --- | --- |
| Diagnostic settings | Route a resource's logs and metrics to Log Analytics, Storage, Event Hubs, or a partner tool |
| Log Analytics | Stores and queries log data using KQL (Kusto Query Language) |
| Application Insights | Captures application requests, dependencies, exceptions, traces, and availability tests, usually through OpenTelemetry |
| Alerts and action groups | Fire notifications or trigger automation when a condition is met |
| Workbooks | Build reusable dashboards and reports on top of the data above |

Workspace boundaries should reflect who needs access, data residency rules, retention requirements, ownership, and cost.

## Deploying Monitoring Correctly

Data Collection Rules and diagnostic settings need to be deployed consistently, through IaC or Policy rather than by hand. After deployment, generate a known event and confirm it actually arrives. An enabled setting with no confirmed data flowing through it is not real monitoring.

## What a Good Alert Looks Like

A production alert needs:

- A signal that matters to users
- A threshold or dynamic condition
- An evaluation window
- A severity level
- An owner
- An action group
- A linked runbook

Test both the firing notification and the resolved notification before you trust the alert.

## Investigating an Incident

Start with the affected transaction. Compare Application Insights requests and dependencies against resource metrics, Log Analytics data, deployment markers, and Azure Activity Log changes. Confirm recovery by running the same transaction again.

## Monitoring Multiple AKS Clusters

For several AKS clusters, use:

- Azure Monitor container insights data where it's needed
- Azure Managed Prometheus, or self-managed Prometheus, for Kubernetes metrics
- Azure Managed Grafana, or Grafana, for shared views across clusters
- Centralized but access-controlled Log Analytics workspaces

Add cluster, subscription, region, and environment labels, but avoid high-cardinality dimensions — labels with too many unique values, such as raw user or request IDs, which drive up cost and slow down queries.
