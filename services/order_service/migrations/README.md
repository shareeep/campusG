# Database Migrations

This directory contains database migrations for the Order Service.

## Creating a New Migration

To create a new migration:

```
flask db migrate -m "Migration description"
```

This will generate a new migration script in the `versions` directory based on the changes detected in your models.

## Applying Migrations

To apply migrations to the database:

```
flask db upgrade
```

This will apply all pending migrations to the database.

## Reverting Migrations

To revert the last migration:

```
flask db downgrade
```

## Migration Commands

- `flask db init`: Initialize migration repository (already done)
- `flask db migrate`: Generate a migration
- `flask db upgrade`: Apply migrations to the database
- `flask db downgrade`: Revert migrations
- `flask db current`: Show current migration
- `flask db history`: Show migration history
- `flask db show`: Show specific migration
