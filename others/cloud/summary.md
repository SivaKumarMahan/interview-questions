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

For an online purchase, the presentation tier submits the order, the application tier checks identity, inventory, price, and the payment workflow, and the data tier records the order and the inventory transaction. The response then travels back through the application and presentation tiers.

Separating the tiers improves maintainability and security, but tiers alone don't guarantee a good system.

A production design also needs stateless scaling wherever possible, health-based load balancing, caching, asynchronous messaging, network paths that only allow the access they need, secrets management, observability, timeouts and retries on dependencies, data consistency, backups, and a tested disaster-recovery plan.

Scale whichever tier the metrics show is actually the bottleneck, not every tier equally.
