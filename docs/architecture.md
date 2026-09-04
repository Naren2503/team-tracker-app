# Architecture

## Modules

- `auth`: login/logout and session cookie creation
- `users/admin`: admin-only user and role management
- `tracker-records`: secured CRUD for master records
- `work-logs`: imported daily activity data
- `imports`: preview, validation, import modes, history, error CSV
- `dashboard`: aggregate metrics and filters
- `audit`: immutable admin audit log
- `exports`: filtered dataset export foundation

## Permission Enforcement

UI links are hidden for unauthorized users, but security is enforced in backend dependencies and route handlers. Mutating endpoints check explicit permissions. Record updates also check ownership unless the actor has `edit_all_records`.

## Concurrency

`tracker_records.version` and `work_logs.version` support optimistic concurrency. Update requests can include the current version; stale updates return HTTP 409.

## Production Upgrade Path

Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL, run migrations in a controlled pipeline, and use Microsoft Entra ID for authentication while keeping local role mappings in the app database.
