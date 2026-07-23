# Helm Detailed Interview Notes

### Q: Explain the folder structure of a Helm chart and the purpose of each folder/file. What commands you use to deploy Helm charts?

**A:** A Helm chart has a specific folder structure that organizes the files and templates needed to deploy applications on Kubernetes. Here's an overview of the typical folder structure of a Helm chart:

```
mychart/
│
├── Chart.yaml
├── values.yaml
│
├── charts/
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── _helpers.tpl
│   ├── hpa.yaml
│   ├── NOTES.txt
│
└── .helmignore
```

Here's a brief explanation of each folder/file:

1. **`Chart.yaml`:** This file contains metadata about the chart, such as its name, version, description, and maintainers. It is essential for Helm to identify and manage the chart.
2. **`values.yaml`:** This file contains the default configuration values for the chart. Users can override these values when deploying the chart to customize the deployment.
3. **`charts/`:** This directory is used to store any dependent charts that your chart relies on. These dependencies can be other Helm charts that are packaged together with your main chart.
4. **`templates/`:** This directory contains the Kubernetes manifest templates that Helm uses to generate the final YAML files for deployment. These templates can include Deployments, Services, Ingresses, and other Kubernetes resources. The templates can use Go templating syntax to allow for dynamic configuration based on the values provided in `values.yaml` or during deployment.
   - **`deployment.yaml`:** Template for creating a Kubernetes Deployment resource.
   - **`service.yaml`:** Template for creating a Kubernetes Service resource.
   - **`ingress.yaml`:** Template for creating a Kubernetes Ingress resource.
   - **`_helpers.tpl`:** A file that contains helper template functions that can be reused across other templates.
   - **`hpa.yaml`:** Template for creating a Horizontal Pod Autoscaler resource.
   - **`NOTES.txt`:** A file that provides post-installation instructions or notes to the user after the chart is deployed.
5. **`.helmignore`:** This file specifies patterns for files and directories that should be ignored when packaging the chart. It works similarly to a `.gitignore` file.

To deploy Helm charts, you can use the following commands:

1. `helm install <release-name> <chart-path>`: This command installs a Helm chart into your Kubernetes cluster. Replace `<release-name>` with a name for your deployment and `<chart-path>` with the path to your chart.
2. `helm upgrade <release-name> <chart-path>`: This command upgrades an existing release with a new version of the chart.
3. `helm uninstall <release-name>`: This command removes a deployed Helm release from the cluster.
4. `helm repo add <repo-name> <repo-url>`: This command adds a Helm chart repository.
5. `helm repo update`: This command updates the local cache of chart repositories.
6. `helm list`: This command lists all the deployed Helm releases in the cluster.

Helm uses Kubernetes Deployment's rolling update strategy. When you upgrade a Helm release, it triggers a rolling update of pods with new configurations/images — old pods are terminated only after new ones become Ready, ensuring zero downtime.

---

## Helm Project Examples

### 1. Full-stack To-Do application

- Containerize frontend and backend separately and publish immutable image digests to Azure Container Registry.
- Use one reusable chart or clearly separated charts for Deployments, Services, ConfigMaps, external secrets, probes, resources, and Ingress.
- Keep Dev, QA, and Production values separate while reusing the same chart version.
- Validate with `helm lint`, `helm template`, and a server-side dry run before `helm upgrade --install`.
- Use `--atomic --wait --timeout 5m`, then verify rollout status and a business-level smoke test.
- Roll back to a known Helm revision only after checking whether database or external dependency changes are backward-compatible.

### 2. Node.js To-Do application

The chart exposes the application through a Service and includes startup/readiness/liveness probes so Kubernetes does not send traffic before the application is ready. A NodePort can be used for learning, but production normally uses Ingress or a LoadBalancer with TLS, authentication, and controlled network exposure.

### 3. Jenkins on Kubernetes

Jenkins can be installed from a chart with persistent storage for the controller and ephemeral Kubernetes agents for builds. PersistentVolume backup, plugin/version pinning, credentials, security context, resource limits, controller recovery, and chart upgrade tests must be planned before treating this as a production installation.

### 4. Helmfile

Helmfile declaratively coordinates multiple Helm releases and environment values. I use it when several related releases must be installed in a known order, while still pinning chart versions, separating secrets, reviewing rendered changes, and verifying each release. For Kubernetes desired-state reconciliation across clusters, Argo CD or Flux may be a better GitOps control plane.

---

### Q: what is email signing and Helm chart signing? which tools do you use to sign Helm charts?

**A:**

**Email Signing:**

Email signing is the process of digitally signing an email message to verify the sender's identity and ensure the integrity of the message content. It uses cryptographic techniques to create a digital signature that is attached to the email. The recipient can then verify the signature using the sender's public key, confirming that the email has not been altered and is indeed from the claimed sender. Common standards for email signing include **S/MIME** (Secure/Multipurpose Internet Mail Extensions) and **PGP** (Pretty Good Privacy).

**Helm Chart Signing:**

Helm chart signing is the process of digitally signing Helm charts to ensure their authenticity and integrity. By signing a Helm chart, the chart maintainer provides a way for users to verify that the chart has not been tampered with and is from a trusted source. Helm uses **GPG** (GNU Privacy Guard) for signing charts. When a chart is signed, a signature file is created alongside the chart package. Users can then verify the signature using the public key of the chart maintainer before installing the chart.

**Tools for Signing Helm Charts:**

1. **GPG (GNU Privacy Guard):** GPG is the primary tool used for signing Helm charts. It allows you to create a key pair (public and private keys) and use the private key to sign the chart. The public key can be shared with users who want to verify the chart's signature.

To sign a Helm chart, you can use the following command:

```bash
helm package <chart-path> --sign --key <key-id> --keyring <path-to-keyring>
```

To verify a signed Helm chart, you can use:

```bash
helm verify <chart-package>
```

In summary, email signing and Helm chart signing both serve to verify authenticity and integrity, but they apply to different contexts — email communication and software package distribution, respectively. GPG is the tool commonly used for signing Helm charts.

---
