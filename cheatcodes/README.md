# DevOps Cheatcodes

Command-heavy material extracted from the screenshots is grouped here by tool. Commands contain placeholders and should be tested in a non-production environment first.

- [Kubernetes and kubectl](kubernetes/kubectl.md)
- [Terraform](terraform/terraform.md)
- [GitHub Actions](github-actions/workflows.md)
- [Jenkins](jenkins/jenkinsfile-and-cli.md)
- [Argo CD and GitOps](gitops/argocd.md)
- [Docker](docker/docker.md)
- [Ansible](ansible/ansible.md)
- [TLS certificates](security/tls.md)
- [Linux](linux/linux.md)
- [Shell scripts](shell-scripting/scripts.md)
- [Git](git/git.md)
- [AWS CLI](aws/aws-cli.md)

Safety rules:

- Resolve exact environment, account, cluster, namespace, resource, and file path before changing anything.
- Prefer read-only inspection before mutation.
- Never paste credentials into commands, YAML, Git, process arguments, or logs.
- Review destructive commands and backups; broad deletion examples from internet cheat sheets are intentionally omitted.
- Versions in screenshots age quickly. Use versions supported by the current platform and pin dependencies/actions according to repository policy.
