# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## AWS Cloud

### 7.1 Design an auto-scaling strategy for a high-traffic app

- **Compute:** Use Auto Scaling Groups for EC2, or HPA plus Cluster Autoscaler/Karpenter for EKS. Put an ALB or NLB in front, spread across multiple AZs.
- **Scaling policies:** Start with target-tracking as the baseline — for example, keep CPU near 60%, or track ALB requests per target. Add step scaling for sudden bursts, scheduled scaling for predictable peaks, and predictive scaling for known daily patterns.
- **Keep the app tier stateless** so instances are disposable. Store sessions in Redis or DynamoDB instead of on the instance.
- **Downstream:** Scale the data layer too — RDS read replicas or Aurora Auto Scaling, DynamoDB on-demand. Add CloudFront plus caching, and use SQS to absorb traffic spikes.
- **Guardrails:** Set min/max bounds, use warm pools so scale-out is fast, add health checks, and set cost alarms.

### 7.2 Secure an S3 bucket used for static website hosting

- **Don't make the bucket public.** Serve it through CloudFront with Origin Access Control (OAC). Keep Block Public Access turned on, and only let CloudFront read from the bucket, through a bucket policy.
- **Force HTTPS.** Enforce it with a bucket policy condition (`aws:SecureTransport`), plus a CloudFront redirect-to-HTTPS rule and an ACM certificate.
- **Encrypt data at rest** (SSE-S3 or SSE-KMS), turn on **versioning** so you can recover from mistakes, and turn on **logging** (CloudTrail data events or S3 server access logs).
- Add **WAF** on CloudFront. Give IAM only the permissions it actually needs, and disable ACLs (bucket-owner-enforced). Nothing but the static assets should be reachable, and nothing should be writable from the public internet.

### 7.4 Design a highly available, scalable microservices architecture on AWS (auto-scaling + DR)

- Default to **multi-AZ**; add **multi-region** for disaster recovery.
- **Ingress path:** Route 53 (with health checks, latency-based or failover routing) → CloudFront/WAF → ALB.
- **Compute:** EKS or ECS Fargate, with HPA and Cluster Autoscaler/Karpenter spread across AZs. Keep services stateless.
- **Data:** Aurora Multi-AZ with a cross-region replica, DynamoDB global tables, and ElastiCache. Handle anything async through SQS, SNS, or Kafka.
- **DR strategy:** Pick one based on your recovery targets — backup-and-restore, pilot light, warm standby, or active-active. Define how much downtime and data loss you can tolerate (RTO/RPO), automate the failover, replicate both data and infrastructure code to the DR region, and actually test failover on a regular schedule.
- **Observability and resilience:** Centralize logs, metrics, and traces. Add circuit breakers and retries, pod disruption budgets, and keep infrastructure defined in Terraform so it's reproducible.

### 7.5 Security best practices for AWS IAM and secrets

- **IAM:** Give every identity only the permissions it needs, nothing more. Prefer roles over long-lived keys. Use IAM roles for service accounts (IRSA) in EKS and OIDC for CI. Require MFA for humans. Avoid wildcard `*` policies. Use permission boundaries and SCPs in AWS Organizations. Rotate any access key you can't avoid using, and audit access with IAM Access Analyzer.
- **Secrets:** Keep them in Secrets Manager or SSM Parameter Store, never in code. Log and monitor everything.

---
