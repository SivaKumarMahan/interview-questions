# Kubernetes Networking Notes

### Q: Explain port, targetPort and nodePort in kubernetes?

In Kubernetes, `port` is the service's port inside the cluster, `targetPort` is the container port the traffic is sent to, and `nodePort` is the port exposed on each worker node for external access.

Example: request → `nodePort` (30080) → service `port` (80) → container `targetPort` (8080).

- **`port`:** The port on which the Kubernetes Service is exposed within the cluster. Other pods can access the service using this port.
- **`targetPort`:** The port on the container (pod) that the service forwards traffic to. This is where the application inside the pod is actually listening.
- **`nodePort`:** A port on each worker node that exposes the service to external traffic. This allows access to the service from outside the cluster using `<node-ip>:<nodePort>`.

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

Port forwarding in Kubernetes allows you to access a specific pod directly from your local machine by forwarding a local port to a port on the pod. It's typically used for debugging or accessing applications running inside pods without exposing them via a service.
```bash
kubectl port-forward <pod-name> <local-port>:<pod-port>
```

Example:

```bash
kubectl port-forward my-pod 8080:80
```

This command forwards local port `8080` to port `80` on the pod named `my-pod`.

You can then access the application running on the pod by navigating to `http://localhost:8080` in your web browser or using `curl`.

**Use Cases:**

- **Debugging:** Access application logs or interfaces running inside a pod.
- **Testing:** Test services running in pods without exposing them externally.
- **Accessing Databases:** Connect to databases running in pods for management or queries.

**Limitations:**

- Port forwarding is temporary and only lasts as long as the `kubectl` command is running.
- It only works for pods, not services or deployments directly.
- Requires `kubectl` access to the cluster and appropriate permissions to access the pod.

**Example Command:**

```bash
kubectl port-forward deployment/my-app 9090:80
```

This forwards local port `9090` to port `80` of the pods managed by the `my-app` deployment.

Now you can access the application running in the `my-app` pods via `http://localhost:9090`

---

### Q: How do you restrict pod-to-pod communication in a Kubernetes cluster?

To restrict pod-to-pod communication in a Kubernetes cluster, you can use **Network Policies**. Network Policies allow you to define rules that control the traffic flow between pods based on labels, namespaces, and ports.

Here's how to implement pod-to-pod communication restrictions using Network Policies:

1. **Enable Network Policy Support:**
   - Ensure that your Kubernetes cluster has a network plugin that supports Network Policies, such as Calico, Cilium, or Weave.
2. **Define Network Policies:**
   - Create a Network Policy YAML manifest to specify the communication rules. Here's an example of a Network Policy that restricts communication to only allow traffic from pods with a specific label:

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

   - In this example, only pods with the label `role: frontend` can communicate with pods labeled `role: backend` on port 80.
3. **Apply the Network Policy:**
   - Use the following command to apply the Network Policy to your cluster:

   ```bash
   kubectl apply -f network-policy.yaml
   ```

4. **Test the Policy:**
   - Verify that the Network Policy is working as expected by testing pod-to-pod communication.
   - Attempt to communicate between pods that should be allowed and those that should be restricted based on the defined policy.
5. **Create Additional Policies:**
   - You can create multiple Network Policies to define different communication rules for various pods and namespaces as needed.
6. **Monitor and Update Policies:**
   - Regularly monitor the effectiveness of your Network Policies and update them as your application architecture evolves.

By using Network Policies, you can effectively restrict pod-to-pod communication in your Kubernetes cluster, enhancing security and controlling traffic flow between different components of your applications.

---
