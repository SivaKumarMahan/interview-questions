# Jenkins: Running Jenkins on Kubernetes with Helm

> Where to run Jenkins (VM, Docker, Kubernetes), installing it with the official Helm chart, managing plugins and configuration as code, recovering the admin password, and practical questions about where pipeline files live and how long jobs take.

## Key Concepts

### Ways to run Jenkins

| Option | How | Good for | Watch out for |
| --- | --- | --- | --- |
| VM (EC2 or Azure VM) | Package install (`apt` / `dnf`) as a systemd service | Simple setups, Windows or macOS agents nearby | Manual patching, backups and scaling |
| Docker container | `jenkins/jenkins:lts-jdk21` image with a volume for `/var/jenkins_home` | Labs and small teams | Data is lost without a volume; Docker-in-Docker security |
| Kubernetes with Helm | Official `jenkins/jenkins` chart on EKS, AKS or GKE | Production at scale, dynamic agents | Persistent volume, backups, resource limits |
| Kubernetes YAML manifests | Your own StatefulSet, Service, PVC and RBAC | Full control | More to maintain than the chart |

On Kubernetes, the controller runs as a StatefulSet with a persistent volume, and the **Kubernetes plugin** starts a new agent Pod for each build and deletes it afterwards.

### Helm chart layout

A Helm chart, including the one you use to deploy Jenkins, follows this structure:

```text
jenkins/
├── Chart.yaml          # chart name, version, appVersion, dependencies
├── values.yaml         # default settings you override per environment
├── values.schema.json  # optional: validates values
├── templates/          # Kubernetes manifests with Go templating
│   ├── _helpers.tpl
│   ├── statefulset.yaml   # Jenkins controller
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml     # JCasC configuration
│   ├── pvc.yaml           # jenkins_home storage (when not created by the StatefulSet)
│   ├── serviceaccount.yaml / rbac.yaml
│   └── NOTES.txt
├── charts/             # dependency charts
└── README.md
```

You normally do not edit the official chart. You keep your own `values-prod.yaml` in Git and install the chart with it.

### Install with Helm

```bash
helm repo add jenkins https://charts.jenkins.io
helm repo update
helm upgrade --install jenkins jenkins/jenkins \
  --namespace jenkins --create-namespace \
  --version <chart-version> \
  -f values-prod.yaml
kubectl -n jenkins rollout status statefulset/jenkins
```

Example `values-prod.yaml`:

```yaml
controller:
  image:
    tag: "2.516.3-jdk21"          # pin the LTS version
  resources:
    requests: { cpu: "1", memory: "2Gi" }
    limits:   { cpu: "2", memory: "4Gi" }
  installPlugins:                 # pinned plugin versions
    - kubernetes:4358.vcfd9c5a_0a_f51
    - workflow-aggregator:608.v67378e9d3db_1
    - git:5.7.0
    - configuration-as-code:1971.vf9280461ea_89
  JCasC:
    configScripts:
      welcome: |
        jenkins:
          systemMessage: "Managed by Helm and JCasC. Do not change settings in the UI."
  ingress:
    enabled: true
    ingressClassName: nginx
    hostName: jenkins.example.com
persistence:
  enabled: true
  size: 50Gi
  storageClass: managed-csi
```

The plugin versions above are examples; take current ones from the plugin site or your running instance.

## Interview Questions

<details><summary>Q1. [Basic] How would you deploy Jenkins in your organization?</summary>

**Answer:**

I would compare four options:

1. **VM install** (EC2 or Azure VM) with the official package as a systemd service.
2. **Docker container** with a named volume for `/var/jenkins_home`.
3. **Helm chart on Kubernetes** (EKS, AKS or GKE).
4. **Plain Kubernetes manifests** (StatefulSet, Service, PVC, RBAC).

For production I prefer **Helm on Kubernetes**: the controller configuration is in Git (values file plus Configuration as Code), agents are created as Pods on demand so we don't pay for idle build servers, and upgrades are a `helm upgrade` that can be rolled back. If the team builds Windows or macOS applications, I add static VM agents for those.

Whatever the platform, the essentials are the same: persistent storage for `jenkins_home`, regular backups, TLS and SSO in front of the UI, no builds on the controller (`numExecutors: 0`), and pinned plugin versions.

</details>

<details><summary>Q2. [Basic] When you deploy Jenkins with Helm, what is the folder structure?</summary>

**Answer:**

The chart has `Chart.yaml` (metadata and dependencies), `values.yaml` (default settings), a `templates/` folder with the Kubernetes manifests (StatefulSet for the controller, Service, Ingress, ConfigMap for JCasC, PVC, ServiceAccount and RBAC, `_helpers.tpl`, `NOTES.txt`), a `charts/` folder for dependencies and a `README.md`.

In practice, my repository does not contain the chart itself. It contains the files I own:

```text
platform-jenkins/
├── values-common.yaml
├── values-dev.yaml
├── values-prod.yaml
├── casc/                 # extra JCasC files: credentials references, clouds, jobs
└── pipeline.yaml         # pipeline that runs helm upgrade --install
```

</details>

<details><summary>Q3. [Intermediate] Jenkins is deployed with Helm. How do you add or update plugins?</summary>

**Answer:**

1. Change the plugin list and versions in the values file:

   ```yaml
   controller:
     installPlugins:
       - kubernetes:<version>
       - git:<new-version>
     additionalPlugins:
       - slack:<version>
   ```

2. Test in a non-production Jenkins first, because plugin updates are the most common cause of broken pipelines.
3. Apply it with Helm:

   ```bash
   helm upgrade jenkins jenkins/jenkins -n jenkins -f values-prod.yaml
   ```

   The controller Pod restarts and the init container installs the listed plugins.
4. If something breaks: `helm rollback jenkins <revision> -n jenkins`.

Avoid installing plugins from the UI on a Helm-managed Jenkins: those changes are not in Git and can be lost or overwritten at the next upgrade. Better still, build a custom controller image with the plugins baked in (`jenkins-plugin-cli --plugin-file plugins.txt`), so every restart is identical and does not depend on the update site.

</details>

<details><summary>Q4. [Intermediate] You lost the Jenkins admin password. How do you recover access?</summary>

**Answer:**

It depends on the situation:

- **Fresh installation** (setup wizard not finished): read the initial password.

  ```bash
  kubectl exec -n jenkins -it jenkins-0 -c jenkins -- cat /var/jenkins_home/secrets/initialAdminPassword
  # VM: sudo cat /var/lib/jenkins/secrets/initialAdminPassword
  ```

- **Helm chart with the default admin user:** the password is stored in a Kubernetes Secret.

  ```bash
  kubectl get secret jenkins -n jenkins -o jsonpath='{.data.jenkins-admin-password}' | base64 -d
  ```

- **Another admin exists:** that admin resets the password under *Manage Jenkins → Users*.
- **SSO (Entra ID, Okta, LDAP):** reset it in the identity provider; Jenkins has no local password to recover.
- **Last resort on a locally managed instance:** stop Jenkins, back up `config.xml`, temporarily disable security (`<useSecurity>false</useSecurity>`) or run a Groovy init script that resets the admin password, start Jenkins, set a new password, re-enable security immediately and restart. Do this only in a maintenance window, because Jenkins is open while security is off.

Prevent it by using SSO, defining the admin in JCasC with the password from a secret store, and backing up `jenkins_home`.

</details>

<details><summary>Q5. [Basic] Where do you store Jenkinsfiles and Dockerfiles?</summary>

**Answer:**

In the **application's own repository**, next to the code, so pipeline and build changes are versioned and reviewed together with the code:

```text
orders-service/
├── src/
├── Dockerfile
├── Jenkinsfile
├── helm/                 # or a separate GitOps repository for deployment manifests
└── README.md
```

Shared steps (build, scan, push, deploy) go into a **Jenkins shared library** in a separate repository, so each Jenkinsfile stays short:

```groovy
@Library('platform-lib@v3') _
standardPipeline(appName: 'orders-service', deployTo: ['dev', 'qa', 'prod'])
```

Jobs are created automatically by a **multibranch pipeline** or an organization folder that scans the repositories for a `Jenkinsfile`.

</details>

<details><summary>Q6. [Basic] How long does a Jenkins job take to complete?</summary>

**Answer:**

It depends on the pipeline, so give real numbers from your project and explain what drives them. For example:

> "Pull request builds for our Java services take about 6–8 minutes: 2 minutes for build and unit tests, 2 for SonarQube and dependency scans, 1–2 for the Docker build and push, and the rest for agent start-up. A full release to production takes about 25 minutes including integration tests and a manual approval."

Then mention how you keep it fast: dependency caching, parallel stages, Docker layer caching, running only affected tests, warm agent pools or pre-built agent images, and a timeout on every stage so stuck jobs fail instead of blocking agents. See [pipeline performance optimization](08-pipeline-performance-optimization.md).

</details>
