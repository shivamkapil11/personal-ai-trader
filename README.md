# Personal AI Trader

Local-first stock research and decision-support workspace for single-stock analysis, side-by-side comparison, and optional portfolio-aware insights.

## What This Product Does

`Personal AI Trader` helps a user:

- analyze one stock or compare up to three stocks
- classify names as swing-trade, long-term, watchlist, or avoid-for-now
- see provider/source visibility for quotes and market context
- turn rough notes into a structured analysis brief
- optionally connect Kite for live portfolio-aware insights
- keep watchlist items, search history, and feedback in a local-first workflow

The app is designed so stock analysis works even when portfolio connectivity is not enabled.

## Core Capabilities

- auth-first flow with Google sign-in and local dev fallback
- onboarding split for Kite and non-Kite users
- provider chain: `Kite MCP -> jugaad-data -> Yahoo Finance`
- technical, fundamental, risk, and return scoring
- source-tagged reasoning using a knowledge registry
- optional TradingView Desktop snapshot support
- portfolio insight flow for holdings, positions, and concentration analysis

## Recommended Reading Order

- [Documentation Index](docs/README.md)
- [Architecture](docs/project/architecture.md)
- [Deployment Guide](docs/operations/deployment.md)
- [GoDaddy Domain Setup](docs/operations/domain-setup-godaddy.md)
- [Roadmap](docs/project/roadmap.md)
- [GitHub Desktop Guide](docs/project/github-desktop-guide.md)

## Repository Structure

```text
personal-ai-trader/
├── api/                          # Vercel entrypoint
├── app/
│   ├── main.py                   # FastAPI app and routes
│   ├── config.py                 # Environment-driven settings
│   ├── models.py                 # Request/session models
│   ├── jobs.py                   # In-memory job/event manager
│   ├── services/                 # Market data, auth, Kite, portfolio, knowledge
│   ├── static/                   # Frontend JS and CSS
│   └── templates/                # Jinja templates
├── data/                         # Local JSON-backed registry/state assets
├── docs/                         # Product, architecture, ops, roadmap, repo docs
├── infrastructure/
│   └── postgres/migrations/      # SQL scaffolding for future persistent storage
├── requirements.txt
├── run_local.sh
└── vercel.json
```

## Quick Start

```bash
git clone <your-private-repo-url>
cd personal-ai-trader
cp .env.example .env
SKIP_PIP_INSTALL=1 ./run_local.sh
```

Open [http://127.0.0.1:8008](http://127.0.0.1:8008).

Notes:

- Use `SKIP_PIP_INSTALL=1` when the virtual environment is already prepared.
- Set `APP_RELOAD=1` if you want `uvicorn --reload` locally.
- The current launcher defaults to non-reload mode for better stability.
- `.python-version` pins deploy/runtime targets to Python `3.12`.

## Environment Variables

The complete environment reference lives in [.env.example](.env.example) and is explained in [Deployment Guide](docs/operations/deployment.md).

Key groups:

- app/session: `APP_*`
- market data/provider order: `MARKET_DATA_PROVIDER_ORDER`
- Kite: `KITE_MCP_*`
- Firebase/Auth: `FIREBASE_*`, `AUTH_ALLOW_DEV_FALLBACK`
- Firestore feedback: `FEEDBACK_FIRESTORE_*`
- TradingView: `TRADINGVIEW_*`
- Postgres readiness: `POSTGRES_*`

## Current Integration Status

- `Kite MCP`: hosted session bridge is wired into FastAPI and preserves Zerodha login/consent flow
- `Firebase Auth`: prepared, defaults to local dev fallback when credentials are absent
- `Firebase Admin`: supports either `FIREBASE_ADMIN_CREDENTIALS_PATH` locally or `FIREBASE_ADMIN_CREDENTIALS_JSON` for hosted deploys
- `Firestore`: prepared for feedback storage, not enabled by default
- `PostgreSQL`: runtime store supports Postgres when `POSTGRES_ENABLED=true` and `POSTGRES_DSN` is set
- `TradingView Desktop`: supported through the local desktop bridge when available

## Technical Direction

- current stack: FastAPI + Jinja + vanilla JS/CSS
- recommended deploy target for the current monolith: Vercel
- future scaling path: move persistent state to Postgres/Firestore and move job execution into background workers

## Private Repository Guidance

This repository is prepared to stay private while still being clean enough for future teammates and contractors:

- absolute personal filesystem paths have been removed from repo-facing docs and metadata
- docs are structured for onboarding, operations, and roadmap review
- deployment guidance assumes future collaborators need to stand the project up without prior context

## Known Limitations

- local JSON remains the fallback when Postgres is not configured
- Firebase production auth is not configured by default
- Firestore feedback storage is not configured by default
- Vercel deployment is only appropriate once persistence is externalized
- background jobs are in-memory and do not survive process restarts

## License / Internal Use

Add your preferred private-company or internal-use license before wider collaboration. The repository currently assumes internal/private use.
