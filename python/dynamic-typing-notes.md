# Dynamic Typing

Typing describes how a language associates values and operations with data types. In a dynamically typed language such as Python, type checks occur while the program executes and a variable name can later reference a value of a different type. Python is also strongly typed: it does not silently combine incompatible values such as `"1" + 2`.

```python
value = 1          # value refers to an int
value = "one"      # it can later refer to a str

total = "1" + str(2)  # explicit conversion produces "12"
```

Dynamic typing speeds exploration and reduces declarations, but type errors can appear only on an executed path. I use type hints, static checking such as mypy or pyright, unit tests, input validation, and clear interfaces to find mistakes earlier. “Dynamic” vs. “static” and “strong” vs. “weak/coercive” describe different aspects and should not be treated as the same comparison.

