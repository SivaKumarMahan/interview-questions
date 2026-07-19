# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## AWS Cloud

### 7.1 Design an auto-scaling strategy for a high-traffic app
- **Compute:** Auto Scaling Groups (EC2) or HPA + Cluster Autoscaler/Karpenter (EKS), fronted by an **ALB/NLB** across multiple AZs.
- **Scaling policies:** target-tracking (e.g. CPU 60%, or ALB request-count-per-target) as the baseline; step scaling for bursts; **scheduled scaling** for predictable peaks; predictive scaling for known daily patterns.
- **Stateless app tier** so instances are disposable; sessions in Redis/DynamoDB.
- **Downstream:** scale the data layer too (RDS read replicas/Aurora Auto Scaling, DynamoDB on-demand), add **CloudFront + caching** and SQS to absorb spikes.
- **Guardrails:** min/max bounds, warm pools for fast scale-out, health checks, and cost alarms.

### 7.2 Secure an S3 bucket used for static website hosting
- **Don't make the bucket public.** Serve via **CloudFront + Origin Access Control (OAC)**; keep **Block Public Access ON** and grant CloudFront read via bucket policy only.
- **HTTPS only:** enforce with a bucket policy condition (`aws:SecureTransport`) and CloudFront redirect-to-HTTPS + ACM cert.
- **Encryption at rest** (SSE-S3/SSE-KMS), **versioning** for recovery, and access **logging** (CloudTrail data events / S3 server access logs).
- Add **WAF** on CloudFront, least-privilege IAM, and disable ACLs (bucket-owner-enforced). Only the static assets should be reachable — nothing writable to the public.

### 7.4 Design a highly available, scalable microservices architecture on AWS (auto-scaling + DR)
- **Multi-AZ** by default; **multi-region** for DR.
- **Ingress:** Route 53 (health-checked, latency/failover routing) → CloudFront/WAF → ALB.
- **Compute:** EKS (or ECS Fargate) with HPA + Cluster Autoscaler/Karpenter across AZs; stateless services.
- **Data:** Aurora Multi-AZ (+ cross-region replica), DynamoDB global tables, ElastiCache; async via SQS/SNS/Kafka.
- **DR strategy** (pick per RTO/RPO): backup-and-restore → pilot light → warm standby → active-active. Define **RTO/RPO**, automate failover, replicate data + IaC to the DR region, and **test failover regularly**.
- **Observability & resilience:** centralized logging/metrics/tracing, circuit breakers/retries, PDBs, and IaC (Terraform) for reproducibility.

### 7.5 Security best practices for AWS IAM and secrets
- **IAM:** least privilege, roles over long-lived keys, **IAM roles for service accounts (IRSA)** in EKS and **OIDC** for CI, MFA on humans, no wildcard `*` policies, use permission boundaries + SCPs (Organizations), rotate/avoid access keys, audit with Access Analyzer.
- **Secrets:** Secrets Manager/SSM Parameter Store, never in code. Everything logged and monitored.

---
