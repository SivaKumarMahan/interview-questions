# Git: Clone vs Fork, the .git Folder, and History Cleanup

> The difference between cloning and forking, what is inside the `.git` folder, what to do if it is lost, and how to combine several commits into one.

## Key Concepts

### What lives in `.git`

| Path | Contents |
| --- | --- |
| `objects/` | All content: blobs (files), trees (folders), commits and tags, compressed and named by hash |
| `refs/heads/`, `refs/remotes/`, `refs/tags/` | Branch, remote-tracking branch and tag pointers |
| `packed-refs` | Many refs packed into one file |
| `HEAD` | The current branch, for example `ref: refs/heads/main` |
| `config` | Repository settings, remotes (`origin`) and branch tracking |
| `index` | The staging area |
| `logs/` | The reflog: where `HEAD` and each branch pointed over time |
| `hooks/` | Local hook scripts such as `pre-commit` (not shared through push) |

The working files you edit are only a checkout of one commit. All history is inside `.git`.

## Interview Questions

<details><summary>Q1. [Basic] What is the difference between <code>git clone</code> and a fork?</summary>

**Answer:**

| | Clone | Fork |
| --- | --- | --- |
| What it is | A Git command that copies a repository, with full history, to your machine | A server-side copy of a repository under your account or organization (GitHub, GitLab, Azure Repos) |
| Where | Local | On the hosting platform |
| Typical use | Working on a repository you have write access to | Contributing to a repository you cannot push to, such as open source |
| Getting changes back | `git push` to a branch, then a pull request | Push to your fork, then a pull request to the original ("upstream") |

A common fork workflow:

```bash
git clone git@github.com:me/project.git        # clone your fork
git remote add upstream git@github.com:org/project.git
git fetch upstream
git rebase upstream/main                      # keep your fork current
```

Inside a company, teams usually work with branches in one shared repository rather than forks.

</details>

<details><summary>Q2. [Basic] What is the <code>.git</code> folder?</summary>

**Answer:**

It is the repository itself. It holds every commit, file version, branch, tag, the staging area, the configuration (including remotes) and the reflog. The project files next to it are just the checked-out version of one commit. Deleting `.git` turns the folder into plain files with no history and no link to the remote. Hooks in `.git/hooks` are local only, which is why teams share hooks through tools such as `pre-commit` or Husky.

</details>

<details><summary>Q3. [Intermediate] You lost the <code>.git</code> folder. How do you recover?</summary>

**Answer:**

Local history cannot be rebuilt from the working files alone, but anything that was **pushed** still exists on the remote.

**Easiest, if the code was pushed:** clone again and copy over any uncommitted changes.

```bash
git clone git@github.com:org/app.git app-fresh
rsync -av --exclude .git ./app-old/ ./app-fresh/   # bring over local edits
cd app-fresh && git status && git diff             # review what changed
```

**Reconnect the existing folder in place:**

```bash
cd app-old
git init
git remote add origin git@github.com:org/app.git
git fetch origin
git reset origin/main          # mixed reset: keeps your files, points the branch at the remote history
git status                     # local edits now show as changes
```

What is lost for good: commits that were never pushed, local-only branches and stashes, and the reflog. That is why you push work-in-progress branches often.

</details>

<details><summary>Q4. [Intermediate] How do you combine several commits into one?</summary>

**Answer:**

**Interactive rebase** (for the last `n` commits on your own branch):

```bash
git rebase -i HEAD~3
```

In the editor, keep `pick` on the first commit and change the others to `squash` (or `s`, keep their messages) or `fixup` (or `f`, discard their messages):

```text
pick   a1b2c3 Add payment API
squash d4e5f6 Fix tests
fixup  g7h8i9 Typo
```

Save, edit the final message, then update the remote branch safely:

```bash
git push --force-with-lease
```

**Alternatives:**

- `git reset --soft HEAD~3 && git commit -m "Add payment API"` squashes without the editor.
- **Squash merge** in the pull request ("Squash and merge" on GitHub, "Squash commit" in Azure Repos) keeps `main` clean without rewriting the feature branch by hand.

Only rewrite history on branches nobody else is building on. Never force-push to `main`. See [merge, squash and rebase](03-pull-requests-merging-and-conflicts.md) for the comparison.

</details>
