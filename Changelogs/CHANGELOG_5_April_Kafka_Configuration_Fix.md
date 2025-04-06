# Kafka Configuration Fix - April 5, 2025

## Issue
When running tests from outside Docker containers, Kafka connectivity was failing with the error:
```
DNS lookup failed for kafka:9092 exception was [Errno 11001] getaddrinfo failed. Is your advertised.listeners (called advertised.host.name before Kafka 9) correct and resolvable?
```

This happened because Kafka was configured to advertise itself as `kafka:9092`, which is only resolvable from within the Docker network, not from the host machine.

## Changes Made

1. Updated the Kafka configuration in `docker-compose.yml` to support connections from both inside the Docker network and from the host machine:

```yaml
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,PLAINTEXT_HOST://0.0.0.0:29092
KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
```

2. Updated port mapping in `docker-compose.yml` to expose the external listener port:

```yaml
ports:
  - "9092:9092"
  - "29092:29092"
```

3. Updated `comprehensive_test.py` to use the correct external listener port:

```python
"kafka_servers": "localhost:29092", # Updated to use external listener port 29092
```

## Technical Explanation

- `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP`: Maps listener names to security protocols
- `KAFKA_ADVERTISED_LISTENERS`: Specifies the listeners that will be advertised to clients. Now includes:
  - `PLAINTEXT://kafka:9092` for services inside Docker network
  - `PLAINTEXT_HOST://localhost:9092` for external connections (like tests run from host)
- `KAFKA_LISTENERS`: Configures where Kafka will listen for connections
- `KAFKA_INTER_BROKER_LISTENER_NAME`: Specifies which listener to use for broker-to-broker communication

## Next Steps

To apply this change:

1. Stop any running Docker services:
   ```
   docker-compose down
   ```

2. Start Docker services with the updated configuration:
   ```
   docker-compose up -d
   ```

3. You should now be able to run the comprehensive test script directly from the host machine:
   ```
   cd services/create-order-saga-orchestrator && python comprehensive_test.py --docker
