# Async CRM backend

For a fully containerized local setup and production deployment, see [DOCKER.md](DOCKER.md).

Python 3.12+, FastAPI, SQLAlchemy AsyncSession, asyncpg, PostgreSQL and Alembic.
Every database operation uses an async driver; no SQLite or synchronous engine.
Alembic uses the official async connection `run_sync` bridge for its synchronous
migration API; database I/O still runs through asyncpg. Password hashing runs in
a worker thread so CPU-intensive hashing does not block the event loop.

## Run locally (PowerShell)

```powershell
cd crm-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
Copy-Item .env.example .env
# Replace JWT_SECRET in .env with a random secret before starting.
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

Swagger documentation: http://localhost:8000/docs

Register using POST `/api/v1/auth/register` with email, name, password.
Login using POST `/api/v1/auth/login` with email and password. Use the returned
token in `Authorization: Bearer <token>`, or the Swagger Authorize button.

## API

- `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`
- `/api/v1/companies`, `/api/v1/contacts`, `/api/v1/deals`, `/api/v1/tasks`:
  GET list, POST create, GET /{id}, PUT /{id}, DELETE /{id}.
- Lists accept `limit` (1–100), `offset`, and `q` for literal text search.
- PUT replaces editable fields; optional omitted fields reset to defaults.
- `/api/v1/dashboard`: counts and deal pipeline grouped by currency and stage.
- `/health`: process liveness; `/ready`: database connectivity.

Records and related references are restricted to the authenticated owner.
Deleting a related company/contact/deal clears references using SET NULL.
Deleting records returns 204. Missing or inaccessible records return 404.
Timestamps use time zones, money uses decimals, task due dates require a timezone.
No schema is created during application startup: migrations are required.

## Migrations

```powershell
alembic revision --autogenerate -m "describe schema change"
# Review the generated migration.
alembic upgrade head
alembic current
alembic check
# Roll back the last revision (removes data for dropped tables).
alembic downgrade -1
```

Run migrations once as a deployment step before starting application workers.
The database credentials in compose.yaml are for local development. Supply
deployment secrets through environment variables and terminate HTTPS at your
reverse proxy. This starter has individual user ownership; shared teams,
password reset and login rate limiting are not implemented.

## Integration tests

Tests require a dedicated empty PostgreSQL database. They create users and CRM
records and clean up those users afterward. Never point tests at production.

```powershell
# Set DATABASE_URL to your dedicated asyncpg PostgreSQL test database in .env.
alembic upgrade head
pytest
```

Implementation was not executed in the authoring environment because the
terminal process failed to initialize. Run the commands above to verify locally.
