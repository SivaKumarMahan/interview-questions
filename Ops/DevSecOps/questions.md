## 1. How do you implement runtime security beyond image vulnerability scanning?

**Answer:**

Image scanning only checks things before deployment. It can't catch stolen credentials, unexpected processes, lateral movement, or a risky runtime setup once the container is actually running.

So I combine signed, approved images and admission policy with hardening: non-root users, read-only root filesystems, dropped Linux capabilities, seccomp/AppArmor/SELinux, no privileged mode or host Docker socket, resource limits, namespace isolation, and default-deny network rules.

At runtime, I rely on Falco, eBPF-based tooling, cloud workload protection, Kubernetes audit logs, and container monitoring to catch suspicious behavior — things like a shell popping up in a service that should never have one, writes to system paths, crypto-mining, privilege escalation, unusual outbound traffic, or access to service-account tokens.

Every detection rule has an owner, context, a tested severity, and a defined response. Noisy generic alerts get tuned, not ignored.

When an alert looks real, I isolate the traffic or workload first, while preserving audit, process, network, and image evidence. Then I revoke any exposed identities, check for lateral movement, and rebuild the workload or node from trusted artifacts rather than trying to clean it in place.

Afterward I confirm the service has recovered and the attack path is now blocked, then improve policy, patching, key rotation, and detection coverage based on what I learned.

## 2. How would you secure secrets for more than 100 microservices without exposing credentials?

**Answer:**

I centralize secrets in Vault, a cloud secret manager, or an approved platform, and give each workload its own short-lived identity to authenticate with. Kubernetes workload identity and service accounts, cloud IAM roles, or SPIFFE-style identities all remove the need for shared static credentials.

Policies map one service, in one environment, to only the secret paths and operations it actually needs. Production identities can't be used from a developer laptop or a CI branch.

Applications fetch secrets at runtime, or through an external-secrets/CSI integration that delivers them in memory or to a controlled file. Secret values never end up in Git, images, Terraform outputs, command arguments, tickets, or normal logs.

Rotation works with an overlap: issue the new secret, update the consumers, verify, revoke the old one, and audit for failures. Dynamic database credentials with short lifetimes make rotation much simpler.

At this scale I also need clear ownership, naming, metadata, expiry, rotation targets, access reviews, audit alerts, a break-glass procedure, and dashboards that flag stale or unused secrets. If something leaks, I revoke it first, check the audit logs to see how it was used, rotate anything downstream that trusted it, rebuild affected artifacts, and then clean up the leaked copies.

## 3. How do you maintain cybersecurity practices across a DevOps environment?

**Answer:**

I use defense in depth: source, CI, artifacts, infrastructure, workloads, and operations each get their own layer of controls.

Source repositories get SSO/MFA, branch protection, signed or reviewed changes, secret scanning, and access limited to only what's needed.

CI runs on isolated, short-lived runners with short-lived identities, pinned actions and plugins, SAST/SCA/IaC/container scans, SBOMs, signed artifacts, and protected deployment environments. Policies block critical violations, with a documented path for approved exceptions.

Infrastructure is private by default, encrypted, built from hardened images, patched, and reviewed for IAM issues, with backups, centralized audit logs, and drift detection on the IaC. Runtime controls limit privilege and network access and feed into real, actionable alerts.

Incident response has clear ownership: preserve evidence, revoke credentials, contain the issue, recover from trusted artifacts, communicate with stakeholders, and improve afterward.

I track metrics like patch and secret age, time to fix critical findings, policy bypasses, privileged access, restore tests, detection coverage, and failed changes tied to security issues. Security lives inside the normal delivery path — it's not a final manual checklist at the end.

## 4. A secret key was accidentally committed to Git. What actions do you take?

**Answer:**

I treat the key as compromised the moment it's committed, even if the commit gets deleted quickly. First I revoke or disable it, check the provider's and repo's audit logs to see if it was used, issue a replacement with only the access it needs and a real expiry, update consumers through the secret manager, and confirm the service still works.

If that key could have unlocked other credentials, I rotate those too.

Next I remove the value from the current code, and if policy requires it, coordinate a history rewrite with `git filter-repo`, protect against force-pushes, tell people to re-clone, and clean up forks, caches, CI artifacts, logs, and any package or image layers that captured it. Cleaning up history reduces exposure, but it doesn't replace revoking the key — that has to happen either way.

I write down the timeline, scope, evidence of access, and how it was resolved, notify security and the owners, and add controls to prevent a repeat: pre-commit and server-side secret scanning, push protection, short-lived workload identity, restricted CI logs and artifacts, and developer training.

Finally, I test that the old key no longer works and that the new identity only has the access it needs.
