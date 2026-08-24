# Webhooks in CI/CD

A webhook is an HTTP callback sent when something happens. Instead of a CI system repeatedly polling a repository for changes, GitHub, GitLab, or Azure Repos sends a signed event — a push, a pull request, a tag, or a release — straight to the CI/CD endpoint. That endpoint validates the event and decides whether to start a pipeline.

Example flow:

```text
developer push → repository webhook → Jenkins/GitLab/Azure pipeline
→ build and tests → artifact publication → deployment or GitOps update
→ status reported back to the commit and notification channel
```

Security and reliability controls:

- Use TLS, and validate the webhook signature with a secret that gets rotated regularly.
- Only accept expected event types, and validate the repository, branch, and sender.
- Protect against replay using delivery IDs and timestamps. Make event handling idempotent, meaning it's safe to process the same event more than once without side effects.
- Acknowledge the webhook quickly, queue the actual work, and use limited retries with a dead-letter queue for failures.
- Never treat receiving a webhook as authorization to deploy to production on its own. Branch protection, checks, artifact trust, environment approval, and deployment identity are all still separate controls.
- Log the delivery ID, event type, repository, decision, and pipeline run — but never log secrets or sensitive payload data.

When troubleshooting, I compare the repository's delivery log against the receiver's access logs, check DNS, TLS, firewall rules, and the response status, validate the signature secret and endpoint path, and check whether a pipeline rule intentionally ignored the event.
