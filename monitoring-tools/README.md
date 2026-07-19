# Monitoring and Observability Interview Topics

Monitoring material is organized by platform or responsibility:

| Folder | Coverage |
| --- | --- |
| [`azure`](azure/) | Azure Monitor, Log Analytics, KQL, Application Insights, diagnostic settings and AKS monitoring |
| [`aws`](aws/) | CloudWatch metrics/logs/alarms, CloudTrail audit events and S3 log-delivery investigation |
| [`prometheus`](prometheus/) | Scraping, PromQL, exporters, rules, storage, HA and cardinality |
| [`grafana`](grafana/) | Data sources, dashboards, variables, alerting and operational dashboard design |
| [`netdata`](netdata/) | Real-time Agent monitoring, collectors, health alerts, security and Parent-Child streaming |
| [`alertmanager`](alertmanager/) | Routing, grouping, inhibition, silences and Slack/Teams/PagerDuty integration |
| [`kubernetes`](kubernetes/) | Cluster, node, workload and application monitoring; multi-cluster architecture |
| [`logging`](logging/) | ELK/OpenSearch, Loki, Fluent Bit, structured logs, retention and correlation |
| [`apm`](apm/) | Dynatrace, Datadog, New Relic and application-performance monitoring |
| [`ci-cd`](ci-cd/) | Jenkins/Azure DevOps pipeline telemetry and post-deployment health gates |
| [`infrastructure-as-code`](infrastructure-as-code/) | Monitoring provisioned with Terraform and Terraform run/drift telemetry |
| [`host-monitoring`](host-monitoring/) | Linux/Windows host CPU, memory, disk, process, service and log monitoring |
| [`databases`](databases/) | Database availability, latency, pools, locks, replication and backup signals |
| [`finops`](finops/) | Telemetry ingestion, retention, cardinality and observability cost controls |
| [`observability`](observability/) | Golden signals, SLOs, traces, serverless, incident correlation and alert quality |

Network latency, packet loss, flow-log and load-balancer path investigations remain under [`networking/observability`](../networking/observability/README.md) because networking is their primary subject.

The former mixed root files were distributed into these folders. Relevant material from Azure, AWS, Kubernetes, Jenkins, Terraform, CI/CD, Ops/SRE and other folders was consolidated here; the original topic files remain useful for their broader interview context.
