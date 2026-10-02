# Python: Automation, APIs, and Data Handling

> Using Python for DevOps automation: REST APIs and FastAPI, JSON and YAML, shell commands, errors, secrets, large files, pandas missing values, scheduling, and production readiness.

## Key Concepts

### Missing Values in pandas

`isna()` (or its alias `isnull()`) flags missing values. Calling `sum()` on top of that counts them per column, since Python treats `True` as `1`.

```python
import numpy as np
import pandas as pd

data = {
    "id": [1, 4, np.nan, 9],
    "age": [30, 45, np.nan, np.nan],
    "score": [np.nan, 140, 180, 198],
}

frame = pd.DataFrame(data)

print(frame.isna().sum())
print(frame.isna().mean().mul(100).round(2))  # missing percentage
```

Finding the missing values is only step one. What you do about them depends on what "missing" actually means here:

- Use `dropna()` only when dropping those rows or columns won't skew the result.
- Use `fillna()` with a constant or a statistic you can justify, for simple cases.
- For time series, forward- or backward-filling only makes sense if the domain actually supports it.
- Add a missing-value flag when the fact that something is missing is itself useful information.
- Learn the imputation rule from the training data only, then apply that same rule to validation and test data — otherwise you leak information across the split.
- Tell apart `NaN`, `None`, empty strings, and placeholder values — they aren't always the same kind of "missing."

### Where Python shows up in DevOps

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

### Infrastructure automation

Python with the Azure SDK can create, manage, start, or stop Azure resources directly instead of shelling out to `az` CLI commands.

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

credential = DefaultAzureCredential()
client = ComputeManagementClient(credential, "<subscription-id>")

client.virtual_machines.begin_start("rg-dev", "vm01")
```

`DefaultAzureCredential` tries several authentication methods in order (managed identity, environment variables, Azure CLI login, etc.) so the same code works locally and in a pipeline without changes.

### Kubernetes automation via the native client

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

### CI/CD automation

Python scripts running inside Jenkins or Azure DevOps pipelines can validate configuration files, trigger deployments, generate release notes, or send notifications.

```python
import requests

requests.post(
    "https://hooks.slack.com/services/...",
    json={"text": "Deployment completed successfully"}
)
```

### Log analysis

```python
with open("app.log") as file:
    for line in file:
        if "ERROR" in line:
            print(line)
```

**Use cases:** count errors, generate reports, trigger alerts based on error patterns.

### Monitoring automation

Python can query the Prometheus HTTP API (or Azure Monitor APIs) directly, useful when you need to act on a metric programmatically rather than just view it on a dashboard.

```python
import requests

url = "http://prometheus:9090/api/v1/query"
query = {"query": "up"}

response = requests.get(url, params=query)
print(response.json())
```

### File automation

```python
with open("config.yaml", "r") as f:
    data = f.read()

data = data.replace("dev", "prod")

with open("config.yaml", "w") as f:
    f.write(data)
```

Useful for simple templating, though for anything beyond a trivial string swap, parsing with `PyYAML` (`yaml.safe_load`/`yaml.safe_dump`) instead of raw text replacement avoids accidentally corrupting the file structure.

### Git and Docker automation

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

### Email and notification automation

```python
import smtplib

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
```

In practice, `smtplib` is more common for legacy/on-prem notification flows; Slack/Teams webhooks (as in [§4](#4-cicd-automation)) are more common in modern pipelines.

### Report generation

Common report targets: running VMs, AKS cluster status, failed Jenkins jobs, disk usage, and Terraform execution results - typically generated by combining one of the automation patterns above (SDK/API call) with simple text/CSV/HTML output.

### Python error debugging playbook

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

### General Python debugging tips

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

### Useful Python libraries for DevOps

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

## Interview Questions

<details><summary>Q1. [Basic] How do you call a REST API in Python?</summary>

**Answer:**

I use `requests` or `httpx`, set a timeout, check the status code, validate the response, and only retry failures that are safe and temporary.

```python
import requests

url = "https://api.example.com/v1/health"
try:
    response = requests.get(url, timeout=(3, 10))
    response.raise_for_status()
    payload = response.json()
    print(payload["status"])
except requests.Timeout:
    raise SystemExit("API request timed out")
except requests.HTTPError as exc:
    raise SystemExit(f"API returned {exc.response.status_code}")
except (requests.ConnectionError, ValueError) as exc:
    raise SystemExit(f"API request failed: {exc}")
```

For authentication I get a short-lived token from managed identity or a secret store and send it in a header, and I never log it. I also handle pagination and rate limits, respect `Retry-After`, use correlation IDs, and make sure a POST is safe to retry (it won't create duplicates) before I turn retries on for it.

</details>

<details><summary>Q2. [Intermediate] How do you create API endpoints and call another API using FastAPI?</summary>

**Answer:**

FastAPI is a Python framework for building HTTP APIs. Type hints and Pydantic models validate input and automatically generate an OpenAPI schema plus interactive docs.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    quantity: int

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}

@app.post("/items", status_code=201)
async def create_item(item: Item) -> dict[str, object]:
    if item.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    return {"message": "item created", "item": item.model_dump()}
```

During development I run it with an ASGI server, for example `uvicorn main:app --reload`, and check `/docs`. Production also needs authentication and authorization, input and output models, request IDs, structured logs, metrics, rate limits, dependency timeouts, tests, and a proper deployment setup.

For an outbound call from an async endpoint, I use an async client so it doesn't block the event loop:

```python
import httpx
from fastapi import HTTPException

@app.get("/external-status")
async def external_status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.example.com/status")
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="upstream timed out") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="upstream request failed") from exc
```

In a busy service, I reuse one client across the app's lifetime instead of opening a fresh connection pool for every request. Retries stay limited, and only used for calls that are safe to repeat.

</details>

<details><summary>Q3. [Basic] How do you read and write JSON in Python?</summary>

**Answer:**

The `json` module converts JSON text to Python dictionaries and lists, and back again.

```python
import json
from pathlib import Path

config = json.loads(Path("config.json").read_text(encoding="utf-8"))
if "environment" not in config:
    raise ValueError("Missing environment")

result = {"environment": config["environment"], "status": "ready"}
Path("result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
```

I always check required fields and types, because text can be valid JSON and still not match what the application expects. For large newline-delimited JSON files, I stream one record at a time instead of loading the whole file.

For output that matters, I write to a temporary file first and then rename it. That way a crash mid-write never leaves a half-written file behind.

</details>

<details><summary>Q4. [Intermediate] How do you fetch JSON data and query it efficiently?</summary>

**Answer:**

I fetch with a timeout, check the HTTP status and the JSON structure, then pick a query approach based on the data size and how it will be accessed.

```python
import requests

def fetch_active_users(url: str) -> list[dict]:
    response = requests.get(url, timeout=(3, 10))
    response.raise_for_status()
    payload = response.json()

    users = payload.get("users")
    if not isinstance(users, list):
        raise ValueError("Response must contain a users list")

    return [
        user
        for user in users
        if isinstance(user, dict) and user.get("active") is True
    ]
```

Scanning a large list over and over is wasteful. If I'm going to look things up by the same key repeatedly, I build an index once:

```python
users_by_id = {user["id"]: user for user in active_users}
requested_user = users_by_id.get(123)  # Average O(1) lookup
```

I handle pagination and rate limits, and I never assume that because JSON is valid, it also matches the schema I expect. For very large responses, I ask the server to filter or paginate, or use a streaming JSON parser instead of loading the entire body at once.

If queries get complicated or run often against a lot of data, I move the records into a proper database with indexes instead of treating a JSON file like one. Authentication tokens stay short-lived and never get logged.

</details>

<details><summary>Q5. [Basic] How do you parse YAML in Python?</summary>

**Answer:**

I use `yaml.safe_load`. I never use `yaml.load` on input I don't fully trust, because it can build arbitrary Python objects and run code as a side effect.

```python
from pathlib import Path
import yaml

with Path("config.yaml").open(encoding="utf-8") as handle:
    config = yaml.safe_load(handle)

if not isinstance(config, dict) or "services" not in config:
    raise ValueError("config.yaml must contain a services map")
```

I catch parser errors with file and line information, and I validate the resulting structure against a schema. If comments and formatting need to survive a rewrite, I use a round-trip capable library instead of the plain loader. Any secrets referenced by the YAML are fetched separately at runtime, not stored in the file.

</details>

<details><summary>Q6. [Basic] How do you execute shell commands from Python?</summary>

**Answer:**

I use `subprocess.run` with an argument list, `check=True`, a timeout, and captured text output. I avoid `shell=True` on anything with user-controlled input, because it opens the door to command injection.

```python
import subprocess

result = subprocess.run(
    ["kubectl", "get", "pods", "-n", "payments", "-o", "json"],
    check=True,
    capture_output=True,
    text=True,
    timeout=30,
)
```

I handle `CalledProcessError` and `TimeoutExpired`, redact sensitive arguments, and prefer a Python SDK when one exists, since it's typed and easier to test. In tests I mock the subprocess call itself and check the command arguments, exit-code handling, and timeout behavior.

</details>

<details><summary>Q7. [Intermediate] Python: Kubernetes pod health check</summary>

```python
import subprocess
import json

namespace = "production"

result = subprocess.run(
    ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Unable to retrieve pods")
    exit(1)

data = json.loads(result.stdout)

failed = []

for pod in data["items"]:
    name = pod["metadata"]["name"]
    phase = pod["status"].get("phase")

    if phase != "Running":
        failed.append(name)

if failed:
    print("Unhealthy pods:")
    for pod in failed:
        print(pod)
    exit(1)

print("All pods are healthy")
```

With `namespace = "production"`, the `subprocess.run()` call is equivalent to running:

```bash
kubectl get pods -n production -o json
```

**How `subprocess.run()` is being used here:**

- The list `["kubectl", "get", "pods", "-n", namespace, "-o", "json"]` is the command and its arguments - no shell string parsing involved, which avoids shell-injection issues.
- `capture_output=True` captures stdout and stderr instead of letting them print directly to the terminal.
- `text=True` returns `result.stdout`/`result.stderr` as strings instead of bytes.
- `result.returncode` holds the exit status of the command - `0` usually means success, non-zero means failure (e.g. `if result.returncode != 0: print(result.stderr)`).

The overall flow:

```
Python script
     |
     v
subprocess.run()
     |
     v
kubectl get pods
     |
     v
Kubernetes API
     |
     v
JSON output (result.stdout)
     |
     v
json.loads()
     |
     v
Python dictionary
     |
     v
Iterate pod["status"]["phase"] and flag anything != "Running"
```

This is a common pattern for wrapping `kubectl` (or any CLI tool) in Python when you need to process structured output rather than just eyeballing text - `-o json` plus `json.loads()` turns an opaque CLI into something you can iterate over programmatically.

</details>

<details><summary>Q8. [Intermediate] Python: Docker image age script</summary>

```python
import subprocess
from datetime import datetime, timedelta

result = subprocess.run(
    ["docker", "images", "--format", "{{.ID}} {{.CreatedAt}}"],
    capture_output=True,
    text=True
)

cutoff = datetime.now() - timedelta(days=7)

for line in result.stdout.splitlines():
    print(line)
```

`docker images --format "{{.ID}} {{.CreatedAt}}"` lists every local image as `<image-id> <created-timestamp>`, using Docker's Go-template formatting to strip out everything except the two fields needed. `cutoff = datetime.now() - timedelta(days=7)` computes "7 days ago" as a comparison point.

As written, the script only prints the raw `ID CreatedAt` lines - to actually act on image age you'd parse each line's timestamp (Docker's `CreatedAt` format needs explicit parsing, e.g. with `datetime.strptime`) and compare it against `cutoff`, then collect the IDs older than the cutoff to remove with `docker rmi`. This is the same overall shape as the pod-health-check script: shell out with `subprocess.run()`, capture structured-ish text output, then parse and filter it in Python.

</details>

<details><summary>Q9. [Basic] How do you handle errors in Python scripts?</summary>

**Answer:**

I catch specific exceptions at the point where the code can either recover or add useful context. I avoid `except Exception: pass` because it just hides the failure instead of dealing with it.

```python
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def load_config(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"Config file not found: {path}") from exc
    except PermissionError as exc:
        raise RuntimeError(f"Cannot read config file: {path}") from exc
```

At the outer boundary of the program, I log the failure once and return a non-zero exit code. Cleanup happens through context managers or `finally`.

I also separate retryable failures from validation errors, keep secrets out of exception messages, and test the failure paths themselves: timeouts, invalid input, partial output, and a dependency that isn't available.

</details>

<details><summary>Q10. [Intermediate] Debugging a pipeline failure caused by a Python script</summary>

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

</details>

<details><summary>Q11. [Intermediate] How do you manage secrets in Python automation?</summary>

**Answer:**

I authenticate with managed identity, workload identity, or another short-lived mechanism, and fetch secrets at runtime from Vault or a cloud secret manager. Environment variables can work as a delivery method in some setups, but they still need protection, since child processes and diagnostic tools can expose them.

I never commit secrets, put them in default arguments, print them, or let them end up in exception messages. Access is scoped to only what's needed, audited, and rotated regularly. The code only receives a secret at the point where it's used, and never writes it to disk.

If a secret does get exposed, I revoke it first, then review logs and access history, rotate any downstream credentials, remove retained output, and add a test or a scan so it doesn't happen again.

</details>

<details><summary>Q12. [Intermediate] How do you process large log files in Python?</summary>

**Answer:**

I stream the file line by line instead of loading it all into memory. This example counts status codes:

```python
from collections import Counter

counts = Counter()
with open("access.log", encoding="utf-8", errors="replace") as handle:
    for line_number, line in enumerate(handle, start=1):
        parts = line.split()
        if len(parts) < 9:
            continue
        counts[parts[8]] += 1

print(counts.most_common())
```

For production use, I define the expected log format, count the malformed records instead of silently skipping them, use generators, read compressed files directly, write output incrementally, and checkpoint long runs. I also measure throughput and memory.

If the volume keeps growing or becomes continuous, I move parsing to a log platform or streaming system instead of stretching one script past its limits.

</details>

<details><summary>Q13. [Basic] How do you schedule Python automation?</summary>

**Answer:**

The right choice depends on runtime, retry needs, environment, and who owns operating it. Options include cron or systemd timers, GitHub Actions or Azure Pipelines schedules, Kubernetes CronJobs, Azure Functions timers, and workflow orchestrators.

For a Kubernetes CronJob, I set the concurrency policy, deadlines, history limits, resource requests, and failure alerts. Whatever the scheduler, the script must be safe to run more than once, and it needs a distributed lock if overlapping runs would cause problems.

I record the start and end time, how many items were processed, the result, and a correlation ID. I test missed schedules, timeouts, partial failures, retries, daylight-saving and time-zone behavior, and manual reruns.

Secrets come from workload identity or a secret manager, never from the schedule definition itself.

</details>

<details><summary>Q14. [Intermediate] How do you make a Python script production-ready?</summary>

**Answer:**

My checklist:

- `argparse` or typed configuration with validation
- Structured logs with correlation IDs and no secrets
- Specific exception handling, timeouts, limited retries, and exit codes
- A way to run the script again safely without causing duplicate side effects
- Unit and integration tests, linting, typing, and security scans
- Pinned dependencies and reproducible packaging
- An identity with only the access it needs, and secrets kept outside the code
- Metrics, alerts, and a documented runbook

I test the happy path, invalid input, a dependency being down, partial failure, retries, and running the script twice in a row. A script isn't production-ready just because it worked once on a laptop. Someone else needs to be able to run it, watch it, stop it, and recover from a failure safely.

</details>

<details><summary>Q15. [Intermediate] Python script: restart pods stuck in CrashLoopBackOff</summary>

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

**Use case:** automatically recover unhealthy pods. This targets `CrashLoopBackOff` specifically via `container_statuses[].state.waiting.reason`, using the native `kubernetes` client - a more targeted check than the generic `phase != "Running"` test in the `subprocess`+`kubectl -o json` pod-health-check script elsewhere in this file, which detects unhealthy pods but doesn't act on them.

</details>

<details><summary>Q16. [Intermediate] Python script: delete old Docker images, keeping the 5 newest</summary>

```python
import subprocess

images = subprocess.check_output(
    "docker images -q",
    shell=True
).decode().split()

for image in images[5:]:
    subprocess.run(["docker", "rmi", "-f", image])
```

**Use case:** free up disk space on Jenkins agents. This is a count-based policy (keep the 5 most recent, delete the rest via list slicing) - a different approach from the age-based `docker images --format` + datetime-cutoff script elsewhere in this file, which filters by a 7-day age threshold instead of a fixed count. Pick whichever policy actually matches your retention need: count-based is simpler but doesn't account for build frequency; age-based accounts for time but not how many images accumulated in that time.

</details>

<details><summary>Q17. [Intermediate] Python script: check disk usage</summary>

```python
import shutil

usage = shutil.disk_usage("/")

free = usage.free // (1024**3)

if free < 10:
    print("Warning: Disk space below 10 GB")
```

**Use case:** alert when disk space is running low - a pure-Python equivalent of the Bash `df`-based check, useful when the rest of the monitoring tooling is already Python.

</details>

<details><summary>Q18. [Intermediate] Python script: check website health</summary>

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

</details>

<details><summary>Q19. [Intermediate] Python script: list Azure Virtual Machines</summary>

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

</details>

<details><summary>Q20. [Intermediate] Python script: validate YAML before deployment</summary>

```python
import yaml

with open("deployment.yaml") as f:
    data = yaml.safe_load(f)

print(data["kind"])
```

**Use case:** validate Kubernetes manifests before applying them - catches YAML syntax errors and lets you sanity-check fields (like confirming `kind` is what you expect) before they ever reach `kubectl apply`.

</details>
