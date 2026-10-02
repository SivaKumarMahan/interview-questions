# Kubernetes: Security, RBAC, and Secrets

> Cluster hardening, security contexts, RBAC and ServiceAccounts, secrets and certificates, image trust, multi-tenancy, and compliance.

## Key Concepts

### Security

Use layered controls:

- Strong identity integration and least-privilege RBAC
- Namespaces, quotas, and tenancy boundaries
- Pod Security Admission
- Non-root containers and restrictive security contexts
- Read-only root filesystems
- Dropped Linux capabilities and seccomp profiles
- Trusted, signed, and scanned images
- NetworkPolicies
- External secret stores and workload identity
- API audit logs and runtime monitoring
- Regular cluster and node-image upgrades

A security context can define `runAsUser`, `runAsGroup`, `fsGroup`, `allowPrivilegeEscalation`, capabilities, SELinux options, seccomp, privileged mode, and read-only filesystem settings.

Deleting a ServiceAccount does not necessarily terminate existing Pods immediately. Bound tokens are short-lived and refreshed; access will eventually fail when refresh or authorization no longer succeeds.

New Pods referencing a missing ServiceAccount cannot be admitted.

### Operations Notes

- Secure a cluster with RBAC, short-lived ServiceAccount or workload identity, NetworkPolicies, Pod Security admission, signed and scanned images, a proper secret-management integration, audit logs, regular patching, and restricted administrative access. `imagePullSecrets` are a fallback for private registries — prefer cloud workload identity where it's available.

### Security and Compliance

- Use identity-based least privilege, separate service accounts, Pod Security Admission, non-root/read-only containers, seccomp, approved signed images, default-deny network controls, encrypted secrets, and audit/runtime monitoring.
- A leaked secret must be revoked and rotated immediately; removing it from a log or Git file is not fix. Investigate access, update consumers through an overlap period, verify the new value, and then revoke the old value.
- Certificate incidents require identifying the exact endpoint and owner, checking expiry, SAN, SNI, issuer, chain, and consumer reload. Automate renewal and alert well before expiry.
- Multi-tenant and multi-cluster designs need explicit isolation boundaries, quotas, policy enforcement, centralized identity and audit, and separate clusters where the risk boundary requires it.

## Interview Questions

### 1. How do you secure a Kubernetes cluster?

**Answer:**

I secure every layer:

- Identity, MFA, and RBAC with only the permissions people actually need.
- A private or restricted API endpoint with audit logging.
- Patched control-plane and worker-node versions.
- Pod Security Admission, non-root containers, no privilege escalation, dropped capabilities, seccomp, and read-only filesystems.
- Signed, scanned, digest-pinned images.
- NetworkPolicies and controlled outbound traffic.
- External secrets, workload identity, and encryption.
- Quotas, tenant separation, runtime detection, central logs, and backups.

Policies are versioned and tested, and any exception has an expiry date. Nodes use fixed, replaceable images where possible, and etcd data and backups stay protected. I continuously check RBAC, public exposure, deprecated versions, and certificate expiry, and I test what happens when a deployment gets denied and how the incident procedure holds up.

Security is about managing threat and risk, not a checklist. No single tool "secures Kubernetes" — what matters is verifying the controls actually work and that response and restore procedures hold up under a real test.

### 2. How do you secure Kubernetes cluster?

**Answer:**
• Use RBAC for access control.
• Enable Network Policies.
• Regularly patch cluster.
• Restrict container privileges (no root user).
• Use Secrets API for sensitive data.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 3. How do you enforce zero-trust security in a Kubernetes cluster?

**Answer:** Disable default network connectivity, apply strict NetworkPolicies, enforce PodSecurityAdmission, use mTLS with a service mesh, and verify identity per request.

Mini-case: We deployed Istio with strict mTLS and namespace isolation; even if an attacker gained pod access, they couldn’t reach other services without valid identity.
**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 4. Kubernetes security contexts — configuring permissions and access controls?

Kubernetes **Security Contexts** allow you to define security settings for Pods and Containers. They help configure permissions and access controls to enhance the security of your applications running in a Kubernetes cluster. Here are some key aspects:

**1. User and Group IDs:**

Specify the user ID (UID) and group ID (GID) that a container should run as using the `runAsUser` and `runAsGroup` fields.

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 3000
```

**2. Privileged containers:**

Set the `privileged` field to `true` to allow a container to run with elevated privileges.

```yaml
securityContext:
  privileged: true
```

**3. Read-only root filesystem:**

Enforce a read-only root filesystem for a container by setting the `readOnlyRootFilesystem` field to `true`.

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

**4. Capabilities:**

Add or drop Linux capabilities for a container using the `capabilities` field.

```yaml
securityContext:
  capabilities:
    add: ["NET_ADMIN"]
    drop: ["MKNOD"]
```

**5. Seccomp profiles:**

Specify a seccomp profile to restrict system calls that a container can make.

```yaml
securityContext:
  seccompProfile:
    type: Localhost
    localhostProfile: "profiles/seccomp.json"
```

**6. SELinux options:**

Set SELinux options for a container using the `seLinuxOptions` field.

```yaml
securityContext:
  seLinuxOptions:
    level: "s0:c123,c456"
```

**7. Pod-level security context:**

Define a security context at the Pod level that applies to all containers within the Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  securityContext:
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: mycontainer
    image: myimage
```

By configuring security contexts, you can enforce security policies and ensure that your applications run with the appropriate permissions and access controls in a Kubernetes environment.

### 5. I want to give only read-only permissions to check logs for users. How can you set up RBAC for this?

Use a `ClusterRole` scoped to reading pods and pod logs, then bind it to the user:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: log-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: log-reader-binding
subjects:
- kind: User
  name: log-user
roleRef:
  kind: ClusterRole
  name: log-reader
  apiGroup: rbac.authorization.k8s.io
```

### 6. How do you enforce least privilege (only the permissions needed) in Kubernetes?

**Answer:** Use RBAC roles → Bind only necessary permissions → Restrict cluster admin → Enable PodSecurityPolicies/OPA.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 7. If a ServiceAccount is deleted while Pods using it are still running, what happens to the mounted tokens and API access?

**Answer:**

Existing Pods continue to function with their mounted tokens, but with important limitations.

Immediate effects:

- **Running Pods:** Continue using cached/mounted tokens until Pod restart.
- **Token refresh:** May fail when tokens expire (typically 1 hour).
- **New Pods:** Cannot be created using the deleted ServiceAccount.

Token behavior:

- Mounted tokens remain valid until expiration.
- Kubernetes doesn't immediately revoke tokens from running Pods.
- Applications may experience authentication failures when tokens expire.

Recovery steps:

```bash
# Recreate the ServiceAccount
kubectl create serviceaccount myapp-sa

# Restart Pods to get new tokens
kubectl rollout restart deployment/myapp
```

### 8. How do you handle authentication for AKS clusters and store secrets securely in Kubernetes?

**Authentication for AKS clusters:**

1. **Azure Active Directory (AAD) Integration:** AKS can be integrated with Azure AD to manage user access to the cluster. This allows you to use Azure AD identities for authentication and role-based access control (RBAC) within the cluster.
2. **kubeconfig file:** When you create an AKS cluster, a kubeconfig file is generated that contains the necessary credentials to access the cluster. Use the `az aks get-credentials` command to download and configure your kubeconfig file.
3. **Service Principals and Managed Identities:** AKS can use Azure Service Principals or Managed Identities for authenticating applications running in the cluster to access Azure resources securely.

**Storing secrets securely in Kubernetes:**

1. **Kubernetes Secrets:** Kubernetes provides a built-in resource called Secrets to store sensitive information such as passwords, OAuth tokens, and SSH keys. Secrets are base64-encoded and can be created using YAML manifests or the `kubectl create secret` command.
2. **Encryption at Rest:** You can enable encryption at rest for Secrets in Kubernetes by configuring the encryption providers in the API server.
3. **External Secret Management Tools:** For enhanced security, you can use external secret management tools like HashiCorp Vault, Azure Key Vault, or AWS Secrets Manager. These tools can be integrated with Kubernetes to fetch secrets dynamically at runtime.
4. **RBAC Policies:** Implement Role-Based Access Control (RBAC) policies to restrict access to Secrets based on user roles and permissions.
5. **Avoid Hardcoding Secrets:** Never hardcode sensitive information in your application code or configuration files. Always use Secrets or external secret management solutions.

By following these practices, you can ensure secure authentication for your AKS clusters and safely manage sensitive information within your Kubernetes environment.

### 9. How do you manage secrets in Kubernetes?

**Answer:** Store in Kubernetes Secrets (base64 encoded) → Encrypt at rest → Integrate with Vault/Key Vault for rotation.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 10. How do you securely manage secrets and certificates in EKS?

**Answer:**

I use EKS Pod Identity or IRSA so a ServiceAccount gets short-lived AWS permissions instead of long-lived credentials. Secrets themselves live in Secrets Manager or Parameter Store, and get mounted or synced in using the Secrets Store CSI driver or External Secrets.

If a Kubernetes Secret does exist, I turn on envelope encryption with KMS and keep RBAC and audit narrow — remember, base64 is not encryption.

Certificates go through cert-manager with an approved issuer, such as a private CA or ACM integration, with renewal alerts and a tested reload path. I never put secrets in Helm values, Git, or environment logs.

When troubleshooting, I check the ServiceAccount's annotation and association, the OIDC trust relationship, the IAM policy, CSI or operator logs, the secret's version, KMS, network endpoints and DNS, and file permissions. A rotation test confirms the application picks up the new value without an outage and that the old credentials actually get revoked.

### 11. How do you manage secret rotation across CI/CD, Kubernetes, and apps?

**Answer:** Centralize secrets in Vault/Key Vault/Secret Manager, use dynamic short-lived credentials where possible, automate rotation with scripts/events, update pipeline/runtime fetch logic to fetch latest secrets at runtime, and test rotation in staging.

Mini-case: We used Azure Key Vault with rotation policy; CI fetched secrets at job runtime and apps used managed identities to request short-lived tokens, removing the need for static credentials.
**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store — never in Git, YAML, images, command arguments, or build artifacts. A job gets a short-lived identity and fetches only the secret it actually needs for that stage. Masking output is only a secondary control, since an encoded or transformed value can still leak.

Rotation uses an overlap period: issue the new value, update the consumers, verify it works, revoke the old value, and audit for failures. If a scan finds a secret committed to the repo, I revoke it immediately, check where it was used, remove it from active history where that's appropriate, and rotate any downstream credentials too — just deleting the line isn't enough.

Pre-commit and server-side scans, protected logs, least privilege, expiry, and rotation tests are what prevent this from happening again.

### 12. How do you handle Kubernetes secret exposure in logs?

**Answer:** Prevent kubectl describe from showing → Use kubectl get secret -o jsonpath securely → Audit RBAC → Enable encryption at rest.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 13. How do you handle certificate rotation in on-prem Kubernetes clusters?

**Answer:**

I start with an inventory: who owns each certificate, its issuer, purpose, expiry, trust chain, and consumers. For kubeadm clusters, I check `kubeadm certs check-expiration`, back up etcd and config, follow the version-specific documented renewal steps, update admin kubeconfigs and restart static Pods or components as needed, and then verify nodes, the API server, and controllers.

Kubelet's own certificate rotation is checked separately.

Application TLS goes through cert-manager with an internal ACME setup or CA, with alerts well before expiry. Rotation happens in stages: issue the new certificate with an overlap period so both are trusted, deploy or reload the consumers, verify the full TLS chain, SAN, and hostname from a real client, and only then revoke and remove the old one.

I test all of this in non-production first and document the recovery steps. Blindly replacing certificate files can break quorum or API access, so I plan for maintenance windows and console access ahead of time.

### 14. How do you handle Kubernetes certificate expiration?

**Answer:** Monitor cert expiry, automate renewals with cert-manager, rotate cluster certs regularly, and alert on failures. Mini-case: Cert-manager auto-renewed TLS certs before expiry; a Grafana alert ensured we never missed rotation deadlines.

**Detailed interview approach:**
First I identify which certificate actually expired — public ingress, an internal service, the API server, kubelet, a webhook, or a client — and check its issuer, SAN, chain, secret, and expiry with `openssl s_client` or `openssl x509`, plus the relevant controller's status.

For cert-manager, I check the Certificate, CertificateRequest, Order or Challenge objects, controller logs, DNS or HTTP challenge reachability, and the issuer's credentials.

I renew or rotate it through the supported controller, reload the consumer, and verify the complete chain and hostname from a real client. Cluster-level certificates follow the platform's specific rotation procedure and node or control-plane sequence.

Alerts at 30, 14, and 7 days out, automated renewal tests, an owner inventory, and protected issuer keys are what prevent an emergency expiry in the first place.

### 15. How do you enforce that all images come from a trusted internal registry?

**Answer:**

CI builds the image, scans it, generates an SBOM, signs it, and pushes it to the approved registry. An admission policy tool like Kyverno, Gatekeeper, or the cloud provider's own policy engine rejects anything from a non-approved registry, and ideally requires a digest, a signature, and provenance — meaning proof of where the artifact actually came from and how it was built — rather than just checking the registry hostname, since compromised registry credentials could still push a bad tag under a trusted name.

I restrict who has pull and push roles on the registry, protect the signing identity, use immutable tags with a retention policy, keep the registry on a private network, and audit access. I roll the policy out in audit mode first, test it against both compliant and noncompliant Pods, allow controlled exceptions in specific namespaces with an owner and an expiry date, and monitor denials.

I also control which fields can mutate the image reference and who can use ephemeral containers or node runtime access. If the registry becomes unavailable, disaster recovery uses an approved, replicated registry — bypassing image verification is only ever a high-risk, explicitly documented emergency action.

### 16. How do you detect and stop crypto-mining workloads in Kubernetes?

**Answer:** Enable anomaly detection (Falco/Azure Defender), restrict containers from running privileged mode, enforce quotas, and monitor unusual CPU spikes. Mini-case: A compromised pod started crypto-mining; Falco detected suspicious syscalls and Kubernetes killed the pod within seconds.
**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 17. How do you isolate workloads in a multi-tenant EKS cluster?

**Answer:**

Namespaces are the first boundary, but they aren't complete hard tenancy on their own. I combine them with tenant-specific Entra or IAM groups mapped to namespaced RBAC, separate ServiceAccounts and IRSA roles, default-deny network policy, quotas and LimitRanges, Pod security and admission control, trusted images, secrets isolation, and tenant-scoped logs, metrics, and cost labels.

Sensitive tenants get dedicated node groups with taints and a hardened runtime, and sometimes even separate clusters or cloud accounts when stronger isolation, compliance, or a smaller blast radius is required. Cluster-scoped resources, CRDs, webhooks, privileged Pods, and node access all stay platform-team-only.

I test cross-namespace API, network, secret, and IAM access, and resource-exhaustion attempts. I audit access and review quotas regularly. Whether to share a cluster at all follows the threat model, not just cost.

### 18. How do you architect multi-tenant Kubernetes clusters securely?

**Answer:** Use namespaces + strict RBAC per tenant, network policies to isolate traffic, resource quotas & limit ranges, PodSecurity admission controls, encrypt secrets, and audit logging per namespace. Consider separate clusters for high-security tenants.

Mini-case: We separated dev/test tenants into namespaces with network policies; when a noisy tenant consumed CPU, quotas throttled them preventing cross-tenant impact.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 19. How do you manage multiple Kubernetes clusters securely?

**Answer:** Use Rancher, Anthos, or Azure Arc → Apply consistent RBAC & policies → Centralized monitoring/logging.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

### 20. How do you enforce compliance in Kubernetes clusters?

**Answer:** Use OPA/Gatekeeper or Kyverno for policy enforcement → Restrict images, namespaces, resource limits.

**Detailed interview approach:**
I translate requirements into versioned, testable controls at several layers: source and branch rules, CI scanners, Terraform plan policy, Kubernetes admission policy, and cloud-native organization policy.

Typical examples require encryption, approved regions and images, non-root Pods, resource limits, labels and tags, private exposure, and least-privilege identity.

Each rule has unit tests with both allowed and denied fixtures, and produces an actionable reason plus a fix. Hard violations block the change, while approved exceptions are scoped, owned, and set to expire automatically.

Runtime and audit monitoring catches any change that happens outside CI. I track exceptions, false positives, and time to remediate, and periodically map the evidence back to each control, so compliance actually reflects real risk reduction rather than just a checklist.

### 21. How do you secure CI/CD pipelines running in Kubernetes?

**Answer:** Run pipelines as non-root → Restrict namespaces → Use PodSecurityPolicies/OPA → Isolate sensitive workloads.

**Detailed interview approach:**
I use SSO and MFA, role-based authorization, CSRF protection, TLS, a private controller, patched core and plugins, and I never run builds directly on the controller.

Credentials live in Jenkins Credentials or an external vault, scoped to the smallest folder or job that needs them. Pipelines use `withCredentials`, avoid shell tracing, and never interpolate a secret into a command line or artifact.

Agents are ephemeral, isolated, non-root where possible, and get a short-lived cloud identity. If a secret ever shows up in the logs, masking isn't enough — I stop the exposure, revoke and rotate the credential, restrict or delete the retained logs where policy allows, audit where it was used, and fix the step that printed it.

Configuration, plugins, and the restore process are all backed up and tested.
