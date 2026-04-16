# Local PostgreSQL Setup

Use this when PostgreSQL is already installed on the Mac and the app needs to move from local JSON to a real local database.

## What the app expects

- `POSTGRES_ENABLED=true`
- `POSTGRES_DSN=postgresql://<user>:<password>@localhost:5432/<database>`

The app will auto-apply the SQL migrations from `infrastructure/postgres/migrations/` on first use.

## Create a local database and user

Open a terminal and connect with your Postgres superuser account:

```bash
/Library/PostgreSQL/18/bin/psql -h localhost -U postgres -d postgres
```

Then run:

```sql
CREATE ROLE personal_ai_trader WITH LOGIN PASSWORD 'change-this-password';
CREATE DATABASE personal_ai_trader OWNER personal_ai_trader;
GRANT ALL PRIVILEGES ON DATABASE personal_ai_trader TO personal_ai_trader;
```

Exit with:

```sql
\q
```

## Add local environment variables

Create or update `.env` in the repo root:

```bash
APP_TITLE=Gains
APP_HOST=127.0.0.1
APP_PORT=8008
APP_SECRET=change-me
POSTGRES_ENABLED=true
POSTGRES_DSN=postgresql://personal_ai_trader:change-this-password@localhost:5432/personal_ai_trader
KITE_MCP_ENABLED=true
KITE_MCP_URL=https://mcp.kite.trade/mcp
AUTH_ALLOW_DEV_FALLBACK=true
```

## Restart and verify

```bash
cd /Users/shivamsworld/Documents/OpenAi/stock-dashboard
./run_local.sh
```

Then verify:

```bash
curl http://127.0.0.1:8008/health
```

Expected:

- `storage.mode` should switch to `postgres`
- `infrastructure.postgres.ready` should be `true`

## If the password is unknown

If the installer asked you for a password and you do not remember it, reset it from a superuser shell before continuing. The app cannot complete the DB connection without a valid Postgres username and password.
