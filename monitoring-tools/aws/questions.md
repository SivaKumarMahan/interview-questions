## 1. What is the difference between CloudWatch and CloudTrail?

**Answer:**

CloudWatch is operational telemetry: metrics, logs, dashboards, alarms, synthetics and event integrations. CloudTrail records AWS API activity for audit and investigation. I use CloudWatch to see that latency or errors increased and CloudTrail to determine whether a deployment role or administrator changed the load balancer, security policy or scaling configuration at that time.

CloudTrail does not replace application tracing, and CloudWatch does not by itself provide a complete identity audit. Production uses centralized protected trails, selected data events, encryption/retention, actionable CloudWatch alarms and tested SNS/incident routing.

## 2. Logs are not uploading from a healthy EC2 instance to S3. How do you investigate?

**Answer:**

I confirm the collector is reading current files, its spool disk is healthy and it attempted an upload. I identify its role with `aws sts get-caller-identity`, then check bucket/region/prefix, `s3:PutObject`, explicit denies from bucket policy/SCP/boundary, KMS `Encrypt`/`GenerateDataKey`, required tags/conditions, clock and multipart failures. I inspect agent errors and CloudTrail data events without printing credentials.

I fix the narrow collector, IAM, KMS, path or storage issue, then verify a new object with correct encryption/metadata and downstream consumption. Prevention includes instance/task roles, least privilege and alerts on collector backlog, upload age and errors.

## 3. How would you monitor an EC2 CPU incident?

**Answer:**

I confirm CloudWatch duration, customer impact, status checks, autoscaling, recent changes and CPU-credit exhaustion for burstable instances. On the host I compare load, user/system CPU, steal, I/O wait and top processes. I stabilize by shifting traffic, scaling out, rolling back or stopping a proven nonessential runaway job; I avoid rebooting before preserving evidence.

The permanent fix may be profiling, query/cache work, scheduled-job correction, better scaling signals or a suitable instance family. I validate user latency/errors under load and alert on saturation, credits, queueing and failed scaling.
