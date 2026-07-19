# AWS Networking Interview Notes

### 7.3 Design a VPC with subnets, security groups; explain networking (production)
- **VPC** with a planned CIDR (e.g. `10.0.0.0/16`), spanning **≥2 AZs** for HA.
- **Subnets per AZ:** public (ALB/NAT), private-app (compute), private-data (RDS) — a 3-tier layout.
- **Routing:** public subnets → Internet Gateway; private subnets → **NAT Gateway** (egress only, one per AZ for HA). DB subnets have no internet route.
- **Security groups (stateful, instance-level):** ALB SG allows 443 from internet; app SG allows traffic **from the ALB SG**; DB SG allows 5432 **from the app SG** — reference SGs, not CIDRs.
- **NACLs (stateless, subnet-level):** coarse allow/deny as a second layer.
- **Add-ons:** VPC endpoints (S3/ECR) to keep traffic off the internet, flow logs for auditing, and multi-AZ everything.


## AWS Network Security

- **Networking:** private subnets for workloads, tight SGs referencing SGs, NACLs, VPC endpoints, WAF + Shield at the edge, encrypt in transit (TLS) and at rest (KMS), flow logs + GuardDuty + CloudTrail for detection.
