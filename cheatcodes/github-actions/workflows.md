# GitHub Actions Workflow Cheatcode

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
          cache: maven

      - name: Build and test
        run: mvn --batch-mode verify

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-reports
          path: target/surefire-reports/
```

For production, pin third-party actions to reviewed commit SHAs. Add a separate image job with OIDC-based registry/cloud login, build a digest that never changes after it's built, and deploy through a protected environment or GitOps update.

Never run privileged deployment steps for untrusted fork code.

## Common checks

```text
Not triggered → on/event/branch/path filters and YAML location/syntax
403 → effective permissions, token type/scope, environment/repository policy
Secret empty → repository/org/environment scope and correct secrets context
Cache miss → key, restore keys, path, lockfile hash, quota
Artifact missing → upload path/name, job dependency, retention
Runner timeout → queue, labels, runner health, job timeout, logs/resources
```
