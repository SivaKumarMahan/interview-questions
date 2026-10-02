# YAML: Common Mistakes and Validation

> Frequent YAML errors, how to validate files, and converting between YAML and JSON.

## Key Concepts

### Common Mistakes and How to Avoid Them

#### 1. Inconsistent indentation

```yaml
# WRONG
user:
  name: John
 age: 30  # Incorrect indentation level
```

Stick to consistent indentation — 2 spaces is the usual convention.

#### 2. Missing spaces after colons

```yaml
# WRONG
name:John  # Missing space after colon
```

#### 3. Tab characters

YAML parsers often reject tab characters. Use spaces instead.

#### 4. Unquoted special characters

```yaml
# WRONG
message: Hello: World  # The second colon needs to be in quotes
```

Correct version:

```yaml
message: "Hello: World"
```

#### 5. Incorrect list formatting

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

### Validating Your YAML

Validate your files with an online YAML validator or a code-editor YAML linting extension. Common validation errors include:

- Inconsistent indentation
- Missing spaces after colons
- Unquoted special characters
- Improper list formatting

### Converting Between YAML and Other Formats

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

## Interview Questions

<details><summary>Q1. [Basic] What are common YAML mistakes?</summary>

**Answer:**

Common mistakes: tabs, wrong indentation, duplicate keys, missing colons, wrong list nesting, unclear unquoted values, inconsistent types, and multiline text using the wrong block style. In Kubernetes specifically, label-selector mismatches and placing a field under the wrong parent are common logical errors.
To prevent these, I rely on editor YAML support, `yamllint`, schema validation, small reviewed changes, and rendered-output tests for templates. I avoid copy-pasting between environments by hand, and I never assume that a file parsing successfully means the application configuration is actually correct.

</details>

<details><summary>Q2. [Intermediate] Kubernetes YAML Indentation</summary>

#### The broken YAML

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
name: payment-api

spec:
replicas: 3
selector:
matchLabels:
app: payment

template:
metadata:
labels:
app: payment

spec:
containers:
- image: nginx
  ports:
  - containerPort: 80
```

#### What is wrong

YAML uses indentation to show which fields belong to which parent. In this file, `name`, `spec`, `replicas`, `selector`, `matchLabels`, `app`, `template`, `labels`, and the inner `spec` are all written at column 0, so YAML cannot tell they belong under `metadata` or `spec`. On top of that:

- There is no `containers.name` field, only `image`.
- The Pod template `spec.containers` has no resource requests/limits.
- `selector.matchLabels` (`app: payment`) does not clearly match the Pod template labels because the indentation is broken, so Kubernetes cannot verify the Deployment can manage its own Pods.

#### Corrected YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment
  template:
    metadata:
      labels:
        app: payment
    spec:
      containers:
        - name: payment-api
          image: nginx
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"
```

#### Short interview answer

"The YAML is broken because every field is at the same indentation level, so the parser can't tell what's nested under `metadata` or `spec`. I'd re-indent it properly (2 spaces per level), add the missing `name` field under each container, and add resource requests/limits, which are missing but important for scheduling and stability."

</details>

<details><summary>Q3. [Intermediate] How do you validate YAML files?</summary>

**Answer:**

I validate at several levels:

```bash
yamllint config.yaml
yq '.' config.yaml >/dev/null
kubectl apply --dry-run=server -f deployment.yaml
helm lint ./chart
helm template test ./chart | kubeconform -strict
```

First comes syntax and style, then schema validation, then target-tool validation, and finally behavioral testing. For pipelines I use the GitHub/GitLab/Azure pipeline linter. CI should fail on invalid YAML before deployment.

If validation fails, I check indentation, duplicate keys, whether a list or map was expected, unavailable API versions, and values that templating may have altered. I inspect the rendered output too, since a correct template can still generate invalid YAML for certain input values.

</details>
