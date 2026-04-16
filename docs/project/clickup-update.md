# ClickUp Update Package

Direct ClickUp task creation was not completed in this pass because:

- no target list was specified
- no matching existing task/doc was found through workspace search
- creating new tasks safely requires the destination list to be chosen explicitly

Use the sections below as ready-to-paste project updates or as the content for manual task creation.

## Completed

### 1. Repository cleanup and public-friendly structure

- Title: Clean repository structure and remove personal references
- Description: Reworked documentation and source metadata so the repo no longer depends on personal absolute filesystem paths in repo-facing materials.
- Priority: High
- Dependencies: none
- Acceptance criteria:
  - root docs use repo-relative language
  - knowledge registry no longer stores personal machine paths
  - important local source docs are copied into the repo
- Next step: review any remaining private/company-sensitive content before external collaborator access

### 2. Documentation system for future developers

- Title: Add full engineering documentation set
- Description: Added architecture, deployment, domain, roadmap, GitHub Desktop, and ClickUp update docs for new-team onboarding.
- Priority: High
- Dependencies: repo structure clarity
- Acceptance criteria:
  - README covers product overview and repo entrypoint
  - docs index exists
  - architecture and deployment docs are complete
- Next step: keep docs updated alongside each milestone

### 3. Vercel deployment preparation

- Title: Add Vercel-ready repo files
- Description: Added a serverless entrypoint and Vercel routing config so the current monolith has a default free-first deployment path.
- Priority: High
- Dependencies: FastAPI app import stability
- Acceptance criteria:
  - `api/index.py` exists
  - `vercel.json` exists
  - deployment guide documents the environment setup
- Next step: test a private Vercel deployment once secrets are ready

### 4. Kite MCP hosted bridge integration

- Title: Integrate hosted Kite MCP into FastAPI
- Description: Replaced the placeholder bridge assumption with a direct hosted-MCP session flow inside the app. The backend now creates MCP sessions, generates the Zerodha login URL, validates session state, and exposes holdings/positions/search through the same FastAPI app.
- Priority: High
- Dependencies: Zerodha login flow must remain intact
- Acceptance criteria:
  - app can generate a live Zerodha login URL
  - session state is tracked per user
  - instrument search works through the hosted endpoint
  - holdings and positions endpoints use the connected session
- Next step: validate with a real Kite login and portfolio payload

### 5. Postgres-backed runtime state

- Title: Wire runtime persistence to PostgreSQL
- Description: Extended the local app-state service so it can switch from JSON fallback to PostgreSQL-backed users, watchlist, search history, feedback, Kite session metadata, and portfolio snapshots when configured.
- Priority: High
- Dependencies: Postgres DSN and deployment secret management
- Acceptance criteria:
  - app state supports Postgres reads/writes
  - migrations auto-apply from the repo migration folder
  - local JSON remains a fallback for non-configured environments
- Next step: test against a real Postgres instance and set production secrets

## In Progress

### 6. Real environment validation

- Title: Validate hosted Kite and Postgres against live credentials
- Description: The code path is implemented, but it still needs real-user validation with a live Zerodha session and a real Postgres DSN.
- Priority: High
- Dependencies: user login and infrastructure credentials
- Acceptance criteria:
  - real Kite account reaches connected state
  - portfolio payloads load from live holdings/positions
  - Postgres-backed state is verified with actual writes
- Next step: run a real local validation session with credentials enabled

## Pending

### 7. Deployment validation

- Title: Validate private deployment on Vercel
- Description: Confirm the current app boots correctly with private GitHub integration and environment variables.
- Priority: Medium
- Dependencies: secrets, Vercel project setup
- Acceptance criteria:
  - private repo is connected
  - app renders successfully
  - static assets, auth shell, and API endpoints respond
- Next step: run a first internal deploy

### 8. Domain connection

- Title: Connect GoDaddy-managed domain
- Description: Set up a subdomain for the deployed app and verify HTTPS.
- Priority: Medium
- Dependencies: successful deployment
- Acceptance criteria:
  - domain points correctly
  - SSL is active
  - login and static files work under the custom domain
- Next step: add the domain in Vercel, then update GoDaddy DNS

### 9. Feedback storage upgrade

- Title: Move feedback from local storage to Firestore
- Description: Keep the current feedback UI but route persistence into Firestore when enabled.
- Priority: Medium
- Dependencies: Firebase credentials
- Acceptance criteria:
  - submissions are stored in Firestore
  - metadata is preserved
- Next step: add the Firestore write path and fallback handling

## Blocked

### 10. Production-grade persistence rollout

- Title: Turn on Postgres in production
- Description: The code path exists, but production still depends on local JSON until a Postgres DSN is configured in the deployment environment.
- Priority: High
- Dependencies: managed Postgres instance and secrets
- Acceptance criteria:
  - no production dependency on local JSON
- Next step: provision the database and add deployment secrets

### 11. Portfolio-grade live insights

- Title: Unlock fully personalized portfolio insights
- Description: Portfolio analytics depend on the unfinished Kite bridge and valid portfolio payloads.
- Priority: High
- Dependencies: Kite bridge and auth flow
- Acceptance criteria:
  - holdings and positions populate reliably
  - insights update from real data
- Next step: complete live bridge integration

## Future Roadmap

### 11. Watchlist and monitoring expansion

- Title: Expand watchlist into a monitoring system
- Description: Move from simple saved symbols to richer monitoring, notes, and alert hooks.
- Priority: Medium
- Dependencies: Postgres, background jobs
- Acceptance criteria:
  - multi-list support
  - tags and thesis notes
  - alert hooks
- Next step: define watchlist schema v2

### 12. Knowledge ingestion expansion

- Title: Add structured source ingestion workflows
- Description: Scale the book/framework system into a larger ingestion pipeline for notes, annual reports, and research.
- Priority: Medium
- Dependencies: source registry and storage plan
- Acceptance criteria:
  - ingest new sources with metadata
  - influence reasoning consistently
- Next step: define ingestion pipeline stages
