# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Git & Branching Strategy

### 5.1 What branching strategy do you follow / recommend for a 20+ dev team? (justify)

Common options and when to use them:
- **Trunk-Based Development (recommended for large, fast-moving teams):** everyone commits to short-lived branches merged to `main` quickly (≤1–2 days), behind **feature flags**. Requires strong CI and test coverage. **Justification:** minimizes merge hell and long-lived divergence, enables continuous delivery, scales well with many contributors.
- **GitHub Flow:** `main` + short-lived feature branches + PR + deploy. Simple; good for continuous deployment web apps.
- **GitFlow:** `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`. Good for **scheduled releases / versioned products** but heavy and slow for CD.
For a 20+ dev team doing continuous delivery, I recommend **trunk-based with feature flags + PR reviews + strong CI/branch protection**, because it keeps integration continuous and avoids the painful long-lived branches GitFlow encourages.

### 5.2 How do you find / handle merge conflicts?
```bash
git merge main            # or git rebase main
# Git marks conflicts:
git status                # shows "both modified" files
grep -rn '<<<<<<<' .      # find conflict markers
```
Resolve by editing the `<<<<<<< / ======= / >>>>>>>` sections to the correct result, then `git add <file>` and `git commit` (or `git rebase --continue`). Use a merge tool (`git mergetool`, VS Code) for clarity. **Prevent** them: keep branches short-lived, pull/rebase frequently, keep changes small and well-scoped.
---
