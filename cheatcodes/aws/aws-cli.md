# AWS CLI Cheatcode

Prefer SSO or short-lived role credentials over `aws configure` with long-lived access keys.

```bash
aws sts get-caller-identity
aws configure list

aws s3 ls
aws s3 cp <file> s3://<bucket>/<key>
aws s3 cp s3://<bucket>/<key> <file>

aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running
aws ec2 describe-instance-status --include-all-instances

aws ecs list-clusters
aws ecs list-services --cluster <cluster>
aws ecs describe-services --cluster <cluster> --services <service>

aws eks describe-cluster --name <cluster>
aws eks update-kubeconfig --name <cluster> --role-arn <approved-role-arn>
```

Launching, stopping, terminating, or changing resources is intentionally omitted from the quick list because account, region, network, identity, tags, encryption, protection, and approval must be resolved first. Use reviewed IaC for repeatable infrastructure.
