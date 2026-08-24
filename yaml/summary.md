# YAML Summary

YAML (YAML Ain't Markup Language) is the backbone of modern DevOps tooling — Kubernetes, Docker, GitHub Actions, and more.

It is a human-readable data format. Unlike JSON or XML, it favors a clean, minimal syntax that uses indentation for structure, much like Python does. It still stays fully machine-parsable.

## The Basic Building Blocks

### 1. Key-value pairs

The simplest YAML structure is a key-value pair: a label, then its value.

```yaml
name: John Smith
age: 35
occupation: Software Engineer
```

### 2. Lists / arrays

Lists are created using hyphens; each item starts with a hyphen followed by a space:

```yaml
hobbies:
  - Reading
  - Hiking
  - Photography
  - Cooking
```

### 3. Nested structures

YAML shines when representing complex, nested data:

```yaml
person:
  name: Sarah Johnson
  age: 28
  contact:
    email: sarah.j@example.com
    phone: 555-123-4567
  skills:
    - Python
    - JavaScript
    - Docker
```

## A Family Tree Example

Representing relationships and hierarchical data:

```yaml
family:
  name: The Smiths
  members:
    - name: James Smith
      role: Father
      age: 42
      hobbies:
        - Woodworking
        - Gardening
        - Chess

    - name: Maria Smith
      role: Mother
      age: 40
      hobbies:
        - Painting
        - Running
        - Cooking

    - name: Emma Smith
      role: Daughter
      age: 15
      hobbies:
        - Volleyball
        - Piano
        - Reading
      school: Lincoln High School

    - name: Alex Smith
      role: Son
      age: 10
      hobbies:
        - Soccer
        - Video games
        - Science experiments
      school: Washington Elementary

  pets:
    - name: Max
      type: Dog
      breed: Golden Retriever
      age: 5
    - name: Whiskers
      type: Cat
      breed: Maine Coon
      age: 3
```

## A Hobby Tracker Example

```yaml
hobby_tracker:
  user: taylor_garcia
  categories:
    books:
      currently_reading:
        - title: The Midnight Library
          author: Matt Haig
          pages: 304
          progress: 75%
      completed_this_year:
        - title: Project Hail Mary
          author: Andy Weir
          rating: 5
        - title: Educated
          author: Tara Westover
          rating: 4.5
      want_to_read:
        - Cloud Atlas
        - The Three-Body Problem
        - Klara and the Sun

    fitness:
      weekly_goals:
        running:
          distance_km: 20
          current_progress: 12.5
        strength_training:
          sessions: 3
          completed: 2
      personal_records:
        5k_time: "22:45"
        deadlift_kg: 120

    cooking:
      favorite_recipes:
        - name: Vegetable Curry
          cuisine: Indian
          last_made: "2025-04-12"
        - name: Sourdough Bread
          cuisine: Artisan
          last_made: "2025-04-30"
      recipes_to_try:
        - Ramen from scratch
        - Thai Green Curry
        - Homemade Pasta
```

## Important Syntax Rules

Here is a quick reference before the details below:

| Rule | What it means |
| --- | --- |
| Indentation | Use spaces, not tabs. Indentation shows structure. |
| Colon + space | Always put a space after the colon in `key: value`. |
| Quotes | Quote strings with special characters like `:` or `#`. |
| `\|` block | Keeps line breaks as-is. |
| `>` block | Folds line breaks into spaces. |
| Comments | Start with `#`. |

### 1. Indentation matters

YAML uses indentation to show structure — spaces only, never tabs. Keeping that indentation consistent matters a lot:

```yaml
correct:
  nested_key: value
```

```yaml
incorrect:
nested_key: value  # This will cause errors
```

### 2. Colons and spaces

Always put a space after the colon in key-value pairs:

```yaml
correct: value
incorrect:value  # This will cause errors
```

### 3. Quotes for special characters

If your text contains special characters, use quotes:

```yaml
message: "This text has: colons, commas, and other symbols!"
```

### 4. Multi-line strings

The pipe character (`|`) preserves line breaks:

```yaml
description: |
  This is a longer description
  that spans multiple lines.
  Each line break is preserved.
```

The greater-than symbol (`>`) folds line breaks into spaces:

```yaml
description: >
  This is a longer description
  that spans multiple lines.
  Line breaks become spaces.
```

### 5. Comments

Comments start with the `#` symbol:

```yaml
# This is a comment
name: John  # This is an inline comment
```

## Real-World Application: GitHub Actions Workflow

```yaml
name: Build and Test Application

# Trigger on push to main branch
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

# Jobs to run
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install dependencies
      run: npm install

    - name: Run tests
      run: npm test

    - name: Build application
      run: npm run build
```

## Common Mistakes and How to Avoid Them

### 1. Inconsistent indentation

```yaml
# WRONG
user:
  name: John
 age: 30  # Incorrect indentation level
```

Stick to consistent indentation — 2 spaces is the usual convention.

### 2. Missing spaces after colons

```yaml
# WRONG
name:John  # Missing space after colon
```

### 3. Tab characters

YAML parsers often reject tab characters. Use spaces instead.

### 4. Unquoted special characters

```yaml
# WRONG
message: Hello: World  # The second colon needs to be in quotes
```

Correct version:

```yaml
message: "Hello: World"
```

### 5. Incorrect list formatting

```yaml
# WRONG
hobbies:
- Reading  # Missing space after hyphen
```

Correct version:

```yaml
hobbies:
  - Reading
```

## A Travel Planner Example

```yaml
travel_plans:
  destination: Japan
  duration_days: 14
  travelers:
    - name: Emma Wilson
      passport: AB123456
      dietary_restrictions: Vegetarian
    - name: Marcus Wilson
      passport: CD789012
      dietary_restrictions: None

  itinerary:
    - day: 1
      date: 2025-06-10
      location: Tokyo
      accommodations:
        name: Shibuya Excel Hotel
        confirmation: TMY6789
      activities:
        - time: "14:00"
          activity: Check-in at hotel
        - time: "16:00"
          activity: Explore Shibuya Crossing
        - time: "19:00"
          activity: Welcome dinner at Ichiran Ramen
          reservation: true
          confirmation: RMN4532

    - day: 2
      date: 2025-06-11
      location: Tokyo
      accommodations:
        name: Shibuya Excel Hotel
        confirmation: TMY6789
      activities:
        - time: "09:00"
          activity: Tsukiji Outer Market
        - time: "13:00"
          activity: Meiji Shrine
        - time: "16:00"
          activity: Harajuku shopping
        - time: "20:00"
          activity: Dinner at Gonpachi
          reservation: true
          confirmation: GPC7812

  budget:
    currency: USD
    categories:
      flights: 1800
      accommodations: 2200
      food: 1000
      activities: 800
      shopping: 500
      contingency: 700
    total: 7000

  packing_list:
    documents:
      - Passport
      - Flight tickets
      - Hotel reservations
      - Travel insurance
    clothing:
      - T-shirts: 7
      - Pants: 3
      - Dresses: 2
      - Jackets: 1
      - Walking shoes: 1
      - Formal shoes: 1
    electronics:
      - Camera
      - Smartphone
      - Universal adapter
      - Power bank
```

## Validating Your YAML

Validate your files with an online YAML validator or a code-editor YAML linting extension. Common validation errors include:

- Inconsistent indentation
- Missing spaces after colons
- Unquoted special characters
- Improper list formatting

## Converting Between YAML and Other Formats

YAML converts easily to and from other data formats like JSON. For example, in Python:

```python
import yaml
import json

# Convert YAML to JSON
with open('data.yaml', 'r') as yaml_file:
    yaml_data = yaml.safe_load(yaml_file)
    json_data = json.dumps(yaml_data)

# Convert JSON to YAML
with open('data.json', 'r') as json_file:
    json_data = json.load(json_file)
    yaml_data = yaml.dump(json_data)
```

## Conclusion

YAML is simple and readable, which is why it's everywhere in configuration files and data formats. The structure and syntax rules above are the same ones you'll use directly in Kubernetes, Docker, GitHub Actions, and most other modern DevOps tools.
