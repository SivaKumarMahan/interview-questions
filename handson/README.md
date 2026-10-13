# Hands-On

Step-by-step guides for real DevOps workflows on Azure: Helm, Argo CD, Azure DevOps, GitHub Actions, Terraform, Docker, AKS, and VMs. Each guide has the commands, expected results, common problems, and interview questions on the same topic.

## Helm, Argo CD, and AKS

| Guide | What you do | Tools | Time |
| --- | --- | --- | --- |
| [1. Helm chart with Dev and Prod values](01-helm-chart-dev-prod-values.md) | Build a Helm chart from scratch and deploy separate Dev and Prod releases with their own values files | Helm, kubectl | 30 min |
| [2. Azure DevOps: Terraform, Helm, ACR, AKS](02-azure-devops-terraform-helm-acr-aks.md) | One pipeline: Terraform validate, Infracost, SonarQube, plan, then Helm lint, package, push to ACR, and deploy to AKS after approval | Azure DevOps, Terraform, Infracost, SonarQube, Helm, ACR, AKS | 2 h |
| [3. Argo CD with a Helm chart from ACR](03-argocd-helm-oci-acr-aks.md) | Push a versioned chart to ACR, install Argo CD on AKS, connect the private OCI repository, and sync an Application to Healthy and Synced | Helm, ACR, AKS, Argo CD | 1 h |
| [13. Microservices on AKS with Helm and Azure DevOps](13-microservices-aks-helm-azure-devops.md) | AKS with Azure CNI powered by Cilium, application routing, network policies, workload identity and Key Vault, one Helm chart and pipeline per service | AKS, Helm, ACR, Azure DevOps, Key Vault, Azure Monitor | 3 h |

## Terraform pipelines

| Guide | What you do | Tools | Time |
| --- | --- | --- | --- |
| [4. Terraform pipeline with Infracost, SonarQube, and approval](04-terraform-pipeline-infracost-sonarqube.md) | Init, validate, fmt, cost estimate, SonarQube quality gate, plan, manual approval, and apply of the saved plan | Azure DevOps, Terraform, Infracost, SonarQube | 1.5 h |
| [5. Modular landing zone with nested maps](05-terraform-landing-zone-nested-maps.md) | Parent and child modules with nested maps, `for_each`, and dynamic blocks for RGs, VNets, NSGs, VMs, and Application Gateway, deployed by a self-hosted agent pipeline | Terraform, Azure DevOps, Trivy | 3 h |
| [6. Import existing resources through a pipeline](06-terraform-import-via-azure-devops.md) | Bring existing resource groups under Terraform with `import` blocks or `terraform import`, run from Azure DevOps, and confirm the plan shows no changes | Terraform, Azure DevOps | 1 h |
| [7. Terraform with GitHub Actions](07-terraform-github-actions-azure.md) | RG, ACR, and AKS modules deployed by GitHub Actions with OIDC, a Trivy scan, a saved plan, and environment approval, plus using an AI CLI safely to scaffold the code | Terraform, GitHub Actions, Azure | 2 h |

## Application build and deployment

| Guide | What you do | Tools | Time |
| --- | --- | --- | --- |
| [8. React multi-stage Dockerfile with Nginx](08-react-multistage-dockerfile-nginx.md) | Build a React app with Node.js and serve only the static files from a small Nginx image | Docker, Node.js, Nginx | 45 min |
| [9. Java WAR to Tomcat on a Windows agent](09-java-tomcat-azure-devops-windows-agent.md) | Maven build and automated deployment to Tomcat 9 on a Windows self-hosted agent, with a health check and rollback | Azure DevOps, Maven, Tomcat, PowerShell | 1.5 h |
| [10. Frontend to an Azure VM with Nginx](10-frontend-to-azure-vm-nginx-azure-devops.md) | Lint, SonarQube, and dependency scanning, then deploy with an Environment VM resource or over SSH | Azure DevOps, SonarQube, Trivy, Nginx | 2 h |

## Governance and code quality

| Guide | What you do | Tools | Time |
| --- | --- | --- | --- |
| [11. Only feature/* can merge into dev](11-branch-governance-feature-to-dev.md) | A pipeline stage that blocks pull requests into `dev` from non-feature branches, made required with a branch policy | Azure DevOps, Azure Repos | 45 min |
| [12. Biome and yamllint quality gates](12-biome-yamllint-azure-devops.md) | Lint and format checks for JavaScript, TypeScript, and pipeline YAML that fail the build on pull requests | Azure DevOps, Biome, yamllint | 45 min |

Suggested order for beginners: 1 → 8 → 4 → 2 → 3. Guide 1 teaches the chart basics that guides 2, 3, and 13 build on.

Replace the example names (`myacr`, `aks-dev`, `myapp-chart`, service connection names) with your own. Unlike the guides in [labs](../labs/), these have not been run end to end in this repository.
