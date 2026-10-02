# Terraform: Lifecycle, Replacement and Safe Changes

> The lifecycle block, create_before_destroy, preventing accidental deletion, replacement and taint, provisioners, zero-downtime and blue-green rollouts, autoscaling groups, and rollback.

## Key Concepts

### Idempotency and avoiding re-creation

#### Causes of unwanted recreation

| Cause | Fix |
|---|---|
| `timestamp()` or `uuid()` in a name | Use a stable name |
| Changing an immutable field | Check the provider docs first |
| Switching `count` to `for_each` | Use `moved` blocks |
| Another tool changing a field | Narrow `ignore_changes` |
| Renaming a resource in code | Use a `moved` block, not a rename |

#### Habit

Always read the plan for `forces replacement` before approving.

### State, replacement, and provisioners

#### State

Keep it in an encrypted remote backend with locking, versioning, audit logs, and least-privilege access. Protect read access as strongly as write access.

#### Replacement

`terraform taint` is deprecated. Use:

```bash
terraform apply -replace='module.app.aws_instance.web'
```

Check dependencies, data, downtime, and rollback before replacing anything.

#### Provisioners

`local-exec`, `remote-exec`, and `file` are last-resort escape hatches, not a configuration management tool.

Problems with them:

- Hard to make idempotent
- Can fail after the resource is already created
- Errors are hard to recover from

Better options: cloud-init or user data, a pre-baked image, a managed service, Ansible, or a native provider resource.

### Zero downtime deployments

#### Ways to do it

1. **Create before destroy** — bring the new resource up first.
2. **Rolling update** — replace a few instances at a time.
3. **Blue-green** — build a second stack, switch traffic, delete the old one.
4. **Load balancer + health checks** — no traffic until the new instance is healthy.
5. **Test in a lower environment first.**

#### Example

```hcl
resource "aws_autoscaling_group" "web" {
  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
    }
  }
}
```

#### Remember

Databases need their own plan: replica promotion, backups, and a backward-compatible migration.

### Blue-green and canary rollouts

#### Blue-green

1. Build a complete second stack (green) beside the live one (blue).
2. Test green privately.
3. Switch the load balancer or DNS to green.
4. Keep blue for the rollback window, then destroy it.

#### Canary

1. Send a small percentage of traffic to the new version.
2. Watch error rate and latency.
3. Increase gradually, or roll back quickly.

#### With Terraform

Terraform builds both stacks and the routing. The traffic percentage is usually driven by a weighted target group, weighted DNS record, or a service mesh, and changed through the pipeline.

### Changing autoscaling groups and load balancers without downtime

1. A new launch template version does not replace running instances by itself.
2. Use instance refresh with a minimum healthy percentage to roll them gradually.
3. Keep health checks strict so bad instances never receive traffic.
4. Use connection draining (deregistration delay) so in-flight requests finish.
5. For load balancer changes, add the new listener or target group before removing the old one.

```hcl
resource "aws_lb_target_group" "web" {
  deregistration_delay = 30
}
```

## Interview Questions

<details><summary>Q1. [Basic] What is a lifecycle block?</summary>

#### The four options

| Option | What it does |
|---|---|
| `prevent_destroy` | Terraform fails instead of deleting the resource |
| `create_before_destroy` | Creates the new resource first, then deletes the old one |
| `ignore_changes` | Ignores changes to listed attributes |
| `replace_triggered_by` | Replaces this resource when another one changes |

#### Example

```hcl
resource "aws_db_instance" "prod" {
  identifier = "prod-db"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_instance" "web" {
  ami = var.ami

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [tags["LastScanned"]]
  }
}
```

#### Points to remember

- `prevent_destroy` does not help if you delete the whole resource block from the code.
- `create_before_destroy` can fail when names must be unique or quota is full.
- A wide `ignore_changes` hides real drift, so keep it narrow.

#### Interview answer

"`lifecycle` changes how Terraform handles a resource. I use `prevent_destroy` on production databases, and `create_before_destroy` when the old and new resource can exist together. I use `ignore_changes` when another system owns a field like a tag, and `replace_triggered_by` when a change elsewhere must force a replacement. These are helpers, not full protection, so I also use cloud deletion protection and approvals."

</details>

<details><summary>Q2. [Basic] Explain the resource lifecycle and <code>create_before_destroy</code>.</summary>

#### What Terraform decides for each resource

| Decision | When |
|---|---|
| No change | Code matches reality |
| Update in place | Attribute can be changed |
| Replace | Attribute is immutable |
| Create | Resource is new |
| Destroy | Resource removed from code |

#### Default replacement order

1. Destroy the old resource.
2. Create the new one.

That means downtime.

#### With `create_before_destroy`

```hcl
lifecycle {
  create_before_destroy = true
}
```

1. Create the new resource.
2. Switch references to it.
3. Destroy the old one.

#### It can fail when

- The name must be unique.
- Quota does not allow two at once.
- Something is attached to the old resource.

#### Interview answer

"Terraform compares code, state, and reality and decides to do nothing, update in place, replace, create, or destroy. Replacement destroys first and then creates, which causes downtime. `create_before_destroy` reverses that order so the new resource comes up first. It is not a guarantee, because unique names, quotas, and attached resources can block having two at once, so I always confirm the order in the plan."

</details>

<details><summary>Q3. [Intermediate] How do you allow plan and apply but block deletion?</summary>

#### Layers of protection

1. `lifecycle { prevent_destroy = true }` on critical resources.
2. Deletion protection on the cloud resource itself (RDS, load balancer, storage).
3. A policy check (Sentinel, OPA, Checkov) that fails the pipeline if the plan contains a delete.
4. Pipeline credentials that do not have delete permission, with a separate break-glass role.
5. Manual approval before production apply.

#### Important point

There is no single Terraform switch that says "allow every update but never delete", because a replacement includes a delete.

#### Interview answer

"There is no single flag for it, so I use layers. `prevent_destroy` on critical resources, deletion protection on the cloud side, a policy check that rejects plans containing deletes, and pipeline credentials without delete rights. Init, validate, and plan stay allowed because they only read. When a delete is genuinely needed, it goes through a documented break-glass approval."

</details>

<details><summary>Q4. [Intermediate] How do you avoid deleting something by accident?</summary>

#### Layers

1. Always read the plan, especially the destroy section.
2. `prevent_destroy` on critical resources.
3. Cloud-side deletion protection.
4. Separate state files so a mistake has a smaller blast radius.
5. Pipeline credentials without delete permission.
6. Approval before production apply.
7. Backups that have actually been restored once.

#### Example

```hcl
resource "aws_rds_cluster" "prod" {
  cluster_identifier  = "prod-db"
  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}
```

#### Quick habit

Search the plan output for `destroy` before approving:

```bash
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

#### Interview answer

"I never approve a plan without reading the destroy section. On top of that I use `prevent_destroy` and cloud deletion protection on critical resources, separate state files to limit blast radius, pipeline credentials without delete rights, and mandatory approval for production. For the most critical systems there is a break-glass procedure with two approvers and tested backups."

</details>

<details><summary>Q5. [Intermediate] How do you stop someone deleting a critical resource? <em>(scenario)</em></summary>

#### Protection layers

```hcl
resource "aws_db_instance" "prod" {
  identifier          = "prod-db"
  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}
```

1. `prevent_destroy` in the lifecycle block
2. Deletion protection on the cloud resource
3. Policy check that fails the build if the plan has a delete
4. Approval before production apply
5. Pipeline credentials without delete permission

#### If a destroy already started

Stop new runs, check what is actually gone, restore from backup or replica, import whatever survived, then plan a proper recovery.

#### Interview answer

"I use layers: `prevent_destroy` and cloud deletion protection on critical resources, a policy check that rejects plans containing deletes, approval gates, and pipeline credentials without delete rights. If a destroy has already started, I stop the runs, check what really disappeared, restore from backup, and import anything that survived instead of applying blindly."

</details>

<details><summary>Q6. [Intermediate] Preventing accidental deletion of critical resources</summary>

Four layers, used together rather than any single one alone:

1. **`lifecycle.prevent_destroy`** on genuinely critical resources - blocks `terraform destroy` and any replacement that would destroy the resource.

```hcl
resource "azurerm_key_vault" "kv" {
  name = "prod-kv"

  lifecycle {
    prevent_destroy = true
  }
}
```

2. **Always review `terraform plan` before apply** - a plan showing `-` (destroy) or `-/+` (destroy and recreate) against a critical resource should stop the pipeline for human review, not sail through on `-auto-approve`.
3. **RBAC** - restrict who/what can run `terraform apply` against production state to begin with; most accidental deletions come from someone running the wrong command against the wrong workspace, not from a code review that let anything sneaky through.
4. **CI/CD approvals** - require an explicit approval gate before `apply` runs in a production environment, so the plan output is a real checkpoint, not a formality.

Avoid unnecessary destructive changes in the first place - renaming a resource block without a `moved` block, or changing an immutable attribute, can trigger a destroy/recreate you didn't intend.

#### Short interview answer

I use `lifecycle.prevent_destroy` on resources that must never be destroyed by Terraform, review every `plan` before `apply` - especially anything showing `-` or `-/+` - and back that with RBAC restricting who can apply against production, plus a CI/CD approval gate so a human sees the plan before it's applied.

</details>

<details><summary>Q7. [Advanced] The plan wants to destroy and recreate a production database. What do you do?</summary>

#### Steps

1. Do not apply yet.
2. Find which argument forces the replacement. The plan shows `# forces replacement`.
3. Check the provider docs to confirm the field is immutable.
4. Back up the state and take a database snapshot.
5. Decide:
   - Can the change be made in place through the cloud console or a supported operation? Then change the Terraform design or use a narrow `ignore_changes`.
   - Is the change unnecessary? Revert the code.
   - Is replacement really needed? Plan a migration.

#### If replacement is really needed

1. Create the new database beside the old one.
2. Replicate or restore the data.
3. Test the application against it.
4. Move traffic through DNS or connection settings.
5. Keep the old one for a rollback window, then delete it.

#### Important point

`create_before_destroy` only helps if two databases can exist at once. Names, quotas, and licences may not allow it.

#### Interview answer

"I stop and find out which argument forces the replacement, since the plan marks it. I check the provider docs to see whether the field is immutable and whether the change can be done in place instead. If a real replacement is needed, I treat it as a data migration: build the new database, replicate the data, test the application, switch traffic, keep the old one for a rollback window, and only then destroy it. A lifecycle flag alone is not a downtime plan."

</details>

<details><summary>Q8. [Intermediate] Terraform wants to destroy something critical. How do you react? <em>(scenario)</em></summary>

#### Steps

1. Stop. Do not approve the apply.
2. Find the reason in the plan: `# forces replacement`, or the resource was removed from the code.
3. If someone deleted the resource block by mistake, restore the code.
4. If a field forces replacement, check the provider docs for whether it can change in place.
5. Verify backups before doing anything.

#### Quick check on any plan

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

#### Interview answer

"I stop and find out why. Either the resource block was removed from the code by mistake, or an immutable field is forcing replacement, and the plan says which one. I check the provider docs to see whether the change can be done in place, and I verify backups before doing anything. I also run a jq check over the plan JSON so deletes are never buried in a long output."

</details>

<details><summary>Q9. [Intermediate] How do you stop Terraform replacing resources unexpectedly? <em>(scenario)</em></summary>

#### Find out why first

The plan tells you:

```text
~ resource "aws_instance" "web" {
    ~ availability_zone = "us-east-1a" -> "us-east-1b" # forces replacement
```

#### Then decide

| Situation | Action |
|---|---|
| The change is not needed | Revert the code |
| Another system owns that field | Narrow `ignore_changes` |
| Replacement is needed but downtime is not acceptable | `create_before_destroy` plus traffic cutover |
| It is a database or disk | Backup, migrate data, then replace |

#### Example

```hcl
lifecycle {
  ignore_changes = [tags["LastPatched"]]
}
```

Keep the list narrow. A wide `ignore_changes` hides real drift.

#### Interview answer

"I read the plan to see which argument is marked `forces replacement`, because that tells me whether the field is immutable. If the change is not needed I revert the code; if another system owns the field I add a narrow `ignore_changes`; if replacement really is needed I plan for it with create-before-destroy and a traffic cutover. For anything holding data, I treat it as a migration, not a replace."

</details>

<details><summary>Q10. [Intermediate] Preventing Terraform from accidentally replacing resources</summary>

- **Always review `terraform plan`.** A plan showing `-/+` means destroy-and-recreate, not an in-place update - that's the single most important thing to catch before `apply`.
- **Use `lifecycle.prevent_destroy`** for resources that must never be destroyed:

```hcl
resource "azurerm_key_vault" "kv" {
  name = "prod-kv"

  lifecycle {
    prevent_destroy = true
  }
}
```

- **Avoid unnecessary changes to immutable properties** - some resource attributes force replacement when changed (e.g. certain Azure resource name/region/SKU-family fields); changing them without realizing they're immutable is a common accidental-replacement cause.
- **Use `ignore_changes` only where appropriate** - see the question on preventing drift from manually modified resources in [08-drift-import-and-refactoring.md](08-drift-import-and-refactoring.md) for the same caution against overusing it.
- **Import existing resources** rather than letting Terraform "adopt" them by recreating them under a new identity.
- **Prefer `for_each` over `count`** when the resources have a stable identity that matters. With `count`, removing an item from the middle of a list shifts every subsequent resource's index - and Terraform destroys/recreates everything after that index to realign. `for_each` keys resources by a stable value (like a name), so removing one item only affects that one resource.
- **Version modules**, so a module update doesn't silently change resource configuration for every consumer at once.
- **Require production plan review and approval** before `apply` runs against production state.

#### Short interview answer

The plan is the safety net - `-/+` always means destroy-and-recreate, and I review every plan against production for that specifically. `lifecycle.prevent_destroy` backs that up for resources that must never go away. For collections of similar resources, I use `for_each` over `count` specifically because `count` reindexes and can trigger cascading replacement when an item is removed from the middle of the list, while `for_each` only touches the one resource whose key actually changed.

</details>

<details><summary>Q11. [Basic] What are <code>taint</code> and <code>untaint</code>?</summary>

#### What they do

- `terraform taint <address>` marks a resource in state as bad, so the next apply replaces it.
- `terraform untaint <address>` removes that mark.

#### Better way today

`taint` is deprecated. Use an explicit replace:

```bash
terraform plan -replace='aws_instance.web' -out=tfplan
terraform apply tfplan
```

#### Before replacing anything, check

- What depends on this resource
- Whether it holds data
- Whether downtime is acceptable
- Whether create-before-destroy is possible

#### Interview answer

"`taint` marks a resource in state so it gets recreated on the next apply, and `untaint` removes that mark. It is deprecated now, so I prefer `terraform apply -replace=<address>` because the replacement is visible in the plan instead of hidden in state. For databases or disks I never use replacement as a quick troubleshooting step."

</details>

<details><summary>Q12. [Intermediate] A resource is not updating properly. Do taint and untaint help?</summary>

#### First find out why it is not updating

1. Read the plan. Does Terraform even see a change?
2. Check if the field is immutable, which forces a replacement.
3. Check whether `ignore_changes` is hiding it.
4. Check provider errors and permissions.
5. Check whether another tool is changing it back.

#### Then decide

- If the code or input was wrong, fix it and apply. No replacement needed.
- If the resource really must be rebuilt, use `-replace` and review every dependent change.
- If someone tainted a healthy resource by mistake, run `terraform untaint <address>` and plan again.

#### Interview answer

"I do not start with taint. First I check the plan, the provider error, whether the field is immutable, and whether `ignore_changes` is hiding it. If the object really needs to be rebuilt, I use `apply -replace` so the change is visible in the plan. If someone tainted a healthy resource by mistake, `untaint` avoids an unnecessary replacement."

</details>

<details><summary>Q13. [Basic] You changed a variable and want to see the impact. What do you do? <em>(scenario)</em></summary>

#### Run a plan

```bash
terraform plan -var-file=prod.tfvars -out=tfplan
```

#### What to look for

1. Not just the resource you expected. Look at everything.
2. Any `forces replacement`.
3. Any destroy.
4. Changed outputs, which other stacks may depend on.

#### Machine-readable check

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | "\(.change.actions | join(",")) \(.address)"'
```

#### Do not use `-target` to "just check one thing"

It hides everything else.

#### Interview answer

"I run a plan with the right var file and read the whole thing, not just the resource I expected to change, because an immutable field can turn a small value change into a replacement. I look specifically for `forces replacement`, destroys, and changed outputs that other stacks depend on. I avoid `-target`, because narrowing the plan hides exactly what I am trying to catch."

</details>

<details><summary>Q14. [Intermediate] How do you get zero-downtime updates?</summary>

#### Techniques

1. **Create before destroy**

```hcl
resource "aws_launch_template" "web" {
  lifecycle {
    create_before_destroy = true
  }
}
```

2. **Rolling update with instance refresh**

```hcl
resource "aws_autoscaling_group" "web" {
  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
    }
  }
}
```

3. **Blue-green** — build the new stack beside the old one, move traffic with DNS or the load balancer, then delete the old stack.

4. **Health checks** — do not send traffic until the new instance passes.

5. **Databases** — use a replica that can be promoted, or a managed service with failover.

#### Interview answer

"For stateless tiers I use immutable replacement: a new launch template version, an autoscaling instance refresh with a minimum healthy percentage, and health checks before traffic is sent. For bigger changes I use blue-green, so traffic moves only after the new stack is verified and rollback is just switching back. Databases need their own plan with replicas, backups, and application-level migration."

</details>

<details><summary>Q15. [Intermediate] How do you create an autoscaling group?</summary>

#### Two pieces

1. A launch template that describes the instance.
2. An autoscaling group that runs several of them.

#### Example

```hcl
resource "aws_launch_template" "web" {
  name_prefix   = "web-"
  image_id      = var.ami_id
  instance_type = "t3.small"

  vpc_security_group_ids = [aws_security_group.web.id]
}

resource "aws_autoscaling_group" "web" {
  name                = "web-asg"
  vpc_zone_identifier = module.vpc.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.web.arn]

  min_size         = 2
  desired_capacity = 2
  max_size         = 6

  health_check_type         = "ELB"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }
}
```

#### After apply, test

- Scale out works
- New instances register as healthy in the target group
- Terminating one instance brings a new one back

#### Interview answer

"I create a launch template with the approved image, security groups, and instance profile. Then I add an autoscaling group that spreads across availability zones, with min, desired, and max capacity, target group attachment, and health checks. I add a scaling policy on a real metric like CPU or request count. After apply I test scale-out and instance replacement, because seeing the resource created is not proof it works."

</details>

<details><summary>Q16. [Intermediate] How do you do immutable infrastructure? <em>(scenario)</em></summary>

#### The idea

Do not patch a running server. Build a new image and replace the servers.

#### Flow

1. Build and scan a new image, tagged with a version.
2. Update the launch template to that image.
3. Autoscaling instance refresh replaces instances gradually.
4. Health checks decide whether the new instances stay.
5. Roll back by pointing at the previous image version.

#### Example

```hcl
resource "aws_launch_template" "web" {
  image_id = var.ami_id   # a new AMI means a new template version
}

resource "aws_autoscaling_group" "web" {
  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
    }
  }
}
```

#### Interview answer

"Instead of changing servers in place, I build a new versioned image, point the launch template at it, and let the autoscaling instance refresh replace instances gradually while health checks protect the rollout. Rollback is just pointing back at the previous image version. Data stays outside the instances, in managed services, so replacing a server is never risky."

</details>

<details><summary>Q17. [Intermediate] How do you handle database schema changes?</summary>

#### Separate the two jobs

| Terraform | Migration tool |
|---|---|
| Creates the database server, network, backups, users | Creates tables and changes schema |

Terraform is declarative and does not track table versions. Use Flyway, Liquibase, Alembic, or your application's migration framework for schema.

#### Terraform side

```hcl
resource "aws_db_instance" "app" {
  identifier              = "app-db"
  engine                  = "postgres"
  instance_class          = "db.t3.medium"
  allocated_storage       = 20
  backup_retention_period = 7
  skip_final_snapshot     = false

  lifecycle {
    prevent_destroy = true
  }
}

output "db_endpoint" {
  value     = aws_db_instance.app.endpoint
  sensitive = true
}
```

#### Pipeline side

```text
1. Take a snapshot
2. Run the migration tool
3. Deploy the application version that matches the schema
4. Keep the migration backward compatible so rollback is possible
```

#### Interview answer

"I keep them separate: Terraform creates the database instance, networking, backups, and users, and a dedicated migration tool like Flyway or Liquibase handles the schema through the deployment pipeline. Before a migration the pipeline takes a snapshot, and migrations are written to be backward compatible so the previous application version still works if we need to roll back."

</details>

<details><summary>Q18. [Intermediate] How do you roll back a bad deployment? <em>(scenario)</em></summary>

#### Terraform has no rollback command

Rollback means: revert the code and apply again.

```bash
git revert <bad-commit>
terraform plan -out=rollback.tfplan   # review it carefully
terraform apply rollback.tfplan
```

#### What re-applying old code will NOT do

- Bring back deleted data
- Undo a database migration
- Reverse everything a provider did

#### So plan for it in advance

- Backups you have actually restored once
- Blue-green or canary so rollback is a traffic switch
- Deletion protection on data resources

#### Important point

Restoring an old **state** file is not a rollback. It only makes Terraform believe wrong information.

#### Interview answer

"There is no rollback command. I revert the code to the last good commit and apply a new reviewed plan. But I always say clearly that this does not bring back deleted data or undo a database migration, so real rollback safety comes from backups, blue-green deployment, and deletion protection. Restoring an old state file is not a rollback; it just makes Terraform believe something untrue."

</details>

<details><summary>Q19. [Intermediate] How do you implement rollback? <em>(scenario)</em></summary>

#### There is no rollback command

Rollback means revert the code and apply a new plan.

```bash
git revert <bad-commit>
terraform plan -out=rollback.tfplan
terraform apply rollback.tfplan
```

#### Design for rollback in advance

| Change type | How to roll back |
|---|---|
| Stateless app or servers | Blue-green or previous image version, switch traffic |
| Configuration change | Revert the code and apply |
| Database schema | Backward-compatible migration plus a restore plan |
| Deleted data | Only backups can help |

#### Interview answer

"Rollback is reverting the code and applying a new reviewed plan, not restoring an old state file. Applying old code cannot bring back deleted data or undo a migration, so I design for rollback up front. That means blue-green so rollback is just a traffic switch, backward-compatible migrations, deletion protection, and backups that have actually been restored once in a test."

</details>
