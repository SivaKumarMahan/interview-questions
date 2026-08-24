# Dynamic Typing

Typing is about how a language connects values and operations to data types. Python is dynamically typed, which means type checks happen while the program runs, not before. A variable name can point to one type of value now and a different type later.

Python is also strongly typed. It will not silently mix incompatible values, so `"1" + 2` raises an error instead of guessing what you meant.

```python
value = 1          # value refers to an int
value = "one"      # it can later refer to a str

total = "1" + str(2)  # explicit conversion produces "12"
```

Dynamic typing makes it faster to write and explore code, since you skip type declarations. The tradeoff is that a type mistake may not show up until the program actually runs that line.

To catch mistakes earlier, I use type hints, a static checker like mypy or pyright, unit tests, input validation, and clear interfaces. One thing worth remembering: "dynamic vs. static" and "strong vs. weak" are two different questions. Don't treat them as the same comparison.
