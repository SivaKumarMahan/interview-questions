# Network Security Interview Summary

## TLS and Certificate Troubleshooting

An expired TLS certificate causes browser trust warnings, such as `ERR_CERT_DATE_INVALID`, and blocks the secure connection entirely. First capture the exact hostname, port, SNI, the client error, and the certificate that was actually served.

Check `notBefore`/`notAfter`, the SAN hostname, the issuer, the full chain, the server's clock, and whether a CDN, load balancer, or proxy is serving a different certificate than the backend.

## Renewal and issuance

For **Let's Encrypt**, check the Certbot timer/status, renewal logs, whether the HTTP-01/DNS-01 challenge is reachable, DNS, the firewall, and rate limits, before you run a renewal.

For a **purchased certificate**, generate and protect the key/CSR through the approved process, then install the issued leaf certificate along with the correct intermediate chain.

Never copy private keys into Git or into chat.

## Deployment and validation

Update the exact listener/server paths and permissions, validate the configuration (`nginx -t` or the platform's equivalent), reload gracefully where you can, and retest from an external client using SNI.

Confirm the new expiry date, hostname, chain, OCSP behavior where it's used, every load-balancer/region endpoint, and that the application is healthy.

Restarting the service will **not** fix the issue if you haven't actually replaced the active certificate.

## Preventing recurrence

- Certificate inventory and ownership
- Automated renewal
- Monitoring at 30/14/7 days
- Renewal and reload tests
- Updated CA contacts
- Protected key rotation
- Alerts on failed challenge or mismatched endpoints
