# Git: Fundamentals and Daily Workflow

> Core Git concepts, the everyday clone-branch-commit-update flow, remotes, fetch vs pull, hosting platforms, and access tokens.

## Key Concepts

### Core Concepts

Git stores project history as **commits**.

| Term | What it means |
| --- | --- |
| Branch | A movable pointer to a commit |
| Remote | Another copy of the repository, usually on a server |
| Clone | Creates a local copy of a remote repository |
| Fetch | Downloads new commits and branches from a remote, without touching your files |
| Pull | A fetch followed by merging or rebasing the result into your branch |
| Push | Sends your commits to a remote |
| Merge | Combines two branch histories |
| Rebase | Replays your commits on top of a new base, keeping history linear |
| Stash | Temporarily sets aside uncommitted work |
| Tag | Marks a specific commit, usually a release |

### Typical Reviewed Flow

1. Update local `main`.
2. Create a short-lived branch.
3. Make small, focused commits.
4. Push the branch.
5. Open a pull request with tests and a review.
6. Merge through protected branch controls.
7. Tag or promote a build that will not change after it is created.

Use `git switch` and `git restore` for clear branch and file operations. Use `git revert` to undo a commit that has already been shared, rather than rewriting history. Only rebase or force-push a branch you own, and use `--force-with-lease` instead of a plain force push.

### Git and DevOps

Git supports DevOps in three ways:

- It triggers automated build, test, and scan jobs when code changes.
- It versions infrastructure and pipeline code the same way it versions application code.
- It records deployment configuration, so changes to what gets deployed are tracked too.

CI publishes a build artifact that does not change once it is created. CD then promotes that same artifact through Development, QA, Staging, and Production. Monitoring and rollback always refer back to the same commit or image digest, so everyone knows exactly what is running where.

### Best Practices

- Write clear, focused commit messages.
- Use pull requests and `CODEOWNERS` for review.
- Protect `main` from direct pushes.
- Run secret scanning on every commit.
- Keep a proper `.gitignore`.
- Sign tags and commits where required.
- Clean up merged branches.
- Keep builds reproducible.
- Never make changes directly in production.

If a secret is ever committed, revoke it immediately. Rewriting history alone does not make a leaked secret safe again.

### Clone and inspect

```bash
git clone <repository-url>
cd <repository>
git remote -v
git status
git log --oneline --decorate --graph --all
```

### Create a branch and commit a focused change

```bash
git switch -c feature/<name>
git add <specific-files>
git diff --cached
git commit -m "Explain the completed change"
git push --set-upstream origin feature/<name>
```

### Update safely before opening or completing a pull request

```bash
git fetch origin
git rebase origin/main
# Resolve and stage each conflict, then:
git rebase --continue
git push --force-with-lease
```

I use `--force-with-lease` only on my reviewed feature branch because it refuses to overwrite remote work I have not fetched. Shared and protected branches should reject force pushes.

Before committing, I review the staged diff and run secret scanning so credentials never enter history.

## Interview Questions

<details><summary>Q1. [Basic] What is the difference between <code>origin</code> and <code>upstream</code> remotes?</summary>

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

</details>

<details><summary>Q2. [Basic] What is the difference between <code>git fetch</code> and <code>git pull</code>?</summary>

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

</details>

<details><summary>Q3. [Basic] What is the difference between GitHub, Azure Repos, and GitLab?</summary>

**Answer:**

All three host Git repositories and support pull or merge requests, permissions, branch protection, and integrations.

- **GitHub:** a strong public and open-source ecosystem, plus GitHub Actions, Codespaces, GitHub Apps, and built-in security tooling.
- **Azure Repos:** tightly integrated with Azure Boards, Azure Pipelines, Test Plans, and enterprise Microsoft environments.
- **GitLab:** repository management, CI/CD, security scanning, package management, and planning tools all in one platform, with a self-managed option too.

When comparing them, I look at identity integration, compliance needs, how runners work, network placement, availability, cost, migration effort, developer experience, and the existing toolchain. Repository hosting alone is rarely the deciding factor — CI/CD, security, governance, and who owns operations usually matter more.

</details>

<details><summary>Q4. [Basic] How do you generate a GitHub token?</summary>

**Answer:**

For automation, I prefer GitHub Apps or OpenID Connect, because they give short-lived credentials scoped to only what's needed. If a personal access token is required instead, I create a fine-grained token in GitHub settings, select only the repositories it needs, grant the minimum permissions, and set a short expiration date.

I store the token in a CI secret store or an OS credential manager — never in source code or command history. I test one operation that should work and one that should be denied, to prove the permissions are as tight as they should be. I also record who owns the token and when it expires, and set up rotation alerts.

If a token leaks, I revoke it right away, review GitHub's audit and access logs, rotate any downstream credentials it could have reached, remove the value from history and pipeline output, and investigate how it leaked.

</details>
