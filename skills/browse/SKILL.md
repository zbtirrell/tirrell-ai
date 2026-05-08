---
name: browse
description: |
  Lightweight headless-Chromium browse tool. Fetches web content past Cloudflare-style
  walls that block WebFetch. No daemon — each call is a fresh subprocess (~2-4s),
  with cookies persisted on disk so logins/auth survive between calls.
  Use when WebFetch returns 403/Cloudflare challenge, or when reading rendered JS-heavy
  pages (SPAs, gated newsletters, etc.). Built specifically because gstack browse was
  unreliable on this machine (unsigned-binary kills, daemon crashes).
allowed-tools:
  - Bash
  - Read
---

# z:browse

Bun + Playwright wrapper. Real Chromium, no daemon, persistent on-disk profile.

## First-time setup

```bash
~/.claude/plugins/marketplaces/tirrell-ai/skills/browse/setup.sh
```

This installs the Bun deps and downloads Playwright Chromium (~150MB). Required once after install / on a new machine.

## Why this exists

`WebFetch` fails on Cloudflare-protected pages (403 + "Just a moment..." interstitial). `gstack browse` was the documented fallback, but its daemon binary is unsigned and macOS Gatekeeper kills it intermittently (exit 137). This skill is a clean replacement: small, transparent, and stable.

## Commands

```bash
B=~/.claude/plugins/marketplaces/tirrell-ai/skills/browse/browse

$B goto <url>           # Navigate to URL (waits for networkidle)
$B text [url]           # Print page innerText (loads url if given)
$B html [url]           # Print page outerHTML
$B markdown [url]       # Print page as markdown (article-friendly)
$B screenshot <path>    # Save full-page PNG to path
$B url                  # Print current page URL
$B clear                # Wipe profile (cookies, cache)
```

If `text` / `html` / `markdown` is called without a URL, it re-loads the last URL visited (cached at `~/.zbt-browse/last-url`).

## Architecture

- **Runtime:** Bun (fast startup; already on this machine)
- **Browser:** Playwright bundled Chromium (avoids conflict with the user's Chrome.app)
- **Profile:** Persistent at `~/.zbt-browse/profile/` — cookies, localStorage, and auth state survive between calls
- **No daemon:** Every command spawns a fresh subprocess. Slower than gstack (~2-4s per call vs ~100ms after warmup), but completely stable.

## Cloudflare bypass

Two soft anti-detection measures:
1. Realistic Chrome UA + viewport + en-US locale + America/New_York timezone
2. `navigator.webdriver` masked to `false` via init script

For most newsletter / blog Cloudflare challenges this is enough. If a target requires harder stealth (Akamai, Datadome, Cloudflare Turnstile), upgrade to `playwright-extra` + `puppeteer-extra-plugin-stealth`. Not done by default — adds dependency weight not yet justified.

## When to use this vs WebFetch

| Situation | Use |
|-----------|-----|
| Public docs, GitHub, plain HTML | `WebFetch` (faster, no Chromium spin-up) |
| Cloudflare 403, "Just a moment..." | `z:browse` |
| JS-rendered SPA content | `z:browse` |
| Authenticated pages (after first manual login) | `z:browse` |
| Google services (Drive, Docs, Sheets, Calendar, Gmail) | The respective `mcp__claude_ai_*` MCP — auth handled |

## Maintenance

- Source: `skills/browse/src/browse.ts`
- Wrapper: `skills/browse/browse` (Bash → Bun)
- Setup script: `skills/browse/setup.sh`
- Reset profile (clear cookies/cache): `$B clear`
