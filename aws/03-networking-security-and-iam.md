# AWS: Networking, Security, and IAM

> NAT gateways, security groups vs NACLs, IAM roles and users, secure S3 access, and IAM and secrets best practices.

## Key Concepts

### Internet Gateway vs. NAT Gateway

An **Internet Gateway (IGW)** attaches to a VPC and gives it a route target for internet traffic. A resource in a public subnet is only actually reachable from the internet if routing, a public IPv4/IPv6 address, security groups, network ACLs, and the service itself all allow it.

Typical public endpoints are internet-facing load balancers and deliberately exposed bastion hosts.

A **NAT Gateway** does source NAT for outbound IPv4 connections from private subnets. Private instances route their internet-bound traffic to the NAT Gateway, which reaches the internet through an IGW.

It does not accept unsolicited inbound connections back to those private instances. Design NAT Gateway placement and routing per Availability Zone, so you avoid depending on another AZ and paying its cross-AZ cost.

```text
Public workload: public subnet route -> IGW -> internet
Private egress:  private subnet route -> NAT Gateway -> IGW -> internet
```

Use **VPC endpoints** for supported AWS services when private access, tighter policy control, availability, or avoiding NAT cost makes it worthwhile. When troubleshooting, check the subnet route table, the NAT/IGW association, whether the address is public or private, the security group, the stateless network ACL's return ports, DNS resolution, and flow logs.

Having an IGW or NAT resource in place doesn't by itself prove that end-to-end connectivity actually works.

### Application Load Balancer vs. Network Load Balancer

An Application Load Balancer works at Layer 7, for HTTP/HTTPS. It understands hosts, paths, headers, methods, redirects, and WebSockets, checks target health, and can integrate with WAF and authentication.

I pick it for web applications, APIs, ingress-style routing, and cases where several services sit behind one endpoint.

A Network Load Balancer works at Layer 4, for TCP, TLS, and UDP. It's built for very high throughput and low latency, preserves the client's source IP in supported modes, and gives you static IP addresses or Elastic IPs.

I pick it for non-HTTP protocols, when clients need a fixed IP to allow-list, or when a workload specifically needs Layer-4 behavior.

Other things that factor into the choice: where TLS terminates, target type, cross-zone load balancing and its cost, health checks, idle connection timeouts, whether clients need to see the real source IP, security groups, whether the load balancer is internal or internet-facing, logging/metrics, and how it behaves if a zone fails.

To troubleshoot, I trace the path in order: DNS → listener → rule → target group → target health and port → security group/NACL/route → application response. A healthy load-balancer resource doesn't mean the application behind it is actually reachable.

### AWS Network Security

- **Networking:** private subnets for workloads, tight security groups that reference other security groups, NACLs, VPC endpoints, WAF and Shield at the edge, encryption in transit (TLS) and at rest (KMS), and flow logs plus GuardDuty and CloudTrail for detecting problems.

## Interview Questions

<details><summary>Q1. [Basic] What are the main components of an AWS VPC?</summary>

**Answer:**

A VPC is an isolated network with one or more non-overlapping CIDR blocks. Subnets divide it up by availability zone and purpose.

Route tables decide the next hop for traffic. An Internet Gateway provides a path for public IPv4/IPv6 traffic. A NAT Gateway gives private subnets IPv4 outbound access. An egress-only Internet Gateway handles outbound-only IPv6. Security groups are stateful controls on network interfaces, while network ACLs are stateless controls at the subnet level.

Real-world designs also need DNS settings and Route 53 private zones, Elastic Network Interfaces and addresses, VPC endpoints/PrivateLink, load balancers, flow logs, DHCP options, and connectivity through peering, Transit Gateway, VPN, or Direct Connect.

A subnet is "public" because its route table sends traffic to an Internet Gateway and the resource in it has a public address — not simply because an Internet Gateway happens to exist somewhere in the VPC.

For high availability, I use multiple AZs, keep public and private subnets independent, apply least-privilege routing and security (giving only the access that's needed), control egress, turn on flow logs, and plan IP capacity ahead of time. I test both the forward and return paths, and avoid overlapping CIDRs that would block future connectivity.

</details>

<details><summary>Q2. [Advanced] Design a VPC with subnets, security groups; explain networking (production) <em>(asked in interview round)</em></summary>

- **VPC** with a planned CIDR (e.g. `10.0.0.0/16`), spanning **at least 2 AZs** for high availability.
- **Subnets per AZ:** public (ALB/NAT), private-app (compute), private-data (RDS) — a 3-tier layout.
- **Routing:** public subnets route to the Internet Gateway; private subnets route to a **NAT Gateway** for outbound-only access (one per AZ, for HA). DB subnets get no internet route at all.
- **Security groups (stateful, per-instance):** the ALB's security group allows port 443 from the internet; the app's security group allows traffic **from the ALB's security group**; the DB's security group allows port 5432 **from the app's security group**. Reference other security groups, not raw CIDR ranges.
- **NACLs (stateless, per-subnet):** a coarser allow/deny layer on top of security groups.
- **Add-ons:** VPC endpoints (S3/ECR) to keep that traffic off the public internet, flow logs for auditing, and multi-AZ everywhere.

</details>

<details><summary>Q3. [Basic] Why can't you attach an Internet Gateway directly to a public subnet?</summary>

**Answer:**

An Internet Gateway attaches to the VPC as a whole, not to an individual subnet. A subnet becomes "public" when its route table sends internet-bound traffic (like `0.0.0.0/0`) to that Internet Gateway, and an instance or load balancer in it has a public IPv4/Elastic IP or the right IPv6 address.

Security groups and network ACLs still need to allow the traffic too.

This matters because several public subnets across different availability zones can all share the same VPC-level attachment while each has its own separate route-table association.

A route by itself doesn't translate a private IPv4 address into a public one. And an Internet Gateway doesn't create unsolicited access on its own — if the resource has no public address, or its security rules deny the traffic, the traffic still won't get through.

</details>

<details><summary>Q4. [Basic] How can a server in a private subnet access the internet securely?</summary>

**Answer:**

For IPv4, the private subnet's route table normally sends `0.0.0.0/0` to a NAT Gateway sitting in a public subnet, and that public subnet in turn routes to the Internet Gateway.

I deploy a NAT Gateway per AZ, both for availability and to avoid cross-AZ traffic and its extra cost, and I check the server's security group, NACLs, DNS, the return path, and the NAT Gateway's health.

A self-managed NAT instance is possible, but it needs its own HA design, patching, packet forwarding, and source/destination-check setup.

For talking to other AWS services, I prefer gateway or interface VPC endpoints, so that traffic never has to cross the public internet or go through NAT at all. An egress firewall or proxy, DNS policy, allow-lists, TLS validation, flow logs, and least-privilege endpoint policies all help limit where traffic can actually go.

IPv6 uses an egress-only Internet Gateway for outbound-initiated access.

When troubleshooting, I test DNS, `ip route`, TCP/TLS, NAT Gateway metrics, route table associations, flow logs, and the actual response from the destination — testing from the affected subnet itself, not just from a public bastion.

</details>

<details><summary>Q5. [Basic] What is a NAT Gateway, and where is it deployed?</summary>

**Answer:**

A NAT Gateway lets workloads in a private subnet make outbound IPv4 connections without accepting unsolicited traffic from the internet. It sits in a public subnet with an Elastic IP and a route to an Internet Gateway. Private subnet route tables send `0.0.0.0/0` traffic to it.

For resilience, I deploy one NAT Gateway per Availability Zone, and route each private subnet to the NAT Gateway in its own zone. Where possible, I use VPC endpoints for AWS services like S3 instead, to cut cost and reduce the dependency on internet access altogether.

</details>

<details><summary>Q6. [Basic] What is the difference between a security group and a network ACL?</summary>

**Answer:**

A security group is a stateful, allow-only firewall attached to a resource's network interface. Return traffic is automatically allowed, and rules can reference another security group.

A network ACL is a stateless boundary at the subnet level. It has ordered allow and deny rules, and you have to explicitly allow both inbound and outbound return traffic.

I use security groups for the normal application traffic path, scoped to only what's needed, and NACLs for coarse subnet-level guardrails or when I need an explicit deny. When troubleshooting, I check route tables, both directions of traffic, ephemeral ports, and the actual network interface or subnet involved — not just open everything up with `0.0.0.0/0`.

</details>

<details><summary>Q7. [Basic] How do you connect to an EC2 instance?</summary>

**Answer:**

My preferred way is over the private IP, through a VPN or bastion, or with AWS Systems Manager Session Manager — I avoid public SSH when I can. If SSH is approved:

```bash
chmod 600 key.pem
ssh -i key.pem -o IdentitiesOnly=yes ec2-user@host
```

The username depends on the AMI. The network path needs a route, and the security group/NACL/firewall needs to allow port 22, with `sshd` running on the instance. I check the host key, never share the private key, and use short-lived, certificate-based, or SSM access wherever possible.

**Failure steps:** check DNS/IP, run `nc -vz host 22`, check the security group/NACL/route, confirm the instance and `sshd` are up (via SSM or the console), run `ssh -vvv` for verbose output, and check user/key/`authorized_keys` permissions and the auth logs. I don't open `0.0.0.0/0` as a shortcut.

</details>

<details><summary>Q8. [Intermediate] How do you access an EC2 instance in a private subnet?</summary>

**Answer:**

My preferred option is AWS Systems Manager Session Manager, using an instance profile and either private SSM VPC endpoints or controlled egress. It avoids inbound SSH entirely, gives IAM/MFA control and audit logs, and doesn't require distributing private keys.

Where SSH is genuinely required, I connect through a corporate VPN/Direct Connect or an approved hardened bastion, using `ProxyJump`. The private instance's security group only allows port 22 from the bastion's security group or a specific admin CIDR.

I check the instance is healthy, the route and return path exist, NACLs allow the flow and the ephemeral return ports, the security group is correct, DNS resolves privately, and `sshd`/the host firewall and the user's key are valid. EC2 Instance Connect Endpoint is another controlled option where it's supported.

I never assign a public IP or open SSH to `0.0.0.0/0` just to troubleshoot. Access should be time-bound, least-privilege, logged, and removed once the issue is resolved.

</details>

<details><summary>Q9. [Basic] IAM role versus IAM user: when do you use each?</summary>

**Answer:**

An IAM role hands out temporary credentials to a workload, or to a federated human identity, and it can be assumed with narrowly scoped permissions. An IAM user is a long-lived AWS identity — it's really a legacy option now, only for the rare case where federation or roles genuinely don't work.

I use roles for EC2, Lambda, ECS/EKS workloads, CI, and human access through SSO. I require MFA and give every role only the permissions it needs. I avoid static access keys, rotate any I can't avoid, and review CloudTrail logs along with permission boundaries and SCPs.

</details>

<details><summary>Q10. [Intermediate] Security best practices for AWS IAM and secrets <em>(asked in interview round)</em></summary>

- **IAM:** Give every identity only the permissions it needs, nothing more. Prefer roles over long-lived keys. Use IAM roles for service accounts (IRSA) in EKS and OIDC for CI. Require MFA for humans. Avoid wildcard `*` policies. Use permission boundaries and SCPs in AWS Organizations. Rotate any access key you can't avoid using, and audit access with IAM Access Analyzer.
- **Secrets:** Keep them in Secrets Manager or SSM Parameter Store, never in code. Log and monitor everything.

</details>

<details><summary>Q11. [Intermediate] How do you grant an application access to an S3 bucket safely?</summary>

**Answer:**

I attach an IAM role to the workload — an EC2 instance profile, ECS task role, Lambda execution role, or EKS workload identity — and give it only the actions and prefix it actually needs. For example, `s3:GetObject` on `arn:aws:s3:::reports-bucket/approved/*`, and `s3:ListBucket` restricted by `s3:prefix`.

The bucket policy, IAM policy, permission boundary, SCP, VPC endpoint policy, and KMS key policy all have to allow the access — and an explicit deny anywhere wins over all of them.

I keep Block Public Access turned on unless there's a deliberate reason to serve public content, require TLS and encryption, audit CloudTrail data events where it matters, and test both an allowed operation and a denied one to make sure the policy actually works as intended.

</details>

<details><summary>Q12. [Intermediate] Secure an S3 bucket used for static website hosting <em>(asked in interview round)</em></summary>

- **Don't make the bucket public.** Serve it through CloudFront with Origin Access Control (OAC). Keep Block Public Access turned on, and only let CloudFront read from the bucket, through a bucket policy.
- **Force HTTPS.** Enforce it with a bucket policy condition (`aws:SecureTransport`), plus a CloudFront redirect-to-HTTPS rule and an ACM certificate.
- **Encrypt data at rest** (SSE-S3 or SSE-KMS), turn on **versioning** so you can recover from mistakes, and turn on **logging** (CloudTrail data events or S3 server access logs).
- Add **WAF** on CloudFront. Give IAM only the permissions it actually needs, and disable ACLs (bucket-owner-enforced). Nothing but the static assets should be reachable, and nothing should be writable from the public internet.

</details>

<details><summary>Q13. [Basic] Which types of load balancers have you used in AWS and Kubernetes?</summary>

**Answer:**

| Load balancer | Layer | Use |
| --- | --- | --- |
| **Application Load Balancer (ALB)** | 7 (HTTP/HTTPS, gRPC) | Web apps and APIs: host and path routing, TLS termination with ACM, WAF, authentication with Cognito or OIDC |
| **Network Load Balancer (NLB)** | 4 (TCP/UDP/TLS) | Very high throughput, low latency, static IPs, non-HTTP protocols, PrivateLink services |
| **Gateway Load Balancer (GWLB)** | 3 | Inserting third-party firewalls or inspection appliances |
| **Classic Load Balancer (CLB)** | 4/7 | Legacy only; migrate to ALB or NLB |

In Kubernetes on EKS:

- A `Service` of type `LoadBalancer` creates an **NLB** (with the AWS Load Balancer Controller and the right annotations).
- An `Ingress` (or Gateway API route) with the AWS Load Balancer Controller creates an **ALB**, often shared by many services through ingress groups.
- An NGINX ingress controller behind one NLB is another common pattern.

Example answer: "We used one internet-facing ALB per environment through the AWS Load Balancer Controller, with path-based routing to our services, ACM certificates and AWS WAF, and internal NLBs for TCP services such as a message broker."

</details>

<details><summary>Q14. [Intermediate] You have multiple servers. How would you identify the servers that do not have the required tags? Explain your scripting/automation approach. <em>(asked in interview round)</em></summary>

**Answer:**

I treat this as two problems: **finding** non-compliant resources today (a script or query) and **preventing/continuously detecting** them tomorrow (AWS Config, tag policies, SCPs). A one-off script answers the question; governance stops it from coming back.

**Approach:**

1. Agree on the required tag keys, for example `Owner`, `Environment`, `CostCenter`, `Application`.
2. Run an inventory query per account and Region (EC2 API, or the Resource Groups Tagging API for many resource types).
3. Output a report (CSV) with instance ID, name, missing tags and account/Region.
4. Notify owners or auto-remediate (tag with `Owner=unknown` and raise a ticket, never delete).
5. Turn on continuous detection with the AWS Config `required-tags` managed rule and enforce at creation time with an SCP or tag policy.

```text
Required tag list
      |
      v
Script / query  (per account, per Region)
      |
      v
Report: instance-id, missing tags  --->  Owners / ticket
      |
      v
AWS Config required-tags rule (continuous)  --->  Security Hub / SNS
      |
      v
SCP / tag policy (prevent untagged creation)
```

**Quick check with the AWS CLI and a `JMESPath` query:**

This lists EC2 instances that have no `Owner` tag (works whether the instance has no tags at all or just lacks that key):

```bash
aws ec2 describe-instances \
  --region us-east-1 \
  --query "Reservations[].Instances[?!(Tags[?Key=='Owner'])].[InstanceId, State.Name]" \
  --output text
```

**Reusable Python script (several tags, all Regions):**

```python
#!/usr/bin/env python3
"""Report EC2 instances missing required tags across all enabled Regions."""
import csv
import sys

import boto3

REQUIRED_TAGS = {"Owner", "Environment", "CostCenter", "Application"}

def regions():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]

def main():
    writer = csv.writer(sys.stdout)
    writer.writerow(["region", "instance_id", "name", "state", "missing_tags"])
    for region in regions():
        ec2 = boto3.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for inst in reservation["Instances"]:
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    # Treat empty values as missing too
                    missing = sorted(k for k in REQUIRED_TAGS if not tags.get(k, "").strip())
                    if missing:
                        writer.writerow([
                            region,
                            inst["InstanceId"],
                            tags.get("Name", ""),
                            inst["State"]["Name"],
                            ";".join(missing),
                        ])

if __name__ == "__main__":
    main()
```

It is read-only (`ec2:DescribeInstances`, `ec2:DescribeRegions`), uses pagination so it works with thousands of instances, and can run from a Lambda on a schedule or across accounts by assuming a read-only role in each account.

**Continuous detection with AWS Config:**

```bash
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "ec2-required-tags",
  "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
  "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance"]},
  "InputParameters": "{\"tag1Key\":\"Owner\",\"tag2Key\":\"Environment\",\"tag3Key\":\"CostCenter\"}"
}'
```

Deploy it organization-wide with a conformance pack or an organization Config rule, and view results in an aggregator.

**Prevention:**

- **SCP** that denies `ec2:RunInstances` when `aws:RequestTag/Owner` is null, so untagged instances cannot be created.
- **Tag policies** (AWS Organizations) standardize tag keys and allowed values and report non-compliance.
- **IaC defaults**: Terraform `default_tags` in the AWS provider so every resource gets the mandatory tags.

**Azure equivalent:**

- Azure Resource Graph query: `resources | where type =~ 'microsoft.compute/virtualmachines' | where isnull(tags['Owner'])`.
- Azure Policy built-in "Require a tag on resources" (deny) or "Inherit a tag from the resource group" (modify).

**Important points:**

- The Resource Groups Tagging API (`aws resourcegroupstaggingapi get-resources`) only returns resources that are or were tagged, so resources that never had a tag can be missed. For a complete list use the service API (EC2 `describe-instances`) or AWS Config / Resource Explorer.
- Check empty values as well as missing keys.
- Run across all accounts and Regions, not just the default one.
- Auto-remediation should tag or notify, not stop or terminate production servers.

See also: [Automation shell and Python examples](../repetitive-questions/automation-shell-and-python-examples.md), [Python automation, APIs and data](../python/03-automation-apis-and-data.md).

**Interview-ready answer:**

> "First I agree on the mandatory tags, such as Owner, Environment and CostCenter. For a quick check I use `aws ec2 describe-instances` with a `JMESPath` query, and for a real report I use a `boto3` script that paginates through every Region, compares each instance's tags with the required set, treats empty values as missing, and writes a CSV. I don't rely only on the Tagging API because it can miss resources that were never tagged. To keep it compliant I enable the AWS Config `required-tags` rule across the organization, and I prevent the problem at creation time with an SCP on `aws:RequestTag` plus Terraform `default_tags`. Remediation is notify or tag, never terminate. In Azure, the equivalent is a Resource Graph query plus Azure Policy."

</details>

<details><summary>Q15. [Intermediate] Is a NAT Gateway required? <em>(asked in interview round)</em></summary>

**Answer:**

**It depends.** A NAT Gateway is required only when resources in **private IPv4 subnets need to initiate outbound connections to the internet** (OS patches, third-party APIs, public package repositories, AWS services without a VPC endpoint). It is **not** needed for inbound traffic: users reach private servers through the ALB.

**When you need it:**

- Private EC2/EKS nodes download updates or call external APIs.
- Pods pull images from Docker Hub or other public registries.
- No VPC endpoints exist for the AWS services you call.

**When you may not need it:**

- All AWS dependencies are reached through VPC endpoints (S3, ECR, CloudWatch Logs, STS, Secrets Manager, SSM).
- Outbound goes through a centralized egress VPC (Transit Gateway + shared NAT/firewall).
- The workload uses IPv6 with an egress-only Internet Gateway.
- Fully isolated workloads (databases) that never call out.

**HA configuration:**

A NAT Gateway is a **zonal** resource. For high availability, create one per AZ and point each private route table to the NAT in the same AZ; a single NAT is a single point of failure and adds cross-AZ data charges. AWS has also introduced a regional availability mode for NAT Gateway that spans AZs; check whether it fits your design and Region.

```bash
aws ec2 create-nat-gateway --subnet-id subnet-public-a --allocation-id eipalloc-0abc123
aws ec2 create-route --route-table-id rtb-private-a \
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0aaa111
```

**Cost points:**

- NAT Gateway charges per hour **and** per GB processed. Heavy S3 or ECR traffic through NAT is a common hidden cost; a free S3 gateway endpoint removes it.
- For dev environments, one NAT per VPC may be an acceptable trade-off.

See also: [AWS networking, security and IAM (NAT Gateway)](../aws/03-networking-security-and-iam.md).

**Interview-ready answer:**

> "A NAT Gateway is only required when instances in private subnets need to start outbound connections to the internet, for example to download patches or call third-party APIs. Inbound traffic doesn't need it because it comes through the load balancer. If all the dependencies are AWS services, I can often avoid or reduce NAT usage with VPC endpoints, especially the free S3 and DynamoDB gateway endpoints. For production I deploy one NAT Gateway per AZ with matching route tables so an AZ failure doesn't cut off egress. I also watch the NAT data processing charges, because that is often a surprising part of the bill."

</details>

<details><summary>Q16. [Intermediate] Can a private subnet communicate without a NAT Gateway? <em>(asked in interview round)</em></summary>

**Answer:**

**Yes.** A NAT Gateway is only for outbound IPv4 traffic to the internet. A private subnet can communicate in many other ways.

| Destination | How, without NAT |
| --- | --- |
| Other resources in the same VPC | Built-in `local` route; every subnet can reach every other subnet (subject to SGs/NACLs) |
| Amazon S3, DynamoDB | **Gateway VPC endpoint** (free; route table entry) |
| Other AWS services (ECR, STS, SSM, Secrets Manager, CloudWatch, KMS) | **Interface VPC endpoints** (AWS PrivateLink; ENIs with private IPs; hourly + per-GB charge) |
| Other VPCs | VPC peering or Transit Gateway |
| On-premises | Site-to-Site VPN or Direct Connect via a virtual private gateway or TGW |
| Internet via another VPC | Transit Gateway to a centralized egress VPC with a shared NAT/firewall |
| Internet over IPv6 | **Egress-only Internet Gateway** (outbound only) |
| SaaS / partner services | PrivateLink endpoint services |

```text
Private subnet
   |-- local route ----------------> other subnets in the VPC
   |-- gateway endpoint -----------> S3 / DynamoDB
   |-- interface endpoint (ENI) ---> ECR, STS, SSM, Secrets Manager
   |-- TGW / peering --------------> other VPCs, egress VPC, on-prem
   |-- egress-only IGW (IPv6) -----> internet (outbound only)
```

**Example: private EKS nodes without NAT:**

```bash
# Free gateway endpoint for S3 (ECR image layers are stored in S3)
aws ec2 create-vpc-endpoint --vpc-id vpc-0abc --vpc-endpoint-type Gateway \
  --service-name com.amazonaws.us-east-1.s3 --route-table-ids rtb-private-a rtb-private-b

# Interface endpoints with private DNS
for svc in ecr.api ecr.dkr sts logs ssm ssmmessages ec2messages; do
  aws ec2 create-vpc-endpoint --vpc-id vpc-0abc --vpc-endpoint-type Interface \
    --service-name "com.amazonaws.us-east-1.${svc}" \
    --subnet-ids subnet-app-a subnet-app-b \
    --security-group-ids sg-endpoints --private-dns-enabled
done
```

**Important points:**

- Interface endpoints need private DNS enabled and a security group that allows HTTPS (443) from the subnets.
- Gateway endpoints only work for S3 and DynamoDB and only from within the same Region.
- Endpoint policies can restrict which buckets or actions are allowed.
- Calls to public internet APIs (GitHub, Docker Hub) still need NAT, a proxy or an egress VPC.

See also: [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md).

**Interview-ready answer:**

> "Yes. Inside the VPC, every subnet can talk to every other subnet through the local route. For AWS services I use VPC endpoints: gateway endpoints for S3 and DynamoDB, which are free, and interface endpoints through PrivateLink for services like ECR, STS, SSM and Secrets Manager. To reach other VPCs or on-premises I use peering, Transit Gateway, VPN or Direct Connect, and in larger setups internet egress goes through a central egress VPC over the Transit Gateway. For IPv6, an egress-only Internet Gateway gives outbound-only internet access. NAT is only needed when private IPv4 resources must reach the public internet directly."

</details>

<details><summary>Q17. [Intermediate] What are the Route 53 routing policies? Give practical use cases. <em>(asked in interview round)</em></summary>

**Answer:**

A routing policy decides **which answer** Route 53 returns for a DNS query. Health checks can be attached to most policies so unhealthy endpoints are removed from answers.

**Routing policies:**

| Policy | How it answers | Practical use case |
| --- | --- | --- |
| Simple | Returns the record's value(s); no health checks | Single web server or one ALB for `www.example.com` |
| Weighted | Splits answers by weight (for example 90/10) | Canary or Blue-Green between two ALBs or regions; A/B testing |
| Latency | Returns the region with the lowest latency for the user | Multi-region app in `us-east-1` and `eu-west-1` |
| Failover | Primary while healthy, otherwise secondary | Active-passive DR: primary ALB, secondary S3 static page or DR region |
| Geolocation | Based on the user's continent, country or US state | Serve EU users from EU for data residency; block or localize content |
| Geoproximity | Based on distance between user and resources, adjustable with a bias | Shift more traffic to a region by increasing its bias |
| Multivalue answer | Returns up to 8 healthy records at random | Simple client-side load balancing across several EC2 instances |
| IP-based | Based on the client's source IP CIDR | Route a known ISP or corporate network to a specific endpoint |

**Example: failover flow:**

```text
User --> app.example.com
            |
            v
     Route 53 failover record
       |-- PRIMARY  --> ALB us-east-1  (health check: /health)
       |-- SECONDARY --> ALB us-west-2 (used only if primary health check fails)
```

**Example: weighted records with the CLI:**

```bash
cat > weighted.json <<'EOF'
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "CNAME",
        "SetIdentifier": "blue",
        "Weight": 90,
        "TTL": 60,
        "ResourceRecords": [{ "Value": "blue-alb-123.us-east-1.elb.amazonaws.com" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "CNAME",
        "SetIdentifier": "green",
        "Weight": 10,
        "TTL": 60,
        "ResourceRecords": [{ "Value": "green-alb-456.us-east-1.elb.amazonaws.com" }]
      }
    }
  ]
}
EOF
aws route53 change-resource-record-sets --hosted-zone-id Z0123456789ABC --change-batch file://weighted.json
```

**Important points:**

- Use **alias** records for AWS targets (ALB, CloudFront, S3 website); they work at the zone apex and have no query charge.
- DNS changes depend on TTL and client caching; use a low TTL (for example 60 seconds) before a planned switch.
- Geolocation needs a default record, otherwise users from unmatched locations get no answer.
- Policies can be combined in nested records or Traffic Flow (for example latency first, then weighted inside a region).

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md) and [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md).

**Interview-ready answer:**

> "Route 53 has simple, weighted, latency, failover, geolocation, geoproximity, multivalue answer and IP-based routing. I use simple for a single endpoint, weighted for canary or Blue-Green between two load balancers, and latency for multi-region applications so users reach the nearest region. Failover with health checks gives active-passive disaster recovery. Geolocation helps with data residency or localized content, geoproximity lets me shift traffic with a bias, multivalue returns several healthy IPs, and IP-based routes known client networks. I use alias records for AWS resources and keep TTLs low before planned switches."

</details>

<details><summary>Q18. [Intermediate] How do you connect EC2 to RDS? <em>(asked in interview round)</em></summary>

**Answer:**

The EC2 instance and the RDS instance must have a **network path** (same VPC or a peered VPC), the RDS **security group** must allow the database port from the EC2 security group, and the application connects to the RDS **endpoint DNS name** on the engine port using credentials from Secrets Manager or IAM authentication, over TLS.

**Network flow:**

```text
VPC 10.0.0.0/16
  |
  |-- Private app subnet:  EC2 (sg-app)
  |        |
  |        | TCP 5432 / 3306 to mydb.abc123.us-east-1.rds.amazonaws.com
  |        v
  |-- Private DB subnets (DB subnet group, 2+ AZs): RDS (sg-db)
           sg-db inbound: port 5432 from source sg-app (not from 0.0.0.0/0)
```

**Steps:**

1. Create RDS in a **DB subnet group** with private subnets in at least two AZs; **Public access = No**.
2. Security group on RDS: inbound rule for the engine port with **source = the EC2 security group** (SG referencing SG), so any instance in that group is allowed even if its IP changes.
3. Security group on EC2: outbound allowed to the database port (default outbound allows all).
4. Get the endpoint and port: `aws rds describe-db-instances --db-instance-identifier mydb --query 'DBInstances[0].Endpoint'`.
5. Store credentials in **Secrets Manager** (RDS can manage the master password there with rotation) or use **IAM database authentication**.
6. Connect over TLS using the RDS CA bundle.

**Example: security group rule:**

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0db1234567890abcd \
  --protocol tcp --port 5432 \
  --source-group sg-0app1234567890abcd
```

**Example: connect with a password from Secrets Manager:**

```bash
curl -sO https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

SECRET=$(aws secretsmanager get-secret-value --secret-id prod/orders/db \
  --query SecretString --output text)
export PGPASSWORD=$(echo "$SECRET" | jq -r .password)

# PostgreSQL
psql "host=mydb.abc123.us-east-1.rds.amazonaws.com port=5432 dbname=orders \
      user=app_user sslmode=verify-full sslrootcert=global-bundle.pem"

# MySQL
mysql -h mydb.abc123.us-east-1.rds.amazonaws.com -P 3306 -u app_user -p \
      --ssl-mode=VERIFY_IDENTITY --ssl-ca=global-bundle.pem
```

**Example: IAM database authentication:**

```bash
# The EC2 role needs rds-db:connect on arn:aws:rds-db:us-east-1:123456789012:dbuser:db-ABCDEFGHIJKL/app_user
# In PostgreSQL: CREATE USER app_user; GRANT rds_iam TO app_user;
TOKEN=$(aws rds generate-db-auth-token \
  --hostname mydb.abc123.us-east-1.rds.amazonaws.com --port 5432 \
  --region us-east-1 --username app_user)

PGPASSWORD="$TOKEN" psql "host=mydb.abc123.us-east-1.rds.amazonaws.com port=5432 \
  dbname=orders user=app_user sslmode=verify-full sslrootcert=global-bundle.pem"
```

The token is valid for 15 minutes for opening new connections, and IAM authentication requires SSL.

**Troubleshooting connection failures:**

| Symptom | Likely cause |
| --- | --- |
| Timeout | Security group, NACL, route table or different VPC without peering |
| Connection refused | Wrong port or database not available |
| Name not resolving | Wrong endpoint, or VPC DNS resolution and DNS hostnames disabled |
| Authentication failed | Wrong password, expired IAM token, user missing `rds_iam` grant |

```bash
nc -zv mydb.abc123.us-east-1.rds.amazonaws.com 5432
```

**Important points:**

- Always use the endpoint DNS name, never the IP; it changes after a Multi-AZ failover.
- Keep RDS private; connect from outside through SSM Session Manager port forwarding or a VPN rather than making it public.
- The RDS console "Connect to EC2" option can create the paired security groups automatically.

See also: [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md).

**Interview-ready answer:**

> "I put RDS in private subnets through a DB subnet group with public access disabled, in the same VPC as the EC2 instance or a peered one. The RDS security group allows the database port, such as 5432 for PostgreSQL, only from the EC2 instance's security group, so I reference the security group instead of IP addresses. The application connects to the RDS endpoint DNS name and port, never the IP, because the IP changes after failover. Credentials come from Secrets Manager with rotation, or I use IAM database authentication where the EC2 role generates a 15-minute token. I enforce TLS with the RDS CA bundle and test the path with `nc` before checking the application."

</details>

<details><summary>Q19. [Intermediate] Secure an S3 bucket used for static website hosting. <em>(asked in interview round)</em></summary>

**Answer:**

Do not use the S3 website endpoint for production: it only supports HTTP and requires a public bucket. Keep the bucket private and serve it through CloudFront with Origin Access Control (OAC).

1. Enable S3 Block Public Access at bucket and account level; Object Ownership set to bucket owner enforced (ACLs disabled).
2. Use the bucket's REST endpoint as a CloudFront origin with OAC.
3. Bucket policy allows `s3:GetObject` only to the CloudFront service principal for that distribution.
4. HTTPS only with an ACM certificate, AWS WAF, security headers policy.
5. Default encryption, versioning, access logging.

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "cloudfront.amazonaws.com" },
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-site-bucket/*",
  "Condition": { "StringEquals": { "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE" } }
}
```

**Interview-ready answer:**

> I keep the bucket fully private with Block Public Access on and ACLs disabled, and I do not use the S3 website endpoint because it is HTTP-only and needs public access. CloudFront sits in front using Origin Access Control, and the bucket policy allows reads only from that specific distribution via the `AWS:SourceArn` condition. CloudFront enforces HTTPS with an ACM certificate, WAF and security headers. The bucket also has encryption, versioning and access logging.

See also: [Secure an S3 bucket used for static website hosting](../aws/03-networking-security-and-iam.md)

</details>
