# AWS Monitoring Summary

## CloudWatch

CloudWatch collects AWS service and custom metrics, logs, Logs Insights queries, alarms, dashboards, synthetic checks, and event-driven integrations.

Common signals to watch:

| Service | What to watch |
| --- | --- |
| EC2 | How close resources are to their limits, instance status checks |
| Lambda | Errors, duration, throttles |
| ALB | Latency, HTTP error rates |
| ECS / EKS | Service health |
| RDS | Capacity, connection count |
| SQS | Queue depth, message age |

Route actionable alarms through SNS or an incident-management platform, and actually test the full notification path — don't assume it works just because the alarm exists.

## CloudTrail

CloudTrail is an audit trail for AWS API activity. Each record shows the principal, the action, the time, the source, the target, and the result.

Best practice: centralize organization trails in a protected account, turn on the management and data events you actually need, encrypt and retain the logs, and alert on high-risk changes — things like policy changes, identity changes, logging being disabled, key changes, or a resource becoming publicly accessible.

## Using Them Together

Compare a CloudWatch symptom, like a latency spike or an error rate increase, against deployment and configuration events, then confirm the cause with CloudTrail evidence of what actually changed. CloudTrail tells you what changed and who changed it; it isn't an application-performance monitor on its own.

## Diagnosing Missing S3 Log Uploads

1. Check the collector: is it reading the log path, and is there a backlog?
2. Check disk and spool health on the source host.
3. Confirm which AWS identity the collector is actually using.
4. Check `s3:PutObject` permission, and look for denies from the bucket policy, an SCP, or a permissions boundary.
5. If the bucket uses KMS, check the required encryption permissions.
6. Check region, prefix, and multipart upload errors.

CloudTrail data events and the collector's own metrics tell you whether AWS rejected the request or the collector never attempted one in the first place.

Once fixed, verify a fresh object lands with the correct encryption, and set up alerts on upload age and failure count so it doesn't go unnoticed again.
