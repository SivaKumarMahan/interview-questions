# Python DevOps Automation and Debugging

Where Python actually gets used day-to-day in a DevOps role - infra/Kubernetes/CI-CD/log/monitoring/file/git/Docker/notification/report automation via SDKs and libraries - plus a practical playbook for debugging Python errors when they show up inside a pipeline.

For `subprocess`-based Kubernetes and Docker scripts (calling `kubectl`/`docker` as CLI tools rather than using their native Python client libraries), see [bash-python-automation-scripts.md](bash-python-automation-scripts.md) - this file focuses on library-based automation (Azure SDK, the `kubernetes` client, `requests`, etc.) and on debugging technique.

## Contents

1. [Where Python shows up in DevOps](#1-where-python-shows-up-in-devops)
2. [Infrastructure automation](#2-infrastructure-automation)
3. [Kubernetes automation via the native client](#3-kubernetes-automation-via-the-native-client)
4. [CI/CD automation](#4-cicd-automation)
5. [Log analysis](#5-log-analysis)
6. [Monitoring automation](#6-monitoring-automation)
7. [File automation](#7-file-automation)
8. [Git and Docker automation](#8-git-and-docker-automation)
9. [Email and notification automation](#9-email-and-notification-automation)
10. [Report generation](#10-report-generation)
11. [Small automation examples](#11-small-automation-examples)
12. [Python error debugging playbook](#12-python-error-debugging-playbook)
13. [Debugging a pipeline failure caused by a Python script](#13-debugging-a-pipeline-failure-caused-by-a-python-script)
14. [General Python debugging tips](#14-general-python-debugging-tips)
15. [Useful Python libraries for DevOps](#15-useful-python-libraries-for-devops)

---

## 1. Where Python shows up in DevOps

Python is widely used to automate repetitive tasks rather than doing them by hand every time:

- Infrastructure automation
- Kubernetes automation
- CI/CD automation
- Log analysis
- Monitoring
- File/configuration automation
- Git automation
- Docker automation
- Email and notification automation
- Report generation

---

## 2. Infrastructure automation

Python with the Azure SDK can create, manage, start, or stop Azure resources directly instead of shelling out to `az` CLI commands.

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

credential = DefaultAzureCredential()
client = ComputeManagementClient(credential, "<subscription-id>")

client.virtual_machines.begin_start("rg-dev", "vm01")
```

`DefaultAzureCredential` tries several authentication methods in order (managed identity, environment variables, Azure CLI login, etc.) so the same code works locally and in a pipeline without changes.

---

## 3. Kubernetes automation via the native client

The `kubernetes` Python package talks to the Kubernetes API directly, as an alternative to shelling out to `kubectl`.

```python
from kubernetes import client, config

config.load_kube_config()

v1 = client.CoreV1Api()

pods = v1.list_namespaced_pod("default")

for pod in pods.items:
    print(pod.metadata.name)
```

**Use cases:** restart pods, scale deployments, check pod health, delete failed pods automatically.

---

## 4. CI/CD automation

Python scripts running inside Jenkins or Azure DevOps pipelines can validate configuration files, trigger deployments, generate release notes, or send notifications.

```python
import requests

requests.post(
    "https://hooks.slack.com/services/...",
    json={"text": "Deployment completed successfully"}
)
```

---

## 5. Log analysis

```python
with open("app.log") as file:
    for line in file:
        if "ERROR" in line:
            print(line)
```

**Use cases:** count errors, generate reports, trigger alerts based on error patterns.

---

## 6. Monitoring automation

Python can query the Prometheus HTTP API (or Azure Monitor APIs) directly, useful when you need to act on a metric programmatically rather than just view it on a dashboard.

```python
import requests

url = "http://prometheus:9090/api/v1/query"
query = {"query": "up"}

response = requests.get(url, params=query)
print(response.json())
```

---

## 7. File automation

```python
with open("config.yaml", "r") as f:
    data = f.read()

data = data.replace("dev", "prod")

with open("config.yaml", "w") as f:
    f.write(data)
```

Useful for simple templating, though for anything beyond a trivial string swap, parsing with `PyYAML` (`yaml.safe_load`/`yaml.safe_dump`) instead of raw text replacement avoids accidentally corrupting the file structure.

---

## 8. Git and Docker automation

**Git**, via `subprocess`:

```python
import subprocess

subprocess.run(["git", "clone", "https://github.com/example/repo.git"])
```

**Docker**, via `subprocess`:

```python
import subprocess

subprocess.run(["docker", "build", "-t", "myapp:v1", "."])
subprocess.run(["docker", "push", "myapp:v1"])
```

---

## 9. Email and notification automation

```python
import smtplib

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
```

In practice, `smtplib` is more common for legacy/on-prem notification flows; Slack/Teams webhooks (as in [§4](#4-cicd-automation)) are more common in modern pipelines.

---

## 10. Report generation

Common report targets: running VMs, AKS cluster status, failed Jenkins jobs, disk usage, and Terraform execution results - typically generated by combining one of the automation patterns above (SDK/API call) with simple text/CSV/HTML output.

---

## 11. Small automation examples

### A. Restart pods stuck in CrashLoopBackOff

```python
from kubernetes import client, config

config.load_kube_config()

v1 = client.CoreV1Api()

pods = v1.list_pod_for_all_namespaces()

for pod in pods.items:
    for status in pod.status.container_statuses or []:
        if status.state.waiting and status.state.waiting.reason == "CrashLoopBackOff":
            print(f"Restarting {pod.metadata.name}")
            v1.delete_namespaced_pod(
                pod.metadata.name,
                pod.metadata.namespace
            )
```

**Use case:** automatically recover unhealthy pods. This targets `CrashLoopBackOff` specifically via `container_statuses[].state.waiting.reason`, using the native `kubernetes` client - a more targeted check than the generic `phase != "Running"` test in the `subprocess`+`kubectl -o json` pod-health-check script in `bash-python-automation-scripts.md` §5, which detects unhealthy pods but doesn't act on them.

### B. Delete old Docker images, keeping the 5 newest

```python
import subprocess

images = subprocess.check_output(
    "docker images -q",
    shell=True
).decode().split()

for image in images[5:]:
    subprocess.run(["docker", "rmi", "-f", image])
```

**Use case:** free up disk space on Jenkins agents. This is a count-based policy (keep the 5 most recent, delete the rest via list slicing) - a different approach from the age-based `docker images --format` + datetime-cutoff script in `bash-python-automation-scripts.md` §6, which filters by a 7-day age threshold instead of a fixed count. Pick whichever policy actually matches your retention need: count-based is simpler but doesn't account for build frequency; age-based accounts for time but not how many images accumulated in that time.

### C. Check disk usage

```python
import shutil

usage = shutil.disk_usage("/")

free = usage.free // (1024**3)

if free < 10:
    print("Warning: Disk space below 10 GB")
```

**Use case:** alert when disk space is running low - a pure-Python equivalent of the Bash `df`-based check, useful when the rest of the monitoring tooling is already Python.

### D. Check website health

```python
import requests

url = "https://example.com"

response = requests.get(url)

if response.status_code == 200:
    print("Application is healthy")
else:
    print("Application is down")
```

**Use case:** basic application health monitoring - a simple synthetic check, distinct from Kubernetes liveness/readiness probes since it verifies the application from outside the cluster, over the same path a real user would take.

### E. List Azure Virtual Machines

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

credential = DefaultAzureCredential()

client = ComputeManagementClient(
    credential,
    "<subscription-id>"
)

for vm in client.virtual_machines.list_all():
    print(vm.name)
```

**Use case:** generate VM inventory reports.

### F. Validate YAML before deployment

```python
import yaml

with open("deployment.yaml") as f:
    data = yaml.safe_load(f)

print(data["kind"])
```

**Use case:** validate Kubernetes manifests before applying them - catches YAML syntax errors and lets you sanity-check fields (like confirming `kind` is what you expect) before they ever reach `kubectl apply`.

---

## 12. Python error debugging playbook

Read the traceback **from the bottom up** - the last line usually contains the actual error; everything above it is the call stack that led there.

**`ModuleNotFoundError`**

```
Traceback (most recent call last):
  File "app.py", line 1, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```

Cause: the required package isn't installed. Fix: `pip install requests`.

**`FileNotFoundError`**

```
Traceback (most recent call last):
  File "app.py", line 5, in <module>
    open("config.yaml")
FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'
```

Cause: the file doesn't exist, or the path is wrong (often a relative-path/working-directory mismatch). Fix: verify the file path; use an absolute path if necessary.

**`KeyError`**

```python
data = {"name": "Siva"}
print(data["age"])
```

```
KeyError: 'age'
```

Fix: use `.get()` instead of direct indexing when a key might not exist:

```python
print(data.get("age"))
```

**`IndexError`**

```python
numbers = [10, 20]
print(numbers[5])
```

```
IndexError: list index out of range
```

Fix: check bounds before indexing:

```python
if len(numbers) > 5:
    print(numbers[5])
```

**`TypeError`**

```python
age = "25"
print(age + 5)
```

```
TypeError: can only concatenate str (not "int") to str
```

Fix: cast explicitly:

```python
print(int(age) + 5)
```

---

## 13. Debugging a pipeline failure caused by a Python script

A Jenkins or Azure DevOps pipeline fails with:

```
subprocess.CalledProcessError:
Command 'kubectl apply -f deployment.yaml'
returned non-zero exit status 1.
```

1. **Run the command manually:**

```bash
kubectl apply -f deployment.yaml
```

2. **Check the full error message** - the pipeline log often truncates or buries it among other output.
3. **Verify cluster connectivity:**

```bash
kubectl cluster-info
```

4. **Validate the YAML:**

```bash
kubectl apply --dry-run=client -f deployment.yaml
```

5. **Check pod events:**

```bash
kubectl describe pod <pod-name>
```

The pattern generalizes beyond `kubectl` specifically: reproduce the failing command outside the pipeline, get the full (not truncated) error, verify connectivity/auth to whatever system it's calling, validate the input, and check the target system's own diagnostics.

---

## 14. General Python debugging tips

- Read the traceback from the bottom up.
- Identify the exception type first - it usually tells you the *category* of problem before you've even read the message.
- Check the file name and line number the traceback points to.
- Verify environment variables and configuration files - a huge fraction of "it works locally, fails in CI" bugs are environment differences, not code bugs.
- Verify dependencies (versions, whether they're installed at all in the pipeline's environment).
- Reproduce the issue locally or in a test environment before trying to fix it blind.
- Add logging instead of relying only on `print` statements - logging carries severity levels and can be filtered/routed, print can't.

```python
import logging

logging.basicConfig(level=logging.INFO)

logging.info("Deployment started")
logging.error("Unable to connect to Kubernetes API")
```

### Short interview answer

I have used Python to automate repetitive DevOps tasks - checking server disk usage, monitoring application health over REST APIs, validating Kubernetes YAML before deployment, restarting failed pods via the Kubernetes API, generating Azure VM inventory reports via the Azure SDK, and cleaning up old Docker images on build agents. These run on a schedule via cron or as steps inside Jenkins/Azure DevOps pipelines.

When debugging Python errors, I read the traceback bottom-up to find the exception type and the exact failing line, reproduce the issue locally or in a test environment, verify inputs like config files/env vars/API responses, and add logging if needed. If it's failing inside a CI/CD pipeline specifically, I review the pipeline logs, rerun the failing command manually outside the pipeline, and validate dependencies, permissions, and any external service (Kubernetes, Azure APIs) before implementing a fix.

---

## 15. Useful Python libraries for DevOps

| Library | Purpose |
| --- | --- |
| `os` | File and OS operations |
| `subprocess` | Execute Linux commands |
| `requests` | REST API calls |
| `boto3` | AWS automation |
| `azure-identity` / `azure-mgmt-*` | Azure automation |
| `kubernetes` | Kubernetes API automation |
| `docker` | Docker API automation |
| `paramiko` | SSH to remote servers |
| `PyYAML` | Read/write YAML files |
| `json` | Handle JSON data |
| `argparse` | Build CLI tools |
| `logging` | Generate application logs |
