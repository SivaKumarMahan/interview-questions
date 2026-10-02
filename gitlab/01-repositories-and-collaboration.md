# GitLab: Repositories and Collaboration

> GitLab basics, merge requests and code review, branch protection, groups and access, tags and releases, and repository migration.

## Interview Questions

### 1. What is GitLab?

**Answer:**

GitLab is a DevSecOps platform built around Git repository hosting. It also includes merge requests, issues, access control, CI/CD, runners, package and container registries, releases, and security scanning.

You can use it as GitLab.com or run it self-managed. Organizations pick self-managed when they need control over network placement, upgrades, or data residency.

A typical flow: a developer pushes a branch and opens a merge request. The pipeline runs tests and scans. Reviewers approve, and the change merges. The pipeline publishes an immutable artifact — one that is never changed after it's built, only replaced by a new version. A protected environment job then deploys it.

Before choosing GitLab, I would still check runner security, backup and restore, identity integration, licensing, availability, and who owns it operationally.

### 2. What is a merge request in GitLab?

**Answer:**

A merge request proposes merging a source branch into a target branch. It brings together code review, discussion, pipeline results, approvals, and issue links, and ends with the merge decision.

In the description, I write a clear problem statement, the solution, the risk, test evidence, deployment impact, and rollback notes. GitLab can enforce rules on top of this: Code Owner approval, a successful pipeline, resolved discussions, and no merge conflicts.

I keep changes small enough to review properly. I mark a merge request as draft while the work is still incomplete.

Before merging, I check the generated artifact or infrastructure plan if one exists. After merging, I verify the deployment worked and link the release back to the merge request, so there's a clear audit trail.

### 3. How do you handle code review quality in GitLab?

**Answer:**

I combine process with automation:

- Small merge requests with clear acceptance criteria
- Code Owners required for security-sensitive or specialized areas
- Required approvals, with the author blocked from approving their own change
- Passing unit, integration, lint, security, and policy checks
- Resolved discussions and tested migrations
- Review checklists covering security, failure handling, observability, and rollback

I ask reviewers to explain the risk in a change, not just point out style preferences. Recurring style issues get moved into a linter instead of repeated in review comments. I track review time, defect escape rate, and oversized merge requests. Adding more required approvals without improving review quality just slows delivery down.

### 4. How do you protect branches in GitLab?

**Answer:**

I mark `main` and release branches as protected. That means I restrict who can push and merge, disallow force pushes, and require every change to go through a merge request. Approval rules force the right reviewers or Code Owners to sign off, and pipelines enforce tests, security scans, and policy checks.

I also protect tags and deployment environments. If someone can create a production tag or trigger a deployment directly, they can bypass branch controls entirely. Emergency access is limited, logged, and reviewed afterward.

I test the controls using a normal developer account: a direct push, a force push, an unauthorized merge, and access to protected variables should all fail. I also review access periodically and remove stale users and tokens.

### 5. How do GitLab groups and projects help access management?

**Answer:**

Groups organize related projects and can contain subgroups. Membership and settings can be inherited from a group down to its projects, which makes it easier to manage teams consistently. Projects themselves contain repositories, pipelines, registries, issues, and their own permissions.

I grant access through groups rather than to individual users, and I give each person the lowest role that still lets them do their job. I keep platform administration and application administration separate, and I create subgroups to mark different trust boundaries. A sensitive production project or runner should not inherit broad access just because its parent group has it.

I review inherited permissions, deploy tokens, access tokens, runner scope, protected environments, and external collaborators on a regular basis. Ownership is documented, so every access request and removal has someone accountable for approving it.

### 6. What are GitLab tags and releases used for?

**Answer:**

A Git tag marks a specific commit, usually a version like `v1.4.0`. A GitLab Release wraps that tag with release notes, evidence, links, and assets.

My pipeline builds an artifact once, records its commit SHA and checksum, and promotes that same immutable artifact through each environment rather than rebuilding it. Protected tags restrict who can trigger a release.

I never move a tag that's already published. A correction ships as a new version instead.

Release notes cover user-visible changes, migrations, known issues, deployment steps, and rollback information. After deployment, I check application health and keep enough artifact and pipeline evidence to reproduce exactly what reached production.

### 7. How do you migrate a repository to GitLab?

**Answer:**

First I inventory everything: branches, tags, large files, submodules, issues, pull requests, webhooks, deploy keys, CI secrets, branch policies, packages, and integrations. To move the Git history itself, I mirror all references:

```bash
git clone --mirror <old-url> project.git
cd project.git
git push --mirror <gitlab-url>
```

I recreate permissions, protected branches and tags, runners, variables, and webhooks by hand rather than copying plaintext secrets across. If needed, I migrate issues and review history using supported import tools.

Before cutover, I briefly freeze writes and run a final sync. I compare branch and tag counts and check important commit SHAs match. I test clone, push, merge, pipeline, and release operations on the new side, then switch DNS or repository URLs. The old repository stays read-only for an agreed period, and I keep a documented rollback plan ready.
