# Cloud Architecture Summary

## Three-Tier Application Architecture

A three-tier design separates responsibilities so each tier can be secured, changed, and scaled independently:

1. **Presentation tier:** web, mobile, or desktop interface. It displays information, accepts input, and calls application APIs.
2. **Application tier:** business logic and API services. It authenticates and authorizes requests, validates rules, coordinates workflows, and accesses approved data services.
3. **Data tier:** databases, caches, object storage, and data services. It persists and retrieves data with controlled access, encryption, backup, and recovery.

```text
user -> edge/load balancer -> presentation -> application -> data
                                                    |
                                          cache/queue/services
```

For an online purchase, the presentation tier submits the order, the application tier validates identity, inventory, price, and payment workflow, and the data tier records the order and inventory transaction. The response returns through the application and presentation tiers.

Separation improves maintainability and security, but tiers alone do not guarantee a good system. Production design also needs stateless scaling where possible, health-based load balancing, caching, asynchronous messaging, least-privilege network paths, secrets management, observability, dependency timeouts and retries, data consistency, backups, and tested disaster recovery. Scale the bottleneck shown by metrics rather than increasing every tier equally.
