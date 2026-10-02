# Git: Recovery and Troubleshooting

> Undoing pushed commits, recovering deleted branches, purging secrets from history, and fixing common Git errors.

## Key Concepts

### Recovery commands

```bash
git reflog                         # find a lost local commit
git switch -c recovered <sha>      # preserve it on a new branch
git revert <sha>                   # safely undo a shared commit
git restore --staged <file>        # unstage without deleting work
```

`git reset` rewrites the current branch. Depending on the mode used, it can discard local work. `git revert` creates a new commit that undoes an earlier one instead. Revert is normally safer once a commit has been shared with others.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you undo a bad commit that has already been pushed to the protected main branch?</summary>

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

</details>

<details><summary>Q2. [Intermediate] A team member deleted a critical Git branch. How do you recover it?</summary>

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

</details>

<details><summary>Q3. [Advanced] You committed sensitive information to Git. How do you remove it from history?</summary>

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

</details>

<details><summary>Q4. [Basic] <code>git pull</code> says "not a git repository." How do you troubleshoot?</summary>

**Answer:**

I start by running `pwd` and `git rev-parse --show-toplevel`. This error usually means the command ran outside the cloned directory, the `.git` folder is missing, or a script changed the working directory without me noticing. I `cd` to the repository root and confirm with `git status` and `git remote -v`.

If `.git` was deleted or the checkout is corrupted, I save any uncommitted files first, clone a fresh copy, restore just the work I need, then pull the intended branch. I don't run `git init` inside an unfamiliar directory — that creates unrelated history and can hide what actually went wrong.

</details>
