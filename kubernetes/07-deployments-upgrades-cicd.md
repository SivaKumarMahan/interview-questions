# Kubernetes: Deployments, Upgrades, and CI/CD

> Rolling updates, rollbacks, blue-green and canary, cluster upgrades, CI/CD, Helm, and GitOps.

## Key Concepts

### Rollouts and Deployment Strategies

A Deployment rolling update gradually scales a new ReplicaSet up while scaling the old one down. `maxSurge` and `maxUnavailable` control capacity during the rollout.

For low-risk updates:

- Use multiple replicas across nodes/zones.
- Define realistic readiness and startup probes.
- Set resource requests.
- Use a PodDisruptionBudget and graceful shutdown.
- Configure `preStop` and sufficient termination grace where needed.
- Monitor the rollout and application metrics.
- Keep a tested rollback method.

If a Deployment is updated again during an active rollout, Kubernetes creates or uses a ReplicaSet for the newest Pod template and converges toward that latest state.

Blue-green and canary releases can be implemented with Services, multiple Deployments, Ingress/service-mesh routing, or progressive-delivery tools.

### Delivery, Scaling, and Cost

- Zero-downtime delivery depends on immutable versions, realistic readiness/startup probes, adequate surge capacity, graceful shutdown, compatible database changes, rollout monitoring, and a tested rollback — not only `RollingUpdate` settings.
- Canary and blue-green strategies promote releases using health and business metrics. Keep the old version available during the validation window and automate rollback when thresholds fail.
- HPA scales Pods, a node autoscaler supplies schedulable capacity, and event-driven scaling handles queue or custom demand. Validate metric freshness, resource requests, min/max limits, stabilization windows, dependency capacity, and scale-down behavior.
- Cost optimization combines usage evidence, right-sizing, autoscaling, appropriate node pools, spot capacity for tolerant workloads, log retention, storage lifecycle, quotas, schedules, and SLO verification after each change.

### Controlled cluster upgrade

Back up self-managed etcd and cluster configuration, confirm workload/backup health, review deprecated APIs and add-on compatibility, respect supported version skew, and rehearse in staging.

Upgrade the control plane through the distribution/provider-supported procedure, then cordon and drain worker nodes one at a time while respecting PDBs and replacement capacity.

Upgrade kubelet/runtime/node images and CNI/CSI/Ingress/DNS add-ons in their supported sequence. Verify nodes, system Pods, application transactions, SLOs, and rollback/recovery after every wave.

Do not copy version numbers from a screenshot; select currently supported versions from the platform documentation.

### Operations Notes

- For planned node work, cordon the node with `kubectl cordon <node>`, drain it with a PDB-aware command, do the maintenance, then bring it back with `kubectl uncordon <node>`. Don't reach for `--ignore-daemonsets` as a way to avoid thinking through what the drain will actually disrupt.

### CI/CD and GitOps

A typical delivery flow builds and scans an image, publishes it to a registry, validates manifests or Helm charts, deploys to a lower environment, runs tests, and promotes an immutable version — one that is never changed after it is created, only replaced.

- **Push deployment:** CI credentials apply changes to the cluster.
- **Pull-based GitOps:** Argo CD or Flux reconciles cluster state from Git/OCI sources.

GitOps provides continuous reconciliation and drift visibility. Projects that combine Terraform, EKS/AKS, Helm, Jenkins, Argo CD/Flux, Prometheus, and Grafana demonstrate the full infrastructure-to-observability lifecycle.

### Helm-Based Microservice Delivery

Helm charts define the workload, Service, ingress/Gateway routes, configuration, resource limits, probes and policy-compatible metadata.

Store chart templates separately from environment values; promote an immutable chart version and image digest rather than rebuilding for each environment.

A typical release validates with `helm lint` and `helm template`, runs policy/security checks, deploys with limited `--wait`/`--atomic` behavior where suitable, then proves health through real requests and observability. Helm release success alone is not application success.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you perform rolling updates and rollbacks in Kubernetes?</summary>

**Answer:**

I change the versioned manifest or image digest and apply it through CI or GitOps. The Deployment creates a new ReplicaSet and scales it up according to `maxSurge` and `maxUnavailable`. I watch it happen:

```bash
kubectl diff -f deployment.yaml
kubectl apply -f deployment.yaml
kubectl rollout status deploy/api --timeout=5m
kubectl rollout history deploy/api
```

I check the Pods, events, readiness, and the application's own error rate, latency, and smoke tests. If something regresses, I pause or roll back with `kubectl rollout undo deploy/api --to-revision=N`, or a Git revert or Helm rollback, and then validate.

A rollback might not undo a ConfigMap change, an external system change, or a database change. That's why releases use immutable config and artifacts, and backward-compatible migrations. Whatever failed gets its evidence preserved and fixed before I try the rollout again.

</details>

<details><summary>Q2. [Basic] How do <code>maxSurge</code> and <code>maxUnavailable</code> control a rolling update?</summary>

A Rolling Update is the default Deployment strategy: it replaces old Pods with new ones gradually, in batches, instead of stopping everything at once.

Example: 4 Pods running `v1`, deploying `v2`:

1. Kubernetes creates a `v2` Pod.
2. It waits for the new Pod to become healthy (readiness probe passes).
3. It removes an old `v1` Pod.
4. It repeats until all Pods run `v2`.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 1
```

- `maxSurge` - the maximum number of extra Pods that can be created above the desired replica count during the update.
- `maxUnavailable` - the maximum number of Pods that can be unavailable at once during the update.

Tuning these controls the tradeoff between rollout speed and headroom: a higher `maxSurge` rolls out faster but briefly uses more cluster resources; a higher `maxUnavailable` rolls out faster but reduces how many healthy replicas are guaranteed at any moment.

#### Short interview answer

A Rolling Update gradually replaces old Pods with new ones, waiting for each new Pod to pass its readiness probe before removing an old one - so deployments happen with little or no downtime. `maxSurge` caps how many extra Pods can exist above the desired count during the rollout, and `maxUnavailable` caps how many Pods can be unavailable at once; together they control how aggressively the rollout proceeds.

</details>

<details><summary>Q3. [Intermediate] How does Kubernetes perform rolling updates using YAML to achieve zero downtime deployments?</summary>

Kubernetes performs rolling updates using the **Deployment** resource, which allows you to update your application without downtime by gradually replacing old pods with new ones. You can specify the update strategy and parameters in the Deployment YAML file.

**Example Deployment YAML for a rolling update:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0   # Number of pods that can be unavailable during the update
      maxSurge: 1         # Number of extra pods that can be created temporarily during the update
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app-container
        image: my-app:1.0.0
```

To perform a rolling update, update the image version in the Deployment YAML (e.g., change `my-app:1.0.0` to `my-app:1.1.0`) and apply the changes using `kubectl apply -f deployment.yaml`.

Kubernetes will then:

1. Create new pods with the updated image.
2. Gradually terminate old pods while ensuring that the specified number of replicas is maintained.
3. Use `maxUnavailable` and `maxSurge` settings to control the pace of the update, ensuring zero downtime.

You can monitor the update process using:

```bash
kubectl rollout status deployment my-app
kubectl get pods -o wide
```

**Additional features for zero downtime:**

- Use **readiness probes** to ensure traffic isn't sent to unready Pods.
- The Kubernetes **Service** handles load balancing across old and new Pods during rollout.
- Supports **canary** or **blue-green** strategies if you want finer control.
- Supports **pause/resume** rollout (`kubectl rollout pause/resume`) for manual approval.

**If something goes wrong:**

```bash
kubectl rollout undo deployment my-app
```

</details>

<details><summary>Q4. [Intermediate] If you update a Deployment's image while a rolling update is in progress, will Kubernetes wait for the current rollout to complete or start a new one immediately?</summary>

**Answer:**

Kubernetes immediately starts a new rollout, canceling the current one. This behavior is called "rollout interruption."

What happens:

- The current rolling update stops immediately.
- A new ReplicaSet is created for the updated image.
- The previous ReplicaSet (from the interrupted rollout) begins scaling down.
- The new ReplicaSet scales up according to the rolling update strategy.

You can observe this with:

```bash
kubectl rollout status deployment/myapp
kubectl rollout history deployment/myapp
```

This can lead to more Pods than expected during the transition period, so monitor resource usage carefully.

</details>

<details><summary>Q5. [Advanced] An application upgrade caused downtime even with rolling updates. How do you prevent it next time?</summary>

**Answer:**

I line up the rollout timeline against endpoints, readiness, termination, capacity, errors, and any database or dependency change. Common causes are running only one replica, readiness firing too early or checking the wrong thing, a liveness probe killing the app mid-startup, `maxUnavailable` set too aggressively with no surge capacity, the app ignoring SIGTERM, load-balancer propagation delay, an incompatible config, schema, or API change, or simply not enough resources.

The fix usually involves multiple replicas spread across nodes, a startup and readiness probe tuned from measured timings, `maxUnavailable: 0` where there's capacity for it, a preStop hook with a real termination grace period and connection draining, a PDB for maintenance windows, and a backward-compatible expand-and-contract approach to schema changes. CI runs smoke tests and canary health gates with a rollback path.

I reproduce the failure in a load test and measure how many requests actually get dropped during the rollout. Zero downtime is an end-to-end architecture decision, not just a Deployment strategy setting.

</details>

<details><summary>Q6. [Intermediate] How do you ensure zero downtime deployment in Kubernetes?</summary>

**Answer:** Use RollingUpdate strategy in deployments, configure readiness probes, and keep replicas running until new pods are healthy.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

</details>

<details><summary>Q7. [Intermediate] How do you achieve blue-green deployments in Kubernetes?</summary>

**Answer:**

I run Blue, the current version, and Green, the candidate, as two separate Deployments with distinct version labels. A stable production Service or Ingress route points at Blue.

I deploy Green, test it through a preview Service or hostname, including dependency and data compatibility, and then atomically switch the Service selector or traffic route over to it. I monitor the switch, and I can switch back for a fast rollback since Blue is still running.

I make sure there's enough capacity for both at once, and check sessions, caching, background jobs, database schema compatibility, and that there are no duplicate consumers of the same queue or resource. The Service selector switch itself is fast, but I still watch endpoint and load-balancer propagation. A weighted route can ramp traffic more gradually if needed.

Once I'm confident, I remove Blue and the old resources, with approval. The pipeline records the versions involved, and automated synthetic checks and SLO gates back the decision. Any destructive database migration waits until the rollback window has closed.

</details>

<details><summary>Q8. [Intermediate] How do you perform blue-green deployment in Kubernetes?</summary>

**Answer:** Run two environments (Blue = current, Green = new) → Route traffic to Green only after successful validation → Rollback to Blue if issues occur.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

</details>

<details><summary>Q9. [Intermediate] How do you perform Canary Deployment in Kubernetes?</summary>

**Answer:** Deploy a new version to a small % of users → Use Istio/NGINX Ingress for traffic routing → Gradually increase traffic → Rollback if errors.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

</details>

<details><summary>Q10. [Intermediate] How do you handle a failed deployment in Kubernetes?</summary>

**Answer:** Use kubectl describe pod and kubectl logs to check errors → If critical, rollback with kubectl rollout undo deployment <name> → Fix and redeploy.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

</details>

<details><summary>Q11. [Intermediate] How do you implement rollback in Azure Kubernetes Service (AKS)?</summary>

**Answer:** Use kubectl rollout undo for deployments, or Helm rollback (helm rollback release name ).

**Detailed interview approach:**
I deploy an immutable artifact through a strategy matched to the risk involved: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, and then advances while watching error rate, latency, saturation, and the SLO or error budget.

If a threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record the result, and improve whatever test or guard should have caught the failure earlier.

</details>

<details><summary>Q12. [Intermediate] Do you update only images or also replicas, storage, and CPU?</summary>

**Answer:**

I manage the whole desired state, not just the image: the image digest, replicas and HPA, requests and limits, probes, config and Secret references, the security context, Service, Ingress, and policy, volumes, and annotations. Each of these carries its own risk and needs its own validation.

Changing the image, config, or resources rolls the Pods, so I verify the rollout, capacity, and performance afterward. Manually changing replicas can fight with HPA or GitOps trying to set it back.

Some StorageClass and PVC fields are immutable, and need proper data migration, expansion, topology, or backup work instead — I never casually edit a stateful volume. Changing a Service's selector or port can cause an outage on its own.

Every change flows through a Git diff, render, schema, and policy checks, a lower environment first, then a progressive rollout to production, SLO verification, and a rollback or recovery path. "Deployment" really means configuration plus artifact together, not just the image.

</details>

<details><summary>Q13. [Intermediate] How do you safely update a Kubernetes cluster version?</summary>

**Answer:**

I start with an inventory: the current version, version skew, support status, deprecated APIs (checked with tools like `pluto` or `kubent`), and compatibility across CRDs, webhooks, operators, CNI, CSI, Ingress, and metrics, plus PDB coverage, capacity, and backups. For self-managed etcd, I actually test a backup and restore. I upgrade dev, then staging, under real workload tests first.

For production, I set up a maintenance window and communicate it, upgrade the control plane by one supported version increment, validate the API and controllers, update add-ons, add or upgrade a new node pool, and cordon and drain nodes gradually — respecting PDBs and any local or stateful workload — validating each batch before moving to the next. Then I retire the old node pool.

I monitor SLOs, Pending Pods, restarts, DNS, networking, storage, and admission throughout.

Rolling back a managed control plane usually isn't possible, so recovery often means fixing forward, rolling back the node pool, or failing the workload over elsewhere. I keep IaC, a runbook, and post-upgrade evidence, and I never skip an unsupported version jump.

</details>

<details><summary>Q14. [Intermediate] Have you upgraded Kubernetes clusters?</summary>

**Answer:**

A strong, honest answer states my exact role, the scale, the version, and the actual steps I followed. For example: I inventoried deprecated APIs, version skew, and compatibility across CNI, CSI, Ingress, metrics, and operators, tested a backup restore, ran the upgrade in dev and staging, and then scheduled it for production.

I upgraded the control plane by one supported minor version, validated the API and add-ons, created or upgraded a canary node pool, and cordoned and drained nodes gradually while respecting PDBs and any stateful or local data. I monitored Pending Pods, restarts, DNS, networking, storage, and SLOs throughout, then removed the old node pool. I kept spare capacity, clear communication, and a recovery plan the whole time.

Afterward I validated real transactions, policy and security, and backups, and recorded the evidence and any issues in the root-cause review. If I only assisted on part of it, I say exactly what my responsibility was rather than claiming end-to-end ownership.

</details>

<details><summary>Q15. [Intermediate] How have you upgraded a Kubernetes cluster in production in Azure? What steps did you take to ensure zero downtime?</summary>

In production, I upgrade AKS clusters with zero downtime by upgrading the control plane first, followed by node pools sequentially using Azure CLI. Each node is drained gracefully, with workloads protected by readiness probes, multiple replicas, and PodDisruptionBudgets.

I monitor during the process via Azure Monitor and Grafana, and test in staging beforehand. This rolling approach ensures continuous availability — users never see downtime.

**Steps for a zero-downtime AKS upgrade:**

**1. Pre-upgrade preparation:**

- Review the AKS release notes for breaking changes.
- Test the upgrade process in a staging environment.
- Ensure all workloads have multiple replicas and readiness/liveness probes configured.
- Define **PodDisruptionBudgets (PDBs)** to limit voluntary disruptions.

**2. Upgrade the control plane:**

```bash
az aks upgrade --resource-group <resource-group> --name <aks-cluster-name> --kubernetes-version <new-version> --control-plane-only
```

**3. Upgrade node pools sequentially:**

- The node is cordoned (no new pods scheduled).
- Pods are evicted and rescheduled on healthy nodes.
- A new node with the upgraded image joins the cluster.
- The old node is deleted once draining completes.

```bash
# List node pools
az aks nodepool list --resource-group <resource-group> --cluster-name <aks-cluster-name>

# Upgrade each node pool one at a time
az aks nodepool upgrade --resource-group <resource-group> --cluster-name <aks-cluster-name> --name <nodepool-name> --kubernetes-version <new-version>
```

**4. Monitor the upgrade:**

- Use Azure Monitor and Grafana dashboards to track cluster health, node status, and application performance.
- Check for any Pod evictions or disruptions.

**5. Post-upgrade validation:**

- Verify that all nodes are running the new Kubernetes version.
- Ensure all applications are functioning correctly.
- Review logs for any errors or warnings.

**6. Rollback plan:**

- Have a rollback plan in case of issues, such as restoring from backups or redeploying previous versions of applications.

By following these steps, I ensure a smooth AKS upgrade with zero downtime for end-users.

</details>

<details><summary>Q16. [Intermediate] What are the steps to be performed while upgrading a Kubernetes cluster?</summary>

- **Backup everything:** etcd, configurations, and application data.
- **Check compatibility:** Review release notes and breaking changes.
- **Update the control plane first:** API server, controller-manager, scheduler.
- **Update kubelet and kube-proxy** on nodes one by one.
- **Drain nodes before updating:** `kubectl drain <node> --ignore-daemonsets`.
- **Update CNI and other addons** to compatible versions.
- **Verify cluster health** after each step.
- **Test applications** and roll back if issues occur.
- **Uncordon nodes:** `kubectl uncordon <node>`.

</details>

<details><summary>Q17. [Intermediate] How do you manage Kubernetes cluster upgrades with zero downtime?</summary>

**Answer:** Upgrade control plane first → Drain nodes one by one → Use pod disruption budgets → Monitor workloads.

**Detailed interview approach:**
I review version skew, removed APIs, CNI, CSI, and Ingress compatibility, add-on versions, quotas, and maintenance constraints. I test the exact upgrade on a representative non-production cluster and run API deprecation and workload disruption checks against it.

In production, I upgrade the control plane first, then move through one node pool or failure domain at a time: cordon, drain respecting PDBs, replace or upgrade, and verify before moving on to the next.

I monitor API errors, DNS, networking, scheduling, and node and application SLOs, and keep the rollback and recovery options documented, since a control-plane downgrade often isn't supported.

Backups and a tested cluster-rebuild path are required before rolling this out across the whole fleet.

</details>

<details><summary>Q18. [Advanced] How do you manage Kubernetes upgrades across 50+ clusters?</summary>

**Answer:** Automate upgrades with tools like Rancher/Anthos, test in staging first, roll out gradually, and monitor workloads post-upgrade. Mini-case: Anthos automated rolling upgrades; a failed upgrade in staging paused rollout and prevented production outages.
**Detailed interview approach:**
I review version skew, removed APIs, CNI, CSI, and Ingress compatibility, add-on versions, quotas, and maintenance constraints. I test the exact upgrade on a representative non-production cluster and run API deprecation and workload disruption checks against it.

In production, I upgrade the control plane first, then move through one node pool or failure domain at a time: cordon, drain respecting PDBs, replace or upgrade, and verify before moving on to the next.

I monitor API errors, DNS, networking, scheduling, and node and application SLOs, and keep the rollback and recovery options documented, since a control-plane downgrade often isn't supported.

Backups and a tested cluster-rebuild path are required before rolling this out across the whole fleet.

</details>

<details><summary>Q19. [Advanced] Automated zero-downtime EKS upgrades <em>(asked in interview round)</em></summary>

1. Upgrade the control plane first, one minor version at a time, using `eks update-cluster-version`. AWS manages this part.
2. Upgrade the managed add-ons (VPC CNI, CoreDNS, kube-proxy) to versions compatible with the new control plane.
3. Upgrade the node groups. Use managed node groups or Karpenter to create new nodes on the new version, then cordon and drain the old nodes so pods reschedule gracefully. Managed node groups handle this rolling update for you.
4. Protect availability during the drains with PodDisruptionBudgets, multiple replicas, readiness probes, and topology spread.
5. Validate compatibility beforehand: check for deprecated APIs with tools like `kubent` or `pluto`, test the upgrade in a non-production cluster, and automate the whole flow with IaC (Terraform or eksctl) plus a pipeline.

</details>

<details><summary>Q20. [Intermediate] How do you integrate Kubernetes into a CI/CD pipeline?</summary>

**Answer:**

On a pull request, I run tests, lint, and secret, dependency, and IaC scans. On the main branch, I build the image once, generate an SBOM, scan it, sign it, and push it by its immutable digest.

I render the Helm or Kustomize output and run schema and policy checks against it. I deploy to staging through GitOps where possible, or with a least-privilege CI identity otherwise, then run rollout, smoke, and integration checks.

Once approved, I progressively promote that same digest through the higher environments, monitoring SLOs and ready to roll back traffic or version at any point.

Secrets come from an external manager or workload identity — never an admin kubeconfig in the pipeline. Environments, config, and state stay separated, and concurrency controls prevent two overlapping deploys to the same production environment. Database changes follow an expand, migrate, contract pattern.

The pipeline records the commit, the image digest, the manifests or chart used, the scan results, approvals, the cluster, deployment, and revision, and the verification results. If a deploy fails, its events and logs are preserved, and it's reverted through Git, Helm, or the controller once it's safe to do so.

</details>

<details><summary>Q21. [Intermediate] How do you connect Jenkins to a Kubernetes cluster?</summary>

**Answer:**

I prefer a short-lived cloud or workload identity mapped to Kubernetes RBAC, or better yet a GitOps setup where Jenkins just updates Git and a controller does the actual deploy. If Jenkins does connect directly, it gets a dedicated ServiceAccount and role limited to a specific namespace, resources, and verbs, a protected credential scope, and an isolated deployment agent — never a `cluster-admin` kubeconfig.

The Jenkins Kubernetes plugin might also spin up ephemeral build agents, but that's separate from deployment access. The pipeline verifies the context and namespace, renders and diffs the manifests, deploys, checks rollout and smoke tests, and logs everything for audit.

For an authentication failure, I check the credential, IAM token, or OIDC setup, the kubeconfig context, API DNS, network, CA, and time sync, and RBAC with `kubectl auth can-i`. I test both an allowed and a denied operation. I rotate tokens regularly, restrict who can approve the production stage, and never print a kubeconfig or token in the logs.

</details>

<details><summary>Q22. [Intermediate] How do you handle configuration drift in Kubernetes?</summary>

**Answer:** Use GitOps tools like ArgoCD/Flux → Ensure cluster config matches Git repo → Auto-revert manual changes.

**Detailed interview approach:**
Git holds the reviewed, desired configuration in immutable, versioned commits. Argo CD or Flux continuously compares that against the live cluster and reconciles any difference.

I separate environment permissions and repositories, require branch protection and policy or security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might temporarily pause sync, but it gets captured through a pull request right away — otherwise reconciliation will correctly remove it again. A rollback is just a Git revert to the last known-good commit, followed by a sync and a health and SLO check.

Secrets use an external-secret or encrypted-secret workflow, never plaintext in Git. Sync failures, drift, controller access, and audit events are all monitored, and destructive pruning has explicit safeguards around it.

</details>
