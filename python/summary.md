# Python Summary

## List and Tuple

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

## The `__init__()` Method

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

## Decorators

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

## Missing Values in pandas

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

## Instance, Class and Static Methods

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

## Inheritance

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

## Better Logging in Python with Loguru

A **log level** is a severity label attached to each message. Assigning levels lets you focus on the messages that matter and filter out the noise while troubleshooting or monitoring.

Python's built-in `logging` module ships with `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Loguru adds two more: `TRACE` and `SUCCESS`.

## Log Levels (in order of increasing priority)

| Level | Priority (`no`) | Typical use |
| --- | --- | --- |
| `TRACE` | 5 | Very fine-grained diagnostic detail |
| `DEBUG` | 10 | Debugging information |
| `INFO` | 20 | General informational messages |
| `SUCCESS` | 25 | An operation completed successfully |
| `WARNING` | 30 | Something unexpected, but not fatal |
| `ERROR` | 40 | A failure in the current operation |
| `CRITICAL` | 50 | A severe error; the app may not continue |

## Installing Loguru with pip

```bash
pip install loguru
```

To use Loguru, import the `logger` from the `loguru` module and use it directly:

```python
from loguru import logger

logger.trace("Hi, This is Akhilesh Mishra")
logger.debug("I will show how to use loguru for better logging in python")
logger.info(" I love how the logs look")
logger.warning("Different color of each section of log")
logger.error("Easy to get started with")
logger.critical("So many options to choose from")
logger.success(" You see what i am talking about")
```

The default output format is:

```text
date | level | file location: scope: line number - message
```

The `trace` line above won't print by default, because Loguru's default level is `DEBUG`.

## Changing the default log level

Use the logger's `add()` function to set a different default log level and update the formatting at the same time.

```python
import sys
from loguru import logger

logger.add(sys.stderr, level="TRACE")
logger.trace("Hi, This is Akhilesh Mishra")
```

## Changing the formatting

Unlike the built-in `logging` module, Loguru lets you add a handler, set the format, and set the log level all in one call to `add()`.

```python
import sys
from loguru import logger

logger.remove()  # remove the old formatting
logger.add(sys.stdout, format="{time}::{level} --- {message}", level="INFO")

logger.debug(" Add a handler, update formatting, and change the loglevel")
logger.info(" one function to rule them all")
logger.success(" logger.add()")
```

## Pretty logging with colors

Set colors for your log output using an HTML-like syntax:

```python
logger.remove()
logger.add(
    sys.stdout,
    format=" <yellow>{time} </yellow>:: <green> <bold> {level} </bold> </green>--- <blue> {message} </blue>",
)

logger.info("Set the colors you want to use for logs")
logger.success(" How easy it was???")
```

## Changing the time formatting

```python
import sys
from loguru import logger

logger.remove()
# MMMM D, YYYY > HH:mm:ss!UTC : UTC time
logger.add(sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | <level>{message} </level>")

logger.warning(" Use time format-> {time:MMMM D, YYYY > HH:mm:ss!UTC}")
logger.success("Use the default color from level: <level>{message} </level>")
```

See the [Loguru date/time formatting reference](https://loguru.readthedocs.io/en/stable/api/logger.html#time) for more options.

## Sending logs to a file

Loguru sends logs to the console by default, but you can point it at a file instead:

```python
logger.add("log_file_demo.log")
```

With formatted logs:

```python
from loguru import logger

logger.remove()
logger.add("file_{time}.log", format="{time:MMMM D, YYYY > HH:mm:ss} | {level} | <level>{message} </level>")

logger.info("using file logging")
logger.success(" will send logs to the file")
```

### Rotation, retention, and compression

Loguru can rotate, clean up, and compress log files based on time or size:

```python
logger.add("log_rotate.log", rotation="500 MB")   # Automatically rotate a too-big file
logger.add("log_rotate2.log", rotation="12:00")    # New file is created each day at noon
logger.add("log_rotate3.log", rotation="1 week")   # Once the file is too old, it's rotated

logger.add("log_retention.log", retention="10 days")  # Cleanup after some time

logger.add("log_retention2.log", compression="zip")   # Save some space
```

### JSON logging

Loguru can write logs in JSON format with the `serialize=True` option:

```python
import sys
from loguru import logger

logger.remove(0)
logger.add(
    sys.stderr,
    format="{time:MMMM D: YYYY:: HH:mm:ss!UTC} | {level} | {message}",
    serialize=True,
)
logger.warning(" Its addictive, use with caution !")
logger.success("I know you started liking loguru")
```

## Adding context to log messages

To attach extra context to a log message, use `bind()`. Add the `{extra}` placeholder to your `add()` format so those custom fields actually show up in the output.

```python
import sys
from loguru import logger

# Remove the default logger
logger.remove(0)

# Add a new logger that outputs to sys.stderr
logger.add(
    sys.stderr,
    format=" {level} | <level>{message}</level> | {extra} ",
)

# Create a new logger with some initial context
context_logger = logger.bind(author="Akhilesh", type="demo")

# Log an info message with the current context
context_logger.info("You can pass context with logs!")
```

You can add more context on top of that:

```python
# Bind additional context to the logger and log a warning message
context_logger.bind(blog_type="Tutorial").warning(
    "You can use extra attributes to bind context!"
)

# Log a success message with additional context provided during formatting
context_logger.success(
    "Use kwargs to add context during formatting: {platform}", platform="Medium"
)
```

### Temporary context with `contextualize()`

Use this context manager to set context that only applies for the duration of the `with` block:

```python
import sys
from loguru import logger

logger.remove(0)

logger.add(
    sys.stderr,
    format=" {level} | <level>{message}</level> | {extra} ",
)

context_logger = logger.bind(blog_id=45)

def do_something():
    context_logger.debug("doing something")

with logger.contextualize(scope="From context manager"):
    do_something()

do_something()
```

### Combine `bind()` and `filter` for fine-grained control

```python
from loguru import logger

logger.add("special.log", filter=lambda record: "special" in record["extra"])
logger.debug("This message is not logged to the file")
logger.bind(special=True).info("This message, though, is logged to the file!")
```

### Attach dynamic values with `patch()`

`patch()` lets you attach a computed value to every message as it's logged:

```python
import sys
from loguru import logger
from datetime import datetime

logger.remove(0)
logger.add(sys.stderr, format="{extra[utc]} - {level} - {message}")
logger = logger.patch(lambda record: record["extra"].update(utc=datetime.now()))

logger.info("using patch method from loguru")
```

## Creating custom log levels

Loguru lets you define your own log level with `level()`:

```python
import sys
from loguru import logger

logger.remove(0)

m_level = logger.level("Medium", no=45, color="<yellow><bold>", icon="/\\/\\")
n_level = logger.level("Nedium", no=45, color="<blue><bold>", icon="|\\|")

logger.add(sys.stderr, format=" <level> {level.icon} :: {message} </level>")

logger.log("Medium", "This is my custom log level")
logger.log("Nedium", "I like having optional log levels")
```

## Logging exceptions

Logging exceptions matters for tracking down bugs, but it's only useful if you can actually see what caused the problem. Loguru prints the full stack trace, including variable values, so the cause is easier to spot.

```python
from loguru import logger

logger.remove(0)

# Caution: "diagnose=True" is the default and may leak sensitive data in prod
logger.add("loguru.log", backtrace=True, diagnose=True)

def func(a, b):
    return a / b

def nested(c):
    try:
        func(5, c)
    except ZeroDivisionError:
        logger.exception("Did you just??")

nested(0)
```

You can also use the `logger.catch()` decorator:

```python
from loguru import logger

logger.remove(0)

# Caution: "diagnose=True" is the default and may leak sensitive data in prod
logger.add("loguru.log", backtrace=False, diagnose=False)

@logger.catch()
def func(a, b):
    return a / b

func(5, 0)
```

By default, `logger.catch()` logs at the `ERROR` level, but you can point it at a different level instead.

## Official References

- [Loguru documentation](https://loguru.readthedocs.io/)
- [Loguru GitHub repository](https://github.com/Delgan/loguru)
