# Helm: Security, CI/CD, and Troubleshooting

> Secrets and chart signing, Helm in CI/CD and GitOps, and monitoring and troubleshooting failed releases.

## Key Concepts

### Secrets

Do not commit plaintext secrets to `values.yaml`. Prefer a dedicated secret-management workflow such as:

- External Secrets Operator
- Secrets Store CSI Driver
- HashiCorp Vault
- Azure Key Vault or AWS Secrets Manager
- Sealed Secrets
- SOPS with an approved Helm integration

Remember that rendered manifests and release data can expose values. Restrict cluster access, CI logs, artifacts, and Helm release information.

### Chart Signing and Provenance

Helm can generate a provenance file — a record of where a chart came from and how it was built — and verify charts using GPG signatures.

```bash
helm package ./mychart --sign --key <key-id> --keyring <keyring-path>
helm verify mychart-1.0.0.tgz
```

For charts published to OCI registries, signing is often handled instead with a supply-chain tool such as Sigstore Cosign, depending on the organization's delivery standard.

### CI/CD and GitOps

A typical CI pipeline:

1. Lints the chart.
2. Validates values and renders templates.
3. Scans images and generated manifests.
4. Packages and publishes a fixed chart version that won't change afterward.
5. Promotes the version after approval.

In a push model, a pipeline runs Helm against the cluster directly. In a pull-based GitOps model, Flux or Argo CD watches Git or OCI sources instead, and continuously reconciles the cluster to match the declared release.

GitOps improves drift detection and avoids giving a central CI system broad cluster credentials.

Helm commonly participates in EKS/AKS delivery with Terraform for infrastructure, Jenkins or another CI system for builds, Argo CD/Flux for deployment, and Prometheus/Grafana/AppDynamics for observability.

### Monitoring and Troubleshooting

Useful checks:

```bash
helm lint ./mychart
helm template my-release ./mychart --debug
helm status my-release
helm history my-release
helm get values my-release --all
helm get manifest my-release
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl describe pod <pod>
kubectl logs <pod> --previous
```

Common causes of failure: invalid rendered YAML, missing values, an attempt to change a field that can't be changed after creation, a failed hook, a failed readiness probe, insufficient resources, an image-pull error, an RBAC restriction, or a dependency-version conflict.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you manage secrets in Helm charts?</summary>

**Answer:**

I never store plaintext secrets in `values.yaml`, in Git, inside a packaged chart, or in `--set` command history. Helm stores release data inside the cluster, so just calling a value "secret" in a template doesn't actually protect it.

My preferred approach is External Secrets Operator or the Secrets Store CSI Driver, backed by Vault, Key Vault, or a cloud secret manager. Workloads authenticate using their own identity, and Kubernetes only ever sees a mounted value or a synced Secret when it's actually needed.

If encrypted values in Git are acceptable for a project, I use SOPS or helm-secrets, with the encryption keys kept outside Git entirely. I restrict RBAC access to Secrets and Helm's release data, make sure CI logs never print rendered values, test that rotation actually works, and confirm that a namespace or service account without permission genuinely can't read the secret.

</details>

<details><summary>Q2. [Intermediate] How do you sign and verify Helm charts?</summary>

**Answer:**

For a classic chart repository, I package and sign the chart with a protected OpenPGP key, using `helm package --sign --key <name> --keyring <ring>`. I publish both the `.tgz` and its `.prov` file — a record of where the chart came from and how it was built — and verify it with `helm verify`.

Key identity, expiry, rotation, and access are all managed centrally. CI gets short-lived access to sign, rather than a developer's own exported private key.

For OCI registries, I prefer signing the chart's fixed digest with a supply-chain tool like Cosign, and enforcing that signature in CI or through admission policy. I also keep track of the source commit, the build workflow's identity, an SBOM and provenance record where relevant, and the registry's audit logs.

Signing proves who — or which workflow — produced an unmodified artifact. It doesn't prove the chart is actually safe. Linting, template and schema validation, security and policy checks, review, and a controlled promotion process are all still needed on top of signing.

</details>

<details><summary>Q3. [Basic] what is email signing and Helm chart signing? which tools do you use to sign Helm charts?</summary>

**A:**

**Email Signing:**

Email signing is the process of digitally signing an email message to verify the sender's identity and ensure the integrity of the message content. It uses cryptographic techniques to create a digital signature that is attached to the email.

The recipient can then verify the signature using the sender's public key, confirming that the email has not been altered and is indeed from the claimed sender. Common standards for email signing include **S/MIME** (Secure/Multipurpose Internet Mail Extensions) and **PGP** (Pretty Good Privacy).

**Helm Chart Signing:**

Helm chart signing is the process of digitally signing Helm charts to ensure their authenticity and integrity. By signing a Helm chart, the chart maintainer provides a way for users to verify that the chart has not been tampered with and is from a trusted source.

Helm uses **GPG** (GNU Privacy Guard) for signing charts. When a chart is signed, a signature file is created alongside the chart package.

Users can then verify the signature using the public key of the chart maintainer before installing the chart.

**Tools for Signing Helm Charts:**

1. **GPG (GNU Privacy Guard):** GPG is the primary tool used for signing Helm charts. It allows you to create a key pair (public and private keys) and use the private key to sign the chart. The public key can be shared with users who want to verify the chart's signature.

To sign a Helm chart, you can use the following command:

```bash
helm package <chart-path> --sign --key <key-id> --keyring <path-to-keyring>
```

To verify a signed Helm chart, you can use:

```bash
helm verify <chart-package>
```

In summary, email signing and Helm chart signing both serve to verify authenticity and integrity, but they apply to different contexts — email communication and software package distribution, respectively. GPG is the tool commonly used for signing Helm charts.

</details>

<details><summary>Q4. [Intermediate] How do you troubleshoot Helm chart deployment failures? <em>(scenario)</em></summary>

**Answer:** Run `helm status` and `helm get manifest` → validate the YAML → check Kubernetes events and logs → roll back with `helm rollback` if needed.

**Detailed interview approach:**
I start with `helm lint`, `helm template --debug`, and a server-side dry run, to catch template, values, and API-schema errors before anything actually deploys.

For a release that already failed, I use `helm status <release>`, `helm get values`, `helm get manifest`, and Kubernetes events and logs to pin down the exact cause — a bad hook, an admission policy rejection, an attempt to change an immutable field, a missing CRD, a bad image, a scheduling problem, or a failed readiness check.

I compare the rendered manifest and values against the last good revision. Then I fix the chart or the environment dependency in Git and run a controlled upgrade. If production is affected, I use `helm rollback <release> <revision>` and check the pods and application metrics afterward.

Tests, schema validation, pinned chart versions, and time-limited atomic upgrades are what prevent this from happening again.

</details>

<details><summary>Q5. [Intermediate] How do you troubleshoot Helm upgrade failures and perform safe rollbacks? <em>(asked in interview round)</em></summary>

**Answer:**

Helm stores each release revision as a Secret in the release namespace. Most upgrade problems are either a template or validation error before anything is applied, resources that do not become healthy within the timeout, or a release stuck in a `pending-*` state after an interrupted operation.

**Steps:**

1. **Check the release state**: `helm status` and `helm history`. Note the last revision with status `deployed`.
2. **Render before applying**: `helm template` or `helm upgrade --dry-run=server` and `helm diff` (plugin) to see what will change.
3. **If resources were applied but are unhealthy**: debug Pods, events and hooks like any Kubernetes failure (image, probes, config).
4. **If the release is stuck in `pending-upgrade`/`pending-install`/`pending-rollback`** (pipeline cancelled, runner killed, timeout), the next upgrade fails with "another operation (install/upgrade/rollback) is in progress". Roll back to the last `deployed` revision; for a stuck first install, uninstall and reinstall. Deleting the pending release Secret is a last resort.
5. **Use safety flags in CI**: `--wait` and `--timeout` so Helm waits for readiness; `--atomic` in Helm 3 or `--rollback-on-failure` in Helm 4 so a failed upgrade rolls back automatically.
6. **Roll back**: `helm rollback <release> <revision> --wait`. Rollback creates a *new* revision with the old manifest.

**Decision flow:**

```text
helm upgrade failed
      |
      v
Error before apply (template, schema, API version)? --yes--> fix chart/values; nothing changed
      |no
      v
Status pending-*? --yes--> helm rollback to last deployed revision (or uninstall if first install)
      |no
      v
Status failed after --wait timeout? --> debug Pods/hooks --> helm rollback <rev> --wait
      |
      v
Fix chart, re-run upgrade with --wait --timeout and automatic rollback flag
```

**Commands:**

```bash
helm status api -n prod
helm history api -n prod --max 10
helm get values api -n prod --revision 7
helm get manifest api -n prod --revision 7 | head -50

helm template api ./chart -f values-prod.yaml | kubectl apply --dry-run=server -f -
helm diff upgrade api ./chart -n prod -f values-prod.yaml      # helm-diff plugin

# Helm 3
helm upgrade --install api ./chart -n prod -f values-prod.yaml --atomic --wait --timeout 10m
# Helm 4 (--atomic renamed)
helm upgrade --install api ./chart -n prod -f values-prod.yaml --rollback-on-failure --wait --timeout 10m

helm rollback api 7 -n prod --wait --timeout 10m
kubectl get secrets -n prod -l owner=helm,name=api
```

**Important points:**

- Without `--wait`, Helm marks the release `deployed` as soon as the manifests are accepted, even if Pods never become ready.
- `--atomic`/`--rollback-on-failure` implies waiting; set a realistic `--timeout` (default 5 minutes) for slow starters and hooks.
- Rollback does not undo database migrations run by hooks, or delete CRDs; plan those separately.
- Always pin chart versions and keep values in Git so any revision can be reproduced.

See also: [Helm security, CI/CD and troubleshooting](../helm/04-security-cicd-and-troubleshooting.md), [Helm release workflow, values and hooks](../helm/02-release-workflow-values-and-hooks.md)

**Interview-ready answer:**

> "I start with `helm status` and `helm history` to see the current state and the last revision that was actually deployed. If the error happened at template or validation time, nothing changed and I fix the chart. If the release is stuck in `pending-upgrade` because a pipeline was cancelled, Helm blocks further operations, so I roll back to the last deployed revision, or uninstall if it was a first install. If resources were applied but unhealthy, I debug the Pods and hooks, then `helm rollback` with `--wait`. In CI I always use `--wait` with a realistic `--timeout`, plus `--atomic` in Helm 3, which Helm 4 renames to `--rollback-on-failure`, so a failed upgrade rolls itself back. I also run `helm diff` before production upgrades."

</details>
