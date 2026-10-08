# Docker local development and deployment

Requires Docker Engine with Docker Compose v2 (Docker Desktop with Linux
containers on Windows). Run commands from the crm-backend directory.

## Local development

```powershell
Copy-Item .env.example .env
# Replace JWT_SECRET in .env.
docker compose up --build -d
docker compose logs -f api
```

Open http://localhost:8000/docs. PostgreSQL is available on localhost:5432.
Compose waits for healthy PostgreSQL, runs `alembic upgrade head`, and starts
the API only after migrations succeed. Application source is mounted read-only
and Uvicorn reloads changes. Container DATABASE_URL uses the `db` service host,
overriding the localhost URL used when running Python directly.

```powershell
# Generate a migration on the host so the migration file persists there.
# Use the host virtual environment and DATABASE_URL=...@localhost:5432/crm.
alembic revision --autogenerate -m "describe schema change"
# Review it, then apply using the async container connection.
docker compose run --rm migrate
# Rebuild after dependency changes.
docker compose up --build -d
# Stop services while retaining database data.
docker compose down
```

## Deployment on one Docker host

```powershell
Copy-Item .env.production.example .env.production
# Replace JWT_SECRET and POSTGRES_PASSWORD, and update DATABASE_URL to match.
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml up --build -d
docker compose --env-file .env.production -f compose.production.yaml ps -a
docker compose --env-file .env.production -f compose.production.yaml logs api migrate
```

Production runs two API workers with no source mounts or reload. The image uses
a non-root user, the application filesystem is read-only, logs rotate, and the
database persists in a named volume. PostgreSQL has no published port. The API
binds to host loopback by default; point your host HTTPS reverse proxy to
127.0.0.1:8000. Configure API_BIND_ADDRESS only when your network setup requires
a different host interface. A reverse proxy is not included.

The migration service runs once before the API starts, rather than once per
worker. For subsequent deployments, back up the database, stop the old API,
and explicitly recreate the migration container before starting the new API:

```powershell
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml stop api
docker compose --env-file .env.production -f compose.production.yaml up --force-recreate --no-deps migrate
# Proceed only if migrate exits with code 0.
docker compose --env-file .env.production -f compose.production.yaml up -d --no-deps --force-recreate api
```

This procedure has deployment downtime. On migration failure, investigate
before restarting the API. Review destructive migrations and take a backup
before applying them. Changing POSTGRES_PASSWORD in the environment does not
rotate a password in an already initialized PostgreSQL volume.

For a registry-based deployment, build and push a versioned CRM_IMAGE in CI,
then use `docker compose ... pull api migrate` and omit the build command on
the host. Alembic revisions must be included in the same image as the API.

Health endpoints: `/health` checks the process; `/ready` checks PostgreSQL.
Docker uses `/ready` for container health. Docker restart policies restart an
exited process; an unhealthy status alone does not trigger a restart.

`docker compose down` retains data. Adding `--volumes` deletes the database.
Keep .env and .env.production out of version control and container build context.

## Verification

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
Invoke-RestMethod http://localhost:8000/ready
docker compose run --rm migrate alembic current
```

Docker build and runtime verification could not be executed in the authoring
environment because terminal initialization failed.
