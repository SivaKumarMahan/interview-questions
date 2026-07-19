# Webhooks in CI/CD

A webhook is an HTTP callback sent when an event occurs. Instead of polling a repository repeatedly, GitHub, GitLab, or Azure Repos sends a signed event such as a push, pull request, tag, or release to the CI/CD endpoint, which validates it and decides whether to start a pipeline.

Example flow:

```text
developer push → repository webhook → Jenkins/GitLab/Azure pipeline
→ build and tests → artifact publication → deployment or GitOps update
→ status reported back to the commit and notification channel
```

Security and reliability controls:

- Use TLS and validate the webhook signature with a rotated secret.
- Allow only expected event types and validate repository, branch, and sender data.
- Protect against replay using delivery IDs/timestamps and make event handling idempotent.
- Acknowledge quickly, queue longer work, and use bounded retry/dead-letter handling.
- Never treat receipt of a webhook as authorization to deploy production; branch protection, checks, artifact trust, environment approval, and deployment identity remain separate controls.
- Log delivery ID, event type, repository, decision, and pipeline run without logging secrets or sensitive payload data.

For troubleshooting I compare the repository delivery log with receiver access logs, verify DNS/TLS/firewall and response status, validate the signature secret and endpoint path, and check whether pipeline rules intentionally ignored the event.

