# Checkov Interview Summary

## What It Is

Checkov is a static policy and security scanner for infrastructure-as-code. For Terraform, it reads the configuration (or a supported plan in JSON) and checks it against built-in or custom policies.

It catches misconfigurations such as public exposure, missing encryption or logging, weak network rules, and unsafe defaults. It also supports other IaC frameworks besides Terraform.

Checkov does **not** prove runtime security. It doesn't replace `terraform validate`, provider policy, cloud audit, or penetration testing — it's one layer, not the whole program.

## Running It

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

## Handling Exceptions

An exception must record:

- The specific check ID
- The business or technical reason
- An owner
- A compensating control
- Who approved it
- An expiry date

A suppression is **not** a fix — it's a tracked, time-bound decision to accept risk. Never skip an entire directory or severity just to make the pipeline green.

## Custom Policies

Organization-specific rules should be versioned and unit tested like any other code. Roll them out in audit or advisory mode first, so you can see what they'd block, before switching them to enforce and failing production changes.
