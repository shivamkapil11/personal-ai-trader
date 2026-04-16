# Local Stock Research Dashboard

This is a local dashboard for stock research and comparison. It runs on your machine, shows a live loading screen with step-by-step progress updates, supports comparing up to three stocks, and can pull TradingView chart snapshots through either:

- `tradingview-mcp` for the installed TradingView Desktop app
- `tradingview-chart-mcp` as a browser-cookie fallback

## What it does

- single-stock or multi-stock comparison
- natural-language prompts, company names, or raw ticker input
- optional free-form thoughts that get auto-structured into a cleaner research brief
- live research progress feed while analysis runs
- summary dashboard with swing vs long-term classification
- technical indicators and price structure
- fundamentals snapshot and valuation summary
- recent headline feed from Yahoo Finance
- an intent layer that infers whether you meant a single-stock run or a side-by-side comparison
- optional TradingView chart snapshots using the local desktop bridge first, then the cookie-based browser bridge as fallback

## Folder layout

- `stock-dashboard/`: this app
- `tradingview-mcp/`: cloned TradingView Desktop bridge repo
- `tradingview-chart-mcp/`: cloned browser-cookie snapshot repo

## Quick start

```bash
cd /Users/shivamsworld/Documents/OpenAi/stock-dashboard
cp .env.example .env
./run_local.sh
```

Then open:

```text
http://127.0.0.1:8008
```

## TradingView Desktop bridge

The dashboard now prefers the locally running TradingView Desktop bridge at:

```text
/Users/shivamsworld/Documents/OpenAi/tradingview-mcp
```

The bridge talks to the installed app on your Mac through Chrome DevTools Protocol.

If TradingView is not already in debug mode, launch it with:

```bash
cd /Users/shivamsworld/Documents/OpenAi/tradingview-mcp
node src/cli/index.js launch --no-kill
```

That uses your installed Desktop app and keeps the workflow local.

## Browser snapshot fallback

The dashboard also knows how to use the cloned browser snapshot repo at:

```text
/Users/shivamsworld/Documents/OpenAi/tradingview-chart-mcp
```

To enable the fallback browser snapshots, add your TradingView cookies to `.env`:

```bash
TRADINGVIEW_SESSION_ID=...
TRADINGVIEW_SESSION_ID_SIGN=...
```

Those values come from your logged-in TradingView browser cookies. Without them, the dashboard still works, but the snapshot section will show a helpful setup message instead of a live chart image.

## Notes

- Market data and headlines are pulled from `yfinance`.
- Classification is rules-based and transparent, so you can extend the scoring logic without needing another service.
- This app is designed for local use and development, not production hardening.
