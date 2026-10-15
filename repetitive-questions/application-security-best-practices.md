# Repetitive Interview Questions

## How do you implement strong security for your applications?

**Interviewer:** What security best practices do you follow to protect an application?

**Candidate:**

I protect an application at multiple levels. I secure the code, identity, secrets, network, container image, Kubernetes configuration, data, and CI/CD pipeline. One control alone is not enough.

```text
User
-> Web Application Firewall
-> Application Gateway
-> AKS Service
-> Pod
-> Database or Storage
```

### Identity and access

I follow least privilege: users and applications receive only the permissions they need.

- Use Microsoft Entra ID for user and administrator access.
- Use managed identity or workload identity for applications.
- Use Kubernetes RBAC for cluster access.
- Require multi-factor authentication for important accounts.
- Review and remove unused access.

Example: an application that only reads one Key Vault secret receives permission to read that secret. It does not receive owner access to the subscription.

### Secrets

I store passwords, API keys, and certificates in Azure Key Vault. I do not store them in:

- Source code.
- Dockerfiles.
- Git repositories.
- Pipeline YAML.
- Plain Kubernetes manifests.

The application accesses Key Vault using its identity, so it does not need a saved password.

```bash
az keyvault secret show \
  --vault-name <vault-name> \
  --name <secret-name>
```

I avoid displaying secret values during normal troubleshooting and ensure that pipeline logs mask them.

### Network protection

I allow only required traffic.

- Use HTTPS for external and internal sensitive traffic.
- Place Application Gateway and WAF in front of public applications.
- Use private endpoints for Key Vault, databases, and storage when required.
- Use firewall and Network Security Group rules.
- Use Kubernetes NetworkPolicies to restrict Pod-to-Pod access.

Example NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-database
spec:
  podSelector:
    matchLabels:
      app: database
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api
```

This policy selects the database Pods and allows incoming traffic only from Pods labelled `app: api` in the same namespace.

### Secure coding

Developers should:

- Validate user input.
- Use parameterized database queries.
- Apply authentication and authorization on the server.
- Avoid returning sensitive details in error messages.
- Keep dependencies updated.
- Set safe timeouts and request-size limits.

For example, parameterized queries help prevent SQL injection:

```text
SELECT * FROM users WHERE email = ?
```

The user input is treated as data, not as part of the SQL command.

### CI/CD security checks

My pipeline runs security checks before deployment:

```text
code
-> unit tests
-> code scan
-> dependency scan
-> secret scan
-> container-image scan
-> deployment
```

If a serious issue is found, the pipeline fails and the image is not promoted.

I also:

- Protect the `main` branch.
- Require pull-request review.
- Use protected Production environments.
- Keep CI/CD permissions limited.
- Use approved and pinned pipeline actions or plugins.

### Container security

I keep container images small and secure:

- Use a trusted base image.
- Use a specific image version.
- Run as a non-root user.
- Remove unnecessary tools.
- Scan the image before deployment.
- Rebuild when the base image receives a security fix.

Example:

```dockerfile
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --chown=101:101 ./dist /usr/share/nginx/html
USER 101
```

### Kubernetes security

I set a secure container configuration:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

I also use:

- Resource requests and limits.
- Separate namespaces.
- RBAC with minimum permissions.
- NetworkPolicies.
- Admission policies.
- Regular AKS and node upgrades.

I do not run a privileged container unless there is a proven requirement.

### Data protection

I protect data both when stored and while travelling:

- Encryption at rest.
- TLS in transit.
- Database access through application identity.
- Backups and restore testing.
- Limited administrator access.
- Audit logging.

Sensitive data should not appear in application or pipeline logs.

### Monitoring and alerts

I monitor:

- Failed logins.
- Unexpected permission changes.
- WAF blocks.
- Container and dependency vulnerabilities.
- Unusual network traffic.
- Key Vault access failures.
- Kubernetes audit and security events.

An alert must have an owner and a clear response step.

### Patch management

I regularly update:

- Application dependencies.
- Container base images.
- AKS versions.
- Worker-node images.
- Operating systems and build tools.

Updates are tested in a lower environment before Production.

### If a secret is exposed

I do not only delete it from Git because it may still exist in history. I:

1. Revoke or rotate the secret immediately.
2. Check where it was used.
3. Review access logs.
4. Update the application safely.
5. Remove the exposed value from history where required.
6. Add a secret scan to prevent recurrence.

### Common mistakes I avoid

- Hardcoding secrets.
- Giving owner or administrator access unnecessarily.
- Running containers as root.
- Using the `latest` image tag.
- Opening firewall access to everyone.
- Ignoring failed security scans.
- Logging passwords, tokens, or personal data.
- Assuming a successful deployment is automatically secure.

### Example

Suppose an AKS application needs to read a database password. I store the password in Key Vault, assign the application's workload identity permission to read it, restrict network access to the vault, and monitor secret-access failures.

The password is not stored in Git, the image, or the pipeline.

### In short

I use layered security: least-privilege identity, Key Vault for secrets, restricted networks, secure coding, CI/CD scans, non-root containers, Kubernetes policies, encryption, patching, and monitoring.

I test these controls regularly and respond quickly when a vulnerability or secret leak is detected.

## Find the security problems in this pipeline snippet

**Interviewer:** What is wrong with this?

```yaml
env:
  - name: DB_PASSWORD
    value: "MyProductionPassword123"

variables:
  azureSubscription: "prod-subscription"
```

**Candidate:**

The main problem is a Production password in plain text in source control.

| Problem | Risk | Fix |
| --- | --- | --- |
| Hardcoded password | Anyone with repo access can read it | Key Vault |
| It is in Git | Stays in history even after deleting the line | Rotate it, then clean history |
| Not a secret variable | Not masked in logs | Key Vault or secret variable |
| Plain env var | Visible in `kubectl describe`, dumps, debug output | Mounted file from Key Vault CSI |
| No rotation | Hardcoded values never change | Key Vault with rotation |
| Service connection may be over-privileged | Pipeline compromise becomes an Azure compromise | Least-privilege RBAC, workload identity federation, approvals |

Fixed version:

```yaml
- task: AzureKeyVault@2
  inputs:
    azureSubscription: prod-service-connection
    KeyVaultName: kv-project-production
    SecretsFilter: 'DB-PASSWORD'
```

Remember: `azureSubscription: prod-subscription` is not a secret. It is just the name of the service connection. The real question is what permissions the identity behind it has.

## How do you scan container images with Trivy?

**Interviewer:** Explain in detail how you use Trivy.

**Candidate:**

Trivy scans the built image for known CVEs in OS packages (Debian, Alpine) and application libraries (Maven, npm, pip). It can also find secrets and misconfigurations. I run it after `docker build` and before the push to ACR, so a failed image never reaches the registry.

```text
docker build -> trivy image -> pass -> push to ACR -> deploy to AKS
                            -> fail -> pipeline stops
```

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --exit-code 1 \
  orders-api:$(Build.BuildId)
```

| Flag | Purpose |
| --- | --- |
| `--severity HIGH,CRITICAL` | Only report what our policy blocks |
| `--exit-code 1` | Fail the pipeline when findings exist. Without it, Trivy prints the table and exits 0. |
| `--ignore-unfixed` | Skip CVEs that have no fixed version yet (track them separately) |
| `--format sarif` or `json --output report.json` | Report for the security dashboard |
| `--scanners vuln,secret,misconfig` | Choose what to scan |

Other Trivy commands:

```bash
trivy fs .                    # dependencies and secrets in the repo
trivy config ./terraform      # IaC misconfigurations (tfsec is now part of Trivy)
trivy image myacr.azurecr.io/orders-api:1.4.0   # rescan an image already in ACR
```

When a HIGH or CRITICAL is found:

1. Upgrade the base image or the dependency, rebuild, rescan.
2. If there is no fix, check if the package is actually used, and raise an exception.
3. An exception goes in `.trivyignore` with a reason, owner, approval, and expiry date. An undocumented ignore list is a bad practice.

Remember:

- Trivy and SonarQube do different jobs. SonarQube checks our source code. Trivy checks the image and its dependencies.
- New CVEs are published after the build, so I also rescan images in the registry (scheduled Trivy job or Defender for Containers on ACR).
- Pin the Trivy version (or image digest) in the pipeline. Security tools are part of the supply chain too.

## What commercial tools can replace SonarQube and Trivy?

**Interviewer:** Instead of SonarQube and Trivy, what non-open-source tools can you use?

**Candidate:**

I group them by the type of check:

| Check | Open-source tool I use | Commercial alternatives |
| --- | --- | --- |
| SAST (our code) | SonarQube Community | Checkmarx One, Veracode, Coverity, GitHub Advanced Security (CodeQL) |
| SCA (dependencies) | OWASP Dependency-Check | Snyk Open Source, Mend.io, Black Duck SCA, JFrog Xray |
| Container image | Trivy | Snyk Container, Prisma Cloud, Aqua, JFrog Xray, Defender for Containers |
| IaC | Checkov, Trivy | Prisma Cloud, Snyk IaC, Checkmarx One |
| Secrets | Gitleaks | GitHub Advanced Security secret scanning |
| DAST (running app) | OWASP ZAP | Veracode DAST, Burp Suite Enterprise |

In Azure DevOps, the easiest commercial option is GitHub Advanced Security for Azure DevOps (now offered as two products, Secret Protection and Code Security):

```yaml
- task: AdvancedSecurity-Codeql-Init@1
  inputs:
    languages: java
- task: AdvancedSecurity-Codeql-Autobuild@1
- task: AdvancedSecurity-Dependency-Scanning@1
- task: AdvancedSecurity-Codeql-Analyze@1
```

Remember:

- These are not one-to-one replacements. SonarQube is mainly code quality. Checkmarx and Veracode focus on security, so many teams keep SonarQube and add a security tool.
- The gate policy matters more than the tool: for example, fail on Critical and High, allow Medium with a ticket.
- Store tool tokens in a service connection or Key Vault.
- I say clearly which tools I used hands-on (SonarQube, Trivy, Checkov) and which I only know.

## Apart from pre-commit hooks, what other checks do you use?

**Interviewer:** What other hooks and checks exist, inside and outside Git?

**Candidate:**

Pre-commit is only the first layer. Local hooks can be skipped with `--no-verify`, so every important check also runs in CI and is enforced again at the cluster and Azure level.

| Layer | Examples | Purpose |
| --- | --- | --- |
| Local Git hooks | `pre-commit`, `commit-msg`, `pre-push` | Format, lint, secret scan, commit message rules, quick tests |
| Server-side Git | `pre-receive`, `update`, `post-receive`; branch policies, push protection | Block bad pushes, require PR review and build validation |
| CI pipeline | SonarQube, OWASP Dependency-Check, Trivy, Checkov, TFLint, Hadolint, ShellCheck, kubeconform | Code, dependency, image, IaC, and manifest checks with a gate |
| Kubernetes admission | Pod Security Admission, Kyverno, OPA Gatekeeper (Azure Policy for AKS) | Deny privileged Pods, missing limits, unapproved registries |
| Azure governance | Azure Policy | Deny public Storage Accounts, unapproved regions, missing tags |

Example `.pre-commit-config.yaml` (pin each `rev` to a current release):

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: check-merge-conflict
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.96.1
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
```

Remember: say where each control lives. SonarQube is a CI quality gate, Kyverno works at cluster admission, and Azure Policy works on Azure resources. None of them are Git hooks.

## What is Azure Policy?

**Interviewer:** What is Azure Policy, and how is it different from RBAC?

**Candidate:**

Azure Policy is a governance service. It checks resource configuration and can audit, deny, or fix it.

- **RBAC:** who can do what.
- **Azure Policy:** what configuration is allowed, whoever does it.

```text
Developer has Contributor
-> creates a Storage Account with public network access
-> Azure Policy: Deny
```

| Effect | What it does |
| --- | --- |
| Audit / AuditIfNotExists | Allows it, marks it non-compliant |
| Deny | Blocks create or update |
| Modify | Adds or changes properties, for example tags |
| DeployIfNotExists | Deploys a missing setting, for example diagnostic settings |
| Disabled | Not evaluated |

Common policies I use: deny public Storage Accounts, allowed regions, required tags, HTTPS only, allowed VM SKUs, and the AKS policy initiative (no privileged containers, only images from our ACR).

```bash
az policy assignment create \
  --name deny-public-storage \
  --policy <policy-definition-id> \
  --scope /subscriptions/<subscription-id>/resourceGroups/rg-prod
```

Remember:

- Start with Audit, review the results, then switch to Deny, so existing deployments do not break.
- Group policies into an initiative and assign it at management group level.
- Modify and DeployIfNotExists need a managed identity and a remediation task for existing resources.

## A Storage Account has become public. How do you fix it?

**Interviewer:** You find a public Storage Account in Azure. What do you do?

**Candidate:**

"Public" can mean two different settings, so I check both.

| Setting | Safe value |
| --- | --- |
| Public network access | Disabled (private endpoint) or selected networks only |
| Anonymous blob access | Disabled at account level, containers set to `Private` |

```bash
az storage account update \
  -g rg-prod -n stappprod \
  --public-network-access Disabled \
  --allow-blob-public-access false \
  --allow-shared-key-access false
```

```text
Identify what is exposed
-> disable anonymous access and public network access
-> private endpoint + private DNS for the apps that need it
-> review RBAC and SAS tokens / access keys (rotate keys if data may have leaked)
-> check Activity Log: who changed it and when
-> check storage logs: was data actually read anonymously?
-> prevent: Azure Policy Deny + fix the Terraform code
```

Terraform:

```hcl
public_network_access_enabled   = false
allow_nested_items_to_be_public = false
shared_access_key_enabled       = false
```

Disabling shared key access breaks apps that still use access keys or account SAS, so I move them to Entra ID (managed identity) first.

Remember: if the fix is only done in the portal, the next `terraform apply` from old code can open it again. The code must be fixed too.

## How do you restrict a developer instead of giving Contributor?

**Interviewer:** A developer asks for Contributor. What do you give instead?

**Candidate:**

I find out what the developer actually needs, then give the smallest role at the smallest scope.

```text
Not this:  Developer -> Contributor -> whole subscription
This:      Entra group -> specific role -> one resource group or resource
```

| Need | Built-in role |
| --- | --- |
| View only | Reader |
| Manage web apps | Website Contributor |
| Work with AKS | Azure Kubernetes Service RBAC Writer (namespace scope) |
| Read blob data | Storage Blob Data Reader |
| Read Key Vault secrets | Key Vault Secrets User |

If no built-in role fits, I create a custom role:

```json
{
  "Name": "WebApp Operator",
  "IsCustom": true,
  "Actions": [
    "Microsoft.Web/sites/read",
    "Microsoft.Web/sites/restart/action"
  ],
  "AssignableScopes": ["/subscriptions/<sub-id>/resourceGroups/rg-dev"]
}
```

```bash
az role definition create --role-definition @webapp-operator.json
```

Remember:

- Assign roles to Entra groups, not to individual users.
- For Production, use Privileged Identity Management (PIM): the developer is eligible, requests access, gets approval, and the role expires automatically.
- I created such custom roles with Bicep, so role assignments are reviewed in PRs like any other code.

## How do you remediate access to a Windows server in Azure?

**Interviewer:** A Windows VM has too much or unauthorized access. How do you fix it?

**Candidate:**

I check every path into the VM: Azure RBAC, Entra login roles, local Windows accounts, and RDP.

```bash
az role assignment list --scope <vm-resource-id> --include-inherited -o table
```

1. **RBAC:** remove broad roles. Virtual Machine Contributor can use Run Command, which means admin inside the OS, so treat it as privileged. Use PIM for admin access.
2. **RDP:** never open 3389 to the internet. Use Azure Bastion (no public IP needed) and Just-in-time VM access in Defender for Cloud.
3. **Local accounts:** review and clean up.

```powershell
Get-LocalGroupMember Administrators
Remove-LocalGroupMember -Group "Administrators" -Member "<user>"
Disable-LocalUser -Name "<user>"
```

4. **Credentials:** reset the local admin password (`az vm user update`) or manage it with Windows LAPS, and rotate service account passwords.
5. **Logs:** Activity Log (RBAC, NSG, Run Command changes), Entra sign-in logs, and Windows Security events 4624 (logon, type 10 = RDP), 4625 (failed logon), 4720 and 4732 (account created, added to a group).

Remember: first find out whether the access was misused, then lock it down, then prevent it with Policy and NSG rules in code.

## Local accounts in AKS

**Interviewer:** What are local accounts in Kubernetes and AKS?

**Candidate:**

A local account is a user the cluster trusts directly, usually through a client certificate in a kubeconfig, not through an identity provider. In AKS, local accounts give a static cluster-admin kubeconfig (`az aks get-credentials --admin`). It cannot be tied to one person, has no MFA, and is hard to audit.

I disable local accounts and use Microsoft Entra ID with Kubernetes RBAC or Azure RBAC for Kubernetes:

```bash
az aks update -g my-rg -n my-aks \
  --enable-aad \
  --enable-azure-rbac \
  --disable-local-accounts
```

Then a developer gets namespace access through an Entra group:

```yaml
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: dev-team-view
  namespace: dev
subjects:
  - kind: Group
    name: "<entra-group-object-id>"
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: view
  apiGroup: rbac.authorization.k8s.io
```

Remember:

- `--disable-local-accounts` needs Entra ID integration enabled first. After it, `--admin` credentials stop working.
- Users sign in through `kubelogin`. Pipelines use a service connection or workload identity.
- Keep an emergency (break-glass) Entra group for cluster admin.

## How do you restrict users before requests reach the application?

**Interviewer:** How do you block unwanted users before they reach the app?

**Candidate:**

I combine network restriction and identity restriction.

```text
User
-> Front Door or Application Gateway + WAF  (OWASP rules, bots, rate limit, IP/geo rules)
-> App Service access restrictions or private endpoint (only the gateway can reach it)
-> App Service Authentication with Entra ID (not signed in -> redirect, not assigned -> denied)
-> application checks app roles
```

- **WAF:** blocks SQL injection, XSS, bad bots, and floods. It does not know who the user is.
- **Lock the backend:** allow only the Application Gateway subnet, or the `AzureFrontDoor.Backend` service tag plus the `X-Azure-FDID` header check. Otherwise users can bypass the WAF using `*.azurewebsites.net`.
- **Easy Auth:** App Service Authentication with Microsoft Entra ID, "Require authentication". Unauthenticated requests never reach the code.
- **Only one group:** in the Enterprise application, set "Assignment required = Yes" and assign only the allowed group.
- **Conditional Access:** require MFA or a compliant device, block risky locations.

Remember: WAF protects against bad traffic, Entra ID decides who is allowed. One does not replace the other.

## How do you move an application from HTTP to HTTPS?

**Interviewer:** The frontend and backend both use HTTP. How do you change them to HTTPS?

**Candidate:**

```text
User -> HTTPS 443 -> Application Gateway (TLS cert from Key Vault, HTTP 80 redirects to 443)
     -> HTTPS -> frontend -> HTTPS -> backend API -> TLS -> database
```

1. Get a certificate from a trusted CA (name in CN/SAN must match), store it in Key Vault.
2. Add an HTTPS listener on Application Gateway that references the Key Vault certificate. Add an HTTP to HTTPS redirect rule.
3. Set an SSL policy with TLS 1.2 minimum.
4. For end-to-end TLS, set the backend settings to HTTPS and make the host name match the backend certificate.
5. Change frontend API URLs to `https://` to avoid mixed-content errors. Mark cookies `Secure` and add the HSTS header.
6. Update NSGs to allow 443, and update Entra redirect URIs to `https://`.
7. Test in Dev and QA, then Production.

For App Service: turn on "HTTPS Only" and set minimum TLS 1.2. For AKS ingress: cert-manager issues and renews the certificate, and the ingress redirects HTTP to HTTPS.

Remember: Azure Load Balancer is Layer 4 and cannot terminate TLS. Use Application Gateway, Front Door, or the ingress controller. TLS termination at the gateway alone is not end-to-end encryption.

## How do you make sure an expiring certificate does not break the application?

**Interviewer:** If a certificate expires, how do you avoid impact?

**Candidate:**

The certificate should never reach its expiry date. I follow: monitor -> renew -> deploy -> validate.

- **Monitor:** keep an inventory, alert at 30, 15, and 7 days. Key Vault sends `CertificateNearExpiry` events to Event Grid, which I route to email, Teams, or a ticket.
- **Auto-renew:** Key Vault lifetime action renews certificates from integrated CAs (DigiCert, GlobalSign) automatically. App Service managed certificates and cert-manager on AKS also renew themselves.
- **Deploy:** Application Gateway referencing a versionless Key Vault secret picks up the renewed certificate automatically (it polls every 4 hours). A pinned version or a manually uploaded certificate must be updated.
- **Validate:**

```bash
openssl s_client -connect app.company.com:443 -servername app.company.com </dev/null \
  | openssl x509 -noout -dates -subject
```

If it has already expired: renew, import, update the binding, validate, then do an RCA on why the alert was missed.

Remember:

- Renewing in Key Vault does not mean every service uses the new certificate. I check each binding.
- Public TLS certificate lifetimes are shrinking (200 days from March 2026, going down to 47 days by 2029), so manual renewal does not scale. Automation is required.

## How are containers isolated? (namespaces and cgroups)

**Interviewer:** How do you isolate a container? What are namespaces and cgroups?

**Candidate:**

A container is a normal Linux process with isolation from the kernel. It does not have its own OS kernel.

- **Namespaces = what the process can see.**
- **cgroups = how much it can use.**

| Namespace | Isolates |
| --- | --- |
| PID | Process tree (each container has its own PID 1) |
| NET | IP address, routes, ports |
| MNT | Filesystem mounts |
| UTS | Hostname |
| IPC | Shared memory |
| USER | Maps root in the container to a normal user on the host |

cgroups limit CPU, memory, disk I/O, and number of processes:

```bash
docker run --memory=512m --cpus=1 nginx
```

In Kubernetes, `resources.limits` become cgroup limits. Over the memory limit -> `OOMKilled`. Over the CPU limit -> throttled.

Extra hardening on top:

- Drop Linux capabilities, `runAsNonRoot`, `allowPrivilegeEscalation: false`, read-only root filesystem.
- Seccomp `RuntimeDefault` and AppArmor or SELinux to limit system calls and file access.
- Pod Security Admission (Restricted), NetworkPolicies, RBAC.
- For untrusted workloads, stronger isolation with a separate kernel: AKS Pod Sandboxing (Kata Containers).

Remember: all containers on a node share one kernel. A privileged container or a kernel bug can break isolation, so I never run privileged containers without a strong reason.
