## 1. How do you troubleshoot Helm chart deployment failures?

**Answer:** Run `helm status` and `helm get manifest` → validate the YAML → check Kubernetes events and logs → roll back with `helm rollback` if needed.

**Detailed interview approach:**
I start with `helm lint`, `helm template --debug`, and a server-side dry run, to catch template, values, and API-schema errors before anything actually deploys.

For a release that already failed, I use `helm status <release>`, `helm get values`, `helm get manifest`, and Kubernetes events and logs to pin down the exact cause — a bad hook, an admission policy rejection, an attempt to change an immutable field, a missing CRD, a bad image, a scheduling problem, or a failed readiness check.

I compare the rendered manifest and values against the last good revision. Then I fix the chart or the environment dependency in Git and run a controlled upgrade. If production is affected, I use `helm rollback <release> <revision>` and check the pods and application metrics afterward.

Tests, schema validation, pinned chart versions, and time-limited atomic upgrades are what prevent this from happening again.
