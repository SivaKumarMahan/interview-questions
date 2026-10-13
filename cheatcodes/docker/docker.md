# Docker Cheatcode

## Version and system info

```bash
docker --version                  # Show the Docker client version
docker version                    # Show client and server (engine) versions
docker info                       # Show engine details: containers, images, storage driver, cgroup driver
```

If `docker version` shows the client but errors on the server part, the Docker daemon is not running or your user cannot reach the Docker socket.

## Images

```bash
docker images                     # List all images
docker pull <image>               # Pull an image from Docker Hub
docker build -t <name>:<tag> .    # Build image from Dockerfile in current directory
docker build -f <file> .          # Build image from a specific Dockerfile
docker tag <image> <new-image>    # Create a tag for an image
docker rmi <image>                # Remove an image
docker image prune                # Remove unused images
docker image inspect <image>      # Display detailed information about an image
docker history <image>            # Show the history of an image
docker save <image> > <file.tar>  # Save an image to a tar archive
```

In production, prefer pulling and running images by their fixed digest (`<image>@sha256:<digest>`) rather than a mutable tag — a digest always points to the exact same content. Check what you have and back it up before pruning, and never run "remove everything" commands on production hosts.

## Containers

```bash
docker ps                              # List running containers
docker ps -a                           # List all containers (running and stopped)
docker run <image>                     # Run a container from an image
docker run -d <image>                  # Run container in detached mode
docker run -p <host:container> <image> # Run container with port mapping
docker run -v <host:container> <image> # Run container with a volume mounted
docker start <container>               # Start a stopped container
docker stop <container>                # Stop a running container
docker restart <container>             # Restart a container
docker rm <container>                  # Remove a container
docker system df                       # Show Docker disk usage
```

## Container interaction

```bash
docker logs <container>                  # Fetch the logs of a container
docker logs -f <container>               # Follow log output of a container
docker exec -it <container> <command>    # Execute a command in a running container
docker exec -it <container> bash         # Get a bash shell in a running container
docker attach <container>                # Attach to a running container
docker cp <container>:<src> <dest>       # Copy files from container to host
docker cp <src> <container>:<dest>       # Copy files from host to container
docker inspect <container>               # Display detailed info about a container
docker stats                             # Live stream of container resource usage
docker top <container>                   # Display the running processes of a container
```

Use `docker exec` for normal investigation; `docker attach` connects to PID 1 and can accidentally signal it. Minimal images may only have `/bin/sh`, not `bash`.

## Networks

```bash
docker network ls                                # List all networks
docker network create <name>                     # Create a network
docker network rm <name>                         # Remove a network
docker network inspect <name>                    # Display detailed information about a network
docker network connect <network> <container>     # Connect a container to a network
docker network disconnect <network> <container>  # Disconnect a container from a network
```

On a user-defined network, containers reach each other by service/container name (e.g. `mysql:<port>`), not a fixed container IP.

## Volumes

```bash
docker volume ls               # List all volumes
docker volume create <name>    # Create a volume
docker volume rm <name>        # Remove a volume
docker volume inspect <name>   # Display detailed information about a volume
docker volume prune            # Remove all unused volumes
docker run -d -v <name>:/data <image>   # Mount a named volume at /data in the container
```

`-v myvolume:/data` mounts a **named volume** managed by Docker (kept under `/var/lib/docker/volumes`); `-v /host/path:/data` is a **bind mount** of a host directory. Data in a volume survives `docker rm` of the container.

## Compose

```bash
docker-compose up          # Create and start containers defined in docker-compose.yml
docker-compose up -d       # Create and start in detached mode
docker-compose down        # Stop and remove containers, networks, images, and volumes
docker-compose ps          # List containers in the Compose project
docker-compose logs        # View output from containers
docker-compose build       # Build or rebuild services
```

Do not place database passwords directly in Compose YAML; use an approved secret mechanism and protect `.env` files from Git. (Docker Compose v2 uses `docker compose` with a space; v1 uses `docker-compose`.)

## Practice run: nginx end to end

Run these in order to practise the everyday commands on one container.

```bash
docker --version && docker info                    # 1. Check Docker is installed and the engine is running

docker pull nginx                                  # 2. Pull the image
docker images                                      #    Confirm it is listed

docker network create app-network                  # 3. Create a user-defined network
docker volume create myvolume                      #    and a named volume

docker run -d --name web -p 8080:80 \
  --network app-network -v myvolume:/data nginx    # 4. Run detached, host port 8080 -> container port 80
docker ps                                          #    Running containers
curl http://localhost:8080                         #    Should return the nginx welcome page

docker logs web                                    # 5. Logs and monitoring
docker stats --no-stream web                       #    One snapshot of CPU and memory
docker top web                                     #    Processes inside the container

docker exec -it web bash                           # 6. Shell inside the container (type exit to leave)

docker network inspect app-network                 # 7. Container is attached to the network
docker volume inspect myvolume                     #    Where the volume lives on the host

docker stop web && docker ps -a                    # 8. Stopped containers appear only with -a
docker start web && docker restart web             #    Start again, then restart

docker rm -f web                                   # 9. Clean up: container,
docker volume rm myvolume                          #    volume,
docker network rm app-network                      #    network,
docker rmi nginx                                   #    and image
```

To practise `docker build -t myapp .`, create a folder with this `Dockerfile` and an `index.html`, then build and run it:

```dockerfile
FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
```

```bash
docker build -t myapp .
docker run -d --name myapp -p 8081:80 myapp
curl http://localhost:8081
```
