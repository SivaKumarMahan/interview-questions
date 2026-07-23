# Better Logging in Python with Loguru

When talking about logging, **log level** is an important term — levels act as a severity scale for your messages. Assigning different levels makes it easier to focus on critical issues while reducing noise from less important events during troubleshooting or monitoring.

Python's built-in `logging` module comes with `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Loguru adds two more: `TRACE` and `SUCCESS`.

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

The `trace` output is not printed by default because the default log level for Loguru is `DEBUG`.

## Changing the default log level

Use the logger's `add()` function to change the default log level and update the log formatting.

```python
import sys
from loguru import logger

logger.add(sys.stderr, level="TRACE")
logger.trace("Hi, This is Akhilesh Mishra")
```

## Changing the formatting

Unlike Python's built-in `logging` module, you can add a handler, update formatting, and change the log level in a single line with `add()`.

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

Change the color of output messages using an HTML-like syntax:

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

Loguru sends logs to the console by default, but you can configure it to send logs to a file:

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

Loguru allows you to rotate, retain, and compress logs with time and size filters:

```python
logger.add("log_rotate.log", rotation="500 MB")   # Automatically rotate a too-big file
logger.add("log_rotate2.log", rotation="12:00")    # New file is created each day at noon
logger.add("log_rotate3.log", rotation="1 week")   # Once the file is too old, it's rotated

logger.add("log_retention.log", retention="10 days")  # Cleanup after some time

logger.add("log_retention2.log", compression="zip")   # Save some space
```

### JSON logging

Loguru supports logging in JSON format with the `serialize=True` option:

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

To add extra information to a log message for context, use the `bind()` method. Add the `{extra}` directive to your `add()` format to include custom entries in the output.

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

You can further customize the context:

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

Use the Python context manager to modify a context-local state temporarily:

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

The `patch()` method allows dynamic values to be attached to each new message:

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

Loguru allows you to create your own log level with the `level()` function:

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

Logging exceptions is crucial for tracking bugs, but it's not helpful if you don't know the cause. Loguru shows the entire stack trace, including variable values, so you can identify the problem.

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

By default `logger.catch()` logs at the `ERROR` level, but you can customize it to use a different level.

## Official References

- [Loguru documentation](https://loguru.readthedocs.io/)
- [Loguru GitHub repository](https://github.com/Delgan/loguru)
