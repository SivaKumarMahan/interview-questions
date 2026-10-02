# Python: Fundamentals and Data Types

> Why Python is used in DevOps, dynamic typing, core collection types, slicing, copying, variable scope, modules and packages, and virtual environments.

## Key Concepts

### Dynamic Typing

Typing is about how a language connects values and operations to data types. Python is dynamically typed, which means type checks happen while the program runs, not before. A variable name can point to one type of value now and a different type later.

Python is also strongly typed. It will not silently mix incompatible values, so `"1" + 2` raises an error instead of guessing what you meant.

```python
value = 1          # value refers to an int
value = "one"      # it can later refer to a str

total = "1" + str(2)  # explicit conversion produces "12"
```

Dynamic typing makes it faster to write and explore code, since you skip type declarations. The tradeoff is that a type mistake may not show up until the program actually runs that line.

To catch mistakes earlier, I use type hints, a static checker like mypy or pyright, unit tests, input validation, and clear interfaces. One thing worth remembering: "dynamic vs. static" and "strong vs. weak" are two different questions. Don't treat them as the same comparison.

### List and Tuple

Lists and tuples are both ordered collections, and both can hold mixed types. The main difference between them is whether you can change them after creation.

| List | Tuple |
|---|---|
| Mutable: items can be added, removed, or replaced | Immutable: once created, its items can't be swapped out |
| Written with `[]` | Usually written with `()` |
| Has mutating methods such as `append()`, `extend()`, and `remove()` | Has fewer methods, since there's nothing to mutate |
| Good for a collection that changes over time | Good for a fixed record, or an interface that shouldn't change |
| Not hashable | Can be hashable, if everything inside it is hashable too |

```python
topics = ["Python", "Linux", "Kubernetes"]
topics.append("Terraform")

coordinates = (17.3850, 78.4867)

print(topics)
print(coordinates)
```

Being "immutable" only applies to the tuple's own slots. It doesn't reach inside. A tuple can hold a list, and that list can still be changed freely.

## Interview Questions

### 1. How is Python useful for DevOps?

**Answer:**

I reach for Python when automation needs more structure than a short shell script can give. I use it for REST APIs, cloud SDKs, log parsing, validation, reports, operational tools, and pipeline helpers.

A practical example is an unused-resource report: authenticate with workload identity, list cloud disks, filter out unattached resources older than a threshold, estimate cost, and write a report. The first version runs in dry-run mode only. Deletion needs approval and a second check before it happens.

For production automation I also add argument parsing, structured logging, timeouts, retries with backoff (each retry waits a bit longer than the last), tests, dependency locking, useful exit codes, and metrics. I never hardcode credentials, and I never catch every exception just to make errors disappear silently.

### 2. Short interview answer: How have you used Python for DevOps automation and debugging?

I have used Python to automate repetitive DevOps tasks - checking server disk usage, monitoring application health over REST APIs, validating Kubernetes YAML before deployment, restarting failed pods via the Kubernetes API, generating Azure VM inventory reports via the Azure SDK, and cleaning up old Docker images on build agents. These run on a schedule via cron or as steps inside Jenkins/Azure DevOps pipelines.

When debugging Python errors, I read the traceback bottom-up to find the exception type and the exact failing line, reproduce the issue locally or in a test environment, verify inputs like config files/env vars/API responses, and add logging if needed. If it's failing inside a CI/CD pipeline specifically, I review the pipeline logs, rerun the failing command manually outside the pipeline, and validate dependencies, permissions, and any external service (Kubernetes, Azure APIs) before implementing a fix.

### 3. What is the difference between a list, tuple, set, and dictionary?

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

### 4. Explain Python list, tuple, dictionary and set with examples.

#### 8.1 List

Ordered, mutable (can be changed), allows duplicates.

```python
fruits = ["apple", "banana", "apple"]

fruits.append("orange")
print(fruits)
# ['apple', 'banana', 'apple', 'orange']
```

#### 8.2 Tuple

Ordered, immutable (cannot be changed), allows duplicates.

```python
colors = ("red", "green", "blue")

print(colors[0])
# red
```

Trying to modify it:

```python
colors[0] = "black"   # Error
```

#### 8.3 Dictionary

Stores data as key-value pairs. Mutable. Keys must be unique.

```python
employee = {
    "name": "Siva",
    "age": 28,
    "city": "Hyderabad"
}

print(employee["name"])
# Siva

employee["age"] = 29
```

#### 8.4 Set

Unordered. Does not allow duplicates. Mutable.

```python
numbers = {1, 2, 3, 2, 1}

print(numbers)
# {1, 2, 3}

numbers.add(4)
print(numbers)
# {1, 2, 3, 4}
```

#### 8.5 Interview summary

| Data Type | Ordered | Mutable | Duplicates | Example |
|---|---|---|---|---|
| List | Yes | Yes | Yes | `["a", "b", "a"]` |
| Tuple | Yes | No | Yes | `("a", "b", "a")` |
| Dictionary | Yes | Yes | Keys No, Values Yes | `{"name": "Siva"}` |
| Set | No | Yes | No | `{1, 2, 3}` |

#### 8.6 One-line interview answer

- **List:** ordered, mutable, allows duplicates.
- **Tuple:** ordered, immutable, allows duplicates.
- **Dictionary:** stores data in key-value pairs with unique keys.
- **Set:** unordered collection of unique elements.

### 5. What is the difference between a Python list and an array?

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

### 6. What is slicing in Python?

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

### 7. What is the difference between a shallow copy and a deep copy?

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

### 8. Explain local, nonlocal, and global variables in Python.

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

### 9. What is the difference between a module, package, and library?

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

### 10. How do you create a Python virtual environment?

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
