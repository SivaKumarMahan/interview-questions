# GitHub Actions: Cross-Repository Triggers and Handoffs

> Triggering workflows in other repositories with repository_dispatch and handing off to Azure DevOps.

## Key Concepts

### Handoff to Azure DevOps

When GitHub Actions handles CI and Azure DevOps handles CD, GitHub Actions publishes a versioned package or an immutable ACR image digest, along with provenance (where the artifact came from and how it was built) and scan evidence.

Azure DevOps consumes and promotes that same artifact through protected environments — it should not rebuild the application.

Prefer GitHub OIDC to obtain short-lived Azure credentials, grant that identity only the ACR publishing permissions it needs, and protect the production Azure DevOps environment with resource permissions, branch control, approvals, and checks.

If Azure Pipelines already connects directly to GitHub and can own the whole workflow, it's worth comparing that simpler design before committing to a cross-platform handoff.

## Interview Questions

### 1. How do you trigger a GitHub Actions workflow in another repository?

**Answer:**

The best approach depends on who owns each repository. For loosely coupled systems, I prefer publishing a versioned artifact or image and letting the consumer repository detect or promote that version on its own.

When a direct trigger is needed, common options are `repository_dispatch`, calling `workflow_dispatch` through the API, or a reusable workflow — that last one works when repositories share an organization and a trust model.

The caller needs permission to invoke the target repository. I prefer a GitHub App token with narrow, short-lived access over a broad personal access token.

The payload should only carry identifiers, like a version number and source commit, never secrets. The target repository validates the sender, checks the artifact exists, and confirms the environment is allowed before it deploys.

I also add concurrency control, make the workflow idempotent, meaning safe to run more than once, keep audit logs, and attach a correlation ID. That way duplicate requests can't deploy twice, and both workflow runs stay traceable.

### 2. What is the purpose of `repository_dispatch` in GitHub Actions?

**Answer:**

`repository_dispatch` is a custom event sent through the GitHub API. It lets an external system or another repository start a workflow and pass a small JSON payload.

```yaml
on:
  repository_dispatch:
    types: [deploy-version]

jobs:
  deploy:
    if: github.event.client_payload.environment == 'staging'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ github.event.client_payload.version }}"
```

I use it for controlled cross-repository orchestration, not as an open production deployment endpoint. The sender needs the right repository permission. The receiver validates the event type and payload. Environment protection still controls what reaches production.

GitHub limits how big the payload can be, so artifacts stay in a registry or artifact store. The event itself carries only metadata.

### 3. How would you trigger a CI/CD pipeline in Repo A from changes in Repo B?

**Answer:**

Say Repo B builds a shared library and Repo A deploys an application. My preferred flow is:

1. Repo B tests and publishes an immutable library or image version.
2. Repo B authenticates with a GitHub App token.
3. It sends a dispatch event to Repo A with the version, source commit, and correlation ID.
4. Repo A checks that the version exists and is approved.
5. Repo A runs its own tests and gets environment approval before deploying.

```bash
gh api --method POST repos/company/repo-a/dispatches \
  -f event_type=dependency-released \
  -F 'client_payload[version]=2.3.1' \
  -F 'client_payload[source_sha]=abc123'
```

I prevent loops by defining one-way ownership, add concurrency control per environment, and keep the workflow idempotent.

If Repo A only needs a dependency update, a pull request from Dependabot or an update bot is often safer. It goes through normal review instead of triggering a deployment directly.
