# Clerk Integration Guide

This guide explains how to set up the integration between Clerk authentication and the CampusG user service.

## Overview

The integration connects Clerk's authentication service with our backend user database through:

1. A webhook that syncs user data from Clerk to our database
2. API endpoints to fetch user data by Clerk ID
3. Frontend utilities to combine Clerk auth with our backend data

## Database Migration

After adding the `clerk_user_id` field to the User model, you need to apply a database migration:

```bash
# Create a migration script (if using Alembic)
alembic revision --autogenerate -m "add_clerk_user_id_to_users"

# Apply the migration
alembic upgrade head
```

Or if you're using raw SQL:

```sql
ALTER TABLE users ADD COLUMN clerk_user_id VARCHAR(255);
CREATE UNIQUE INDEX ix_users_clerk_user_id ON users(clerk_user_id);
```

## Running the Required Services

You can start just the services needed for Clerk integration using the provided docker-compose file:

```bash
# Start the required services (database and user service)
docker-compose -f docker-compose.clerk-test.yml up --build
```

This will start:
- PostgreSQL database for the user service
- User service with the Clerk webhook endpoint

### Database Initialization

Before using the service, you need to initialize the database:

```bash
# Initialize the database (create tables)
docker-compose -f docker-compose.clerk-test.yml exec user-service python init_db.py

# Apply the migration to add the clerk_user_id column
docker-compose -f docker-compose.clerk-test.yml exec user-service python migration_add_clerk_user_id.py
```

### Running the Frontend

Start the frontend development server locally:

```bash
cd frontend
npm install  # If needed
npm run dev
```

## Setting Up Ngrok

To make your webhook accessible from the internet during development:

1. If you're not using Docker, start your user service directly:
   ```bash
   cd services/user-service
   python run.py
   ```

   If using Docker, your service is already running from the previous step.

2. In a new terminal, start Ngrok to create a tunnel to your service:
   ```bash
   # Assuming the user service runs on port 5000
   ngrok http 5000
   ```

3. Ngrok will display a URL like `https://a1b2c3d4.ngrok.io`. Copy this URL as you'll need it to configure the Clerk webhook.

## Configuring Clerk Webhooks

1. Go to the [Clerk Dashboard](https://dashboard.clerk.dev/)
2. Navigate to your application
3. In the sidebar, click on "Webhooks"
4. Click "Add Endpoint"
5. Configure the webhook:
   - URL: `https://your-ngrok-url.ngrok.io/api/webhook/clerk`
   - Select events:
     - `user.created`
     - `user.updated`
     - `user.deleted`
   - Set a secret (optional but recommended for production)
6. Click "Create"

## Testing the Integration

1. Create a new user in Clerk (by signing up in your application)
2. Check your user service logs to confirm the webhook was received
3. Verify the user was created in your database:
   ```sql
   SELECT * FROM users WHERE clerk_user_id IS NOT NULL;
   ```

## Using the Frontend Integration

The frontend integration provides a `useBackendUser` hook that combines Clerk authentication with your backend user data:

```tsx
import { useBackendUser } from '@/lib/useBackendUser';

function ProfileComponent() {
  const { backendUser, clerkUser, loading, error } = useBackendUser();
  
  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error}</p>;
  if (!backendUser) return <p>User not found</p>;
  
  return (
    <div>
      <h1>Welcome, {backendUser.firstName} {backendUser.lastName}</h1>
      <p>Email: {backendUser.email}</p>
      <p>Customer Rating: {backendUser.customerRating}</p>
      <p>Runner Rating: {backendUser.runnerRating}</p>
    </div>
  );
}
```

## Future Enhancements

1. **JWT Verification**: Implement JWT verification in the backend to validate user requests
2. **Webhook Signature Verification**: Add verification of webhook signatures for security
3. **Kafka Integration**: Move webhook processing to Kafka for better reliability and scalability
