# Kubernetes Guide for CampusG

This guide explains how to use Kubernetes with the CampusG project, covering both fundamentals and implementation details.

## Table of Contents
- [What is Kubernetes?](#what-is-kubernetes)
- [Docker vs. Kubernetes](#docker-vs-kubernetes)
- [Kubernetes Core Concepts](#kubernetes-core-concepts)
- [Setting Up a Local Kubernetes Environment](#setting-up-a-local-kubernetes-environment)
- [Deploying CampusG to Kubernetes](#deploying-campusg-to-kubernetes)
- [Kubectl Commands Cheat Sheet](#kubectl-commands-cheat-sheet)
- [Troubleshooting](#troubleshooting)

## What is Kubernetes?

Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. It was originally developed by Google and is now maintained by the Cloud Native Computing Foundation (CNCF).

### Key Benefits

- **Auto-scaling**: Automatically scales applications based on resource usage or custom metrics
- **Self-healing**: Automatically replaces failed containers and reschedules them on healthy nodes
- **Service discovery**: Provides built-in DNS for service discovery and internal communication
- **Load balancing**: Distributes network traffic to ensure stability and reliability
- **Storage orchestration**: Integrates with various storage systems (cloud, on-prem)
- **Automated rollouts and rollbacks**: Controls application deployment and updates
- **Secret and configuration management**: Manages sensitive information and application configuration

## Docker vs. Kubernetes

| Feature | Docker & Docker Compose | Kubernetes |
|---------|-------------------------|------------|
| **Purpose** | Container runtime & simple orchestration | Full container orchestration platform |
| **Scale** | Suitable for single-host deployments | Designed for multi-host, production-grade deployments |
| **Configuration** | `docker-compose.yml` with simple syntax | Multiple YAML manifests with more complex schema |
| **Auto-healing** | Limited; requires manual intervention | Automatic pod restarts, rescheduling, etc. |
| **Load Balancing** | Basic load balancing | Advanced ingress controllers, service mesh integration |
| **Scaling** | Manual scaling with `docker-compose up --scale` | Automatic horizontal scaling based on metrics |
| **Updates** | Simple but with service disruption | Rolling updates with zero downtime |
| **Service Discovery** | Simple DNS-based discovery | Built-in service discovery, DNS, environment variables |
| **Learning Curve** | Low to moderate | Steep |

**When to use Docker Compose**:
- Local development environments
- Simple applications with few services
- Projects with limited scaling needs
- Small teams with limited DevOps resources

**When to use Kubernetes**:
- Production environments
- Large-scale applications
- Applications requiring high availability
- Systems with complex networking requirements
- Projects needing auto-scaling and self-healing

## Kubernetes Core Concepts

### Pod

The smallest deployable unit in Kubernetes, a Pod represents a single instance of a running process in a cluster. It encapsulates one or more containers, shared storage, network resources, and instructions for how to run the containers.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
spec:
  containers:
  - name: container-name
    image: image-name
    ports:
    - containerPort: 8080
```

### Deployment

Manages the deployment and scaling of a set of Pods and provides declarative updates to applications.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-deployment
spec:
  replicas: 3  # Run 3 instances of this pod
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
    spec:
      containers:
      - name: example-container
        image: example-image
        ports:
        - containerPort: 8080
```

### Service

An abstract way to expose an application running on a set of Pods as a network service. Kubernetes services provide stable network endpoints to access pods.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: example-service
spec:
  selector:
    app: example
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP  # Could also be NodePort or LoadBalancer
```

### ConfigMap

Stores non-confidential configuration data in key-value pairs, which can be consumed by pods or used to populate environment variables.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: example-config
data:
  database_url: "postgresql://postgres:postgres@postgres:5432/db"
  api_host: "https://api.example.com"
```

### Secret

Similar to ConfigMaps but designed for sensitive data like passwords, tokens, or keys.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: example-secret
type: Opaque
data:
  username: YWRtaW4=  # Base64 encoded "admin"
  password: cGFzc3dvcmQ=  # Base64 encoded "password"
```

### StatefulSet

Manages the deployment and scaling of a set of Pods with unique, persistent identities. Useful for stateful applications like databases.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: "postgres"
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 1Gi
```

### Namespace

Virtual clusters within a physical cluster. Useful for separating resources in a shared Kubernetes cluster.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: campusg
```

### Ingress

Manages external access to services within a cluster, typically HTTP. Ingress can provide load balancing, SSL termination, and name-based virtual hosting.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
spec:
  rules:
  - host: campusg.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

## Setting Up a Local Kubernetes Environment

### Option 1: Minikube (Recommended for Beginners)

Minikube is a tool that runs a single-node Kubernetes cluster on your personal computer.

**Prerequisites**:
- Docker or a hypervisor like VirtualBox
- kubectl command-line tool

**Installation**:

1. Install Minikube from [the official website](https://minikube.sigs.k8s.io/docs/start/)
2. Start Minikube:
```sh
minikube start
```
3. Verify installation:
```sh
kubectl get nodes
```

### Option 2: Docker Desktop Kubernetes

If you already have Docker Desktop, you can enable Kubernetes in its settings.

1. Open Docker Desktop
2. Go to Settings/Preferences
3. Select "Kubernetes" in the left sidebar
4. Check "Enable Kubernetes"
5. Click "Apply & Restart"

### Option 3: kind (Kubernetes IN Docker)

kind creates Kubernetes clusters using Docker containers as nodes.

```sh
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.11.1/kind-linux-amd64
chmod +x ./kind
mv ./kind /usr/local/bin/kind

# Create a cluster
kind create cluster --name campusg
```

## Deploying CampusG to Kubernetes

### Step 1: Create CampusG Namespace

```sh
kubectl apply -f kubernetes/infrastructure/namespace.yaml
```

### Step 2: Deploy Infrastructure (Postgres and Kafka)

```sh
# Deploy PostgreSQL
kubectl apply -f kubernetes/infrastructure/postgres/

# Deploy Kafka
kubectl apply -f kubernetes/infrastructure/kafka/
```

### Step 3: Deploy Microservices

```sh
# Deploy all services
kubectl apply -f kubernetes/services/

# Or deploy services individually
kubectl apply -f kubernetes/services/user-service/
kubectl apply -f kubernetes/services/order-service/
# ... and so on
```

### Step 4: Deploy Frontend

```sh
kubectl apply -f kubernetes/frontend/
```

### Step 5: Access the Application

For Minikube:
```sh
# Get the URL to access frontend
minikube service frontend -n campusg
```

For other setups:
```sh
kubectl port-forward svc/frontend 3000:3000 -n campusg
```

## Kubectl Commands Cheat Sheet

### General Commands
```sh
# Get cluster info
kubectl cluster-info

# View all resources in a namespace
kubectl get all -n campusg

# Get node status
kubectl get nodes
```

### Pod Management
```sh
# List all pods
kubectl get pods -n campusg

# Get detailed info about a pod
kubectl describe pod <pod-name> -n campusg

# Get pod logs
kubectl logs <pod-name> -n campusg

# Execute a command in a pod
kubectl exec -it <pod-name> -n campusg -- /bin/bash
```

### Deployment Management
```sh
# Scale a deployment
kubectl scale deployment <deployment-name> --replicas=3 -n campusg

# Rollout status
kubectl rollout status deployment/<deployment-name> -n campusg

# Rollback to previous version
kubectl rollout undo deployment/<deployment-name> -n campusg
```

### Service Management
```sh
# List services
kubectl get services -n campusg

# Get endpoints (to see where a service is connected)
kubectl get endpoints <service-name> -n campusg
```

### Config and Secrets
```sh
# Get ConfigMaps
kubectl get configmaps -n campusg

# Get Secrets
kubectl get secrets -n campusg
```

### Networking
```sh
# Port forwarding to access a service locally
kubectl port-forward svc/<service-name> <local-port>:<service-port> -n campusg

# Get ingress info
kubectl get ingress -n campusg
```

## Troubleshooting

### Common Issues and Solutions

#### Pods in "Pending" State
```sh
kubectl describe pod <pod-name> -n campusg
```
Common causes: Insufficient resources, PersistentVolumeClaim not bound

#### Pods in "CrashLoopBackOff" State
```sh
kubectl logs <pod-name> -n campusg
```
Common causes: Application errors, incorrect configuration, resource limits

#### Service Cannot Be Accessed
```sh
kubectl get endpoints <service-name> -n campusg
```
Common causes: Label selector mismatch, pods not running

#### PersistentVolume Issues
```sh
kubectl get pv
kubectl get pvc -n campusg
```
Common causes: Storage class not available, incorrect access modes

### Getting Additional Help

If you encounter issues not covered here:
1. Check the Kubernetes documentation: https://kubernetes.io/docs/
2. Search the Kubernetes GitHub issues: https://github.com/kubernetes/kubernetes/issues
3. Visit Stack Overflow with the kubernetes tag: https://stackoverflow.com/questions/tagged/kubernetes
