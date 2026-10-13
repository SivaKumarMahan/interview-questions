# Hands-on 8: Multi-Stage Dockerfile for a React App Served by Nginx

> Build a React ToDo app with Node.js in one Docker stage, then serve only the static production files with Nginx in a small final image.

**Time:** about 45 minutes. **Level:** Basic.

## What you practise

- Creating a React app with Vite and building it for production
- Writing a `.dockerignore` to keep the build context small
- A multi-stage Dockerfile: Node.js to build, Nginx to serve
- Ordering Dockerfile instructions so the layer cache is reused
- An Nginx config for a single-page app (SPA): routing fallback, cache headers, and gzip
- Comparing image size and layers with `docker images` and `docker history`

## Prerequisites

| Tool | Purpose |
| --- | --- |
| Docker Desktop or Docker Engine | Build and run the image |
| Node.js 20 and npm (local) | Create the app and test it before containerising |
| A browser and `curl` | Check the running app and response headers |

Related lab: [labs/03-docker-multistage-optimization](../labs/03-docker-multistage-optimization/).

## Flow

```text
Source code (React + Vite)
     |
     v
Stage 1: node:20-alpine  (name: build)
     npm ci  -->  npm run build  -->  /app/dist
     |
     |  COPY --from=build /app/dist  (only the static files)
     v
Stage 2: nginx:1.27-alpine
     /usr/share/nginx/html + nginx.conf
     |
     v
docker run -p 8080:80  -->  http://localhost:8080
```

The final image contains Nginx and the built HTML, CSS, and JavaScript. It does not contain Node.js, `node_modules`, or the source code.

## Steps

### 1. Create the React app with Vite

```bash
npm create vite@latest todo-app -- --template react
cd todo-app
npm install
npm run dev
```

Open the URL that Vite prints (usually http://localhost:5173) to check that the app runs.

Vite writes the production build to the `dist` folder. Create React App (`create-react-app`) writes to `build` instead, and it is deprecated, so use Vite for new projects.

### 2. Replace the starter page with a small ToDo app

`src/App.jsx`:

```jsx
import { useState } from 'react';

export default function App() {
  const [items, setItems] = useState([]);
  const [text, setText] = useState('');

  function addItem(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setItems([...items, { id: Date.now(), text, done: false }]);
    setText('');
  }

  function toggle(id) {
    setItems(items.map((i) => (i.id === id ? { ...i, done: !i.done } : i)));
  }

  return (
    <main style={{ maxWidth: 480, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>ToDo</h1>
      <form onSubmit={addItem}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="New task" />
        <button type="submit">Add</button>
      </form>
      <ul>
        {items.map((i) => (
          <li key={i.id} onClick={() => toggle(i.id)}
              style={{ textDecoration: i.done ? 'line-through' : 'none', cursor: 'pointer' }}>
            {i.text}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

Build once locally to see the output:

```bash
npm run build
ls dist
# index.html  assets/  (plus files from public/)
```

### 3. Add a `.dockerignore`

`.dockerignore`:

```text
node_modules
dist
.git
Dockerfile*
*.md
```

Without this file, Docker sends `node_modules` and `.git` to the builder as the build context. That is slow, and a local `node_modules` built for your OS could end up inside the image.

### 4. Write the Nginx config

`nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;

    # Vite puts hashed file names in /assets, so they can be cached for a long time
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # index.html must always be checked again, so users get new releases
    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    # SPA routing: unknown paths return index.html and React handles the route
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- `try_files $uri $uri/ /index.html;` is the key line. Without it, refreshing a page such as `/tasks/5` returns 404, because no such file exists on disk.
- File names in `/assets` change on every build (for example `index-B4x9k2.js`), so a long cache is safe.
- `index.html` is not hashed, so it uses `no-cache`. The browser checks for a new version every time.

### 5. Write the multi-stage Dockerfile

`Dockerfile`:

```dockerfile
# ---------- Stage 1: build ----------
FROM node:20-alpine AS build
WORKDIR /app

# Copy only the dependency files first, so this layer is cached
COPY package*.json ./
RUN npm ci

# Now copy the source and build
COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine

# Replace the default server config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy only the build output from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# The nginx base image already starts nginx in the foreground
```

Why `package*.json` first: Docker caches each layer. If only source files change, the `npm ci` layer is reused and the build is much faster. If you copy everything first, any code change runs `npm ci` again.

`npm ci` installs exactly what is in `package-lock.json`, so builds are repeatable. Commit `package-lock.json` to Git.

### 6. Build and run

```bash
docker build -t todo-app:1.0 .
docker run -d --name todo -p 8080:80 todo-app:1.0
docker ps --filter name=todo
```

Open http://localhost:8080 in the browser.

### 7. Verify

```bash
# Home page
curl -I http://localhost:8080/
# Expected: HTTP/1.1 200 OK and Cache-Control: no-cache

# A client-side route (no file on disk)
curl -I http://localhost:8080/some/route
# Expected: 200 OK (index.html is returned), not 404

# A hashed asset (use a real file name from the dist/assets folder)
docker exec todo ls /usr/share/nginx/html/assets
curl -I -H "Accept-Encoding: gzip" http://localhost:8080/assets/<file>.js
# Expected: Cache-Control: public, max-age=31536000, immutable
# and Content-Encoding: gzip

# Nginx logs
docker logs todo
```

Expected: the ToDo page loads, you can add and tick tasks, and the headers match the comments above.

### 8. Compare with a single-stage image

Create `Dockerfile.single` to see the difference:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 4173
CMD ["npx", "vite", "preview", "--host", "0.0.0.0"]
```

```bash
docker build -f Dockerfile.single -t todo-app:single .
docker images todo-app
docker history todo-app:1.0
docker history todo-app:single
```

Expected: the single-stage image is several hundred MB, because it holds Node.js, `node_modules`, and the source. The multi-stage image is close to the size of `nginx:1.27-alpine` plus the small `dist` folder. `docker history` shows that the final image has no `npm ci` layer.

## Important points

- **Only the last stage is shipped.** Build tools, dev dependencies, and source code stay in the build stage and are not in the final image.
- **Build-time variables.** Vite replaces `import.meta.env.VITE_*` values at build time. They are baked into the JavaScript files, so you cannot change them with `docker run -e`. For per-environment config, either build one image per environment, or (better) serve a small `config.json` or `env.js` file that is written when the container starts (for example from a mounted ConfigMap), and have the app load it at runtime.
- **Never put secrets in `VITE_*` variables.** Everything in the bundle is visible to anyone who opens the site.
- **Run as non-root.** The standard `nginx` image starts as root and then runs worker processes as the `nginx` user. For a fully non-root container, use `nginxinc/nginx-unprivileged:1.27-alpine` as the final stage. It listens on port 8080, so change `listen 80;` to `listen 8080;`, use `EXPOSE 8080`, and run with `-p 8080:8080`.
- **Pin versions.** Use exact tags such as `node:20-alpine` and `nginx:1.27-alpine` (or digests), not `latest`, so builds are repeatable.
- **Scan the image.** Run a scanner such as Trivy or Docker Scout on the final image in CI.
- **Health check.** Kubernetes or the platform can probe `/` on the container port. You can also add a `HEALTHCHECK` instruction for plain Docker.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Blank page or 404 when refreshing a route like `/tasks/5` | Nginx looks for a file that does not exist | Add `try_files $uri $uri/ /index.html;` in `location /` |
| `COPY --from=build /app/build` fails: not found | Vite outputs `dist`, Create React App outputs `build` | Copy the folder that your build tool actually creates |
| Default "Welcome to nginx" page appears | The build output was copied to the wrong path, or the custom config was not copied | Copy to `/usr/share/nginx/html` and check with `docker exec todo ls /usr/share/nginx/html` |
| `npm ci` runs on every build | `COPY . .` comes before `npm ci` | Copy `package*.json`, run `npm ci`, then copy the source |
| "Sending build context" is slow or huge | No `.dockerignore`, so `node_modules` and `.git` are sent | Add the `.dockerignore` from step 3 |
| `npm ci` fails: lock file missing or out of sync | `package-lock.json` not committed or not updated | Run `npm install` locally and commit `package-lock.json` |
| Users see the old version after a release | `index.html` is cached by the browser or a CDN | Send `Cache-Control: no-cache` for `index.html` |
| App calls the wrong API URL in another environment | `VITE_*` value was baked in at build time | Use runtime config (a `config.json` loaded at start) or build per environment |

## Clean up

```bash
docker rm -f todo
docker rmi todo-app:1.0 todo-app:single
docker builder prune -f
```

## Interview questions

<details><summary>Q1. Why use a multi-stage build for a React app?</summary>

A React app needs Node.js and many npm packages to build, but at runtime it is only static files. With a multi-stage build, the first stage uses Node.js to run `npm ci` and `npm run build`. The second stage starts from a small Nginx image and copies only the `dist` folder. The final image is much smaller, starts fast, and has a smaller attack surface because there is no Node.js, no `node_modules`, and no source code in it.

</details>

<details><summary>Q2. Why do you copy <code>package.json</code> before the rest of the source?</summary>

Docker caches each layer and reuses it if the inputs have not changed. Dependencies change rarely, but source code changes all the time. By copying `package.json` and `package-lock.json` first and running `npm ci`, the dependency layer stays cached when only code changes. Only the `COPY . .` and `npm run build` layers run again, which makes builds much faster.

</details>

<details><summary>Q3. What is inside the final image?</summary>

Only the last stage: the `nginx:1.27-alpine` base, my `nginx.conf` in `/etc/nginx/conf.d/default.conf`, and the built files (`index.html` and the hashed files in `assets/`) in `/usr/share/nginx/html`. Everything from the build stage that I did not copy with `COPY --from=build` is discarded. I can confirm this with `docker history` and by listing the folder inside the container.

</details>

<details><summary>Q4. How do you handle different config for Dev, Test, and Prod?</summary>

Vite bakes `VITE_*` variables into the bundle at build time, so environment variables passed to `docker run` do not change them. One option is to build one image per environment, but that breaks "build once, deploy many". A better option is runtime config: the app fetches a small `config.json` (or loads an `env.js`) at start, and that file is provided per environment, for example from a Kubernetes ConfigMap or written by an entrypoint script. Secrets never go in the frontend at all.

</details>

<details><summary>Q5. How would you make this image smaller and more secure?</summary>

Use Alpine-based images and pin exact versions or digests. Keep a good `.dockerignore`. Use `nginxinc/nginx-unprivileged` so the container runs as non-root on port 8080, and run it with a read-only root filesystem where possible. Remove unused Nginx modules and server tokens if needed, add security headers, scan the image with Trivy or Docker Scout in CI, and rebuild regularly to pick up base image patches.

</details>
