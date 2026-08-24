## 1. What is the difference between CloudWatch and CloudTrail?

**Answer:**

CloudWatch holds operational monitoring data: metrics, logs, dashboards, alarms, synthetic checks, and event integrations. CloudTrail records AWS API activity for audit and investigation.

In practice, I use CloudWatch to spot that latency or errors went up, then use CloudTrail to check whether a deployment role or an administrator changed the load balancer, a security policy, or a scaling setting around that same time.

CloudTrail isn't a substitute for application tracing, and CloudWatch alone doesn't give a full identity audit trail. In production, I use centralized, protected CloudTrail trails, turn on the data events that matter, enable encryption and retention, make sure CloudWatch alarms are actually actionable, and test that SNS or the incident tool really receives them.

## 2. Logs are not uploading from a healthy EC2 instance to S3. How do you investigate?

**Answer:**

First I confirm the log collector is actually reading current files, that its local spool disk is healthy, and that it attempted an upload at all.

Then I check permissions. I run `aws sts get-caller-identity` to see which role the instance is actually using, and check the target bucket, region, and prefix. I look for `s3:PutObject` permission, any explicit denies coming from the bucket policy, an SCP, or a permissions boundary, and the KMS `Encrypt`/`GenerateDataKey` permissions if the bucket uses KMS encryption. I also check required tags or conditions, clock skew, and multipart upload failures.

I look at the collector's own error logs and at CloudTrail data events for that bucket, without ever printing credentials to the screen.

Once I find the real cause, I fix that one thing: the collector, the IAM policy, the KMS permission, the path, or the storage config. Then I verify a fresh object lands with the right encryption and metadata, and that downstream consumers pick it up.

To stop it recurring, I use instance or task roles instead of long-lived keys, keep permissions scoped to only what's needed, and alert on collector backlog, upload age, and error counts.

## 3. How would you monitor an EC2 CPU incident?

**Answer:**

First I check the basics in CloudWatch: how long the high CPU has lasted, whether customers are actually affected, instance status checks, autoscaling activity, any recent deployments or config changes, and CPU credit exhaustion if it's a burstable instance type.

Then on the host itself, I compare load average, user versus system CPU time, CPU steal, I/O wait, and the top processes.

To stabilize things, I shift traffic away, scale out, roll back a bad deployment, or stop a runaway job once I've confirmed it's safe to stop. I avoid rebooting before I've captured evidence of what was happening.

The real fix depends on what I find. It could be profiling the code, fixing a slow query or cache, correcting a scheduled job, improving autoscaling triggers, or moving to a better-suited instance type.

Afterward, I confirm user-facing latency and error rates are back to normal under load, and I set up alerts for CPU running close to its limit, credit exhaustion, request queueing, and failed scaling events.
