# Git Interview Summary

## Core Concepts

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

## Typical Reviewed Flow

1. Update local `main`.
2. Create a short-lived branch.
3. Make small, focused commits.
4. Push the branch.
5. Open a pull request with tests and a review.
6. Merge through protected branch controls.
7. Tag or promote a build that will not change after it is created.

Use `git switch` and `git restore` for clear branch and file operations. Use `git revert` to undo a commit that has already been shared, rather than rewriting history. Only rebase or force-push a branch you own, and use `--force-with-lease` instead of a plain force push.

## Git and DevOps

Git supports DevOps in three ways:

- It triggers automated build, test, and scan jobs when code changes.
- It versions infrastructure and pipeline code the same way it versions application code.
- It records deployment configuration, so changes to what gets deployed are tracked too.

CI publishes a build artifact that does not change once it is created. CD then promotes that same artifact through Development, QA, Staging, and Production. Monitoring and rollback always refer back to the same commit or image digest, so everyone knows exactly what is running where.

## Best Practices

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
