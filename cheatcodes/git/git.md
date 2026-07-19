# Git Cheatcode

## Setup and inspect

```bash
git config --global user.name '<name>'
git config --global user.email '<email>'
git status
git remote -v
git log --oneline --graph --decorate --all
git diff
git diff --staged
git show <commit>
git blame <file>
```

## Branch workflow

```bash
git switch main
git pull --ff-only
git switch -c <feature-branch>
git add -p
git commit -m '<clear message>'
git push -u origin <feature-branch>
```

## Recovery and integration

```bash
git fetch --all --prune
git rebase origin/main
git merge <branch>
git cherry-pick <commit>
git revert <published-commit>
git reflog
git restore <file>
git restore --staged <file>
git stash push -m '<reason>'
git stash list
git stash pop
```

Do not use `reset --hard`, `clean -fd`, or force push as routine cleanup. Inspect targets first. For an owned branch use `git push --force-with-lease`, never a blind force push. Revoke committed secrets before any history cleanup.

## Tags

```bash
git tag -s <version> -m '<release>'
git push origin <version>
```
