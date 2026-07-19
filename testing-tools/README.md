# Testing, Quality, and Security Tools

This folder is the parent location for interview material about testing, code quality, vulnerability scanning, and security validation tools used in CI/CD pipelines.

Future content should be organized into tool-specific subfolders here, for example:

- `SonarQube/` — code quality, static analysis, coverage, and quality gates
- `Trivy/` — container, filesystem, dependency, IaC, and secret scanning
- `Snyk/` — dependency, code, container, and IaC security scanning
- `Checkov/` — infrastructure-as-code policy and security checks
- `tfsec/` — Terraform security scanning
- `OWASP-ZAP/` — dynamic application security testing
- `Selenium/` — browser and UI automation
- `JUnit/` — Java unit testing and test reports
- `Pytest/` — Python testing and fixtures
- `Postman-Newman/` — API testing and command-line pipeline execution
- `JMeter/` — performance and load testing
- `k6/` — scriptable performance and load testing

Create a tool subfolder only when relevant content is added. Each subfolder should contain its own `README.md` topic index and any applicable `questions.txt`, `notes.txt`, `summary.txt`, or example files.

General testing strategy or pipeline-design questions that are not tied to one tool can be stored directly in this folder.

## Current Content

- `questions.txt` — build-time and registry-time container-image scanning
- `scenario-questions.txt` — vulnerability scanning, quality gates, provenance, security scanning, and supply-chain scenarios
- `jenkins-quality-flow-notes.md` — detailed SonarQube, Trivy, Jenkins, and notification pipeline example
- [`Checkov/`](Checkov/README.md) — detailed Terraform/IaC scanning, CI gates, troubleshooting, exceptions, and custom-policy coverage
