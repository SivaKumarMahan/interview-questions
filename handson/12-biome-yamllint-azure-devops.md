# Hands-on 12: Code Quality Gates with Biome and yamllint in Azure DevOps

> Add Biome (JavaScript, TypeScript, and React linting and formatting) and yamllint (YAML checks) to an Azure DevOps pipeline, and make the pipeline fail when code quality does not meet the standard.

**Time:** about 45 minutes. **Level:** Basic.

## What you practise

- Installing Biome with a pinned version and creating `biome.json`
- Finding unused imports, formatting problems, and correctness issues
- The difference between `biome check --write` (local fix) and `biome ci` (read-only check for CI)
- Configuring yamllint for pipeline and Kubernetes YAML
- Running both tools as separate pipeline steps that fail the build
- Making the pipeline a required check on pull requests with a branch policy

## Prerequisites

| Item | Purpose |
| --- | --- |
| Node.js 20 and npm | Run Biome locally |
| Python 3 and pip | Run yamllint locally |
| A JavaScript, TypeScript, or React project in Azure Repos | Code to check |
| Azure DevOps project | Pipeline and branch policy |

## Flow

```text
Developer
   |  npx biome check --write .   (fix locally, optional pre-commit hook)
   |  git push / open pull request
   v
Azure DevOps pipeline (build validation on the PR)
   |
   |-- npm ci                         (exact Biome version from the lock file)
   |-- npx biome ci .                 (read-only: lint + format check) --> fail on issues
   |-- pip install yamllint
   '-- yamllint -f parsable .         (YAML syntax and style)          --> fail on errors
   |
   v
Pull request can be completed only if the pipeline passes
```

## Steps

### 1. Install Biome with an exact version

In the project root:

```bash
npm install --save-dev --save-exact @biomejs/biome
npx @biomejs/biome init
```

- `--save-exact` writes an exact version (for example `"2.1.2"`, not `"^2.1.2"`) in `package.json`. Every developer and the pipeline then use the same Biome version, so they get the same results.
- `init` creates a `biome.json` file.
- After installing, `npx biome` runs the local binary.

### 2. Configure `biome.json`

Keep the config small. A minimal example for Biome 2.x:

```json
{
  "$schema": "./node_modules/@biomejs/biome/configuration_schema.json",
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  },
  "files": {
    "includes": ["**", "!**/dist", "!**/node_modules"]
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "correctness": {
        "noUnusedImports": "error",
        "noUnusedVariables": "error"
      }
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single"
    }
  }
}
```

- `vcs.useIgnoreFile` makes Biome skip files listed in `.gitignore`.
- `recommended: true` turns on Biome's recommended rules. The `correctness` block makes unused imports and variables errors, so they fail the build.
- Configuration keys can differ between Biome versions. For example, Biome 1.x used `"files": { "ignore": ["dist"] }` instead of `includes`. Use the `$schema` line so your editor shows errors, and check the docs for your installed version. Running `npx biome migrate --write` updates the config after a major upgrade.

### 3. Run Biome locally

```bash
# Show problems only
npx biome check .

# Fix what can be fixed safely: formatting, import sorting, safe lint fixes
npx biome check --write .

# Only format, or only lint
npx biome format --write .
npx biome lint .
```

Example: a file with `import { useEffect, useState } from 'react';` that never uses `useEffect` is reported by `noUnusedImports`, and `check --write` can remove the unused import.

Add scripts to `package.json` so everyone runs the same commands:

```json
{
  "scripts": {
    "check": "biome check --write .",
    "ci:check": "biome ci ."
  }
}
```

### 4. Use `biome ci` in the pipeline, not `check --write`

This is the most important point of this guide.

- `biome check --write` **changes files on the build agent**. Nothing commits those changes back to the repository. The step can pass while the repository still has the same problems.
- `biome ci .` is **read-only**. It runs the formatter check, the linter, and import sorting checks, and it exits with a non-zero code if anything is wrong. The build fails, and the developer fixes the code locally.

So: `--write` belongs on the developer machine and in pre-commit hooks. `biome ci` belongs in the pipeline.

### 5. Install and configure yamllint

```bash
pip install yamllint
yamllint --version
```

`.yamllint` in the repository root:

```yaml
extends: default

ignore: |
  node_modules/
  dist/

rules:
  line-length:
    max: 160
    level: warning
  document-start: disable
  comments:
    min-spaces-from-content: 1
  truthy:
    allowed-values: ['true', 'false']
    check-keys: false
```

- `extends: default` starts from the default rule set.
- `line-length` at 160 (or `line-length: disable`) avoids noise from long scripts and URLs in pipeline files.
- `document-start: disable` stops the warning about a missing `---` at the top of each file.
- `truthy` warns about values like `yes`, `no`, and `on`, which some YAML parsers treat as booleans. `check-keys: false` allows the key `on:` in GitHub Actions workflows. If you lint GitHub workflows with key checking on, add `'on'` to `allowed-values` instead.

Run it:

```bash
yamllint -f parsable .
# or only the pipeline files
yamllint -f parsable azure-pipelines.yml templates/
```

yamllint exits with code 1 when there are errors. Warnings do not fail the run unless you add `--strict`.

### 6. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

steps:
  - task: NodeTool@0
    displayName: Use Node.js 20
    inputs:
      versionSpec: '20.x'

  - script: npm ci
    displayName: Install dependencies (exact Biome version)

  - script: npx biome ci .
    displayName: Biome lint and format check

  - task: UsePythonVersion@0
    displayName: Use Python 3.12
    inputs:
      versionSpec: '3.12'

  - script: pip install yamllint
    displayName: Install yamllint

  - script: yamllint -f parsable .
    displayName: yamllint
```

- Each tool runs as its **own step**, so the run summary shows exactly which check failed.
- A failed step stops the job, and the build is marked as failed.
- To run yamllint even when Biome fails (so developers see both results in one run), add `condition: succeededOrFailed()` to the two yamllint steps.
- For Azure Repos, the `pr:` trigger in YAML is ignored. Pull request runs come from the branch policy in the next step.

### 7. Make it a required check on pull requests

1. Go to **Repos > Branches**, open the menu for `main`, and choose **Branch policies**.
2. Under **Build validation**, click **+**, select this pipeline, set **Trigger** to Automatic, **Policy requirement** to Required, and choose a build expiration.
3. Save.

Now every pull request into `main` runs the pipeline, and the pull request cannot be completed until Biome and yamllint pass.

### 8. Optional: a pre-commit hook

Catching problems before the push saves pipeline time. With Husky and lint-staged:

```bash
npm install --save-dev husky lint-staged
npx husky init
echo "npx lint-staged" > .husky/pre-commit
```

In `package.json`:

```json
{
  "lint-staged": {
    "*.{js,jsx,ts,tsx,json}": "biome check --write --no-errors-on-unmatched"
  }
}
```

Biome also has `--staged` and `--changed` options for checking only changed files. The pipeline still runs `biome ci .` on everything, because hooks can be skipped.

### 9. Verify

Make a deliberate mistake on a branch:

```jsx
// src/App.jsx
import { useEffect, useState } from 'react';   // useEffect is not used

export default function App() {
    const [count, setCount] = useState(0)        // 4-space indent, no semicolon
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

And a YAML problem:

```yaml
# azure-pipelines.yml - duplicated key
pool:
  vmImage: ubuntu-latest
pool:
  vmImage: windows-latest
```

Open a pull request. Expected:

- The **Biome lint and format check** step fails and lists the unused import (`noUnusedImports`) and the formatting difference.
- After fixing Biome, the **yamllint** step fails with a `key-duplicates` error, in the format `file:line:column: [error] ... (key-duplicates)`.
- The pull request shows the build validation as failed and cannot be completed.

Fix locally with `npx biome check --write .`, remove the duplicate key, push again, and the check turns green.

## Important points

- Pin Biome with `--save-exact` and install with `npm ci`, so local and CI results match.
- `biome check --write` fixes code locally. `biome ci` checks code in CI. Do not use `--write` as a CI gate.
- Biome replaces both ESLint and Prettier for JavaScript, TypeScript, JSX, JSON, and CSS in one fast tool. If you need an ESLint plugin that Biome does not have, you may still need ESLint for that part.
- yamllint checks YAML syntax and style, not meaning. It does not know whether an Azure DevOps task input is valid. The pipeline run itself (or the pipeline editor's validate button) checks that.
- When adding strict rules to an existing codebase, first run `npx biome check --write .` once in a dedicated pull request, so the formatting change is separate from feature work.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Passes locally, fails in CI (or the opposite) | Different Biome versions on the laptop and the agent | Use `--save-exact`, commit `package-lock.json`, use `npm ci`, and run `npx biome` (not a global install) |
| `biome.json` errors after an upgrade | Config keys changed between Biome versions | Run `npx biome migrate --write` and check the `$schema` errors |
| Pipeline is green but the code still has problems | CI runs `biome check --write`, which fixes files only on the agent | Use `npx biome ci .` in the pipeline |
| Biome checks `dist` or generated files | Folders not ignored | Enable `vcs.useIgnoreFile` or add them to `files.includes` with `!` |
| yamllint reports many `line-too-long` errors | Long scripts or URLs in pipeline files | Raise `line-length.max`, set it to `warning`, or disable it |
| `truthy` warnings on `on:` or `yes` | Rule expects only `true` and `false` | Use `true`/`false`, set `check-keys: false`, or add `'on'` to `allowed-values` |
| yamllint errors on Azure DevOps template lines like `${{ if ... }}:` | Indentation or spacing around template expressions | Fix the indentation; if a rule still conflicts, tune or disable it for those files with `ignore` |
| yamllint scans `node_modules` | Folder not ignored | Add it to the `ignore` block in `.yamllint` |

## Interview questions

<details><summary>Q1. What is Biome, and how does it compare to ESLint plus Prettier?</summary>

Biome is a linter and formatter for JavaScript, TypeScript, JSX, JSON, and CSS, written in Rust. It replaces ESLint and Prettier with one tool and one config file, and it is much faster, which matters in large repositories and in CI. ESLint has a bigger plugin ecosystem, so a team that depends on special plugins might keep ESLint. For most React and TypeScript projects, Biome covers the common rules, such as unused imports, and removes conflicts between the linter and the formatter.

</details>

<details><summary>Q2. Why do you run <code>biome ci</code> in the pipeline instead of <code>biome check --write</code>?</summary>

`check --write` changes files on the build agent, and nothing commits those changes back. The step can pass while the repository still contains the problems, so the gate is useless. `biome ci` is read-only: it reports lint, format, and import issues and exits non-zero, so the build fails and the developer fixes the code. `--write` is for local development and pre-commit hooks.

</details>

<details><summary>Q3. Why lint YAML files in a DevOps repository?</summary>

Pipelines, Kubernetes manifests, Helm values, and Ansible playbooks are all YAML. A wrong indent, a duplicated key, or a tab can break a deployment or silently change a value. yamllint catches syntax errors, duplicate keys, bad indentation, and risky values like `yes`/`no` before the pipeline or `kubectl` runs. It is fast and cheap compared to finding the error during a release.

</details>

<details><summary>Q4. How do you enforce quality gates on pull requests in Azure DevOps?</summary>

I put the checks in a pipeline where each tool is a separate step that fails on errors. Then I add that pipeline as a required **build validation** in the branch policy for `main`. Every pull request runs it automatically, and the pull request cannot be completed until it passes. I combine this with required reviewers and, if needed, other gates such as SonarQube or security scans.

</details>

<details><summary>Q5. How do you roll out strict linting on an existing codebase without blocking everyone?</summary>

First, run the formatter once on the whole codebase in a single pull request, so formatting noise is separate from real changes. Next, start with the recommended rules and set noisy rules to `warn`, then raise them to `error` step by step. Biome can also check only changed files (`--changed` or `--staged`) during the transition, while the full `biome ci .` becomes required once the backlog is fixed. Pin the tool version, add a pre-commit hook so developers find problems before the pipeline does, and agree the rules with the team.

</details>
