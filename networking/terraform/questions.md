# Terraform Networking Interview Questions

### 1. What are the prerequisites before importing a VPC in Terraform?

**Answer:**

I gather the exact details first: account, region, VPC ID, CIDR and IPv6 settings, DNS attributes, tenancy, tags, ownership, and what depends on it. The provider alias and credentials must point at that account and region, and a matching resource block or module address must already exist in code.

I also confirm the VPC is not already managed in another state file.

Importing a VPC does not automatically import the things inside it. Subnets, route tables, gateways, ACLs, endpoints, and peering connections each need their own import and their own address. Before I start, I lock and back up the remote state and decide those addresses up front.

Then I import, run `state show` to see what Terraform recorded, and update the configuration to match without triggering a replacement. I review a full plan and test connectivity afterward.

This process keeps an adoption exercise from accidentally changing production networking.

---

### 2. How do you pass arguments to a VPC while using `terraform import`?

**Answer:**

You don't. Import only maps a provider resource ID to an existing Terraform address — it does not take configuration arguments. For example:

```bash
terraform import aws_vpc.prod vpc-0123456789
```

CIDR, DNS settings, tenancy, and tags belong in the `aws_vpc` resource block, and can be supplied there through variables. After import, I check `terraform state show aws_vpc.prod` and run a plan, then adjust the code until it matches the live VPC with no unexpected changes.

Newer import blocks make the mapping reviewable in code, but they still don't replace writing the resource configuration.

---

### 3. How do you dynamically retrieve VPC details to create an EC2 instance? Write the code.

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

---

### 4. What dependencies are needed for an IP address or networking resource?

**Answer:**

It depends on the address type and the traffic path.

A public-facing EC2 instance typically needs a VPC, a subnet that assigns public IPs, an internet gateway with a route, a network ACL, a security group, and an Elastic IP association.

A private address may need route tables, NAT or another egress path, DNS, peering or transit routing, or a load balancer in front of it.

Where one resource references another, like `subnet_id = aws_subnet.public.id`, Terraform works out the order on its own. I prefer that over `depends_on`, because the reference also documents the real relationship between the resources. I only reach for `depends_on` when there's a dependency Terraform can't see from an attribute — for example, waiting for a policy attachment to finish before a service calls an API.

After apply, I check the real thing: that routing works, ACLs and security groups behave as expected, DNS resolves, and the application port responds from the actual source.
