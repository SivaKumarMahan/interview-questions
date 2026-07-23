# Network Security Interview Summary

## TLS and Certificate Troubleshooting

An expired TLS certificate causes browser trust warnings such as `ERR_CERT_DATE_INVALID` and blocks secure connections. First capture the exact hostname, port, SNI, client error, and served certificate. Check `notBefore`/`notAfter`, SAN hostname, issuer, complete chain, server time, and whether a CDN/load balancer/proxy is serving a different certificate than the backend.

## Renewal and issuance

For **Let's Encrypt**, inspect the Certbot timer/status, renewal logs, HTTP-01/DNS-01 challenge reachability, DNS, firewall, and rate limits before running renewal. For a **purchased certificate**, generate and protect the key/CSR through the approved process and install the issued leaf plus correct intermediate chain. Never copy private keys into Git or chat.

## Deployment and validation

Update the exact listener/server paths and permissions, validate configuration (`nginx -t` or the platform equivalent), reload gracefully where possible, and retest from an external client with SNI. Verify the new expiry, hostname, chain, OCSP behavior where used, every load-balancer/region endpoint, and application health. A service restart without replacing the correct active certificate will **not** fix the issue.

## Preventing recurrence

- Certificate inventory and ownership
- Automated renewal
- Monitoring at 30/14/7 days
- Renewal and reload tests
- Updated CA contacts
- Protected key rotation
- Alerts on failed challenge or mismatched endpoints
