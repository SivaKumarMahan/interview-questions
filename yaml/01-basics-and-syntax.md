# YAML: Basics and Syntax

> What YAML is, its building blocks (key-value pairs, lists, nesting), and the core syntax rules for indentation, strings, anchors, and comments.

## Key Concepts

### What YAML Is

YAML (YAML Ain't Markup Language) is the backbone of modern DevOps tooling — Kubernetes, Docker, GitHub Actions, and more.

It is a human-readable data format. Unlike JSON or XML, it favors a clean, minimal syntax that uses indentation for structure, much like Python does. It still stays fully machine-parsable.

### The Basic Building Blocks

#### 1. Key-value pairs

The simplest YAML structure is a key-value pair: a label, then its value.

```yaml
name: John Smith
age: 35
occupation: Software Engineer
```

#### 2. Lists / arrays

Lists are created using hyphens; each item starts with a hyphen followed by a space:

```yaml
hobbies:
  - Reading
  - Hiking
  - Photography
  - Cooking
```

#### 3. Nested structures

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

### Important Syntax Rules

Here is a quick reference before the details below:

| Rule | What it means |
| --- | --- |
| Indentation | Use spaces, not tabs. Indentation shows structure. |
| Colon + space | Always put a space after the colon in `key: value`. |
| Quotes | Quote strings with special characters like `:` or `#`. |
| `\|` block | Keeps line breaks as-is. |
| `>` block | Folds line breaks into spaces. |
| Comments | Start with `#`. |

#### 1. Indentation matters

YAML uses indentation to show structure — spaces only, never tabs. Keeping that indentation consistent matters a lot:

```yaml
correct:
  nested_key: value
```

```yaml
incorrect:
nested_key: value  # This will cause errors
```

#### 2. Colons and spaces

Always put a space after the colon in key-value pairs:

```yaml
correct: value
incorrect:value  # This will cause errors
```

#### 3. Quotes for special characters

If your text contains special characters, use quotes:

```yaml
message: "This text has: colons, commas, and other symbols!"
```

#### 4. Multi-line strings

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

#### 5. Comments

Comments start with the `#` symbol:

```yaml
# This is a comment
name: John  # This is an inline comment
```

### Conclusion

YAML is simple and readable, which is why it's everywhere in configuration files and data formats. The structure and syntax rules above are the same ones you'll use directly in Kubernetes, Docker, GitHub Actions, and most other modern DevOps tools.

## Interview Questions

### 1. What is YAML?

**Answer:**

YAML is a human-readable data serialization format used for configuration. It represents scalars, lists, and key-value mappings using indentation.

Kubernetes manifests, Ansible playbooks, Helm values, GitHub Actions, Azure Pipelines, and many application configurations use it.

```yaml
application:
  name: orders-api
  replicas: 3
  features:
    - payments
    - notifications
```

YAML describes data; the consuming tool decides what that data means. A syntactically valid YAML file can still be invalid for Kubernetes or a pipeline, so I validate both YAML syntax and the target schema.

I also avoid putting secrets directly in YAML committed to Git.

### 2. Why is indentation important in YAML?

**Answer:**

Indentation defines parent-child structure. YAML uses spaces rather than braces, so moving a line can change its meaning or make the document invalid. Tabs should not be used for indentation.

```yaml
# Correct: ports belongs to the container
containers:
  - name: api
    image: example/api:1.0
    ports:
      - containerPort: 8080
```

I stick to a consistent two-space convention, turn on whitespace display in my editor, and run `yamllint` plus tool-specific validation. When something breaks, I check the exact line the parser reports, and the parent keys around it.

Copying YAML through chat or documents can introduce tabs or smart characters, so I validate the actual committed file.

### 3. What is the difference between a YAML list and map?

**Answer:**

A map stores named key-value pairs; a list stores ordered items. A list item starts with `-`.

```yaml
# Map
labels:
  app: orders
  tier: backend

# List of maps
containers:
  - name: api
    image: example/api:1.0
  - name: log-agent
    image: example/agent:2.0
```

The distinction matters because schemas expect a specific type. Kubernetes `metadata.labels` is a map, while `spec.template.spec.containers` is a list.

If I supply a map where a list is required, parsing may succeed but schema validation fails with a type error.

### 4. How do strings work in YAML?

**Answer:**

Strings can be plain, single-quoted, double-quoted, or written in block style. A plain value that looks like a boolean, number, date, or null can get interpreted as that type instead of a string — it depends on the YAML version and the parser.

```yaml
plain: hello
literal: |
  first line
  second line
folded: >
  this becomes one
  folded line
port_as_string: "8080"
special: "value:with:colons"
```

Single quotes keep most characters literal. Double quotes support escape sequences. I quote anything unclear — image tags, wildcard-like values, and any string with a `:`, `#`, or a leading special character.

I confirm the consumer's expected type rather than quoting everything automatically.

### 5. What are YAML anchors and aliases?

**Answer:**

An anchor names a YAML node with `&name`, and an alias reuses it with `*name`. The merge key `<<` is commonly used to reuse mappings.

```yaml
defaults: &defaults
  retries: 3
  timeout: 30

development:
  <<: *defaults
  endpoint: https://dev.example.com

production:
  <<: *defaults
  endpoint: https://prod.example.com
  retries: 5
```

Anchors reduce duplication within one YAML document, but support and merge behavior depend on the consuming parser. Kubernetes manifests do not provide a general cross-file templating system through anchors.

For complex reuse I prefer Helm, Kustomize, or pipeline templates because they make environment composition more explicit.
