#!/bin/bash
# Minikube setup script for CampusG

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    echo "Minikube is not installed. Please install it first."
    echo "Visit https://minikube.sigs.k8s.io/docs/start/ for installation instructions."
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install it first."
    echo "Visit https://kubernetes.io/docs/tasks/tools/ for installation instructions."
    exit 1
fi

# Start minikube with sufficient resources
echo "Starting minikube with 4 CPUs and 8GB of memory..."
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable necessary addons
echo "Enabling ingress addon..."
minikube addons enable ingress

# Create the campusg namespace
echo "Creating campusg namespace..."
kubectl apply -f ../infrastructure/namespace.yaml

# Deploy infrastructure components
echo "Deploying PostgreSQL..."
kubectl apply -f ../infrastructure/postgres/

echo "Deploying Kafka and Zookeeper..."
kubectl apply -f ../infrastructure/kafka/

# Wait for infrastructure to be ready
echo "Waiting for infrastructure to be ready..."
echo "This may take a few minutes..."

kubectl wait --namespace campusg \
  --for=condition=ready pod \
  --selector=app=postgres \
  --timeout=300s

kubectl wait --namespace campusg \
  --for=condition=ready pod \
  --selector=app=kafka \
  --timeout=300s

# Deploy services
echo "Deploying microservices..."
kubectl apply -f ../services/

# Deploy frontend
echo "Deploying frontend..."
kubectl apply -f ../frontend/

# Add entry to hosts file for local development
echo "127.0.0.1 campusg.local" | sudo tee -a /etc/hosts

# Setup port forwarding for ingress
echo "Setting up port forwarding..."
minikube tunnel &

# Get the URLs for services
echo "CampusG has been deployed to Minikube!"
echo ""
echo "To access the application, use the following URL:"
echo "http://campusg.local"
echo ""
echo "Or you can use port forwarding for direct access:"
echo "kubectl port-forward -n campusg svc/frontend 3000:3000"
echo ""
echo "You can view the status of your pods with:"
echo "kubectl get pods -n campusg"
echo ""
echo "To view the dashboard, run:"
echo "minikube dashboard"
