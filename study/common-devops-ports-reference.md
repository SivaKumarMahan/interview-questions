# Common DevOps Ports Reference

A quick-lookup table of ports that come up constantly across networking, CI/CD, Kubernetes, and observability interview questions.

| Port | Service |
| --- | --- |
| 22 | SSH |
| 53 | DNS |
| 80 | HTTP |
| 443 | HTTPS |
| 3306 | MySQL |
| 5432 | PostgreSQL |
| 1433 | Microsoft SQL Server |
| 27017 | MongoDB |
| 6379 | Redis |
| 5672 | RabbitMQ |
| 9092 | Kafka |
| 2181 | ZooKeeper |
| 8080 | Jenkins / Tomcat |
| 9000 | SonarQube |
| 9090 | Prometheus |
| 3000 | Grafana |
| 5601 | Kibana |
| 9200 | Elasticsearch |
| 5044 | Logstash / Beats |
| 2375 | Docker API (unencrypted - not recommended) |
| 2376 | Docker API over TLS |
| 6443 | Kubernetes API Server |
| 10250 | Kubelet |
| 10257 | kube-controller-manager |
| 10259 | kube-scheduler |
| 8472 | VXLAN / Flannel |
| 179 | BGP / Calico |
| 10254 | NGINX Ingress health/metrics |
| 25 | SMTP |
| 389 | LDAP |
| 636 | LDAPS |

**Most important for interviews:** `22, 53, 80, 443, 8080, 9000, 9090, 3000, 6443, 10250, 3306, 5432, 6379, 9092, 9200, 5601`.
