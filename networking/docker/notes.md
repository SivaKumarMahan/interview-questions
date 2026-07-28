# Docker Networking Notes

## Q: What is the difference between `EXPOSE` in a Dockerfile and `-p` in `docker run`?

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

---

## Q: How do you run NGINX on a Linux server using Docker?

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

---
