# Security Networking Scenario Questions

### 1. How do you handle expired SSL/TLS certificates in production?

**Answer:**

- Use Let's Encrypt + Cert Manager in Kubernetes for auto-renewal.
- Monitor expiry with alerts.
- Rotate certificates via CI/CD pipeline before expiration.

**Detailed interview approach:**

I first identify which certificate expired—public ingress, internal service, API server, kubelet, webhook, or client—and inspect issuer, SAN, chain, secret, and expiry with `openssl s_client`/`openssl x509` and the relevant controller status.

For cert-manager I inspect Certificate, CertificateRequest, Order/Challenge, controller logs, DNS/HTTP challenge reachability, and issuer credentials.

I renew or rotate through the supported controller, reload the consumer, and verify the complete chain and hostname from a real client. Cluster certificates follow the platform-specific rotation procedure and node/control-plane sequence.

Alerts at 30/14/7 days, automated renewal tests, owner inventory, and protected issuer keys prevent emergency expiry.
