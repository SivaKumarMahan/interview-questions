## 1. What is the difference between `origin` and `upstream` remotes?

**Answer:**

A Git remote is just a local name for another repository's URL. `origin` is a convention, not a rule: it is usually the repository I cloned from, and the place where I push my branch. In a fork workflow, `upstream` usually points to the original project I forked from.

```bash
git remote -v
git remote add upstream https://github.com/company/project.git
git fetch upstream
git rebase upstream/main
git push --force-with-lease origin feature/login
```

The flow is simple: fetch the latest changes from the original project through `upstream`, update my feature branch, then push that branch to my fork through `origin`. These names aren't special to Git — they can be changed. So when troubleshooting, I always check `git remote -v` instead of assuming what they point to.

## 2. What is the difference between `git fetch` and `git pull`?

**Answer:**

`git fetch` downloads remote commits, branches, and tags, and updates references like `origin/main`. It does not touch my current branch or working files.

`git pull` does a fetch, then integrates the remote branch into my current branch — usually by merge or rebase.

```bash
git fetch origin
git log --oneline --left-right HEAD...origin/main
git diff HEAD..origin/main
git merge origin/main
```

I prefer fetch when I want to see what changed before integrating it, especially on an important branch. On my own private feature branch, I use `git pull --rebase` when team policy allows it.

Before pulling, I check `git status` and commit or stash any local work, so the pull doesn't mix unrelated changes together.

## 3. How do you resolve merge conflicts?

**Answer:**

First, I figure out why the two branches changed the same lines. I don't just pick "ours" or "theirs" blindly. My approach:

1. Run `git status` to list conflicted files.
2. Open each file and review the `<<<<<<<`, `=======`, and `>>>>>>>` sections.
3. Talk to the other author if the business logic isn't clear.
4. Edit the file into the correct combined result and remove the markers.
5. Run formatters, unit tests, builds, and any relevant integration tests.
6. Stage the resolved files and continue the merge or rebase.

```bash
git status
git diff --name-only --diff-filter=U
git add src/service.py
git commit                 # merge
# or: git rebase --continue
```

If the resolution starts to feel unsafe, I run `git merge --abort` or `git rebase --abort`, go back to the original state, and try again after getting clarity. I also compare the final diff against both parent branches, so I don't accidentally drop a valid change.

## 4. You committed sensitive information to Git. How do you remove it from history?

**Answer:**

The first thing I do is revoke or rotate the secret. Removing it from Git doesn't make an exposed password or token safe, because clones, caches, logs, and forks may already have a copy of it.

Then I:

1. Remove the secret from the current code and replace it with a reference to a secret manager.
2. Use `git filter-repo` to rewrite every affected commit.
3. Coordinate a force push, since this changes the commit IDs.
4. Ask team members to re-clone the repository or carefully reset their branches.
5. Clear CI artifacts and caches where possible, and review audit logs.

```bash
git filter-repo --path config/credentials.env --invert-paths
git push --force --all origin
git push --force --tags origin
```

I use `--force-with-lease` where I can, but a full history cleanup sometimes needs a coordinated force update instead. To prevent this from happening again: pre-commit secret scanning, server-side scanning, protected branches, short-lived credentials, and never storing secrets in a tracked `.env` file.

## 5. A team member deleted a critical Git branch. How do you recover it?

**Answer:**

Deleting a branch normally only deletes the pointer, not the commits — not right away. So I start by finding the last good commit, from a pull request, a pipeline build, a release tag, another developer's clone, or the reflog.

```bash
git reflog --all
git log --all --decorate --oneline
git branch release/2.4 <commit-sha>
git push origin release/2.4
```

Before pushing, I compare the recovered commit against the last deployed build and ask the branch owner to confirm it's the right one. Then I restore branch protection and build-validation rules, since recreating a branch doesn't automatically bring those settings back.

I avoid running garbage collection or cleanup commands until the recovery is done.

## 6. How do you generate a GitHub token?

**Answer:**

For automation, I prefer GitHub Apps or OpenID Connect, because they give short-lived credentials scoped to only what's needed. If a personal access token is required instead, I create a fine-grained token in GitHub settings, select only the repositories it needs, grant the minimum permissions, and set a short expiration date.

I store the token in a CI secret store or an OS credential manager — never in source code or command history. I test one operation that should work and one that should be denied, to prove the permissions are as tight as they should be. I also record who owns the token and when it expires, and set up rotation alerts.

If a token leaks, I revoke it right away, review GitHub's audit and access logs, rotate any downstream credentials it could have reached, remove the value from history and pipeline output, and investigate how it leaked.

## 7. Explain the Gitflow branching strategy.

**Answer:**

Gitflow uses two long-lived branches: `main` and `develop`. Feature branches start from `develop`. A release branch stabilizes a planned version. When a release is done, it merges into both `main` and `develop`. Urgent production fixes get their own hotfix branches, started from `main`.

```text
main ────────────────●────────────●
                     \ hotfix     /
develop ──●──●──●────●───────────●
           \ feature / \ release /
```

It gives you explicit control over releases, which suits products with scheduled versions or several supported releases at once. The downside is extra merge overhead and branches that drift apart the longer they stay open.

For teams delivering continuously, trunk-based development with short feature branches and feature flags is usually simpler. I pick a strategy based on release frequency, regulatory requirements, team size, and how long releases need to be supported — not by defaulting to Gitflow.

## 8. What is the difference between GitHub, Azure Repos, and GitLab?

**Answer:**

All three host Git repositories and support pull or merge requests, permissions, branch protection, and integrations.

- **GitHub:** a strong public and open-source ecosystem, plus GitHub Actions, Codespaces, GitHub Apps, and built-in security tooling.
- **Azure Repos:** tightly integrated with Azure Boards, Azure Pipelines, Test Plans, and enterprise Microsoft environments.
- **GitLab:** repository management, CI/CD, security scanning, package management, and planning tools all in one platform, with a self-managed option too.

When comparing them, I look at identity integration, compliance needs, how runners work, network placement, availability, cost, migration effort, developer experience, and the existing toolchain. Repository hosting alone is rarely the deciding factor — CI/CD, security, governance, and who owns operations usually matter more.

## 9. What is a pull request or merge request?

**Answer:**

A pull request (on GitHub or Azure Repos) or a merge request (on GitLab) proposes merging one branch into another. It's really a collaboration and quality-control step, not just a Git operation.

A good one explains the problem, the solution, the risk, and includes test evidence, screenshots or plan output where relevant, deployment notes, and how to roll back if needed. Automated checks should validate the build, tests, security, linting, and policy.

Reviewers check for correctness, maintainability, security, how it behaves in operation, and any side effects.

Once feedback is resolved and checks pass, the change gets merged using whatever strategy the team has chosen. The linked issue, reviewers, checks, comments, and final commit together form an audit trail.

## 10. How do you protect the main branch?

**Answer:**

I block direct pushes and require everyone to go through a pull request. The typical controls are:

- A minimum number of the right reviewers, including CODEOWNERS for sensitive paths.
- Passing build, test, security, and policy checks.
- All review comments resolved.
- The branch up to date, or a merge queue in place.
- Signed commits where required.
- Force pushes, branch deletion, and policy bypasses restricted.
- A separate, audited emergency-access path with a post-incident review.

I test the policy with a normal developer account to confirm that direct pushes and unauthorized bypasses actually fail. I also protect pipeline configuration and infrastructure directories, since changing a workflow file can be just as powerful as changing application code.

## 11. What is the difference between merge, squash, and rebase?

**Answer:**

- **Merge** combines two histories and usually adds a merge commit. It keeps the real branch structure, but the graph can get noisy.
- **Squash merge** combines all the feature branch's commits into a single new commit on the target branch. This keeps `main` simple, but the individual feature-branch commits no longer show up in history.
- **Rebase** replays your commits onto a new base, giving a straight, linear history. Because this changes commit IDs, I avoid rebasing a branch that others are already working from.

For short feature branches, I often squash a string of small "fix" commits into one clean, reviewed change. For a release or integration branch where the individual commits matter, a regular merge is usually better.

If I rebase a branch I own, I push with `--force-with-lease`, never a plain `--force`.

## 12. How do you handle release tags?

**Answer:**

I create an annotated tag on the exact reviewed commit that was used to build the release. Once created, a tag like this should never change — that's what makes it trustworthy as a release marker. Semantic versioning, like `v2.4.1`, makes compatibility clear at a glance.

```bash
git tag -a v2.4.1 -m "Release 2.4.1"
git push origin v2.4.1
git show v2.4.1
```

CI builds a versioned artifact or image and records the commit SHA, tag, checksums, and release notes. Promoting to production reuses that same artifact rather than rebuilding from a branch that keeps moving.

I restrict who can create or delete tags, sign tags when required, and never quietly move a published release tag. If something needs fixing, it gets a new version instead.

## 13. How do you find merge conflicts before completing a merge?

**Answer:**

I update my remote references and try the integration locally, either directly or in a temporary branch.

```bash
git fetch origin
git switch feature/order-api
git rebase origin/main
# or: git merge --no-commit --no-ff origin/main
git diff --name-only --diff-filter=U
```

If I just want to check without changing anything, `git merge-tree` can show what a merge would produce without touching the working tree. CI should also test the actual proposed merge commit, because two branches can merge cleanly at the text level and still break the build or the behavior.

After resolving conflicts, I run the full relevant test set and review the combined diff.

## 14. What branching strategy would you recommend for a team of more than 20 developers?

**Answer:**

First, I'd ask about release frequency, how many versions need support at once, regulatory approvals, repository ownership, and whether incomplete work can just hide behind a feature flag. Team size alone doesn't decide the strategy.

For frequent delivery, I prefer trunk-based development: short-lived branches, small pull requests, a protected `main`, mandatory automated checks, a merge queue, and feature flags. This cuts down long-running conflicts and integration risk.

For scheduled releases or several supported versions at once, I add release branches with clear owners and a limited lifespan.

I track lead time, how long pull requests stay open, change-failure rate, how often conflicts happen, and rollback time. If branches sit open for weeks, that's a sign the process itself is creating integration risk.

CODEOWNERS, component-level tests, and clearly defined repository boundaries help a large team work independently without weakening code review.

## 15. How do you undo a bad commit that has already been pushed to the protected main branch?

**Answer:**

On a shared, protected branch, I create a new revert commit rather than rewriting history that's already been published:

```bash
git switch main
git pull --ff-only
git revert <bad-commit-sha>
git push origin main
```

For a merge commit, I identify the correct mainline parent and use `git revert -m 1 <merge-sha>`, then check the resulting diff carefully. If several dependent commits are involved, I revert them in a controlled order, or revert the merge through a pull request instead.

I run tests and follow the normal review and deployment process, and pause or roll back the affected release if production is actually being impacted.

I avoid `reset --hard` plus a force push on a shared main branch, since that rewrites history and disrupts everyone else's clone. A leaked secret is a different case: I revoke it immediately, and may still need to coordinate a history rewrite, because a revert alone leaves the value sitting in history.

## 16. What branching strategy keeps releases clean, and how do you handle a production hotfix?

**Answer:**

For frequent delivery, I prefer protected trunk-based development: short-lived branches, small pull requests, mandatory checks, and feature flags. I only create a release branch when a supported release needs to be stabilized. New feature work keeps going on `main`, while the release branch accepts only approved fixes.

For a hotfix, I branch from the exact production tag, make the smallest change that fixes the issue, get it reviewed, build a new version that won't change once created, and deploy it through the emergency pipeline — which is still audited.

Then I merge or cherry-pick the fix back into `main` and any release branches still being supported, so it isn't lost in the next release.

I tag the fixed release and document the incident.

The branch itself doesn't guarantee stability — the controls around it do. I require reproducible builds, tests, security checks, code owners, traceable approvals, and a verified rollback path. I also delete or close stale release branches so they don't drift out of sync.

## 17. How should Dev, QA, UAT, and Production be represented in Git?

**Answer:**

I avoid permanent environment branches that hold different versions of the application code, because merging between them creates drift and makes it unclear what's actually in a release. Application code should normally live on one protected main branch, with release tags that don't change once created.

The same built artifact then gets promoted through Dev, QA, UAT, and Production — nothing gets rebuilt along the way.

Environment-specific configuration can live in clearly separated directories or repositories, with protected pull requests and environment owners. Promoting to the next environment just changes the image digest or chart version there — it doesn't rebuild the source.

Secrets stay as external references, never checked into the repo.

If an organization insists on environment branches, I define one-way promotion, automated comparison between environments, branch protection, and rules that block direct commits to production. But I'd also explain the drift risk this creates and push toward artifact-based promotion instead.

## 18. `git pull` says "not a git repository." How do you troubleshoot?

**Answer:**

I start by running `pwd` and `git rev-parse --show-toplevel`. This error usually means the command ran outside the cloned directory, the `.git` folder is missing, or a script changed the working directory without me noticing. I `cd` to the repository root and confirm with `git status` and `git remote -v`.

If `.git` was deleted or the checkout is corrupted, I save any uncommitted files first, clone a fresh copy, restore just the work I need, then pull the intended branch. I don't run `git init` inside an unfamiliar directory — that creates unrelated history and can hide what actually went wrong.
