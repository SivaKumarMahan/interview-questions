# AWS: Monitoring and Troubleshooting

> Using CloudWatch and CloudTrail in production, investigating EC2 high CPU, and debugging failed S3 log uploads.

## Key Concepts

### EC2 High-CPU Investigation

Start with CloudWatch: CPU utilization, instance status checks, traffic, deployment and configuration history, and network/disk I/O. Install the CloudWatch Agent if you need memory or process-level metrics.

For burstable T-series instances, check the CPU credit balance and figure out whether sustained demand is burning through it.

On the host itself, find the responsible process and the type of pressure before you touch capacity:

```bash
top
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head
pidstat -u 1
```

Compare what you see against application and system logs, I/O wait, recent releases, scheduled jobs, and dependency latency. To stabilize things, use a safe rollback, a traffic shift, a rate limit, autoscaling, or terminate a process you've confirmed is safe to kill.

Then fix the actual root cause — inefficient code or a bad query, a background job, a capacity mismatch, the burst-credit model, or unexpected traffic — and confirm both user-facing latency/errors and CPU recover. Scaling out without diagnosing the cause just hides the problem and costs more.

## Interview Questions

<details><summary>Q1. [Basic] What do you use AWS CloudWatch and CloudTrail for in production?</summary>

**Answer:**

CloudWatch is where operational monitoring data lives: AWS service metrics, custom metrics, logs, dashboards, alarms, traces, synthetic checks, and event-driven actions.

I use it to watch EC2 and container resource usage, application signals, Lambda errors/duration/throttling, load balancer status and latency, and queue depth and age, and to run log queries. I build SLO dashboards and route alarms through SNS or incident tooling so they actually get acted on.

CloudTrail records AWS API activity — who or which role called an action, when, from where, against which resource, and whether it succeeded.

I centralize the organization's trails in a protected security account, turn on the right management and data events, encrypt and retain the logs, and alert on high-risk actions: policy changes, a trail getting disabled, public exposure, key changes, or an unusual role assumption.

During an incident I compare what CloudWatch shows against deployment or config changes and CloudTrail's API evidence. Neither tool replaces application tracing or full OS-level metrics. CloudTrail is an audit trail, not a real-time performance monitor.

</details>

<details><summary>Q2. [Intermediate] An EC2 instance reaches 100% CPU. How do you investigate and recover it?</summary>

**Answer:**

First I check how long this has been happening, whether customers are actually affected, the instance status checks, the current load, any recent deploys, autoscaling activity, and — if it's a burstable (T-series) instance — whether it has run out of CPU credits.

Then I connect through SSM or SSH and run `uptime`, `top`, `ps`, and `pidstat`, along with application metrics, to figure out what's actually using the CPU: user time, system time, steal time, I/O wait, a runaway process, garbage collection, a traffic spike, a cron job, an agent, or possibly a compromise.

To stabilize things, I shift traffic away, scale out, rate-limit, stop a runaway process I've confirmed is safe to stop, or roll back a bad release. I avoid rebooting first unless the host is truly unrecoverable — a reboot destroys the evidence I need and often just moves the problem elsewhere.

If there's any sign of compromise, I isolate the host and start incident response instead of just restarting it.

The real fix might be profiling the application, improving a query or cache, setting resource limits, fixing a scheduled job, autoscaling on a better signal, choosing a different instance type, or general capacity planning.

Afterward I confirm latency, errors, and CPU actually recover under real load, and I add alerts for saturation — how close the resource is to its limit — plus credit exhaustion, queueing, and scaling failures.

</details>

<details><summary>Q3. [Intermediate] A server is healthy and has network connectivity, but logs are not uploading to an S3 bucket. What do you investigate?</summary>

**Answer:**

I break the problem into pieces: is the log agent reading files correctly, is it authenticated, does it have permission on the bucket, and is the upload itself actually succeeding?

First I check the log agent. Is it reading the right path? Does it have permission on the files? Is it stuck behind a lock or a full spool disk? Are there any recent errors in its own logs?

Next I test the AWS identity directly. I run `aws sts get-caller-identity`, then try a small test upload to the exact bucket and prefix, without printing the credentials.

Common causes I look for: an expired or wrong credential, the wrong instance profile or region, a missing `s3:PutObject` permission, an explicit deny somewhere (bucket policy, SCP, or permissions boundary), a required object tag or ACL condition, a KMS key policy that's missing `kms:Encrypt` or `kms:GenerateDataKey`, Object Lock, a wrong prefix, clock skew, a failed multipart upload, or a storage-class/lifecycle rule getting in the way.

CloudTrail data events and S3's own server-side logs show whether AWS actually received the request and denied it, or never saw it at all.

Once I find the real cause, I fix that one thing — the policy, the key permission, the agent config, the disk space, or file ownership — and then confirm a new object actually lands, with the right encryption and metadata, and that downstream systems pick it up.

Going forward, I use an instance role that only has the permissions it needs, watch agent health and backlog metrics, set limits on any dead-letter or spool queue, and alert if uploads get too old or start failing.

</details>

<details><summary>Q4. [Intermediate] A VM was working fine but suddenly stopped. What do you check? <em>(asked in interview round)</em></summary>

**Answer:**

I check from the outside in: **platform** (is the VM running, was there an Azure/AWS event?), then **access** (network, NSG), then **inside the OS** (boot, disk, memory, services). Recent changes are always a suspect.

**Steps:**

1. **VM state:** is it Running, Stopped, Deallocated? Check the Activity Log (Azure) or CloudTrail (AWS) to see who or what stopped it (user, auto-shutdown, scale-in, policy, budget automation).
2. **Platform health:** Resource Health / Service Health (Azure) or EC2 status checks and scheduled events (AWS). A host failure or planned maintenance can reboot the VM.
3. **Boot diagnostics / serial console / instance screenshot:** shows kernel panic, boot errors, `fstab` mount failures or filesystem checks.
4. **Metrics:** CPU, memory, disk and network before the failure (CPU 100%, OOM, disk full).
5. **Network:** NSG/security group rules, route tables, public IP changes, firewall, DNS.
6. **Inside the OS (if reachable):** disk full (`df -h`), OOM killer in `dmesg`, failed services, logs.
7. **Recent changes:** patching, configuration changes, deployment, certificate or password expiry.
8. **Fix and recover:** start/redeploy the VM, restore from backup or snapshot if the disk is corrupted, and add monitoring/alerts.

**Flow:**

```text
VM down
  |
  v
Portal state + Activity Log / CloudTrail (who stopped it?)
  |
  v
Resource Health / EC2 status checks (platform issue?)
  |
  v
Boot diagnostics / serial console (OS boot error?)
  |
  v
Metrics: CPU, memory, disk (resource exhaustion?)
  |
  v
NSG / routes / DNS (network?) -> logs inside OS -> fix, add alerts
```

**Example commands:**

```bash
# Azure
az vm get-instance-view -g my-rg -n app-vm --query "instanceView.statuses[].displayStatus"
az monitor activity-log list --resource-id <vm-id> --offset 1d -o table
az vm boot-diagnostics get-boot-log -g my-rg -n app-vm

# AWS
aws ec2 describe-instance-status --instance-ids i-0abc123 --include-all-instances

# Inside the Linux VM
df -h; free -h; dmesg -T | grep -i -E "oom|error"; journalctl -p err -b -1
```

**Important points:**

- Activity Log/CloudTrail answers "who stopped it" in seconds; check it first.
- In AWS, a failed system status check is a host problem (stop and start moves it to new hardware); a failed instance status check is an OS problem.
- Serial console access is the way in when SSH/RDP does not work.
- Prevent repeats: availability sets/zones, backups, and alerts on VM availability and disk usage.

See also: [Linux performance troubleshooting](../linux/09-performance-troubleshooting-and-production.md), [Production issues](../repetitive-questions/production-issues.md).

**Interview-ready answer:**

> "First I check the VM state and the Activity Log or CloudTrail to see whether someone, an auto-shutdown schedule or automation stopped it. Then I check Resource Health or the EC2 status checks to see whether it was a platform issue like a host failure or maintenance. If the VM is running but not reachable, I use boot diagnostics and the serial console to look for boot errors, a full disk or a bad `fstab` entry. I review metrics for CPU, memory and disk just before the failure, and I check NSG rules, routes and DNS. I also look at recent changes like patching or deployments. After recovery I add alerts and use availability zones or backups so it does not happen again."

</details>

<details><summary>Q5. [Intermediate] EC2 is healthy but the application is unreachable. How do you troubleshoot? <em>(asked in interview round)</em></summary>

**Answer:**

EC2 status checks only prove the hypervisor and OS are responding. The path to the application includes DNS, the load balancer, security groups, NACLs, route tables and the application itself, so I trace the request hop by hop.

**Steps:**

1. **Application on the instance**: running, listening on the right port and on `0.0.0.0` (`ss -lntp`), responds locally with `curl`.
2. **Instance firewall**: `iptables`/`firewalld` and SELinux.
3. **Security group**: inbound rule for the app port from the right source (the ALB's security group, not `0.0.0.0/0`).
4. **NACL**: stateless, so it needs both inbound on the port and outbound on ephemeral ports (1024 to 65535) for return traffic.
5. **Routing**: public subnet has a route to an internet gateway; private instance is behind an ALB or reachable through NAT for outbound only.
6. **Load balancer**: target group health check path, port and success codes; listener rules; the ALB security group allows the client and egress to the target.
7. **DNS and TLS**: Route 53 record points to the right ALB; certificate matches the hostname.
8. Use **VPC Reachability Analyzer** and **VPC Flow Logs** (`ACCEPT` vs `REJECT`) to confirm.

**Decision flow:**

```text
Client --> DNS --> ALB --> Target group --> SG/NACL --> Instance --> App
      |
      v
curl localhost on instance OK? --no--> app/bind/firewall issue
      |yes
      v
Target health = healthy? --no--> health check path/port, SG from ALB SG, NACL ephemeral ports
      |yes
      v
ALB reachable from client? --no--> ALB SG, listener, subnets public, IGW route
      |yes
      v
DNS/TLS correct? --> Route 53 alias, certificate, HTTPS listener
```

**Commands:**

```bash
# On the instance
ss -lntp | grep 8080
curl -sv http://127.0.0.1:8080/health

# AWS CLI
aws elbv2 describe-target-health --target-group-arn <tg-arn>
aws ec2 describe-security-groups --group-ids <sg-id> --query 'SecurityGroups[].IpPermissions'
aws ec2 describe-network-acls --filters Name=association.subnet-id,Values=<subnet-id>
aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=<subnet-id>
dig +short app.example.com
```

**Important points:**

- Target health reason codes (`Target.Timeout`, `Target.ResponseCodeMismatch`, `Target.FailedHealthChecks`) tell you exactly which layer fails.
- A timeout is a network block; a `connection refused` is a listener problem.
- Reachability Analyzer checks configuration paths without sending traffic, which is ideal for SG/NACL/route mistakes.

See also: [AWS monitoring and troubleshooting](../aws/04-monitoring-and-troubleshooting.md), [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md), [Linux networking](../linux/06-networking.md)

**Interview-ready answer:**

> "EC2 status checks only tell me the VM is alive, so I trace the request path. On the instance I confirm the app is running and listening on `0.0.0.0` on the expected port and responds to `curl` locally. Then I check target group health and its reason code, which tells me whether the health check path, port or security group is wrong. I verify the instance security group allows the app port from the ALB's security group, and that the NACL allows both the port and the ephemeral return ports, since NACLs are stateless. I check route tables, the ALB listener and subnets, and finally DNS and the certificate. VPC Flow Logs and Reachability Analyzer help confirm exactly where traffic is rejected."

</details>

<details><summary>Q6. [Advanced] How do you troubleshoot IAM permission errors, load balancers and private network connectivity? <em>(asked in interview round)</em></summary>

**Answer:**

All three are "access denied somewhere on the path" problems. I identify the exact identity, action and resource, or the exact network hop, and check each control that can deny it.

**IAM permission errors:**

1. **Who am I?** `aws sts get-caller-identity` (or `az account show`). Pipelines often run as a different role than expected.
2. **What was denied?** The error names the action and resource. CloudTrail shows the full event; `aws sts decode-authorization-message` decodes encoded failures.
3. **Check every policy layer**: identity policy, resource policy (S3 bucket, KMS key policy), permission boundary, session policy, SCPs/RCPs in AWS Organizations. An explicit `Deny` anywhere wins.
4. **Conditions**: required tags, source VPC endpoint, MFA, region restrictions.
5. **Test** with IAM Policy Simulator or IAM Access Analyzer, then fix with least privilege.

**Load balancers:**

1. Target health and reason codes.
2. Listener rules, ports, TLS certificates.
3. Security groups between LB and targets; health check path and expected codes.
4. Timeouts (idle timeout vs app keep-alive) for `502`/`504` errors.

**Private network connectivity:**

1. DNS: does the name resolve to the private IP (private hosted zones, VPC endpoint private DNS)?
2. Routing: route tables, peering or Transit Gateway routes in **both** directions; no overlapping CIDRs.
3. Security groups, NACLs, firewalls on both sides.
4. Endpoint policies on VPC endpoints.
5. Flow logs and Reachability Analyzer to find where the packet stops.

**Decision flow:**

```text
AccessDenied?
   yes --> identity (sts get-caller-identity) --> CloudTrail event --> which policy layer denies?
            identity / resource / boundary / SCP / KMS key policy / condition
   no  --> network?
            DNS resolves to private IP? --> routes both ways? --> SG/NACL? --> endpoint policy?
```

**Commands:**

```bash
aws sts get-caller-identity
aws sts decode-authorization-message --encoded-message "<msg>" --query DecodedMessage --output text
aws iam simulate-principal-policy --policy-source-arn <role-arn> \
  --action-names s3:GetObject --resource-arns arn:aws:s3:::my-bucket/data/file.json
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject --max-results 5
aws elbv2 describe-target-health --target-group-arn <tg-arn>
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id>
```

**Important points:**

- KMS-encrypted resources need permission on the key as well as the resource; this is a very common hidden denial.
- Cross-account access needs both the caller's identity policy and the target's resource policy (or role trust).
- Routing must be symmetric; one missing return route looks exactly like a firewall drop.

See also: [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md), [AWS monitoring and troubleshooting](../aws/04-monitoring-and-troubleshooting.md), [Azure identity, security and governance](../azure/05-identity-security-and-governance.md), [Azure Application Gateway and WAF](../azure/07-application-gateway-and-waf.md)

**Interview-ready answer:**

> "For IAM errors I first confirm the actual identity with `sts get-caller-identity`, because pipelines often assume a different role than people think. Then I read the denied action and resource from the error or CloudTrail and check every layer that can deny it: the identity policy, the resource policy, KMS key policy, permission boundaries and SCPs, remembering that an explicit deny always wins. I verify with the policy simulator and fix with least privilege. For load balancers I check target health reason codes, listeners, security groups and timeouts. For private connectivity I check DNS resolves to private IPs, routes exist in both directions, and security groups, NACLs and endpoint policies allow the traffic, using flow logs and Reachability Analyzer to find the exact hop."

</details>
