# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Git & Branching Strategy

### 5.1 What branching strategy do you follow / recommend for a 20+ dev team? (justify)

Here are the common options and when each one makes sense:

- **Trunk-based development (recommended for large, fast-moving teams):** everyone commits to short-lived branches and merges to `main` quickly, within a day or two. Unfinished work stays hidden behind feature flags instead of a long-lived branch. This needs strong CI and good test coverage. I recommend it because it avoids messy merges and long branch divergence, and it scales well with many contributors.
- **GitHub Flow:** `main` plus short-lived feature branches, a pull request, then deploy. Simple, and works well for web apps deployed continuously.
- **GitFlow:** uses `main`, `develop`, `feature/*`, `release/*`, and `hotfix/*` branches. Good for scheduled releases or versioned products, but it is heavy and slow for continuous delivery.

For a 20+ dev team doing continuous delivery, I recommend trunk-based development with feature flags, pull request reviews, and strong CI with branch protection. It keeps integration continuous and avoids the long-lived branches that GitFlow tends to create.

### 5.2 How do you find / handle merge conflicts?

```bash
git merge main            # or git rebase main
# Git marks conflicts:
git status                # shows "both modified" files
grep -rn '<<<<<<<' .      # find conflict markers
```

I resolve conflicts by editing the `<<<<<<<` / `=======` / `>>>>>>>` sections to the correct result, then running `git add <file>` and `git commit` (or `git rebase --continue`). A merge tool such as `git mergetool` or VS Code makes this easier to see clearly.

To prevent conflicts in the first place: keep branches short-lived, pull or rebase often, and keep changes small and focused.
---
