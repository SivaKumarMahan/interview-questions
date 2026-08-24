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
