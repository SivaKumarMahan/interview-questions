# Artifact Repositories: Security, Signing, and Access Control

> Trusted registries, artifact signing and verification, securing artifact storage and registries, Nexus authentication, RBAC, and supply-chain controls.

## Interview Questions

<details><summary>Q1. [Basic] Which container registry should you trust for production images?</summary>

**Answer:**

I trust an organization-approved registry, not an image just because it is public or popular.

The registry needs strong identity controls and repositories locked down to the minimum access people actually need. It also needs TLS and encryption, tags that can't be changed after creation (or deployment by digest instead of tag), vulnerability scanning, audit logs, retention and recovery, replication and availability, and integration with signing, SBOM, and admission policy.

Examples include ECR, ACR, GCR/Artifact Registry, JFrog Artifactory, Nexus, Harbor, or another managed internal service.

Base images come from allowlisted publishers. They're mirrored internally, pinned by digest, scanned, and rebuilt on a schedule the team owns. CI authenticates with a short-lived identity, signs the resulting digest, and only the release workflow can write to production repositories.

Kubernetes or the runtime checks that the image comes from an approved registry, verifies its signature and provenance (proof of where it came from and how it was built), and checks policy before deployment.

I test pull behavior during a registry or availability-zone failure, and monitor auth failures, scan findings, replication lag, storage, and unusual downloads. A private registry alone doesn't guarantee trust. Provenance and controlled promotion into production are what actually establish it.

</details>

<details><summary>Q2. [Intermediate] How do you secure Docker registry in production? <em>(scenario)</em></summary>

**Answer:** Enable HTTPS & authentication → Use signed images (Cosign) → Restrict access via IAM.

**Detailed interview approach:**
I look at the image, the runtime configuration, and the host separately. Builds use multi-stage Dockerfiles, small pinned trusted base images, a `.dockerignore` file, dependency layers ordered for caching, and non-root runtime users.

CI scans the dependencies and the image, generates an SBOM, signs the digest so it can't be swapped later, and pushes it over TLS to a registry with tightly scoped write access. Deployment then verifies that same digest before running it.

At runtime I drop unnecessary capabilities, use seccomp, AppArmor, or SELinux, run with a read-only filesystem, set resource limits, avoid exposing the privileged Docker socket, and restrict networking.

If startup is slow or a push fails, I measure layer size and cache hits, check registry DNS, auth, and TLS, and check disk and application initialization, instead of just retrying blindly. Then I rebuild from patched base images and re-verify functionality and security findings.

</details>

<details><summary>Q3. [Intermediate] How do you secure CI/CD artifact storage? <em>(scenario)</em></summary>

**Answer:** Store in Nexus/Artifactory → Enable RBAC → Use signed artifacts → Encrypt storage.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, isolated ephemeral runners, and short-lived identities scoped to the minimum access needed.

On top of that I run SAST, dependency, secret, IaC, and container scans, generate an SBOM, sign the provenance record and the artifacts themselves, use protected registries, and verify everything again at deployment admission.

Scan findings get an agreed severity and SLA, plus a time-limited exception process, so the gates are strict but still usable day to day.

If I suspect compromise, I stop promotion, revoke runner and signing credentials, isolate the affected artifacts, preserve audit evidence, rebuild from a trusted runner and source, and verify signatures again before redeploying.

Regular patching, egress restrictions, audit log retention, and recovery drills cover the gaps that scanners alone can't catch.

</details>

<details><summary>Q4. [Advanced] How do you sign software artifacts and verify them before deployment?</summary>

**Answer:**

I sign the digest after the build and security checks pass, using a protected key or a keyless workload identity tied to the CI workflow. Containers and OCI Helm charts can use Cosign. Classic Helm charts can use provenance signatures. Packages can use whatever signing mechanism is native to that ecosystem.

The signature and provenance record the source commit, the builder or workflow that produced it, the artifact digest, and any attestations such as SBOM or test results.

Deployment policy checks the digest, the signature's identity and issuer, the expected repository or workflow, and any required attestations before admitting or promoting the artifact. Keys have owners, rotation, revocation, and audit trails. CI jobs never get long-lived exported private keys.

I also test offline or recovery-mode verification, so it still works when something else is down.

Signing proves origin and integrity, not quality. Code review, tests, scanning, policy checks, and runtime controls are still needed on top of it.

If a key or workflow is compromised, I revoke trust, find every digest signed with it, rebuild from a trusted pipeline, and block those old artifacts from deployment.

</details>

<details><summary>Q5. [Intermediate] What is the role of Nexus Repository in software supply-chain management?</summary>

**Answer:**

Nexus is the controlled distribution point for software inputs and outputs.

It helps establish:

- Which external sources builds may use.
- Which internal artifact coordinate is authoritative.
- Who uploaded and downloaded components.
- Which immutable artifact was promoted/deployed.
- Central dependency inventory and usage visibility.
- An enforcement point for routing, access and retention.
- Integration with scanning, policy, SBOM, signatures and provenance.

Representative flow:

```text
approved source
-> Nexus proxy/group
-> reproducible build
-> SAST/SCA/tests
-> artifact and SBOM
-> sign immutable checksum/digest
-> Nexus hosted/staging repository
-> approval/promotion
-> deployment verifies identity and digest
```

Nexus alone does not prove that an artifact is safe. Repository management, Sonatype Firewall/Lifecycle where licensed, CI security checks, signing, admission/deployment verification and incident response work together.

</details>

<details><summary>Q6. [Intermediate] How would you configure authentication and authorization in Nexus Repository?</summary>

**Answer:**

I separate authentication from authorization.

Authentication options depend on edition/deployment and can include:

- Local Nexus users.
- External identity realms such as LDAP.
- SAML/SSO capabilities in applicable Pro deployments.
- User tokens/API keys where supported.
- Dedicated CI service accounts.

Authorization uses:

- **Privileges:** Actions such as browse, read, add, edit, delete and repository administration.
- **Roles:** Collections of privileges.
- **Content selectors:** More detailed access to paths/namespaces.
- **Users/groups:** Assigned one or more roles.

Example roles:

```text
developers-read
  browse/read maven-public and npm-group

orders-ci-publisher
  browse/read/add/edit orders hosted repository
  no delete
  no repository administration

release-manager
  approved promotion operations

nexus-operator
  system operations without unnecessary artifact publication
```

I:

- Disable anonymous access unless there is a justified read-only use case.
- Change the initial administrator password.
- Use named administrator accounts and MFA/SSO where available.
- Avoid sharing `admin` credentials with pipelines.
- Restrict role-management permissions because a user able to assign roles can escalate privileges.
- Review access periodically and remove leavers/stale service accounts.
- Keep Production publisher and reader permissions separate where required.

</details>

<details><summary>Q7. [Intermediate] How do you handle access control for different development teams in Nexus Repository?</summary>

**Answer:**

I design access around teams and actions:

```text
team-orders-developers
  read/browse common groups
  no release write

team-orders-ci
  read group
  add/edit only orders snapshot/release namespace
  no delete/admin

team-payments-ci
  separate hosted namespace and credential

release-managers
  approved promotion operation

repository-operators
  repository/system administration
```

I use:

- Identity-provider groups mapped to Nexus roles.
- Repository-view privileges.
- Content selectors for namespace/path-level separation.
- Separate service accounts for each pipeline/team.
- Environment-specific release permissions.
- Periodic access reviews.
- Immediate leaver/service-account cleanup.

Read permission on a group can expose the content of all its members through that group. So I never put restricted artifacts inside a broadly readable group.

</details>

<details><summary>Q8. [Intermediate] How do you secure sensitive artifacts stored in Nexus Repository?</summary>

**Answer:**

I apply defense in depth:

- HTTPS only with trusted certificates.
- Restricted network exposure through private connectivity/firewalls/reverse proxy.
- Anonymous access disabled unless explicitly justified.
- Enterprise SSO/MFA where supported.
- Least-privilege roles and content selectors.
- Separate identities for humans, CI readers, CI publishers and administrators.
- Secrets stored in Azure Key Vault, not pipeline YAML or client project files.
- Encryption at rest through the database/blob-storage design.
- Immutable release coordinates and disabled redeploy.
- Audit/security logging and alerts for unusual download/upload/delete behavior.
- Supported Nexus/Java/OS versions and timely patching.
- Routing rules to constrain namespace/source behavior.
- Artifact scanning, SBOM, signing and checksum verification in the supply-chain process.
- Tested backups with restricted access.

If an artifact is confidential, I also keep it out of any broadly readable group and restrict who can access backups and support bundles. Even when the binary itself is encrypted, the name and metadata around it can still be sensitive.

I never run Nexus as the operating-system root account.

</details>
