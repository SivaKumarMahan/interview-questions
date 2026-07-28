# Git Interview Summary

## Git and DevOps

Git stores project history as **commits**.

A **branch** is a movable reference, a **remote** is another repository location, `clone` creates a local copy, `fetch` downloads references, `pull` combines fetch with integration, `push` publishes commits, `merge` combines histories, `rebase` reapplies commits, `stash` temporarily saves work, and **tags** identify releases.

## Typical reviewed flow

1. Update local `main`
2. Create a short-lived branch
3. Make small commits
4. Push
5. Pull request with tests/review
6. Merge through protected controls
7. Tag or promote an immutable (not changed after creation) artifact

Prefer `git switch`/`git restore` for clear branch/file operations and `git revert` to undo published shared history. Rebase/force-push only on owned branches and use `--force-with-lease`.

## Git and DevOps integration

Git supports DevOps by triggering automated build, test, and scan jobs; versioning infrastructure and pipeline code; and recording deployment configuration. **CI** publishes an immutable artifact, meaning a version that is not changed after creation. **CD** promotes that same artifact through Development, QA, Staging, and Production, while monitoring and rollback refer to the same commit or digest.

## Best practices

- Clear commits
- Pull requests/`CODEOWNERS`
- Protected `main`
- Secret scanning
- `.gitignore`
- Signed tags/commits where required
- Branch cleanup
- Reproducible builds
- No direct production changes

A committed secret must be revoked immediately; rewriting history alone does **not** make it safe.
