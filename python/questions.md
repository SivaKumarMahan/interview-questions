# Python Interview Questions

### 1. How is Python useful for DevOps?

**Answer:**

Python is useful when automation needs more structure than a short shell script. I use it for REST APIs, cloud SDKs, log parsing, validation, reports, operational tools, and pipeline helpers.

A practical example is an unused-resource report: authenticate with workload identity, list cloud disks, filter unattached resources older than a threshold, estimate cost, and create a report. The first version runs in dry-run mode; deletion requires approval and revalidation.

For production automation I add argument parsing, structured logging, timeouts, retries with backoff, tests, dependency locking, useful exit codes, and metrics. I do not hardcode credentials or catch every exception without handling it.

---

### 2. How do you call a REST API in Python?

**Answer:**

I use `requests` or `httpx`, set a timeout, check status codes, validate the response, and retry only safe transient failures.

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

For authentication I retrieve a short-lived token from managed identity or a secret store and send it in a header without logging it. I handle pagination and rate limits, respect `Retry-After`, use correlation IDs, and make POST retries idempotent before enabling them.

---

### 3. How do you handle errors in Python scripts?

**Answer:**

I catch specific exceptions at the layer that can recover or add useful context. I avoid `except Exception: pass` because it hides failure.

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

At the program boundary I log the failure once and return a non-zero exit code. Cleanup uses context managers or `finally`. I distinguish retryable failures from validation errors, never include secrets in exception messages, and test failure paths such as timeout, invalid input, partial output, and unavailable dependencies.

---

### 4. How do you read and write JSON in Python?

**Answer:**

The `json` module converts JSON to Python dictionaries/lists and back.

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

I validate required fields and types because valid JSON may still violate the application schema. For large newline-delimited JSON files I stream one record at a time. For important output I write to a temporary file and atomically rename it so a crash does not leave a half-written file.

---

### 5. How do you parse YAML in Python?

**Answer:**

I use `yaml.safe_load`, never `yaml.load` on untrusted input because unsafe constructors can execute arbitrary objects.

```python
from pathlib import Path
import yaml

with Path("config.yaml").open(encoding="utf-8") as handle:
    config = yaml.safe_load(handle)

if not isinstance(config, dict) or "services" not in config:
    raise ValueError("config.yaml must contain a services map")
```

I catch parser errors with file and line information, validate the resulting structure against a schema, and avoid rewriting YAML if comments and formatting must be preserved unless I use a round-trip capable library. Secrets referenced by the YAML are fetched separately at runtime.

---

### 6. How do you execute shell commands from Python?

**Answer:**

I use `subprocess.run` with an argument list, `check=True`, a timeout, and captured text output. I avoid `shell=True` for user-controlled input because it can cause command injection.

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

I handle `CalledProcessError` and `TimeoutExpired`, redact sensitive arguments, and prefer a Python SDK when it provides typed and testable behavior. In tests I mock the subprocess boundary and verify command arguments, exit-code handling, and timeout behavior.

---

### 7. How do you manage secrets in Python automation?

**Answer:**

I authenticate using managed identity, workload identity, or another short-lived mechanism and fetch secrets at runtime from Vault or a cloud secret manager. Environment variables are acceptable as a delivery mechanism in some systems but must still be protected because child processes and diagnostics may expose them.

I never commit secrets, put them in default arguments, print them, or include them in exception messages. Access is least privilege, audited, and rotated. The code receives the secret only where needed and does not write it to disk.

If a secret is exposed, I revoke it first, review logs and access history, rotate downstream credentials, remove retained output, and add tests or scanning to prevent recurrence.

---

### 8. How do you create a Python virtual environment?

**Answer:**

A virtual environment isolates project packages from the system Python.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
deactivate
```

On Windows activation is commonly `.venv\Scripts\Activate.ps1`. I do not commit `.venv`; I commit a dependency definition and lock file where appropriate. CI creates a clean environment each run, installs pinned dependencies, scans them, and tests against supported Python versions. Containers are another isolation boundary but do not remove the need for dependency pinning.

---

### 9. How do you process large log files in Python?

**Answer:**

I stream the file line by line rather than loading it into memory. The following counts status codes:

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

For production I define the log format, count malformed records, use generators, process compressed files directly, write output incrementally, and checkpoint long runs. I measure throughput and memory. If data volume becomes continuous or distributed, I move parsing to a log platform or streaming system rather than making one script handle unlimited scale.

---

### 10. How do you make a Python script production-ready?

**Answer:**

My checklist includes:

- `argparse` or typed configuration with validation
- Structured logs with correlation IDs and no secrets
- Specific exception handling, timeouts, bounded retries, and exit codes
- Idempotency or a safe resume strategy
- Unit and integration tests, linting, typing, and security scans
- Pinned dependencies and reproducible packaging
- Least-privilege identity and external secrets
- Metrics/alerts and a documented runbook

I test success, invalid input, dependency outage, partial failure, retry, and repeated execution. A script is not production-ready merely because it works once on a laptop; another operator must be able to run, observe, stop, and recover it safely.

---

### 11. What is the difference between a list, tuple, set, and dictionary?

**Answer:**

- A **list** is ordered and mutable; use it for a sequence that can change.
- A **tuple** is ordered and immutable; use it for a fixed record or hashable composite value.
- A **set** stores unique hashable values and is efficient for membership tests.
- A **dictionary** maps unique hashable keys to values and preserves insertion order in current Python versions.

```python
servers = ["web1", "web2"]
endpoint = ("db.internal", 5432)
regions = {"centralindia", "eastus"}
ports = {"http": 80, "https": 443}
```

I choose based on semantics, not only syntax. For example, a set removes duplicates but does not represent a business ordering; a dictionary makes named lookup clearer than relying on list positions.

---

### 12. How do you schedule Python automation?

**Answer:**

The choice depends on runtime, retry needs, environment, and operational ownership. Options include cron/systemd timers, GitHub Actions or Azure Pipelines schedules, Kubernetes CronJobs, Azure Functions timers, and workflow orchestrators.

For a Kubernetes CronJob I set concurrency policy, deadlines, history limits, resource requests, and failure alerts. For any scheduler, the script must be idempotent and use a distributed lock if overlapping runs would be unsafe.

I record start/end time, processed item count, result, and correlation ID. I test missed schedules, timeout, partial failure, retry, daylight-saving/time-zone behavior, and manual rerun. Secrets come from workload identity or a secret manager, not the schedule definition.

---

### 13. How do you count every character in a string using a dictionary and find the maximum and minimum counts?

**Answer:**

I scan the string once and use each character as a dictionary key. If the character already exists, I increment its count; otherwise I start it at one.

```python
def character_statistics(text: str) -> tuple[dict[str, int], list[str], list[str]]:
    counts: dict[str, int] = {}

    for character in text:
        if character.isspace():       # Remove this condition if spaces must be counted.
            continue
        counts[character] = counts.get(character, 0) + 1

    if not counts:
        return {}, [], []

    maximum = max(counts.values())
    minimum = min(counts.values())

    most_frequent = [char for char, count in counts.items() if count == maximum]
    least_frequent = [char for char, count in counts.items() if count == minimum]
    return counts, most_frequent, least_frequent


counts, maximum_characters, minimum_characters = character_statistics("banana")
print(counts)               # {'b': 1, 'a': 3, 'n': 2}
print(maximum_characters)   # ['a']
print(minimum_characters)   # ['b']
```

I return lists because several characters may have the same maximum or minimum count. The scan is `O(n)` time and uses `O(k)` space, where `k` is the number of distinct characters. I clarify whether comparison is case-sensitive and whether spaces and punctuation should count. `collections.Counter` is shorter in production, but the dictionary solution demonstrates the logic expected in an interview.

---

### 14. How do you check whether a number is prime using recursion?

**Answer:**

A prime number is greater than one and has no divisor other than one and itself. It is enough to test divisors up to the square root of the number.

```python
def is_prime(number: int, divisor: int = 2) -> bool:
    if number < 2:
        return False

    if divisor * divisor > number:
        return True

    if number % divisor == 0:
        return False

    return is_prime(number, divisor + 1)


print(is_prime(29))  # True
print(is_prime(21))  # False
print(is_prime(1))   # False
```

For `29`, the function tests `2`, `3`, `4`, and `5`. When `6 * 6` becomes greater than `29`, no factor has been found, so the number is prime. The time complexity is approximately `O(sqrt(n))`. Recursion is useful for demonstrating the concept, but Python has a recursion-depth limit, so an iterative implementation is safer for very large numbers.

---

### 15. How do you remove a value supplied by the user from a string?

**Answer:**

First I clarify whether the input represents one character or a complete substring, whether matching is case-sensitive, and whether every occurrence should be removed. To remove every exact occurrence of a substring:

```python
def remove_value(text: str, value: str) -> str:
    if value == "":
        raise ValueError("The value to remove cannot be empty")
    return text.replace(value, "")


original = input("Enter the string: ")
value_to_remove = input("Enter the character or substring to remove: ")
print(remove_value(original, value_to_remove))
```

For input `"cloud engineering"` and value `"engineer"`, the result is `"cloud ing"`. `str.replace` returns a new string because Python strings are immutable.

If the requirement is to remove individual characters contained in an input such as `"aeiou"`, I use a set and filter instead:

```python
def remove_characters(text: str, characters: str) -> str:
    blocked = set(characters)
    return "".join(char for char in text if char not in blocked)
```

---

### 16. How do you reverse a string without using a built-in reverse function or slicing?

**Answer:**

I start at the final index and move backwards until the first character.

```python
def reverse_string(text: str) -> str:
    result = ""
    index = len(text) - 1

    while index >= 0:
        result += text[index]
        index -= 1

    return result


print(reverse_string("Python"))  # nohtyP
```

This clearly demonstrates the algorithm, but repeatedly concatenating immutable strings can approach `O(n²)` work. A more efficient production version appends characters to a list and joins them once:

```python
def reverse_string_efficient(text: str) -> str:
    characters: list[str] = []
    for index in range(len(text) - 1, -1, -1):
        characters.append(text[index])
    return "".join(characters)
```

For user-visible Unicode text, code-point reversal may not preserve combined characters or emoji grapheme clusters; a Unicode-aware library may be required.

---

### 17. How do you create API endpoints and call another API using FastAPI?

**Answer:**

FastAPI is a Python framework for building HTTP APIs. Type hints and Pydantic models validate input and generate an OpenAPI schema and interactive documentation.

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

Run it during development with an ASGI server, for example `uvicorn main:app --reload`, and inspect `/docs`. Production also needs authentication/authorization, input and output models, request IDs, structured logs, metrics, rate limits, dependency timeouts, tests and a suitable deployment configuration.

For an outbound API call from an async endpoint, I use an async client so the event loop is not blocked:

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

In a busy service I normally reuse a client through application lifespan/dependency management rather than opening a new connection pool for every request. Retries are bounded and used only for safe or idempotent operations.

---

### 18. How do you remove duplicate digits from a very large number or string and retain the latest occurrence?

**Answer:**

I treat the value as a string so leading zeros are preserved and there is no integer-size conversion. “Retain the latest” means keep the final occurrence of every character. I scan from right to left, keep the first character seen in that direction, and reverse the collected result once.

```python
def keep_latest_occurrence(value: str) -> str:
    seen: set[str] = set()
    reversed_result: list[str] = []

    for character in reversed(value):
        if character not in seen:
            seen.add(character)
            reversed_result.append(character)

    return "".join(reversed(reversed_result))


print(keep_latest_occurrence("112233214"))  # 3214
```

In `112233214`, the last occurrences appear in the final result as `3`, `2`, `1`, and `4`. The algorithm is `O(n)` time and `O(k)` space. If built-in `reversed` is prohibited, I use an index loop from `len(value) - 1` to zero.

If the interviewer instead means “keep the first occurrence and discard later duplicates,” I scan left to right:

```python
def keep_first_occurrence(value: str) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for character in value:
        if character not in seen:
            seen.add(character)
            result.append(character)
    return "".join(result)
```

---

### 19. What is the difference between a shallow copy and a deep copy?

**Answer:**

A shallow copy creates a new outer object but reuses references to nested mutable objects. A deep copy recursively creates independent nested objects.

```python
import copy

original = [[1, 2], [3, 4]]
shallow = copy.copy(original)
deep = copy.deepcopy(original)

shallow[0].append(99)
print(original)  # [[1, 2, 99], [3, 4]] because inner list is shared

deep[1].append(88)
print(original)  # unchanged by the deep-copy modification
```

Assignment such as `second = original` creates no copy; both names refer to the same object. A list slice or `list.copy()` is shallow. Deep copying can be expensive and may be unsuitable for resources such as sockets, locks or database connections. I use it only when independent nested state is truly required, and I often prefer immutable data or explicitly constructing the required fields.

---

### 20. Explain local, nonlocal, and global variables in Python.

**Answer:**

Python resolves names using LEGB: Local, Enclosing, Global, Built-in.

- A local variable belongs to the current function.
- `nonlocal` allows a nested function to rebind a variable in the nearest enclosing function.
- `global` allows a function to rebind a module-level variable.

```python
application_name = "orders"       # Global/module scope


def create_counter():
    count = 0                       # Enclosing scope

    def increment() -> int:
        nonlocal count
        count += 1
        return count

    return increment


counter = create_counter()
print(counter())  # 1
print(counter())  # 2
```

Without `nonlocal count`, `count += 1` tries to create a local `count` before it has a value and raises `UnboundLocalError`. I avoid mutable global state because it makes tests, concurrency and reasoning difficult. Function arguments, returned values, closures or class instances are normally clearer. `nonlocal` is useful for small closures such as counters or decorators.

---

### 21. What is the difference between a module, package, and library?

**Answer:**

- A **module** is one importable Python file, for example `validators.py`.
- A **package** is an importable directory hierarchy that groups modules and subpackages. Traditional packages contain `__init__.py`; namespace packages can work without it.
- A **library** is a general term for reusable functionality and may contain one or many packages and modules. It is not a separate Python syntax construct.

```text
inventory_library/
├── pyproject.toml
└── src/
    └── inventory/
        ├── __init__.py
        ├── client.py
        └── validators.py
```

```python
from inventory.client import InventoryClient
from inventory import validators
```

`pip` installs a distribution package from a package index, while `import` loads an import package/module. Their names can differ. For production libraries I define metadata and dependencies in `pyproject.toml`, use a virtual environment, pin/lock application dependencies, test the public API and avoid circular imports or important work at import time.

---

### 22. What is a decorator in Python?

**Answer:**

A decorator is a callable that receives a function or class and returns a wrapped or modified callable. It adds reusable behavior without changing every function body. Common examples are authorization, logging, timing, caching and route registration.

```python
from functools import wraps
from time import perf_counter


def measure_time(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            duration = perf_counter() - start
            print(f"{function.__name__} took {duration:.4f}s")

    return wrapper


@measure_time
def add(left: int, right: int) -> int:
    return left + right


print(add(2, 3))
```

`@wraps` preserves the original name, documentation and metadata, which helps debugging and frameworks. A decorator that accepts its own arguments adds one more outer function. For async functions, the wrapper must also be async and `await` the original. I never log sensitive arguments blindly.

---

### 23. What is the difference between a Python list and an array?

**Answer:**

A Python list is a general-purpose dynamic sequence that stores references to objects and can contain mixed types. `array.array` stores values of one basic C-compatible type more compactly. A NumPy array is a separate third-party structure for homogeneous multidimensional numeric data and vectorized operations.

```python
from array import array

items = [1, "two", 3.0]          # Mixed Python objects are allowed.
numbers = array("i", [1, 2, 3])  # Signed integers only.
```

Lists are best for ordinary application collections and support rich object values. Typed arrays use less memory for large primitive sequences, while NumPy is normally much faster for bulk numerical computation because operations execute in optimized native code rather than Python loops. Both lists and these arrays are ordered and mutable; indexing is generally `O(1)`, while insertion near the beginning requires shifting elements and is `O(n)`.

---

### 24. What is slicing in Python?

**Answer:**

Slicing selects a portion of a sequence with `sequence[start:stop:step]`. The start is included, the stop is excluded, and omitted values use defaults. Negative indexes count from the end.

```python
values = [10, 20, 30, 40, 50, 60]

print(values[1:4])    # [20, 30, 40]
print(values[:3])     # [10, 20, 30]
print(values[3:])     # [40, 50, 60]
print(values[-2:])    # [50, 60]
print(values[::2])    # [10, 30, 50]
print(values[::-1])   # [60, 50, 40, 30, 20, 10]
```

For built-in lists, a slice creates a new shallow list: the outer list is new but nested objects are still shared. String and tuple slices also create new sequence values. A zero step raises `ValueError`. Large slices allocate memory proportional to the result; an iterator such as `itertools.islice` is preferable when streaming a large iterable.

---

### 25. How do you fetch JSON data and query it efficiently?

**Answer:**

I fetch with a timeout, validate the HTTP status and JSON structure, then choose the query strategy from the data size and access pattern.

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

Repeatedly scanning a large list is inefficient. If many lookups use the same unique key, I build an index once:

```python
users_by_id = {user["id"]: user for user in active_users}
requested_user = users_by_id.get(123)  # Average O(1) lookup
```

I handle pagination and rate limits and never assume that valid JSON has the expected schema. For very large responses, I request server-side filtering/pagination or use a streaming JSON parser instead of loading the whole body. If queries become complex or repeated across large data, I store normalized records in a database with suitable indexes rather than treating a JSON file as a database. Authentication tokens are short-lived and never logged.

---

### 26. How do you rotate a string anticlockwise?

**Answer:**

For a one-dimensional string, anticlockwise rotation normally means a left rotation. A left rotation by `positions` moves that many leading characters to the end.

```python
def rotate_left(text: str, positions: int) -> str:
    if not text:
        return text

    positions %= len(text)
    return text[positions:] + text[:positions]


print(rotate_left("abcdef", 2))   # cdefab
print(rotate_left("abcdef", 8))   # cdefab, because 8 % 6 == 2
```

Using modulo handles rotation counts larger than the string length. With this definition, a negative position rotates to the right. The algorithm takes `O(n)` time and space because strings are immutable and a new string is produced. If the interviewer means rotating a two-dimensional character matrix anticlockwise, that is a different problem and I would clarify it before coding.
