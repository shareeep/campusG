#!/bin/bash
# Script to build and push Docker images for CampusG services

# Configuration
DOCKER_REGISTRY=${DOCKER_REGISTRY:-localhost}
TAG=${TAG:-latest}
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Ensure Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running or not accessible. Please start Docker."
  exit 1
fi

# Build and push each service image
build_and_push() {
  local service=$1
  local context=$2
  
  echo "Building $service image..."
  docker build -t $DOCKER_REGISTRY/campusg/$service:$TAG $context
  
  if [ "$DOCKER_REGISTRY" != "localhost" ]; then
    echo "Pushing $service image to registry..."
    docker push $DOCKER_REGISTRY/campusg/$service:$TAG
  fi
}

# Build all services
echo "Building CampusG Docker images..."

# Frontend
build_and_push "frontend" "$PROJECT_ROOT/frontend"

# Order Service
build_and_push "order-service" "$PROJECT_ROOT/services/order_service"

# User Service
build_and_push "user-service" "$PROJECT_ROOT/services/user-service"

# Payment Service
build_and_push "payment-service" "$PROJECT_ROOT/services/payment-service"

# Escrow Service
build_and_push "escrow-service" "$PROJECT_ROOT/services/escrow-service"

# Scheduler Service
build_and_push "scheduler-service" "$PROJECT_ROOT/services/scheduler-service"

# Notification Service
build_and_push "notification-service" "$PROJECT_ROOT/services/notification-service"

echo "All images have been built successfully!"
echo ""
echo "To deploy to Kubernetes, run the minikube-setup.sh script:"
echo "cd kubernetes/setup && ./minikube-setup.sh"
