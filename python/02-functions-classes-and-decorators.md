# Python: Functions, Classes, and Decorators

> Object-oriented Python (constructors, instance/class/static methods, inheritance) and decorators.

## Key Concepts

### The `__init__()` Method

`__init__()` runs right after Python creates a new object, and its job is to set up the object's starting state. It should always return `None`. People often call it "the constructor" in interviews, though technically it's `__new__()` that creates the object — `__init__()` just initializes it.

```python
class Book:
    def __init__(self, title: str) -> None:
        self.title = title

    def display(self) -> None:
        print(f"Book name: {self.title}")

book = Book("Sandman")
book.display()
```

Here, `self` refers to the newly created instance. Each `Book` object receives its own `title` attribute.

### Instance, Class and Static Methods

| Method type | Declaration | First argument | Typical purpose |
|---|---|---|---|
| Instance method | Normal `def` in a class | `self` | Read or change one object's state; can also reach class state |
| Class method | `@classmethod` | `cls` | Read or change class-level state; often used as an alternate constructor |
| Static method | `@staticmethod` | None supplied automatically | A utility that's related to the class but doesn't need instance or class state |

```python
class Deployment:
    platform = "AKS"

    def __init__(self, service: str) -> None:
        self.service = service

    def description(self) -> str:
        return f"{self.service} runs on {self.platform}"

    @classmethod
    def from_repository(cls, repository: str) -> "Deployment":
        service = repository.rsplit("/", maxsplit=1)[-1]
        return cls(service)

    @staticmethod
    def valid_replicas(replicas: int) -> bool:
        return replicas > 0
```

A static method can still read global data if it needs to — nothing stops it. It just doesn't get `self` or `cls` handed to it automatically. If the logic actually needs object or class state, use the method type that gets it.

### Inheritance

Inheritance lets a child class reuse and specialize behavior from a parent class, and it's what makes polymorphism work. That said, composition is often the clearer choice when the relationship isn't a genuine "is-a" one.

```python
class Notifier:
    def send(self, message: str) -> None:
        raise NotImplementedError

class TeamsNotifier(Notifier):
    def __init__(self, channel: str) -> None:
        self.channel = channel

    def send(self, message: str) -> None:
        print(f"Sending to {self.channel}: {message}")
```

A child class can override any inherited method. Use `super()` when the parent's version still needs to run too, especially when extending `__init__()`. Keep inheritance trees shallow, and test overridden behavior directly.

### Decorators

A decorator takes a function or class and returns something that either replaces it or adds behavior on top of it. The `@decorator` syntax applies it without touching the original function's body. Common uses are logging, timing, authentication, authorization, caching, and retries.

```python
from collections.abc import Callable
from functools import wraps
from typing import Any

def audit_call(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Completed {func.__name__}")
        return result

    return wrapper

@audit_call
def say_hello(name: str) -> str:
    return f"Hello, {name}!"

print(say_hello("Momen"))
```

`functools.wraps()` keeps the original function's name and docstring attached to the wrapper, which makes debugging easier. The wrapper takes `*args` and `**kwargs` so it can forward calls no matter what arguments the original function expects.

## Interview Questions

### 1. What is a decorator in Python?

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
