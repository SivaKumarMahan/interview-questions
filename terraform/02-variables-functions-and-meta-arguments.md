# Terraform: Variables, Functions and Meta-Arguments

> Meta-arguments like count and for_each, built-in functions, input validation, tagging with default tags and merge, CIDR helpers, and creating resources from external data.

## Key Concepts

### Meta-arguments

| Meta-argument | What it does |
|---|---|
| `count` | Numbered instances, good for identical copies |
| `for_each` | Named instances from a map or set, good when each has an identity |
| `depends_on` | A dependency Terraform cannot infer |
| `lifecycle` | Controls replacement and drift behaviour |
| `provider` | Picks a provider alias |

#### `for_each` with a simple map

```hcl
variable "resource_groups" {
  type = map(string)

  default = {
    dev  = "dev-rg"
    test = "test-rg"
    prod = "prod-rg"
  }
}

resource "azurerm_resource_group" "this" {
  for_each = var.resource_groups
  name     = each.value
  location = "centralindia"
}
```

Addresses become `azurerm_resource_group.this["dev"]`, and so on.

#### `for_each` with a map of objects

```hcl
variable "storage_accounts" {
  type = map(object({
    name     = string
    location = string
    tier     = string
  }))
}

resource "azurerm_storage_account" "this" {
  for_each                 = var.storage_accounts
  name                     = each.value.name
  location                 = each.value.location
  account_tier             = each.value.tier
  resource_group_name      = azurerm_resource_group.main.name
  account_replication_type = "LRS"
}
```

`each.key` is the map key, `each.value` is the whole object.

#### `for_each` over a list of names

```hcl
resource "azurerm_resource_group" "this" {
  for_each = toset(var.resource_group_names)
  name     = each.value
  location = var.location
}
```

`toset()` removes duplicates. If duplicates mean the input is wrong, reject them with validation instead of hiding them.

### Functions you actually use

Try any of these with `terraform console`.

#### List functions

**`length()`** — how many items.

```hcl
length(["a", "b", "c"])   # 3
```

**`element()`** — item at an index.

```hcl
element(["Mon", "Tue", "Wed"], 2)   # "Wed"
```

**`slice()`** — a part of a list, end index not included.

```hcl
slice([1, 2, 3, 4, 5], 1, 3)   # [2, 3]
```

**`concat()`** — join lists together.

```hcl
concat(["a", "b"], ["c"])   # ["a", "b", "c"]
```

**`flatten()`** — turn nested lists into one list.

```hcl
flatten([["a", "b"], ["c"], ["d"]])   # ["a", "b", "c", "d"]
```

**`distinct()`** — remove duplicates, keep the order.

```hcl
distinct(["a", "b", "a", "c"])   # ["a", "b", "c"]
```

**`compact()`** — remove empty and null values.

```hcl
compact(["apple", "", "mango", null])   # ["apple", "mango"]
```

**`formatlist()`** — format every item.

```hcl
formatlist("app-%s", ["web", "api"])   # ["app-web", "app-api"]
```

**`toset()`** — convert a list to a set, for `for_each`.

```hcl
toset(["a", "b", "a"])   # ["a", "b"]
```

#### Map functions

**`keys()` and `values()`**

```hcl
keys({ env = "prod", app = "web" })     # ["app", "env"]
values({ env = "prod", app = "web" })   # ["web", "prod"]
```

**`lookup()`** — read a key with a fallback.

```hcl
variable "db_urls" {
  type = map(string)

  default = {
    dev  = "dev-db.internal"
    prod = "prod-db.internal"
  }
}

output "db_url" {
  value = lookup(var.db_urls, var.environment, "localhost")
}
```

**`merge()`** — combine maps. Later maps win.

```hcl
merge({ Env = "dev", Owner = "team-a" }, { Env = "prod" })
# { Env = "prod", Owner = "team-a" }
```

This is the usual way to build tags:

```hcl
locals {
  tags = merge(var.common_tags, { Component = "database" })
}
```

**`zipmap()`** — build a map from two lists.

```hcl
zipmap(["timeout", "retries"], [30, 5])
# { timeout = 30, retries = 5 }
```

**`for` expression** — transform a map.

```hcl
locals {
  prices = { apple = 0.5, banana = 0.3 }

  discounted = { for name, price in local.prices : name => price * 0.9 }
  # { apple = 0.45, banana = 0.27 }
}
```

**Build a `for_each` map from a list of objects**

```hcl
locals {
  users_map = { for u in var.users : u.name => u }
}
```

#### String functions

**`format()`** — build a string from a pattern.

```hcl
format("web-%s-%02d", "prod", 3)   # "web-prod-03"
```

**`join()` and `split()`**

```hcl
join(",", ["a", "b", "c"])       # "a,b,c"
split(",", "a,b,c")              # ["a", "b", "c"]
split("@", "user1@example.com")  # ["user1", "example.com"]
```

**`replace()`**

```hcl
replace("my.app.name", ".", "-")   # "my-app-name"
```

**`upper()`, `lower()`, `title()`**

```hcl
upper("prod")         # "PROD"
lower("PROD")         # "prod"
title("hello world")  # "Hello World"
```

**`trimspace()` and `chomp()`** — remove spaces or a trailing newline. Useful after `file()`.

```hcl
chomp(file("${path.module}/version.txt"))
```

**`substr()`**

```hcl
substr("terraform", 0, 4)   # "terr"
```

#### Number and network functions

**`min()`, `max()`, `abs()`, `ceil()`, `floor()`**

```hcl
max(3, 7, 2)   # 7
ceil(4.1)      # 5
```

**`cidrsubnet()`** — split a network into subnets.

```hcl
cidrsubnet("10.0.0.0/16", 8, 0)   # "10.0.0.0/24"
cidrsubnet("10.0.0.0/16", 8, 1)   # "10.0.1.0/24"
```

```hcl
locals {
  subnets = [for i in range(3) : cidrsubnet("10.0.0.0/16", 8, i)]
}
```

**`cidrhost()`** — a specific address inside a network.

```hcl
cidrhost("10.0.1.0/24", 10)   # "10.0.1.10"
```

#### Validation and safety

**`can()`** — true if the expression works.

```hcl
can(regex("^t3\\.", var.instance_type))
```

**`try()`** — return the first value that works.

```hcl
locals {
  region = try(var.region, "us-east-1")
}
```

**Use them in variable validation**

```hcl
variable "environment" {
  type = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}
```

#### File functions

**`file()`** — read a file as a string. The file must exist before Terraform runs.

```hcl
locals {
  startup_script = file("${path.module}/startup.sh")
}
```

**`templatefile()`** — read a file and fill in variables. Better than `file()` for scripts and config.

```hcl
user_data = templatefile("${path.module}/init.sh.tftpl", {
  app_name = var.app_name
  port     = 8080
})
```

**`fileexists()`, `basename()`, `dirname()`, `abspath()`**

```hcl
fileexists("${path.module}/config.txt")   # true or false
basename("/tmp/app/main.tf")              # "main.tf"
dirname("/tmp/app/main.tf")               # "/tmp/app"
```

#### Path values

| Value | Meaning |
|---|---|
| `path.module` | Folder of the current module |
| `path.root` | Folder of the root module |
| `path.cwd` | Current working directory |

#### Encoding functions

**`jsonencode()` and `jsondecode()`**

```hcl
policy = jsonencode({
  Version = "2012-10-17"
  Statement = [{
    Effect   = "Allow"
    Action   = "s3:GetObject"
    Resource = "${aws_s3_bucket.app.arn}/*"
  }]
})
```

```hcl
locals {
  users = jsondecode(file("${path.module}/users.json"))
}
```

**`yamlencode()` and `yamldecode()`** — the same idea for YAML.

**`base64encode()` and `base64decode()`**

```hcl
resource "aws_instance" "web" {
  user_data = base64encode(file("${path.module}/init.sh"))
}
```

### Tagging and labelling

#### Set defaults once

```hcl
provider "aws" {
  default_tags {
    tags = {
      Environment = var.environment
      Owner       = var.owner
      CostCenter  = var.cost_center
      ManagedBy   = "terraform"
    }
  }
}
```

#### Or merge in a module

```hcl
locals {
  tags = merge(var.common_tags, {
    Component = "database"
  })
}
```

#### Why it matters

Tags drive cost reports, ownership, automated cleanup, and compliance checks. Enforce them with variable validation and a policy check.

### CIDR basics

```text
10.0.0.0/16   = 65,536 addresses    (a whole VPC)
10.0.1.0/24   = 256 addresses       (a subnet)
10.0.1.0/28   = 16 addresses        (a small subnet)
```

The number after the slash is how many bits are fixed. The remaining bits are host addresses.

#### Planning tips

1. Plan non-overlapping ranges across environments and clouds, or peering will fail later.
2. Leave room to grow. You cannot easily shrink or move a subnet afterwards.
3. Cloud providers reserve some addresses in every subnet, so the usable count is lower than the raw number. AWS reserves 5 per subnet.

#### Useful function

```hcl
locals {
  subnets = [for i in range(3) : cidrsubnet("10.0.0.0/16", 8, i)]
  # 10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24
}
```

## Interview Questions

### 1. What is the difference between `count` and `for_each`?

| `count` | `for_each` |
|---|---|
| Creates numbered instances: `aws_subnet.app[0]` | Creates named instances: `aws_subnet.app["web"]` |
| Good for identical copies or an on/off switch | Good for named items with different values |
| Removing a middle item shifts all later indexes | Keys stay stable when an item is removed |

#### `count` example

```hcl
resource "aws_instance" "web" {
  count         = 3
  ami           = var.ami
  instance_type = "t3.micro"
}
```

#### `for_each` example

```hcl
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
}

resource "aws_subnet" "app" {
  for_each          = var.subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
}
```

#### Important point

Switching from `count` to `for_each` changes resource addresses, so Terraform may want to destroy and recreate. Use a `moved` block or `terraform state mv` to avoid that.

#### Interview answer

"`count` gives numbered instances and is fine when the resources are identical. `for_each` gives named instances from a map or set, which is safer when each item has an identity, because removing one item does not shift the others. If I switch between them, I use `moved` blocks so Terraform does not recreate resources."

### 2. Why does Terraform use `toset()`?

`toset()` converts a collection into a set. A set contains unique values and does not preserve a meaningful order.

```hcl
locals {
  unique_servers = toset(["web", "app", "web", "db"])
}
```

The resulting set contains `web`, `app`, and `db` only once.

#### Using a set with `for_each`

```hcl
resource "azurerm_resource_group" "example" {
  for_each = toset(["development", "test", "production"])

  name     = "rg-${each.value}"
  location = "Central India"
}
```

Terraform creates one resource instance for each unique string. The string is also used as the stable resource key. Choose values that will remain stable because renaming a key can make Terraform plan a destroy and create unless the state address is moved.

#### List compared with set

| List | Set |
| --- | --- |
| Ordered | Unordered |
| Allows duplicates | Contains unique values |
| Supports index access | Does not support index access |
| Use when position or order matters | Use when unique membership matters |

### 3. Why does Terraform use `each.value`?

Inside a resource or module that uses `for_each`:

- `each.key` is the current instance key.
- `each.value` is the value associated with that key.

#### Map example

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

#### Short interview answer

`each.value` gives the value of the current item in a `for_each` loop. It is especially useful with maps, where `each.key` identifies the resource instance and `each.value` contains that instance's configuration.

### 4. How do you validate input variables?

#### Simple validation

```hcl
variable "environment" {
  type        = string
  description = "Deployment environment"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.micro"

  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Only t3 instance types are allowed."
  }
}
```

#### Typed objects

```hcl
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
}
```

#### Preconditions

```hcl
resource "aws_instance" "app" {
  lifecycle {
    precondition {
      condition     = var.environment != "prod" || var.instance_type != "t3.micro"
      error_message = "Production cannot use t3.micro."
    }
  }
}
```

#### Interview answer

"I use `validation` blocks in variable declarations so bad input fails immediately with a clear message, for example only allowing dev, test, or prod, or only approved instance types. I also use strong types like `map(object({...}))` instead of plain strings, and `precondition` blocks when the rule depends on more than one value. Failing early is much cheaper than failing during apply."

### 5. How do you create resources from external data?

#### Example: create users from a JSON file

```hcl
locals {
  users = jsondecode(file("${path.module}/users.json"))

  users_map = { for u in local.users : u.username => u }
}

resource "aws_iam_user" "team" {
  for_each = local.users_map

  name = each.key

  tags = {
    Department = each.value.department
  }
}
```

#### Example: from an API

```hcl
data "http" "services" {
  url = "https://registry.example.com/services"
}

locals {
  services = jsondecode(data.http.services.response_body).items
}

resource "aws_lb_target_group" "services" {
  for_each = { for s in local.services : s.name => s }

  name     = each.key
  port     = each.value.port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
}
```

#### Warning

If the external data changes between runs, your plan changes too. Keep the source stable and read-only.

#### Interview answer

"I read the data with `jsondecode(file(...))`, the `http` data source, or an `external` data source, turn it into a map in `locals`, and drive `for_each` from that map so each item has a stable key. The important warning is that the plan now depends on outside data, so the source must be stable and read-only, otherwise every run produces a different plan."
### 6. How do you dynamically retrieve VPC details to create an EC2 instance? Write the code.

**Answer:**

I use a data source when the VPC is owned by another stack and has a stable, unique tag to search on. I also make sure the query can't accidentally match the wrong environment. For example:

```hcl
data "aws_vpc" "selected" {
  filter {
    name   = "tag:Name"
    values = ["prod-vpc"]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  filter {
    name   = "tag:Tier"
    values = ["private"]
  }
}

resource "aws_instance" "app" {
  ami           = var.ami_id
  instance_type = "t3.micro"
  subnet_id     = data.aws_subnets.private.ids[0]
}
```

For production I'd pick the subnet by a stable key instead of `[0]`, since list ordering can change. I'd also add the instance role, security groups, an encrypted root disk, tags, and a requirement for IMDSv2 (the safer, token-based way instances fetch metadata).

If the VPC is created in the same root module, I just reference its resource or module output directly. A data source isn't needed, and it would only add a weaker, implicit link between the two.
