# Simple Fix for Mac Users

If you're on Mac and getting "permission denied" errors when running the notification service, follow these exact steps:

## Steps to Fix

1. Open Terminal

2. Go to the project directory:
   ```
   cd path/to/campusG
   ```

3. Run these commands exactly as shown:
   ```
   chmod +x services/notification-service/start.sh
   chmod +x services/notification-service/poll_worker.sh
   ```

4. Now rebuild and restart the container:
   ```
   docker-compose build notification-service
   docker-compose up -d notification-service
   ```

That's it! The service should now start correctly.

## If That Doesn't Work

Try this one-line fix:
```
docker-compose exec notification-service /bin/bash -c "chmod +x /app/start.sh /app/poll_worker.sh"
```

Then restart the container:
```
docker-compose restart notification-service
