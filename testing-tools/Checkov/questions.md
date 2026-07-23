## 1. What is Checkov, and where do you use it with Terraform?

**Answer:**

Checkov statically analyzes Terraform and other IaC against security and policy checks before infrastructure is deployed. I run it locally or in pre-commit for fast feedback and in pull-request CI as an enforced gate. It can detect patterns such as public storage, unrestricted security rules, missing encryption or logging and unsafe Kubernetes settings.

```bash
checkov --directory ./terraform --framework terraform
```

I combine it with `terraform fmt -check`, `validate`, a reviewed plan, provider/cloud policy and post-deployment verification. Static scanning cannot see every runtime value, external resource or business requirement, so a pass is evidence—not proof of complete security.

## 2. How do you integrate Checkov into a CI/CD pipeline?

**Answer:**

The pipeline uses a pinned Checkov version, checks out the reviewed commit, scans the correct root modules and variable/plan context, writes a machine-readable report where required, and blocks on the organization's agreed policy. The job has no cloud credentials when scanning source does not need them, and report/artifact access is restricted because findings can reveal architecture.

```yaml
- name: Scan Terraform with Checkov
  run: checkov --directory infrastructure --framework terraform
```

I keep the same configuration locally and in CI, exclude generated/vendor directories deliberately, and make the result visible on the pull request. After tool/policy upgrades I test representative repositories before enforcement so a new rule set does not unexpectedly block every team.

## 3. Checkov fails a Terraform pipeline. How do you investigate and fix it?

**Answer:**

I capture the check ID, resource address, file/line, evaluated attribute and guideline. I inspect the complete module and variable path to distinguish a real insecure value, unknown/dynamic value, generated configuration or false positive. I read the policy and provider behavior, then change the Terraform to the secure design—for example private access, encryption, diagnostic logging or a restricted CIDR—and rerun Checkov plus Terraform validation/plan.

If an exception is genuinely required, I document threat, compensating control, owner, approval and expiry against the exact check/resource. I do not use a broad `--skip-check` or suppress the repository. After deployment, cloud policy/configuration evidence verifies that the intended control exists.

## 4. How do Checkov suppressions and custom checks work safely?

**Answer:**

A narrow inline suppression associates a Checkov check ID and reason with a specific Terraform block:

```hcl
resource "aws_s3_bucket" "audit_archive" {
  # checkov:skip=CKV_AWS_18: Central organization trail writes access evidence.
  bucket = "example-audit-archive"
}
```

The syntax alone does not make the exception acceptable. Review verifies the reason, compensating evidence, scope and expiry. Exceptions are inventoried and periodically rechecked.

For an organization-specific rule, I create a versioned external check, add positive/negative unit fixtures and load it with the supported external-check mechanism. I first report findings without blocking, measure false positives, document remediation and ownership, then enforce it. Policy code receives the same review and release discipline as infrastructure modules.

## 5. Should you scan Terraform source or the Terraform plan?

**Answer:**

Source scanning is fast and provides file-level feedback before credentials or planning, but some values remain unknown or are created through modules. Plan scanning can evaluate more resolved configuration but requires a safely generated JSON plan and may contain sensitive values. I often scan source on every pull request and add a protected plan scan for high-risk production workflows.

Plan and state artifacts are encrypted, access-controlled and never printed indiscriminately. Neither mode replaces review of destructive changes, state security, runtime cloud policy or application testing.
