# Repetitive Interview Questions

## How do you implement strong security for your applications? What security best practices do you follow so that applications are not compromised?

### Detailed answer

In my Azure projects, I implement security through **defense in depth**. I do not claim that any application can be guaranteed never to be compromised. My objective is to reduce the probability of compromise, minimize the blast radius if one control fails, detect abnormal activity quickly and recover safely.

I treat security as a shared responsibility across architecture, development, CI/CD, Azure infrastructure, AKS, data, monitoring and operations. It starts during design and continues after the application reaches Production.

A simplified request and dependency flow is:

```text
internet/client
-> Azure Application Gateway WAF
-> TLS termination and approved routing
-> AKS ingress and Kubernetes Service
-> restricted non-root application Pod
-> Microsoft Entra Workload ID
-> Azure Key Vault / PostgreSQL / Blob Storage
-> private endpoints and private DNS

security telemetry
-> Azure Monitor / Log Analytics / Application Insights
-> Defender for Cloud and security alerts
-> investigation and incident-response process
```

The major principles I follow are:

- Verify explicitly and do not trust a request only because it came from an internal network.
- Grant the least privilege required for the shortest practical duration.
- Prefer identity-based, short-lived access instead of static credentials.
- Keep Production isolated from lower environments.
- Build once and promote the same immutable artifact.
- Automate preventive controls and continuously monitor detective controls.
- Assume one control can fail and maintain multiple independent layers.

### 1. Security requirements and threat modeling

Before implementation, I identify:

- The sensitive assets and data handled by the application.
- Users, administrators, services and external integrations.
- Entry points, APIs, upload endpoints and trust boundaries.
- Authentication and authorization requirements.
- Data classification, residency, retention and recovery requirements.
- Likely abuse cases such as account takeover, injection, broken access control, credential theft, malicious uploads and denial of service.
- Required RPO, RTO and business response to a security incident.

For an important application change, the team reviews the data flow and asks:

```text
What are we protecting?
Who should be allowed to access it?
How could an attacker misuse this flow?
Which preventive control blocks that path?
Which log or alert tells us if it happens?
How will we contain and recover from it?
```

We use the OWASP Top 10 and OWASP ASVS as practical references for requirements and verification, while also applying the organization's security and compliance policies. Findings have an owner, severity, remediation date and evidence of closure.

### 2. Identity and access management

Identity is the main security boundary in the project.

For human access:

- We authenticate users and administrators through Microsoft Entra ID.
- MFA and Conditional Access are applied according to organizational policy.
- Privileged roles are activated only when required through Privileged Identity Management where available.
- Named accounts are used; shared administrator accounts are avoided.
- Joiner, mover and leaver processes remove access when a person's responsibility changes.
- Emergency access accounts are tightly controlled, monitored and periodically tested.

For application access:

- User-facing applications use approved OAuth 2.0/OpenID Connect flows with Microsoft Entra ID.
- APIs validate the token signature, issuer, audience, expiry and required scopes or roles.
- Authentication only proves identity; the application performs authorization for every protected action.
- Object-level authorization prevents one authenticated user from reading or changing another user's resource.
- Administrative endpoints use separate, stronger roles and are not exposed merely because a user is authenticated.

For service-to-service access:

- Azure resources use managed identities.
- AKS Pods use Microsoft Entra Workload ID with a dedicated Kubernetes service account.
- Each application and environment receives a separate identity.
- Azure RBAC is assigned at the narrowest practical resource scope.
- Broad Owner or Contributor access is not given to a runtime identity.
- Kubernetes RBAC is also least-privilege and separated from Azure management-plane access.

This approach removes long-lived cloud credentials from source code and pipelines and limits the damage if one workload identity is compromised.

### 3. Secrets, keys and certificates

Secrets such as database passwords, third-party API tokens and certificates are stored in Azure Key Vault. They are not kept in:

- Git repositories.
- Dockerfiles or container images.
- Helm values committed to source control.
- Plain pipeline variables.
- Application configuration files.
- Debug logs or deployment output.

AKS applications authenticate with Workload ID and retrieve only their approved secrets from Key Vault, directly through the SDK or through the Key Vault provider for the Secrets Store CSI Driver when a mounted-secret pattern is required.

Key Vault is protected with:

- Azure RBAC and least-privilege data access.
- Private endpoint and Private DNS where required by the architecture.
- Firewall/public-network restrictions.
- Soft delete and purge protection.
- Expiration and rotation processes.
- Diagnostic logs and alerts for unusual secret access or permission changes.
- Separation between Development, Testing and Production vaults.

If a secret is exposed, I do not only delete it from Git history. I immediately revoke or rotate it, identify where it was used, review the access logs, replace affected deployments and determine whether unauthorized access occurred.

### 4. Network and edge protection

Public traffic reaches the application through an approved edge component such as Azure Application Gateway with Web Application Firewall.

The controls include:

- HTTPS only with an approved TLS policy.
- Certificates sourced and renewed through the controlled certificate process.
- WAF managed rules for common web attacks.
- Custom rules for application-specific paths, source restrictions or known abuse patterns.
- Request-size, connection and rate controls at the appropriate layer.
- DDoS protection based on the application's risk and network architecture.
- Access logs, WAF logs and alerts for abnormal blocking or traffic patterns.

WAF policies are first tested and tuned so that legitimate traffic is not blocked, and Production policies use prevention where approved. A WAF is an additional layer; it does not replace input validation, authorization or secure coding.

Inside Azure:

- Production networks and subscriptions are separated from lower environments.
- AKS, databases, Key Vault and Storage use private connectivity where the design requires it.
- Network Security Groups restrict subnet traffic.
- Private DNS is configured and verified with private endpoints.
- Azure Firewall or an approved egress control limits unexpected outbound communication when required.
- Management endpoints are not unnecessarily exposed to the internet.
- Kubernetes NetworkPolicies start from default-deny and allow only required Pod-to-Pod, ingress and egress flows.

For example, the frontend is allowed to call the application API, but it is not automatically allowed to connect directly to the database. The API can reach only the required database and platform endpoints.

### 5. Secure application development

Developers implement security in the application instead of depending only on infrastructure controls.

Important application controls include:

- Validate input on the server using type, length, range, format and allowlist rules.
- Use parameterized queries or the safe ORM mechanism to prevent injection.
- Encode output in the correct HTML, JavaScript, URL or other context.
- Perform authorization on every protected API and resource identifier.
- Use unpredictable identifiers where appropriate, without treating them as authorization.
- Enforce upload type, size and authorization; rename files and malware-scan them where required.
- Restrict outbound destinations to reduce server-side request-forgery risk.
- Configure CORS for known origins instead of using a broad wildcard with credentials.
- Apply CSRF protection to cookie-authenticated state-changing requests.
- Use secure, `HttpOnly` and appropriate `SameSite` cookie settings.
- Apply timeouts, body-size limits, pagination and abuse/rate limits.
- Avoid unsafe deserialization and command construction.
- Return controlled error messages without stack traces, credentials or internal paths.
- Keep framework and dependency versions supported and patched.

Sensitive data is never trusted simply because it came from another internal service. Each API validates the caller and its permissions.

Security-relevant unit and integration tests cover positive and negative cases. For example, tests verify that a valid user can access the correct object and receives a denial for another user's object.

### 6. DevSecOps controls in CI/CD

Security checks run early in pull requests and again at controlled stages before Production. A representative flow is:

```text
feature branch
-> pull request and peer review
-> secret scan
-> SAST and dependency scan
-> unit/security tests
-> Terraform, Helm and Kubernetes policy scan
-> build immutable container
-> container image and package scan
-> generate provenance/SBOM where adopted
-> deploy to non-production
-> integration and authorized DAST
-> approval and policy checks
-> promote the same image digest to Production
-> runtime monitoring
```

Typical controls are:

- Protected branches and mandatory pull-request reviews.
- `CODEOWNERS` or equivalent approval for sensitive code and infrastructure.
- Secret scanning to stop credentials before merge.
- SAST using an approved tool such as SonarQube, CodeQL or Semgrep.
- Software-composition analysis for vulnerable and unapproved dependencies.
- IaC and Kubernetes-manifest scanning with an approved scanner such as Checkov.
- Container-image scanning with Defender for Cloud, Trivy or the approved registry control.
- Authorized DAST, for example OWASP ZAP, against a controlled non-production environment.
- License and policy validation where required.
- SBOM generation and artifact signing/verification where the platform has adopted them.

Release gates are based on an agreed severity policy. A Critical or High vulnerability is not casually ignored. If a genuine exception is necessary, it must contain:

- Business justification.
- Risk and compensating controls.
- Named risk owner and approval.
- Expiry date.
- Remediation plan and tracking item.

Pipeline security is equally important:

- Runners/agents are patched, isolated and preferably ephemeral for sensitive builds.
- Pipelines use workload federation, service connections or managed identity instead of long-lived credentials.
- Production secrets are never made available to untrusted pull-request jobs.
- Third-party actions, plugins, images and modules are pinned to reviewed versions or digests.
- Only the deployment identity can deploy, and it receives only the required scope.
- Build output is immutable and the exact approved digest is promoted between environments.
- Pipeline changes themselves require review.

### 7. Container-image security

For containerized applications, I:

- Start from a trusted, minimal and supported base image.
- Use multi-stage builds so compilers and build tools are not shipped in the runtime image.
- Pin important dependencies and base-image versions, then update them through a controlled process.
- Run as a non-root user.
- Do not copy credentials, source-control metadata or unnecessary files into the image.
- Use a `.dockerignore` file.
- Scan the image before it is pushed or promoted.
- Store it in Azure Container Registry with restricted access.
- Deploy by immutable digest instead of a mutable `latest` tag.
- Rebuild and redeploy when the base image or dependency needs a security patch.

Scanning an image once is not enough. New vulnerabilities can be published after deployment, so the registry and runtime inventory are continuously reassessed and affected images are rebuilt.

### 8. AKS workload and cluster hardening

AKS security is applied at both cluster and workload levels.

For cluster access:

- Integrate access with Microsoft Entra ID and least-privilege Kubernetes/Azure RBAC.
- Restrict the API server according to the approved private or authorized-network design.
- Keep Kubernetes, node images and supported add-ons patched.
- Separate workloads by namespace and risk boundary.
- Enable required AKS control-plane, audit and workload logs.
- Use Azure Policy/Gatekeeper and Pod Security Admission to enforce guardrails.
- Protect privileged namespaces and administrative service accounts.

For workloads:

- Use a dedicated service account and Workload ID per application.
- Disable automatic service-account token mounting when the Pod does not require it.
- Run as non-root and prohibit privilege escalation.
- Drop Linux capabilities unless one is explicitly required.
- Use the default runtime seccomp profile.
- Use a read-only root filesystem when the application supports it.
- Define CPU/memory requests and limits.
- Do not allow privileged containers, host networking or unapproved `hostPath` mounts.
- Use default-deny NetworkPolicies and add explicit allowed flows.
- Retrieve secrets from Key Vault instead of treating base64-encoded Kubernetes Secret values as encryption.
- Use readiness, liveness and startup probes without exposing sensitive information.

A representative workload security context is:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orders-api
  template:
    metadata:
      labels:
        app: orders-api
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: orders-api
      automountServiceAccountToken: true
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: orders-api
          image: <acr-name>.azurecr.io/orders-api@sha256:<approved-digest>
          ports:
            - name: http
              containerPort: 8080
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          volumeMounts:
            - name: temporary-files
              mountPath: /tmp
      volumes:
        - name: temporary-files
          emptyDir: {}
```

`automountServiceAccountToken` is enabled in this example because Workload ID needs the projected service-account token. For a workload that does not call the Kubernetes API and does not use this identity flow, I disable token automounting. The exact manifest is validated against the application rather than copied blindly.

### 9. Data and database protection

I protect data throughout its lifecycle:

- Collect and retain only the data required by the business.
- Classify sensitive data and define its owner.
- Encrypt traffic in transit and use platform encryption at rest.
- Use private access for Azure Database for PostgreSQL and Storage where required.
- Give the application identity only the necessary database/schema/object permissions.
- Separate migration privileges from normal runtime privileges.
- Parameterize database queries.
- Mask sensitive values in lower environments.
- Do not write passwords, tokens, personal data or full payment details to logs.
- Configure retention and secure deletion based on policy.
- Use backups, point-in-time recovery and tested restore procedures based on RPO/RTO.

Encryption protects confidentiality but does not correct excessive permissions. Identity, authorization, private connectivity, monitoring and recovery are still required.

### 10. Infrastructure and policy as code

Azure infrastructure is created through reviewed Terraform or Bicep rather than unmanaged manual changes.

The infrastructure workflow includes:

- Reusable, approved modules.
- Formatting, validation, linting and security scanning.
- Pull-request review of the deployment plan.
- Remote state with locking and tightly restricted access for Terraform.
- Separate state and identities for each environment.
- Azure Policy for required tags, approved regions/SKUs, diagnostic settings, network restrictions and AKS security standards.
- Defender for Cloud recommendations and workload protection where approved.
- Detection and reconciliation of configuration drift.

I initially introduce policies in audit mode to understand impact, remediate existing resources and then move suitable controls to deny. Break-glass changes are documented, reviewed and reconciled back into code.

### 11. Logging, detection and alerting

Prevention is incomplete without detection. We centralize signals in Azure Monitor and Log Analytics and use Application Insights, Prometheus and Grafana for application and platform visibility.

Security-relevant telemetry includes:

- Application authentication failures and authorization denials.
- Administrative and sensitive business actions.
- Application Gateway access and WAF logs.
- AKS control-plane and audit logs.
- Container restarts and unexpected process/network behavior.
- Microsoft Entra sign-in and audit events.
- Azure Activity Log and RBAC changes.
- Key Vault access and policy changes.
- Database and Storage security events.
- Defender for Cloud alerts and vulnerability findings.

Alerts focus on actionable patterns such as:

- Sudden authentication failures or impossible access behavior.
- Repeated WAF matches or unusual request rates.
- Unexpected role assignment or policy changes.
- Abnormal secret access.
- Critical vulnerable artifacts in active environments.
- Suspicious Pod creation, privileged settings or unexpected outbound traffic.
- A sharp increase in HTTP 401, 403 or 5xx responses.

Logs contain timestamps, environment, component and correlation IDs, but sensitive tokens and request bodies are redacted. Access to logs is itself restricted and audited. Alerts have an owner, severity, runbook and escalation route.

### 12. Vulnerability and patch management

Vulnerabilities are handled through a repeatable process:

1. Discover the issue through scanning, a vendor advisory, Defender or testing.
2. Validate whether the affected component and vulnerable path are actually present.
3. Prioritize using severity, exploitability, exposure, data sensitivity and business impact.
4. Patch, upgrade, remove or mitigate the component.
5. Rebuild from the trusted source and redeploy the immutable artifact.
6. Rescan and verify that the finding is closed.
7. Track any temporary exception until its expiry.

Operating systems, AKS versions, node images, language runtimes, libraries, build agents and security tools all have supported-version and patching processes. Unused packages, public endpoints, identities and resources are periodically removed.

### 13. Incident response

Even with strong controls, we prepare for an incident.

If suspicious activity is detected, the high-level response is:

1. Validate and classify the alert without destroying evidence.
2. Contain the impact by blocking traffic, disabling an identity, isolating a workload or revoking a credential.
3. Preserve relevant logs, timestamps, artifact digests and deployment information.
4. Determine affected users, data, identities, environments and time window.
5. Eradicate the cause by patching code, rotating secrets and rebuilding from a trusted source.
6. Recover using the approved deployment or restore process.
7. Increase monitoring during recovery.
8. Complete root-cause analysis and add preventive and detective actions.

I avoid making uncontrolled changes directly in a running container. A compromised workload is replaced with a verified image, and the permanent fix is committed through the normal code and pipeline process.

### 14. Verification and evidence

I verify security through evidence rather than assuming that a configured control works.

Examples include:

- Threat-model and architecture review records.
- Pull-request approvals and pipeline scan reports.
- Tests proving unauthorized users receive a denial.
- Azure Policy compliance results.
- Evidence that a privileged Pod is rejected.
- Network tests proving disallowed flows fail.
- Key Vault and RBAC access reviews.
- Vulnerability remediation reports.
- Restore tests and incident-response exercises.
- Authorized penetration testing for important applications.

Security is reviewed after architecture changes, new integrations, major framework upgrades and incidents—not only during the first deployment.

### 15. Common security mistakes I avoid

- Saying that a WAF alone secures the application.
- Giving broad Contributor, cluster-admin or database-owner access to applications.
- Storing secrets in Git, images, Helm values or pipeline logs.
- Treating base64-encoded Kubernetes Secrets as encrypted secure storage.
- Exposing databases, Key Vault or cluster management endpoints unnecessarily.
- Running every container as root or privileged.
- Using one identity and one vault across all environments.
- Deploying a mutable image tag without recording the digest.
- Running scans but allowing findings to remain unowned indefinitely.
- Disabling a security rule to make a deployment pass without understanding the risk.
- Logging tokens, personal data, stack traces or full request bodies.
- Patching manually in Production without updating the source and image.
- Assuming private networking removes the need for authentication and authorization.

### Layered-control summary

| Layer | Main controls | Evidence I check |
| --- | --- | --- |
| Design | Threat modeling, classification, OWASP requirements | Reviewed data flow and tracked risks |
| Identity | Entra ID, MFA, Workload ID, least privilege | Access review and sign-in/RBAC logs |
| Secrets | Key Vault, rotation, private access | Expiry status and vault diagnostics |
| Edge/network | TLS, Application Gateway WAF, NSGs, private endpoints, NetworkPolicies | WAF logs and permitted-flow tests |
| Application | Validation, authorization, safe queries, secure errors | Unit, negative and integration tests |
| CI/CD | Reviews, SAST, SCA, secret/IaC/image scanning | Passing gates and approved exceptions |
| Container/AKS | Non-root, restricted Pods, policy enforcement, patching | Admission result and workload inventory |
| Data | Encryption, minimal access, backup and retention | Access audit and successful restore test |
| Runtime | Monitor, logs, alerts and Defender | Alert tests, triage records and runbooks |
| Response | Containment, rotation, rebuild and RCA | Exercise/incident actions closed |

### Concise interview answer

In my Azure project, I secure applications using defense in depth; I never depend on a single tool or claim that compromise is impossible. At the identity layer, users authenticate through Microsoft Entra ID and workloads use managed identity or AKS Workload ID with least-privilege RBAC. Secrets and certificates are stored in Azure Key Vault and are not committed to code, images or pipeline files.

At the network layer, public traffic passes through Azure Application Gateway WAF over HTTPS. Production services use restricted networks, private endpoints, NSGs and Kubernetes default-deny NetworkPolicies. At the application layer, we enforce server-side authorization, strict input validation, parameterized database queries, secure error handling, upload controls, supported dependencies and security tests based on OWASP guidance.

Security is shifted left in CI/CD through protected branches, peer review, secret scanning, SAST, dependency, IaC and container-image scans. We build one immutable image, store it in Azure Container Registry and promote its digest. In AKS, containers run as non-root, cannot escalate privileges, drop unnecessary capabilities and are controlled by RBAC, Pod Security and Azure Policy.

Finally, we continuously monitor Application Gateway, AKS, Entra ID, Key Vault and application events through Azure Monitor, Log Analytics, Application Insights and Defender for Cloud. Alerts have runbooks, and if an incident occurs we contain it, revoke credentials, preserve evidence, rebuild from a trusted artifact, recover and complete root-cause actions. This approach reduces the likelihood and blast radius of compromise and helps us detect and respond quickly.
