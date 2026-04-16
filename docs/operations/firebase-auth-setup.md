# Firebase Google Auth Setup

Use this to turn the current local-dev auth fallback into real Google sign-in.

## Create the Firebase project

1. Open the Firebase console.
2. Create a project for the dashboard.
3. Add a Web app to that project.
4. Copy the generated web config values.

## Enable Google sign-in

1. Open `Authentication`.
2. Open the `Sign-in method` section.
3. Enable `Google`.
4. Set a support email and save.

## Add authorized domains

Add each domain where the dashboard will run:

- `localhost` for local testing
- your Vercel preview domains if needed
- your final production domain or subdomain

## Create an Admin SDK key

1. Open project `Settings`.
2. Open `Service Accounts`.
3. Click `Generate new private key`.
4. Save the JSON file somewhere safe outside the repo when possible.

## Add local environment variables

Update `.env`:

```bash
FIREBASE_ENABLED=true
FIREBASE_API_KEY=<web-api-key>
FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
FIREBASE_PROJECT_ID=<project-id>
FIREBASE_STORAGE_BUCKET=<project-id>.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=<sender-id>
FIREBASE_APP_ID=<app-id>
FIREBASE_MEASUREMENT_ID=<measurement-id-if-used>
FIREBASE_ADMIN_CREDENTIALS_PATH=/absolute/path/to/service-account.json
AUTH_ALLOW_DEV_FALLBACK=false
```

If you plan to deploy on Vercel, use this instead of a file path:

```bash
FIREBASE_ADMIN_CREDENTIALS_JSON='{"type":"service_account","project_id":"..."}'
```

You only need one of these:

- `FIREBASE_ADMIN_CREDENTIALS_PATH`
- `FIREBASE_ADMIN_CREDENTIALS_JSON`

## Restart and verify

```bash
cd /Users/shivamsworld/Documents/OpenAi/stock-dashboard
./run_local.sh
curl http://127.0.0.1:8008/health
```

Expected:

- `auth.firebase_enabled` should be `true`
- `auth.firebase_backend_ready` should be `true`
- `auth.firebase_admin_ready` should be `true`
- `auth.firebase_missing` should be an empty list

## Production notes

- Add the same Firebase web config values in Vercel project environment variables.
- Prefer `FIREBASE_ADMIN_CREDENTIALS_JSON` in Vercel rather than a filesystem path.
- Add the final production domain to Firebase Auth authorized domains before testing Google login in production.
