# Lab 3: Multi-Stage Dockerfile Optimization

> Build the same Go web service twice, with a single-stage and a multi-stage Dockerfile, and compare image size, contents, and security.

**Time:** about 20 minutes. **Level:** Basic to Intermediate.

## What you practise

- Why a build toolchain should not ship in a runtime image
- Multi-stage builds, layer caching, and static binaries
- Running as a non-root user on a distroless base image
- Using a Dockerfile-specific `.dockerignore`
- The concepts in [docker/03-image-optimization-multi-stage-and-bake.md](../../docker/03-image-optimization-multi-stage-and-bake.md)

## Prerequisites

Docker with BuildKit, which is the default builder in current Docker versions. Tested with Docker 29.1. Go does not need to be installed: it runs inside the build stage.

## Files

| File | Purpose |
| --- | --- |
| `app/main.go`, `app/go.mod` | A small HTTP service with `/` and `/healthz` |
| `app/README-notes.txt` | A file the app does not need, to show what gets copied |
| `Dockerfile.before` | Single stage on the full `golang` image, copies everything, runs as root |
| `Dockerfile.after` | Multi-stage: build a static binary, then copy it into `distroless/static:nonroot` |
| `Dockerfile.after.dockerignore` | Ignore rules used only by `Dockerfile.after` |

## Steps

### 1. Build the "before" image

```bash
docker build -f Dockerfile.before -t lab-app:before app/
```

### 2. Build the "after" image

```bash
docker build -f Dockerfile.after -t lab-app:after app/
```

### 3. Compare the two images

```bash
docker images lab-app
docker history lab-app:before | head -5
docker history lab-app:after
```

### 4. Compare what is inside

```bash
docker run --rm lab-app:before ls /src                    # source and stray files shipped
docker run --rm lab-app:before whoami                     # runs as root
docker inspect lab-app:after --format '{{.Config.User}}'  # nonroot:nonroot
docker run --rm --entrypoint /bin/sh lab-app:after        # fails: there is no shell
```

### 5. Check that the optimized image still works

```bash
docker run -d --rm --name lab-after -p 8080:8080 lab-app:after
curl -s localhost:8080/healthz
docker stop lab-after
```

### 6. Optional: see the build cache at work

Change the message in `app/main.go` and rebuild both images. With `Dockerfile.after`, the `go mod download` layer is reused, because `go.mod` is copied before the source code. With `Dockerfile.before`, every change invalidates the `COPY . .` layer and everything after it.

## Expected result

```text
$ docker images lab-app --format '{{.Tag}}\t{{.Size}}'
after     7.18MB
before    919MB

$ docker run --rm lab-app:before ls /src
README-notes.txt  go.mod  main.go

$ docker inspect lab-app:after --format '{{.Config.User}}'
nonroot:nonroot

$ curl -s localhost:8080/healthz
ok
```

- The optimized image is more than 100 times smaller: about 7 MB against about 900 MB.
- The "before" image contains the source code, the stray notes file, and the whole Go toolchain, and it runs as root.
- The "after" image contains only the binary, has no shell or package manager, and runs as `nonroot`.

Exact sizes depend on the base image versions you pull.

<details><summary>Why is the difference so big?</summary>

The `golang` image holds a full Debian system plus the Go compiler and standard library. The service only needs one compiled file. With `CGO_ENABLED=0` the binary is static, so it can run on `distroless/static`, which holds little more than CA certificates, time zone data, and a `nonroot` user. Less software in the image also means fewer packages for scanners to flag and a smaller attack surface.

</details>

## Clean up

```bash
docker rmi lab-app:before lab-app:after
```

## Interview takeaways

- Use multi-stage builds to keep compilers and build tools out of runtime images.
- Order `COPY` steps from least to most often changed, so the build cache helps you.
- Run as a non-root user, and prefer minimal bases such as distroless or alpine.
- Remember that a distroless image has no shell. Debug it with `kubectl debug` or a debug image variant.
- Related questions: [docker/02-dockerfiles-and-building-images.md](../../docker/02-dockerfiles-and-building-images.md) and [docker/05-security-ci-cd-and-deployments.md](../../docker/05-security-ci-cd-and-deployments.md).
