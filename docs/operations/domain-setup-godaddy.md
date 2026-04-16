# GoDaddy Domain Setup

This guide assumes:

- the repository stays private
- the current recommended deployment target is Vercel
- the custom domain is managed in GoDaddy

## Recommended Domain Flow

1. Deploy the app on Vercel first.
2. Add the domain inside Vercel.
3. Update DNS records in GoDaddy.
4. Wait for verification.
5. Confirm HTTPS is active.

## Suggested Domain Structure

- production app: `app.yourdomain.com`
- marketing or landing page later: `www.yourdomain.com`
- API later if split: `api.yourdomain.com`

This is cleaner than pointing the root domain directly to an app that may still change architecture.

## DNS Steps

### If using a subdomain like `app.yourdomain.com`

In Vercel:

1. Open your project.
2. Go to `Settings -> Domains`.
3. Add `app.yourdomain.com`.
4. Vercel will show the DNS target.

In GoDaddy DNS:

1. Open your domain DNS management.
2. Add a `CNAME` record.
3. Host/name: `app`
4. Points to: the Vercel target shown in project settings
5. Save changes.

### If using the apex/root domain like `yourdomain.com`

In Vercel:

1. Add the root domain in project settings.
2. Copy the exact DNS records Vercel provides.

In GoDaddy DNS:

1. Add or update the required `A` record or records Vercel specifies.
2. If Vercel asks for TXT verification, add that too.

## SSL Notes

Vercel automatically provisions SSL once:

- the domain points correctly
- DNS propagates
- domain verification succeeds

You do not need to buy a separate SSL certificate from GoDaddy for this setup.

## Verification Checklist

- domain added inside Vercel
- DNS records updated in GoDaddy
- no conflicting old A/CNAME records remain
- domain status inside Vercel shows active or verified
- `https://app.yourdomain.com` loads successfully
- certificate warning is gone
- app assets and static files load over HTTPS

## Common Problems

### Domain stays unverified

Check:

- typo in host/name field
- stale DNS records still present
- wrong value copied from Vercel
- DNS propagation delay

### SSL does not appear immediately

This usually resolves after domain verification completes. Recheck after DNS propagation.

### App loads but login breaks

Check:

- Firebase auth domain allow-list
- cookie behavior under HTTPS
- environment variables in the deployed app

## Private Repo Note

Keeping the repository private does not change domain setup. The deploy platform only needs access to the private GitHub repo through the linked GitHub account or Vercel integration.
