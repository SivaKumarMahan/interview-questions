## 1. How do you design least-privilege (minimum required access) IAM for CI/CD agents?

**Answer:** Assign one service account per pipeline with minimum roles, rotate keys, use workload identity (GCP/Azure managed identities), and avoid shared accounts. Mini-case: Each Jenkins job used a dedicated service account scoped only to its resource group — preventing privilege escalation.
**Detailed interview approach:**
I identify the exact principal, resource, action, scope, and denied condition from the error and cloud audit logs. I inspect effective IAM/RBAC including inherited roles, deny policies, conditional bindings, tenant/project/subscription, and token audience/expiry.

I reproduce a harmless call with the same identity, then grant the narrow predefined/custom role at the smallest scope—never owner/admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys.

For a leaked key I disable/revoke it immediately, review its use and resources changed, rotate related secrets, and rebuild the workload identity path. Access reviews, expiry, policy tests, and audit alerts prevent role sprawl.

## 2. How do you implement fine-grained service-to-service authentication in microservices?

**Answer:** Use mTLS with service mesh (Istio/Linkerd) or SPIFFE/SPIRE for issuing short-lived identities; enforce policy and RBAC at sidecar/proxy layer.

Mini-case: Introducing SPIRE for workloads provided automatic short-lived certificates; even if a pod was compromised, its certs expired quickly and lateral movement was limited.
**Detailed interview approach:**
I introduce a service mesh for a concrete need such as workload identity, mTLS, traffic policy, or monitoring data—not merely to add proxies. I inventory protocols and ports, install and monitor the control plane, onboard a non-critical namespace, and confirm sidecar/ambient resource overhead.

Identities come from service accounts and short-lived certificates; mTLS moves from permissive to strict only after observing all callers. AuthorizationPolicy allows exact service-to-service paths and default-denies others.

I test certificate rotation, retries/timeouts, failure of the control plane, and proxy bypass paths, then roll out gradually. Dashboards and tracing verify latency/errors, while version-skew and upgrade procedures keep the mesh supportable.

## 3. How do you secure CI/CD runner/agent environments?

**Answer:** Use ephemeral agents (containerized) that run jobs then destroy; limit agent permissions, sandbox builds, run static & dynamic scans before publishing artifacts, and isolate sensitive pipelines into dedicated, locked-down agents.

Mini-case: Switching to Kubernetes-based ephemeral agents eliminated persistent credential theft vectors — each job had only the minimal IAM role for its runtime.
**Detailed interview approach:**
I use SSO/MFA, role-based authorization, CSRF protection, TLS, a private controller, patched core/plugins, and no builds on the controller.

Credentials live in Jenkins Credentials or an external vault and are scoped to the smallest folder/job; pipelines use `withCredentials`, avoid shell tracing, and never interpolate secrets into command lines or artifacts.

Agents are ephemeral, isolated, non-root where possible, and receive short-lived cloud identity. If a secret appears in logs, masking is not enough: I stop exposure, revoke/rotate it, restrict/delete retained logs where policy permits, audit use, and fix the step that printed it.

Configuration, plugins, and restore are backed up and tested.

## 4. How do you rotate API keys securely in CI/CD?

**Answer:** Store in Secret Manager/Key Vault → Rotate via automation → Update pipeline secrets → Invalidate old keys.

**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

## 5. How do you ensure CI/CD pipelines are auditable for compliance?

**Answer:** Store pipeline definitions in Git → Enable logging for all jobs → Require approvals for prod → Retain build artifacts & logs.

**Detailed interview approach:**
Pipeline definitions, infrastructure, policies, and approvals are versioned and protected in Git.

Every run records actor, commit, immutable (not changed after creation) artifact digest, test/security results, plan, approver, target, timestamps, deployment result, and rollback; cloud, cluster, registry, and secret-manager audit logs provide independent evidence.

Identities are named or workload-based rather than shared, with separation of duties and least privilege (only the permissions needed). Logs/artifacts use access control, integrity protection, retention, legal/compliance policy, and time synchronization, while secrets are redacted.

I periodically sample a release and prove end-to-end traceability from requirement/change ticket to production and back, then fix missing evidence before an external audit finds it.

## 6. How do you handle secret rotation in cloud (GCP/Azure)?

**Answer:** Use GCP Secret Manager / Azure Key Vault → Enable automatic key rotation → Update CI/CD pipelines to fetch secrets dynamically instead of hardcoding.

**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

## 7. How do you ensure compliance & governance in DevOps pipelines?

**Answer:** • Enforce policy as code with tools like OPA/Conftest.
• Restrict Terraform modules for compliance.
• Enable audit logging in GCP/Azure.
• Add mandatory approval gates in Jenkins/Azure DevOps.

**Detailed interview approach:**
I translate requirements into versioned, testable controls at several layers: source/branch rules, CI scanners, Terraform plan policy, Kubernetes admission policy, and cloud-native organization policy.

Examples require encryption, approved regions/images, non-root Pods, resource limits, labels/tags, private exposure, and least-privilege (minimum required access) identity.

Rules have unit tests with allowed and denied fixtures and produce an actionable reason and fix. Hard violations block, while approved exceptions are scoped, owned, and expire automatically.

Runtime/audit monitoring catches changes outside CI. I measure exceptions, false positives, and time to remediate, and periodically map evidence to the control so compliance represents actual risk reduction.

## 8. How do you ensure auditability in DevOps?

**Answer:** • Store IaC in Git for versioning.
• Enable Cloud Audit Logs (GCP/Azure).
• Use Jenkins pipeline logs.
• Implement approval stages for production.

**Detailed interview approach:**
Pipeline definitions, infrastructure, policies, and approvals are versioned and protected in Git.

Every run records actor, commit, immutable (not changed after creation) artifact digest, test/security results, plan, approver, target, timestamps, deployment result, and rollback; cloud, cluster, registry, and secret-manager audit logs provide independent evidence.

Identities are named or workload-based rather than shared, with separation of duties and least privilege (only the permissions needed). Logs/artifacts use access control, integrity protection, retention, legal/compliance policy, and time synchronization, while secrets are redacted.

I periodically sample a release and prove end-to-end traceability from requirement/change ticket to production and back, then fix missing evidence before an external audit finds it.

## 9. How do you ensure security in DevOps pipelines?

**Answer:**
Scan code with SonarQube
Scan images with Trivy/Anchore
Use IAM least privilege (only the permissions needed) in GCP/Azure
Store secrets in Secret Manager/Key Vault
Enable audit logging

**Detailed interview approach:**
Terraform code is protected by branch rules, code owners, signed/identified commits where required, and reviews from platform/security owners. CI pins Terraform, providers, modules, and third-party actions; runs format, validate, lint, secret, IaC security, and policy checks; and produces an access-controlled plan.

Backend and cloud credentials are never stored in Git—jobs use short-lived workload identity. Module sources and checksums are trusted, dependency updates are reviewed, and production apply is restricted to protected environments.

If a secret is committed I revoke/rotate it immediately and audit use; history cleanup alone is not fix. Audit logs link commit, plan, approval, identity, and apply.

## 10. How do you secure secrets in pipelines?

**Answer:** Use Jenkins credentials manager, Vault, or cloud secret managers (GCP Secret Manager, Azure Key Vault) instead of storing secrets in code.

**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

## 11. How do you ensure security throughout the container lifecycle from build to runtime?

**Answer:** Pre-commit Dockerfile scans → Trivy in CI with critical-CVE rejection → ECR image scanning → runtime NetworkPolicies + OPA Gatekeeper + Falco → read-only rootfs/non-root via Pod Security Standards → Cosign signing verified at admission.

**Detailed interview approach:**
The container security approach covers the entire lifecycle. During development, developers use pre-commit hooks that scan Dockerfiles for best practices.

In CI, I use Trivy for vulnerability scanning before pushing images to ECR, with automated rejection of images containing critical vulnerabilities.

For runtime security, I implement Kubernetes network policies for pod-to-pod communication and use OPA Gatekeeper as an admission controller to enforce policies such as preventing privileged containers. AWS ECR image scanning provides automated notifications for newly discovered vulnerabilities in deployed images.

Container runtime security is handled by Falco, which monitors for suspicious activities and integrates with the alerting system.

All containers run with read-only root filesystems and non-root users, enforced through Kubernetes Pod Security Standards, and images are signed using Cosign and verified before deployment through admission control.

## 12. How do you manage secrets and environment-specific configurations securely?

**Answer:** HashiCorp Vault for app secrets + AWS Secrets Manager for infra secrets → GitHub Actions OIDC for temporary AWS creds → Vault Kubernetes injection with dynamic rotating DB credentials → Kustomize overlays per env + Vault policies for isolation.
**Detailed interview approach:**
I use a dual approach with HashiCorp Vault for application secrets and AWS Secrets Manager for infrastructure secrets. Vault is deployed in each EKS cluster with authentication tied to Kubernetes service accounts, and sensitive Terraform variables are stored in AWS Secrets Manager and accessed via the AWS provider.
GitHub Actions uses OIDC authentication to obtain temporary AWS credentials, avoiding stored secrets. For application secrets, the Vault Kubernetes integration injects secrets at runtime, and Vault's dynamic secrets capability automatically rotates database credentials.

Environment-specific configurations are managed in ArgoCD with Kustomize overlays for each environment, while Vault policies enforce environment isolation for secrets access.
