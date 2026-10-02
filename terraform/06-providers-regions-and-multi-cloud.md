# Terraform: Providers, Regions, Accounts and Multi-Cloud

> Provider versions and compatibility, extending Terraform when no provider exists, multiple regions and accounts, multi-cloud layouts, cloud migration, and building IAM roles and EKS clusters.

## Key Concepts

### Provider compatibility

1. Pin with `~>` so patch updates come in but major versions do not.
2. Commit the lock file so CI and laptops match.
3. `terraform providers` shows which module requires which provider.
4. Read the release notes before upgrading; providers do have breaking changes.
5. Never delete the lock file just to make CI pass.

### Multi-cloud

1. One provider block per cloud, with aliases for extra regions or accounts.
2. Provider-specific modules. Do not force AWS and Azure into one generic module.
3. Separate state per cloud, account, environment, and region.
4. Separate identity and pipeline stage per cloud.
5. Share the standards: naming, tags, policy checks.

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}
```

### Cross-region dependencies

1. Use provider aliases for each region.
2. Keep separate state per region.
3. Pass values between regions as variables, or read them from remote state.
4. Deploy in a defined order through the pipeline.

```hcl
provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

resource "aws_s3_bucket" "dr_backup" {
  provider = aws.dr
  bucket   = "app-backup-dr"
}
```

#### Remember

Some services are global (IAM, Route 53, CloudFront). Keep those in one global stack instead of duplicating them per region.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you handle provider or module version problems?</summary>

#### Where to look

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}
```

Also check `.terraform.lock.hcl` and the module `version` argument.

#### Useful command

```bash
terraform providers        # shows which module needs which provider
terraform init -upgrade    # only when you intend to upgrade
```

#### Upgrade process

1. Do it in its own pull request.
2. Read the release notes for breaking changes.
3. Run `init -upgrade`, validate, and test.
4. Compare the plan in a lower environment first.
5. Then promote.

#### What to avoid

Do not delete `.terraform.lock.hcl` just to make CI pass. Find out why local and CI picked different versions.

#### Interview answer

"I check `required_version`, the provider constraints, the lock file, and the module version, and `terraform providers` shows which module needs what. I pin ranges and commit the lock file. Upgrades happen in their own pull request after reading the release notes, testing in a lower environment, and comparing plans. I never delete the lock file just to make the pipeline pass."

</details>

<details><summary>Q2. [Intermediate] How do you handle provider version conflicts? <em>(scenario)</em></summary>

#### Pin the versions

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}
```

#### Commit the lock file

`.terraform.lock.hcl` belongs in Git for root modules. It keeps CI and laptops on the same versions.

#### Debug

```bash
terraform providers        # which module needs which provider
terraform version
terraform init -upgrade    # only when upgrading on purpose
```

#### Interview answer

"I pin `required_version` and provider constraints and commit the lock file so CI and laptops resolve the same versions. `terraform providers` shows which module is pulling in a conflicting constraint, which is usually an old module needing an update. Upgrades happen deliberately in their own pull request, and I never delete the lock file just to make the pipeline pass."

</details>

<details><summary>Q3. [Intermediate] Have you written a custom provider or used external data sources?</summary>

#### Honest answer

If you have not written a provider, say so, and explain what you would do instead.

#### Order of preference

1. Official provider.
2. Community or REST/HTTP provider.
3. `external` data source for simple read-only lookups.
4. Custom provider only when nothing else fits.

#### Example: external data source

```hcl
data "external" "config" {
  program = ["python3", "${path.module}/get_config.py"]
}

resource "aws_instance" "app" {
  ami           = data.external.config.result.ami_id
  instance_type = "t3.small"
}
```

Keep it read-only and predictable. Terraform may run it during refresh and planning.

#### When a custom provider is justified

An internal API that needs proper create, read, update, delete behaviour, schema validation, and import support.

#### Interview answer

"I have not written a production provider, and I would be honest about that. I first look for an official provider, then a REST or HTTP provider, then a read-only `external` data source. I have used data sources to look up existing networks, images, and account details so modules do not hardcode IDs. A custom provider is worth it only for an internal API that needs proper CRUD, validation, and import support, plus tests and ownership."

</details>

<details><summary>Q4. [Advanced] How do you extend Terraform when no provider exists?</summary>

#### Options from easiest to hardest

1. **Existing provider** — check the registry first.
2. **`http` data source** — read-only calls to a REST API.
3. **`external` data source** — run a small script that returns JSON.
4. **`terraform_data` with a provisioner** — last resort for a one-off action.
5. **Custom provider** — write it in Go with the Terraform Plugin Framework.

#### External data source example

```hcl
data "external" "cmdb" {
  program = ["python3", "${path.module}/lookup.py"]

  query = {
    app_name = var.app_name
  }
}
```

The script reads JSON from stdin and prints a flat JSON object.

#### When to build a real provider

Your internal system needs full create, read, update, delete behaviour, schema validation, and import support. Then you also need tests, versioning, and an owner.

#### Interview answer

"First I check whether an official or community provider already exists. For simple read-only needs I use the `http` or `external` data source. A custom provider written in Go with the Plugin Framework is worth it only when an internal API needs real CRUD support, schema validation, and import, and when someone will own and test it long term."

</details>

<details><summary>Q5. [Advanced] How do you handle multiple regions and multiple accounts?</summary>

#### Multiple regions: provider alias

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "aws" {
  alias  = "west"
  region = "us-west-2"
}

resource "aws_s3_bucket" "backup" {
  provider = aws.west
  bucket   = "app-backup-west"
}
```

#### Multiple accounts: assume role

```hcl
provider "aws" {
  alias  = "prod"
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::111122223333:role/TerraformRole"
  }
}
```

#### Sharing values between stacks

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-tf-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
}
```

#### Interview answer

"For multiple regions I use provider aliases, and for multiple accounts I use a provider with `assume_role` into a Terraform role in the target account. I keep separate state per account and region but share the same modules so everything is built the same way. Stacks exchange values through remote state outputs or stable interfaces like DNS."

</details>

<details><summary>Q6. [Advanced] You need infrastructure in 10 AWS regions. How do you structure it?</summary>

#### Approach

1. Write one reusable regional module.
2. Give each region its own state file.
3. Use a pipeline matrix to plan all regions in parallel and control how many apply at once.
4. Keep global resources such as IAM, Route 53, and CloudFront in a separate global stack.

#### Why not one big state with provider aliases?

Provider aliases work for a small fixed list, but with one state:

- One failed region can block all the others.
- The blast radius is huge.
- Plans get slow.

#### Interview answer

"I build one regional module and give every region its own state so a failure in one region does not block the rest. A pipeline matrix runs the plans in parallel and controls apply concurrency. Region-specific values like CIDRs and availability zones come from variables. Global resources like IAM and DNS live in a separate global stack."

</details>

<details><summary>Q7. [Intermediate] How do you provision resources across two accounts?</summary>

#### Example

```hcl
provider "aws" {
  alias  = "app"
  region = "us-east-1"
}

provider "aws" {
  alias  = "logs"
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::${var.logs_account_id}:role/TerraformRole"
  }
}

# Bucket in the logging account
resource "aws_s3_bucket" "logs" {
  provider = aws.logs
  bucket   = "app-logs-${var.environment}"
}

# Role in the app account
resource "aws_iam_role" "app" {
  provider = aws.app
  name     = "app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Bucket policy allowing the app account role
resource "aws_s3_bucket_policy" "logs" {
  provider = aws.logs
  bucket   = aws_s3_bucket.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.app.arn }
      Action    = ["s3:PutObject"]
      Resource  = "${aws_s3_bucket.logs.arn}/*"
    }]
  })
}
```

#### Interview answer

"I define one provider alias per account, with `assume_role` pointing at a Terraform role in the target account, then set `provider = aws.<alias>` on each resource. The trust and resource policies together allow cross-account access. In larger setups there is a management account holding the Terraform roles and a separate account for state, all with least-privilege permissions."

</details>

<details><summary>Q8. [Advanced] How do you structure Terraform for multi-cloud?</summary>

#### Approach

1. Write provider-specific modules. Do not try to hide AWS and Azure behind one generic module.
2. Separate state per cloud, account, environment, and region.
3. Give each cloud its own identity and its own pipeline stage.
4. Share the standards: naming, tags, policy checks, review process.
5. Connect stacks through stable outputs or DNS, not one shared state.

#### Example provider setup

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}
```

#### Interview answer

"I use provider-specific modules instead of one generic module that pretends the clouds are the same, and I separate state by cloud, account, environment, and region. Each cloud gets its own least-privilege identity and pipeline stage. What I share across clouds is the standards: naming, tagging, policy checks, and review process. That way one cloud outage or provider bug does not block everything."

</details>

<details><summary>Q9. [Advanced] How do you migrate infrastructure from one cloud to another? <em>(scenario)</em></summary>

#### Steps

1. Build the target environment with new Terraform code, in its own state.
2. Run both environments in parallel.
3. Copy the data: database dump and restore, or replication.
4. Move traffic gradually with DNS.
5. Keep the old environment for a rollback window.
6. Destroy the old environment once everyone agrees.

#### Important point

You cannot "migrate state" from AWS to Azure. The resources are different. You write new code and use `terraform import` only for resources that already exist in the target cloud.

#### Interview answer

"State does not move between clouds, because the resource types are different, so I write new code for the target cloud in its own state. I run both sides in parallel, copy the data, and shift traffic with DNS so rollback is possible. If some resources already exist in the target cloud, I import them instead of recreating them. The old environment is destroyed only after an agreed rollback window."

</details>

<details><summary>Q10. [Advanced] Migrating Terraform state across clouds</summary>

When migrating infrastructure across providers - for example AWS to Azure - don't try to reuse the old state. The resources and providers are fundamentally different; there's nothing to "migrate" at the resource level, only at the process level.

1. **Back up the old state** before touching anything:

```bash
terraform state pull > terraform.tfstate.backup
```

2. **Create/import the target resources** on the new cloud. New resources get created normally through `terraform apply`; resources that already exist for some other reason get brought under management with `terraform import`:

```bash
terraform import azurerm_resource_group.rg /subscriptions/<sub-id>/resourceGroups/prod-rg
```

3. **Validate with `terraform plan`** against the new state until it shows no unexpected changes.
4. **Migrate application traffic** to the new infrastructure - DNS cutover, connection string changes, whatever the application needs - only once the new infrastructure is confirmed healthy.
5. **Decommission the old infrastructure** last, after traffic has been running successfully on the new cloud for a safe period.

**Narrower case:** if only the *backend* is changing (e.g. moving state storage from one Azure Storage account to another, still within Terraform/Azure) rather than the cloud provider itself, that's much simpler:

```bash
terraform init -migrate-state
```

This copies existing state into the new backend configuration - no resource recreation involved.

#### Short interview answer

I don't try to reuse state across providers - the resource types are different, so there's nothing to carry over directly. I back up the old state with `terraform state pull`, stand up the new infrastructure (importing anything that needs to be brought under management), validate with `plan` until it's clean, cut traffic over once the new side is verified healthy, and only then decommission the old infrastructure. If it's just a backend change within the same provider, `terraform init -migrate-state` handles that without any of this.

</details>

<details><summary>Q11. [Intermediate] How do you create IAM roles in Terraform?</summary>

#### Two parts of a role

1. **Trust policy:** who can assume the role.
2. **Permission policy:** what the role can do.

#### Example

```hcl
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "app-role"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy_attachment" "app_s3" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_s3.arn
}
```

#### Good practices

- Use `aws_iam_policy_document` instead of hand-written JSON strings.
- Give only the actions that are needed. Avoid `"*"`.
- Use a module when the same role pattern repeats.
- Test the access after apply and check CloudTrail.

#### Interview answer

"I separate the trust policy from the permission policy. I build both with `aws_iam_policy_document` so the JSON is valid and can use variables. I keep permissions least privilege and avoid wildcards. When the same role pattern repeats, I put it in a module with required tags and boundaries, and I test the access after applying."

</details>

<details><summary>Q12. [Intermediate] How do you create an EKS cluster with Terraform?</summary>

#### What you need

1. VPC with private subnets
2. IAM roles for the cluster and the nodes
3. The EKS cluster itself
4. Managed node groups
5. Add-ons: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver

#### Example

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.8.4"

  cluster_name    = "payments-prod"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      desired_size = 3
      max_size     = 12
    }
  }
}
```

#### Control plane vs worker nodes

| Control plane (managed by AWS) | Worker nodes (yours) |
|---|---|
| API server | kubelet |
| etcd, stores cluster state | Container runtime |
| Scheduler | Runs your pods |
| Controllers | Networking agents |

#### After apply, check

API access, node status, system pods, DNS, storage class, autoscaling, and a test workload.

#### Interview answer

"I use a pinned EKS module with a VPC, private subnets, cluster and node IAM roles, managed node groups, and the core add-ons. AWS runs the control plane, which is the API server, etcd, scheduler, and controllers, while worker nodes run kubelet and my pods. I plan cluster, node, and add-on upgrades separately. After apply I check API access, node readiness, system pods, DNS, and a sample workload, because a successful apply alone does not prove the cluster works."

</details>
