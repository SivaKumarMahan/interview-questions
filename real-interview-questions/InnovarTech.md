# Innovar Tech - Interview Questions

## Q1. Which application have you used in frontend and backend? How is frontend connected to backend? Write the Dockerfile you used in the project.

For an Azure DevOps Engineer interview, explain it as a real 3-tier application: React.js frontend + Java Spring Boot backend + database, then explain how you containerized it and deployed it to AKS.

### 1. What applications have you used?

You can answer:

> "In one of my projects, we had a React.js frontend and Java Spring Boot microservices as the backend. The frontend was responsible for the user interface, while the backend exposed REST APIs for business operations. We used a database such as PostgreSQL or Azure SQL depending on the service. The applications were containerized using Docker and deployed to AKS. Azure DevOps was used for CI/CD, ACR for storing Docker images, Helm for Kubernetes deployments, and Azure Monitor / Application Insights for monitoring."

**Architecture:**

```
                    Users
                      |
                      v
               Azure Application Gateway
                      |
                   Ingress
                      |
          +-----------+-----------+
          |                       |
          v                       v
   React Frontend          Spring Boot APIs
   Nginx Container         Backend Containers
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
                Database                  Other APIs
```

### 2. How does the React frontend connect to the backend?

The important point is:

**React does not directly connect to the database.**

React calls backend REST APIs over HTTP / HTTPS.

For example, React might call:

```
GET https://myapp.com/api/users
```

The backend receives the request:

```
React
  |
  | HTTPS REST API
  v
Spring Boot
  |
  v
Database
```

For example, in React:

```javascript
const response = await fetch("/api/users");

const users = await response.json();
```

The backend exposes:

```java
@GetMapping("/api/users")
public List<User> getUsers() {
    return userService.getUsers();
}
```

The backend then talks to the database.

### 3. How do you connect frontend and backend in Kubernetes?

I would normally expose them through an Ingress.

For example:

```
https://myapp.com/
        |
        v
    Ingress
    /      \
   /        \
  v          v
React      Backend
           /api/*
```

Ingress rules can route:

```
myapp.com/       -> frontend-service
myapp.com/api/*  -> backend-service
```

This is useful because the React application can simply call:

```javascript
fetch("/api/users")
```

instead of hardcoding:

```javascript
fetch("http://backend-service:8080/api/users")
```

### 4. Dockerfile for React frontend

For React, I would use a multi-stage Docker build.

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build


# Runtime stage
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

The exact output directory depends on the React setup. For example, some setups generate `build/`, while Vite normally generates `dist/`.

For Vite:

```dockerfile
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 5. Why a multi-stage Dockerfile?

The first stage contains:

- Node.js
- npm
- source code
- dependencies
- build tools

These are not needed at runtime.

The final image contains only:

- Nginx
- React static files

So the production image is much smaller.

```
Stage 1
Node
  |
  +-- npm install
  +-- npm build
  |
  v
React build files
  |
  v
Stage 2
Nginx
  |
  +-- React files
  |
  v
Production container
```

### 6. Backend Dockerfile

If the backend is Java Spring Boot, a typical Dockerfile would be:

```dockerfile
# Build stage
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /app

COPY pom.xml .

RUN mvn dependency:go-offline

COPY src ./src

RUN mvn clean package -DskipTests


# Runtime stage
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

Again, the exact Java version depends on the project.

### 7. Azure DevOps CI/CD flow

This is where you should connect the answer to your DevOps role.

```
Developer
    |
    v
Azure Repos / Git
    |
    v
Azure DevOps Pipeline
    |
    +--> React npm install
    +--> React tests
    +--> React build
    +--> SonarQube
    |
    +--> Docker build
    +--> Docker image
    |
    v
Azure Container Registry
    |
    | myfrontend:BuildId
    | mybackend:BuildId
    |
    v
Helm Deployment
    |
    v
AKS
    |
    +--> Frontend Pod
    |
    +--> Backend Pods
             |
             v
          Database
```

### Interview answer

> "In my project, the frontend was developed using React.js and the backend consisted of Java Spring Boot REST APIs. The React application communicates with the backend through HTTPS REST API calls. The frontend doesn't directly access the database. The backend handles business logic and communicates with the database.
>
> We containerized both applications separately. For React, I used a multi-stage Dockerfile where Node.js was used to build the application and Nginx was used as the lightweight runtime server. For the Spring Boot backend, I used Maven to build the JAR in the first stage and a lightweight JRE image in the second stage.
>
> In Kubernetes, we deployed frontend and backend as separate deployments and services. Ingress routed normal application traffic to the frontend and `/api` requests to the backend. In Azure DevOps, the pipeline built and tested the applications, ran SonarQube analysis, built Docker images, pushed them to ACR, and deployed them to AKS using Helm."
