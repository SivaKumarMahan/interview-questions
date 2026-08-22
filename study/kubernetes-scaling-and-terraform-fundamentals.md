# Kubernetes Scaling and Terraform Fundamentals

## 1. Vertical and Horizontal Scaling in Kubernetes

| Vertical scaling | Horizontal scaling |
| --- | --- |
| Gives a pod more CPU or memory | Adds more pod replicas |
| Also called scaling up | Also called scaling out |
| Makes one pod more powerful | Shares work across several pods |
| Often requires pod recreation | Adds new pods while current pods keep running |
| Limited by the size of a node | Can spread replicas across nodes |
| Useful for workloads that cannot use replicas | Usually best for stateless APIs and web applications |

### Example

An application starts with one pod using one CPU and 2 GB of memory.

Vertical scaling changes it to one larger pod:

```text
1 CPU → 4 CPUs
2 GB  → 8 GB
```

Horizontal scaling keeps the same pod size but increases the count:

```text
1 pod → 5 pods
```

A Kubernetes Service distributes traffic across the ready replicas.

### HPA and VPA

The Horizontal Pod Autoscaler (HPA) changes the number of replicas based on CPU, memory, custom, or external metrics.

The Vertical Pod Autoscaler (VPA) recommends or updates pod CPU and memory requests. Applying an update can require the pod to be recreated.

Horizontal scaling is usually preferred for stateless services because it improves availability and can grow beyond one node. Vertical scaling is useful for legacy, stateful, or single-instance applications that cannot easily share work across replicas.

### Short interview answer

Vertical scaling gives an existing pod more CPU or memory and is limited by node capacity. Horizontal scaling adds more replicas and normally uses HPA. Horizontal scaling is often preferred for stateless services because it provides better availability and fault tolerance, while VPA is useful when a workload benefits from a larger pod.

## 2. Why Terraform Uses `toset()`

`toset()` converts a collection into a set. A set contains unique values and does not preserve a meaningful order.

```hcl
locals {
  unique_servers = toset(["web", "app", "web", "db"])
}
```

The resulting set contains `web`, `app`, and `db` only once.

### Using a set with `for_each`

```hcl
resource "azurerm_resource_group" "example" {
  for_each = toset(["development", "test", "production"])

  name     = "rg-${each.value}"
  location = "Central India"
}
```

Terraform creates one resource instance for each unique string. The string is also used as the stable resource key. Choose values that will remain stable because renaming a key can make Terraform plan a destroy and create unless the state address is moved.

### List compared with set

| List | Set |
| --- | --- |
| Ordered | Unordered |
| Allows duplicates | Contains unique values |
| Supports index access | Does not support index access |
| Use when position or order matters | Use when unique membership matters |

## 3. Why Terraform Uses `each.value`

Inside a resource or module that uses `for_each`:

- `each.key` is the current instance key.
- `each.value` is the value associated with that key.

### Map example

```hcl
variable "instances" {
  default = {
    web = "Standard_B2s"
    app = "Standard_B4ms"
    db  = "Standard_D2s_v3"
  }
}

resource "azurerm_linux_virtual_machine" "vm" {
  for_each = var.instances

  name = each.key
  size = each.value
  # Other required VM arguments are omitted.
}
```

For the `web` instance, `each.key` is `web` and `each.value` is `Standard_B2s`.

When `for_each` uses a set of strings, `each.key` and `each.value` are the same string.

### Short interview answer

`each.value` gives the value of the current item in a `for_each` loop. It is especially useful with maps, where `each.key` identifies the resource instance and `each.value` contains that instance's configuration.

## 4. Terraform and OpenTofu

Terraform and OpenTofu are Infrastructure as Code tools with very similar configuration language and workflows. OpenTofu began as a fork after HashiCorp changed Terraform's license.

| Terraform | OpenTofu |
| --- | --- |
| Developed by HashiCorp | Community-governed under the Linux Foundation |
| Uses HashiCorp's source-available Business Source License for current releases | Uses the open-source Mozilla Public License 2.0 |
| Integrates with HCP Terraform and HashiCorp products | Focuses on an open, vendor-neutral ecosystem |
| Uses the `terraform` command | Uses the `tofu` command |

The main commands are similar:

```bash
terraform init
terraform plan
terraform apply
```

```bash
tofu init
tofu plan
tofu apply
```

Many configurations and providers work with both, but they are developed independently and compatibility should be tested before switching an existing project. Terraform can be practical for teams that use HashiCorp support and HCP Terraform. OpenTofu is attractive to teams that require an open-source, community-governed tool.

## 5. Preventing Concurrent Terraform Changes

Two users applying changes to the same state at the same time can cause conflicts or unsafe infrastructure changes. Use a remote backend that supports state locking.

### Azure

Azure Blob Storage uses a blob lease to lock the state while Terraform is changing it.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform"
    storage_account_name = "tfstateprod"
    container_name       = "tfstate"
    key                  = "production.tfstate"
  }
}
```

When one operation holds the lock, another operation against the same state receives a lock error and must wait or stop.

### AWS and Google Cloud

- The S3 backend supports state locking. Current Terraform versions can use S3 lockfiles; older configurations commonly use DynamoDB-based locking.
- The Google Cloud Storage backend protects state updates using object generation checks.

Always confirm the locking method supported by the Terraform or OpenTofu version and backend used by the project.

### Team controls

- Run production applies only through CI/CD.
- Allow one apply job per environment at a time.
- Use pull requests, a reviewed plan, and approval before apply.
- Give each environment its own state instead of sharing one state across development, test, and production.
- Use RBAC so only approved identities can apply production changes.
- Do not store state in Git or pass state files between team members manually.
- Do not use `-lock=false` for normal applies.
- Do not force-unlock until confirming that no operation still owns the lock.

### Short interview answer

Store Terraform state in a remote backend with locking. When one apply acquires the lock, another apply against the same state is blocked. In production, also serialize apply jobs through CI/CD, use separate state for each environment, and restrict apply permission with RBAC.
