# Git: Pull Requests, Merging, and Conflicts

> Pull/merge requests, protecting main, merge vs squash vs rebase, and finding and resolving merge conflicts.

## Interview Questions

<details><summary>Q1. [Basic] What is a pull request or merge request?</summary>

**Answer:**

A pull request (on GitHub or Azure Repos) or a merge request (on GitLab) proposes merging one branch into another. It's really a collaboration and quality-control step, not just a Git operation.

A good one explains the problem, the solution, the risk, and includes test evidence, screenshots or plan output where relevant, deployment notes, and how to roll back if needed. Automated checks should validate the build, tests, security, linting, and policy.

Reviewers check for correctness, maintainability, security, how it behaves in operation, and any side effects.

Once feedback is resolved and checks pass, the change gets merged using whatever strategy the team has chosen. The linked issue, reviewers, checks, comments, and final commit together form an audit trail.

</details>

<details><summary>Q2. [Basic] How do you protect the main branch?</summary>

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

</details>

<details><summary>Q3. [Basic] What is the difference between merge, squash, and rebase?</summary>

**Answer:**

- **Merge** combines two histories and usually adds a merge commit. It keeps the real branch structure, but the graph can get noisy.
- **Squash merge** combines all the feature branch's commits into a single new commit on the target branch. This keeps `main` simple, but the individual feature-branch commits no longer show up in history.
- **Rebase** replays your commits onto a new base, giving a straight, linear history. Because this changes commit IDs, I avoid rebasing a branch that others are already working from.

For short feature branches, I often squash a string of small "fix" commits into one clean, reviewed change. For a release or integration branch where the individual commits matter, a regular merge is usually better.

If I rebase a branch I own, I push with `--force-with-lease`, never a plain `--force`.

</details>

<details><summary>Q4. [Basic] How do you resolve merge conflicts?</summary>

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

</details>

<details><summary>Q5. [Intermediate] How do you find merge conflicts before completing a merge?</summary>

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

</details>

<details><summary>Q6. [Basic] How do you find / handle merge conflicts? <em>(asked in interview round)</em></summary>

```bash
git merge main            # or git rebase main
# Git marks conflicts:
git status                # shows "both modified" files
grep -rn '<<<<<<<' .      # find conflict markers
```

I resolve conflicts by editing the `<<<<<<<` / `=======` / `>>>>>>>` sections to the correct result, then running `git add <file>` and `git commit` (or `git rebase --continue`). A merge tool such as `git mergetool` or VS Code makes this easier to see clearly.

To prevent conflicts in the first place: keep branches short-lived, pull or rebase often, and keep changes small and focused.

</details>
