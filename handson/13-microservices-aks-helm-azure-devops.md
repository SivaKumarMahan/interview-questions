# Hands-on 13: Microservices on AKS with Helm, ACR, and Azure DevOps

> Build an end-to-end microservices platform on AKS: Azure CNI powered by Cilium for networking and policies, managed ingress for routing, one Helm chart per service, secrets from Key Vault through workload identity, and an Azure DevOps pipeline that builds to ACR and deploys only the services that changed.

**Time:** about 2-3 hours. **Level:** Advanced.

## What you practise

- Creating AKS with Azure CNI Overlay and the Cilium dataplane, workload identity, ACR, and Container Insights
- Default-deny network policies with an allow rule for the ingress controller
- Path-based routing to two services (`orders`, `payments`) with the AKS application routing add-on
- One Helm chart per microservice with per-environment values
- Key Vault Secrets Store CSI driver plus workload identity, and Entra ID auth for Cosmos DB, Redis, and Service Bus
- An Azure DevOps multi-stage pipeline: path-filtered build, push to ACR, `helm upgrade --install --atomic`, and a Prod approval
- Observability with Container Insights, Application Insights (OpenTelemetry), and KQL

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription with Owner (or Contributor + User Access Administrator) on `rg-dev` | Create AKS and assign roles |
| ACR `myacr` | Stores the service images |
| Log Analytics workspace and Application Insights resource | Logs, metrics, and traces |
| Key Vault, Cosmos DB, Redis, and Service Bus (ideally with private endpoints) | Backend services |
| Azure DevOps project with an Azure Resource Manager service connection (workload identity federation) and a Docker registry service connection to ACR | Pipeline access |
| Azure CLI, kubectl, kubelogin, Helm 3 | Commands in this lab |

## Flow

```text
                    Users (HTTPS)
                         |
                         v
        Azure Load Balancer (public IP, DNS name)
                         |
                         v
   Managed ingress (app routing add-on, namespace app-routing-system)
        |  /orders                          |  /payments
        v                                   v
   Service orders (ClusterIP)          Service payments (ClusterIP)
        |                                   |
        v                                   v
   orders Pods  ---- Service Bus ---->  payments Pods       namespace: shop
        |       (events via private      |                (Cilium network policies)
        |        endpoint)               |
        +---------+----------------------+
                  |  private endpoints + private DNS zones
                  v
   Cosmos DB (orders data)   Redis (cache)   Service Bus (queues/topics)

   Secrets:  Key Vault --(CSI driver + workload identity)--> files mounted in Pods
   Identity: Pod ServiceAccount --(federated credential)--> user-assigned managed identity
   Images:   AKS kubelet identity --(AcrPull)--> myacr.azurecr.io
   Monitor:  Container Insights + Prometheus metrics --> Log Analytics / Azure Monitor
             OpenTelemetry in each service --> Application Insights

   CI/CD:  Azure Repos / GitHub --> Azure DevOps pipeline
           build + push image to ACR --> helm upgrade --install (dev --> approval --> prod)
```

## Steps

### 1. Create the AKS cluster with Azure CNI powered by Cilium

```bash
RG=rg-dev
AKS=aks-dev
LOCATION=westeurope
LAW_ID=$(az monitor log-analytics workspace show -g $RG -n law-dev --query id -o tsv)

az aks create \
  --resource-group $RG \
  --name $AKS \
  --location $LOCATION \
  --node-count 3 \
  --node-vm-size Standard_D4s_v5 \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --pod-cidr 192.168.0.0/16 \
  --network-dataplane cilium \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --enable-managed-identity \
  --attach-acr myacr \
  --enable-addons monitoring,azure-keyvault-secrets-provider \
  --workspace-resource-id $LAW_ID \
  --enable-aad --enable-azure-rbac \
  --generate-ssh-keys

az aks get-credentials -g $RG -n $AKS
kubelogin convert-kubeconfig -l azurecli
kubectl get nodes
```

- `--network-plugin azure --network-plugin-mode overlay`: Pods get IPs from a private overlay range, so they do not use up VNet addresses.
- `--network-dataplane cilium`: eBPF dataplane. It replaces kube-proxy and enforces network policies, so no separate policy engine is needed.
- `--enable-oidc-issuer --enable-workload-identity`: lets Pods get Entra ID tokens without secrets.
- `--attach-acr myacr`: gives the kubelet identity `AcrPull` on ACR (you need permission to assign roles on the registry).
- `monitoring`: Container Insights. `azure-keyvault-secrets-provider`: the Key Vault CSI driver.

### 2. Enable managed ingress

> **Accuracy note:** the community **ingress-nginx** project was retired by Kubernetes SIG Network; its best-effort maintenance ended in March 2026, so it gets no more fixes. For new clusters, do not install the community Helm chart. Use the **AKS application routing add-on** (managed by Microsoft) or **Gateway API**, for example **Application Gateway for Containers**. Check the AKS documentation for the add-on's own support timeline and Gateway API migration path.

```bash
az aks approuting enable -g $RG -n $AKS
kubectl get ingressclass
kubectl get svc -n app-routing-system
```

Expected: an IngressClass named `webapprouting.kubernetes.azure.com` and a `LoadBalancer` Service with a public IP in `app-routing-system`.

### 3. Create the namespace and network policies

```bash
kubectl create namespace shop
```

`network-policies.yaml`:

```yaml
# 1. Deny all incoming traffic to every Pod in the namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: shop
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
# 2. Allow the ingress controller to reach orders and payments
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress
  namespace: shop
spec:
  podSelector:
    matchExpressions:
      - key: app.kubernetes.io/name
        operator: In
        values: ["orders", "payments"]
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: app-routing-system
      ports:
        - protocol: TCP
          port: 8080
---
# 3. Allow orders to call payments directly
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-orders-to-payments
  namespace: shop
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: payments
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: orders
      ports:
        - protocol: TCP
          port: 8080
```

```bash
kubectl apply -f network-policies.yaml
```

Cilium enforces standard Kubernetes `NetworkPolicy`. It also supports `CiliumNetworkPolicy` for features such as FQDN-based egress rules and Layer 7 (HTTP) rules; on AKS these advanced features need **Advanced Container Networking Services**. A simple CiliumNetworkPolicy equivalent to rule 3:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-orders-to-payments
  namespace: shop
spec:
  endpointSelector:
    matchLabels:
      app.kubernetes.io/name: payments
  ingress:
    - fromEndpoints:
        - matchLabels:
            app.kubernetes.io/name: orders
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
```

If you later add a default-deny **egress** policy, remember to allow DNS (UDP and TCP 53 to `kube-system`) and the private endpoint IPs, or every outbound call fails.

### 4. Set up workload identity for the services

One user-assigned managed identity per service gives least privilege. Example for `orders`:

```bash
OIDC_ISSUER=$(az aks show -g $RG -n $AKS --query oidcIssuerProfile.issuerUrl -o tsv)

az identity create -g $RG -n id-orders
ORDERS_CLIENT_ID=$(az identity show -g $RG -n id-orders --query clientId -o tsv)
ORDERS_PRINCIPAL_ID=$(az identity show -g $RG -n id-orders --query principalId -o tsv)

az identity federated-credential create \
  --name fc-orders \
  --identity-name id-orders \
  --resource-group $RG \
  --issuer $OIDC_ISSUER \
  --subject system:serviceaccount:shop:orders \
  --audience api://AzureADTokenExchange
```

Grant the identity access to the backends. Prefer **Entra ID auth with the managed identity** over connection strings wherever the service supports it:

```bash
# Key Vault: read secrets (vault uses Azure RBAC)
az role assignment create --assignee-object-id $ORDERS_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -n kv-shop-dev --query id -o tsv)

# Service Bus: send messages
az role assignment create --assignee-object-id $ORDERS_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Azure Service Bus Data Sender" \
  --scope $(az servicebus namespace show -g $RG -n sb-shop-dev --query id -o tsv)

# Cosmos DB: data-plane RBAC (built-in Data Contributor role)
az cosmosdb sql role assignment create \
  --account-name cosmos-shop-dev -g $RG \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id $ORDERS_PRINCIPAL_ID \
  --scope "/"
```

Azure Cache for Redis and Azure Managed Redis also support Entra ID authentication; add the identity as a Redis data access user. With Entra auth, the app only needs the **endpoint names**, not passwords.

### 5. Mount Key Vault values with the CSI driver

Use Key Vault for values that are not identity-based, such as a third-party API key or a Redis access key for a cache that cannot use Entra ID yet.

`secretproviderclass-orders.yaml`:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: orders-kv
  namespace: shop
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "<ORDERS_CLIENT_ID>"     # workload identity client ID
    keyvaultName: kv-shop-dev
    tenantId: "<TENANT_ID>"
    objects: |
      array:
        - |
          objectName: payment-gateway-api-key
          objectType: secret
        - |
          objectName: cosmos-endpoint
          objectType: secret
  secretObjects:                      # optional: also sync to a Kubernetes Secret
    - secretName: orders-secrets
      type: Opaque
      data:
        - objectName: cosmos-endpoint
          key: COSMOS_ENDPOINT
```

The service account and Pod settings (these go into the Helm chart in the next step):

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders
  namespace: shop
  annotations:
    azure.workload.identity/client-id: "<ORDERS_CLIENT_ID>"
```

```yaml
# Pod template fragment
metadata:
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: orders
  containers:
    - name: orders
      volumeMounts:
        - name: secrets
          mountPath: /mnt/secrets
          readOnly: true
  volumes:
    - name: secrets
      csi:
        driver: secrets-store.csi.k8s.io
        readOnly: true
        volumeAttributes:
          secretProviderClass: orders-kv
```

Each Key Vault secret appears as a file, for example `/mnt/secrets/payment-gateway-api-key`. The synced Kubernetes Secret is only created while a Pod mounts the volume.

### 6. Create one Helm chart per microservice

Repository layout:

```text
shop-repo/
├── services/
│   ├── orders/          # source code + Dockerfile
│   └── payments/
├── charts/
│   ├── orders/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-prod.yaml
│   │   └── templates/   # deployment, service, serviceaccount, secretproviderclass, hpa
│   └── payments/
│       └── ...
├── k8s/
│   ├── network-policies.yaml
│   └── ingress.yaml
└── pipelines/
    ├── orders.yml
    ├── payments.yml
    └── templates/
        └── service-template.yml
```

`charts/orders/values.yaml` (defaults):

```yaml
image:
  repository: myacr.azurecr.io/orders
  tag: "latest"          # overridden by the pipeline with the build ID
replicaCount: 2
containerPort: 8080
serviceAccount:
  name: orders
  clientId: ""
keyVault:
  name: ""
  tenantId: ""
resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits: { memory: 256Mi }
env:
  SERVICEBUS_NAMESPACE: ""
  REDIS_HOST: ""
```

`charts/orders/values-prod.yaml` (only what differs):

```yaml
replicaCount: 4
serviceAccount:
  clientId: "<PROD_ORDERS_CLIENT_ID>"
keyVault:
  name: kv-shop-prod
  tenantId: "<TENANT_ID>"
env:
  SERVICEBUS_NAMESPACE: sb-shop-prod.servicebus.windows.net
  REDIS_HOST: redis-shop-prod.redis.cache.windows.net
resources:
  requests: { cpu: 250m, memory: 256Mi }
  limits: { memory: 512Mi }
```

`charts/orders/templates/deployment.yaml` (key parts):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app.kubernetes.io/name: orders
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: orders
  template:
    metadata:
      labels:
        app.kubernetes.io/name: orders
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: {{ .Values.serviceAccount.name }}
      containers:
        - name: orders
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.containerPort }}
          env:
            {{- range $key, $value := .Values.env }}
            - name: {{ $key }}
              value: {{ $value | quote }}
            {{- end }}
          readinessProbe:
            httpGet: { path: /healthz, port: {{ .Values.containerPort }} }
          livenessProbe:
            httpGet: { path: /healthz, port: {{ .Values.containerPort }} }
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          volumeMounts:
            - name: secrets
              mountPath: /mnt/secrets
              readOnly: true
      volumes:
        - name: secrets
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: {{ .Release.Name }}-kv
```

The chart also contains a ClusterIP Service on port 80 targeting 8080, the ServiceAccount, and the SecretProviderClass from step 5, all templated from values. An alternative is an **umbrella chart** with `orders` and `payments` as dependencies; it is useful for deploying the whole system at once, but it couples the release of all services.

Validate locally:

```bash
helm lint charts/orders -f charts/orders/values-dev.yaml
helm template orders charts/orders -f charts/orders/values-dev.yaml --set image.tag=test
```

### 7. Route traffic with an Ingress

`k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  namespace: shop
spec:
  ingressClassName: webapprouting.kubernetes.azure.com
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /orders
            pathType: Prefix
            backend:
              service:
                name: orders
                port:
                  number: 80
          - path: /payments
            pathType: Prefix
            backend:
              service:
                name: payments
                port:
                  number: 80
```

```bash
kubectl apply -f k8s/ingress.yaml
kubectl get ingress -n shop
```

The services must handle the `/orders` and `/payments` prefixes, because the path is passed through unchanged. For TLS, the add-on can use a certificate from Key Vault (`az aks approuting update --attach-kv`) with the `kubernetes.azure.com/tls-cert-keyvault-uri` annotation, and it can manage Azure DNS records.

### 8. Build the Azure DevOps pipeline

Use **one pipeline per service**, each with a path filter, so a change in `services/orders` builds and deploys only `orders`. All pipelines share one template.

`pipelines/orders.yml`:

```yaml
trigger:
  branches:
    include: [main]
  paths:
    include:
      - services/orders/*
      - charts/orders/*

pr:
  branches:
    include: [main]
  paths:
    include:
      - services/orders/*
      - charts/orders/*

extends:
  template: templates/service-template.yml
  parameters:
    serviceName: orders
```

`pipelines/templates/service-template.yml`:

```yaml
parameters:
  - name: serviceName
    type: string

variables:
  acrConnection: acr-myacr            # Docker registry service connection
  azureConnection: azure-wif          # ARM service connection (workload identity federation)
  imageRepo: ${{ parameters.serviceName }}
  tag: $(Build.BuildId)

stages:
  - stage: Build
    jobs:
      - job: BuildPush
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: Docker@2
            displayName: Build and push ${{ parameters.serviceName }}
            inputs:
              command: buildAndPush
              containerRegistry: $(acrConnection)
              repository: $(imageRepo)
              Dockerfile: services/${{ parameters.serviceName }}/Dockerfile
              buildContext: services/${{ parameters.serviceName }}
              tags: |
                $(tag)
          - script: helm lint charts/${{ parameters.serviceName }}
            displayName: Helm lint

  - stage: DeployDev
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: Deploy
        environment: shop-dev
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self          # deployment jobs do not check out code by default
                - task: AzureCLI@2
                  displayName: Helm deploy to aks-dev
                  inputs:
                    azureSubscription: $(azureConnection)
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials -g rg-dev -n aks-dev --overwrite-existing
                      kubelogin convert-kubeconfig -l azurecli
                      helm upgrade --install ${{ parameters.serviceName }} \
                        charts/${{ parameters.serviceName }} \
                        -n shop \
                        -f charts/${{ parameters.serviceName }}/values-dev.yaml \
                        --set image.tag=$(tag) \
                        --atomic --wait --timeout 5m

  - stage: DeployProd
    dependsOn: DeployDev
    condition: succeeded()
    jobs:
      - deployment: Deploy
        environment: shop-prod            # approvals and checks are set on this environment
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  displayName: Helm deploy to aks-prod
                  inputs:
                    azureSubscription: $(azureConnection)
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials -g rg-prod -n aks-prod --overwrite-existing
                      kubelogin convert-kubeconfig -l azurecli
                      helm upgrade --install ${{ parameters.serviceName }} \
                        charts/${{ parameters.serviceName }} \
                        -n shop \
                        -f charts/${{ parameters.serviceName }}/values-prod.yaml \
                        --set image.tag=$(tag) \
                        --atomic --wait --timeout 10m
```

Setup in Azure DevOps:

1. **Pipelines → Environments**: create `shop-dev` and `shop-prod`. On `shop-prod`, open **Approvals and checks** and add **Approvals** (and optionally business hours or a branch control check for `main`).
2. The ARM service connection's identity needs `Azure Kubernetes Service Cluster User Role` and an AKS RBAC role (for example `Azure Kubernetes Service RBAC Writer` on the `shop` namespace) on each cluster.
3. Create one pipeline from `pipelines/orders.yml` and one from `pipelines/payments.yml`.

Notes:

- The image is tagged with `$(Build.BuildId)`, so every deployment is traceable and rollback is just the previous tag. Avoid `latest`.
- `--atomic --wait` waits until the Pods are ready and rolls back automatically if they are not.
- The same image built once is promoted from Dev to Prod. For separate Prod registries, import the image (`az acr import`) instead of rebuilding.
- The `HelmDeploy@0` task (`command: upgrade`, `chartType: FilePath`, `arguments: --atomic --wait`) is an alternative to the inline script.

### 9. Add observability

- **Container Insights** (the `monitoring` add-on) collects container logs, node and Pod metrics, and Kubernetes events into Log Analytics. Enable **Managed Prometheus** and **Managed Grafana** for metrics dashboards if needed.
- **Application Insights**: instrument each service with the **Azure Monitor OpenTelemetry Distro** (.NET, Node.js, Python) or the **Application Insights Java agent**. Pass the connection string as an environment variable, for example in the Helm values:

```yaml
env:
  APPLICATIONINSIGHTS_CONNECTION_STRING: "<from Key Vault or values>"
  OTEL_SERVICE_NAME: orders
  JAVA_TOOL_OPTIONS: "-javaagent:/app/applicationinsights-agent.jar"   # Java only
```

Distributed tracing then shows one request flowing through ingress → orders → Service Bus → payments → Cosmos DB in the **Application map**.

KQL in Log Analytics, errors per Pod in the last hour:

```kusto
ContainerLogV2
| where TimeGenerated > ago(1h)
| where PodNamespace == "shop"
| where LogMessage has "error" or LogLevel == "error"
| summarize Errors = count() by PodName, bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

Pods that restarted:

```kusto
KubePodInventory
| where TimeGenerated > ago(1h)
| where Namespace == "shop"
| summarize Restarts = max(ContainerRestartCount) by Name
| where Restarts > 0
```

Failed requests in Application Insights:

```kusto
requests
| where timestamp > ago(1h)
| where success == false
| summarize Failures = count() by cloud_RoleName, name, resultCode
| order by Failures desc
```

### 10. Verify

```bash
kubectl get pods,svc,ingress -n shop
kubectl get networkpolicy -n shop

INGRESS_IP=$(kubectl get svc -n app-routing-system -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')
curl -H "Host: shop.example.com" http://$INGRESS_IP/orders/healthz
curl -H "Host: shop.example.com" http://$INGRESS_IP/payments/healthz

# network policy check: a test Pod without the right labels must be blocked
kubectl run test --rm -it --image=busybox -n shop --restart=Never -- \
  wget -qO- -T 3 http://payments/healthz

# secret mounted from Key Vault
kubectl exec -n shop deploy/orders -- ls /mnt/secrets

helm list -n shop
```

Expected: all Pods `Running` and ready, both `curl` calls return HTTP 200, the busybox request times out (blocked by default deny), the Key Vault files are listed, and `helm list` shows `orders` and `payments` with the image tag from the latest build.

## Important points

- **One identity per service** with only the roles it needs. Prefer Entra ID auth to Cosmos DB, Service Bus, and Redis over connection strings; use Key Vault for what cannot use Entra ID.
- Put Cosmos DB, Redis, Service Bus, Key Vault, and ACR behind **private endpoints**, and link each private DNS zone (for example `privatelink.documents.azure.com`) to the AKS VNet.
- **Default deny** network policies plus explicit allows. Cilium enforces them in eBPF, with better performance and observability than iptables.
- Do not use the retired community ingress-nginx for new clusters; use the application routing add-on or Gateway API.
- Add a HorizontalPodAutoscaler and a PodDisruptionBudget to each chart for Prod.
- Keep per-environment differences in `values-<env>.yaml`, never in the templates.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `ImagePullBackOff` | Kubelet identity has no `AcrPull`, wrong image name or tag, or ACR firewall blocks the nodes | `az aks check-acr -g rg-dev -n aks-dev --acr myacr.azurecr.io`; check the tag with `az acr repository show-tags` |
| `404` from the ingress | Wrong `host` header, wrong `ingressClassName`, path or Service name mismatch, or the app does not serve the `/orders` prefix | `kubectl describe ingress shop -n shop`; check endpoints with `kubectl get endpoints -n shop` |
| `502` or timeouts from the ingress | Network policy blocks the ingress namespace, or the Pod is not ready | Check `allow-from-ingress` selectors and port; check readiness probes |
| Service-to-service calls time out | Default deny without an allow rule, or egress deny without DNS | Add the allow policy; allow UDP/TCP 53 to `kube-system` |
| Pod stuck in `ContainerCreating` with `MountVolume.SetUp failed` for the CSI volume | Wrong `clientID` or `tenantId`, missing federated credential, missing `Key Vault Secrets User` role, or secret name typo | `kubectl describe pod`; check the federated credential subject `system:serviceaccount:shop:orders` and the role |
| Workload identity token error (`AADSTS70021`) | ServiceAccount name or namespace does not match the federated credential, or the Pod lacks the `azure.workload.identity/use` label | Fix the subject or labels and restart the Pod |
| Pods cannot reach Cosmos DB through the private endpoint | The Cosmos DB name resolves to a public IP because the private DNS zone is not linked to the AKS VNet, or custom DNS does not forward to Azure DNS | `kubectl run dns --rm -it --image=busybox -- nslookup cosmos-shop-dev.documents.azure.com`; link `privatelink.documents.azure.com` to the VNet or add a conditional forwarder |
| Pipeline deploys every service | No path filter, or a shared folder is in every filter | Use per-service `trigger.paths` |
| `helm upgrade` fails and rolls back | `--atomic` detected unready Pods | Check events and logs, fix, and run again |

## Clean up

```bash
helm uninstall orders payments -n shop
kubectl delete -f k8s/ingress.yaml -f k8s/network-policies.yaml
kubectl delete namespace shop
az identity delete -g rg-dev -n id-orders
az aks delete -g rg-dev -n aks-dev --yes --no-wait
```

## Interview questions

<details><summary>Q1. Why use one Helm chart per microservice?</summary>

Each service has its own release cycle, team, and configuration. With one chart per service, I can deploy, upgrade, and roll back `orders` without touching `payments`, and `helm history` shows the history for that service only. Each chart has small per-environment values files. An umbrella chart is useful to install the whole system at once, for example for a test environment, but it couples the releases, so I use it only where that coupling is wanted.

</details>

<details><summary>Q2. How does a user request flow through this architecture?</summary>

DNS points to the public IP of an Azure Load Balancer. The load balancer sends traffic to the managed ingress controller (application routing add-on) in `app-routing-system`. The Ingress rule matches the host and path, for example `/orders`, and forwards to the `orders` ClusterIP Service, which load-balances to ready `orders` Pods. Network policies allow this hop only from the ingress namespace. The Pod then calls Cosmos DB, Redis, or Service Bus through private endpoints, using its managed identity for authentication.

</details>

<details><summary>Q3. Why choose Azure CNI powered by Cilium?</summary>

With overlay mode, Pods get IPs from a private range, so the VNet does not run out of addresses. The Cilium eBPF dataplane replaces kube-proxy and iptables, which scales better with many Services, and it enforces network policies built in, so I do not need Calico or Azure NPM. It also supports richer policies with `CiliumNetworkPolicy`, such as FQDN and Layer 7 rules (with Advanced Container Networking Services), and better network observability.

</details>

<details><summary>Q4. How do secrets reach the Pods securely?</summary>

First, I avoid secrets where I can: Pods use workload identity, so the Pod's ServiceAccount is federated to a user-assigned managed identity, and the app gets Entra ID tokens for Cosmos DB, Service Bus, and Redis. For values that still need to be secret, the Key Vault Secrets Store CSI driver uses the same identity to read from Key Vault and mounts them as files in the Pod, optionally synced to a Kubernetes Secret. No secret is stored in Git, Helm values, or the pipeline.

</details>

<details><summary>Q5. How do you deploy only the services that changed?</summary>

Each service has its own Azure DevOps pipeline with a path filter, for example `services/orders/*` and `charts/orders/*`, and all pipelines extend one shared template. A commit that touches only `orders` triggers only the `orders` pipeline, which builds the image, tags it with the build ID, pushes it to ACR, and runs `helm upgrade --install --atomic --wait` for that release. In a single pipeline, the alternative is a script that runs `git diff` against the last successful commit and sets conditions per service.

</details>
