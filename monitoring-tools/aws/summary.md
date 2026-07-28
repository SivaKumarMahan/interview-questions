# AWS Monitoring Summary

**CloudWatch** provides AWS service and custom metrics, logs, Logs Insights, alarms, dashboards, synthetics and event-driven integrations.

Common signals include EC2 saturation (how close a resource is to its limit) and status, Lambda errors/duration/throttles, ALB latency and HTTP errors, ECS/EKS service health, RDS capacity and connections, and SQS depth and message age.

Route actionable alarms through SNS or an incident platform and test the full notification path.

**CloudTrail** is an audit source for AWS API activity: principal, action, time, source, target and result. Centralize organization trails in a protected account, select required management/data events, encrypt and retain evidence, and alert on high-risk policy, identity, logging, key and public-access changes.

Compare a CloudWatch symptom with deployment/configuration events and CloudTrail evidence; CloudTrail is not an application-performance monitor.

For **missing S3 log uploads**, check the collector path and backlog, disk/spool health, the active AWS identity, `s3:PutObject`, bucket/SCP/permissions-boundary denies, required encryption/KMS permissions, region/prefix and multipart errors.

CloudTrail data events and agent metrics distinguish a rejected AWS request from a collector that never attempted one.

Verify a fresh encrypted object and alert on upload age and failure count.
