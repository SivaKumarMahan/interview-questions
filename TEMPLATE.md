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

<details><summary>Q1. [Basic] What is a Kubernetes Service, and why do you need one?</summary>

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

</details>

<details><summary>Q2. [Intermediate] A Service has no endpoints. How do you troubleshoot it? <em>(scenario)</em></summary>

**Answer:**

1. Compare the Service selector with the Pod labels: `kubectl get pods --show-labels`.
2. Check that the Pods are `Ready`. Pods that fail their readiness probe are left out of the endpoints.
3. Check that `targetPort` matches the port the container listens on.

</details>

<details><summary>Q3. [Advanced] How did you expose internal APIs securely across teams in your last project? <em>(asked in interview round)</em></summary>

**Answer:**

TODO (Siva): add your real example here.

</details>

---

## Rules for every topic file

- **Scope line:** one sentence at the top, starting with `>`.
- **Sections:** always `## Key Concepts` first, then `## Interview Questions`.
- **Questions:** wrap each one in `<details><summary>Q<n>. [Level] question</summary>` ... `</details>`, number them 1, 2, 3, and keep related questions next to each other. Leave a blank line after `<summary>` and before `</details>` so the answer's Markdown renders.
- **Difficulty:** `[Basic]` for definitions, "what is X", and "difference between X and Y". `[Intermediate]` for day-to-day how-to and standard troubleshooting. `[Advanced]` for design at scale, security incidents, multi-team or multi-region trade-offs, and tricky edge cases.
- **Tags:** add `<em>(scenario)</em>` for troubleshooting or design situations, and `<em>(asked in interview round)</em>` for questions asked in a real interview, at the end of the summary line.
- **No Markdown inside `<summary>`:** GitHub does not render it there. Use `<code>` instead of backticks and `<em>` instead of `*`.
- **Style:** simple English, short sentences, practical examples, and commands in code blocks.
- **Personal details:** never invent an experience or a company name. Leave a `TODO (Siva):` placeholder.
