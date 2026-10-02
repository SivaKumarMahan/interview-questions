# Terraform: Troubleshooting, Performance and Operations

> Speeding up slow plans and applies, API rate limits, failed or half-finished applies, authentication errors, dependency cycles, recovering from a destroy in production, and monitoring and cost management for production changes.

## Key Concepts

### Performance on large infrastructure

| Problem | Fix |
|---|---|
| One huge state | Split by component and environment |
| Slow refresh | Fewer resources per state |
| Broad data sources | Pass IDs in as variables |
| Provider download every run | Cache or mirror providers in CI |
| API throttling | Lower `-parallelism`, enable provider retries |
| Extra `depends_on` | Remove it, let Terraform infer |

Avoid using `-target` as a normal habit. It gives an incomplete plan.

### Monitoring and logging

1. Create the alarms and dashboards in Terraform along with the resource, so nothing ships unmonitored.
2. Enable cloud logging: CloudTrail, Azure Activity Log, GCP Audit Logs.
3. Alert on drift job results and failed applies.
4. Send apply summaries to the team channel.

```hcl
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "web-high-cpu"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  evaluation_periods  = 2
  period              = 300
  statistic           = "Average"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

### Cost management

1. Right-size in dev: small instances, one node, short backup retention.
2. Turn dev off outside working hours.
3. Use spot or preemptible instances for non-critical workloads.
4. Tag everything for cost allocation.
5. Create budgets and alerts in Terraform.
6. Run a cost estimate in the pipeline, for example with Infracost.

```hcl
variable "instance_type" {
  type = map(string)

  default = {
    dev  = "t3.small"
    prod = "m6i.large"
  }
}
```

## Interview Questions

<details><summary>Q1. [Intermediate] How do you make Terraform runs faster?</summary>

#### First measure where the time goes

- Provider and module download
- Refresh (API calls for every resource)
- Data sources
- Apply itself

#### Then fix

| Problem | Fix |
|---|---|
| Too many resources in one state | Split into smaller states |
| Broad data sources scanning everything | Pass IDs as variables instead |
| Extra `depends_on` | Remove it and let Terraform infer dependencies |
| Downloading providers every run | Use a provider cache or mirror in CI |
| Slow apply | Tune `-parallelism` within API rate limits |

#### What to avoid

Do not make `-target` your normal way to work. It produces an incomplete plan and hides changes.

#### Interview answer

"I measure first: is the time going to provider downloads, refresh, or apply? Then I split large states, remove broad data sources and unnecessary `depends_on`, cache providers in CI, and run independent states in parallel. I avoid using `-target` routinely because it hides changes, and I keep a scheduled full plan so the speedups do not hide drift."

</details>

<details><summary>Q2. [Intermediate] Why is <code>terraform plan</code> slow, and how do you speed it up? <em>(scenario)</em></summary>

#### Where the time goes

1. `init` downloading providers and modules
2. Refresh, which calls the cloud API for every resource
3. Data sources that list everything in an account
4. Unnecessary graph dependencies

#### Fixes

| Cause | Fix |
|---|---|
| Too many resources | Split the state |
| Broad data sources | Pass IDs as variables |
| Provider download every run | Provider cache or mirror |
| Refresh is the bottleneck | `-refresh=false` for a quick check only, never for the final plan |

#### Interview answer

"First I find out where the time goes: provider download, refresh, or data sources. Usually it is refresh on a very large state, so the real fix is splitting the state. I also replace broad data sources with variables, remove unnecessary `depends_on`, and cache providers in CI. I avoid `-target` as a routine speedup because the plan then hides changes."

</details>

<details><summary>Q3. [Intermediate] Why is <code>terraform apply</code> slow? <em>(scenario)</em></summary>

#### Common causes

| Cause | Fix |
|---|---|
| Many resources in one state | Split the state |
| API rate limiting | Lower `-parallelism`, enable provider retries |
| Resources that are slow by nature (RDS, clusters) | Nothing to fix, plan the window |
| Long dependency chains | Remove unnecessary `depends_on` |

#### Example

```bash
terraform apply -parallelism=5 tfplan
```

Lowering parallelism can actually be faster when the provider is throttling you.

#### Interview answer

"I check whether it is the number of resources, API throttling, or resources that are simply slow to create like databases and clusters. Splitting the state helps most. If the provider is throttling, lowering parallelism and enabling retries is often faster than pushing more requests. Unnecessary `depends_on` also serializes work that could run in parallel."

</details>

<details><summary>Q4. [Intermediate] How do you reduce total Terraform execution time? <em>(scenario)</em></summary>

#### Quick wins

| Action | Effect |
|---|---|
| Split large states | Biggest win, refresh is the usual bottleneck |
| Cache providers in CI | Saves the download every run |
| Replace broad data sources with variables | Fewer API calls |
| Run independent stacks in parallel | Wall-clock time drops |
| Tune `-parallelism` | Helps or hurts depending on throttling |

#### Keep a full plan somewhere

If you optimize by narrowing scope, keep a scheduled full plan so nothing goes unnoticed.

#### Interview answer

"The biggest win is splitting large states, because refresh is normally the bottleneck. After that: cache providers in CI, replace broad data sources with variables, and run independent stacks in parallel. I tune parallelism carefully since raising it can trigger throttling. And whatever I narrow for speed, I keep a scheduled full plan so nothing is hidden."

</details>

<details><summary>Q5. [Intermediate] How do you handle provider API rate limits?</summary>

#### Options

1. Lower parallelism:

```bash
terraform apply -parallelism=5
```

2. Use provider retry settings:

```hcl
provider "aws" {
  region             = "us-east-1"
  retry_mode         = "adaptive"
  max_retries        = 10
}
```

3. Add a small wait between heavy resources:

```hcl
resource "time_sleep" "wait" {
  depends_on      = [aws_iam_role_policy_attachment.app]
  create_duration = "30s"
}
```

4. Split the configuration into smaller states so fewer calls happen at once.

#### Interview answer

"I reduce `-parallelism`, turn on the provider's retry and backoff settings, and split large configurations into smaller states so fewer API calls happen at the same time. If one specific resource type always triggers throttling, I add a short `time_sleep` between the stages. I also check whether a quota increase is the real fix."

</details>

<details><summary>Q6. [Intermediate] Apply is failing because of API rate limits. What do you do? <em>(scenario)</em></summary>

#### Fixes

```bash
terraform apply -parallelism=5 tfplan
```

```hcl
provider "aws" {
  region      = "us-east-1"
  max_retries = 10
  retry_mode  = "adaptive"
}
```

```hcl
provider "google" {
  project                     = var.project_id
  request_timeout             = "60s"
  batching {
    enable_batching = true
  }
}
```

#### Longer-term fixes

- Split the configuration so fewer calls happen at once
- Request a quota increase
- Stagger pipelines instead of running them all at 9am

#### Interview answer

"I lower `-parallelism`, enable the provider's retry and backoff settings, and split large configurations so fewer API calls happen at once. If it keeps happening I request a quota increase and stagger the pipelines, because throttling is usually caused by many jobs starting at the same time rather than one big apply."

</details>

<details><summary>Q7. [Intermediate] Apply succeeded but the resource is not working. How do you debug?</summary>

#### Important point

A successful apply only means the cloud API accepted the request. It does not mean the service works.

#### Debug order

1. Start from the failing user path.
2. Check DNS, route tables, security groups, and NSG rules.
3. Check IAM permissions.
4. Check service health and bootstrap logs.
5. Compare the code, the plan, and `terraform state show` with the console.

#### Useful commands

```bash
terraform state show aws_instance.web
terraform output
TF_LOG=DEBUG terraform plan   # use briefly, logs can show secrets
```

#### Interview answer

"A successful apply only proves the API calls worked. I start from the failing user path and check DNS, routing, security groups, IAM, and application logs. I compare my code, the plan, and `terraform state show` with what the console shows. I enable `TF_LOG` only briefly because it can expose sensitive values, and I never edit state to fix a runtime problem."

</details>

<details><summary>Q8. [Intermediate] How do you debug a failed apply in a big module setup?</summary>

#### Steps

1. Stop retries and read the exact resource address in the error.
2. Check the usual causes: permissions, quota, name already exists, network, API outage.
3. Compare the saved plan with what failed.
4. Inspect values:

```bash
terraform console
> module.vpc.private_subnet_ids
terraform state show module.compute.aws_instance.web
```

5. Turn on debug logs briefly:

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./tf.log
```

6. Compare state with the real resources. Import anything created but not tracked.
7. Fix the cause, run a fresh full plan, apply, and verify.

#### Interview answer

"I stop retries and find the exact resource address and provider error, then check permissions, quotas, name conflicts, network, and provider version. I use `terraform console` and `state show` to inspect module inputs and outputs, and I enable `TF_LOG` only briefly because logs can contain sensitive data. If the API created something Terraform did not record, I import it instead of recreating it. Then I fix the cause, run a full plan, and verify the application, not just the resource."

</details>

<details><summary>Q9. [Advanced] A production apply failed halfway. How do you recover?</summary>

#### Steps

1. Stop automatic retries and keep the lock until you know nothing is running.
2. Save the error, the plan, the state version, and the cloud activity log.
3. Find which resources were actually created.
4. Fix the customer impact first.
5. Reconcile state:
   - Resource created but not in state → import it.
   - In state but does not exist → decide to recreate or `state rm`.
6. Fix the real cause: quota, permission, name conflict, network, provider bug.
7. Run a new full plan, review it, apply, and verify.

#### What not to do

Do not run `terraform destroy` to "clean up". It can delete working dependencies.

#### Interview answer

"Terraform records the resources that succeeded, so I stop retries, keep evidence, and find out exactly what was created. If something exists in the cloud but not in state, I import it; if state has something that no longer exists, I decide carefully before removing it. Then I fix the real cause, run a fresh full plan, review it, and apply. I never destroy everything to clean up."

</details>

<details><summary>Q10. [Intermediate] What if the apply fails halfway? <em>(scenario)</em></summary>

#### What Terraform does

Resources that succeeded are recorded in state. Terraform does not roll back the ones already created.

#### Steps

1. Stop retries.
2. Read the exact error and resource address.
3. Compare state with the real cloud resources.
4. Reconcile:
   - Created but not in state → import it
   - In state but missing → decide recreate or `state rm`
5. Fix the real cause: quota, permission, name conflict, network.
6. Run a fresh full plan, review, apply, verify.

#### Do not

Do not run destroy to "clean up", and do not blindly re-run apply hoping it works.

#### Interview answer

"Terraform keeps whatever succeeded in state, so it is not all-or-nothing. I stop retries, read the exact error, and compare state with the real resources. If something was created but not recorded, I import it; if state has something that no longer exists, I decide carefully. Then I fix the actual cause, run a fresh full plan, and apply. I never destroy everything to clean up."

</details>

<details><summary>Q11. [Intermediate] Terraform cannot authenticate to the cloud. How do you debug it? <em>(scenario)</em></summary>

#### Check in this order

1. Which credentials is Terraform actually using?

```bash
aws sts get-caller-identity
az account show
gcloud auth list
```

2. Are the environment variables set in the pipeline?

```bash
ARM_CLIENT_ID  ARM_CLIENT_SECRET  ARM_TENANT_ID  ARM_SUBSCRIPTION_ID
AWS_ROLE_ARN   AWS_WEB_IDENTITY_TOKEN_FILE
```

3. Has the secret or certificate expired?
4. Is the right subscription, project, or account selected?
5. Does the identity have the role it needs?
6. For OIDC, does the trust condition match the repo and branch?

#### Interview answer

"I first confirm which identity Terraform is actually using with `sts get-caller-identity` or `az account show`, because the problem is usually a different identity than expected. Then I check whether the environment variables are set in the job, whether the secret expired, whether the right subscription is selected, and whether the role assignment exists. For OIDC I check that the trust condition matches the repository and branch."

</details>

<details><summary>Q12. [Intermediate] How do you fix a dependency cycle error? <em>(scenario)</em></summary>

#### The error

```text
Error: Cycle: aws_security_group.app, aws_security_group.db
```

Usually two security groups reference each other.

#### The fix

Use separate rule resources instead of inline rules:

```hcl
resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = var.vpc_id
}

resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = var.vpc_id
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
}
```

#### Other tips

- Remove unnecessary `depends_on`, which often creates the cycle.
- View the graph: `terraform graph | dot -Tsvg > graph.svg`
- Split the resources into two modules if they really belong to different layers.

#### Interview answer

"A cycle usually comes from two resources referencing each other, like two security groups with inline rules. I break it by moving the rules into separate `aws_security_group_rule` resources so the groups themselves no longer depend on each other. I also remove unnecessary `depends_on`, since manual dependencies often cause the cycle, and I use `terraform graph` to see the loop."

</details>

<details><summary>Q13. [Advanced] Someone ran destroy in production. What now? <em>(scenario)</em></summary>

#### Immediate steps

1. Stop the pipeline and any other running jobs.
2. Find out what was actually deleted from the cloud activity log.
3. Restore in priority order: data first, then compute.
   - Database from snapshot or replica
   - Storage from versioning or backup
4. Re-apply the code for stateless resources.
5. Import anything that survived instead of recreating it.
6. Verify the application, not just the resources.

#### Prevent it happening again

- Remove destroy permission from the pipeline identity
- `prevent_destroy` on critical resources
- Approval before any destroy
- Separate state per environment

#### Interview answer

"First I stop everything and work out from the audit log what was actually deleted. Data comes back first, from snapshots or replicas, then I re-apply the code for stateless resources and import anything that survived. Once the service is verified, I make it impossible to repeat: no destroy permission for the pipeline identity, `prevent_destroy` on critical resources, and mandatory approval."

</details>

<details><summary>Q14. [Intermediate] How do you monitor Terraform changes in production? <em>(scenario)</em></summary>

#### What to capture

1. The plan artifact for every run, stored and access controlled.
2. A notification to Slack or Teams with the summary before apply.
3. Approval recorded with who approved and when.
4. Apply logs stored for audit.
5. Cloud audit logs to correlate.

#### Machine-readable output

```bash
terraform apply -json tfplan | tee apply.json
```

#### After apply

Run a smoke check, and watch dashboards and alarms for the next few minutes.

#### Interview answer

"Every run stores its plan as an artifact, posts a summary to the team channel, and records who approved it. Apply output is kept in JSON for the audit trail, and I correlate it with cloud audit logs. After apply the pipeline runs a smoke check and I watch the service dashboards, because the value is in noticing a bad change quickly, not just in having the logs."

</details>

<details><summary>Q15. [Intermediate] How do you monitor and notify on Terraform deployments? <em>(scenario)</em></summary>

#### In the pipeline

```bash
terraform apply -json tfplan > apply.json
```

Send the summary to Slack or Teams:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"Terraform apply finished for prod: $(jq -r '.[] | select(.type==\"change_summary\") | .message' apply.json)\"}" \
  "$SLACK_WEBHOOK"
```

#### Also monitor

- Alarms and dashboards created by Terraform itself
- Cloud audit logs for changes made outside Terraform
- Drift job results

#### Interview answer

"The pipeline produces JSON output and posts a change summary to the team channel, so everyone can see what was applied and by whom. Terraform also creates the alarms and dashboards for the resources it builds, so the service is monitored from day one. On top of that, cloud audit logs and the nightly drift job catch changes that did not come from the pipeline."

</details>
