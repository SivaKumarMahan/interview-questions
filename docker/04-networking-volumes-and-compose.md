# Docker: Networking, Volumes, and Compose

> Docker networks, volumes and bind mounts, and running multi-container applications with Docker Compose and beyond.

## Key Concepts

### Docker networking

Docker provides multiple network types.

**1. Default bridge.** When you run, say, an nginx container, the web server listens on port 80 *inside* the container.

From inside the container `curl 127.0.0.1:80` returns the page (`127.0.0.1` is the loopback address for localhost), but you cannot reach it from the host by default. Inspect the container and networks:

```bash
docker inspect nginx-container
docker network ls
docker network inspect bridge
```

The default bridge network does not expose container services automatically — you must forward ports — and it does **not** provide internal DNS name resolution, so containers can reach each other by IP but not by name.

**Port forwarding** publishes a container port to a host port:

```bash
# docker run -d -p <host port>:<container port> --name <container name> <image>
docker run -t -d -p 5000:80 --name nginx-container nginx:latest
```

**2. User-defined bridge network.** Docker recommends creating your own network rather than using the default bridge.

It provides isolation from the host network *and* name resolution between containers (they still need port forwarding to be reached from the host).

```bash
docker network create blog-network
docker run -itd --network blog-network --name nginx-con nginx
docker network inspect blog-network
docker inspect nginx-con
```

Containers on `blog-network` can now ping each other by name (e.g. `ping nginx-con`).

**3. Host network.** The container shares the host's network stack directly:

```bash
docker run -td --network host --name nginx-server nginx:latest
docker inspect nginx-server | grep IPAddress
```

The container has no IP of its own — it uses the host machine's IP.

### Docker volumes

Docker isolates a container's content from your local filesystem, so deleting a container deletes everything inside it. To persist data a container generates, use volumes.

- **Bind mount** — a file or directory on the host machine is mounted into a container.
- **Docker volume** — a location on your filesystem managed by Docker. It does not increase the size of the containers using it, and its contents live outside any single container's lifecycle.

There are two syntaxes:

- **`-v` / `--volume`** — three colon-separated fields: (1) host path (bind mount) or volume name, (2) mount path in the container, (3) optional comma-separated options such as `ro`, `z`, `Z`.
- **`--mount`** — comma-separated key-value pairs: `type` (`bind`, `volume`, or `tmpfs`), `source`, and `target` (the mount path in the container).

**Example — shared named volume across containers.** Note: `-v <name>:/path` (no leading `/`) creates a **named volume**, not a true bind mount (a bind mount requires an absolute host path like `-v /host/dir:/app/log`).

That is why the shared data below is *not* visible on the host filesystem — it lives in Docker-managed storage.

```bash
mkdir docker-bind-mount
docker run -t -d -v docker-bind-mount:/app/log --name captain-america busybox
docker run -t -d -v docker-bind-mount:/app/log --name thor busybox
docker run -t -d -v docker-bind-mount:/app/log --name hulk busybox
docker run -t -d -v docker-bind-mount:/app/log --name iron-man alpine

# equivalent with --mount
docker run -t -d --mount type=bind,source=docker-bind-mount,target=/app/log \
  --name captain-america busybox
```

Logs written under `/app/log` in any of these containers are visible to all of them. Inspect a container's `Mounts` section for details:

```bash
docker inspect hulk
```

**Example — Docker volumes.**

```bash
docker volume create thor-vol
docker volume create hulk-vol
docker volume ls
docker volume inspect thor-vol
```

Mount a volume when creating containers (with `--mount`, `type` defaults to `volume` when the source is a volume name):

```bash
docker run -d \
  --name thor-container \
  --mount type=volume,source=thor-vol,target=/app \
  nginx:latest

docker run -d \
  --name hulk-container \
  --mount source=thor-vol,target=/app \
  nginx:latest
```

Both containers share the data written under `/app`. Remove volumes with:

```bash
docker volume rm <volume-name> [<volume-name>...]
```

### Docker Compose

Docker Compose is a tool for defining and running multi-container applications. You describe all the services in a single file (`docker-compose.yml`) and run the whole application with one command, `docker-compose up`.

#### Why Docker Compose

- You define application services and their build options — networks, volumes, environment variables — in one `docker-compose.yml`.
- All services share the same network and can talk to each other internally (front-end, API, DB services, etc.).
- You build and run every service with a single command: `docker-compose up`.
- Because the whole application is one config file, it is easy to share, store in version control (GitHub), and wire into a CI/CD pipeline.

#### Example: multi-container Flask + Postgres app

This example runs two containers — a Postgres database and a Flask web app that talks to it.

Create the folder structure:

```bash
mkdir docker-compose
cd docker-compose
# create files/directory to store the code
touch docker-compose.yml requirements.txt app.py Dockerfile
mkdir -p static/css
touch static/css/style.css
mkdir templates
touch templates/index.html
```

What each file is for:

- **Dockerfile** — builds the web application image (a Flask/gunicorn image; see the `docker init` section above for a representative Python Dockerfile).
- **app.py** — the Flask code. It initializes SQLAlchemy, sets the PostgreSQL connection URI, defines a data model with `id` and `name` columns, and defines routes on `/` handling both GET and POST to store and render data.
- **requirements.txt** — the application dependencies (Flask, Flask-SQLAlchemy, the Postgres driver, gunicorn, etc.).
- **docker-compose.yml** — the Compose config file.
- **templates/index.html** — the HTML for the Flask app.
- **static/css/style.css** — the CSS.

The `docker-compose.yml` defines two services, `app` and `db`, on the same network, with these characteristics: `app` port 5000 is exposed to host port 5000 and `db` port 5432 to host port 5432; `app` depends on `db`; a health check on `db` ensures Postgres is ready before `app` connects; a named volume persists the database; and environment variables hold the Postgres credentials and database name.

A configuration matching that description:

```yaml
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:latest
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

Normally you should **not** hardcode credentials in the config file — see "Using environment variables" below.

If you would rather not write Compose files by hand, use `docker init` to generate them (see the `docker init` section above).

#### Running the application

```bash
git clone https://github.com/akhileshmishrabiz/Devops-zero-to-hero
cd Devops-zero-to-hero/AWS-Projects/multi-container-app-docker-compose

docker-compose up --build
```

Check the running containers:

```text
$ docker ps
CONTAINER ID  IMAGE                              COMMAND                  STATUS                 PORTS                    NAMES
7c99c9539298  flask-app-docker-compose-app       "python app.py"          Up About a minute      0.0.0.0:5000->5000/tcp   flask-app-docker-compose-app-1
78f6a230ca24  postgres:latest                    "docker-entrypoint.s…"   Up About a minute (healthy)  0.0.0.0:5432->5432/tcp   flask-app-docker-compose-db-1
```

On a local machine, access the app at `http://localhost:5000` (`127.0.0.1`). On an EC2 instance with a public IP, use that IP on port 5000. You can connect to the Postgres DB from pgAdmin or a DB viewer.

Because the database uses a named volume, data persists across restarts:

```bash
docker-compose down
docker-compose up
```

#### Installing Docker and Docker Compose (Amazon Linux 2)

Docker Desktop is the easiest option locally (it installs both Docker and Compose). On a cloud Linux VM such as an Amazon Linux 2 EC2 instance:

```bash
# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user
# Log out and back in to run docker without sudo
```

```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
# Check the installation
docker-compose version
```

#### Using environment variables for credentials

Instead of hardcoding credentials in `docker-compose.yml`, use a `.env` file. Create a `.env` in the same location as `docker-compose.yml`, remove the environment values from the Compose file, and put them in `.env`.

Compose loads it automatically on `docker-compose up`.

One problem: if you commit your code to GitHub, a `.env` in the repo exposes the credentials. Keep the secrets file out of the repo (e.g. `.gitignore` it) and pass a dedicated env file explicitly:

```bash
docker-compose --env-file db-variables.env up
```

### Docker Networking Overview

Docker networking connects containers to each other, to the host, and to the outside world, while still keeping them isolated. On a typical Linux host, Docker creates a bridge interface called `docker0`. Containers get an address on that bridge's subnet, and outbound traffic normally goes through the host's NAT rules (`iptables` or `nftables`).

### Network Drivers

| Driver | What it's for |
| --- | --- |
| `bridge` | Single-host container networking. Prefer a user-defined bridge over the default one — it gives you proper isolation and lets containers find each other by name. |
| `host` | Shares the host's own network stack directly. No port mapping, and almost no isolation. Only use this when you have a specific, measured reason to. |
| `none` | No real network interface beyond loopback. Useful when a container should be fully isolated from the network. |
| `overlay` | Multi-host networking, used with Docker Swarm. |
| `macvlan` | Gives a container its own MAC address and IP on the physical network. Needs sign-off from the network team, and has some quirks around host-to-container communication. |
| `ipvlan` | Similar to macvlan — connects containers at layer 2/3 — but handles MAC addresses differently and scales differently. |

`EXPOSE 80` in a Dockerfile just documents which port the app uses. To actually reach it from outside the container, you publish it:

```bash
docker run -p 8080:80 image
```

This maps host port `8080` to container port `80`. Containers on the same user-defined network can reach each other by name — for example, `mysql:3306` — so avoid hardcoding a container's IP address anywhere in configuration; it can change.

### Best Practices

Give each application (or trust boundary) its own network. Publish only the ports you actually need, on the interfaces you intend. Avoid `--network host` unless you have a real reason. Use DNS names instead of IPs. Restrict inbound and outbound traffic with host or cloud firewall policy. Keep an eye on network and NAT connection capacity.

When troubleshooting, work through: `docker inspect` on the container, its network namespace routes and listening ports, Docker's DNS, the host firewall and NAT rules, port mappings, and — if needed — a packet capture on both the host and container side.

## Interview Questions

<details><summary>Q1. [Basic] What Docker network types exist, and which is common in production?</summary>

**Answer:**

The common Docker network drivers are `bridge` for single-host container networking, `host` for sharing the host's own network stack directly, `none` for no networking at all, and `overlay` for multi-host networking under Swarm. `macvlan` and `ipvlan` can put containers directly on the physical network, but they add real operational complexity.

A user-defined bridge network is a sensible default for local or single-host work, since it gives you both DNS-based service discovery and isolation.

In production, platforms like Kubernetes and ECS usually bring their own networking layer (a CNI plugin or VPC networking) instead of exposing Docker's raw network types directly. The right choice comes down to isolation needs, service discovery, policy requirements, observability, and how failures should be contained.

</details>

<details><summary>Q2. [Basic] What are the Docker network types (bridge, host, none, overlay, macvlan), and which one do you use?</summary>

Docker provides several network drivers that define how containers communicate with each other and the outside world.

#### 11.1 Bridge network (most common)

This is the default network created by Docker.

- Containers on the same bridge network can communicate with each other.
- External access is provided using port mapping (`-p`).
- Best suited for standalone applications running on a single host.

```bash
docker network create my-bridge

docker run -d --network my-bridge nginx
```

**Use case:** web applications, APIs, databases running on a single Docker host.

#### 11.2 Host network

The container shares the host's network stack.

- No separate container IP.
- No NAT or port mapping required.
- Better network performance.
- Only one service can use a given port on the host.

```bash
docker run --network host nginx
```

**Use case:** high-performance networking applications.

#### 11.3 None network

The container has no network connectivity.

- No internet access.
- No communication with other containers.

```bash
docker run --network none nginx
```

**Use case:** secure batch jobs or isolated containers.

#### 11.4 Overlay network

Used when containers run on multiple Docker hosts.

- Enables communication across different hosts.
- Commonly used with Docker Swarm.

```bash
docker network create -d overlay my-overlay
```

**Use case:** multi-host container deployments.

#### 11.5 Macvlan network

Assigns a unique MAC and IP address to each container.

- Containers appear as physical devices on the network.
- Communicate directly with the LAN.

**Use case:** legacy applications requiring direct network access.

#### 11.6 Which one do you use?

> "In my projects, I primarily use the Bridge network because most of our Docker containers run on a single host during development or in CI/CD pipelines. It provides isolated networking, and I expose only the required ports using `-p`. For Kubernetes deployments, I don't manage Docker networking directly because Kubernetes uses its own Container Network Interface (CNI) plugins such as Azure CNI or Calico to handle pod networking."

#### 11.7 Follow-up: how do containers communicate on a bridge network?

Containers connected to the same bridge network can communicate using container names because Docker provides an internal DNS service.

```bash
docker network create app-network

docker run -d --name db --network app-network mysql

docker run -d --name web --network app-network nginx
```

The web container can connect to the database using:

```
db:3306
```

instead of using an IP address.

#### 11.8 Quick summary

| Network Type | Description | Typical Use |
|---|---|---|
| Bridge | Default isolated network on one host | Most commonly used |
| Host | Shares host network | High-performance apps |
| None | No networking | Isolated containers |
| Overlay | Multi-host networking | Docker Swarm |
| Macvlan | Container gets its own MAC/IP | Legacy or direct LAN access |

#### 11.9 Short interview conclusion

> "Docker supports Bridge, Host, None, Overlay, and Macvlan networks. I mostly use the Bridge network for standalone containers because it provides secure communication between containers on the same host while allowing controlled external access through port mapping. For Kubernetes environments, networking is managed by the cluster's CNI plugin rather than Docker network drivers."

</details>

<details><summary>Q3. [Basic] What is the difference between <code>EXPOSE</code> in a Dockerfile and <code>-p</code> in <code>docker run</code>?</summary>

`EXPOSE 80` documents that the application expects traffic on container port 80.

It does not publish the port to the host. The application must also be configured to listen on that port.

```bash
docker build -t mynginx .
docker run mynginx
```

The container runs, but the host cannot reach its port directly because no host port was published.

```bash
docker run -p 8080:80 mynginx
```

`-p 8080:80` maps host port 8080 to container port 80.

Open `http://localhost:8080` to reach the application.

Think of it like this:

- **`EXPOSE`:** The restaurant has a door at a known location.
- **`-p`:** The host opens a route that customers can use to reach that door.

</details>

<details><summary>Q4. [Basic] How do you run NGINX on a Linux server using Docker?</summary>

```bash
docker pull nginx:1.27-alpine
```

This downloads a specific NGINX image version from Docker Hub.

```bash
docker run -d -p 80:80 --name mynginx nginx:1.27-alpine
```

- `-d` → Runs the container in detached mode (in the background).
- `-p 80:80` → Maps port 80 of the container to port 80 on the host.
- `--name mynginx` → Assigns a name to your container for easy reference.
- `nginx:1.27-alpine` → The image and version to run.

Open `http://<your-server-public-ip>` to see the NGINX welcome page. The server firewall or cloud security rule must allow inbound port 80.

```bash
docker run -d -p 8080:80 --name web \
  -v /home/ubuntu/website:/usr/share/nginx/html \
  nginx:1.27-alpine
```

The container listens on port 80, and Docker maps it to host port 8080. The `-v` option mounts the host's website directory into NGINX's default content directory.

Open `http://<your-server-ip>:8080` to view the website.

</details>

<details><summary>Q5. [Intermediate] How do you troubleshoot container DNS resolution failures?</summary>

**Answer:**

First I figure out the scope: is it one container, one network, the whole host, or every destination? Inside the container, I check `/etc/resolv.conf`, run `getent hosts`, look at the application's own error, and test whether connecting by IP works even when connecting by name doesn't.

On the host, I check the Docker network, Docker's embedded DNS server (`127.0.0.11`), the upstream DNS server, routes and firewall rules, any VPN, and the daemon logs.

```bash
docker exec app cat /etc/resolv.conf
docker exec app getent hosts db.internal
docker network inspect appnet
```

I also check the search domain, the DNS record type, whether a stale cache (TTL) is the culprit, and which network the container is actually attached to. I avoid "fixing" this by hardcoding an IP address — that just hides the real problem. Once I fix it, I re-test both the intended hostname and an external one, and keep an eye out for it recurring.

</details>

<details><summary>Q6. [Intermediate] What strategies do you use for debugging container networking issues?</summary>

**Answer:**

I follow the path a packet actually takes: the app binding to a port inside the container → the container's own network namespace and IP → Docker's bridge or overlay network → the host's routes, NAT, and firewall → the remote service or load balancer.

Along the way I check `docker ps` and its port mappings, `docker inspect`, the networks involved, what's actually listening, DNS, routes, firewall rules, and — when it's approved — a packet capture. I test both from inside the source container and from the host, to narrow down which layer is broken.

The usual culprits: the app is bound to `localhost` instead of `0.0.0.0`, the wrong host port was published, the containers are on different networks, DNS isn't resolving, the host firewall is blocking traffic, two networks have overlapping IP ranges, MTU is misconfigured, or a proxy is in the way. I make the smallest fix that addresses the real cause, re-test in both directions, confirm the app is healthy, and write the working network configuration down so it doesn't get lost.

</details>

<details><summary>Q7. [Basic] What are Docker volumes and bind mounts, and when would you use each?</summary>

**Answer:**

A named volume is managed by Docker and is the right choice for data a container needs to keep. A bind mount points at a specific path on the host — handy for local development or config files, but it ties the container tightly to the host's folder layout and permissions.

```bash
docker volume create dbdata
docker run -v dbdata:/var/lib/postgresql/data postgres
docker run --mount type=bind,src="$PWD/config",dst=/app/config,readonly app
```

For anything persistent, I plan backup, restore, ownership, encryption, and capacity up front. Removing a container doesn't automatically remove its volume. In an orchestrated environment I use the platform's own persistent volumes rather than assuming a local Docker volume gives high availability.

</details>

<details><summary>Q8. [Basic] What is Docker Compose?</summary>

**Answer:**

Docker Compose describes a multi-container application — its services, networks, volumes, environment variables, and dependencies — in one YAML file, and runs it with `docker compose`.

```yaml
services:
  api:
    build: .
    ports: ["8080:8080"]
    depends_on: [db]
  db:
    image: postgres:16
    volumes: ["dbdata:/var/lib/postgresql/data"]
volumes: { dbdata: {} }
```

It's great for local development, integration tests, and small single-host setups. Note that `depends_on` only waits for the container to start, not for the database inside it to actually be ready — you still need a health check or a retry loop for that.

For production running across multiple nodes, an orchestrator like Kubernetes or ECS is normally what handles scheduling, high availability, secrets, and scaling.

</details>

<details><summary>Q9. [Intermediate] How do you run multi-container applications in production without Compose?</summary>

**Answer:**

I use an orchestrator such as Kubernetes, ECS, or AKS. Each component gets its own image, its own Deployment or task definition, a way for other services to find it, its own configuration and identity, and its own scaling, health, and resource settings.

The delivery pipeline publishes signed, fixed images, and then Helm, plain manifests, or GitOps declares how the application should run. Databases usually run as a managed service rather than as a container, and secrets come from a dedicated secret manager.

I make sure there's redundancy, health probes, a rolling or canary rollout strategy, network policies, monitoring, logging, backups, and a disaster recovery plan. Compose is a good way to model services locally, but production needs a real cluster scheduler and the operational pieces around it.

</details>
