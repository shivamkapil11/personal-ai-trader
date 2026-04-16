# Deployment Guide

## Deployment Strategy

Use a free-first approach and only introduce more infrastructure when the product needs it.

### Recommended current deploy target

- `Vercel`

Why:

- easiest match for the current FastAPI monolith
- simple GitHub integration
- free tier is enough for early demos and internal use
- quick custom-domain and SSL setup

### Secondary options

- `Netlify`
  - good if the frontend is split from the backend later
  - less ideal for the current monolithic FastAPI shape
- `Firebase Hosting`
  - best for frontend hosting after a future frontend/backend split
  - not the best direct fit for the current Python monolith

## Current Production Readiness Caveat

The repo can be deployed, but production-safe persistence is not fully complete yet.

Current blockers:

- runtime state still defaults to local JSON unless Postgres is configured
- Firebase production auth / Firestore are not configured by default
- background jobs are in-memory

Recommended production order:

1. externalize persistence
2. externalize feedback storage
3. finish production auth
4. move long-running jobs into a background runner

## Vercel Setup

This repo now includes:

- `api/index.py`
- `vercel.json`

These files prepare the project for Vercel to treat the FastAPI app as the server entrypoint.

## Environment Variables

Use the `.env.example` file as the source of truth.

### Minimum demo deployment

```bash
APP_TITLE=Personal AI Trader
APP_SECRET=<long-random-secret>
MARKET_DATA_PROVIDER_ORDER=kite_mcp,jugaad_data,yfinance
AUTH_ALLOW_DEV_FALLBACK=true
TRADINGVIEW_ENABLED=false
TRADINGVIEW_DESKTOP_ENABLED=false
```

### Recommended internal deployment

```bash
APP_TITLE=Personal AI Trader
APP_SECRET=<long-random-secret>
MARKET_DATA_PROVIDER_ORDER=kite_mcp,jugaad_data,yfinance
KITE_MCP_ENABLED=true
KITE_MCP_URL=https://mcp.kite.trade/mcp
FIREBASE_ENABLED=true
FIREBASE_API_KEY=<firebase-client-key>
FIREBASE_AUTH_DOMAIN=<firebase-auth-domain>
FIREBASE_PROJECT_ID=<firebase-project-id>
FIREBASE_APP_ID=<firebase-app-id>
FIREBASE_ADMIN_CREDENTIALS_JSON=<service-account-json>
FEEDBACK_FIRESTORE_ENABLED=true
FEEDBACK_FIRESTORE_COLLECTION=feedback
POSTGRES_ENABLED=true
POSTGRES_DSN=<postgres-connection-string>
```

## Deploy Steps: Vercel

### Option A: Vercel Dashboard

1. Push the repo to GitHub.
2. In Vercel, choose `Add New Project`.
3. Import the private GitHub repository.
4. Set the root directory to the repo root.
5. Add environment variables from `.env.example`.
6. Deploy.

### Option B: Vercel CLI

```bash
npm i -g vercel
vercel login
vercel
vercel --prod
```

## Netlify Guidance

Netlify is better reserved for a future split architecture:

- frontend on Netlify
- backend on Vercel or another Python host

If you try to deploy the current monolith there, expect extra work around Python function routing and static asset handling.

## Firebase Hosting Guidance

Firebase Hosting is a strong future option if:

- the frontend becomes a standalone app
- backend moves to a separate Python API
- auth and feedback are already Firebase-native

For the current monolith, Firebase Hosting alone is not enough because it does not run the Python backend by itself.

## Production Config Notes

### Sessions

- always set a strong `APP_SECRET`
- keep `secure=True` on cookies once HTTPS-only production config is introduced

### Persistence

- disable local JSON state in shared environments
- migrate users, preferences, watchlist, and history to Postgres
- move feedback events to Firestore

### Background Work

- current job manager is in-memory
- long-term path should use a worker system and durable queue

### Static Assets

- current static files are served by FastAPI
- this is acceptable in the current stage
- a future scale-up can move static assets to CDN/edge hosting

## Troubleshooting

### App boots locally but not on Vercel

Check:

- `vercel.json` exists
- `api/index.py` imports the FastAPI app correctly
- environment variables are present in Vercel project settings

### Login works locally but not in deployed environment

Check:

- Firebase client keys
- Firebase auth domain allow-list
- Firebase admin credentials JSON or token verification path
- cookie settings if HTTPS-only handling changes later

### Portfolio insights never load

Check:

- Kite bridge URL is set
- bridge can reach the underlying Kite MCP login flow
- the user has actually connected Kite

### Data disappears between deploys

Expected if local JSON is still being used in production. Move state to Postgres/Firestore before treating deployment as durable.

## Known Limitations

- current deployment can be demo-ready before it is truly production-ready
- Vercel works best only after persistence is externalized
- Netlify and Firebase Hosting are better for a future split stack than the current monolith
