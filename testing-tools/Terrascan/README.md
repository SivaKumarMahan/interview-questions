# Complete DevSecOps Guide to Terrascan for Infrastructure as Code Security

## Why Infrastructure Security Scanning Matters

### The Hidden Cost of Misconfigurations

Real-world impact of IaC security failures:

- 🏦 **Capital One (2019):** Misconfigured WAF led to 100+ million customer records exposed.
- 📊 **Elasticsearch incidents:** Thousands of instances leaked sensitive data due to default configurations.
- ☁️ **AWS S3 breaches:** Countless incidents from misconfigured bucket permissions.
- 🔐 **Kubernetes exposures:** APIs accidentally exposed to the internet via network policies.

### Common Infrastructure Security Risks

| Risk Category | Examples | Impact Level |
| --- | --- | --- |
| Network Security | Open security groups, exposed databases | 🔴 Critical |
| Access Control | Overprivileged IAM roles, public buckets | 🔴 Critical |
| Encryption | Unencrypted storage, data in transit | 🟠 High |
| Compliance | Missing logging, audit trails | 🟡 Medium |
| Resource Management | Untagged resources, cost overruns | 🟡 Medium |

## What is Terrascan?

Terrascan is an open-source static code analyzer created by Tenable, specially designed for Infrastructure as Code security. It's your first line of defense against configuration vulnerabilities.

### Key Features That Set Terrascan Apart

- ✅ **Multi-Cloud Support:** AWS, Azure, GCP, Kubernetes
- ✅ **Multiple IaC Tools:** Terraform, Helm, Kubernetes, Docker
- ✅ **Custom Policies:** Write organization-specific security rules
- ✅ **CI/CD Integration:** Seamless DevOps workflow integration
- ✅ **Compliance Frameworks:** SOC 2, PCI DSS, GDPR, HIPAA
- ✅ **Active Community:** Regular updates and policy additions

### Terrascan vs Competitors

| Feature | Terrascan | Checkov | tfsec | Bridgecrew |
| --- | --- | --- | --- | --- |
| Open Source | ✅ Free | ✅ Free | ✅ Free | ❌ Paid |
| Custom Policies | ✅ Rego | ✅ Python | ❌ Limited | ✅ Advanced |
| Multi-Cloud | ✅ Excellent | ✅ Good | ✅ Good | ✅ Excellent |
| Docker Scanning | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| Learning Curve | 🟡 Moderate | 🟢 Easy | 🟢 Easy | 🔴 Steep |

## Installation and Setup

### Method 1: Homebrew (Mac/Linux)

```bash
# Install via Homebrew (recommended for Mac)
brew install terrascan

# Verify installation
terrascan version
```

### Method 2: Manual Installation

```bash
# Download latest release
curl -L "$(curl -s https://api.github.com/repos/tenable/terrascan/releases/latest | grep -o -E "https://.+?_Darwin_x86_64.tar.gz")" > terrascan.tar.gz

# Extract and install
tar -xf terrascan.tar.gz terrascan && rm terrascan.tar.gz
sudo install terrascan /usr/local/bin && rm terrascan

# Verify installation
terrascan version
```

### Method 3: Docker

```bash
# Run as Docker container
docker run --rm tenable/terrascan version

# Scan current directory
docker run --rm -it -v "$(pwd):/iac" -w /iac tenable/terrascan scan
```

## Basic Usage and Commands

### Your First Scan

Navigate to any directory containing Infrastructure as Code files and run:

```bash
# Basic scan - scans all supported files in current directory
terrascan scan
```

Example output:

```text
Violated Policies (7):
  LOW     | Ensure S3 bucket has versioning enabled
  MEDIUM  | Ensure S3 bucket has access logging enabled
  HIGH    | Ensure S3 bucket is not publicly readable
  HIGH    | Security group allows ingress from 0.0.0.0/0 to port 22
```

### Essential Command Flags

```bash
# Get comprehensive help
terrascan --help
terrascan scan --help
```

```text
Flags:
      --config-only               will output resource config (should only be used for debugging purposes)
      --config-with-error         will output resource config and errors (if any)
      --find-vuln                 fetches vulnerabilities identified in Docker images
  -h, --help                      help for scan
  -d, --iac-dir string            path to a directory containing one or more IaC files (default ".")
  -f, --iac-file string           path to a single IaC file
  -i, --iac-type string           iac type (arm, cft, docker, helm, k8s, kustomize, terraform, tfplan)
      --iac-version string        iac version (arm: v1, cft: v1, docker: v1, helm: v3, k8s: v1, kustomize: v2, v3, v4, terraform: v12, v13, v14, v15, tfplan: v1)
      --non-recursive             do not scan directories and modules recursively
  -p, --policy-path stringArray   policy path directory
  -t, --policy-type strings       policy type (all, aws, azure, docker, gcp, github, k8s) (default [all])
  -r, --remote-type string        type of remote backend (git, s3, gcs, http, terraform-registry)
  -u, --remote-url string         url pointing to remote IaC repository
      --repo-ref string           branch of the repo being scanned
      --repo-url string           URL of the repo being scanned, will be reflected in scan summary
      --scan-rules strings        one or more rules to scan (example: --scan-rules="ruleID1,ruleID2")
      --severity string           minimum severity level of the policy violations to be reported by terrascan
      --show-passed               display passed rules, along with violations
      --skip-rules strings        one or more rules to skip while scanning (example: --skip-rules="ruleID1,ruleID2")
      --use-colors string         color output (auto, t, f) (default "auto")
      --use-terraform-cache       use terraform init cache for remote modules (when used directory scan will be non recursive, flag applicable only with terraform IaC provider)
      --values-files strings      one or more values files to scan(applicable for iactype=helm) (example: --values-files="file1-values.yaml,file2-values.yaml")
  -v, --verbose                   will show violations with details (applicable for default output)
      --webhook-token string      optional token used when sending authenticated requests to the notification webhook
      --webhook-url string        webhook URL where Terrascan will send JSON scan report and normalized IaC JSON

Global Flags:
  -c, --config-path string      config file path
  -l, --log-level string        log level (debug, info, warn, error, panic, fatal) (default "info")
      --log-output-dir string   directory path to write the log and output files
  -x, --log-type string         log output type (console, json) (default "console")
  -o, --output string           output type (human, json, yaml, xml, junit-xml, sarif, github-sarif) (default "human")
      --temp-dir string         temporary directory path to download remote repository,module and templates
```

### Target-Specific Scanning

```bash
# Scan specific cloud provider
terrascan scan -t aws           # AWS only
terrascan scan -t azure         # Azure only
terrascan scan -t gcp           # GCP only
terrascan scan -t k8s           # Kubernetes only

# Scan specific IaC type
terrascan scan -i terraform     # Terraform files
terrascan scan -i helm          # Helm charts
terrascan scan -i docker        # Dockerfiles
terrascan scan -i k8s           # Kubernetes manifests
```

### Output Format Options

```bash
# JSON output for automation
terrascan scan -o json

# YAML output
terrascan scan -o yaml

# SARIF format for GitHub integration
terrascan scan -o sarif

# JUnit XML for CI reporting
terrascan scan -o junit-xml
```

Try out different flags with the command:

```bash
terrascan scan -t gcp -i terraform -o json --severity "High"
```

## Advanced Scanning Techniques

### Severity-Based Filtering

```bash
# Only show high severity issues
terrascan scan --severity "High"

# Show medium and high severity
terrascan scan --severity "Medium"

# Verbose output with details
terrascan scan -v
```

### File and Directory Targeting

```bash
# Scan specific file
terrascan scan -f main.tf

# Scan specific directory
terrascan scan -d /path/to/terraform/modules

# Non-recursive scan (current directory only)
terrascan scan --non-recursive
```

### Rule Management

```bash
# Skip specific rules
terrascan scan --skip-rules="AWS.S3.DS.High.1041,AWS.EC2.NetworkACL.Medium.0506"

# Scan only specific rules
terrascan scan --scan-rules="AWS.S3.DS.High.1041,AWS.RDS.DS.High.1025"

# Show passed rules along with violations
terrascan scan --show-passed
```

### Remote Repository Scanning

```bash
# Scan remote Git repository
terrascan scan -r git -u https://github.com/user/repo.git

# Scan specific branch
terrascan scan -r git -u https://github.com/user/repo.git --repo-ref develop

# Scan Terraform modules from registry
terrascan scan -r terraform-registry -u terraform-aws-modules/vpc/aws
```

### Configuration Debugging

```bash
# Output resource configuration for debugging
terrascan scan --config-only -o json

# Show configuration with errors
terrascan scan --config-with-error

# Enable debug logging
terrascan scan -l debug
```

## Docker Integration

### Scanning Dockerfiles

```bash
# Scan Dockerfiles for vulnerabilities
terrascan scan -i docker

# Find vulnerabilities in container images
terrascan scan -i docker --find-vuln
```

### Running Terrascan in Docker

```bash
# Basic Docker usage
docker run --rm -v "$(pwd):/iac" -w /iac tenable/terrascan scan

# With specific parameters
docker run --rm -v "$(pwd):/iac" -w /iac tenable/terrascan scan -i terraform -t aws -o json
```

## CI/CD Pipeline Integration

### GitHub Actions Integration

Create `.github/workflows/terrascan.yml`:

```yaml
name: Terrascan Security Scan
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  terrascan_job:
    runs-on: ubuntu-latest
    name: Terrascan Security Analysis
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3

    - name: Run Terrascan
      id: terrascan
      uses: tenable/terrascan-action@main
      with:
        iac_type: 'terraform'
        iac_version: 'v15'
        policy_type: 'aws'
        only_warn: true
        sarif_upload: true

    - name: Upload SARIF file
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: terrascan.sarif
```

### GitLab CI Integration

Add to `.gitlab-ci.yml`:

```yaml
terrascan_security:
  stage: security
  image: tenable/terrascan:latest
  script:
    - terrascan scan -i terraform -t aws -o json --config-path terrascan-config.toml
  artifacts:
    reports:
      sast: terrascan-results.json
  only:
    - merge_requests
    - main
```

### Jenkins Integration

```groovy
pipeline {
    agent any
    stages {
        stage('Terrascan Security Scan') {
            steps {
                script {
                    docker.image('tenable/terrascan:latest').inside {
                        sh 'terrascan scan -i terraform -o junit-xml > terrascan-results.xml'
                    }
                }
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'terrascan-results.xml'
                }
            }
        }
    }
}
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
- repo: https://github.com/tenable/terrascan
  rev: v1.18.0
  hooks:
  - id: terrascan
    args: ['scan', '-i', 'terraform', '--severity', 'High']
    verbose: true
```

Install and use:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run terrascan --all-files
```

## Custom Security Policies

### Understanding Rego Policy Language

Terrascan uses Rego (from Open Policy Agent) for custom policies. This allows you to create organization-specific security rules.

### Example: Prevent Public SSH Access

Create `custom-policies/terraform/no_public_ssh/rule.rego`:

```rego
package accurics

# Rule to deny SSH access from 0.0.0.0/0
deny_public_ssh[msg] {
    resource := input.aws_security_group[_]
    rule := resource.config.ingress[_]
    rule.from_port <= 22
    rule.to_port >= 22
    rule.cidr_blocks[_] == "0.0.0.0/0"

    msg := sprintf("Security group '%s' allows SSH (port 22) from 0.0.0.0/0", [resource.name])
}
```

### Example: Enforce Resource Tagging

Create `custom-policies/terraform/require_tags/rule.rego`:

```rego
package accurics

required_tags := ["Environment", "Owner", "Project"]

# Check if EC2 instances have required tags
deny_missing_tags[msg] {
    resource := input.aws_instance[_]
    missing_tags := required_tags[_]
    not resource.config.tags[missing_tags]

    msg := sprintf("EC2 instance '%s' is missing required tag '%s'", [resource.name, missing_tags])
}
```

### Using Custom Policies

```bash
# Scan with custom policies
terrascan scan -p ./custom-policies

# Combine with built-in policies
terrascan scan -p ./custom-policies -t aws
```

### Policy Development Best Practices

1. **Start Simple:** Begin with basic rules and iterate.
2. **Test Thoroughly:** Use different scenarios to validate policies.
3. **Document Rules:** Include clear descriptions and examples.
4. **Version Control:** Store policies in Git with your infrastructure code.
5. **Peer Review:** Have security and DevOps teams review custom policies.

## Best Practices and Recommendations

### 1. Implement Shift-Left Security

```bash
# Run in development environment
terrascan scan -i terraform --severity High

# Integrate with IDE plugins
# Use VS Code Terrascan extension
```

### 2. Create Security Gates

```yaml
# GitHub Actions example with failure conditions
- name: Terrascan Security Gate
  run: |
    terrascan scan -i terraform -o json > results.json
    HIGH_ISSUES=$(jq '.results.violations[] | select(.severity == "HIGH") | length' results.json)
    if [ "$HIGH_ISSUES" -gt 0 ]; then
      echo "❌ High severity security issues found. Blocking deployment."
      exit 1
    fi
```

### 3. Configure Organization Policies

Create `terrascan-config.toml`:

```toml
[rules]
    skip-rules = [
        "AWS.S3.DS.High.1041",  # Allow specific exceptions
    ]

[severity]
    level = "MEDIUM"

[output]
    format = "json"

[notifications]
    webhook-url = "https://hooks.slack.com/your-webhook"
```

### 4. Regular Policy Updates

```bash
# Stay updated with latest policies
docker pull tenable/terrascan:latest

# Check for new rule releases
terrascan scan --help | grep -A 20 "policy-type"
```

## Troubleshooting Common Issues

### Issue 1: False Positives

**Problem:** Legitimate configurations flagged as violations.

**Solution:**

```bash
# Skip specific rules for false positives
terrascan scan --skip-rules="RULE_ID_1,RULE_ID_2"
```

```hcl
# Use inline comments in Terraform
resource "aws_s3_bucket" "example" {
  # ts:skip=AWS.S3.DS.High.1041 Business requirement for public access
  bucket = "my-public-bucket"
}
```

### Issue 2: Performance with Large Codebases

**Problem:** Slow scanning on large repositories.

**Solution:**

```bash
# Use non-recursive scanning
terrascan scan --non-recursive

# Scan specific directories
terrascan scan -d terraform/modules/security

# Use .terrascignore file
echo "*.backup" > .terrascignore
echo "test/" >> .terrascignore
```

### Issue 3: Custom Policy Errors

**Problem:** Rego policy compilation errors.

**Solution:**

```bash
# Test policy syntax
opa fmt custom-policies/

# Validate policy structure
opa test custom-policies/
```

## Advanced Configuration Options

### Webhook Integration

```bash
# Send results to webhook
terrascan scan --webhook-url https://your-webhook.com/endpoint --webhook-token your-token
```

### Multi-Environment Scanning

```bash
# Development environment
terrascan scan -d environments/dev --severity Low

# Production environment
terrascan scan -d environments/prod --severity High --config-path prod-config.toml
```

## Security Scanning Metrics and KPIs

Track your infrastructure security improvements:

| Metric | Target | Measurement |
| --- | --- | --- |
| Critical Issues | 0 | High severity violations |
| Scan Coverage | 100% | % of IaC files scanned |
| Policy Compliance | >95% | Passed rules / Total rules |
| Mean Time to Fix | <24h | Time from detection to resolution |

## Conclusion

Infrastructure security can't be an afterthought anymore. With the rise in cloud misconfigurations leading to major breaches, scanning your Infrastructure as Code is no longer optional — it's essential.

Key takeaways:

- 🔒 **Prevention is cheaper than remediation** – Catch issues before deployment.
- ⚡ **Automation is key** – Integrate scanning into your CI/CD pipeline.
- 📋 **Custom policies matter** – Tailor security rules to your organization.
- 📊 **Measure and improve** – Track security metrics and continuously improve.

Terrascan makes infrastructure security scanning accessible and powerful, automatically checking your code against hundreds of security policies while allowing complete customization for your organization's specific needs.

Start implementing Terrascan today, and transform your infrastructure security from reactive to proactive.

## Official References

- [Terrascan documentation](https://runterrascan.io/)
- [Terrascan GitHub repository](https://github.com/tenable/terrascan)
- [Open Policy Agent / Rego](https://www.openpolicyagent.org/docs/latest/policy-language/)
