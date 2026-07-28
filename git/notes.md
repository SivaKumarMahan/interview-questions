# Git Daily Workflow Reference

## Clone and inspect

```bash
git clone <repository-url>
cd <repository>
git remote -v
git status
git log --oneline --decorate --graph --all
```

## Create a branch and commit a focused change

```bash
git switch -c feature/<name>
git add <specific-files>
git diff --cached
git commit -m "Explain the completed change"
git push --set-upstream origin feature/<name>
```

## Update safely before opening or completing a pull request

```bash
git fetch origin
git rebase origin/main
# Resolve and stage each conflict, then:
git rebase --continue
git push --force-with-lease
```

I use `--force-with-lease` only on my reviewed feature branch because it refuses to overwrite remote work I have not fetched. Shared and protected branches should reject force pushes.

Before committing, I review the staged diff and run secret scanning so credentials never enter history.

## Recovery commands

```bash
git reflog                         # find a lost local commit
git switch -c recovered <sha>      # preserve it on a new branch
git revert <sha>                   # safely undo a shared commit
git restore --staged <file>        # unstage without deleting work
```

`git reset` rewrites the current branch and can discard local work depending on mode, while `git revert` creates a new inverse commit and is normally safer after a commit has been shared.
