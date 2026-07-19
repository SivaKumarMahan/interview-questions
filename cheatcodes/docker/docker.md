# Docker Cheatcode

## Containers and images

```bash
docker version
docker ps
docker ps -a
docker images
docker pull <image>@sha256:<digest>
docker build -t <registry>/<image>:<tag> .
docker run --name <name> -d -p 127.0.0.1:8080:80 <image>:<tag>
docker logs --tail 200 <container>
docker inspect <container>
docker exec -it <container> /bin/sh
docker stop <container>
docker rm <container>
docker image rm <image>
docker system df
```

Inspect and back up state before pruning. Do not use “remove everything” commands on production hosts.

## Volumes

```bash
docker volume ls
docker volume inspect <volume>
docker volume create <volume>
docker run --mount type=volume,src=<volume>,dst=/app/data <image>
```

## Networks

```bash
docker network ls
docker network inspect <network>
docker network create <network>
docker network connect <network> <container>
docker network disconnect <network> <container>
docker run --name mysql --network app-net <mysql-image>
docker run --name backend --network app-net <backend-image>
```

The backend connects using `mysql:<port>`, not a fixed container IP.

## Compose

```bash
docker compose config
docker compose up -d
docker compose ps
docker compose logs --tail 200
docker compose down
```

Do not place database passwords directly in Compose YAML; use an approved secret mechanism and protect `.env` files from Git.
