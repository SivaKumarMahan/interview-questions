## 1. How do you monitor Azure resources in production?

**Answer:**

I start with the user journey and the service's goals. Then I use Azure Monitor metrics, resource diagnostic settings, Log Analytics, Application Insights, the Activity Log, alerts with action groups, and workbooks.

I watch availability, latency, errors, traffic, saturation (how close a resource is to its limit), dependency failures, queue age, and capacity — not just VM CPU.

For an incident, I fix the time window and scope first. Then I compare healthy and unhealthy traffic, check deployment and Activity Log changes, follow Application Insights dependencies, and query the relevant resource logs. I fix the confirmed cause and confirm recovery using the original transaction.

Monitoring is deployed through IaC or Policy. Access and retention are controlled, and alert delivery is tested regularly.

## 2. What are Log Analytics and KQL?

**Answer:**

Log Analytics is the Azure Monitor tool for querying workspace log tables. KQL, or Kusto Query Language, is a read-only pipeline language you use to filter data, select columns, parse fields, summarize results, and join tables.

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| summarize Requests=count(),
            Failures=countif(Success == false),
            P95=percentile(DurationMs, 95)
  by bin(TimeGenerated, 5m)
```

I scope the time range and resource early. I confirm the right table and schema with a known event, and I avoid expensive broad joins. Once a query is proven, I turn it into a saved function, a workbook, or an alert. Workspace design also covers region, RBAC, retention, data residency, and ingestion cost.

## 3. What is Application Insights, and how would you investigate a slow API?

**Answer:**

Application Insights captures requests, dependencies, exceptions, traces, availability tests, and distributed correlation through SDK or OpenTelemetry instrumentation.

To investigate a slow API, I compare P50/P95/P99 latency, failure rate, and deployment markers. I pick out slow traces and separate application processing time from SQL, cache, or external dependency time.

I verify the suspected dependency using its own metrics and logs before I change capacity or code.

I also set up sampling, filter out sensitive data, configure trace propagation and retention, and run meaningful synthetic tests. After a rollback, a query fix, or another change, I repeat the same transaction and confirm that latency, errors, and dependency health have recovered.

## 4. How do you create and validate an Azure Monitor alert?

**Answer:**

I pick a resource and an actionable metric or log signal. Then I set a threshold or dynamic condition, an evaluation frequency and window, a severity, and an action group. Log alerts use a KQL query, tested against historical and known data.

The notification should include the environment, resource, observed value, owner, dashboard, and runbook.

I deploy the alert through Bicep, Terraform, or Policy. I trigger a safe test condition to confirm the notification fires and creates an incident, then confirm it resolves correctly. Alert processing rules handle planned maintenance windows.

I track noise and missed incidents, and tune the rule over time rather than leaving an untested portal configuration in place.

## 5. What are Azure diagnostic settings?

**Answer:**

Diagnostic settings route a resource's supported log and metric categories to Log Analytics, Storage, Event Hubs, or a partner tool. Categories differ by resource type, so nothing is enabled everywhere by default.

I choose destinations based on query needs, SIEM requirements, archiving, retention, and cost. I deploy settings consistently, trigger a known event, and check that the resource ID, timestamp, and fields show up correctly at the destination. I also alert on ingestion gaps and lock down the destination against unauthorized deletion.
