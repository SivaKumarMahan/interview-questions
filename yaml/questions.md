# YAML Interview Questions

---

### 1. What is YAML?

**Answer:**

YAML is a human-readable data serialization format used for configuration. It represents scalars, lists, and key-value mappings using indentation. Kubernetes manifests, Ansible playbooks, Helm values, GitHub Actions, Azure Pipelines, and many application configurations use it.

```yaml
application:
  name: orders-api
  replicas: 3
  features:
    - payments
    - notifications
```

YAML describes data; the consuming tool decides what that data means. A syntactically valid YAML file can still be invalid for Kubernetes or a pipeline, so I validate both YAML syntax and the target schema. I also avoid putting secrets directly in YAML committed to Git.

---

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

I use a consistent two-space convention, editor whitespace display, `yamllint`, and tool-specific validation. When troubleshooting, I inspect the exact line reported by the parser and nearby parent keys. Copying YAML through chat or documents can introduce tabs or smart characters, so I validate the actual committed file.

---

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

The distinction matters because schemas expect a specific type. Kubernetes `metadata.labels` is a map, while `spec.template.spec.containers` is a list. If I supply a map where a list is required, parsing may succeed but schema validation fails with a type error.

---

### 4. How do strings work in YAML?

**Answer:**

Strings can be plain, single-quoted, double-quoted, or block style. Plain values that resemble booleans, numbers, dates, or null may be interpreted as another type depending on YAML version and parser.

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

Single quotes preserve most characters literally; double quotes support escapes. I quote ambiguous values, image tags, wildcard-like values, and strings containing `:`, `#`, or leading special characters. I confirm the consumer's expected type rather than quoting everything automatically.

---

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

Anchors reduce duplication within one YAML document, but support and merge behavior depend on the consuming parser. Kubernetes manifests do not provide a general cross-file templating system through anchors. For complex reuse I prefer Helm, Kustomize, or pipeline templates because they make environment composition more explicit.

---

### 6. How is YAML used in Kubernetes?

**Answer:**

Kubernetes YAML describes API objects and their desired state. The main fields are `apiVersion`, `kind`, `metadata`, and `spec`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: example/api:1.0.0
          ports:
            - containerPort: 8080
```

I validate with a schema tool and `kubectl apply --dry-run=server -f deployment.yaml`. After applying, I check rollout status, Pods, events, and the Service endpoint. I store manifests in Git, review changes, pin images, and keep secrets outside plaintext YAML.

---

### 7. How is YAML used in CI/CD?

**Answer:**

CI/CD YAML defines triggers, stages, jobs, dependencies, variables, artifacts, environments, and deployment rules. Each platform has its own schema even though the syntax is YAML.

A safe flow defines CI for pull requests and restricts production deployment to protected branches or environments. I keep build and deployment jobs separate, publish one immutable artifact, use secret references rather than values, pin external tasks/actions, and add timeouts and rollback checks.

I validate using the platform’s linter and a test branch. A YAML parser only proves the file is syntactically valid; it does not prove that job permissions, conditions, or deployment logic are correct.

---

### 8. How do you validate YAML files?

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

If validation fails, I check indentation, duplicate keys, expected list/map types, unavailable API versions, and values altered by templating. I inspect rendered output because a correct template can still generate invalid YAML for specific values.

---

### 9. What are common YAML mistakes?

**Answer:**

Common mistakes include tabs, incorrect indentation, duplicate keys, missing colons, wrong list nesting, ambiguous unquoted values, inconsistent types, and multiline text with the wrong block style. In Kubernetes, label-selector mismatches and putting a field under the wrong parent are frequent logical errors.

My prevention measures are editor YAML support, `yamllint`, schema validation, small reviewed changes, and rendered-output tests for templates. I avoid manual copy-paste between environments and never assume that successful parsing means the application configuration is correct.

---

### 10. How do you manage environment-specific YAML?

**Answer:**

I keep a common base and store only differences per environment. The mechanism depends on the tool:

- Helm: one chart with `values-dev.yaml`, `values-stage.yaml`, and `values-prod.yaml`
- Kustomize: a base plus environment overlays
- CI/CD: reusable templates plus protected environment variables
- Applications: base configuration plus external configuration/secret references

I do not duplicate entire manifests because fixes then drift between environments. Secrets stay in a secret manager. CI renders the final configuration, validates schemas and policies, displays a reviewable diff, and promotes the same application version. After deployment I verify the environment received the intended values without exposing sensitive output.
