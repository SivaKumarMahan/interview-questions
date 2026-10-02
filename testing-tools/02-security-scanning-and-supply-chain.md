# Testing Tools: Security Scanning and Supply-Chain Security

> Vulnerability, image and secrets scanning in CI/CD, image provenance, and end-to-end supply-chain security for container images.

## Interview Questions

### 1. Which security scanning tools do you run on container images at build time and registry time?

**Answer:**

At build time I scan source dependencies and the final image before it's published. Tools may include Trivy, Grype, Snyk, Docker Scout, or a commercial platform. Semgrep and SonarQube cover code and static findings, while Checkov and tfsec cover infrastructure definitions.

I generate an SBOM (a software bill of materials — a list of what's inside the image) with Syft or the build platform. I scan the actual image, not just the Dockerfile, and fail the build based on an agreed policy covering severity, exploitability, fix availability, age, and approved exceptions.

At registry time I enable continuous rescanning through a service such as ECR, ACR, Harbor, JFrog Xray, Nexus IQ, or Prisma. This catches vulnerabilities that get disclosed after an image was already built.

Alerts identify the image digest — which stays fixed once the image is built — along with the deployed workloads, the owner, the exposure, the base image, and the fix deadline. Production admission checks that the image comes from an approved registry, is signed, and meets policy.

I don't treat "zero CVEs" as the whole security program. Base images are pinned and rebuilt regularly. Secrets are scanned separately. Licenses and malware may have their own policy, and runtime controls catch behavior that scanning can't.

Exceptions are time-bound. When a fix is needed, the patched image is rebuilt, retested, signed, promoted, and verified — I don't patch a running container in place.

### 2. How do you integrate vulnerability scanning in CI/CD pipelines? *(scenario)*

**Answer:** Run static scans like Snyk or Trivy during the build. Fail the build if it finds critical CVEs, and automatically create a ticket to fix them.

Mini-case: Trivy caught a CVE in a base image. The pipeline failed, and developers patched the image before it went out.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege, meaning they only get the access they need for that one job. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM (a software bill of materials — a list of what's inside the build).

Images and artifacts are signed with provenance, meaning you can prove where they came from and how they were built. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

### 3. How do you enforce security scans in CI/CD? *(scenario)*

**Answer:** Add SAST (code scan with SonarQube) and DAST (OWASP ZAP) → Container image scans (Trivy/Anchore) → IaC scans (Checkov, tfsec).

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

### 4. CI/CD Pipeline Failing at the Trivy Security Scan

#### The pipeline

```text
Build → Test → SonarQube → Docker Build → Trivy Scan → Push ACR → Deploy Dev → Approval → Deploy Prod
```

Trivy stage fails with:

```text
CRITICAL vulnerabilities found
Exit code: 1
```

#### What I would do next

**I would not bypass Trivy and deploy anyway.** A CRITICAL vulnerability finding exists specifically to block deployment of known, exploitable weaknesses — pushing past it defeats the purpose of having the scan in the pipeline at all, and could ship a real security hole to production.

Instead:

1. **Review the actual findings** — Trivy's report names the specific CVEs, the affected package, and the severity. Not all "CRITICAL" findings are equally urgent (e.g., a CVE in a library function the app never calls is lower real-world risk than one in an internet-facing component).
2. **Check if a fixed version exists** — often the fix is simply updating a base image or dependency to a patched version.
3. **Rebuild and rescan** after the fix to confirm the vulnerability is resolved.
4. **If there's a genuine false positive or accepted risk** (e.g., the vulnerable code path is unreachable, or it's a transitive dependency with no fix available yet), document a formal exception/waiver with the security team's sign-off, and use Trivy's `.trivyignore` mechanism to suppress that specific CVE with a comment explaining why — not to silence the whole scan.
5. **Escalate the timeline** if the fix will take time — communicate the delay rather than silently skipping the gate.

```bash
# example: targeted, documented ignore (not a blanket bypass)
# .trivyignore
CVE-2023-XXXXX  # accepted risk: unreachable code path, tracked in JIRA-1234, review by 2026-09-01
```

#### Short interview answer

"I would not bypass a CRITICAL finding just to keep the pipeline moving — that's exactly the scenario the scan exists to prevent. I'd look at the actual CVE details to see if a patched base image or dependency version is available, fix and rescan, and only if there's a genuine false positive or an accepted, time-boxed risk would I use a targeted `.trivyignore` entry with sign-off and a tracking ticket — never a blanket bypass of the whole Trivy stage."

### 5. How do you manage secrets scanning and prevention of accidental commits? *(scenario)*

**Answer:** Use pre-commit hooks like git-secrets, CI scanning for secrets, and push-blocking hooks in company repos. Rotate any secret that gets found, and train developers to avoid this.

Mini-case: A developer accidentally committed an API key. The pre-commit hook blocked the push locally. When they tried again, the CI scan caught it and auto-rotated the leaked key.

**Detailed interview approach:**
Secrets belong in a secret manager such as Vault, Key Vault, or the CI credential store. They should never live in Git, YAML files, container images, command arguments, or build artifacts.

Each job gets a short-lived identity and fetches only the secret it needs for that stage. Masking log output is a secondary control, not the main one — an encoded or transformed value can still leak.

Rotation uses an overlap period. I issue the new value, update consumers, verify it works, then revoke the old value and check for anything that failed.

If a scan finds a secret that was already committed, I revoke it immediately. I check where it was used, remove it from active history where appropriate, and rotate any downstream credentials — just deleting the line from the file is not enough.

Pre-commit and server-side scans, protected logs, least privilege, expiry, and rotation tests all help prevent it happening again.

### 6. How do you monitor and enforce container image provenance across environments? *(scenario)*

**Answer:** Require signed images and immutable tags — once a tag is created, it can't be changed. Every image needs an SBOM, and deployments are gated on the SBOM and on vulnerability thresholds.

Mini-case: A new release's SBOM showed a vulnerable dependency. The gate blocked deployment until the image was rebuilt with the dependency patched.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

### 7. How do you implement end-to-end supply-chain security for container images? *(scenario)*

**Answer:** Sign and verify images with Cosign. Scan images during the build with Trivy or Anchore. Use reproducible builds, enforce image provenance in registries, and block unsigned or vulnerable images in the pipeline.

Mini-case: In a pipeline, I added a build step that runs Trivy, then Cosign signs the image on success.

The registry policy rejects any image without a valid signature — preventing a compromised build from reaching prod.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

### 8. How do you secure CI/CD pipelines from supply chain attacks? *(scenario)*

**Answer:** Pin dependencies → Verify container/image signatures (Cosign) → Scan dependencies → Restrict external plugin usage.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.
