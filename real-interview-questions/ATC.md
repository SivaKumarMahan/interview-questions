# ATC Interview Questions

Real interview questions with simple, easy-to-read answers.

---

## 1. Local accounts in Kubernetes

If you mean **Local Accounts in Kubernetes**, this usually refers to user authentication using client certificates instead of an external identity provider.

### What are local accounts?

A local account is a user that is authenticated directly by the Kubernetes cluster, typically using an X.509 client certificate. The cluster recognizes the certificate and grants permissions based on RBAC.

Unlike Azure AD, LDAP, or OIDC users, local accounts are managed within the cluster.

### How it works

1. Generate a private key and CSR (Certificate Signing Request).
2. Sign the CSR with the cluster's Certificate Authority (CA).
3. Create a kubeconfig file containing the certificate.
4. Create an RBAC Role/ClusterRole and RoleBinding/ClusterRoleBinding.
5. The user authenticates using the client certificate.

### Example

Create a Role:

```yaml
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: pod-reader
  namespace: dev

rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
```

Bind it to a local user:

```yaml
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: pod-reader-binding
  namespace: dev

subjects:
- kind: User
  name: siva

roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

The user `siva` can now list and view pods only in the `dev` namespace.

### In AKS

By default, authentication is done through Microsoft Entra ID (formerly Azure AD). However, AKS also supports local accounts, which use the cluster-admin kubeconfig instead of Entra ID.

You can disable local accounts for better security:

```bash
az aks update \
  --resource-group myRG \
  --name myAKS \
  --disable-local-accounts
```

### Interview answer

"Local accounts are Kubernetes users authenticated directly by the cluster, usually through client certificates rather than an external identity provider like Microsoft Entra ID. Access is controlled using Kubernetes RBAC. In AKS, local accounts provide cluster-admin access through kubeconfig, but many organizations disable them and use Microsoft Entra ID to improve security, auditing, and centralized access management."

---

## 2. How do you authenticate Terraform to Azure?

This is a very common interview question. The interviewer usually wants to know the different authentication methods and when you would use each.

### Answer

Terraform authenticates to Azure through the Azure Resource Manager (AzureRM) provider. There are multiple authentication methods.

### 1. Service Principal (most common in CI/CD)

This is the most common method in Azure DevOps, Jenkins, and GitHub Actions.

Steps:

1. Create a Service Principal.
2. Assign required RBAC roles (Contributor, Reader, etc.).
3. Configure Terraform using the Service Principal credentials.

Example:

```bash
export ARM_CLIENT_ID=<client-id>
export ARM_CLIENT_SECRET=<client-secret>
export ARM_SUBSCRIPTION_ID=<subscription-id>
export ARM_TENANT_ID=<tenant-id>
```

Terraform automatically reads these environment variables.

**Interview point:** We use a Service Principal in CI/CD pipelines because it provides non-interactive authentication and follows least-privilege access.

### 2. Managed Identity (recommended for Azure-hosted workloads)

If Terraform runs on:

- Azure VM
- Azure VMSS
- AKS
- Azure Container Instance

it can use a Managed Identity.

Example:

```hcl
provider "azurerm" {
  features {}
  use_msi = true
}
```

No client secret is required.

**Interview point:** Managed Identity is more secure because Azure manages credential rotation automatically, eliminating the need to store secrets.

### 3. Azure CLI authentication (developer machines)

Developers authenticate locally by logging in with Azure CLI.

```bash
az login
```

Terraform automatically uses the Azure CLI session.

**Interview point:** This is mainly used for local development and testing.

### 4. Workload Identity Federation (recommended for modern CI/CD)

Instead of storing client secrets, Terraform authenticates using OpenID Connect (OIDC) between the CI/CD platform and Azure.

Supported platforms include:

- Azure DevOps
- GitHub Actions

No secrets are stored.

**Interview point:** This is Microsoft's recommended approach because it removes long-lived secrets and reduces the risk of credential leakage.

### 5. Azure DevOps Service Connection

In Azure DevOps, Terraform tasks commonly use an Azure Resource Manager Service Connection.

The pipeline authenticates through the service connection, which can be backed by:

- Service Principal (traditional)
- Workload Identity Federation (recommended)

No credentials need to be hardcoded in the Terraform code.

### Which method should you use?

| Scenario | Authentication Method |
|---|---|
| Local development | Azure CLI (`az login`) |
| Azure DevOps Pipeline | Azure Resource Manager Service Connection (prefer Workload Identity Federation) |
| GitHub Actions | OIDC / Workload Identity Federation |
| Azure VM or AKS | Managed Identity |
| Older CI/CD pipelines | Service Principal with client secret |

### Interview answer (30 seconds)

"Terraform authenticates to Azure using the AzureRM provider. For local development, I use Azure CLI with `az login`. In CI/CD pipelines, I prefer an Azure DevOps Service Connection or Workload Identity Federation because it avoids storing secrets. If Terraform runs on Azure resources like VMs or AKS, I use Managed Identity. In older environments, Service Principals with RBAC permissions are also commonly used. The preferred approach today is Workload Identity Federation or Managed Identity because they eliminate the need to manage client secrets."

---

## 3. VM vs Container

This is one of the most common DevOps interview questions.

| Virtual Machine (VM) | Container |
|---|---|
| Virtualizes hardware | Virtualizes the operating system |
| Has its own Guest OS | Shares the host OS kernel |
| Larger in size (GBs) | Smaller in size (MBs) |
| Takes minutes to boot | Starts in seconds or less |
| Higher resource usage | Lower resource usage |
| Better isolation | Lightweight isolation |
| Can run different operating systems | Must use the host OS kernel (Linux containers on Linux, Windows containers on Windows) |
| Managed by Hypervisor (VMware, Hyper-V, KVM) | Managed by Container Runtime (Docker, containerd) |

### VM architecture

```
Application
Application
-----------------
Guest OS
Guest OS
-----------------
Hypervisor
-----------------
Host OS
-----------------
Physical Server
```

Each VM has its own operating system, making it heavier.

### Container architecture

```
Application
Application
-----------------
Container Runtime
-----------------
Host OS Kernel
-----------------
Physical Server
```

All containers share the same host OS kernel, making them lightweight.

### Example

Suppose you have three applications.

Using VMs:

```
VM1
- Ubuntu
- Java App

VM2
- Ubuntu
- Python App

VM3
- Ubuntu
- Node.js App
```

Each VM has a complete operating system.

Using containers:

```
Container1
- Java App

Container2
- Python App

Container3
- Node.js App
```

All share the same Linux kernel. No separate operating system is needed for each application.

### Advantages of VMs

- Strong isolation
- Can run different operating systems simultaneously
- Suitable for legacy applications
- Better security boundaries for untrusted workloads

### Advantages of containers

- Fast startup
- Lightweight
- Efficient resource utilization
- Easy to scale
- Portable across environments
- Ideal for microservices and Kubernetes

### When to use VMs

- Running Windows and Linux on the same host
- Hosting legacy or monolithic applications
- Workloads requiring strong isolation
- Traditional enterprise applications

### When to use containers

- Microservices
- CI/CD pipelines
- Kubernetes deployments
- Cloud-native applications
- Rapid scaling and deployments

### Interview answer (1 minute)

"A Virtual Machine virtualizes the hardware and includes its own guest operating system, making it larger, slower to start, and more resource-intensive. A container virtualizes the operating system, shares the host OS kernel, and packages only the application and its dependencies. Because containers are lightweight, they start in seconds and allow much higher application density on the same infrastructure. In my DevOps work, we package applications as Docker containers and orchestrate them with Kubernetes for faster deployments and easier scaling, while VMs are typically used for hosting the Kubernetes nodes or for workloads that require stronger isolation or different operating systems."

---

## 4. How do you isolate the container?

This is a common Kubernetes/Docker interview question. The interviewer wants to know the Linux kernel features behind container isolation.

### Answer

Containers are isolated using Linux kernel features, not by running separate operating systems. The main isolation mechanisms are:

### 1. Namespaces (isolation)

Namespaces ensure each container has its own view of system resources.

- **PID Namespace** – Each container has its own process IDs.
- **Network Namespace** – Each container has its own IP address, routing table, and network interfaces.
- **Mount Namespace** – Each container has its own filesystem view.
- **UTS Namespace** – Each container has its own hostname.
- **IPC Namespace** – Isolates shared memory and message queues.
- **User Namespace** – Maps container users to different host users, improving security.

Example: Two containers can both have a process with PID 1 because each has its own PID namespace.

### 2. Control Groups (cgroups)

cgroups limit and monitor resource usage.

They control:

- CPU
- Memory
- Disk I/O
- Network bandwidth (indirectly through Linux traffic control)
- Number of processes

Example:

```bash
docker run --memory=512m --cpus=1 nginx
```

This container can use a maximum of 512 MB RAM and 1 CPU.

### 3. Filesystem isolation

Each container gets its own writable layer on top of read-only image layers using a storage driver such as OverlayFS.

This ensures:

- Changes in one container do not affect another.
- Containers can share image layers efficiently.

### 4. Security features

Containers are further isolated using:

- Linux Capabilities (remove unnecessary root privileges)
- Seccomp (restricts system calls)
- AppArmor or SELinux (mandatory access control)
- Read-only root filesystem (optional)
- Non-root users (recommended)

### 5. Kubernetes isolation

Kubernetes adds additional controls:

- Resource requests and limits
- Network Policies
- RBAC
- Pod Security Admission
- Security Contexts

Example:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
```

### Interview answer (1 minute)

"Containers are isolated primarily through Linux namespaces and cgroups. Namespaces isolate processes, networking, filesystems, hostnames, IPC, and users so each container sees its own environment. cgroups enforce resource limits such as CPU and memory. Filesystem isolation ensures each container has its own writable layer, while security mechanisms like seccomp, AppArmor or SELinux, Linux capabilities, and running as a non-root user further reduce risk. In Kubernetes, we strengthen isolation with Network Policies, Security Contexts, Pod Security Admission, and resource limits."

---

## 5. Provisioners in Terraform

Provisioners in Terraform are used to execute scripts or commands after a resource is created or before it is destroyed.

They are considered a last resort because they are not idempotent, can be unreliable, and make Terraform configurations harder to maintain. Whenever possible, prefer cloud-init, custom images, configuration management tools (Ansible, Chef, Puppet), or managed services.

### Types of provisioners

#### 1. local-exec

Runs a command on the machine where Terraform is executed, not on the created resource.

Example:

```hcl
resource "azurerm_linux_virtual_machine" "vm" {
  # VM configuration

  provisioner "local-exec" {
    command = "echo VM Created Successfully"
  }
}
```

Use cases:

- Send a notification
- Update an inventory file
- Call an external script
- Trigger another automation

#### 2. remote-exec

Runs commands inside the created VM over SSH (Linux) or WinRM (Windows).

Example:

```hcl
resource "azurerm_linux_virtual_machine" "vm" {
  # VM configuration

  connection {
    type        = "ssh"
    host        = self.public_ip_address
    user        = "azureuser"
    private_key = file("id_rsa")
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt update",
      "sudo apt install nginx -y",
      "sudo systemctl start nginx"
    ]
  }
}
```

Use cases:

- Install packages
- Configure software
- Start services

#### 3. file

Copies files from the local machine to the remote resource.

Example:

```hcl
provisioner "file" {
  source      = "config.conf"
  destination = "/tmp/config.conf"
}
```

### Destroy provisioner

Runs commands before Terraform destroys a resource.

```hcl
provisioner "local-exec" {
  when    = destroy
  command = "echo VM is being deleted"
}
```

### Why are provisioners discouraged?

- They are not fully tracked in Terraform state.
- Failures can leave resources partially configured.
- Re-running them consistently is difficult.
- They mix infrastructure provisioning with configuration management.

Instead, use:

- cloud-init for Linux VM initialization.
- Azure VM Custom Script Extension when appropriate.
- Ansible or similar tools for post-provisioning configuration.
- Packer to build preconfigured machine images.

### Interview answer (1 minute)

"Provisioners in Terraform execute scripts or commands after a resource is created or before it is destroyed. The three main provisioners are `local-exec`, which runs commands on the machine executing Terraform, `remote-exec`, which runs commands on the provisioned VM over SSH or WinRM, and `file`, which copies files to the remote machine. Although provisioners are useful for simple bootstrapping tasks, HashiCorp recommends avoiding them when possible because they are less reliable and not fully declarative. In production, I prefer cloud-init, Azure VM extensions, or Ansible for configuring resources after deployment."

---

## 6. Types of load balancers

This is a common interview question for Azure, Kubernetes, and networking.

### 1. Layer 4 (Transport Layer) load balancer

Works at the Transport Layer of the OSI model.

Routes traffic based on:

- IP Address
- TCP/UDP Port

It does not inspect the HTTP request.

Examples:

- Azure Load Balancer
- AWS Network Load Balancer (NLB)
- Kubernetes Service of type LoadBalancer (typically backed by a cloud L4 load balancer)

Use cases:

- High-performance TCP/UDP traffic
- SSH
- Databases
- Gaming
- VoIP

### 2. Layer 7 (Application Layer) load balancer

Works at the Application Layer.

Routes traffic based on:

- URL path
- Hostname
- HTTP headers
- Cookies

It understands HTTP/HTTPS traffic.

Examples:

- Azure Application Gateway
- NGINX Ingress Controller
- HAProxy
- AWS Application Load Balancer (ALB)

Use cases:

- Web applications
- Microservices
- API routing

Example:

```
example.com/api     → API Service
example.com/login   → Auth Service
example.com/images  → Image Service
```

### Azure load balancer types

#### 1. Public Load Balancer

- Internet-facing
- Has a public IP
- Distributes external traffic to backend VMs

Example:

```
Internet
    │
Public Load Balancer
    │
VM1   VM2   VM3
```

#### 2. Internal Load Balancer (ILB)

- Private IP only
- Used inside a VNet
- Not accessible from the internet

Example:

```
App Servers
     │
Internal Load Balancer
     │
Database Servers
```

### Kubernetes perspective

In Kubernetes, a Service of type LoadBalancer creates a cloud load balancer.

Example:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: LoadBalancer
```

On AKS:

- Azure Load Balancer provides Layer 4 load balancing.
- If you need Layer 7 features such as path-based or host-based routing, use an Ingress Controller like NGINX or Azure Application Gateway.

### Interview answer (1 minute)

"Load balancers are mainly classified into Layer 4 and Layer 7. A Layer 4 load balancer routes traffic using IP addresses and TCP/UDP ports without inspecting application data, making it suitable for high-performance network traffic. A Layer 7 load balancer understands HTTP and HTTPS, so it can perform host-based and path-based routing, SSL termination, and other application-aware features. In Azure, Azure Load Balancer is a Layer 4 load balancer, while Azure Application Gateway is a Layer 7 load balancer. In AKS, a Service of type LoadBalancer uses Azure Load Balancer, whereas an Ingress Controller provides Layer 7 routing for web applications."

---

## 7. Which load balancer have you used in Azure?

For an interview, answer based on practical experience. A strong response is:

"I have primarily used Azure Load Balancer with AKS and virtual machines. In AKS, when I create a Service of type LoadBalancer, Azure automatically provisions an Azure Load Balancer and assigns a public or internal IP. It distributes incoming TCP/UDP traffic across healthy pods. I have also configured health probes and load-balancing rules and used both public and internal load balancers depending on whether the application needed internet or private access."

If they ask for more details, you can explain the two scenarios:

### 1. Azure Load Balancer (Layer 4)

Where I used it:

- AKS Services of type LoadBalancer
- Virtual Machine Scale Sets
- High availability for applications

Features:

- TCP/UDP load balancing
- Health probes
- Public and Internal Load Balancers
- Zone-redundant support

### 2. Azure Application Gateway (Layer 7) — if applicable

If you have used it:

"For web applications, I have used Azure Application Gateway with AKS Ingress. It provides Layer 7 routing, SSL termination, path-based routing, host-based routing, and Web Application Firewall (WAF)."

### If you have only used AKS

A truthful answer is:

"In my projects, I mainly worked with Azure Load Balancer. It was automatically created by AKS when exposing applications through a LoadBalancer Service. For HTTP routing, we used an Ingress Controller, while Azure Load Balancer handled the external Layer 4 traffic."

This answer is technically accurate and reflects a common AKS deployment architecture.

---

## 8. How do you connect to AKS?

This is a very common AKS interview question.

### Answer

To connect to an AKS cluster, I use the Azure CLI to download the cluster credentials into my local kubeconfig file. After that, I use `kubectl` to interact with the cluster.

### Step 1: Login to Azure

```bash
az login
```

### Step 2: Select the subscription (if multiple subscriptions exist)

```bash
az account set --subscription "<subscription-name-or-id>"
```

### Step 3: Get AKS credentials

```bash
az aks get-credentials \
  --resource-group myResourceGroup \
  --name myAKS
```

This command downloads the cluster credentials and merges them into:

```
~/.kube/config
```

### Step 4: Verify the connection

```bash
kubectl get nodes
```

or

```bash
kubectl get pods -A
```

If the nodes or pods are listed, the connection is successful.

### How authentication works

- **Microsoft Entra ID-enabled AKS:** Your Azure identity is authenticated, and Kubernetes RBAC or Azure RBAC determines what actions you're allowed to perform.
- **Local accounts enabled:** You can use the cluster-admin kubeconfig to connect with administrative privileges.

### If the cluster is private

For a private AKS cluster, you cannot connect directly from the internet. You typically connect from:

- A VM (jump box/bastion) inside the VNet
- A machine connected through VPN or ExpressRoute
- A network that has connectivity to the AKS private endpoint

### Interview answer (1 minute)

"I first authenticate to Azure using `az login` and select the correct subscription if needed. Then I run `az aks get-credentials` with the resource group and AKS cluster name. This downloads the cluster credentials into my local kubeconfig file. After that, I verify connectivity using commands like `kubectl get nodes` or `kubectl get pods -A`. If the AKS cluster is private, I connect from a machine that has network access to the cluster, such as a jump box, VPN-connected machine, or an Azure Bastion-hosted VM."

---

## 9. What is an Ingress Controller?

This is one of the most frequently asked Kubernetes interview questions.

### What is an Ingress Controller?

An Ingress Controller is a Kubernetes component that implements the rules defined in an Ingress resource. It watches the Kubernetes API for Ingress objects and configures a reverse proxy or load balancer to route incoming HTTP/HTTPS traffic to the correct Services.

Without an Ingress Controller, an Ingress resource does nothing.

### Why do we need it?

Suppose you have three applications:

- User Service
- Order Service
- Payment Service

Without an Ingress Controller, you might expose each Service using its own LoadBalancer, resulting in multiple public IPs.

```
Internet
   │
LB1 → User Service
LB2 → Order Service
LB3 → Payment Service
```

This is more expensive and harder to manage.

With an Ingress Controller, a single external IP can route traffic to different services.

```
               Internet
                   │
           Ingress Controller
                   │
      ┌────────────┼────────────┐
      │            │            │
 /users        /orders      /payment
      │            │            │
User Service Order Service Payment Service
```

### How it works

1. A client sends an HTTP/HTTPS request.
2. The request reaches the Ingress Controller.
3. The controller checks the Ingress rules.
4. It forwards the request to the appropriate Kubernetes Service.
5. The Service sends the request to one of the backend Pods.

### Common features

- Path-based routing
- Host-based routing
- SSL/TLS termination
- URL rewriting
- Load balancing
- Authentication integration
- Rate limiting (controller-dependent)

### Example

Ingress resource:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress

spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80

      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

Requests are routed as follows:

```
example.com/api → api-service
example.com/web → web-service
```

### Popular Ingress Controllers

- NGINX Ingress Controller
- Azure Application Gateway Ingress Controller (AGIC)
- Traefik
- HAProxy
- Kong

### In AKS

A common setup is:

```
Internet
     │
Azure Load Balancer
     │
NGINX Ingress Controller
     │
Ingress Resource
     │
Kubernetes Services
     │
Pods
```

Alternatively, you can use Azure Application Gateway with Application Gateway Ingress Controller (AGIC), which uses the Application Gateway as the Layer 7 load balancer.

### Interview answer (1 minute)

"An Ingress Controller is a Kubernetes component that implements Ingress resources. It watches the Kubernetes API for Ingress rules and configures a reverse proxy to route incoming HTTP or HTTPS requests to the correct Services. It enables features such as host-based routing, path-based routing, SSL termination, and load balancing. In AKS, I've commonly used NGINX Ingress Controller with Azure Load Balancer to expose multiple applications through a single public IP. For applications requiring Azure-native Layer 7 capabilities and WAF, Azure Application Gateway with AGIC is another common choice."

---

## 10. What are the types of services in Kubernetes?

This is a very common Kubernetes interview question.

### What is a Service in Kubernetes?

A Service provides a stable network endpoint for a group of Pods. Since Pods are ephemeral and their IP addresses can change, a Service gives applications a consistent way to communicate with them.

### 1. ClusterIP (default)

- Exposes the application only inside the cluster.
- Gets an internal virtual IP.
- Cannot be accessed directly from the internet.

Use cases:

- Backend APIs
- Databases
- Internal microservices

Example:

```yaml
spec:
  type: ClusterIP
```

Flow:

```
Pod → ClusterIP Service → Backend Pods
```

### 2. NodePort

- Exposes the Service on a port of every worker node.

Accessible using:

```
NodeIP:NodePort
```

Default NodePort range:

```
30000–32767
```

Use cases:

- Testing
- Development
- When no cloud load balancer is available

Example:

```yaml
spec:
  type: NodePort
```

Flow:

```
Internet
    │
NodeIP:30080
    │
NodePort Service
    │
Pods
```

### 3. LoadBalancer

- Creates an external cloud load balancer.
- Assigns a public or private IP (depending on configuration).
- Commonly used in AKS, EKS, and GKE.

Use cases:

- Production web applications
- Public APIs

Example:

```yaml
spec:
  type: LoadBalancer
```

Flow:

```
Internet
    │
Azure Load Balancer
    │
Service
    │
Pods
```

### 4. ExternalName

- Maps a Kubernetes Service to an external DNS name.
- No Pods or Endpoints are created.

Example:

```yaml
spec:
  type: ExternalName
  externalName: database.company.com
```

Use cases:

- Accessing external databases
- Calling third-party services

Flow:

```
Application
    │
ExternalName Service
    │
database.company.com
```

### 5. Headless Service

Uses:

```yaml
clusterIP: None
```

- Kubernetes does not assign a ClusterIP.
- DNS returns the individual Pod IPs instead of a single virtual IP.

Use cases:

- StatefulSets
- Databases like Cassandra, Kafka, MongoDB
- Direct Pod-to-Pod communication

Example:

```yaml
spec:
  clusterIP: None
```

Flow:

```
Application
      │
DNS Lookup
      │
Pod1   Pod2   Pod3
```

### Summary table

| Service Type | Accessible From | IP Assigned | Common Use Case |
|---|---|---|---|
| ClusterIP | Inside cluster only | Internal ClusterIP | Internal communication |
| NodePort | NodeIP:Port | Internal + NodePort | Testing, development |
| LoadBalancer | Internet or private network | Cloud Load Balancer IP | Production applications |
| ExternalName | External DNS | No Service IP | External services/databases |
| Headless | Inside cluster | No ClusterIP | Stateful applications |

### Interview answer (1 minute)

"Kubernetes provides five Service types. ClusterIP is the default and is used for internal communication within the cluster. NodePort exposes the application on a port of every node, making it accessible using the node's IP and port. LoadBalancer provisions a cloud load balancer, such as Azure Load Balancer in AKS, to expose applications externally. ExternalName maps a Service to an external DNS name, allowing applications to access external resources through Kubernetes DNS. Headless Service does not allocate a ClusterIP and returns the IP addresses of individual Pods, making it useful for StatefulSets and distributed databases."

---

## 11. How do you expose an application in Kubernetes?

This is a common Kubernetes interview question. The interviewer wants to know the different ways to make an application accessible.

### Answer

There are several ways to expose an application in Kubernetes, depending on whether it needs to be accessed internally or externally.

### 1. ClusterIP (internal access)

- Default Service type.
- Accessible only within the Kubernetes cluster.

Example:

```yaml
spec:
  type: ClusterIP
```

Use case: Backend APIs, databases, internal microservices.

### 2. NodePort

Exposes the application on a port on every worker node.

Access using:

```
http://<NodeIP>:<NodePort>
```

Example:

```yaml
spec:
  type: NodePort
```

Use case: Development and testing.

### 3. LoadBalancer

- Creates a cloud load balancer (Azure Load Balancer in AKS).
- Assigns a public or private IP.

Example:

```yaml
spec:
  type: LoadBalancer
```

Use case: Internet-facing applications.

### 4. Ingress (recommended for multiple applications)

Instead of creating multiple LoadBalancer Services, use an Ingress Controller.

Example:

```
Internet
     │
Azure Load Balancer
     │
NGINX Ingress Controller
     │
───────────────
/app1 → Service1
/app2 → Service2
/api  → Service3
```

Benefits:

- Single public IP
- Host-based routing
- Path-based routing
- SSL/TLS termination

### 5. Port forwarding

Used only for debugging.

```bash
kubectl port-forward pod/nginx 8080:80
```

Access:

```
http://localhost:8080
```

### In AKS (production flow)

A common production architecture is:

```
Internet
     │
Azure Load Balancer
     │
NGINX Ingress Controller
     │
Ingress Resource
     │
ClusterIP Services
     │
Pods
```

Here:

- The Ingress Controller is exposed using a LoadBalancer Service.
- Backend applications remain as ClusterIP Services.
- External traffic reaches the applications through the Ingress rules.

### Interview answer (1 minute)

"Applications in Kubernetes can be exposed using different Service types. ClusterIP is used for internal communication, NodePort exposes the application on a port of each worker node, and LoadBalancer provisions a cloud load balancer for external access. For production environments with multiple web applications, I typically use an Ingress Controller. In AKS, the Ingress Controller is exposed through an Azure Load Balancer, and it routes HTTP/HTTPS traffic to backend ClusterIP Services based on hostnames or URL paths. This approach is scalable, cost-effective, and supports features like SSL termination and path-based routing."

---

## 12. What are Linux namespaces and cgroups?

This is a very common Docker and Kubernetes interview question.

### Linux namespaces

Namespaces provide isolation. They make a container think it has its own independent system by isolating resources from other containers and the host.

### Types of namespaces

| Namespace | Purpose |
|---|---|
| PID | Isolates process IDs. Each container has its own process tree. |
| NET | Isolates networking. Each container gets its own IP address, routing table, and network interfaces. |
| MNT (Mount) | Isolates filesystem mount points. |
| IPC | Isolates shared memory and message queues. |
| UTS | Allows each container to have its own hostname and domain name. |
| USER | Maps container users to different host users, improving security. |

### Example

Suppose you have two containers:

```
Container A
PID 1 → Nginx

Container B
PID 1 → Apache
```

Both processes have PID 1 inside their own containers because of the PID namespace.

### Linux cgroups (Control Groups)

cgroups control and limit how much of the system's resources a process or container can use.

They can limit:

- CPU
- Memory
- Disk I/O
- Number of processes
- Device access

### Example

Run a Docker container with limits:

```bash
docker run --memory=512m --cpus=1 nginx
```

This limits the container to:

- 512 MB RAM
- 1 CPU

If the application tries to exceed these limits:

- Memory overuse can result in an OOMKilled event.
- CPU usage is throttled to the configured limit.

### Namespaces vs cgroups

| Namespaces | cgroups |
|---|---|
| Provide isolation | Provide resource control |
| Separate processes, networking, filesystems, etc. | Limit CPU, memory, disk I/O, and other resources |
| Make containers appear independent | Prevent one container from consuming excessive resources |

### How Docker uses them

When you start a container:

1. Namespaces create an isolated environment.
2. cgroups enforce resource limits.
3. The container runtime starts the application inside that isolated, resource-controlled environment.

### How Kubernetes uses them

When you define:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

Kubernetes passes these limits to the container runtime, which uses cgroups to enforce them. The container runtime also relies on Linux namespaces to isolate the container from other workloads.

### Interview answer (1 minute)

"Linux namespaces and cgroups are the core technologies behind containers. Namespaces provide isolation by giving each container its own view of processes, networking, filesystems, hostnames, IPC, and users. This makes each container appear as if it has its own operating system. cgroups, or control groups, manage resource usage by limiting CPU, memory, disk I/O, and other resources for each container. Together, namespaces provide isolation and cgroups provide resource control, enabling multiple containers to run safely and efficiently on the same Linux host."

---

## 13. If `agent` is not given in a Jenkins Declarative Pipeline, what will happen?

This is a common Jenkins interview question.

### Answer

In a Declarative Pipeline, the `agent` directive specifies where the pipeline or a stage should run.

If you do not specify an agent, the pipeline fails with a compilation/validation error because Declarative Pipelines require an agent either:

- At the pipeline level, or
- At each stage (if `agent none` is used).

For example, this is invalid:

```groovy
pipeline {
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
    }
}
```

Error: Jenkins reports that no agent is specified.

### Valid options

#### 1. Global agent

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
    }
}
```

The pipeline runs on any available Jenkins agent.

#### 2. No global agent

```groovy
pipeline {
    agent none

    stages {
        stage('Build') {
            agent any
            steps {
                sh 'mvn clean package'
            }
        }
    }
}
```

Here, there is no global agent. Each stage must define its own agent.

### Why use `agent none`?

- Prevents reserving an agent for the entire pipeline.
- Each stage can run on a different node.
- Improves resource utilization.
- Useful when different stages require different operating systems or tools.

Example:

```groovy
pipeline {
    agent none

    stages {
        stage('Build') {
            agent { label 'linux' }
            steps {
                sh 'mvn package'
            }
        }

        stage('Deploy') {
            agent { label 'windows' }
            steps {
                bat 'deploy.bat'
            }
        }
    }
}
```

### Interview answer (30 seconds)

"In a Declarative Pipeline, an agent is mandatory. If you don't specify one, Jenkins fails to validate the pipeline because it doesn't know where to execute the stages. You can either define a global agent, such as `agent any`, or use `agent none` at the pipeline level and specify an agent for each stage individually. Using `agent none` is useful when different stages need different build nodes or you want to optimize agent usage."

---

## 14. If `steps` are not given in a Jenkins Declarative Pipeline, what will happen?

This is another common Jenkins interview question.

### Answer

In a Declarative Pipeline, every stage that performs work must contain a `steps` block.

If a stage does not have a `steps` block (or another valid stage content such as `parallel`, `matrix`, or `stages`), the pipeline fails during validation/compilation before it starts executing.

### Invalid example

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            sh 'mvn clean package'
        }
    }
}
```

This is invalid because `sh` must be inside a `steps` block.

Jenkins throws a validation error similar to:

```
Expected one of "steps", "stages", or "parallel"
```

### Correct example

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
    }
}
```

### Can a stage exist without steps?

Yes, but only if it contains another valid Declarative Pipeline section such as:

- `parallel`
- `matrix`
- Nested `stages`

Example:

```groovy
stage('Test') {
    parallel {
        stage('Unit Test') {
            steps {
                sh 'mvn test'
            }
        }
        stage('Integration Test') {
            steps {
                sh 'mvn verify'
            }
        }
    }
}
```

### Interview answer (30 seconds)

"In a Declarative Pipeline, a stage that executes commands must include a `steps` block. If it's missing, Jenkins fails validation before execution because Declarative syntax requires executable statements to be inside `steps`. The only exception is when the stage contains valid alternatives like `parallel`, `matrix`, or nested stages instead of `steps`."

---

## 15. Sample providers.tf file

A `providers.tf` file is used to configure the provider that Terraform will use. In Azure projects, this is typically the AzureRM provider.

### Example 1: Basic Azure provider

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}
```

Terraform authenticates using:

- Azure CLI (`az login`)
- Service Principal
- Managed Identity
- Workload Identity Federation

### Example 2: Provider with subscription ID

```hcl
provider "azurerm" {
  features {}

  subscription_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Example 3: Multiple Azure subscriptions

```hcl
provider "azurerm" {
  alias           = "dev"
  subscription_id = "11111111-1111-1111-1111-111111111111"
  features {}
}

provider "azurerm" {
  alias           = "prod"
  subscription_id = "22222222-2222-2222-2222-222222222222"
  features {}
}
```

Use the provider:

```hcl
resource "azurerm_resource_group" "dev_rg" {
  provider = azurerm.dev

  name     = "dev-rg"
  location = "East US"
}
```

### Example 4: Provider using Managed Identity

```hcl
provider "azurerm" {
  features {}

  use_msi = true
}
```

### Typical project structure

```
terraform-project/
├── providers.tf
├── versions.tf
├── variables.tf
├── terraform.tfvars
├── main.tf
├── outputs.tf
└── backend.tf
```

**providers.tf**

```hcl
provider "azurerm" {
  features {}
}
```

**versions.tf**

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}
```

### Interview answer

"The `providers.tf` file configures the cloud provider that Terraform uses to create and manage resources. In Azure, it typically contains the `azurerm` provider block with `features {}` and optionally settings like `subscription_id` or provider aliases for multiple subscriptions. Authentication is usually handled separately through Azure CLI, a Service Principal, Managed Identity, or Workload Identity Federation rather than hardcoding credentials in the provider configuration."

---

## 16. Sample Jenkins pipeline

Here is a simple Declarative Jenkins Pipeline that is commonly used in DevOps interviews.

### Sample Jenkins pipeline

```groovy
pipeline {
    agent any

    environment {
        APP_NAME = "myapp"
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                url: 'https://github.com/example/myapp.git'
            }
        }

        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Unit Test') {
            steps {
                sh 'mvn test'
            }
        }

        stage('SonarQube Scan') {
            steps {
                sh 'mvn sonar:sonar'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t myacr.azurecr.io/myapp:${IMAGE_TAG} .'
            }
        }

        stage('Push Docker Image') {
            steps {
                sh 'docker push myacr.azurecr.io/myapp:${IMAGE_TAG}'
            }
        }

        stage('Deploy to AKS') {
            steps {
                sh 'kubectl apply -f deployment.yaml'
                sh 'kubectl apply -f service.yaml'
            }
        }
    }

    post {
        always {
            echo 'Pipeline execution completed.'
        }

        success {
            echo 'Deployment successful.'
        }

        failure {
            echo 'Deployment failed.'
        }
    }
}
```

### Pipeline flow

```
GitHub
   │
Checkout
   │
Build (Maven)
   │
Unit Tests
   │
SonarQube Scan
   │
Docker Build
   │
Push to ACR
   │
Deploy to AKS
```

### Common stages

1. **Checkout** – Pull source code from Git.
2. **Build** – Compile the application.
3. **Test** – Run unit tests.
4. **Code Quality** – Run SonarQube analysis.
5. **Docker Build** – Create a Docker image.
6. **Push Image** – Push the image to a registry such as Azure Container Registry (ACR).
7. **Deploy** – Deploy the application to Kubernetes using `kubectl` or Helm.

### Interview answer (1 minute)

"In my projects, I use a Declarative Jenkins Pipeline. It starts by checking out the source code from Git, builds the application using Maven, runs unit tests, performs a SonarQube scan for code quality, builds a Docker image, pushes it to Azure Container Registry, and finally deploys the application to AKS using Kubernetes manifests or Helm. I also use the `post` section to handle success, failure, and cleanup tasks such as notifications or workspace cleanup."
