## 1. How do you monitor Azure resources in production?

**Answer:**

I start with the user journey and service objectives, then use Azure Monitor metrics, resource diagnostic settings, Log Analytics, Application Insights, Activity Log, alerts/action groups and workbooks.

I monitor availability, latency, errors, traffic, saturation (how close a resource is to its limit), dependency failures, queue age and capacity rather than only VM CPU.
For an incident I fix the time and scope, compare healthy and unhealthy traffic, compare deployment and Activity Log changes, follow Application Insights dependencies and query relevant resource logs. I mitigate the proven failure and validate recovery with the original transaction.

Monitoring is deployed through IaC/Policy, access and retention are controlled, and alert delivery is regularly tested.

## 2. What are Log Analytics and KQL?

**Answer:**

Log Analytics is the Azure Monitor experience for querying workspace log tables. Kusto Query Language is a read-only pipeline language used to filter, select columns, parse, summarize, and join monitoring data.

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| summarize Requests=count(),
            Failures=countif(Success == false),
            P95=percentile(DurationMs, 95)
  by bin(TimeGenerated, 5m)
```

I scope time/resource early, confirm the correct table/schema with a known event, avoid expensive broad joins, and turn proven queries into saved functions, workbooks and alerts. Workspace design includes region, RBAC, retention, data residency and ingestion cost.

## 3. What is Application Insights, and how would you investigate a slow API?

**Answer:**

Application Insights provides requests, dependencies, exceptions, traces, availability and distributed correlation through SDK/OpenTelemetry instrumentation. I compare P50/P95/P99, failure rate and deployment markers, select slow traces, and separate application processing from SQL/cache/external dependency time.

I verify the suspected dependency using its native metrics and logs before changing capacity or code.

I configure sampling, sensitive-data filtering, trace propagation, retention and meaningful synthetic tests. After rollback, query optimization or another fix, I repeat the same transaction and confirm latency, errors and dependency health recover.

## 4. How do you create and validate an Azure Monitor alert?

**Answer:**

I select a resource and actionable metric/log signal, define threshold or dynamic condition, evaluation frequency/window, severity and an action group. Log alerts use a KQL query tested against historical and known data.

The notification includes environment, resource, observed value, owner, dashboard and runbook.

I deploy it through Bicep/Terraform/Policy, generate a safe condition, verify firing notification and incident creation, then verify resolution. Alert processing rules handle planned maintenance.

I measure noise and missed incidents and tune the rule rather than leaving an untested portal configuration.

## 5. What are Azure diagnostic settings?

**Answer:**

They route supported resource log/metric categories to Log Analytics, Storage, Event Hubs or partners. Categories differ per resource and are not automatically enabled everywhere.

I choose destinations from query, SIEM, archive, retention and cost needs; deploy settings consistently; generate a known event; and verify resource ID, timestamp and fields at the destination. I also alert on ingestion gaps and protect the destination from unauthorized deletion.
