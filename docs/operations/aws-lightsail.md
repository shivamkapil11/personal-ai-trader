# AWS Lightsail Deployment Guide

## Recommended AWS path

For this app, the simplest AWS route is:

- `AWS Lightsail`
- `Ubuntu instance`
- `nginx` as reverse proxy
- `uvicorn` behind a `systemd` service

This is simpler than App Runner for the current stack and easier to pair with a GoDaddy domain.

## Cost estimate

- `$5/month` instance is enough for light demo traffic
- `$10/month` gives more comfort
- with `$120` in AWS credits:
  - about `24 months` at `$5/month`
  - about `12 months` at `$10/month`

## What is already prepared in the repo

- `deploy/lightsail/setup_server.sh`
- `deploy/lightsail/gains.service`
- `deploy/lightsail/nginx-gains.conf`

## Step 1: Create the Lightsail instance

1. Open AWS Lightsail.
2. Create an instance.
3. Platform: `Linux/Unix`
4. Blueprint: `OS Only -> Ubuntu 24.04 LTS`
5. Instance plan: start with `$5/month`
6. Name it `gains-app`

## Step 2: Attach a static IP

1. In Lightsail, open `Networking`.
2. Create a static IP.
3. Attach it to `gains-app`.

Keep this IP for GoDaddy later.

## Step 3: SSH into the instance

You can use the browser SSH terminal from Lightsail or your local terminal.

## Step 4: Run the setup script

First get the repo onto the server. Since your GitHub repo is private, use one of these:

- clone with GitHub credentials or SSH key
- or upload the repo archive to the server and unzip it

Then run:

```bash
cd /home/ubuntu/personal-ai-trader
bash deploy/lightsail/setup_server.sh
```

## Step 5: Configure environment variables

Edit:

```bash
nano /home/ubuntu/personal-ai-trader/.env
```

Set at minimum:

```bash
APP_TITLE=Gains
APP_SECRET=<long-random-secret>
APP_HOST=127.0.0.1
APP_PORT=8008
POSTGRES_ENABLED=false
KITE_MCP_ENABLED=true
KITE_MCP_MODE=hosted
KITE_MCP_URL=https://mcp.kite.trade/mcp
FIREBASE_ENABLED=true
FIREBASE_API_KEY=<value>
FIREBASE_AUTH_DOMAIN=<value>
FIREBASE_PROJECT_ID=<value>
FIREBASE_STORAGE_BUCKET=<value>
FIREBASE_MESSAGING_SENDER_ID=<value>
FIREBASE_APP_ID=<value>
FIREBASE_MEASUREMENT_ID=<value>
FIREBASE_ADMIN_CREDENTIALS_JSON=<single-line-json>
AUTH_ALLOW_DEV_FALLBACK=false
TRADINGVIEW_ENABLED=false
TRADINGVIEW_DESKTOP_ENABLED=false
```

## Step 6: Restart the app

```bash
sudo systemctl restart gains
sudo systemctl status gains
```

## Step 7: Verify in browser

Open:

```text
http://<your-static-ip>
```

## Step 8: GoDaddy domain

For a subdomain like `app.yourdomain.com`:

1. In GoDaddy DNS, add an `A` record.
2. Host: `app`
3. Value: `<your Lightsail static IP>`

Then add that same domain to Firebase `Authorized domains`.

## Useful commands

```bash
sudo systemctl status gains
sudo systemctl restart gains
sudo systemctl status nginx
sudo nginx -t
tail -f /var/log/nginx/error.log
journalctl -u gains -f
```

## Important note

The local AWS CLI available on this Mac is a user-local install, which is enough for AWS commands here, but the actual app deployment happens on the Lightsail server after the instance is created and SSH access is available.
