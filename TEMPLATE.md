# Topic File Template

Copy this layout when you add a new topic file. Name the file `NN-short-topic-name.md` inside the tool's folder, for example `kubernetes/03-networking-and-traffic.md`. The number sets the study order: `01` is the basics, and later numbers cover production and troubleshooting.

Everything between the two lines below is the template.

---

# Tool: Topic Title

> One sentence that says what this file covers, for example: "Services, Ingress, DNS, and NetworkPolicies, and how traffic reaches a Pod."

## Key Concepts

### Concept name

Explain the idea in two to four short sentences. Say what it is, why it exists, and when you use it.

```bash
# A small command or config example
kubectl get svc -n my-app
```

### Another concept name

Use a short list when there are several points:

- **Point one:** one short sentence.
- **Point two:** one short sentence.

## Interview Questions

### 1. What is a Kubernetes Service, and why do you need one?

**Answer:**

Pods get new IP addresses every time they restart, so clients cannot rely on a Pod IP. A Service gives a group of Pods one stable name and IP address. It selects the Pods by label and sends traffic only to Pods that are ready.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8080
```

**How to verify:** `kubectl get endpoints api` should list the Pod IPs. If it is empty, the selector does not match the Pod labels.

### 2. A Service has no endpoints. How do you troubleshoot it? *(scenario)*

**Answer:**

1. Compare the Service selector with the Pod labels: `kubectl get pods --show-labels`.
2. Check that the Pods are `Ready`. Pods that fail their readiness probe are left out of the endpoints.
3. Check that `targetPort` matches the port the container listens on.

### 3. How did you expose an internal API in your last project? *(asked in interview round)*

**Answer:**

TODO (Siva): add your real example here.

---

## Rules for every topic file

- **Scope line:** one sentence at the top, starting with `>`.
- **Sections:** always `## Key Concepts` first, then `## Interview Questions`.
- **Questions:** number them 1, 2, 3, and keep related questions next to each other.
- **Tags:** add *(scenario)* for troubleshooting or design situations, and *(asked in interview round)* for questions asked in a real interview.
- **Style:** simple English, short sentences, practical examples, and commands in code blocks.
- **Personal details:** never invent an experience or a company name. Leave a `TODO (Siva):` placeholder.
