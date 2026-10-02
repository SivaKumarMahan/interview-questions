# Testing Tools: Checkov

> Checkov as an IaC policy scanner for Terraform: running it, CI/CD integration, fixing failures, suppressions and custom checks, and source versus plan scanning.

## Key Concepts

### What Checkov Is

Checkov is a static policy and security scanner for infrastructure-as-code. For Terraform, it reads the configuration (or a supported plan in JSON) and checks it against built-in or custom policies.

It catches misconfigurations such as public exposure, missing encryption or logging, weak network rules, and unsafe defaults. It also supports other IaC frameworks besides Terraform.

Checkov does **not** prove runtime security. It doesn't replace `terraform validate`, provider policy, cloud audit, or penetration testing — it's one layer, not the whole program.

### Running Checkov

```bash
checkov --directory . --framework terraform
checkov --file main.tf --framework terraform
```

Run it locally or in a pre-commit hook for fast feedback, and again in pull-request CI before `terraform apply`. In CI:

| Practice | Why |
| --- | --- |
| Pin the Checkov version | Keeps results reproducible across runs |
| Publish a machine-readable report (SARIF, JUnit XML) | Makes findings visible in the PR and to other tools |
| Fail according to an agreed policy | Turns the scan into an enforceable gate, not just a suggestion |

Review each finding against the real resource path, its variables and modules, the provider's actual behavior, and the environment it targets — don't just react to the check ID.

### Handling Exceptions

An exception must record:

- The specific check ID
- The business or technical reason
- An owner
- A compensating control
- Who approved it
- An expiry date

A suppression is **not** a fix — it's a tracked, time-bound decision to accept risk. Never skip an entire directory or severity just to make the pipeline green.

### Custom Policies

Organization-specific rules should be versioned and unit tested like any other code. Roll them out in audit or advisory mode first, so you can see what they'd block, before switching them to enforce and failing production changes.

## Interview Questions

### 1. What is Checkov, and where do you use it with Terraform?

**Answer:**

Checkov statically analyzes Terraform and other IaC against security and policy checks before infrastructure is deployed. I run it locally or in pre-commit for fast feedback and in pull-request CI as an enforced gate.

It can detect patterns such as public storage, unrestricted security rules, missing encryption or logging and unsafe Kubernetes settings.

```bash
checkov --directory ./terraform --framework terraform
```

I combine it with `terraform fmt -check`, `validate`, a reviewed plan, provider/cloud policy, and post-deployment verification. Static scanning can't see every runtime value, external resource, or business requirement. A pass is evidence, not proof of complete security.

### 2. How do you integrate Checkov into a CI/CD pipeline?

**Answer:**

The pipeline uses a pinned Checkov version and checks out the reviewed commit. It scans the correct root modules and variable/plan context, writes a machine-readable report where required, and blocks based on the organization's agreed policy.

The job has no cloud credentials when scanning the source doesn't need them. Access to the report and its artifacts is restricted, because findings can reveal how the infrastructure is built.
```yaml
- name: Scan Terraform with Checkov
  run: checkov --directory infrastructure --framework terraform
```

I keep the same configuration locally and in CI, deliberately exclude generated and vendor directories, and make the result visible on the pull request. After a tool or policy upgrade, I test it against representative repositories before enforcing it, so a new rule set doesn't unexpectedly block every team.

### 3. Should you scan Terraform source or the Terraform plan?

**Answer:**

Source scanning is fast. It gives file-level feedback before you need credentials or a plan, but some values stay unknown, or only appear once modules resolve. Plan scanning can evaluate more of the resolved configuration, but it needs a safely generated JSON plan, and that plan may contain sensitive values.

I usually scan the source on every pull request, and add a protected plan scan for high-risk production workflows.

Plan and state artifacts are encrypted, access-controlled, and never printed without care. Neither mode replaces reviewing destructive changes, securing state, enforcing runtime cloud policy, or testing the application itself.

### 4. Checkov fails a Terraform pipeline. How do you investigate and fix it?

**Answer:**

I capture the check ID, resource address, file and line, the evaluated attribute, and the guideline it's checking. Then I trace the full module and variable path, to tell apart a real insecure value from an unknown or dynamic value, a generated configuration, or a false positive.

I read the policy and the provider's behavior, then fix the Terraform to the secure design — for example private access, encryption, diagnostic logging, or a restricted CIDR. I rerun Checkov plus Terraform validate/plan to confirm.

If an exception is genuinely needed, I document the threat, the compensating control, the owner, the approval, and the expiry, against the exact check and resource. I don't use a broad `--skip-check` or suppress it repo-wide.

After deployment, cloud policy/configuration evidence verifies that the intended control exists.

### 5. How do Checkov suppressions and custom checks work safely?

**Answer:**

A narrow inline suppression associates a Checkov check ID and reason with a specific Terraform block:

```hcl
resource "aws_s3_bucket" "audit_archive" {
  # checkov:skip=CKV_AWS_18: Central organization trail writes access evidence.
  bucket = "example-audit-archive"
}
```

The syntax alone doesn't make the exception acceptable. Review still checks the reason, the compensating evidence, the scope, and the expiry. Exceptions are logged in an inventory and rechecked periodically.

For an organization-specific rule, I write a versioned external check, add positive and negative unit fixtures, and load it through the supported external-check mechanism. I run it in report-only mode first, measure false positives, document the fix and its owner, then turn on enforcement.

Policy code gets the same review and release discipline as infrastructure modules do.
