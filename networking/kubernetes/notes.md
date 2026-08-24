# Kubernetes Networking Notes

### Q: Explain port, targetPort and nodePort in kubernetes?

In Kubernetes, `port` is the port a Service exposes inside the cluster. `targetPort` is the port on the container that traffic actually gets sent to. `nodePort` is the port opened on each worker node so the service can be reached from outside the cluster.

Example: request → `nodePort` (30080) → service `port` (80) → container `targetPort` (8080).

- **`port`:** The port where the Service is exposed inside the cluster. Other pods reach the service through this port.
- **`targetPort`:** The port on the pod's container that the service forwards traffic to. This is where the application actually listens.
- **`nodePort`:** A port opened on every worker node. It lets you reach the service from outside the cluster using `<node-ip>:<nodePort>`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-web-service
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80           # Service port (cluster-internal)
    targetPort: 8080   # Pod port (container)
    nodePort: 30080    # Node port (external)
```

**NodePort range (by default):** `30000–32767`.

---

### Q: what is port forwarding in kubernetes?

Port forwarding lets you reach a single pod directly from your local machine. You forward a port on your machine to a port on the pod. It's mainly used for debugging or for reaching an app inside a pod without setting up a full service.

```bash
kubectl port-forward <pod-name> <local-port>:<pod-port>
```

Example:

```bash
kubectl port-forward my-pod 8080:80
```

This forwards local port `8080` to port `80` on the pod named `my-pod`.

You can then reach the app by opening `http://localhost:8080` in a browser, or by using `curl`.

**Use Cases:**

- **Debugging:** Look at logs or interfaces running inside a pod.
- **Testing:** Try out a service without exposing it externally.
- **Accessing Databases:** Connect to a database running in a pod to manage it or run queries.

**Limitations:**

- Port forwarding only lasts as long as the `kubectl` command keeps running.
- It works only against pods, not directly against services or deployments.
- You need `kubectl` access to the cluster and permission to reach the pod.

**Example Command:**

```bash
kubectl port-forward deployment/my-app 9090:80
```

This forwards local port `9090` to port `80` on the pods managed by the `my-app` deployment.

You can now reach the app at `http://localhost:9090`.

---

### Q: How do you restrict pod-to-pod communication in a Kubernetes cluster?

To restrict pod-to-pod traffic in a cluster, use **Network Policies**. A Network Policy is a rule that controls which pods can talk to which, based on labels, namespaces, and ports.

Here's how to set one up:

1. **Check that your CNI supports Network Policies.**
   - Your cluster's network plugin needs to enforce them — for example Calico, Cilium, or Weave.
2. **Write the policy.**
   - Create a Network Policy YAML file that spells out the allowed traffic. Here's an example that only lets frontend pods reach backend pods:

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-frontend-to-backend
     namespace: default
   spec:
     podSelector:
       matchLabels:
         role: backend         # Target backend pods
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             role: frontend    # Allow only frontend pods
       ports:
       - protocol: TCP
         port: 80
   ```

   - Here, only pods labeled `role: frontend` can reach pods labeled `role: backend`, and only on port 80.
3. **Apply the policy:**

   ```bash
   kubectl apply -f network-policy.yaml
   ```

4. **Test it.**
   - Confirm that allowed pod-to-pod traffic still works, and that traffic that should be blocked actually is.
5. **Add more policies as needed.**
   - Different pods and namespaces will need their own rules.
6. **Keep reviewing your policies.**
   - Check that they still match how the application works, and update them as the architecture changes.

Network Policies are the main tool for restricting pod-to-pod traffic. Used well, they improve security and give you clear control over how traffic flows between parts of your application.

---
