# Python: Coding Challenges

> Hands-on string and number problems commonly asked in Python coding rounds.

## Key Concepts

### Python sample programs

The most commonly asked Python coding questions in DevOps interview rounds.

### Most common Python interview programs

1. Fibonacci series
2. Prime number
3. Factorial
4. Palindrome
5. Reverse string
6. Reverse number
7. Swap two numbers
8. Even / odd
9. Largest number
10. Remove duplicates
11. Count vowels
12. Character frequency
13. Multiplication table
14. Sum of list elements
15. Armstrong number

These cover most of the basic Python coding questions asked in DevOps, Azure DevOps, and SRE interviews.

## Interview Questions

<details><summary>Q1. [Basic] How do you count every character in a string using a dictionary and find the maximum and minimum counts?</summary>

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

</details>

<details><summary>Q2. [Basic] How do you reverse a string without using a built-in reverse function or slicing?</summary>

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

</details>

<details><summary>Q3. [Basic] How do you rotate a string anticlockwise?</summary>

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

</details>

<details><summary>Q4. [Basic] How do you remove a value supplied by the user from a string?</summary>

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

</details>

<details><summary>Q5. [Intermediate] How do you remove duplicate digits from a very large number or string and retain the latest occurrence?</summary>

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

</details>

<details><summary>Q6. [Intermediate] How do you check whether a number is prime using recursion?</summary>

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

</details>

<details><summary>Q7. [Basic] Write a Python program to print the Fibonacci series.</summary>

```python
n = 10
a, b = 0, 1

for i in range(n):
    print(a, end=" ")
    a, b = b, a + b
```

Output:

```
0 1 1 2 3 5 8 13 21 34
```

</details>

<details><summary>Q8. [Basic] Write a Python program to check whether a number is prime.</summary>

```python
num = 17

if num > 1:
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            print("Not Prime")
            break
    else:
        print("Prime")
else:
    print("Not Prime")
```

</details>

<details><summary>Q9. [Basic] Write a Python program to swap two numbers.</summary>

Using a temporary variable:

```python
a = 10
b = 20

temp = a
a = b
b = temp

print(a, b)
```

The Python way:

```python
a = 10
b = 20

a, b = b, a

print(a, b)
```

</details>

<details><summary>Q10. [Basic] Write a Python program to reverse a string.</summary>

```python
text = "DevOps"

print(text[::-1])
```

Output:

```
spOveD
```

</details>

<details><summary>Q11. [Basic] Write a Python program to reverse a number.</summary>

```python
num = 12345
rev = 0

while num > 0:
    digit = num % 10
    rev = rev * 10 + digit
    num //= 10

print(rev)
```

</details>

<details><summary>Q12. [Basic] Write a Python program to find the factorial of a number.</summary>

```python
num = 5
fact = 1

for i in range(1, num + 1):
    fact *= i

print(fact)
```

Output:

```
120
```

</details>

<details><summary>Q13. [Basic] Write a Python program to check whether a number is a palindrome.</summary>

```python
num = 121
temp = num
rev = 0

while temp > 0:
    digit = temp % 10
    rev = rev * 10 + digit
    temp //= 10

if num == rev:
    print("Palindrome")
else:
    print("Not Palindrome")
```

</details>

<details><summary>Q14. [Basic] Write a Python program to count the vowels in a string.</summary>

```python
text = "Hello World"

count = 0

for ch in text.lower():
    if ch in "aeiou":
        count += 1

print(count)
```

</details>

<details><summary>Q15. [Basic] Write a Python program to find the largest number in a list.</summary>

```python
numbers = [10, 45, 23, 89, 67]

print(max(numbers))
```

</details>

<details><summary>Q16. [Basic] Write a Python program to remove duplicates from a list.</summary>

```python
numbers = [1, 2, 2, 3, 4, 4, 5]

unique = list(set(numbers))

print(unique)
```

</details>

<details><summary>Q17. [Basic] Write a Python program to count the frequency of characters in a string.</summary>

```python
text = "banana"

freq = {}

for ch in text:
    freq[ch] = freq.get(ch, 0) + 1

print(freq)
```

Output:

```
{'b': 1, 'a': 3, 'n': 2}
```

</details>

<details><summary>Q18. [Basic] Write a Python program to check whether a number is even or odd.</summary>

```python
num = 18

if num % 2 == 0:
    print("Even")
else:
    print("Odd")
```

</details>

<details><summary>Q19. [Basic] Write a Python program to find the maximum in a list without using max().</summary>

```python
numbers = [5, 9, 2, 14, 7]

largest = numbers[0]

for n in numbers:
    if n > largest:
        largest = n

print(largest)
```

</details>

<details><summary>Q20. [Basic] Write a Python program to find the sum of list elements.</summary>

```python
numbers = [10, 20, 30, 40]

print(sum(numbers))
```

</details>

<details><summary>Q21. [Basic] Write a Python program to print a multiplication table.</summary>

```python
num = 5

for i in range(1, 11):
    print(f"{num} x {i} = {num * i}")
```

</details>

<details><summary>Q22. [Basic] Write a Python program to check whether a number is an Armstrong number.</summary>

A number equal to the sum of its own digits, each raised to the power of the digit count (e.g. `153 = 1³ + 5³ + 3³`).

```python
num = 153
digits = str(num)
power = len(digits)

total = sum(int(d) ** power for d in digits)

if total == num:
    print("Armstrong number")
else:
    print("Not an Armstrong number")
```

</details>
