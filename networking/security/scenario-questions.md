# Security Networking Scenario Questions

### 1. How do you handle expired SSL/TLS certificates in production?

**Answer:**

- Use Let's Encrypt + Cert Manager in Kubernetes for auto-renewal.
- Monitor expiry with alerts.
- Rotate certificates via CI/CD pipeline before expiration.

**Detailed interview approach:**

First I identify which certificate actually expired — public ingress, an internal service, the API server, kubelet, a webhook, or a client. I check the issuer, SAN, chain, secret, and expiry using `openssl s_client`/`openssl x509` and the relevant controller's status.

For cert-manager, I check the Certificate, CertificateRequest, Order/Challenge, controller logs, whether the DNS/HTTP challenge is reachable, and the issuer's credentials.

I renew or rotate the certificate through the supported controller, reload whatever consumes it, and confirm the full chain and hostname from a real client. Cluster certificates follow the platform's own rotation procedure and node/control-plane sequence.

Alerts at 30/14/7 days out, automated renewal tests, a clear owner inventory, and protected issuer keys are what actually prevent an emergency expiry.
