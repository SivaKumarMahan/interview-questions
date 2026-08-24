# Python Interview Questions

### 1. How is Python useful for DevOps?

**Answer:**

I reach for Python when automation needs more structure than a short shell script can give. I use it for REST APIs, cloud SDKs, log parsing, validation, reports, operational tools, and pipeline helpers.

A practical example is an unused-resource report: authenticate with workload identity, list cloud disks, filter out unattached resources older than a threshold, estimate cost, and write a report. The first version runs in dry-run mode only. Deletion needs approval and a second check before it happens.

For production automation I also add argument parsing, structured logging, timeouts, retries with backoff (each retry waits a bit longer than the last), tests, dependency locking, useful exit codes, and metrics. I never hardcode credentials, and I never catch every exception just to make errors disappear silently.

---

### 2. How do you call a REST API in Python?

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

---

### 3. How do you handle errors in Python scripts?

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

---

### 4. How do you read and write JSON in Python?

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

---

### 5. How do you parse YAML in Python?

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

---

### 6. How do you execute shell commands from Python?

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

---

### 7. How do you manage secrets in Python automation?

**Answer:**

I authenticate with managed identity, workload identity, or another short-lived mechanism, and fetch secrets at runtime from Vault or a cloud secret manager. Environment variables can work as a delivery method in some setups, but they still need protection, since child processes and diagnostic tools can expose them.

I never commit secrets, put them in default arguments, print them, or let them end up in exception messages. Access is scoped to only what's needed, audited, and rotated regularly. The code only receives a secret at the point where it's used, and never writes it to disk.

If a secret does get exposed, I revoke it first, then review logs and access history, rotate any downstream credentials, remove retained output, and add a test or a scan so it doesn't happen again.

---

### 8. How do you create a Python virtual environment?

**Answer:**

A virtual environment keeps a project's packages separate from the system Python install.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
deactivate
```

On Windows, activation is usually `.venv\Scripts\Activate.ps1`. I don't commit `.venv` to source control; I commit a dependency file and a lock file instead.

CI creates a fresh environment on every run, installs pinned dependencies, scans them, and tests against the supported Python versions. Containers add another layer of isolation, but they don't remove the need to pin dependencies.

---

### 9. How do you process large log files in Python?

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

---

### 10. How do you make a Python script production-ready?

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

---

### 11. What is the difference between a list, tuple, set, and dictionary?

**Answer:**

- A **list** is ordered and can change. Use it for a sequence that grows or shrinks.
- A **tuple** is ordered but fixed once created. Use it for a fixed record, or when you need a hashable composite value.
- A **set** stores unique values and is fast for checking membership.
- A **dictionary** maps unique keys to values and keeps insertion order in current Python versions.

```python
servers = ["web1", "web2"]
endpoint = ("db.internal", 5432)
regions = {"centralindia", "eastus"}
ports = {"http": 80, "https": 443}
```

I pick based on what the data actually means, not just syntax. A set removes duplicates, but it doesn't represent an order that matters to the business. A dictionary makes a named lookup clearer than relying on list positions.

---

### 12. How do you schedule Python automation?

**Answer:**

The right choice depends on runtime, retry needs, environment, and who owns operating it. Options include cron or systemd timers, GitHub Actions or Azure Pipelines schedules, Kubernetes CronJobs, Azure Functions timers, and workflow orchestrators.

For a Kubernetes CronJob, I set the concurrency policy, deadlines, history limits, resource requests, and failure alerts. Whatever the scheduler, the script must be safe to run more than once, and it needs a distributed lock if overlapping runs would cause problems.

I record the start and end time, how many items were processed, the result, and a correlation ID. I test missed schedules, timeouts, partial failures, retries, daylight-saving and time-zone behavior, and manual reruns.

Secrets come from workload identity or a secret manager, never from the schedule definition itself.

---

### 13. How do you count every character in a string using a dictionary and find the maximum and minimum counts?

**Answer:**

I scan the string once and use each character as a dictionary key. If the character has already been seen, I bump its count; otherwise I start it at one.

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

I return lists because more than one character can share the same maximum or minimum count. The scan takes `O(n)` time and `O(k)` space, where `k` is the number of distinct characters.

Before I code, I ask whether comparison should be case-sensitive and whether spaces and punctuation count. In production I'd just use `collections.Counter`, but writing it out with a dictionary shows the logic an interviewer wants to see.

---

### 14. How do you check whether a number is prime using recursion?

**Answer:**

A prime number is greater than one and has no divisor other than one and itself. It's enough to test divisors up to the square root of the number.

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

For `29`, the function tests `2`, `3`, `4`, and `5`. Once `6 * 6` passes `29`, no factor has turned up, so the number is prime.

The time complexity is roughly `O(sqrt(n))`. Recursion is fine for showing the idea, but Python limits how deep recursion can go, so an iterative version is safer for very large numbers.

---

### 15. How do you remove a value supplied by the user from a string?

**Answer:**

First I ask whether the input is one character or a whole substring, whether matching should be case-sensitive, and whether every occurrence should go. To remove every exact occurrence of a substring:

```python
def remove_value(text: str, value: str) -> str:
    if value == "":
        raise ValueError("The value to remove cannot be empty")
    return text.replace(value, "")


original = input("Enter the string: ")
value_to_remove = input("Enter the character or substring to remove: ")
print(remove_value(original, value_to_remove))
```

For input `"cloud engineering"` and value `"engineer"`, the result is `"cloud ing"`. `str.replace` returns a new string, because Python strings can't be changed in place — a fresh string is always created.

If instead the goal is to remove individual characters that appear in a set like `"aeiou"`, I use a set and filter:

```python
def remove_characters(text: str, characters: str) -> str:
    blocked = set(characters)
    return "".join(char for char in text if char not in blocked)
```

---

### 16. How do you reverse a string without using a built-in reverse function or slicing?

**Answer:**

I start at the last index and walk backwards to the first character.

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

This shows the algorithm clearly, but repeatedly building a string this way can approach `O(n²)` work, since a new string gets created on each append. A faster version appends characters to a list and joins them once at the end:

```python
def reverse_string_efficient(text: str) -> str:
    characters: list[str] = []
    for index in range(len(text) - 1, -1, -1):
        characters.append(text[index])
    return "".join(characters)
```

For user-visible Unicode text, reversing by code point can break apart combined characters or emoji made of multiple parts. A Unicode-aware library may be needed there.

---

### 17. How do you create API endpoints and call another API using FastAPI?

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

---

### 18. How do you remove duplicate digits from a very large number or string and retain the latest occurrence?

**Answer:**

I treat the value as a string, so leading zeros survive and there's no risk of an integer overflowing. "Keep the latest" means keep the last time each character appears. I scan from right to left, keep the first copy of each character I see going that direction, then reverse the result once.

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

In `112233214`, the last occurrences of each digit come out as `3`, `2`, `1`, and `4`. This is `O(n)` time and `O(k)` space. If `reversed` isn't allowed, I loop an index from `len(value) - 1` down to zero instead.

If the interviewer actually means "keep the first occurrence and drop later duplicates," I scan left to right instead:

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

A shallow copy makes a new outer object, but the objects nested inside it are still shared with the original. A deep copy rebuilds everything inside, recursively, so nothing is shared.

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

Assignment like `second = original` doesn't copy anything at all; both names point to the exact same object. A list slice or `list.copy()` gives you a shallow copy.

Deep copies can be expensive, and they don't make sense for things like sockets, locks, or database connections. I only reach for one when I genuinely need independent nested state, and often I'd rather use an immutable value or build the fields I need explicitly instead.

---

### 20. Explain local, nonlocal, and global variables in Python.

**Answer:**

Python looks up names using LEGB order: Local, Enclosing, Global, Built-in.

- A local variable belongs to the current function.
- `nonlocal` lets a nested function change a variable that belongs to the function wrapping it.
- `global` lets a function change a variable that lives at the module level.

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

Without `nonlocal count`, the line `count += 1` would try to create a brand-new local `count` before it has a value, and Python raises `UnboundLocalError`. I avoid mutable global state in general, because it makes tests, concurrency, and just reasoning about the code harder.

Passing arguments, returning values, using closures, or using a class instance is usually clearer. `nonlocal` earns its place in small closures like counters or decorators.

---

### 21. What is the difference between a module, package, and library?

**Answer:**

- A **module** is a single importable Python file, for example `validators.py`.
- A **package** is an importable directory that groups modules and subpackages together. Traditional packages contain `__init__.py`; namespace packages can skip it.
- A **library** is a general term for reusable code, and it can hold one or many packages and modules. It isn't a separate syntax feature in Python.

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

`pip` installs a distribution package from a package index, while `import` loads an import package or module. Their names don't have to match.

For a library I plan to publish, I define metadata and dependencies in `pyproject.toml`, use a virtual environment, pin or lock the dependencies, test the public API, and avoid circular imports or heavy work happening just from importing the module.

---

### 22. What is a decorator in Python?

**Answer:**

A decorator is a callable that takes a function or class and returns a wrapped or modified version of it. It adds reusable behavior without touching the original function's body. Common uses are authorization, logging, timing, caching, and route registration.

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

`@wraps` keeps the original function's name, docstring, and other metadata intact, which helps debugging and any framework that inspects the function. A decorator that takes its own arguments just adds one more outer function layer.

For async functions, the wrapper needs to be async too, and it needs to `await` the original call. I never log arguments blindly, in case one of them is sensitive.

---

### 23. What is the difference between a Python list and an array?

**Answer:**

A Python list is a general-purpose sequence. It stores references to objects and can hold mixed types. `array.array` stores values of a single basic type more compactly.

A NumPy array is a separate third-party structure built for uniform, multi-dimensional numeric data and vectorized math.

```python
from array import array

items = [1, "two", 3.0]          # Mixed Python objects are allowed.
numbers = array("i", [1, 2, 3])  # Signed integers only.
```

Lists work best for ordinary collections that hold rich object values. Typed arrays use less memory for large sequences of plain numbers, and NumPy is normally much faster for bulk numeric work, since the operations run in optimized native code instead of a Python loop.

Both lists and these arrays keep their order and can be changed. Indexing is roughly `O(1)`, but inserting near the start requires shifting everything else, so that's `O(n)`.

---

### 24. What is slicing in Python?

**Answer:**

Slicing pulls out part of a sequence with `sequence[start:stop:step]`. The start index is included, the stop index is excluded, and any value you leave out uses a sensible default. Negative indexes count from the end.

```python
values = [10, 20, 30, 40, 50, 60]

print(values[1:4])    # [20, 30, 40]
print(values[:3])     # [10, 20, 30]
print(values[3:])     # [40, 50, 60]
print(values[-2:])    # [50, 60]
print(values[::2])    # [10, 30, 50]
print(values[::-1])   # [60, 50, 40, 30, 20, 10]
```

For a regular list, a slice creates a new outer list, but the objects inside it are still shared with the original. String and tuple slices also produce new sequences.

A step of zero raises `ValueError`. A large slice uses memory proportional to its size, so for a big iterable I'd rather stream it with something like `itertools.islice`.

---

### 25. How do you fetch JSON data and query it efficiently?

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

---

### 26. How do you rotate a string anticlockwise?

**Answer:**

For a one-dimensional string, "anticlockwise" usually just means a left rotation. A left rotation by `positions` moves that many leading characters to the end.

```python
def rotate_left(text: str, positions: int) -> str:
    if not text:
        return text

    positions %= len(text)
    return text[positions:] + text[:positions]


print(rotate_left("abcdef", 2))   # cdefab
print(rotate_left("abcdef", 8))   # cdefab, because 8 % 6 == 2
```

Using modulo handles a rotation count larger than the string's length. With this definition, a negative position rotates to the right instead.

This takes `O(n)` time and space, since strings can't be changed in place and a new string always has to be built. If the interviewer actually means rotating a two-dimensional character grid, that's a different problem, and I'd ask before coding it.
