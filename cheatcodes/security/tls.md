# TLS Certificate Cheatcode

## Inspect the served certificate

```bash
openssl s_client -connect <domain>:443 -servername <domain> -showcerts </dev/null
openssl s_client -connect <domain>:443 -servername <domain> </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -serial -dates -ext subjectAltName
```

Check the actual edge/load-balancer endpoint, hostname/SNI, SAN, expiry, issuer, and complete chain.

## Certbot and web server

```bash
certbot certificates
certbot renew --dry-run
certbot renew
nginx -t
systemctl reload nginx
apachectl configtest
systemctl reload apache2
```

Do not renew/restart blindly. Inspect renewal logs and challenge reachability, back up configuration, confirm active certificate paths, prefer graceful reload, and retest externally. Use the service name appropriate to the distribution.
