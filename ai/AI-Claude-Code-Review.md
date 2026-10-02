# How Claude Code Review Works (Explained Simply)

This is how I'd explain our automated "Claude reviews every pull request" setup to an interviewer — what it is, why we built it this way, and how it works end to end.

## The one-line pitch

Every time someone opens a pull request in one of our ~28 repositories, an AI (Claude) automatically reads the code changes and leaves review comments directly on the PR — checking for bugs, security issues, hardcoded secrets, and bad practices — before a human ever looks at it.

## Why we built it this way (the core idea: don't repeat yourself)

We have many repositories: Terraform/OpenTofu infrastructure, Python data pipelines, React frontends, backend APIs, Databricks pipelines, etc. Two bad options were on the table:

1. Copy-paste the same GitHub Actions workflow into every repo — a maintenance nightmare, because fixing one bug means editing 28 files.
2. Write one custom review workflow per repo — too slow to maintain and inconsistent.

Instead, we centralized everything in **one shared repository** called `cicd-workflows`, and every other repo just "calls" it. This is the same idea as a shared library in software — write the logic once, reuse it everywhere.

## The pieces, end to end

### 1. The trigger — a PR event in the application repo

Each application repository (e.g. `infrastructure`, `CMM`, `tenetic-v3-agent`) has a tiny file:
`.github/workflows/claude-code-review.yml`

It listens for pull request events — opened, updated (`synchronize`), marked ready for review, or reopened — and skips draft PRs. It doesn't contain any review logic itself. It just says: "when a PR happens, go run the shared workflow in `tenetic/cicd-workflows`, and pass it my repo name."

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  review:
    if: ${{ !github.event.pull_request.draft }}
    uses: tenetic/cicd-workflows/.github/workflows/claude-code-review.yml@main
    with:
      repository-name: ${{ github.event.repository.name }}
    secrets:
      ANTHROPIC_API_KEY_03: ${{ secrets.ANTHROPIC_API_KEY_03 }}
```

This is a **reusable GitHub Actions workflow** — think of it like calling a function and passing arguments (the repo name and an API key secret).

### 2. The shared workflow — checkout + build a prompt + call Claude

Inside `cicd-workflows/.github/workflows/claude-code-review.yml`, three things happen:

1. **Checkout the code** — pull down the PR's files so there's something to review.
2. **Resolve the review prompt** — a step figures out exactly what instructions to give Claude for this specific repository (details below).
3. **Run `anthropics/claude-code-action`** — the official GitHub Action that runs Claude Code inside the pipeline, hands it the prompt, and restricts what tools it's allowed to use:
   - It can post inline PR comments (`mcp__github_inline_comment__create_inline_comment`)
   - It can run a few read-only `gh` CLI commands (`gh pr comment`, `gh pr diff`, `gh pr view`)
   - It is **not** given permission to approve, merge, or change PR metadata — it can only leave comments.

### 3. The prompt system — one default + swappable "role" modules

This is the clever part, and the part I'd highlight most in an interview: **the review instructions are modular, like a config file, not hardcoded.**

- `prompts/claude-code-review/default.md` — the base instructions every repo gets: focus on real bugs, security risks, maintainability, CI/CD safety, doc accuracy; specifically flag hardcoded secrets/credentials/tokens; only comment, never approve or merge.
- `prompts/claude-code-review/roles/*.md` — specialized reviewer "hats," each written like "Act as a senior AWS security reviewer..." Examples: `aws.md`, `python.md`, `opentofu.md`, `databricks.md`, `sensitive-data.md`, `web-applications.md`.
- `prompts/claude-code-review/repositories/<repo-name>.txt` — a simple text file per repo listing which role files apply. For example, the `infrastructure` repo's mapping file lists `opentofu.md`, `aws.md`, `github.md`, `shell.md`, `identity-and-saas.md`, `data-platforms.md` — because that repo is all Terraform/AWS.

A small bash script (`resolve-claude-code-review-prompt.sh`) does the assembly at run time:
1. Start with `default.md`.
2. Look up the calling repo's `.txt` mapping file.
3. Append each listed role file's content.
4. Replace placeholders like `{{REPOSITORY}}`, `{{REPOSITORY_NAME}}`, `{{PR_NUMBER}}` with real values from the current PR.
5. Fail loudly (with a clear error) if any expected file is missing — so a typo in a repo mapping can't silently produce an empty or broken review.

If a repo has no mapping file at all, it just gets the generic `default.md` review — so onboarding a new repo requires zero extra work, and you only add specialization when you need it.

### 4. Claude does the review

`anthropic/claude-code-action` runs Claude Code with that assembled prompt. Claude reads the PR diff, applies whatever combination of general + role-specific instructions it was given, and:
- Leaves inline comments on specific lines when it finds real issues (bugs, security holes, hardcoded secrets, bad IAM permissions, missing encryption, etc.)
- Leaves a short "looks safe" note if there's nothing to flag
- Never modifies the PR itself — strictly advisory

### 5. Rollout

This same pattern (one caller-workflow file per repo, pointing at the shared workflow) has been copy-pasted into ~28 repositories — infra, data pipelines, frontends, backend APIs — tracked in a single checklist in the `cicd-workflows` docs. Adding Claude review to a new repo is a 5-line YAML file plus, optionally, a one-line-per-role `.txt` mapping file.

## How I'd summarize it in one breath (interview soundbite)

> "We didn't want to hand-write a review workflow per repo, so we built one reusable GitHub Actions workflow in a central `cicd-workflows` repo. Every app repo just calls it on every PR, passing its own name. That shared workflow assembles a review prompt out of a common base instructions file plus optional per-repo 'role' modules — like an AWS security reviewer persona for infra repos, or a Python reviewer persona for pipeline repos — then hands that prompt to Claude Code via the official `claude-code-action`, scoped so it can only leave PR comments, never approve or merge. It's basically a config-driven, pluggable AI review layer sitting in front of human review."

## Key takeaways / design principles worth naming

- **DRY (Don't Repeat Yourself):** one shared workflow instead of 28 copies.
- **Composable prompts:** default + role modules + repo mapping, so specialization doesn't mean duplication.
- **Least privilege:** Claude's GitHub token scope only allows commenting — it structurally cannot approve or merge a PR.
- **Fail-fast:** the prompt-resolution script errors out clearly instead of silently reviewing with an empty or wrong prompt.
- **Cheap to extend:** onboarding a new repo, or adding a new specialization, is a small config change, not new code.
